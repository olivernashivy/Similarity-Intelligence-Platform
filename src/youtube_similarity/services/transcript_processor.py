"""Transcript processing service for chunking and normalizing transcripts."""

import logging
from typing import List
from ..config import settings
from ..models import TranscriptSegment, TranscriptChunk
from ..utils.text_utils import normalize_text, clean_transcript_text

logger = logging.getLogger(__name__)


class TranscriptProcessor:
    """
    Processes and chunks transcripts for embedding generation.

    Handles:
    - Text normalization (lowercase, remove fillers)
    - Chunking by word count with timestamp preservation
    - Metadata attachment
    """

    def __init__(
        self,
        chunk_size_words: int = None,
        chunk_overlap_words: int = 10
    ):
        """
        Initialize transcript processor.

        Args:
            chunk_size_words: Number of words per chunk (uses settings if not provided)
            chunk_overlap_words: Number of overlapping words between chunks
        """
        self.chunk_size_words = chunk_size_words or settings.chunk_size_words
        self.chunk_overlap_words = min(chunk_overlap_words, self.chunk_size_words // 2)

    def process_transcript(
        self,
        segments: List[TranscriptSegment],
        video_id: str
    ) -> List[TranscriptChunk]:
        """
        Process transcript segments into chunks ready for embedding.

        Args:
            segments: List of transcript segments
            video_id: Associated video ID

        Returns:
            List of processed chunks
        """
        if not segments:
            logger.warning(f"No segments to process for video {video_id}")
            return []

        logger.info(f"Processing {len(segments)} transcript segments for video {video_id}")

        # First, merge segments into continuous text while tracking timestamps
        merged_text, timestamp_map = self._merge_segments(segments)

        # Normalize the text
        normalized_text = clean_transcript_text(merged_text)

        # Split into word-based chunks
        chunks = self._create_chunks(normalized_text, timestamp_map, video_id)

        logger.info(f"Created {len(chunks)} chunks from transcript")
        return chunks

    def _merge_segments(
        self,
        segments: List[TranscriptSegment]
    ) -> tuple[str, List[dict]]:
        """
        Merge transcript segments into continuous text with timestamp mapping.

        Args:
            segments: List of transcript segments

        Returns:
            Tuple of (merged_text, timestamp_map)
            timestamp_map contains word positions and their timestamps
        """
        words = []
        timestamp_map = []
        word_position = 0

        for segment in segments:
            segment_words = segment.text.split()

            for word in segment_words:
                words.append(word)
                timestamp_map.append({
                    'word_position': word_position,
                    'start': segment.start,
                    'end': segment.end
                })
                word_position += 1

        merged_text = ' '.join(words)
        return merged_text, timestamp_map

    def _create_chunks(
        self,
        text: str,
        timestamp_map: List[dict],
        video_id: str
    ) -> List[TranscriptChunk]:
        """
        Create overlapping chunks from text with timestamp preservation.

        Args:
            text: Normalized text
            timestamp_map: Mapping of word positions to timestamps
            video_id: Video ID

        Returns:
            List of transcript chunks
        """
        words = text.split()
        chunks = []
        chunk_index = 0

        if len(words) <= self.chunk_size_words:
            # Single chunk
            if timestamp_map:
                start_time = timestamp_map[0]['start']
                end_time = timestamp_map[-1]['end']
            else:
                start_time = end_time = 0.0

            chunk = TranscriptChunk(
                text=text,
                start=start_time,
                end=end_time,
                video_id=video_id,
                chunk_index=chunk_index
            )
            return [chunk]

        # Create overlapping chunks
        step = self.chunk_size_words - self.chunk_overlap_words

        for i in range(0, len(words), step):
            chunk_words = words[i:i + self.chunk_size_words]

            # Skip if chunk is too small (less than half the target size)
            if len(chunk_words) < self.chunk_size_words // 2:
                continue

            chunk_text = ' '.join(chunk_words)

            # Get timestamps for this chunk
            start_word_pos = i
            end_word_pos = min(i + len(chunk_words) - 1, len(timestamp_map) - 1)

            if start_word_pos < len(timestamp_map) and end_word_pos < len(timestamp_map):
                start_time = timestamp_map[start_word_pos]['start']
                end_time = timestamp_map[end_word_pos]['end']
            else:
                # Fallback if timestamp map is incomplete
                start_time = end_time = 0.0

            chunk = TranscriptChunk(
                text=chunk_text,
                start=start_time,
                end=end_time,
                video_id=video_id,
                chunk_index=chunk_index
            )
            chunks.append(chunk)
            chunk_index += 1

        return chunks

    def process_article(self, title: str, content: str) -> List[str]:
        """
        Process article into chunks for embedding.

        Args:
            title: Article title
            content: Article content

        Returns:
            List of article chunks
        """
        # Combine title and content with title weighted
        full_text = f"{title}. {title}. {content}"  # Title repeated for emphasis

        # Normalize
        normalized = normalize_text(full_text, remove_fillers=False)

        # Chunk by words
        words = normalized.split()
        chunks = []

        if len(words) <= self.chunk_size_words:
            return [normalized]

        step = self.chunk_size_words - self.chunk_overlap_words

        for i in range(0, len(words), step):
            chunk_words = words[i:i + self.chunk_size_words]

            # Skip if chunk is too small
            if len(chunk_words) < self.chunk_size_words // 2:
                continue

            chunks.append(' '.join(chunk_words))

        logger.info(f"Created {len(chunks)} chunks from article")
        return chunks

    def get_snippet_from_chunks(
        self,
        chunks: List[TranscriptChunk],
        max_length: int = 300
    ) -> str:
        """
        Extract a snippet from transcript chunks.

        Args:
            chunks: List of transcript chunks
            max_length: Maximum snippet length

        Returns:
            Snippet text
        """
        if not chunks:
            return ""

        # Combine chunk texts
        combined = ' '.join(chunk.text for chunk in chunks)

        # Truncate to max length
        if len(combined) <= max_length:
            return combined

        # Find last space before max_length
        snippet = combined[:max_length].rsplit(' ', 1)[0]
        return f"{snippet}..."
