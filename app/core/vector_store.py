"""FAISS vector store for similarity search."""
import os
import pickle
import numpy as np
import faiss
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict

from app.config import settings


@dataclass
class VectorMetadata:
    """Metadata for a vector in the store."""

    source_id: str
    source_type: str  # article, youtube, submission
    chunk_index: int
    chunk_text: str
    language: str = "en"
    timestamp: Optional[str] = None  # For YouTube (MM:SS format)
    title: Optional[str] = None
    identifier: Optional[str] = None  # URL or video ID


class FAISSVectorStore:
    """FAISS-based vector store for similarity search."""

    def __init__(
        self,
        dimension: int,
        index_path: Optional[str] = None,
        metric: str = "cosine"
    ):
        """
        Initialize FAISS vector store.

        Args:
            dimension: Embedding dimension
            index_path: Path to save/load index
            metric: Distance metric (cosine or euclidean)
        """
        self.dimension = dimension
        self.index_path = index_path or settings.vector_store_path
        self.metric = metric

        # Create index directory
        Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize FAISS index
        if metric == "cosine":
            # Use Inner Product for cosine similarity (assuming normalized vectors)
            self.index = faiss.IndexFlatIP(dimension)
        else:
            # Use L2 distance
            self.index = faiss.IndexFlatL2(dimension)

        # Metadata storage (indexed by vector ID)
        self.metadata: Dict[int, VectorMetadata] = {}
        self.next_id = 0

        # Load existing index if available
        self._load()

    def add_vectors(
        self,
        embeddings: np.ndarray,
        metadata_list: List[VectorMetadata]
    ) -> List[int]:
        """
        Add vectors with metadata to the store.

        Args:
            embeddings: Numpy array of embeddings (N x dimension)
            metadata_list: List of metadata objects

        Returns:
            List of assigned vector IDs
        """
        if len(embeddings) != len(metadata_list):
            raise ValueError("Number of embeddings must match metadata list")

        # Ensure embeddings are float32
        embeddings = embeddings.astype(np.float32)

        # Normalize for cosine similarity
        if self.metric == "cosine":
            faiss.normalize_L2(embeddings)

        # Add to FAISS index
        start_id = self.next_id
        self.index.add(embeddings)

        # Store metadata
        vector_ids = []
        for i, meta in enumerate(metadata_list):
            vector_id = start_id + i
            self.metadata[vector_id] = meta
            vector_ids.append(vector_id)

        self.next_id += len(embeddings)

        return vector_ids

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        filter_fn: Optional[callable] = None
    ) -> List[Tuple[VectorMetadata, float]]:
        """
        Search for similar vectors.

        Args:
            query_embedding: Query embedding (1D array)
            k: Number of results to return
            filter_fn: Optional filter function for metadata

        Returns:
            List of (metadata, similarity_score) tuples
        """
        # Return empty results if index is empty
        if self.index.ntotal == 0:
            return []

        # Ensure query is 2D and float32
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        query_embedding = query_embedding.astype(np.float32)

        # Normalize for cosine similarity
        if self.metric == "cosine":
            faiss.normalize_L2(query_embedding)

        # Search
        # Request more results to account for filtering
        search_k = min(k * 3, self.index.ntotal) if filter_fn else min(k, self.index.ntotal)
        distances, indices = self.index.search(query_embedding, int(search_k))

        # Process results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # No more results
                break

            meta = self.metadata.get(idx)
            if meta is None:
                continue

            # Apply filter if provided
            if filter_fn and not filter_fn(meta):
                continue

            # Convert distance to similarity
            # For IP (cosine), distance is already similarity
            # For L2, convert: similarity = 1 / (1 + distance)
            if self.metric == "cosine":
                similarity = float(dist)
            else:
                similarity = 1.0 / (1.0 + float(dist))

            results.append((meta, similarity))

            # Stop if we have enough results
            if len(results) >= k:
                break

        return results

    def batch_search(
        self,
        query_embeddings: np.ndarray,
        k: int = 10
    ) -> List[List[Tuple[VectorMetadata, float]]]:
        """
        Search for multiple queries.

        Args:
            query_embeddings: Query embeddings (N x dimension)
            k: Number of results per query

        Returns:
            List of result lists
        """
        # Ensure float32
        query_embeddings = query_embeddings.astype(np.float32)

        # Normalize for cosine similarity
        if self.metric == "cosine":
            faiss.normalize_L2(query_embeddings)

        # Search
        distances, indices = self.index.search(query_embeddings, k)

        # Process results for each query
        all_results = []
        for query_distances, query_indices in zip(distances, indices):
            results = []
            for dist, idx in zip(query_distances, query_indices):
                if idx == -1:
                    break

                meta = self.metadata.get(idx)
                if meta is None:
                    continue

                # Convert distance to similarity
                if self.metric == "cosine":
                    similarity = float(dist)
                else:
                    similarity = 1.0 / (1.0 + float(dist))

                results.append((meta, similarity))

            all_results.append(results)

        return all_results

    def remove_by_source(self, source_id: str) -> int:
        """
        Remove all vectors for a specific source.

        Note: FAISS doesn't support efficient deletion, so we rebuild the index.

        Args:
            source_id: Source ID to remove

        Returns:
            Number of vectors removed
        """
        # Find vectors to keep
        ids_to_remove = [
            vid for vid, meta in self.metadata.items()
            if meta.source_id == source_id
        ]

        if not ids_to_remove:
            return 0

        # Rebuild index without removed vectors
        ids_to_keep = [
            vid for vid in self.metadata.keys()
            if vid not in ids_to_remove
        ]

        if not ids_to_keep:
            # All vectors removed, reset index
            self.index.reset()
            self.metadata.clear()
            self.next_id = 0
            return len(ids_to_remove)

        # Extract vectors to keep
        vectors_to_keep = []
        metadata_to_keep = []

        for vid in ids_to_keep:
            # Note: This is inefficient but FAISS doesn't provide direct access
            # In production, consider using FAISS with IDMap or IndexIVF
            pass

        # For MVP, just remove from metadata
        # (vectors stay in FAISS but won't be returned)
        for vid in ids_to_remove:
            del self.metadata[vid]

        return len(ids_to_remove)

    def get_stats(self) -> Dict:
        """Get store statistics."""
        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "metadata_count": len(self.metadata),
            "metric": self.metric
        }

    def save(self) -> None:
        """Save index and metadata to disk."""
        # Save FAISS index
        index_file = f"{self.index_path}/faiss.index"
        faiss.write_index(self.index, index_file)

        # Save metadata
        meta_file = f"{self.index_path}/metadata.pkl"
        with open(meta_file, 'wb') as f:
            pickle.dump({
                'metadata': self.metadata,
                'next_id': self.next_id
            }, f)

        print(f"Saved vector store to {self.index_path}")

    def _load(self) -> None:
        """Load index and metadata from disk."""
        index_file = f"{self.index_path}/faiss.index"
        meta_file = f"{self.index_path}/metadata.pkl"

        # Load FAISS index
        if os.path.exists(index_file):
            self.index = faiss.read_index(index_file)
            print(f"Loaded FAISS index from {index_file}")

        # Load metadata
        if os.path.exists(meta_file):
            with open(meta_file, 'rb') as f:
                data = pickle.load(f)
                self.metadata = data['metadata']
                self.next_id = data['next_id']
            print(f"Loaded metadata from {meta_file}")

    def clear(self) -> None:
        """Clear all vectors and metadata."""
        self.index.reset()
        self.metadata.clear()
        self.next_id = 0


# Global vector store instances
_article_store: Optional[FAISSVectorStore] = None
_youtube_store: Optional[FAISSVectorStore] = None


def get_article_store() -> FAISSVectorStore:
    """Get the global article vector store."""
    global _article_store
    if _article_store is None:
        store_path = f"{settings.vector_store_path}/articles"
        _article_store = FAISSVectorStore(
            dimension=settings.embedding_dimension,
            index_path=store_path,
            metric="cosine"
        )
    return _article_store


def get_youtube_store() -> FAISSVectorStore:
    """Get the global YouTube vector store."""
    global _youtube_store
    if _youtube_store is None:
        store_path = f"{settings.vector_store_path}/youtube"
        _youtube_store = FAISSVectorStore(
            dimension=settings.embedding_dimension,
            index_path=store_path,
            metric="cosine"
        )
    return _youtube_store
