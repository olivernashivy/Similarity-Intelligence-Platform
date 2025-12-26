"""Embedding generation using Sentence Transformers."""
import numpy as np
from typing import List, Union
from sentence_transformers import SentenceTransformer
from functools import lru_cache

from app.config import settings


class EmbeddingGenerator:
    """Generates embeddings for text using Sentence Transformers."""

    _instance = None
    _model = None

    def __new__(cls):
        """Singleton pattern to avoid loading model multiple times."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the embedding model."""
        if self._model is None:
            self._load_model()

    def _load_model(self):
        """Load the sentence transformer model."""
        try:
            self._model = SentenceTransformer(settings.embedding_model)
            print(f"Loaded embedding model: {settings.embedding_model}")
        except Exception as e:
            raise RuntimeError(f"Failed to load embedding model: {e}")

    @property
    def model(self) -> SentenceTransformer:
        """Get the loaded model."""
        if self._model is None:
            self._load_model()
        return self._model

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return settings.embedding_dimension

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for text(s).

        Args:
            texts: Single text or list of texts
            batch_size: Batch size for encoding
            normalize: Whether to normalize embeddings (L2 norm)

        Returns:
            Numpy array of embeddings
        """
        # Ensure texts is a list
        if isinstance(texts, str):
            texts = [texts]

        # Generate embeddings
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=normalize
        )

        return embeddings

    def encode_single(self, text: str, normalize: bool = True) -> np.ndarray:
        """
        Encode a single text.

        Args:
            text: Input text
            normalize: Whether to normalize

        Returns:
            1D numpy array
        """
        embeddings = self.encode([text], normalize=normalize)
        return embeddings[0]

    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Similarity score (0-1)
        """
        # Cosine similarity (since embeddings are normalized)
        similarity = np.dot(embedding1, embedding2)
        return float(np.clip(similarity, 0.0, 1.0))

    def batch_similarity(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Calculate similarity between query and multiple candidates.

        Args:
            query_embedding: Query embedding (1D array)
            candidate_embeddings: Candidate embeddings (2D array)

        Returns:
            Array of similarity scores
        """
        # Matrix multiplication for batch cosine similarity
        similarities = np.dot(candidate_embeddings, query_embedding)
        return np.clip(similarities, 0.0, 1.0)


# Global instance
embedding_generator = EmbeddingGenerator()


def get_embedding_generator() -> EmbeddingGenerator:
    """Get the global embedding generator instance."""
    return embedding_generator
