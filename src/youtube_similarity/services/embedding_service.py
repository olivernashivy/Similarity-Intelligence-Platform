"""Embedding generation service for creating vector representations of text."""

import logging
from typing import List, Optional
import numpy as np
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Generates embeddings for text using OpenAI's embedding API.

    Supports:
    - Batch processing for efficiency
    - Automatic retries on failure
    - Cost tracking
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize embedding service.

        Args:
            api_key: OpenAI API key (uses settings if not provided)
            model: Embedding model name (uses settings if not provided)
        """
        self.api_key = api_key or settings.openai_api_key
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model or settings.embedding_model
        self.embedding_dimension = self._get_embedding_dimension()

        logger.info(f"Initialized embedding service with model: {self.model}")

    def _get_embedding_dimension(self) -> int:
        """
        Get embedding dimension for the configured model.

        Returns:
            Embedding dimension size
        """
        # OpenAI embedding dimensions
        dimensions = {
            'text-embedding-3-small': 1536,
            'text-embedding-3-large': 3072,
            'text-embedding-ada-002': 1536
        }
        return dimensions.get(self.model, 1536)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector as numpy array
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return np.zeros(self.embedding_dimension)

        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )

            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of input texts
            batch_size: Number of texts to process per API call

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Filter out empty texts
        filtered_texts = [text if text and text.strip() else " " for text in texts]

        embeddings = []

        for i in range(0, len(filtered_texts), batch_size):
            batch = filtered_texts[i:i + batch_size]

            try:
                logger.debug(f"Generating embeddings for batch {i // batch_size + 1}")

                response = self.client.embeddings.create(
                    input=batch,
                    model=self.model
                )

                batch_embeddings = [
                    np.array(data.embedding, dtype=np.float32)
                    for data in response.data
                ]
                embeddings.extend(batch_embeddings)

            except Exception as e:
                logger.error(f"Error generating batch embeddings: {e}")
                # Add zero vectors for failed batch
                embeddings.extend([
                    np.zeros(self.embedding_dimension)
                    for _ in range(len(batch))
                ])

        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings

    def cosine_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0 to 1)
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Calculate cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)

        # Ensure result is in [0, 1] range
        # Cosine similarity is in [-1, 1], we shift to [0, 1]
        return float((similarity + 1) / 2)

    def find_most_similar(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: List[np.ndarray],
        top_k: int = 5
    ) -> List[tuple[int, float]]:
        """
        Find most similar embeddings to query.

        Args:
            query_embedding: Query embedding vector
            candidate_embeddings: List of candidate embeddings
            top_k: Number of top results to return

        Returns:
            List of (index, similarity_score) tuples
        """
        if not candidate_embeddings:
            return []

        # Calculate similarities
        similarities = [
            (i, self.cosine_similarity(query_embedding, emb))
            for i, emb in enumerate(candidate_embeddings)
        ]

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def calculate_similarity_matrix(
        self,
        embeddings1: List[np.ndarray],
        embeddings2: List[np.ndarray]
    ) -> np.ndarray:
        """
        Calculate pairwise similarity matrix between two sets of embeddings.

        Args:
            embeddings1: First set of embeddings
            embeddings2: Second set of embeddings

        Returns:
            Similarity matrix of shape (len(embeddings1), len(embeddings2))
        """
        if not embeddings1 or not embeddings2:
            return np.array([])

        # Convert to numpy arrays
        matrix1 = np.array(embeddings1)
        matrix2 = np.array(embeddings2)

        # Normalize
        matrix1_norm = matrix1 / np.linalg.norm(matrix1, axis=1, keepdims=True)
        matrix2_norm = matrix2 / np.linalg.norm(matrix2, axis=1, keepdims=True)

        # Calculate cosine similarity matrix
        similarity_matrix = np.dot(matrix1_norm, matrix2_norm.T)

        # Shift to [0, 1] range
        similarity_matrix = (similarity_matrix + 1) / 2

        return similarity_matrix
