# Similarity Intelligence Platform

> **Editorial similarity analysis for written articles** - Compare your content against articles and YouTube video transcripts to assess originality and identify potential overlaps.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## 🎯 What Is This?

The **Similarity Intelligence Platform** is a production-ready API service that helps publishers and content creators understand how their articles compare to existing content across:

- **Article databases** - Other published articles
- **YouTube transcripts** - Spoken content from videos

### Key Principles

✅ **Not a plagiarism detector** - Provides similarity signals for editorial review
✅ **Privacy-first** - No raw article storage by default, opt-out corpus sharing
✅ **Cost-bounded** - Hard caps on processing (~$0.004 per check)
✅ **Async-first** - Non-blocking API with job-based processing
✅ **Production-ready** - Docker, PostgreSQL, Celery, FAISS vector search

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- 4GB+ RAM (for ML models)
- PostgreSQL 15+
- Redis 7+

### 1. Clone & Setup

```bash
cd Similarity-Intelligence-Platform

# Copy environment file
cp .env.example .env

# Edit .env and set SECRET_KEY (required)
# Generate with: openssl rand -hex 32
```

### 2. Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Check health
curl http://localhost:8000/health
```

### 3. Initialize Database

```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Create sample organization and API key
docker-compose exec api python scripts/init_db.py
```

**Save the API key** printed by the script - you'll need it for requests.

### 4. Make Your First Request

```bash
# Use the example script
./scripts/example_request.sh

# Or manually:
curl -X POST http://localhost:8000/v1/check \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": "Your article content here...",
    "language": "en",
    "sources": ["articles", "youtube"],
    "sensitivity": "medium"
  }'
```

---

## 📚 API Documentation

### Interactive Docs

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Celery Monitor**: http://localhost:5555

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/check` | Submit article for similarity check |
| GET | `/v1/check/{id}` | Get check results |
| GET | `/v1/usage` | Get usage statistics |

See the [Full API Documentation](#full-api-reference) below for details.

---

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────────┐
│   FastAPI       │◄──── API Key Auth
│   (REST API)    │◄──── Rate Limiting
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  PostgreSQL     │      │    Redis     │
│  (Metadata)     │      │  (Queue)     │
└─────────────────┘      └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │    Celery    │
                         │   Workers    │
                         └──────┬───────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              ┌──────────┐ ┌────────┐ ┌─────────┐
              │ Sentence │ │ FAISS  │ │ YouTube │
              │  BERT    │ │ Vector │ │   API   │
              │Embeddings│ │  Store │ │         │
              └──────────┘ └────────┘ └─────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | FastAPI 0.109 | Async REST API |
| **Database** | PostgreSQL 15 | Metadata storage |
| **Async Tasks** | Celery 5.3 + Redis 7 | Background processing |
| **Vector DB** | FAISS (CPU) | Similarity search |
| **Embeddings** | Sentence-Transformers | Semantic vectors (384-dim) |
| **ORM** | SQLAlchemy 2.0 | Database models |
| **Migration** | Alembic | Schema management |
| **Container** | Docker + Docker Compose | Deployment |

---

## 📊 How It Works

### 1. Text Chunking
- Articles split into 40-60 word chunks with 10-word overlap
- Text normalization (lowercase, whitespace, punctuation)
- Preserves semantic context across boundaries

### 2. Embedding Generation
- Uses `all-MiniLM-L6-v2` (384-dimensional vectors)
- Fast inference (~10ms per chunk)
- L2 normalized for cosine similarity

### 3. Dual-Layer Search

**Layer 1: Candidate Filtering**
- FAISS vector search (top-K retrieval)
- Filters by language, source type
- Caps at 100 candidates max

**Layer 2: Semantic Scoring**
- Cosine similarity calculation
- Threshold-based filtering (sensitivity levels)
- Aggregation by source

### 4. Risk Assessment

**Weighted scoring:**
- Max similarity (40% weight)
- Average similarity (30% weight)
- Coverage - % of chunks matched (20% weight)
- Match count (10% weight)

**Risk Levels:**
- 🟢 **Low** (0-65%): Minimal overlap
- 🟡 **Medium** (65-75%): Some similarity, review recommended
- 🔴 **High** (75%+): Significant overlap detected

---

## 🔧 Configuration

Key environment variables (see `.env.example` for all):

```bash
# Security (REQUIRED)
SECRET_KEY=your-32-char-secret-key

# Processing Limits
MAX_ARTICLE_WORDS=1500
MAX_CHUNK_WORDS=60
MAX_CANDIDATE_SOURCES=100

# Similarity Thresholds
SIMILARITY_THRESHOLD_LOW=0.65
SIMILARITY_THRESHOLD_MEDIUM=0.75
SIMILARITY_THRESHOLD_HIGH=0.85

# Privacy
STORE_RAW_ARTICLES=False
AUTO_DELETE_SUBMISSIONS=True
```

---

## 🔒 Privacy & Security

### Privacy Features
- ✅ No raw storage by default
- ✅ Opt-out corpus inclusion
- ✅ 7-day TTL auto-deletion
- ✅ 300-char snippet limits

### Security
- ✅ Bcrypt API key hashing
- ✅ Rate limiting
- ✅ Input validation
- ✅ SQL injection protection

---

## 📈 Performance Benchmarks

| Metric | Value |
|--------|-------|
| Processing time | 15-30 seconds |
| Cost per check | ~$0.004 USD |
| Throughput | ~2-4 checks/second/worker |
| Embedding speed | ~10ms per chunk |
| Vector search | <50ms for 10K vectors |

---

## 🛠️ Development

### Project Structure

```
app/
├── api/              # FastAPI routes
├── auth/             # Authentication
├── core/             # Business logic
│   ├── chunking.py   # Text chunking
│   ├── embeddings.py # Embedding generation
│   ├── similarity.py # Similarity engine
│   ├── vector_store.py # FAISS operations
│   └── youtube.py    # YouTube integration
├── models/           # SQLAlchemy models
├── schemas/          # Pydantic schemas
├── tasks/            # Celery tasks
└── main.py           # FastAPI app
```

### Running Tests

```bash
pytest tests/ -v
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

---

## 🚢 Production Deployment

### Checklist
- [ ] Set strong `SECRET_KEY`
- [ ] Use production database
- [ ] Enable HTTPS/TLS
- [ ] Set `DEBUG=False`
- [ ] Configure monitoring
- [ ] Enable backups
- [ ] Scale workers
- [ ] Set resource limits

---

## 🙋 FAQ

**Q: How accurate is the similarity detection?**
A: Uses semantic embeddings to detect paraphrased content and similar ideas. False positive rate typically <15%.

**Q: What about non-English content?**
A: MVP supports English only. Multi-language support planned for future releases.

**Q: How much does it cost to run?**
A: ~$0.004 per check. Infrastructure costs vary by scale (~$50-200/month for moderate usage).

**Q: Can I use my own embedding model?**
A: Yes! Set `EMBEDDING_MODEL` to any Sentence-Transformers model and update `EMBEDDING_DIMENSION`.

---

## 📞 Support

- **Issues**: GitHub Issues
- **Documentation**: See `/docs` endpoint
- **Examples**: Check `scripts/example_request.sh`

---

## Full API Reference

### POST `/v1/check` - Submit Similarity Check

**Request:**
```json
{
  "article_text": "Your article content...",
  "language": "en",
  "sources": ["articles", "youtube"],
  "sensitivity": "medium",
  "store_embeddings": false,
  "metadata": {
    "author": "John Doe",
    "title": "My Article"
  }
}
```

**Response (202 Accepted):**
```json
{
  "check_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "language": "en",
  "word_count": 847,
  "chunk_count": 0,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### GET `/v1/check/{check_id}` - Get Results

**Response (completed):**
```json
{
  "check_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "report": {
    "similarity_score": 67.5,
    "risk_level": "medium",
    "match_count": 3,
    "sources_checked": 150,
    "summary": "Found 3 matches...",
    "matches": [
      {
        "source_type": "youtube",
        "source_title": "Understanding AI Ethics",
        "similarity_score": 0.82,
        "snippet": "AI systems must be...",
        "matched_chunks": [...]
      }
    ]
  }
}
```

### GET `/v1/usage` - Usage Statistics

**Response:**
```json
{
  "organization_id": "...",
  "stats": {
    "current_month_checks": 47,
    "monthly_check_limit": 1000,
    "remaining_checks": 953,
    "tier": "starter"
  }
}
```

---

**Built with ❤️ for publishers and content creators**