"""Transcript fetching service for retrieving YouTube video transcripts."""

import logging
from typing import List, Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    TooManyRequests
)

from ..config import settings
from ..models import TranscriptSegment

logger = logging.getLogger(__name__)


class TranscriptFetcherService:
    """
    Fetches transcripts from YouTube videos.

    Only fetches:
    - Publicly available transcripts
    - English language transcripts
    - Non-auto-generated captions (when possible)
    """

    def __init__(self):
        """Initialize transcript fetcher service."""
        self.max_transcript_length = settings.max_transcript_length

    def fetch_transcript(
        self,
        video_id: str,
        prefer_manual: bool = True
    ) -> Optional[List[TranscriptSegment]]:
        """
        Fetch transcript for a YouTube video.

        Args:
            video_id: YouTube video ID
            prefer_manual: Prefer manually created captions over auto-generated

        Returns:
            List of transcript segments or None if unavailable
        """
        try:
            logger.info(f"Fetching transcript for video: {video_id}")

            # Get transcript list
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try to get English transcript
            transcript = None

            try:
                # First, try manual captions
                if prefer_manual:
                    try:
                        transcript = transcript_list.find_manually_created_transcript(['en'])
                        logger.info(f"Found manual English transcript for {video_id}")
                    except NoTranscriptFound:
                        logger.debug("No manual transcript found, trying auto-generated")

                # Fall back to auto-generated if manual not available
                if transcript is None:
                    transcript = transcript_list.find_generated_transcript(['en'])
                    logger.info(f"Using auto-generated English transcript for {video_id}")

            except NoTranscriptFound:
                logger.warning(f"No English transcript found for video {video_id}")
                return None

            # Fetch the actual transcript data
            transcript_data = transcript.fetch()

            # Convert to our model
            segments = self._convert_to_segments(transcript_data, video_id)

            # Validate transcript quality
            if not self._is_transcript_valid(segments):
                logger.warning(f"Transcript quality too low for video {video_id}")
                return None

            logger.info(f"Successfully fetched {len(segments)} transcript segments")
            return segments

        except TranscriptsDisabled:
            logger.warning(f"Transcripts disabled for video {video_id}")
            return None
        except VideoUnavailable:
            logger.warning(f"Video {video_id} is unavailable")
            return None
        except TooManyRequests:
            logger.error(f"Rate limit exceeded when fetching transcript for {video_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching transcript for {video_id}: {e}")
            return None

    def _convert_to_segments(
        self,
        transcript_data: List[dict],
        video_id: str
    ) -> List[TranscriptSegment]:
        """
        Convert raw transcript data to TranscriptSegment models.

        Args:
            transcript_data: Raw transcript data from API
            video_id: Video ID

        Returns:
            List of transcript segments
        """
        segments = []

        for item in transcript_data:
            try:
                segment = TranscriptSegment(
                    text=item['text'],
                    start=float(item['start']),
                    duration=float(item['duration'])
                )
                segments.append(segment)
            except (KeyError, ValueError) as e:
                logger.warning(f"Error parsing transcript segment: {e}")
                continue

        return segments

    def _is_transcript_valid(self, segments: List[TranscriptSegment]) -> bool:
        """
        Validate transcript quality.

        Args:
            segments: List of transcript segments

        Returns:
            True if transcript is of acceptable quality
        """
        if not segments:
            return False

        # Calculate total text length
        total_text = ' '.join(segment.text for segment in segments)
        total_length = len(total_text)

        # Check minimum length
        if total_length < 100:
            logger.debug("Transcript too short")
            return False

        # Check maximum length
        if total_length > self.max_transcript_length:
            logger.debug(f"Transcript too long ({total_length} > {self.max_transcript_length})")
            return False

        # Check for extremely repetitive content (spam indicator)
        unique_words = len(set(total_text.lower().split()))
        total_words = len(total_text.split())

        if total_words > 0:
            uniqueness_ratio = unique_words / total_words
            if uniqueness_ratio < 0.1:  # Less than 10% unique words
                logger.debug("Transcript appears to be spam or extremely repetitive")
                return False

        # Check segment count
        if len(segments) < 3:
            logger.debug("Too few transcript segments")
            return False

        return True

    def get_transcript_text(self, segments: List[TranscriptSegment]) -> str:
        """
        Extract full text from transcript segments.

        Args:
            segments: List of transcript segments

        Returns:
            Combined transcript text
        """
        return ' '.join(segment.text for segment in segments)

    def get_transcript_duration(self, segments: List[TranscriptSegment]) -> float:
        """
        Calculate total duration of transcript.

        Args:
            segments: List of transcript segments

        Returns:
            Total duration in seconds
        """
        if not segments:
            return 0.0

        last_segment = segments[-1]
        return last_segment.start + last_segment.duration

    def filter_by_timerange(
        self,
        segments: List[TranscriptSegment],
        start_time: float,
        end_time: float
    ) -> List[TranscriptSegment]:
        """
        Filter segments by time range.

        Args:
            segments: List of transcript segments
            start_time: Start time in seconds
            end_time: End time in seconds

        Returns:
            Filtered segments
        """
        return [
            segment for segment in segments
            if segment.start >= start_time and segment.end <= end_time
        ]
