"""Shared pytest fixtures for testing."""
import pytest
import numpy as np
from unittest.mock import Mock, MagicMock
from datetime import datetime
from uuid import uuid4

from app.core.chunking import TextChunk


@pytest.fixture
def sample_article_text():
    """Sample article text for testing."""
    return """
    Artificial intelligence and machine learning are transforming the tech industry.
    These technologies enable computers to learn from data and make intelligent decisions.
    Neural networks are a key component of modern AI systems.
    Deep learning models can process vast amounts of information.
    Companies are investing heavily in AI research and development.
    The future of technology depends on advances in machine learning algorithms.
    """


@pytest.fixture
def sample_short_text():
    """Short text for edge case testing."""
    return "This is a very short text."


@pytest.fixture
def sample_empty_text():
    """Empty text for edge case testing."""
    return ""


@pytest.fixture
def sample_video_id():
    """Sample YouTube video ID."""
    return "dQw4w9WgXcQ"


@pytest.fixture
def sample_video_metadata():
    """Sample YouTube video metadata."""
    return {
        "video_id": "dQw4w9WgXcQ",
        "title": "Understanding Machine Learning",
        "channel": "Tech Education",
        "duration_seconds": 600,
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "published_at": "2024-01-15T10:00:00Z",
        "description": "A comprehensive guide to machine learning concepts"
    }


@pytest.fixture
def sample_transcript_data():
    """Sample YouTube transcript data."""
    return [
        {"text": "Hello and welcome to this tutorial", "start": 0.0, "duration": 3.0},
        {"text": "Today we'll learn about machine learning", "start": 3.5, "duration": 4.0},
        {"text": "Machine learning is a subset of AI", "start": 8.0, "duration": 3.5},
        {"text": "It enables computers to learn from data", "start": 12.0, "duration": 3.8},
        {"text": "Neural networks are powerful tools", "start": 16.5, "duration": 3.2},
        {"text": "They can recognize patterns in data", "start": 20.0, "duration": 3.5},
    ]


@pytest.fixture
def sample_chunks():
    """Sample text chunks."""
    return [
        TextChunk(
            text="artificial intelligence machine learning transforming tech industry",
            index=0,
            start_word=0,
            end_word=8
        ),
        TextChunk(
            text="technologies enable computers learn data make intelligent decisions",
            index=1,
            start_word=6,
            end_word=14
        ),
        TextChunk(
            text="neural networks key component modern ai systems",
            index=2,
            start_word=12,
            end_word=19
        ),
    ]


@pytest.fixture
def sample_embeddings():
    """Sample embeddings (fixed numpy arrays for deterministic testing)."""
    np.random.seed(42)
    # 3 embeddings, 384 dimensions (matching all-MiniLM-L6-v2)
    embeddings = np.random.randn(3, 384).astype(np.float32)
    # Normalize
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings / norms


@pytest.fixture
def mock_youtube_client():
    """Mock YouTube API client."""
    mock_client = MagicMock()

    # Mock search response
    search_mock = MagicMock()
    search_mock.list.return_value.execute.return_value = {
        'items': [
            {
                'id': {'videoId': 'video1', 'kind': 'youtube#video'},
                'snippet': {'title': 'Machine Learning Basics'}
            },
            {
                'id': {'videoId': 'video2', 'kind': 'youtube#video'},
                'snippet': {'title': 'AI Tutorial'}
            },
            {
                'id': {'videoId': 'video3', 'kind': 'youtube#video'},
                'snippet': {'title': 'Top 10 AI Fails'}  # Generic content
            },
        ]
    }
    mock_client.search.return_value = search_mock

    # Mock videos response for duration
    videos_mock = MagicMock()
    videos_mock.list.return_value.execute.return_value = {
        'items': [
            {
                'id': 'video1',
                'contentDetails': {'duration': 'PT10M30S'},  # 10m 30s
                'snippet': {
                    'title': 'Machine Learning Basics',
                    'channelTitle': 'Tech Channel',
                    'publishedAt': '2024-01-15T10:00:00Z',
                    'description': 'A tutorial on ML'
                }
            },
            {
                'id': 'video2',
                'contentDetails': {'duration': 'PT5M15S'},  # 5m 15s
                'snippet': {
                    'title': 'AI Tutorial',
                    'channelTitle': 'AI Academy',
                    'publishedAt': '2024-01-10T12:00:00Z',
                    'description': 'Learn AI basics'
                }
            },
        ]
    }
    mock_client.videos.return_value = videos_mock

    return mock_client


@pytest.fixture
def mock_embedding_generator():
    """Mock embedding generator."""
    mock_gen = Mock()

    # Mock encode method
    def mock_encode(texts, normalize=True):
        np.random.seed(42)
        n_texts = len(texts) if isinstance(texts, list) else 1
        embeddings = np.random.randn(n_texts, 384).astype(np.float32)
        if normalize:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / norms
        return embeddings

    # Mock batch_similarity method
    def mock_batch_similarity(embedding, embeddings_list):
        # Return fixed similarities for testing
        np.random.seed(42)
        return np.random.uniform(0.5, 0.95, len(embeddings_list))

    mock_gen.encode = Mock(side_effect=mock_encode)
    mock_gen.batch_similarity = Mock(side_effect=mock_batch_similarity)
    mock_gen.dimension = 384

    return mock_gen


@pytest.fixture
def mock_transcript_api(monkeypatch):
    """Mock YouTubeTranscriptApi."""
    from unittest.mock import patch

    mock_transcript_list = MagicMock()
    mock_transcript = MagicMock()
    mock_transcript.fetch.return_value = [
        {"text": "Hello and welcome", "start": 0.0, "duration": 2.0},
        {"text": "Machine learning basics", "start": 2.5, "duration": 3.0},
        {"text": "Neural networks explained", "start": 6.0, "duration": 3.5},
    ]

    mock_transcript_list.find_manually_created_transcript.return_value = mock_transcript

    with patch('app.core.youtube.YouTubeTranscriptApi') as mock_api:
        mock_api.list_transcripts.return_value = mock_transcript_list
        yield mock_api


@pytest.fixture
def mock_vector_store():
    """Mock vector store."""
    mock_store = Mock()

    def mock_search(embedding, k=10, filter_fn=None):
        """Mock search that returns deterministic results."""
        from app.core.vector_store import VectorMetadata

        results = []
        for i in range(min(k, 3)):
            meta = VectorMetadata(
                source_id=f"source_{i}",
                source_type="article",
                chunk_index=i,
                chunk_text=f"Sample chunk text {i} about machine learning and AI",
                timestamp=None,
                title=f"Article Title {i}",
                identifier=f"https://example.com/article{i}"
            )
            score = 0.85 - (i * 0.1)  # Decreasing scores
            results.append((meta, score))

        return results

    mock_store.search = Mock(side_effect=mock_search)
    mock_store.add_vectors = Mock()
    mock_store.save = Mock()

    return mock_store


@pytest.fixture
def sample_check_id():
    """Sample check UUID."""
    return str(uuid4())


@pytest.fixture
def sample_similarity_matches(sample_chunks):
    """Sample similarity matches."""
    from app.core.similarity import SimilarityMatch

    return [
        SimilarityMatch(
            submission_chunk=sample_chunks[0],
            source_chunk_text="AI and ML are transforming technology",
            source_id="video1",
            source_type="youtube",
            similarity_score=0.87,
            source_metadata={
                "title": "ML Tutorial",
                "identifier": "https://youtube.com/watch?v=video1",
                "timestamp": "00:30",
                "duration_seconds": 600
            }
        ),
        SimilarityMatch(
            submission_chunk=sample_chunks[1],
            source_chunk_text="computers can learn from data automatically",
            source_id="video1",
            source_type="youtube",
            similarity_score=0.82,
            source_metadata={
                "title": "ML Tutorial",
                "identifier": "https://youtube.com/watch?v=video1",
                "timestamp": "01:15",
                "duration_seconds": 600
            }
        ),
        SimilarityMatch(
            submission_chunk=sample_chunks[2],
            source_chunk_text="neural networks are powerful AI tools",
            source_id="video2",
            source_type="youtube",
            similarity_score=0.79,
            source_metadata={
                "title": "AI Basics",
                "identifier": "https://youtube.com/watch?v=video2",
                "timestamp": "02:00",
                "duration_seconds": 300
            }
        ),
    ]
