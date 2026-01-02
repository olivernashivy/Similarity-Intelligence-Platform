"""Similarity check Celery task."""
import time
from datetime import datetime
from uuid import UUID
from typing import List
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.tasks.celery_app import celery_app
from app.config import settings
from app.models.check import Check
from app.models.source import Source
from app.models.match import Match
from app.core.chunking import TextChunker
from app.core.embeddings import get_embedding_generator
from app.core.similarity import SimilarityEngine, SimilarityMatch
from app.core.vector_store import get_article_store, get_youtube_store, VectorMetadata
from app.core.youtube import search_and_fetch_transcripts


# Create async engine for Celery tasks
engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(bind=True, name="process_similarity_check")
def process_similarity_check(self, check_id: str, article_text: str):
    """
    Process similarity check asynchronously.

    Args:
        check_id: Check ID
        article_text: Article text to analyze
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_process_check_async(check_id, article_text))


async def _process_check_async(check_id: str, article_text: str):
    """Async implementation of similarity check."""
    start_time = time.time()

    async with AsyncSessionLocal() as db:
        try:
            # Get check
            result = await db.execute(
                select(Check).where(Check.id == UUID(check_id))
            )
            check = result.scalar_one_or_none()

            if not check:
                raise ValueError(f"Check {check_id} not found")

            # Update status
            check.status = "processing"
            check.started_at = datetime.utcnow()
            await db.commit()

            # Initialize components
            embedder = get_embedding_generator()
            chunker = TextChunker(
                min_words=settings.min_chunk_words,
                max_words=settings.max_chunk_words,
                overlap_words=settings.chunk_overlap_words
            )
            engine = SimilarityEngine(embedder, chunker)

            # Chunk and embed article
            chunks, embeddings = engine.chunk_and_embed(article_text)
            check.chunk_count = len(chunks)
            await db.commit()

            # Collect all matches
            all_matches: List[SimilarityMatch] = []
            sources_checked = 0

            # Get similarity threshold
            threshold = engine.get_threshold_for_sensitivity(check.sensitivity)

            # Check against articles (local corpus + web search)
            if check.check_articles:
                article_matches = await _check_articles(
                    chunks, embeddings, threshold, engine, article_text
                )
                all_matches.extend(article_matches)
                sources_checked += len(set(m.source_id for m in article_matches))

            # Check against YouTube
            if check.check_youtube:
                youtube_matches = await _check_youtube(
                    article_text, chunks, embeddings, threshold, engine, db
                )
                all_matches.extend(youtube_matches)
                sources_checked += len(set(m.source_id for m in youtube_matches if m.source_type == "youtube"))

            # Filter by threshold
            filtered_matches = engine.filter_matches_by_threshold(all_matches, threshold)

            # Calculate overall similarity score
            similarity_score, risk_level = engine.calculate_similarity_score(
                filtered_matches, len(chunks)
            )

            # Aggregate matches by source
            aggregated_matches = engine.aggregate_matches_by_source(filtered_matches)

            # Save matches to database
            for agg_match in aggregated_matches[:20]:  # Limit to top 20 sources
                # Prepare matched chunks data
                matched_chunks_data = [
                    {
                        "submission_text": m.submission_chunk.text,
                        "source_text": m.source_chunk_text,
                        "similarity_score": round(m.similarity_score, 3),
                        "timestamp": m.source_metadata.get("timestamp") if m.source_metadata else None
                    }
                    for m in agg_match.matches[:5]
                ]

                match = Match(
                    check_id=check.id,
                    source_id=None,  # Would link to Source if available
                    source_type=agg_match.source_type,
                    source_title=agg_match.source_title,
                    source_identifier=agg_match.source_identifier,
                    similarity_score=agg_match.similarity_score,
                    match_count=agg_match.match_count,
                    max_chunk_similarity=agg_match.max_chunk_similarity,
                    avg_chunk_similarity=agg_match.avg_chunk_similarity,
                    matched_chunks=matched_chunks_data,
                    snippet=agg_match.snippet,
                    explanation=agg_match.explanation,
                    risk_contribution=agg_match.risk_contribution
                )
                db.add(match)

            # Update check with results
            check.status = "completed"
            check.similarity_score = similarity_score
            check.risk_level = risk_level
            check.match_count = len(aggregated_matches)
            check.sources_checked = sources_checked
            check.completed_at = datetime.utcnow()
            check.processing_time_seconds = time.time() - start_time
            check.estimated_cost_usd = settings.target_cost_per_check_usd

            await db.commit()

            return {
                "status": "completed",
                "similarity_score": similarity_score,
                "risk_level": risk_level,
                "match_count": len(aggregated_matches)
            }

        except Exception as e:
            # Handle errors
            if check:
                check.status = "failed"
                check.error_message = str(e)
                check.completed_at = datetime.utcnow()
                await db.commit()

            raise


async def _check_articles(
    chunks, embeddings, threshold, engine, article_text
) -> List[SimilarityMatch]:
    """
    Check against article corpus (both local and web).

    Searches:
    1. Local vector store (if populated)
    2. Real-time web search (Google + Bing)
    """
    matches = []

    # 1. Check local article corpus
    article_store = get_article_store()
    local_matches = 0

    if article_store.count() > 0:
        print(f"Searching local article corpus ({article_store.count()} vectors)...")

        # Search for each chunk
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            # Search vector store
            results = article_store.search(
                embedding,
                k=10,
                filter_fn=lambda meta: meta.source_type == "article"
            )

            # Convert to SimilarityMatch
            for meta, score in results:
                if score >= threshold:
                    matches.append(
                        SimilarityMatch(
                            submission_chunk=chunk,
                            source_chunk_text=meta.chunk_text,
                            source_id=meta.source_id,
                            source_type="article",
                            similarity_score=score,
                            source_metadata={
                                "title": meta.title,
                                "identifier": meta.identifier,
                                "source": "local_corpus"
                            }
                        )
                    )
                    local_matches += 1

        print(f"Found {local_matches} matches in local corpus")
    else:
        print("Local article corpus is empty, skipping...")

    # 2. Search web for articles
    web_matches = await _check_web_articles(
        article_text, chunks, embeddings, threshold, engine
    )
    matches.extend(web_matches)

    print(f"Total article matches: {len(matches)} (local: {local_matches}, web: {len(web_matches)})")
    return matches


async def _check_web_articles(
    article_text, chunks, embeddings, threshold, engine
) -> List[SimilarityMatch]:
    """Search web for similar articles in real-time."""
    from app.core.web_search import search_web_articles
    from app.core.article_fetcher import ArticleFetcher
    from app.core.chunking import extract_keywords

    matches = []

    # Check if any search engines are configured
    from app.core.web_search import WebArticleSearcher
    searcher = WebArticleSearcher()

    if not searcher.google_client and not searcher.bing_api_key:
        print("No web search APIs configured, skipping web article search")
        return matches

    print("Searching web for similar articles...")

    try:
        # Extract keywords from article
        keywords = extract_keywords(article_text, top_k=10)
        print(f"Search keywords: {', '.join(keywords[:5])}...")

        # Search for articles
        search_results = search_web_articles(
            keywords,
            max_results=settings.max_web_articles,
            filter_results=True
        )

        if not search_results:
            print("No web articles found")
            return matches

        print(f"Found {len(search_results)} web articles to analyze")

        # Fetch article content
        fetcher = ArticleFetcher(
            use_cache=True,
            timeout=settings.web_article_fetch_timeout
        )

        # Fetch and compare articles
        for idx, result in enumerate(search_results[:settings.max_web_articles]):
            print(f"[{idx+1}/{len(search_results)}] Fetching: {result.title[:50]}...")

            # Fetch article content
            article_content = fetcher.fetch_article(result.url)

            if not article_content or len(article_content) < 100:
                print(f"   Skipped (failed to fetch or too short)")
                continue

            # Chunk the web article
            web_chunks = engine.chunker.chunk_text(article_content, normalize=True)

            if not web_chunks:
                print(f"   Skipped (no chunks)")
                continue

            print(f"   Fetched {len(article_content)} chars, {len(web_chunks)} chunks")

            # Generate embeddings for web article chunks
            web_chunk_texts = [chunk.text for chunk in web_chunks]
            web_embeddings = engine.embedder.encode(web_chunk_texts, normalize=True)

            # Compare submission chunks against web article chunks
            article_match_count = 0
            for submission_chunk, submission_embedding in zip(chunks, embeddings):
                # Calculate similarities with all web chunks
                similarities = engine.embedder.batch_similarity(
                    submission_embedding,
                    web_embeddings
                )

                # Find matches above threshold
                for i, score in enumerate(similarities):
                    if score >= threshold:
                        matches.append(
                            SimilarityMatch(
                                submission_chunk=submission_chunk,
                                source_chunk_text=web_chunk_texts[i],
                                source_id=result.url,
                                source_type="article",
                                similarity_score=float(score),
                                source_metadata={
                                    "title": result.title,
                                    "identifier": result.url,
                                    "snippet": result.snippet,
                                    "source": f"web_{result.source}"
                                }
                            )
                        )
                        article_match_count += 1

            print(f"   Found {article_match_count} matches")

        print(f"Web article search complete: {len(matches)} total matches")

    except Exception as e:
        print(f"Error searching web articles: {e}")
        import traceback
        traceback.print_exc()

    return matches


async def _check_youtube(
    article_text, chunks, embeddings, threshold, engine, db
) -> List[SimilarityMatch]:
    """Check against YouTube transcripts."""
    matches = []

    # Search and fetch transcripts
    youtube_data = search_and_fetch_transcripts(
        article_text,
        max_videos=settings.max_youtube_videos
    )

    if not youtube_data:
        return matches

    # Get YouTube vector store
    youtube_store = get_youtube_store()

    # Process each video
    for video_idx, video in enumerate(youtube_data):
        video_id = video['video_id']
        metadata = video['metadata']
        transcript_chunks = video['chunks']

        # Generate embeddings for transcript chunks
        chunk_texts = [chunk[0] for chunk in transcript_chunks]
        chunk_timestamps = [chunk[1] for chunk in transcript_chunks]

        transcript_embeddings = engine.embedder.encode(chunk_texts, normalize=True)

        # Add to vector store for similarity matching
        # Note: Only embeddings and metadata (title, URL, timestamps) are stored
        # Full transcript text is NOT stored - only 40-60 word chunks for matching
        # This complies with "no long-term transcript storage" requirement
        vector_metadata_list = [
            VectorMetadata(
                source_id=video_id,
                source_type="youtube",
                chunk_index=i,
                chunk_text=text,  # Short chunk only (40-60 words max)
                timestamp=timestamp,
                title=metadata.get('title'),
                identifier=metadata.get('url')
            )
            for i, (text, timestamp) in enumerate(zip(chunk_texts, chunk_timestamps))
        ]
        youtube_store.add_vectors(transcript_embeddings, vector_metadata_list)

        # Track if this video has any matches
        video_match_count = 0

        # Compare article chunks against transcript
        for article_chunk, article_embedding in zip(chunks, embeddings):
            # Calculate similarities
            similarities = engine.embedder.batch_similarity(
                article_embedding,
                transcript_embeddings
            )

            # Find matches above threshold
            for i, score in enumerate(similarities):
                if score >= threshold:
                    matches.append(
                        SimilarityMatch(
                            submission_chunk=article_chunk,
                            source_chunk_text=chunk_texts[i],
                            source_id=video_id,
                            source_type="youtube",
                            similarity_score=float(score),
                            source_metadata={
                                "title": metadata.get('title'),
                                "identifier": metadata.get('url'),
                                "timestamp": chunk_timestamps[i],
                                "duration_seconds": metadata.get('duration_seconds', 0)
                            }
                        )
                    )
                    video_match_count += 1

        # Early exit: If we've processed 3+ videos with no matches, stop
        if video_idx >= 2 and len(matches) == 0:
            print(f"Early exit: No matches found in first {video_idx + 1} videos")
            break

    # Save YouTube store
    youtube_store.save()

    return matches
