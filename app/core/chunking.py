"""Text chunking utilities."""
import re
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""

    text: str
    start_index: int
    end_index: int
    chunk_index: int
    word_count: int


class TextChunker:
    """Handles text chunking with overlap."""

    def __init__(
        self,
        min_words: int = 40,
        max_words: int = 60,
        overlap_words: int = 10
    ):
        """
        Initialize chunker.

        Args:
            min_words: Minimum words per chunk
            max_words: Maximum words per chunk
            overlap_words: Number of overlapping words between chunks
        """
        self.min_words = min_words
        self.max_words = max_words
        self.overlap_words = overlap_words

    def normalize_text(self, text: str) -> str:
        """
        Normalize text before chunking.

        - Convert to lowercase
        - Remove excessive whitespace
        - Normalize punctuation spacing
        """
        # Convert to lowercase
        text = text.lower()

        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)

        # Normalize punctuation spacing
        text = re.sub(r'\s*([.,!?;:])\s*', r'\1 ', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def chunk_text(self, text: str, normalize: bool = True) -> List[TextChunk]:
        """
        Split text into overlapping chunks.

        Args:
            text: Input text to chunk
            normalize: Whether to normalize text first

        Returns:
            List of TextChunk objects
        """
        if normalize:
            text = self.normalize_text(text)

        # Split into words while preserving positions
        words = text.split()

        if len(words) < self.min_words:
            # If text is too short, return as single chunk
            return [
                TextChunk(
                    text=text,
                    start_index=0,
                    end_index=len(text),
                    chunk_index=0,
                    word_count=len(words)
                )
            ]

        chunks = []
        chunk_index = 0
        start_word_idx = 0

        while start_word_idx < len(words):
            # Calculate end word index
            end_word_idx = min(start_word_idx + self.max_words, len(words))

            # Extract chunk words
            chunk_words = words[start_word_idx:end_word_idx]
            chunk_text = ' '.join(chunk_words)

            # Calculate character positions (approximate)
            start_char = len(' '.join(words[:start_word_idx]))
            if start_word_idx > 0:
                start_char += 1  # Account for space
            end_char = start_char + len(chunk_text)

            chunks.append(
                TextChunk(
                    text=chunk_text,
                    start_index=start_char,
                    end_index=end_char,
                    chunk_index=chunk_index,
                    word_count=len(chunk_words)
                )
            )

            chunk_index += 1

            # Move to next chunk with overlap
            if end_word_idx >= len(words):
                break

            start_word_idx += (self.max_words - self.overlap_words)

        return chunks

    def chunk_with_sentences(self, text: str, normalize: bool = True) -> List[TextChunk]:
        """
        Chunk text respecting sentence boundaries (future enhancement).

        Args:
            text: Input text
            normalize: Whether to normalize

        Returns:
            List of TextChunk objects
        """
        # For MVP, fall back to word-based chunking
        # Future: Use NLTK or spaCy for sentence boundary detection
        return self.chunk_text(text, normalize=normalize)


def extract_keywords(text: str, top_k: int = 10) -> List[str]:
    """
    Extract key terms from text for search.

    Args:
        text: Input text
        top_k: Number of keywords to extract

    Returns:
        List of keywords
    """
    # Simple keyword extraction (TF-IDF would be better)
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
        'those', 'it', 'its', 'they', 'them', 'their'
    }

    # Tokenize and filter
    words = re.findall(r'\b\w+\b', text.lower())
    words = [w for w in words if len(w) > 3 and w not in stop_words]

    # Count frequencies
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1

    # Sort by frequency and return top-k
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:top_k]]
