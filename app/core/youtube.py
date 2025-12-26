"""YouTube transcript fetching and processing."""
import re
import isodate
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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

        # Initialize YouTube API client if API key is available
        self.youtube_client = None
        if settings.youtube_api_key:
            try:
                self.youtube_client = build('youtube', 'v3', developerKey=settings.youtube_api_key)
            except Exception as e:
                print(f"Failed to initialize YouTube API client: {e}")
                self.youtube_client = None

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
            # Remove filler words before processing
            cleaned_text = self._remove_filler_words(segment.text)
            words = cleaned_text.split()
            word_count = len(words)

            if chunk_start_timestamp is None:
                chunk_start_timestamp = segment.timestamp

            current_chunk.append(cleaned_text)
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

    def _remove_filler_words(self, text: str) -> str:
        """
        Remove filler words from transcript text.

        Args:
            text: Input text

        Returns:
            Text with filler words removed
        """
        # Common filler words in spoken content
        filler_words = {
            'um', 'umm', 'uh', 'uhh', 'hmm', 'mhmm',
            'like', 'you know', 'i mean',
            'sort of', 'kind of',
            'basically', 'actually', 'literally',
            'seriously', 'honestly', 'obviously'
        }

        # Normalize and split
        words = text.lower().split()

        # Filter out filler words
        filtered_words = [
            word for word in words
            if word not in filler_words
        ]

        return ' '.join(filtered_words)

    def search_videos_by_keywords(
        self,
        keywords: List[str],
        max_results: int = 5
    ) -> List[str]:
        """
        Search for YouTube videos by keywords using YouTube Data API.

        Args:
            keywords: Search keywords
            max_results: Maximum results

        Returns:
            List of video IDs
        """
        if not self.youtube_client:
            print("YouTube API client not initialized. Returning empty list.")
            return []

        try:
            # Build search query from keywords
            query = ' '.join(keywords[:5])  # Use top 5 keywords

            # Search for videos
            search_response = self.youtube_client.search().list(
                q=query,
                part='id,snippet',
                type='video',
                videoCaption='closedCaption',  # Only videos with captions
                relevanceLanguage='en',  # English language preference
                maxResults=max_results * 2,  # Request more to filter
                order='relevance',
                videoDuration='short',  # Prefer shorter videos
                safeSearch='moderate'
            ).execute()

            # Extract video IDs and titles for filtering
            video_items = [
                {
                    'id': item['id']['videoId'],
                    'title': item['snippet']['title']
                }
                for item in search_response.get('items', [])
                if item['id'].get('kind') == 'youtube#video'
            ]

            # Filter out generic/viral content
            filtered_items = self._filter_generic_content(video_items)

            # Get IDs for duration filtering
            video_ids = [item['id'] for item in filtered_items]

            # Filter by duration
            filtered_ids = self._filter_videos_by_duration(video_ids)

            return filtered_ids[:max_results]

        except HttpError as e:
            print(f"YouTube API error: {e}")
            return []
        except Exception as e:
            print(f"Error searching YouTube videos: {e}")
            return []

    def _filter_generic_content(self, video_items: List[Dict]) -> List[Dict]:
        """
        Filter out generic/viral content that is not contextually relevant.

        Args:
            video_items: List of dicts with 'id' and 'title'

        Returns:
            Filtered list of video items
        """
        # Patterns indicating generic/viral content
        generic_patterns = [
            'compilation', 'compilations',
            'funny moments', 'best moments',
            'top 10', 'top 5', 'top ten', 'top five',
            'fails', 'fail compilation',
            'challenge', 'challenges',
            'prank', 'pranks',
            'reaction', 'reacts to',
            'unboxing',
            'vlog', 'daily vlog',
            'try not to',
            'vs', 'versus',
            'clickbait',
            'you won\'t believe'
        ]

        filtered = []
        for item in video_items:
            title_lower = item['title'].lower()

            # Check if title contains generic patterns
            is_generic = any(pattern in title_lower for pattern in generic_patterns)

            if not is_generic:
                filtered.append(item)
            else:
                print(f"Filtering out generic content: {item['title']}")

        return filtered

    def _filter_videos_by_duration(self, video_ids: List[str]) -> List[str]:
        """
        Filter videos by maximum duration.

        Args:
            video_ids: List of video IDs

        Returns:
            Filtered list of video IDs
        """
        if not self.youtube_client or not video_ids:
            return []

        try:
            # Get video details
            videos_response = self.youtube_client.videos().list(
                part='contentDetails',
                id=','.join(video_ids)
            ).execute()

            filtered_ids = []
            for item in videos_response.get('items', []):
                try:
                    # Parse ISO 8601 duration
                    duration_iso = item['contentDetails']['duration']
                    duration = isodate.parse_duration(duration_iso)
                    duration_minutes = duration.total_seconds() / 60

                    # Check if within limit
                    if duration_minutes <= self.max_duration_minutes and duration_minutes >= 0.5:
                        filtered_ids.append(item['id'])

                except Exception as e:
                    print(f"Error parsing duration for video {item.get('id')}: {e}")
                    continue

            return filtered_ids

        except HttpError as e:
            print(f"YouTube API error filtering videos: {e}")
            return video_ids  # Return original list if filtering fails

    def get_video_metadata(self, video_id: str) -> Dict:
        """
        Get video metadata using YouTube Data API.

        Args:
            video_id: YouTube video ID

        Returns:
            Metadata dict
        """
        if not self.youtube_client:
            # Fallback if API not available
            return {
                "video_id": video_id,
                "title": f"Video {video_id}",
                "channel": "Unknown",
                "duration_seconds": 0,
                "url": f"https://www.youtube.com/watch?v={video_id}"
            }

        try:
            # Get video details from YouTube API
            video_response = self.youtube_client.videos().list(
                part='snippet,contentDetails',
                id=video_id
            ).execute()

            if not video_response.get('items'):
                # Video not found
                return {
                    "video_id": video_id,
                    "title": "Unknown",
                    "channel": "Unknown",
                    "duration_seconds": 0,
                    "url": f"https://www.youtube.com/watch?v={video_id}"
                }

            item = video_response['items'][0]
            snippet = item['snippet']
            content_details = item['contentDetails']

            # Parse duration
            duration_iso = content_details['duration']
            duration = isodate.parse_duration(duration_iso)
            duration_seconds = int(duration.total_seconds())

            return {
                "video_id": video_id,
                "title": snippet['title'],
                "channel": snippet['channelTitle'],
                "duration_seconds": duration_seconds,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "published_at": snippet.get('publishedAt'),
                "description": snippet.get('description', '')[:300]  # Truncate description
            }

        except HttpError as e:
            print(f"YouTube API error getting metadata for {video_id}: {e}")
            return {
                "video_id": video_id,
                "title": "Error fetching metadata",
                "channel": "Unknown",
                "duration_seconds": 0,
                "url": f"https://www.youtube.com/watch?v={video_id}"
            }
        except Exception as e:
            print(f"Error getting metadata for {video_id}: {e}")
            return {
                "video_id": video_id,
                "title": "Error fetching metadata",
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

    IMPORTANT: Transcripts are fetched temporarily for similarity analysis only.
    Full transcripts are NOT stored long-term - only embeddings and short chunks
    (40-60 words) are cached for performance. This complies with privacy requirements.

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
