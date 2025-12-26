"""Text processing utilities for transcript and article analysis."""

import re
from typing import List, Set


# Common filler words to remove from transcripts
FILLER_WORDS: Set[str] = {
    "um", "uh", "umm", "uhh", "hmm", "mhmm", "yeah", "yep", "nope",
    "like", "you know", "i mean", "sort of", "kind of", "basically",
    "actually", "literally", "seriously", "honestly", "obviously"
}


def normalize_text(text: str, remove_fillers: bool = True) -> str:
    """
    Normalize text for embedding and comparison.

    Args:
        text: Input text to normalize
        remove_fillers: Whether to remove filler words

    Returns:
        Normalized text
    """
    # Convert to lowercase
    text = text.lower()

    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?-]', ' ', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Remove filler words if requested
    if remove_fillers:
        words = text.split()
        words = [w for w in words if w not in FILLER_WORDS]
        text = ' '.join(words)

    return text


def chunk_text_by_words(
    text: str,
    chunk_size: int = 50,
    overlap: int = 10
) -> List[str]:
    """
    Split text into overlapping chunks based on word count.

    Args:
        text: Text to chunk
        chunk_size: Number of words per chunk
        overlap: Number of overlapping words between chunks

    Returns:
        List of text chunks
    """
    words = text.split()
    chunks = []

    if len(words) <= chunk_size:
        return [text]

    step = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk_words = words[i:i + chunk_size]
        if len(chunk_words) >= overlap:  # Avoid tiny chunks at the end
            chunks.append(' '.join(chunk_words))

    return chunks


def truncate_text(text: str, max_length: int = 300) -> str:
    """
    Truncate text to maximum length, breaking at word boundaries.

    Args:
        text: Text to truncate
        max_length: Maximum length in characters

    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text

    # Find the last space before max_length
    truncated = text[:max_length].rsplit(' ', 1)[0]
    return f"{truncated}..."


def extract_sentences(text: str, max_sentences: int = 3) -> str:
    """
    Extract the first N sentences from text.

    Args:
        text: Input text
        max_sentences: Maximum number of sentences to extract

    Returns:
        First N sentences
    """
    # Simple sentence splitting (could be improved with NLTK)
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return '. '.join(sentences[:max_sentences]) + '.'


def calculate_word_count(text: str) -> int:
    """
    Calculate word count in text.

    Args:
        text: Input text

    Returns:
        Number of words
    """
    return len(text.split())


def clean_transcript_text(text: str) -> str:
    """
    Clean transcript text by removing common transcript artifacts.

    Args:
        text: Raw transcript text

    Returns:
        Cleaned text
    """
    # Remove timestamps if present [00:00:00]
    text = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', text)

    # Remove speaker labels if present (e.g., "Speaker 1:")
    text = re.sub(r'Speaker \d+:', '', text)

    # Remove music/sound descriptions [Music], [Applause]
    text = re.sub(r'\[[A-Za-z\s]+\]', '', text)

    # Normalize
    return normalize_text(text, remove_fillers=True)
