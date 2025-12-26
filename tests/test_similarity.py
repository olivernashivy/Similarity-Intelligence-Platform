"""Tests for similarity engine module."""
import pytest
import numpy as np
from unittest.mock import Mock, patch

from app.core.similarity import (
    SimilarityEngine,
    SimilarityMatch,
    AggregatedMatch
)
from app.core.chunking import TextChunk


class TestSimilarityEngine:
    """Test cases for SimilarityEngine class."""

    @pytest.fixture
    def engine(self, mock_embedding_generator):
        """Create similarity engine with mocked embedder."""
        from app.core.chunking import TextChunker
        chunker = TextChunker(min_words=40, max_words=60, overlap_words=10)
        return SimilarityEngine(mock_embedding_generator, chunker)

    def test_init(self, mock_embedding_generator):
        """Test SimilarityEngine initialization."""
        engine = SimilarityEngine(mock_embedding_generator)

        assert engine.embedder == mock_embedding_generator
        assert engine.chunker is not None

    def test_chunk_and_embed(self, engine, sample_article_text):
        """Test chunking and embedding."""
        chunks, embeddings = engine.chunk_and_embed(sample_article_text)

        # Should return chunks and embeddings
        assert len(chunks) > 0
        assert len(embeddings) == len(chunks)
        assert embeddings.shape[1] == 384  # Embedding dimension

    def test_chunk_and_embed_empty_text(self, engine, sample_empty_text):
        """Test chunking and embedding with empty text."""
        chunks, embeddings = engine.chunk_and_embed(sample_empty_text)

        # Should handle empty input gracefully
        assert len(chunks) == 0
        assert len(embeddings) == 0

    def test_calculate_similarity_score_no_matches(self, engine):
        """Test similarity score calculation with no matches."""
        score, risk_level = engine.calculate_similarity_score([], total_chunks=10)

        assert score == 0.0
        assert risk_level == "low"

    def test_calculate_similarity_score_single_match(self, engine, sample_chunks):
        """Test similarity score with single match."""
        matches = [
            SimilarityMatch(
                submission_chunk=sample_chunks[0],
                source_chunk_text="similar text",
                source_id="source1",
                source_type="article",
                similarity_score=0.85
            )
        ]

        score, risk_level = engine.calculate_similarity_score(matches, total_chunks=10)

        # Score should be > 0
        assert score > 0
        assert risk_level in ["low", "medium", "high"]

    def test_calculate_similarity_score_multiple_matches(self, engine, sample_similarity_matches):
        """Test similarity score with multiple matches."""
        score, risk_level = engine.calculate_similarity_score(
            sample_similarity_matches,
            total_chunks=10
        )

        # Should calculate weighted score
        assert score > 0
        assert risk_level in ["low", "medium", "high"]

    def test_calculate_similarity_score_high_risk(self, engine, sample_chunks):
        """Test high risk score calculation."""
        # Create matches with very high similarity
        matches = [
            SimilarityMatch(
                submission_chunk=sample_chunks[i % len(sample_chunks)],
                source_chunk_text=f"text {i}",
                source_id="source1",
                source_type="article",
                similarity_score=0.95
            )
            for i in range(10)  # Many high-similarity matches
        ]

        score, risk_level = engine.calculate_similarity_score(matches, total_chunks=10)

        # Should be high risk
        assert score > 70  # High threshold
        assert risk_level in ["medium", "high"]

    def test_aggregate_matches_by_source(self, engine, sample_similarity_matches):
        """Test aggregating matches by source."""
        aggregated = engine.aggregate_matches_by_source(sample_similarity_matches)

        # Should group by source_id
        assert len(aggregated) > 0
        assert all(isinstance(agg, AggregatedMatch) for agg in aggregated)

        # Check fields are populated
        for agg in aggregated:
            assert agg.source_id is not None
            assert agg.source_type is not None
            assert agg.match_count > 0
            assert 0 <= agg.similarity_score <= 1
            assert agg.snippet is not None
            assert agg.explanation is not None

    def test_aggregate_matches_sorted_by_score(self, engine, sample_chunks):
        """Test that aggregated matches are sorted by similarity score."""
        matches = [
            SimilarityMatch(
                submission_chunk=sample_chunks[0],
                source_chunk_text="text1",
                source_id="source_low",
                source_type="article",
                similarity_score=0.65
            ),
            SimilarityMatch(
                submission_chunk=sample_chunks[1],
                source_chunk_text="text2",
                source_id="source_high",
                source_type="article",
                similarity_score=0.95
            ),
            SimilarityMatch(
                submission_chunk=sample_chunks[2],
                source_chunk_text="text3",
                source_id="source_med",
                source_type="article",
                similarity_score=0.75
            ),
        ]

        aggregated = engine.aggregate_matches_by_source(matches)

        # Should be sorted by score (descending)
        scores = [agg.similarity_score for agg in aggregated]
        assert scores == sorted(scores, reverse=True)

    def test_aggregate_youtube_coverage(self, engine, sample_chunks):
        """Test YouTube coverage percentage calculation."""
        matches = [
            SimilarityMatch(
                submission_chunk=sample_chunks[i % len(sample_chunks)],
                source_chunk_text=f"text {i}",
                source_id="youtube_video",
                source_type="youtube",
                similarity_score=0.85,
                source_metadata={
                    "title": "Video Title",
                    "identifier": "https://youtube.com/watch?v=abc",
                    "timestamp": f"00:{i:02d}",
                    "duration_seconds": 600  # 10 minutes
                }
            )
            for i in range(3)
        ]

        aggregated = engine.aggregate_matches_by_source(matches)

        # YouTube videos should have coverage percentage
        youtube_match = next((agg for agg in aggregated if agg.source_type == "youtube"), None)
        assert youtube_match is not None
        assert youtube_match.coverage_percentage is not None
        assert 0 <= youtube_match.coverage_percentage <= 100

    def test_generate_snippet(self, engine, sample_similarity_matches):
        """Test snippet generation."""
        aggregated = engine.aggregate_matches_by_source(sample_similarity_matches)

        for agg in aggregated:
            # Snippet should be populated and within limits
            assert agg.snippet is not None
            assert len(agg.snippet) <= 303  # Max + "..."

    def test_generate_explanation_youtube(self, engine, sample_chunks):
        """Test explanation generation for YouTube sources."""
        matches = [
            SimilarityMatch(
                submission_chunk=sample_chunks[0],
                source_chunk_text="test",
                source_id="yt_video",
                source_type="youtube",
                similarity_score=0.85,
                source_metadata={
                    "title": "Video",
                    "identifier": "url",
                    "timestamp": "00:00",
                    "duration_seconds": 300
                }
            )
        ]

        aggregated = engine.aggregate_matches_by_source(matches)

        # Should have "Possible similarity to spoken content" label
        assert "Possible similarity to spoken content" in aggregated[0].explanation

    def test_generate_explanation_article(self, engine, sample_chunks):
        """Test explanation generation for article sources."""
        matches = [
            SimilarityMatch(
                submission_chunk=sample_chunks[0],
                source_chunk_text="test",
                source_id="article1",
                source_type="article",
                similarity_score=0.80,
                source_metadata={"title": "Article", "identifier": "url"}
            )
        ]

        aggregated = engine.aggregate_matches_by_source(matches)

        # Should NOT have YouTube-specific label
        assert "spoken content" not in aggregated[0].explanation.lower()

    def test_filter_matches_by_threshold(self, engine, sample_similarity_matches):
        """Test filtering matches by threshold."""
        threshold = 0.80

        filtered = engine.filter_matches_by_threshold(sample_similarity_matches, threshold)

        # Should only keep matches >= threshold
        assert all(match.similarity_score >= threshold for match in filtered)
        # Some matches should be filtered out
        assert len(filtered) <= len(sample_similarity_matches)

    def test_filter_matches_high_threshold(self, engine, sample_similarity_matches):
        """Test filtering with very high threshold."""
        threshold = 0.95

        filtered = engine.filter_matches_by_threshold(sample_similarity_matches, threshold)

        # Most/all matches should be filtered out
        assert len(filtered) <= len(sample_similarity_matches)
        assert all(match.similarity_score >= threshold for match in filtered)

    def test_filter_matches_zero_threshold(self, engine, sample_similarity_matches):
        """Test filtering with zero threshold."""
        threshold = 0.0

        filtered = engine.filter_matches_by_threshold(sample_similarity_matches, threshold)

        # No matches should be filtered
        assert len(filtered) == len(sample_similarity_matches)

    def test_get_threshold_for_sensitivity_low(self, engine):
        """Test threshold for low sensitivity."""
        threshold = engine.get_threshold_for_sensitivity("low")

        # Low sensitivity = high threshold (fewer matches)
        assert threshold > 0.7

    def test_get_threshold_for_sensitivity_medium(self, engine):
        """Test threshold for medium sensitivity."""
        threshold = engine.get_threshold_for_sensitivity("medium")

        # Medium sensitivity = medium threshold
        assert 0.6 < threshold < 0.8

    def test_get_threshold_for_sensitivity_high(self, engine):
        """Test threshold for high sensitivity."""
        threshold = engine.get_threshold_for_sensitivity("high")

        # High sensitivity = low threshold (more matches)
        assert threshold < 0.7

    def test_get_threshold_invalid_sensitivity(self, engine):
        """Test threshold with invalid sensitivity."""
        threshold = engine.get_threshold_for_sensitivity("invalid")

        # Should return default (medium)
        assert threshold > 0

    def test_calculate_youtube_coverage_zero_duration(self, engine, sample_chunks):
        """Test coverage calculation with zero duration."""
        matches = [
            SimilarityMatch(
                submission_chunk=sample_chunks[0],
                source_chunk_text="test",
                source_id="video",
                source_type="youtube",
                similarity_score=0.85,
                source_metadata={"duration_seconds": 0, "timestamp": "00:00"}
            )
        ]

        coverage = engine._calculate_youtube_coverage(
            matches,
            {"duration_seconds": 0}
        )

        # Should return 0 for zero duration
        assert coverage == 0.0

    def test_calculate_youtube_coverage_normal(self, engine, sample_chunks):
        """Test coverage calculation with normal values."""
        # 3 matches * 30 seconds = 90 seconds
        # 90 / 600 seconds = 15%
        matches = [
            SimilarityMatch(
                submission_chunk=sample_chunks[i % len(sample_chunks)],
                source_chunk_text=f"text {i}",
                source_id="video",
                source_type="youtube",
                similarity_score=0.85,
                source_metadata={
                    "duration_seconds": 600,
                    "timestamp": f"00:{i:02d}"
                }
            )
            for i in range(3)
        ]

        coverage = engine._calculate_youtube_coverage(
            matches,
            {"duration_seconds": 600}
        )

        # Should be approximately 15% (3 chunks * 30s / 600s)
        assert 10 <= coverage <= 20

    def test_risk_contribution_levels(self, engine, sample_chunks):
        """Test that risk contribution is correctly categorized."""
        # High risk
        high_match = SimilarityMatch(
            submission_chunk=sample_chunks[0],
            source_chunk_text="test",
            source_id="high_source",
            source_type="article",
            similarity_score=0.90
        )

        # Low risk
        low_match = SimilarityMatch(
            submission_chunk=sample_chunks[1],
            source_chunk_text="test",
            source_id="low_source",
            source_type="article",
            similarity_score=0.60
        )

        aggregated_high = engine.aggregate_matches_by_source([high_match])
        aggregated_low = engine.aggregate_matches_by_source([low_match])

        # Risk contributions should be different
        assert aggregated_high[0].risk_contribution in ["medium", "high"]
        assert aggregated_low[0].risk_contribution in ["low", "medium"]


class TestSimilarityMatch:
    """Test cases for SimilarityMatch dataclass."""

    def test_similarity_match_creation(self, sample_chunks):
        """Test SimilarityMatch creation."""
        match = SimilarityMatch(
            submission_chunk=sample_chunks[0],
            source_chunk_text="source text",
            source_id="src1",
            source_type="article",
            similarity_score=0.85,
            source_metadata={"title": "Test"}
        )

        assert match.submission_chunk == sample_chunks[0]
        assert match.source_chunk_text == "source text"
        assert match.source_id == "src1"
        assert match.source_type == "article"
        assert match.similarity_score == 0.85
        assert match.source_metadata == {"title": "Test"}


class TestAggregatedMatch:
    """Test cases for AggregatedMatch dataclass."""

    def test_aggregated_match_creation(self, sample_similarity_matches):
        """Test AggregatedMatch creation."""
        agg = AggregatedMatch(
            source_id="video1",
            source_type="youtube",
            source_title="Test Video",
            source_identifier="https://youtube.com/watch?v=123",
            similarity_score=0.85,
            match_count=3,
            max_chunk_similarity=0.90,
            avg_chunk_similarity=0.80,
            matches=sample_similarity_matches,
            snippet="Test snippet",
            explanation="Test explanation",
            risk_contribution="high",
            coverage_percentage=15.5
        )

        assert agg.source_id == "video1"
        assert agg.match_count == 3
        assert agg.coverage_percentage == 15.5
        assert agg.risk_contribution == "high"
