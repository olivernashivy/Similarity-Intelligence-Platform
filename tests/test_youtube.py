"""Tests for YouTube integration module."""
import pytest
from unittest.mock import patch, Mock, MagicMock
from googleapiclient.errors import HttpError

from app.core.youtube import (
    YouTubeTranscriptFetcher,
    TranscriptSegment,
    search_and_fetch_transcripts
)


class TestYouTubeTranscriptFetcher:
    """Test cases for YouTubeTranscriptFetcher class."""

    @pytest.fixture
    def fetcher(self, mock_youtube_client):
        """Create fetcher with mocked YouTube client."""
        with patch('app.core.youtube.build') as mock_build:
            mock_build.return_value = mock_youtube_client
            with patch('app.core.youtube.settings') as mock_settings:
                mock_settings.youtube_api_key = "test_api_key"
                fetcher = YouTubeTranscriptFetcher(max_videos=5, max_duration_minutes=30)
                fetcher.youtube_client = mock_youtube_client
                return fetcher

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        with patch('app.core.youtube.build') as mock_build:
            mock_build.return_value = MagicMock()
            with patch('app.core.youtube.settings') as mock_settings:
                mock_settings.youtube_api_key = "test_key"
                fetcher = YouTubeTranscriptFetcher()

                assert fetcher.max_videos == 5
                assert fetcher.max_duration_minutes == 30

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        with patch('app.core.youtube.settings') as mock_settings:
            mock_settings.youtube_api_key = None
            fetcher = YouTubeTranscriptFetcher()

            assert fetcher.youtube_client is None

    def test_extract_video_id_standard_url(self, fetcher):
        """Test video ID extraction from standard YouTube URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = fetcher.extract_video_id(url)

        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_short_url(self, fetcher):
        """Test video ID extraction from short URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        video_id = fetcher.extract_video_id(url)

        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_embed_url(self, fetcher):
        """Test video ID extraction from embed URL."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        video_id = fetcher.extract_video_id(url)

        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_plain_id(self, fetcher):
        """Test video ID extraction from plain ID string."""
        video_id = fetcher.extract_video_id("dQw4w9WgXcQ")

        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid(self, fetcher):
        """Test video ID extraction with invalid input."""
        video_id = fetcher.extract_video_id("not a valid url or id")

        assert video_id is None

    def test_fetch_transcript_success(self, fetcher, sample_video_id):
        """Test successful transcript fetching."""
        with patch('app.core.youtube.YouTubeTranscriptApi') as mock_api:
            mock_transcript_list = MagicMock()
            mock_transcript = MagicMock()
            mock_transcript.fetch.return_value = [
                {"text": "Hello world", "start": 0.0, "duration": 2.0}
            ]
            mock_transcript_list.find_manually_created_transcript.return_value = mock_transcript

            mock_api.list_transcripts.return_value = mock_transcript_list

            result = fetcher.fetch_transcript(sample_video_id)

            assert result is not None
            assert len(result) > 0
            assert "text" in result[0]

    def test_fetch_transcript_no_manual_fallback_auto(self, fetcher, sample_video_id):
        """Test fallback to auto-generated transcript."""
        with patch('app.core.youtube.YouTubeTranscriptApi') as mock_api:
            mock_transcript_list = MagicMock()
            mock_transcript = MagicMock()
            mock_transcript.fetch.return_value = [
                {"text": "Auto-generated", "start": 0.0, "duration": 2.0}
            ]

            # Manual transcript not found, fall back to auto
            mock_transcript_list.find_manually_created_transcript.side_effect = Exception("Not found")
            mock_transcript_list.find_generated_transcript.return_value = mock_transcript

            mock_api.list_transcripts.return_value = mock_transcript_list

            result = fetcher.fetch_transcript(sample_video_id)

            assert result is not None
            assert result[0]["text"] == "Auto-generated"

    def test_fetch_transcript_disabled(self, fetcher, sample_video_id):
        """Test handling of disabled transcripts."""
        from youtube_transcript_api._errors import TranscriptsDisabled

        with patch('app.core.youtube.YouTubeTranscriptApi') as mock_api:
            mock_api.list_transcripts.side_effect = TranscriptsDisabled(sample_video_id)

            result = fetcher.fetch_transcript(sample_video_id)

            assert result is None

    def test_process_transcript(self, fetcher, sample_transcript_data):
        """Test transcript processing into segments."""
        segments = fetcher.process_transcript(sample_transcript_data)

        assert len(segments) > 0
        assert all(isinstance(seg, TranscriptSegment) for seg in segments)

        # Check first segment
        first_seg = segments[0]
        assert first_seg.text == "Hello and welcome to this tutorial"
        assert first_seg.start_time == 0.0
        assert first_seg.duration == 3.0
        assert first_seg.timestamp == "00:00"

    def test_process_transcript_timestamp_formatting(self, fetcher):
        """Test timestamp formatting in transcript processing."""
        data = [
            {"text": "Test", "start": 65.5, "duration": 2.0},  # 1:05
            {"text": "Test2", "start": 125.0, "duration": 2.0},  # 2:05
        ]

        segments = fetcher.process_transcript(data)

        assert segments[0].timestamp == "01:05"
        assert segments[1].timestamp == "02:05"

    def test_chunk_transcript(self, fetcher):
        """Test transcript chunking."""
        segments = [
            TranscriptSegment(text="Hello world", start_time=0.0, duration=2.0, timestamp="00:00"),
            TranscriptSegment(text="This is a test", start_time=2.0, duration=2.0, timestamp="00:02"),
            TranscriptSegment(text="Of the chunking system", start_time=4.0, duration=2.0, timestamp="00:04"),
        ]

        chunks = fetcher.chunk_transcript(segments, target_words=5)

        assert len(chunks) > 0
        # Each chunk is a tuple of (text, timestamp)
        assert all(isinstance(chunk, tuple) and len(chunk) == 2 for chunk in chunks)
        assert all(isinstance(chunk[0], str) and isinstance(chunk[1], str) for chunk in chunks)

    def test_remove_filler_words(self, fetcher):
        """Test filler word removal."""
        text = "Um, like, you know, this is actually a test"
        cleaned = fetcher._remove_filler_words(text)

        # Filler words should be removed
        assert "um" not in cleaned.lower()
        assert "like" not in cleaned.lower()
        assert "actually" not in cleaned.lower()
        assert "test" in cleaned.lower()

    def test_search_videos_by_keywords(self, fetcher):
        """Test video search by keywords."""
        keywords = ["machine", "learning", "tutorial"]

        video_ids = fetcher.search_videos_by_keywords(keywords, max_results=3)

        assert isinstance(video_ids, list)
        # Should filter generic content, so may have fewer results
        assert len(video_ids) <= 3

    def test_search_videos_no_client(self):
        """Test video search without API client."""
        fetcher = YouTubeTranscriptFetcher()
        fetcher.youtube_client = None

        video_ids = fetcher.search_videos_by_keywords(["test"], max_results=5)

        # Should return empty list
        assert video_ids == []

    def test_search_videos_http_error(self, fetcher):
        """Test handling of HTTP errors during search."""
        # Mock HTTP error
        error_resp = Mock()
        error_resp.status = 403
        http_error = HttpError(resp=error_resp, content=b"Forbidden")

        fetcher.youtube_client.search().list().execute.side_effect = http_error

        video_ids = fetcher.search_videos_by_keywords(["test"])

        assert video_ids == []

    def test_filter_generic_content(self, fetcher):
        """Test filtering of generic/viral content."""
        video_items = [
            {'id': 'video1', 'title': 'Machine Learning Tutorial'},  # Good
            {'id': 'video2', 'title': 'Top 10 AI Fails Compilation'},  # Generic
            {'id': 'video3', 'title': 'Deep Learning Explained'},  # Good
            {'id': 'video4', 'title': 'Funny AI Moments Compilation'},  # Generic
            {'id': 'video5', 'title': 'ML Challenge Prank'},  # Generic
        ]

        filtered = fetcher._filter_generic_content(video_items)

        # Should filter out generic content
        assert len(filtered) < len(video_items)

        # Good videos should remain
        titles = [item['title'] for item in filtered]
        assert any('Machine Learning Tutorial' in title for title in titles)
        assert any('Deep Learning Explained' in title for title in titles)

        # Generic content should be removed
        assert not any('Compilation' in title for title in titles)
        assert not any('Challenge' in title for title in titles)

    def test_filter_videos_by_duration(self, fetcher):
        """Test filtering videos by duration."""
        video_ids = ['video1', 'video2']

        filtered = fetcher._filter_videos_by_duration(video_ids)

        # Should return videos within duration limits
        assert isinstance(filtered, list)
        assert len(filtered) <= len(video_ids)

    def test_filter_videos_by_duration_no_client(self):
        """Test duration filtering without client."""
        fetcher = YouTubeTranscriptFetcher()
        fetcher.youtube_client = None

        filtered = fetcher._filter_videos_by_duration(['video1', 'video2'])

        assert filtered == []

    def test_get_video_metadata(self, fetcher, sample_video_id):
        """Test fetching video metadata."""
        metadata = fetcher.get_video_metadata(sample_video_id)

        assert isinstance(metadata, dict)
        assert 'video_id' in metadata
        assert 'title' in metadata
        assert 'channel' in metadata
        assert 'duration_seconds' in metadata
        assert 'url' in metadata

    def test_get_video_metadata_no_client(self, sample_video_id):
        """Test metadata fetching without API client."""
        fetcher = YouTubeTranscriptFetcher()
        fetcher.youtube_client = None

        metadata = fetcher.get_video_metadata(sample_video_id)

        # Should return fallback metadata
        assert metadata['video_id'] == sample_video_id
        assert metadata['title'] == f"Video {sample_video_id}"
        assert metadata['channel'] == "Unknown"

    def test_format_timestamp(self, fetcher):
        """Test timestamp formatting."""
        # Test various durations
        assert fetcher._format_timestamp(0) == "00:00"
        assert fetcher._format_timestamp(65) == "01:05"
        assert fetcher._format_timestamp(125) == "02:05"
        assert fetcher._format_timestamp(3665) == "61:05"


class TestSearchAndFetchTranscripts:
    """Test cases for search_and_fetch_transcripts function."""

    def test_search_and_fetch_basic(self, sample_article_text):
        """Test basic search and fetch."""
        with patch('app.core.youtube.YouTubeTranscriptFetcher') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.search_videos_by_keywords.return_value = ['video1', 'video2']
            mock_fetcher.get_video_metadata.return_value = {
                'video_id': 'video1',
                'title': 'Test Video',
                'duration_seconds': 300
            }
            mock_fetcher.fetch_transcript.return_value = [
                {"text": "Test transcript", "start": 0.0, "duration": 2.0}
            ]
            mock_fetcher.process_transcript.return_value = [
                TranscriptSegment(text="Test", start_time=0.0, duration=2.0, timestamp="00:00")
            ]
            mock_fetcher.chunk_transcript.return_value = [("Test chunk", "00:00")]
            mock_fetcher.max_duration_minutes = 30

            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.core.youtube.extract_keywords') as mock_extract:
                mock_extract.return_value = ['machine', 'learning']

                results = search_and_fetch_transcripts(sample_article_text, max_videos=2)

                assert isinstance(results, list)

    def test_search_and_fetch_no_videos_found(self, sample_article_text):
        """Test when no videos are found."""
        with patch('app.core.youtube.YouTubeTranscriptFetcher') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.search_videos_by_keywords.return_value = []

            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.core.youtube.extract_keywords') as mock_extract:
                mock_extract.return_value = ['test']

                results = search_and_fetch_transcripts(sample_article_text)

                assert results == []

    def test_search_and_fetch_skip_long_videos(self, sample_article_text):
        """Test that videos exceeding duration limit are skipped."""
        with patch('app.core.youtube.YouTubeTranscriptFetcher') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.search_videos_by_keywords.return_value = ['video1']
            mock_fetcher.get_video_metadata.return_value = {
                'video_id': 'video1',
                'title': 'Long Video',
                'duration_seconds': 3600  # 60 minutes
            }
            mock_fetcher.max_duration_minutes = 30

            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.core.youtube.extract_keywords') as mock_extract:
                mock_extract.return_value = ['test']

                results = search_and_fetch_transcripts(sample_article_text)

                # Should skip video due to duration
                assert len(results) == 0

    def test_search_and_fetch_skip_no_transcript(self, sample_article_text):
        """Test that videos without transcripts are skipped."""
        with patch('app.core.youtube.YouTubeTranscriptFetcher') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.search_videos_by_keywords.return_value = ['video1']
            mock_fetcher.get_video_metadata.return_value = {
                'video_id': 'video1',
                'title': 'No Transcript Video',
                'duration_seconds': 300
            }
            mock_fetcher.fetch_transcript.return_value = None  # No transcript
            mock_fetcher.max_duration_minutes = 30

            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.core.youtube.extract_keywords') as mock_extract:
                mock_extract.return_value = ['test']

                results = search_and_fetch_transcripts(sample_article_text)

                # Should skip video due to missing transcript
                assert len(results) == 0
