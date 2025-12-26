"""Tests for text utility functions."""

import pytest
from src.youtube_similarity.utils.text_utils import (
    normalize_text,
    chunk_text_by_words,
    truncate_text,
    clean_transcript_text,
    calculate_word_count
)


class TestTextUtils:
    """Test cases for text utility functions."""

    def test_normalize_text(self):
        """Test text normalization."""
        text = "  Hello   WORLD!  This is a TEST.  "
        normalized = normalize_text(text, remove_fillers=False)

        assert normalized == "hello world! this is a test."

    def test_normalize_text_with_fillers(self):
        """Test text normalization with filler word removal."""
        text = "Um, like, you know, this is actually a test"
        normalized = normalize_text(text, remove_fillers=True)

        # Fillers should be removed
        assert "um" not in normalized
        assert "like" not in normalized
        assert "actually" not in normalized
        assert "test" in normalized

    def test_chunk_text_by_words(self):
        """Test text chunking by word count."""
        text = " ".join([f"word{i}" for i in range(100)])
        chunks = chunk_text_by_words(text, chunk_size=20, overlap=5)

        # Should create multiple chunks
        assert len(chunks) > 1

        # Each chunk should have approximately correct size
        for chunk in chunks[:-1]:  # Exclude last chunk
            word_count = len(chunk.split())
            assert word_count <= 20

    def test_chunk_short_text(self):
        """Test chunking of short text."""
        text = "This is a short text"
        chunks = chunk_text_by_words(text, chunk_size=50)

        # Should return single chunk for short text
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_truncate_text(self):
        """Test text truncation."""
        text = "This is a long text that needs to be truncated"
        truncated = truncate_text(text, max_length=20)

        assert len(truncated) <= 23  # max_length + "..."
        assert truncated.endswith("...")

    def test_truncate_short_text(self):
        """Test truncation of already short text."""
        text = "Short text"
        truncated = truncate_text(text, max_length=50)

        assert truncated == text

    def test_clean_transcript_text(self):
        """Test transcript cleaning."""
        text = "[00:01:23] Speaker 1: Hello [Music] this is a test [Applause]"
        cleaned = clean_transcript_text(text)

        # Timestamps and annotations should be removed
        assert "[00:01:23]" not in cleaned
        assert "Speaker 1:" not in cleaned
        assert "[Music]" not in cleaned
        assert "hello" in cleaned
        assert "test" in cleaned

    def test_calculate_word_count(self):
        """Test word count calculation."""
        text = "This is a test sentence with seven words"
        count = calculate_word_count(text)

        assert count == 8
