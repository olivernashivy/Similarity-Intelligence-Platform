"""YouTube video discovery service for finding relevant videos based on keywords."""

import logging
from typing import List, Optional
from datetime import timedelta
import isodate
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config import settings
from ..models import VideoMetadata

logger = logging.getLogger(__name__)


class VideoDiscoveryService:
    """
    Discovers relevant YouTube videos based on search queries.

    Filters videos by:
    - Language (English only)
    - Duration (max duration limit)
    - Relevance to search terms
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize video discovery service.

        Args:
            api_key: YouTube Data API key (uses settings if not provided)
        """
        self.api_key = api_key or settings.youtube_api_key
        if not self.api_key:
            raise ValueError("YouTube API key is required")

        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        self.max_duration_seconds = settings.max_video_duration_seconds
        self.max_results = settings.max_videos_per_check

    def search_videos(
        self,
        query: str,
        max_results: Optional[int] = None
    ) -> List[VideoMetadata]:
        """
        Search for relevant YouTube videos.

        Args:
            query: Search query string
            max_results: Maximum number of results (uses settings if not provided)

        Returns:
            List of video metadata
        """
        max_results = max_results or self.max_results

        try:
            logger.info(f"Searching YouTube for: '{query}' (max results: {max_results})")

            # Search for videos
            search_response = self.youtube.search().list(
                q=query,
                part='id,snippet',
                type='video',
                videoCaption='closedCaption',  # Only videos with captions
                relevanceLanguage='en',  # English language preference
                maxResults=min(max_results * 2, 50),  # Request more to filter
                order='relevance',
                videoDuration='short',  # Short videos (< 4 min) - will filter further
                safeSearch='moderate'
            ).execute()

            # Extract video IDs
            video_ids = [
                item['id']['videoId']
                for item in search_response.get('items', [])
            ]

            if not video_ids:
                logger.warning(f"No videos found for query: '{query}'")
                return []

            # Get detailed video information
            videos = self._get_video_details(video_ids)

            # Filter and limit
            filtered_videos = self._filter_videos(videos)
            result = filtered_videos[:max_results]

            logger.info(f"Found {len(result)} relevant videos after filtering")
            return result

        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error searching videos: {e}")
            raise

    def _get_video_details(self, video_ids: List[str]) -> List[VideoMetadata]:
        """
        Get detailed information for videos.

        Args:
            video_ids: List of video IDs

        Returns:
            List of video metadata
        """
        try:
            # Request video details
            videos_response = self.youtube.videos().list(
                part='snippet,contentDetails',
                id=','.join(video_ids)
            ).execute()

            videos = []
            for item in videos_response.get('items', []):
                try:
                    # Parse duration
                    duration_iso = item['contentDetails']['duration']
                    duration = isodate.parse_duration(duration_iso)
                    duration_seconds = int(duration.total_seconds())

                    # Extract metadata
                    snippet = item['snippet']
                    video_metadata = VideoMetadata(
                        video_id=item['id'],
                        title=snippet['title'],
                        channel_name=snippet['channelTitle'],
                        duration_seconds=duration_seconds,
                        url=f"https://www.youtube.com/watch?v={item['id']}"
                    )
                    videos.append(video_metadata)

                except (KeyError, ValueError) as e:
                    logger.warning(f"Error parsing video {item.get('id')}: {e}")
                    continue

            return videos

        except HttpError as e:
            logger.error(f"Error fetching video details: {e}")
            raise

    def _filter_videos(self, videos: List[VideoMetadata]) -> List[VideoMetadata]:
        """
        Filter videos based on criteria.

        Args:
            videos: List of video metadata

        Returns:
            Filtered list of videos
        """
        filtered = []

        for video in videos:
            # Check duration
            if video.duration_seconds > self.max_duration_seconds:
                logger.debug(
                    f"Skipping '{video.title}' - duration {video.duration_seconds}s "
                    f"exceeds max {self.max_duration_seconds}s"
                )
                continue

            # Check minimum duration (skip very short videos < 30 seconds)
            if video.duration_seconds < 30:
                logger.debug(f"Skipping '{video.title}' - too short ({video.duration_seconds}s)")
                continue

            # Filter out generic/viral content patterns
            if self._is_generic_content(video.title):
                logger.debug(f"Skipping '{video.title}' - appears to be generic content")
                continue

            filtered.append(video)

        return filtered

    def _is_generic_content(self, title: str) -> bool:
        """
        Check if video title suggests generic/viral content.

        Args:
            title: Video title

        Returns:
            True if appears to be generic content
        """
        title_lower = title.lower()

        # Patterns that suggest generic content
        generic_patterns = [
            'compilation',
            'funny moments',
            'top 10',
            'top 5',
            'best of',
            'fails',
            'challenge',
            'prank',
            'reaction',
            'unboxing',
            'vlog',
            'daily vlog'
        ]

        return any(pattern in title_lower for pattern in generic_patterns)

    def get_video_by_id(self, video_id: str) -> Optional[VideoMetadata]:
        """
        Get metadata for a specific video.

        Args:
            video_id: YouTube video ID

        Returns:
            Video metadata or None if not found
        """
        try:
            videos = self._get_video_details([video_id])
            return videos[0] if videos else None
        except Exception as e:
            logger.error(f"Error fetching video {video_id}: {e}")
            return None
