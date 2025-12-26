"""Tests for embedding generation module."""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from app.core.embeddings import EmbeddingGenerator, get_embedding_generator


class TestEmbeddingGenerator:
    """Test cases for EmbeddingGenerator class."""

    @pytest.fixture
    def mock_model(self):
        """Create mock SentenceTransformer model."""
        mock = MagicMock()

        def mock_encode(texts, batch_size=32, show_progress_bar=False,
                       convert_to_numpy=True, normalize_embeddings=True):
            """Mock encode that returns deterministic embeddings."""
            np.random.seed(42)
            n = len(texts) if isinstance(texts, list) else 1
            embeddings = np.random.randn(n, 384).astype(np.float32)
            if normalize_embeddings:
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                embeddings = embeddings / norms
            return embeddings

        mock.encode = Mock(side_effect=mock_encode)
        return mock

    @pytest.fixture
    def generator(self, mock_model):
        """Create EmbeddingGenerator with mocked model."""
        with patch('app.core.embeddings.SentenceTransformer') as mock_st:
            mock_st.return_value = mock_model

            # Reset singleton to force new instance
            EmbeddingGenerator._instance = None
            EmbeddingGenerator._model = None

            with patch('app.core.embeddings.settings') as mock_settings:
                mock_settings.embedding_model = "test-model"
                mock_settings.embedding_dimension = 384

                gen = EmbeddingGenerator()
                gen._model = mock_model
                return gen

    def test_singleton_pattern(self, generator):
        """Test that EmbeddingGenerator uses singleton pattern."""
        # Create another instance
        gen2 = EmbeddingGenerator()

        # Should be the same instance
        assert generator is gen2

    def test_dimension_property(self, generator):
        """Test dimension property."""
        with patch('app.core.embeddings.settings') as mock_settings:
            mock_settings.embedding_dimension = 384

            assert generator.dimension == 384

    def test_model_property(self, generator):
        """Test model property."""
        model = generator.model

        assert model is not None

    def test_encode_single_text(self, generator):
        """Test encoding a single text string."""
        text = "This is a test sentence"

        embeddings = generator.encode(text, normalize=True)

        # Should return 2D array with shape (1, 384)
        assert embeddings.shape == (1, 384)
        assert isinstance(embeddings, np.ndarray)

    def test_encode_multiple_texts(self, generator):
        """Test encoding multiple texts."""
        texts = [
            "First sentence",
            "Second sentence",
            "Third sentence"
        ]

        embeddings = generator.encode(texts, normalize=True)

        # Should return 2D array with shape (3, 384)
        assert embeddings.shape == (3, 384)
        assert isinstance(embeddings, np.ndarray)

    def test_encode_empty_list(self, generator):
        """Test encoding empty list."""
        texts = []

        embeddings = generator.encode(texts, normalize=True)

        # Should return empty array
        assert embeddings.shape[0] == 0

    def test_encode_normalization(self, generator):
        """Test that normalization works correctly."""
        text = "Test sentence"

        # Encode with normalization
        embeddings_norm = generator.encode(text, normalize=True)

        # Check that embeddings are normalized (L2 norm ≈ 1)
        norm = np.linalg.norm(embeddings_norm[0])
        assert np.isclose(norm, 1.0, rtol=1e-5)

    def test_encode_single_method(self, generator):
        """Test encode_single convenience method."""
        text = "Test sentence"

        embedding = generator.encode_single(text, normalize=True)

        # Should return 1D array
        assert embedding.shape == (384,)
        assert isinstance(embedding, np.ndarray)

    def test_similarity_identical_embeddings(self, generator):
        """Test similarity between identical embeddings."""
        # Create identical normalized embeddings
        embedding = np.random.randn(384)
        embedding = embedding / np.linalg.norm(embedding)

        similarity = generator.similarity(embedding, embedding)

        # Should be very close to 1.0
        assert np.isclose(similarity, 1.0, rtol=1e-5)
        assert 0.0 <= similarity <= 1.0

    def test_similarity_orthogonal_embeddings(self, generator):
        """Test similarity between orthogonal embeddings."""
        # Create orthogonal normalized embeddings
        np.random.seed(42)
        embedding1 = np.zeros(384)
        embedding1[0] = 1.0

        embedding2 = np.zeros(384)
        embedding2[1] = 1.0

        similarity = generator.similarity(embedding1, embedding2)

        # Should be close to 0.0
        assert np.isclose(similarity, 0.0, rtol=1e-5)
        assert 0.0 <= similarity <= 1.0

    def test_similarity_similar_embeddings(self, generator):
        """Test similarity between similar but not identical embeddings."""
        np.random.seed(42)
        embedding1 = np.random.randn(384)
        embedding1 = embedding1 / np.linalg.norm(embedding1)

        # Create similar embedding (with noise)
        embedding2 = embedding1 + np.random.randn(384) * 0.1
        embedding2 = embedding2 / np.linalg.norm(embedding2)

        similarity = generator.similarity(embedding1, embedding2)

        # Should be high but not 1.0
        assert 0.7 < similarity < 1.0

    def test_batch_similarity(self, generator):
        """Test batch similarity calculation."""
        np.random.seed(42)

        # Create query embedding
        query = np.random.randn(384)
        query = query / np.linalg.norm(query)

        # Create candidate embeddings
        candidates = np.random.randn(5, 384)
        # Normalize each candidate
        norms = np.linalg.norm(candidates, axis=1, keepdims=True)
        candidates = candidates / norms

        similarities = generator.batch_similarity(query, candidates)

        # Should return array of 5 similarities
        assert similarities.shape == (5,)
        assert isinstance(similarities, np.ndarray)

        # All similarities should be in [0, 1]
        assert np.all(similarities >= 0.0)
        assert np.all(similarities <= 1.0)

    def test_batch_similarity_identical(self, generator):
        """Test batch similarity with identical embedding."""
        np.random.seed(42)

        # Create query embedding
        query = np.random.randn(384)
        query = query / np.linalg.norm(query)

        # Create candidates including identical query
        candidates = np.random.randn(5, 384)
        norms = np.linalg.norm(candidates, axis=1, keepdims=True)
        candidates = candidates / norms

        # Replace first candidate with query
        candidates[0] = query

        similarities = generator.batch_similarity(query, candidates)

        # First similarity should be ~1.0
        assert np.isclose(similarities[0], 1.0, rtol=1e-5)

    def test_batch_similarity_empty_candidates(self, generator):
        """Test batch similarity with empty candidates."""
        query = np.random.randn(384)
        query = query / np.linalg.norm(query)

        candidates = np.empty((0, 384))

        similarities = generator.batch_similarity(query, candidates)

        # Should return empty array
        assert similarities.shape == (0,)

    def test_encode_batch_size_parameter(self, generator):
        """Test that batch_size parameter is passed correctly."""
        texts = [f"Text {i}" for i in range(10)]

        # Should not raise an error
        embeddings = generator.encode(texts, batch_size=4, normalize=True)

        assert embeddings.shape == (10, 384)

    def test_model_loading_error(self):
        """Test handling of model loading errors."""
        with patch('app.core.embeddings.SentenceTransformer') as mock_st:
            mock_st.side_effect = RuntimeError("Model not found")

            # Reset singleton
            EmbeddingGenerator._instance = None
            EmbeddingGenerator._model = None

            with patch('app.core.embeddings.settings') as mock_settings:
                mock_settings.embedding_model = "invalid-model"

                # Should raise RuntimeError
                with pytest.raises(RuntimeError, match="Failed to load embedding model"):
                    EmbeddingGenerator()


class TestGetEmbeddingGenerator:
    """Test cases for get_embedding_generator function."""

    def test_get_embedding_generator(self):
        """Test get_embedding_generator returns an instance."""
        with patch('app.core.embeddings.SentenceTransformer'):
            with patch('app.core.embeddings.settings') as mock_settings:
                mock_settings.embedding_model = "test-model"
                mock_settings.embedding_dimension = 384

                # Reset singleton
                EmbeddingGenerator._instance = None
                EmbeddingGenerator._model = None

                gen = get_embedding_generator()

                assert isinstance(gen, EmbeddingGenerator)

    def test_get_embedding_generator_singleton(self):
        """Test that get_embedding_generator returns same instance."""
        with patch('app.core.embeddings.SentenceTransformer'):
            with patch('app.core.embeddings.settings') as mock_settings:
                mock_settings.embedding_model = "test-model"
                mock_settings.embedding_dimension = 384

                # Reset singleton
                EmbeddingGenerator._instance = None
                EmbeddingGenerator._model = None

                gen1 = get_embedding_generator()
                gen2 = get_embedding_generator()

                # Should be same instance
                assert gen1 is gen2


class TestEmbeddingEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def generator(self):
        """Create mocked generator."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.randn(1, 384)

        with patch('app.core.embeddings.SentenceTransformer') as mock_st:
            mock_st.return_value = mock_model

            EmbeddingGenerator._instance = None
            EmbeddingGenerator._model = None

            with patch('app.core.embeddings.settings') as mock_settings:
                mock_settings.embedding_model = "test"
                mock_settings.embedding_dimension = 384

                gen = EmbeddingGenerator()
                gen._model = mock_model
                return gen

    def test_encode_very_long_text(self, generator):
        """Test encoding very long text."""
        # Create very long text
        long_text = " ".join(["word"] * 10000)

        # Should handle without error
        embeddings = generator.encode(long_text)

        assert embeddings.shape[0] >= 1

    def test_encode_special_characters(self, generator):
        """Test encoding text with special characters."""
        text = "Test with émojis 😀 and spëcial çharacters!"

        # Should handle without error
        embeddings = generator.encode(text)

        assert embeddings.shape == (1, 384)

    def test_encode_unicode(self, generator):
        """Test encoding Unicode text."""
        text = "测试中文 тест на русском тест"

        # Should handle without error
        embeddings = generator.encode(text)

        assert embeddings.shape == (1, 384)

    def test_similarity_clipping(self, generator):
        """Test that similarity values are clipped to [0, 1]."""
        # Create embeddings that might produce values outside [0, 1]
        embedding1 = np.array([1.0] * 384)
        embedding2 = np.array([-1.0] * 384)

        similarity = generator.similarity(embedding1, embedding2)

        # Should be clipped to [0, 1]
        assert 0.0 <= similarity <= 1.0
