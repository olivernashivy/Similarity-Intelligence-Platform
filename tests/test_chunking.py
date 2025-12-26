"""Tests for text chunking module."""
import pytest
from app.core.chunking import TextChunker, extract_keywords, TextChunk


class TestTextChunker:
    """Test cases for TextChunker class."""

    @pytest.fixture
    def chunker(self):
        """Create text chunker instance."""
        return TextChunker(min_words=40, max_words=60, overlap_words=10)

    def test_chunk_text_basic(self, chunker, sample_article_text):
        """Test basic text chunking."""
        chunks = chunker.chunk_text(sample_article_text, normalize=True)

        # Should produce multiple chunks
        assert len(chunks) > 0
        assert all(isinstance(chunk, TextChunk) for chunk in chunks)

        # Check chunk properties
        for chunk in chunks:
            assert hasattr(chunk, 'text')
            assert hasattr(chunk, 'index')
            assert hasattr(chunk, 'start_word')
            assert hasattr(chunk, 'end_word')

    def test_chunk_text_short_input(self, chunker, sample_short_text):
        """Test chunking with text shorter than min_words."""
        chunks = chunker.chunk_text(sample_short_text, normalize=True)

        # Should return single chunk for short text
        assert len(chunks) == 1
        assert chunks[0].index == 0

    def test_chunk_text_empty_input(self, chunker, sample_empty_text):
        """Test chunking with empty input."""
        chunks = chunker.chunk_text(sample_empty_text, normalize=True)

        # Should return empty list for empty input
        assert len(chunks) == 0

    def test_chunk_normalization(self, chunker):
        """Test that text is normalized when normalize=True."""
        text = "  HELLO   World!  This IS a TEST.  "
        chunks = chunker.chunk_text(text, normalize=True)

        # Normalized text should be lowercase and cleaned
        if chunks:
            assert chunks[0].text.islower()
            assert '  ' not in chunks[0].text  # No double spaces

    def test_chunk_overlap(self, chunker):
        """Test that chunks have proper overlap."""
        # Create text with exactly 100 words
        text = " ".join([f"word{i:03d}" for i in range(100)])
        chunks = chunker.chunk_text(text, normalize=False)

        # Should have multiple chunks with overlap
        if len(chunks) > 1:
            # Check that chunks overlap
            chunk0_words = chunks[0].text.split()
            chunk1_words = chunks[1].text.split()

            # Last words of chunk 0 should appear in chunk 1
            # (due to overlap_words=10)
            overlap_found = any(
                word in chunk1_words[:15]
                for word in chunk0_words[-15:]
            )
            assert overlap_found

    def test_chunk_word_count_limits(self, chunker):
        """Test that chunks respect min/max word limits."""
        # Create long text
        text = " ".join([f"word{i}" for i in range(200)])
        chunks = chunker.chunk_text(text, normalize=False)

        # Check word counts (allow some flexibility for last chunk)
        for i, chunk in enumerate(chunks[:-1]):  # Exclude last chunk
            word_count = len(chunk.text.split())
            assert chunker.min_words <= word_count <= chunker.max_words

    def test_chunk_indices(self, chunker, sample_article_text):
        """Test that chunk indices are sequential."""
        chunks = chunker.chunk_text(sample_article_text, normalize=True)

        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_chunk_text_preserves_content(self, chunker):
        """Test that chunking doesn't lose content."""
        text = "Important information that should not be lost during chunking process."
        chunks = chunker.chunk_text(text, normalize=False)

        # Reconstruct text from chunks (accounting for overlap)
        assert len(chunks) > 0
        # At minimum, first chunk should contain some original words
        original_words = set(text.split())
        chunk_words = set(' '.join([c.text for c in chunks]).split())
        overlap_count = len(original_words & chunk_words)
        assert overlap_count >= len(original_words) * 0.8  # At least 80% preserved


class TestExtractKeywords:
    """Test cases for keyword extraction."""

    def test_extract_keywords_basic(self, sample_article_text):
        """Test basic keyword extraction."""
        keywords = extract_keywords(sample_article_text, top_k=10)

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert len(keywords) <= 10

        # Keywords should be strings
        assert all(isinstance(kw, str) for kw in keywords)

    def test_extract_keywords_empty_input(self, sample_empty_text):
        """Test keyword extraction with empty input."""
        keywords = extract_keywords(sample_empty_text, top_k=10)

        # Should return empty list or handle gracefully
        assert isinstance(keywords, list)
        assert len(keywords) == 0

    def test_extract_keywords_short_text(self, sample_short_text):
        """Test keyword extraction with short text."""
        keywords = extract_keywords(sample_short_text, top_k=10)

        # Should return some keywords even for short text
        assert isinstance(keywords, list)
        # May have fewer than top_k keywords
        assert len(keywords) <= 10

    def test_extract_keywords_top_k_limit(self, sample_article_text):
        """Test that top_k limit is respected."""
        top_k = 5
        keywords = extract_keywords(sample_article_text, top_k=top_k)

        assert len(keywords) <= top_k

    def test_extract_keywords_uniqueness(self, sample_article_text):
        """Test that extracted keywords are unique."""
        keywords = extract_keywords(sample_article_text, top_k=20)

        # No duplicate keywords
        assert len(keywords) == len(set(keywords))

    def test_extract_keywords_relevance(self):
        """Test that keywords are relevant to content."""
        text = """
        Machine learning and artificial intelligence are revolutionary technologies.
        Machine learning algorithms can learn from data.
        Artificial intelligence systems are becoming more sophisticated.
        """
        keywords = extract_keywords(text, top_k=10)

        # Should extract relevant domain terms
        keywords_lower = [kw.lower() for kw in keywords]
        # At least one of the key terms should be present
        assert any(
            term in ' '.join(keywords_lower)
            for term in ['machine', 'learning', 'artificial', 'intelligence', 'algorithm']
        )

    def test_extract_keywords_stopwords_filtered(self):
        """Test that common stopwords are filtered."""
        text = "The quick brown fox jumps over the lazy dog. " * 10
        keywords = extract_keywords(text, top_k=10)

        # Common stopwords shouldn't dominate keywords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were'}
        keywords_set = set(kw.lower() for kw in keywords)

        # Most keywords should not be stopwords
        stopword_count = len(keywords_set & stopwords)
        assert stopword_count < len(keywords) * 0.3  # Less than 30% stopwords


class TestTextChunk:
    """Test cases for TextChunk dataclass."""

    def test_text_chunk_creation(self):
        """Test TextChunk creation."""
        chunk = TextChunk(
            text="sample chunk text",
            index=0,
            start_word=0,
            end_word=3
        )

        assert chunk.text == "sample chunk text"
        assert chunk.index == 0
        assert chunk.start_word == 0
        assert chunk.end_word == 3

    def test_text_chunk_equality(self):
        """Test TextChunk equality comparison."""
        chunk1 = TextChunk(text="test", index=0, start_word=0, end_word=1)
        chunk2 = TextChunk(text="test", index=0, start_word=0, end_word=1)

        # Should be equal if all fields match
        assert chunk1 == chunk2

    def test_text_chunk_string_representation(self):
        """Test TextChunk string representation."""
        chunk = TextChunk(text="sample text", index=1, start_word=5, end_word=10)

        str_repr = str(chunk)
        assert "sample text" in str_repr or "TextChunk" in str_repr
