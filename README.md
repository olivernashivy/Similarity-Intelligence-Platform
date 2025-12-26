# Similarity Intelligence Platform

A comprehensive YouTube similarity detection subsystem for identifying semantic similarities between articles and YouTube video transcripts using advanced NLP and embedding techniques.

## Overview

This platform analyzes article content and compares it against publicly available YouTube video transcripts to detect potential semantic similarities. It's designed for **similarity analysis, NOT copyright enforcement**.

### Key Features

- **Intelligent Video Discovery**: Automatically searches YouTube for relevant videos based on article keywords
- **Transcript Analysis**: Fetches and processes public English transcripts
- **Semantic Matching**: Uses state-of-the-art embeddings to compare content semantically
- **Performance Optimized**: Redis caching layer for transcript embeddings
- **Cost Controls**: Hard limits on API usage and processing
- **REST API**: FastAPI-based API with comprehensive documentation

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Article Input                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Keyword Extraction                              │
│  • Title-weighted terms                                      │
│  • Named entities                                            │
│  • High TF-IDF phrases                                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           YouTube Video Discovery                            │
│  • YouTube Data API search                                   │
│  • Filter by duration, language                              │
│  • Limit to max videos (default: 10)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           Transcript Fetching                                │
│  • Public captions only                                      │
│  • English language                                          │
│  • Quality validation                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│        Transcript Processing & Chunking                      │
│  • Normalize text                                            │
│  • Chunk by words (40-60 per chunk)                          │
│  • Preserve timestamps                                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           Embedding Generation                               │
│  • OpenAI text-embedding-3-small                             │
│  • Batch processing                                          │
│  • Redis caching                                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         Similarity Matching                                  │
│  • Cosine similarity                                         │
│  • Threshold filtering (≥0.80)                               │
│  • Match aggregation                                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Results Reporting                               │
│  • Video metadata                                            │
│  • Timestamp ranges                                          │
│  • Similarity scores                                         │
│  • Transcript snippets                                       │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Backend**: Python 3.11+, FastAPI
- **NLP**: OpenAI Embeddings, spaCy, scikit-learn
- **Caching**: Redis
- **YouTube Integration**: YouTube Data API v3, youtube-transcript-api
- **Deployment**: Docker, Docker Compose

## Installation

### Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose (for containerized deployment)
- YouTube Data API key
- OpenAI API key
- Redis (optional, for caching)

### Quick Start with Docker

1. **Clone the repository**:
   ```bash
   git clone https://github.com/olivernashivy/Similarity-Intelligence-Platform.git
   cd Similarity-Intelligence-Platform
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

3. **Start the services**:
   ```bash
   docker-compose up -d
   ```

4. **Access the API**:
   - API Documentation: http://localhost:8000/docs
   - Alternative Docs: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/health

### Local Development Setup

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the application**:
   ```bash
   python -m src.api.main
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `YOUTUBE_API_KEY` | YouTube Data API key | Required |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `REDIS_HOST` | Redis server host | localhost |
| `REDIS_PORT` | Redis server port | 6379 |
| `MAX_VIDEOS_PER_CHECK` | Max videos to analyze per request | 10 |
| `MAX_VIDEO_DURATION_MINUTES` | Max video duration in minutes | 20 |
| `SIMILARITY_THRESHOLD` | Minimum similarity score (0-1) | 0.80 |
| `CHUNK_SIZE_WORDS` | Words per chunk | 50 |
| `CACHE_ENABLED` | Enable Redis caching | true |
| `CACHE_TTL_HOURS` | Cache TTL in hours | 24 |
| `EMBEDDING_MODEL` | OpenAI embedding model | text-embedding-3-small |

## API Usage

### Analyze Article for Similarities

**Endpoint**: `POST /api/v1/similarity/analyze`

**Request**:
```json
{
  "title": "Understanding Neural Networks",
  "content": "Neural networks are a fundamental concept in machine learning...",
  "author": "John Doe",
  "url": "https://example.com/article"
}
```

**Response**:
```json
{
  "article_title": "Understanding Neural Networks",
  "analyzed_at": "2025-12-26T10:30:00Z",
  "videos_analyzed": 8,
  "matches_found": 3,
  "message": "Possible similarity to spoken content",
  "keywords_extracted": ["neural networks", "machine learning", "deep learning"],
  "results": [
    {
      "video_id": "abc123",
      "video_title": "Neural Networks Explained",
      "channel_name": "AI Academy",
      "video_url": "https://www.youtube.com/watch?v=abc123",
      "max_similarity": 0.87,
      "matched_chunks_count": 12,
      "coverage_percentage": 15.5,
      "matches": [
        {
          "video_id": "abc123",
          "video_title": "Neural Networks Explained",
          "channel_name": "AI Academy",
          "video_url": "https://www.youtube.com/watch?v=abc123",
          "timestamp_start": 120.5,
          "timestamp_end": 185.2,
          "transcript_snippet": "neural networks work by processing data through layers...",
          "similarity_score": 0.87,
          "matched_chunks_count": 5
        }
      ]
    }
  ]
}
```

### Other Endpoints

- `GET /api/v1/similarity/health` - Health check
- `GET /api/v1/similarity/cache/stats` - Cache statistics
- `DELETE /api/v1/similarity/cache/clear` - Clear cache

## Safety & Privacy Controls

### What This System Does

- Analyzes publicly available YouTube transcripts
- Compares semantic similarity (not exact copying)
- Uses only public YouTube Data API
- Caches embeddings (not full transcripts)
- Implements hard limits on processing

### What This System Does NOT Do

- Does NOT download audio/video content
- Does NOT store full transcripts permanently
- Does NOT access private or unlisted videos
- Does NOT make copyright claims
- Does NOT provide legal conclusions

### Cost Controls

- Max videos per check: 10 (configurable)
- Max video duration: 20 minutes (configurable)
- Max transcript length: 10,000 characters
- Caching to reduce API calls
- Early exit on low similarity

## Development

### Project Structure

```
Similarity-Intelligence-Platform/
├── src/
│   ├── youtube_similarity/
│   │   ├── config.py                 # Configuration management
│   │   ├── models.py                 # Data models
│   │   ├── services/
│   │   │   ├── keyword_extractor.py  # Keyword extraction
│   │   │   ├── video_discovery.py    # YouTube search
│   │   │   ├── transcript_fetcher.py # Transcript fetching
│   │   │   ├── transcript_processor.py # Text processing
│   │   │   ├── embedding_service.py  # Embedding generation
│   │   │   ├── similarity_matcher.py # Similarity matching
│   │   │   └── cache_service.py      # Redis caching
│   │   ├── core/
│   │   │   └── youtube_similarity_engine.py # Main engine
│   │   └── utils/
│   │       └── text_utils.py         # Text utilities
│   └── api/
│       ├── main.py                   # FastAPI app
│       └── routes/
│           └── similarity.py         # API routes
├── tests/                            # Unit tests
├── docker-compose.yml                # Docker setup
├── Dockerfile                        # Container image
├── requirements.txt                  # Dependencies
└── README.md                         # Documentation
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/
```

## Troubleshooting

### Common Issues

1. **YouTube API quota exceeded**:
   - Reduce `MAX_VIDEOS_PER_CHECK`
   - Use caching to minimize API calls

2. **OpenAI rate limits**:
   - Increase retry delays
   - Use smaller batch sizes
   - Consider using sentence-transformers for local embeddings

3. **Redis connection errors**:
   - Verify Redis is running: `docker ps`
   - Check `REDIS_HOST` and `REDIS_PORT` settings

4. **No transcripts found**:
   - Ensure videos have public captions
   - Try videos with manually created captions
   - Check video language is English

## Performance Optimization

- **Caching**: Enable Redis caching to avoid re-processing videos
- **Batch Size**: Adjust embedding batch size for your API limits
- **Video Filters**: Use duration and language filters effectively
- **Chunk Size**: Optimize chunk size (40-60 words) for your use case

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and questions:
- GitHub Issues: https://github.com/olivernashivy/Similarity-Intelligence-Platform/issues

## Acknowledgments

- OpenAI for embedding models
- YouTube Data API
- FastAPI framework
- Redis caching system