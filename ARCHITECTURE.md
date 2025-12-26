# Architecture Overview

## System Design Principles

### 1. **Async-First Architecture**
- Non-blocking API responses (202 Accepted pattern)
- Celery workers for background processing
- Redis message queue for reliable task distribution
- Async database operations with SQLAlchemy 2.0

### 2. **Cost Optimization**
- Hard caps on article length (1,500 words)
- Limited candidate sources (100 max)
- Embedding caching via FAISS persistence
- Early exit for low-similarity cases
- Target cost: $0.004 per check

### 3. **Privacy by Design**
- No raw article storage by default
- Opt-out corpus inclusion
- 7-day TTL on submission data
- 300-character snippet limits
- API key hashing with bcrypt

### 4. **Scalability**
- Horizontal scaling via Celery workers
- Database connection pooling (20 connections)
- Stateless API design
- Vector store persistence for fast startup

## Data Flow

### Similarity Check Flow

```
1. Client Request
   POST /v1/check
   ↓
2. API Layer (FastAPI)
   - Validate API key
   - Check rate limits
   - Validate input (Pydantic)
   - Create Check record
   - Queue Celery task
   - Return job_id (202)
   ↓
3. Celery Worker
   - Fetch Check from DB
   - Normalize & chunk text
   - Generate embeddings (Sentence-BERT)
   ↓
4. Vector Search (FAISS)
   - Search article corpus
   - Search YouTube corpus
   - Apply similarity threshold
   ↓
5. Results Processing
   - Aggregate matches by source
   - Calculate risk score
   - Generate explanations
   - Save to database
   ↓
6. Client Polling
   GET /v1/check/{job_id}
   - Return status
   - Return report (if complete)
```

## Database Schema

### Tables

**organizations**
- Multi-tenant support
- Subscription tiers
- Usage quotas

**api_keys**
- Hashed keys (bcrypt)
- Rate limits
- Usage tracking

**checks**
- Job metadata
- Processing status
- Results summary

**sources**
- Reference content metadata
- Article & YouTube sources
- Indexing info

**matches**
- Individual similarity matches
- Source references
- Matched chunk data

**usage_logs**
- API usage tracking
- Cost tracking
- Analytics

### Vector Collections (FAISS)

**article_chunks**
- Source: article
- Metadata: source_id, chunk_index, title, url

**youtube_chunks**
- Source: youtube
- Metadata: video_id, chunk_index, timestamp, title

**submission_chunks** (optional, opt-in only)
- Source: submission
- TTL: 7 days
- Corpus inclusion with permission

## Component Responsibilities

### FastAPI API Layer
- Request validation
- Authentication & authorization
- Rate limiting
- Job submission
- Result retrieval
- OpenAPI documentation

### Celery Workers
- Text preprocessing
- Embedding generation
- Vector search
- Result aggregation
- Error handling

### PostgreSQL
- Relational data storage
- ACID transactions
- Complex queries (usage stats, filtering)
- Data integrity

### Redis
- Celery message broker
- Task result backend
- Future: Caching layer

### FAISS Vector Store
- Fast similarity search (cosine)
- In-memory index with disk persistence
- Metadata storage
- Top-K retrieval

### Sentence-Transformers
- Semantic embeddings
- 384-dimensional vectors
- Normalized (L2)
- Model: all-MiniLM-L6-v2

## Similarity Engine

### Text Chunking
```python
Input: "Article text..."
↓
Normalize (lowercase, whitespace)
↓
Split into 40-60 word chunks
↓
10-word overlap between chunks
↓
Output: List[TextChunk]
```

### Embedding Pipeline
```python
Chunks: ["chunk 1", "chunk 2", ...]
↓
Batch encode (Sentence-BERT)
↓
Normalize (L2)
↓
Output: np.array (N x 384)
```

### Similarity Scoring
```python
Query embeddings vs. Corpus embeddings
↓
Cosine similarity (dot product)
↓
Filter by threshold (sensitivity)
↓
Aggregate by source
↓
Calculate weighted score:
  - Max similarity: 40%
  - Avg similarity: 30%
  - Coverage: 20%
  - Match count: 10%
↓
Risk level: low/medium/high
```

## Performance Characteristics

### Latency Breakdown
- API response time: <50ms
- Queue latency: <100ms
- Text chunking: ~100ms (1000 words)
- Embedding generation: ~500ms (15 chunks)
- Vector search: <50ms (10K vectors)
- Result processing: ~200ms
- **Total: 15-30 seconds**

### Throughput
- Single worker: ~2-4 checks/second
- Horizontal scaling: Linear with workers
- Bottleneck: Embedding generation (CPU-bound)

### Resource Usage
- Memory per worker: ~2GB (model + index)
- CPU: High during embedding (1 core per worker)
- Disk: ~100MB per 10K sources
- Network: Minimal (local processing)

## Security Measures

### API Security
- API key authentication (X-API-Key header)
- Bcrypt hashing (cost factor 12)
- Rate limiting (configurable)
- Input validation (Pydantic)
- SQL injection protection (ORM)

### Data Security
- No raw article storage
- Encrypted connections (TLS)
- Secrets in environment variables
- No sensitive data in logs

### Privacy Controls
- Opt-out corpus inclusion
- TTL-based deletion
- Minimal data retention
- Snippet length limits

## Deployment Architecture

### Docker Compose (Development)
```yaml
services:
  - db (PostgreSQL)
  - redis
  - api (FastAPI)
  - celery_worker
  - celery_flower (monitoring)
```

### Production Recommendations
- **Load balancer**: Nginx/HAProxy
- **API replicas**: 2-4 instances
- **Workers**: 4-8 instances
- **Database**: Managed PostgreSQL (RDS, CloudSQL)
- **Redis**: Managed Redis (ElastiCache)
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK stack
- **Secrets**: Vault, AWS Secrets Manager

## Future Enhancements

### Short-term
- [ ] Webhook notifications (Pro tier)
- [ ] Batch API for multiple articles
- [ ] Enhanced YouTube search (Data API)
- [ ] Result caching

### Medium-term
- [ ] Multi-language support
- [ ] Web crawling integration
- [ ] Custom corpus upload
- [ ] Advanced filtering (date ranges, sources)

### Long-term
- [ ] Cross-language similarity
- [ ] Real-time streaming checks
- [ ] ML-based false positive reduction
- [ ] Graph-based source relationships
- [ ] Federated search across instances

## Monitoring & Observability

### Key Metrics
- API request rate (req/s)
- Check processing time (p50, p95, p99)
- Queue depth (pending tasks)
- Worker utilization
- Error rate (%)
- Cost per check

### Alerts
- High error rate (>5%)
- Slow processing (>60s)
- Queue backup (>100 pending)
- Database connection issues
- High memory usage (>90%)

### Health Checks
- `/health` endpoint
- Database connectivity
- Redis connectivity
- Worker availability
- FAISS index loaded

## Trade-offs & Design Decisions

### Async vs. Sync API
**Decision**: Async (job-based)
**Rationale**: Processing takes 15-30s, blocking requests bad UX
**Trade-off**: More complex client integration

### FAISS CPU vs. GPU
**Decision**: CPU (MVP)
**Rationale**: Lower cost, simpler deployment
**Trade-off**: 10x slower than GPU, but acceptable for MVP

### Sentence-Transformers vs. OpenAI
**Decision**: Local Sentence-Transformers
**Rationale**: No API costs, data privacy, predictable latency
**Trade-off**: Lower quality than GPT embeddings

### PostgreSQL vs. NoSQL
**Decision**: PostgreSQL
**Rationale**: ACID transactions, complex queries, mature ecosystem
**Trade-off**: Vertical scaling limits (mitigated by connection pooling)

### Celery vs. AWS Lambda
**Decision**: Celery
**Rationale**: No vendor lock-in, stateful processing, local models
**Trade-off**: More infrastructure to manage

## Cost Analysis

### Per-Check Breakdown
- Compute (embedding): $0.002
- Vector search: $0.001
- Database operations: $0.0005
- YouTube API: $0.0005 (if used)
- **Total: ~$0.004**

### Monthly Infrastructure (moderate usage)
- PostgreSQL (managed): $50
- Redis (managed): $20
- Compute (4 workers): $80
- Storage: $10
- **Total: ~$160/month**
- **At 10K checks/month**: $0.016 per check (infra) + $0.004 (compute) = $0.02/check
