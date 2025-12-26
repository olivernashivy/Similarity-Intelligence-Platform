"""Similarity matching service for comparing article and transcript embeddings."""

import logging
from typing import List, Tuple
import numpy as np

from ..config import settings
from ..models import (
    TranscriptChunk,
    VideoMetadata,
    SimilarityMatch,
    VideoSimilarityResult
)

logger = logging.getLogger(__name__)


class SimilarityMatcher:
    """
    Matches article chunks against transcript chunks using vector similarity.

    Provides:
    - Pairwise similarity calculation
    - Match aggregation per video
    - Coverage calculation
    - Result ranking
    """

    def __init__(self, similarity_threshold: float = None):
        """
        Initialize similarity matcher.

        Args:
            similarity_threshold: Minimum similarity score for matches
        """
        self.similarity_threshold = similarity_threshold or settings.similarity_threshold

    def find_matches(
        self,
        article_embeddings: List[np.ndarray],
        transcript_chunks: List[TranscriptChunk],
        transcript_embeddings: List[np.ndarray],
        video_metadata: VideoMetadata
    ) -> VideoSimilarityResult:
        """
        Find similarity matches between article and transcript.

        Args:
            article_embeddings: Article chunk embeddings
            transcript_chunks: Transcript chunks
            transcript_embeddings: Transcript chunk embeddings
            video_metadata: Video metadata

        Returns:
            Aggregated similarity results for the video
        """
        if not article_embeddings or not transcript_embeddings:
            logger.warning(f"Empty embeddings for video {video_metadata.video_id}")
            return self._create_empty_result(video_metadata)

        if len(transcript_chunks) != len(transcript_embeddings):
            logger.error(
                f"Mismatch between chunks ({len(transcript_chunks)}) "
                f"and embeddings ({len(transcript_embeddings)})"
            )
            return self._create_empty_result(video_metadata)

        # Calculate similarity matrix
        similarity_matrix = self._calculate_similarity_matrix(
            article_embeddings,
            transcript_embeddings
        )

        # Find high-similarity matches
        matches = self._extract_matches(
            similarity_matrix,
            transcript_chunks,
            video_metadata
        )

        # Aggregate results
        result = self._aggregate_results(matches, video_metadata)

        logger.info(
            f"Found {len(matches)} matches for video {video_metadata.video_id} "
            f"(max similarity: {result.max_similarity:.3f})"
        )

        return result

    def _calculate_similarity_matrix(
        self,
        embeddings1: List[np.ndarray],
        embeddings2: List[np.ndarray]
    ) -> np.ndarray:
        """
        Calculate pairwise similarity matrix.

        Args:
            embeddings1: First set of embeddings
            embeddings2: Second set of embeddings

        Returns:
            Similarity matrix of shape (len(embeddings1), len(embeddings2))
        """
        # Convert to numpy arrays
        matrix1 = np.array(embeddings1)
        matrix2 = np.array(embeddings2)

        # Normalize
        matrix1_norm = matrix1 / np.linalg.norm(matrix1, axis=1, keepdims=True)
        matrix2_norm = matrix2 / np.linalg.norm(matrix2, axis=1, keepdims=True)

        # Calculate cosine similarity
        similarity_matrix = np.dot(matrix1_norm, matrix2_norm.T)

        # Shift to [0, 1] range
        similarity_matrix = (similarity_matrix + 1) / 2

        return similarity_matrix

    def _extract_matches(
        self,
        similarity_matrix: np.ndarray,
        transcript_chunks: List[TranscriptChunk],
        video_metadata: VideoMetadata
    ) -> List[SimilarityMatch]:
        """
        Extract high-similarity matches from similarity matrix.

        Args:
            similarity_matrix: Similarity scores matrix
            transcript_chunks: Transcript chunks
            video_metadata: Video metadata

        Returns:
            List of similarity matches
        """
        matches = []

        # For each article chunk, find best matching transcript chunks
        for article_idx in range(similarity_matrix.shape[0]):
            article_similarities = similarity_matrix[article_idx]

            # Find transcript chunks above threshold
            high_similarity_indices = np.where(
                article_similarities >= self.similarity_threshold
            )[0]

            for transcript_idx in high_similarity_indices:
                chunk = transcript_chunks[transcript_idx]
                similarity_score = float(article_similarities[transcript_idx])

                # Create match
                match = SimilarityMatch(
                    video_id=video_metadata.video_id,
                    video_title=video_metadata.title,
                    channel_name=video_metadata.channel_name,
                    video_url=video_metadata.url,
                    timestamp_start=chunk.start,
                    timestamp_end=chunk.end,
                    transcript_snippet=self._truncate_snippet(chunk.text),
                    similarity_score=similarity_score,
                    matched_chunks_count=1
                )
                matches.append(match)

        # Merge overlapping/adjacent matches
        merged_matches = self._merge_adjacent_matches(matches)

        return merged_matches

    def _merge_adjacent_matches(
        self,
        matches: List[SimilarityMatch]
    ) -> List[SimilarityMatch]:
        """
        Merge adjacent or overlapping matches.

        Args:
            matches: List of similarity matches

        Returns:
            Merged list of matches
        """
        if not matches:
            return []

        # Sort by timestamp
        sorted_matches = sorted(matches, key=lambda m: m.timestamp_start)

        merged = []
        current = sorted_matches[0]

        for next_match in sorted_matches[1:]:
            # Check if matches are adjacent (within 10 seconds)
            if next_match.timestamp_start - current.timestamp_end <= 10:
                # Merge matches
                current = SimilarityMatch(
                    video_id=current.video_id,
                    video_title=current.video_title,
                    channel_name=current.channel_name,
                    video_url=current.video_url,
                    timestamp_start=current.timestamp_start,
                    timestamp_end=next_match.timestamp_end,
                    transcript_snippet=self._truncate_snippet(
                        f"{current.transcript_snippet} {next_match.transcript_snippet}"
                    ),
                    similarity_score=max(current.similarity_score, next_match.similarity_score),
                    matched_chunks_count=current.matched_chunks_count + 1
                )
            else:
                # Save current and start new
                merged.append(current)
                current = next_match

        # Add last match
        merged.append(current)

        return merged

    def _aggregate_results(
        self,
        matches: List[SimilarityMatch],
        video_metadata: VideoMetadata
    ) -> VideoSimilarityResult:
        """
        Aggregate matches into video-level results.

        Args:
            matches: List of similarity matches
            video_metadata: Video metadata

        Returns:
            Aggregated video similarity result
        """
        if not matches:
            return self._create_empty_result(video_metadata)

        # Calculate metrics
        max_similarity = max(match.similarity_score for match in matches)
        total_matched_chunks = sum(match.matched_chunks_count for match in matches)

        # Calculate coverage (percentage of video with matches)
        total_match_duration = sum(
            match.timestamp_end - match.timestamp_start
            for match in matches
        )
        coverage_percentage = (
            (total_match_duration / video_metadata.duration_seconds) * 100
            if video_metadata.duration_seconds > 0
            else 0
        )

        return VideoSimilarityResult(
            video_id=video_metadata.video_id,
            video_title=video_metadata.title,
            channel_name=video_metadata.channel_name,
            video_url=video_metadata.url,
            max_similarity=max_similarity,
            matched_chunks_count=total_matched_chunks,
            coverage_percentage=coverage_percentage,
            matches=matches
        )

    def _create_empty_result(
        self,
        video_metadata: VideoMetadata
    ) -> VideoSimilarityResult:
        """
        Create empty result for video with no matches.

        Args:
            video_metadata: Video metadata

        Returns:
            Empty video similarity result
        """
        return VideoSimilarityResult(
            video_id=video_metadata.video_id,
            video_title=video_metadata.title,
            channel_name=video_metadata.channel_name,
            video_url=video_metadata.url,
            max_similarity=0.0,
            matched_chunks_count=0,
            coverage_percentage=0.0,
            matches=[]
        )

    def _truncate_snippet(self, text: str, max_length: int = 300) -> str:
        """
        Truncate text to maximum length.

        Args:
            text: Input text
            max_length: Maximum length

        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text

        # Find last space before max_length
        truncated = text[:max_length].rsplit(' ', 1)[0]
        return f"{truncated}..."

    def rank_results(
        self,
        results: List[VideoSimilarityResult]
    ) -> List[VideoSimilarityResult]:
        """
        Rank video results by relevance.

        Args:
            results: List of video similarity results

        Returns:
            Sorted list of results
        """
        # Rank by max similarity, then by matched chunks count
        return sorted(
            results,
            key=lambda r: (r.max_similarity, r.matched_chunks_count),
            reverse=True
        )
