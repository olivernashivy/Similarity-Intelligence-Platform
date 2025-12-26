"""Core similarity detection engine."""
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from app.core.chunking import TextChunk, TextChunker
from app.core.embeddings import EmbeddingGenerator
from app.config import settings


@dataclass
class SimilarityMatch:
    """Represents a similarity match between chunks."""

    submission_chunk: TextChunk
    source_chunk_text: str
    source_id: str
    source_type: str
    similarity_score: float
    source_metadata: Optional[Dict] = None


@dataclass
class AggregatedMatch:
    """Aggregated similarity result for a source."""

    source_id: str
    source_type: str
    source_title: Optional[str]
    source_identifier: Optional[str]

    similarity_score: float  # Normalized 0-1
    match_count: int
    max_chunk_similarity: float
    avg_chunk_similarity: float

    matches: List[SimilarityMatch]
    snippet: Optional[str] = None
    explanation: Optional[str] = None
    risk_contribution: Optional[str] = None


class SimilarityEngine:
    """Core similarity detection engine."""

    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        chunker: Optional[TextChunker] = None
    ):
        """
        Initialize similarity engine.

        Args:
            embedding_generator: Embedding generator instance
            chunker: Text chunker (optional)
        """
        self.embedder = embedding_generator
        self.chunker = chunker or TextChunker(
            min_words=settings.min_chunk_words,
            max_words=settings.max_chunk_words,
            overlap_words=settings.chunk_overlap_words
        )

    def chunk_and_embed(self, text: str) -> Tuple[List[TextChunk], np.ndarray]:
        """
        Chunk text and generate embeddings.

        Args:
            text: Input text

        Returns:
            Tuple of (chunks, embeddings)
        """
        # Chunk the text
        chunks = self.chunker.chunk_text(text, normalize=True)

        # Generate embeddings for all chunks
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = self.embedder.encode(chunk_texts, normalize=True)

        return chunks, embeddings

    def calculate_similarity_score(
        self,
        matches: List[SimilarityMatch],
        total_chunks: int
    ) -> Tuple[float, str]:
        """
        Calculate overall similarity score and risk level.

        Uses multiple signals:
        - Max similarity
        - Number of matches
        - Average similarity
        - Coverage (% of chunks matched)

        Args:
            matches: List of similarity matches
            total_chunks: Total number of chunks in submission

        Returns:
            Tuple of (score 0-100, risk_level)
        """
        if not matches:
            return 0.0, "low"

        # Extract similarity scores
        scores = [m.similarity_score for m in matches]

        # Calculate metrics
        max_similarity = max(scores)
        avg_similarity = np.mean(scores)
        match_count = len(matches)
        coverage = match_count / total_chunks if total_chunks > 0 else 0

        # Weighted scoring
        # - Max similarity (40% weight)
        # - Average similarity (30% weight)
        # - Coverage (20% weight)
        # - Match count bonus (10% weight)
        score = (
            max_similarity * 40 +
            avg_similarity * 30 +
            coverage * 20 +
            min(match_count / 5, 1.0) * 10  # Cap at 5 matches
        )

        # Determine risk level based on thresholds
        if score >= settings.similarity_threshold_high * 100:
            risk_level = "high"
        elif score >= settings.similarity_threshold_medium * 100:
            risk_level = "medium"
        else:
            risk_level = "low"

        return round(score, 2), risk_level

    def aggregate_matches_by_source(
        self,
        matches: List[SimilarityMatch]
    ) -> List[AggregatedMatch]:
        """
        Group matches by source and aggregate metrics.

        Args:
            matches: List of individual matches

        Returns:
            List of aggregated matches per source
        """
        # Group by source_id
        source_groups: Dict[str, List[SimilarityMatch]] = {}
        for match in matches:
            if match.source_id not in source_groups:
                source_groups[match.source_id] = []
            source_groups[match.source_id].append(match)

        # Aggregate each source
        aggregated = []
        for source_id, source_matches in source_groups.items():
            scores = [m.similarity_score for m in source_matches]

            # Get source metadata from first match
            first_match = source_matches[0]
            source_metadata = first_match.source_metadata or {}

            # Calculate aggregated metrics
            max_score = max(scores)
            avg_score = np.mean(scores)
            match_count = len(source_matches)

            # Overall similarity for this source (weighted)
            overall_similarity = (max_score * 0.6 + avg_score * 0.4)

            # Determine risk contribution
            if overall_similarity >= settings.similarity_threshold_high:
                risk_contribution = "high"
            elif overall_similarity >= settings.similarity_threshold_medium:
                risk_contribution = "medium"
            else:
                risk_contribution = "low"

            # Generate snippet and explanation
            snippet = self._generate_snippet(source_matches)
            explanation = self._generate_explanation(
                source_matches,
                overall_similarity,
                first_match.source_type
            )

            aggregated.append(
                AggregatedMatch(
                    source_id=source_id,
                    source_type=first_match.source_type,
                    source_title=source_metadata.get("title"),
                    source_identifier=source_metadata.get("identifier"),
                    similarity_score=round(overall_similarity, 3),
                    match_count=match_count,
                    max_chunk_similarity=round(max_score, 3),
                    avg_chunk_similarity=round(avg_score, 3),
                    matches=source_matches[:5],  # Limit to top 5
                    snippet=snippet,
                    explanation=explanation,
                    risk_contribution=risk_contribution
                )
            )

        # Sort by similarity score (descending)
        aggregated.sort(key=lambda x: x.similarity_score, reverse=True)

        return aggregated

    def _generate_snippet(self, matches: List[SimilarityMatch]) -> str:
        """Generate a short snippet from the best match."""
        if not matches:
            return ""

        # Get the match with highest similarity
        best_match = max(matches, key=lambda m: m.similarity_score)

        # Truncate to max length
        snippet = best_match.source_chunk_text
        if len(snippet) > settings.snippet_max_length:
            snippet = snippet[:settings.snippet_max_length - 3] + "..."

        return snippet

    def _generate_explanation(
        self,
        matches: List[SimilarityMatch],
        similarity: float,
        source_type: str
    ) -> str:
        """Generate human-readable explanation."""
        match_count = len(matches)
        percentage = int(similarity * 100)

        if match_count == 1:
            return (
                f"Found 1 matching segment with {percentage}% similarity "
                f"to this {source_type}."
            )
        else:
            return (
                f"Found {match_count} matching segments with up to {percentage}% similarity "
                f"to this {source_type}. This suggests potential overlap in content or ideas."
            )

    def filter_matches_by_threshold(
        self,
        matches: List[SimilarityMatch],
        threshold: float
    ) -> List[SimilarityMatch]:
        """
        Filter matches by similarity threshold.

        Args:
            matches: List of matches
            threshold: Minimum similarity score (0-1)

        Returns:
            Filtered matches
        """
        return [m for m in matches if m.similarity_score >= threshold]

    def get_threshold_for_sensitivity(self, sensitivity: str) -> float:
        """
        Get similarity threshold based on sensitivity level.

        Args:
            sensitivity: "low", "medium", or "high"

        Returns:
            Threshold value
        """
        thresholds = {
            "low": settings.similarity_threshold_high,  # Only high confidence
            "medium": settings.similarity_threshold_medium,  # Medium and above
            "high": settings.similarity_threshold_low  # Low and above (more sensitive)
        }
        return thresholds.get(sensitivity, settings.similarity_threshold_medium)
