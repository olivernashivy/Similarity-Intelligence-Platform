"""Tests for keyword extraction service."""

import pytest
from src.youtube_similarity.services.keyword_extractor import KeywordExtractor


class TestKeywordExtractor:
    """Test cases for KeywordExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create keyword extractor instance."""
        return KeywordExtractor(max_keywords=10)

    def test_extract_keywords_basic(self, extractor):
        """Test basic keyword extraction."""
        title = "Understanding Machine Learning Algorithms"
        content = """
        Machine learning algorithms are fundamental to artificial intelligence.
        These algorithms learn patterns from data and make predictions.
        Popular algorithms include neural networks, decision trees, and support vector machines.
        """

        keywords = extractor.extract_keywords(title, content)

        assert "title_weighted_terms" in keywords
        assert "named_entities" in keywords
        assert "tfidf_phrases" in keywords
        assert "all_keywords" in keywords

        # Check that some keywords were extracted
        assert len(keywords["all_keywords"]) > 0

    def test_title_weighted_terms(self, extractor):
        """Test that title terms are properly weighted."""
        title = "Python Programming Tutorial"
        content = "Learn Python programming with this comprehensive tutorial."

        keywords = extractor.extract_keywords(title, content)

        # Title words should appear in weighted terms
        weighted = [term.lower() for term in keywords["title_weighted_terms"]]
        assert any("python" in term for term in weighted)

    def test_named_entity_extraction(self, extractor):
        """Test named entity extraction."""
        title = "Article About Technology"
        content = """
        Google and Microsoft are leading companies in artificial intelligence.
        Tesla is revolutionizing the automotive industry.
        """

        keywords = extractor.extract_keywords(title, content)

        entities = keywords["named_entities"]
        # Should find some capitalized entities
        assert len(entities) > 0

    def test_build_search_query(self, extractor):
        """Test search query building."""
        keywords = {
            "title_weighted_terms": ["machine learning", "algorithms"],
            "named_entities": ["Google", "TensorFlow"],
            "tfidf_phrases": ["neural networks", "deep learning"]
        }

        query = extractor.build_search_query(keywords, max_terms=5)

        assert len(query) > 0
        assert isinstance(query, str)

    def test_empty_content(self, extractor):
        """Test handling of empty content."""
        title = "Test Title"
        content = ""

        keywords = extractor.extract_keywords(title, content)

        # Should still return structure even with empty content
        assert "all_keywords" in keywords
