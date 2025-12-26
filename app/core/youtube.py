"""YouTube transcript fetching and processing."""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

from app.config import settings
from app.core.chunking import extract_keywords


@dataclass
class TranscriptSegment:
    """YouTube transcript segment with timestamp."""

    text: str
    start_time: float  # Seconds
    duration: float
    timestamp: str  # Formatted MM:SS


class YouTubeTranscriptFetcher:
    """Fetches and processes YouTube transcripts."""

    def __init__(self, max_videos: int = 5, max_duration_minutes: int = 30):
        """
        Initialize YouTube transcript fetcher.

        Args:
            max_videos: Maximum number of videos to process
            max_duration_minutes: Maximum video duration to consider
        """
        self.max_videos = max_videos
        self.max_duration_minutes = max_duration_minutes

    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from YouTube URL.

        Args:
            url: YouTube URL

        Returns:
            Video ID or None
        """
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]+)',
            r'youtube\.com\/embed\/([a-zA-Z0-9_-]+)',
            r'youtube\.com\/v\/([a-zA-Z0-9_-]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # Check if it's already just an ID
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url

        return None

    def fetch_transcript(
        self,
        video_id: str,
        languages: List[str] = ['en']
    ) -> Optional[List[Dict]]:
        """
        Fetch transcript for a video.

        Args:
            video_id: YouTube video ID
            languages: Preferred languages (e.g., ['en', 'en-US'])

        Returns:
            List of transcript entries or None if not available
        """
        try:
            # Fetch transcript
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try to get manually created transcript first
            try:
                transcript = transcript_list.find_manually_created_transcript(languages)
            except:
                # Fall back to auto-generated
                transcript = transcript_list.find_generated_transcript(languages)

            # Fetch the actual transcript data
            return transcript.fetch()

        except (TranscriptsDisabled, NoTranscriptFound) as e:
            print(f"No transcript available for video {video_id}: {e}")
            return None
        except Exception as e:
            print(f"Error fetching transcript for {video_id}: {e}")
            return None

    def process_transcript(
        self,
        transcript_data: List[Dict]
    ) -> List[TranscriptSegment]:
        """
        Process raw transcript data into segments.

        Args:
            transcript_data: Raw transcript from API

        Returns:
            List of transcript segments
        """
        segments = []

        for entry in transcript_data:
            text = entry.get('text', '').strip()
            start = entry.get('start', 0.0)
            duration = entry.get('duration', 0.0)

            if not text:
                continue

            # Format timestamp
            timestamp = self._format_timestamp(start)

            segments.append(
                TranscriptSegment(
                    text=text,
                    start_time=start,
                    duration=duration,
                    timestamp=timestamp
                )
            )

        return segments

    def chunk_transcript(
        self,
        segments: List[TranscriptSegment],
        target_words: int = 50
    ) -> List[Tuple[str, str]]:
        """
        Chunk transcript segments into larger chunks.

        Args:
            segments: List of transcript segments
            target_words: Target words per chunk

        Returns:
            List of (chunk_text, timestamp) tuples
        """
        chunks = []
        current_chunk = []
        current_word_count = 0
        chunk_start_timestamp = None

        for segment in segments:
            words = segment.text.split()
            word_count = len(words)

            if chunk_start_timestamp is None:
                chunk_start_timestamp = segment.timestamp

            current_chunk.append(segment.text)
            current_word_count += word_count

            # Create chunk when reaching target size
            if current_word_count >= target_words:
                chunk_text = ' '.join(current_chunk)
                chunks.append((chunk_text, chunk_start_timestamp))

                # Reset for next chunk
                current_chunk = []
                current_word_count = 0
                chunk_start_timestamp = None

        # Add remaining chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append((chunk_text, chunk_start_timestamp or "00:00"))

        return chunks

    def search_videos_by_keywords(
        self,
        keywords: List[str],
        max_results: int = 5
    ) -> List[str]:
        """
        Search for YouTube videos by keywords.

        Note: This is a simplified version. In production, use YouTube Data API.

        Args:
            keywords: Search keywords
            max_results: Maximum results

        Returns:
            List of video IDs
        """
        # For MVP, return empty list
        # In production, integrate with YouTube Data API:
        # 1. Build search query from keywords
        # 2. Use youtube.search().list() with relevanceLanguage='en'
        # 3. Filter by duration < max_duration_minutes
        # 4. Return top video IDs

        print(f"YouTube search not implemented in MVP. Keywords: {keywords}")
        return []

    def get_video_metadata(self, video_id: str) -> Dict:
        """
        Get video metadata.

        Note: Simplified for MVP. Use YouTube Data API in production.

        Args:
            video_id: YouTube video ID

        Returns:
            Metadata dict
        """
        # In production, use YouTube Data API
        return {
            "video_id": video_id,
            "title": f"Video {video_id}",
            "channel": "Unknown",
            "duration_seconds": 0,
            "url": f"https://www.youtube.com/watch?v={video_id}"
        }

    def _format_timestamp(self, seconds: float) -> str:
        """
        Format seconds to MM:SS.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"


def search_and_fetch_transcripts(
    article_text: str,
    max_videos: int = None
) -> List[Dict]:
    """
    Search for relevant YouTube videos and fetch their transcripts.

    Args:
        article_text: Article text to extract keywords from
        max_videos: Maximum videos to fetch

    Returns:
        List of video data with transcripts
    """
    max_videos = max_videos or settings.max_youtube_videos
    fetcher = YouTubeTranscriptFetcher(max_videos=max_videos)

    # Extract keywords
    keywords = extract_keywords(article_text, top_k=10)

    # Search for videos
    video_ids = fetcher.search_videos_by_keywords(keywords, max_results=max_videos)

    # Fetch transcripts
    results = []
    for video_id in video_ids[:max_videos]:
        # Get metadata
        metadata = fetcher.get_video_metadata(video_id)

        # Check duration limit
        duration_minutes = metadata.get('duration_seconds', 0) / 60
        if duration_minutes > fetcher.max_duration_minutes:
            continue

        # Fetch transcript
        transcript_data = fetcher.fetch_transcript(video_id)
        if not transcript_data:
            continue

        # Process transcript
        segments = fetcher.process_transcript(transcript_data)
        chunks = fetcher.chunk_transcript(segments, target_words=50)

        results.append({
            'video_id': video_id,
            'metadata': metadata,
            'segments': segments,
            'chunks': chunks
        })

    return results
