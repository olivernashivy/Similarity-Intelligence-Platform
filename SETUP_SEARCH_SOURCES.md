# Search Sources Setup Guide

## 🎉 **NEW: Real-Time Web Article Search**

The system now searches **both local corpus AND the internet** for articles!

When you search for articles, the system will:
1. ✅ Search your local article corpus (if populated)
2. ✅ **Search the web in real-time** (Google + Bing)
3. ✅ Fetch and analyze the most relevant articles
4. ✅ Return combined results from both sources

---

## **Problem 1: YouTube Search Not Working**

### Why It's Failing:
- **No YouTube API key configured** → YouTube client doesn't initialize
- When searching, returns empty list immediately
- Results in 0 videos checked

### How to Fix:

#### Step 1: Get a YouTube Data API v3 Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **YouTube Data API v3**:
   - Go to "APIs & Services" → "Enable APIs and Services"
   - Search for "YouTube Data API v3"
   - Click "Enable"
4. Create credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "API Key"
   - Copy the API key

#### Step 2: Add API Key to Your Environment

**Option A: Using .env file (Recommended)**
```bash
# Create .env file from example
cp .env.example .env

# Edit .env and add your key
YOUTUBE_API_KEY=AIzaSyC-your-actual-api-key-here
```

**Option B: Using Docker Compose**
```yaml
# In docker-compose.yml, add to environment:
services:
  api:
    environment:
      - YOUTUBE_API_KEY=AIzaSyC-your-actual-api-key-here
```

**Option C: Export as environment variable**
```bash
export YOUTUBE_API_KEY=AIzaSyC-your-actual-api-key-here
```

#### Step 3: Restart the Application
```bash
# If using Docker:
docker-compose down
docker-compose up -d

# If running directly:
# Kill the process and restart
```

#### Step 4: Verify YouTube Search Works
```bash
# Test with curl:
curl -X POST http://localhost:8000/v1/check \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": "Artificial intelligence and machine learning are transforming how we build software. Deep learning models like GPT and BERT have revolutionized natural language processing. Companies are now using AI for everything from customer service to code generation.",
    "sources": ["youtube"]
  }'

# Check the result after 30 seconds:
curl -X GET http://localhost:8000/v1/check/{check_id} \
  -H "X-API-Key: YOUR_API_KEY"
```

**Expected Output:**
- `sources_checked` should be > 0
- `matches` array should contain YouTube videos
- Each match should have `source_type: "youtube"` with title, URL, and timestamp

---

## **Problem 2: Web Article Search Setup**

### **NEW: Real-Time Web Article Search**

The system can now search the internet for articles in real-time! Set up Google Custom Search and/or Bing Search API for this feature.

### How to Set Up Web Article Search:

#### **Option A: Google Custom Search (Recommended)**

**Free Tier**: 100 searches/day
**Paid**: $5 per 1,000 queries after free tier

**Steps:**

1. **Create Google Cloud Project**:
   - Go to https://console.cloud.google.com/
   - Create a new project or select existing

2. **Enable Custom Search API**:
   - Navigate to "APIs & Services" → "Enable APIs and Services"
   - Search for "Custom Search API"
   - Click "Enable"

3. **Create API Key**:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "API Key"
   - Copy the API key

4. **Create Custom Search Engine**:
   - Go to https://programmablesearchengine.google.com/
   - Click "Add" to create a new search engine
   - **Sites to search**: Enter `*` (to search the entire web)
   - Click "Create"
   - Copy the **Search Engine ID** (starts with a number/letters like `017576662512468239146:omuauf_lfve`)

5. **Add to Environment**:
   ```bash
   # Add to .env file:
   GOOGLE_SEARCH_API_KEY=AIzaSyC-your-api-key-here
   GOOGLE_SEARCH_ENGINE_ID=your-search-engine-id-here
   ```

6. **Restart Application**

#### **Option B: Bing Search API**

**Free Tier**: 1,000 transactions/month (S1 tier)
**Paid**: Various pricing tiers available

**Steps:**

1. **Create Microsoft Azure Account**:
   - Go to https://portal.azure.com/
   - Sign up or sign in

2. **Create Bing Search Resource**:
   - Click "Create a resource"
   - Search for "Bing Search v7"
   - Click "Create"
   - Choose pricing tier (F1 = Free)
   - Create resource

3. **Get API Key**:
   - Navigate to your Bing Search resource
   - Go to "Keys and Endpoint"
   - Copy one of the keys

4. **Add to Environment**:
   ```bash
   # Add to .env file:
   BING_SEARCH_API_KEY=your-bing-api-key-here
   ```

5. **Restart Application**

#### **Best Practice: Use Both**

For maximum coverage, configure **both** Google and Bing:
- The system will use both engines simultaneously
- Results are combined and deduplicated
- Increases diversity of sources found
- More resilient if one API has issues

```bash
# In .env - Configure both for best results:
GOOGLE_SEARCH_API_KEY=your-google-key
GOOGLE_SEARCH_ENGINE_ID=your-engine-id
BING_SEARCH_API_KEY=your-bing-key
```

### **How Web Article Search Works:**

When you submit a similarity check:

1. **Extract Keywords**: System extracts top keywords from your article
2. **Search Web**: Queries Google and/or Bing for relevant articles
3. **Fetch Content**: Downloads article content from top 10 URLs
4. **Extract Text**: Uses newspaper3k + BeautifulSoup to extract clean article text
5. **Chunk & Embed**: Processes each web article into semantic chunks
6. **Compare**: Compares your article against web articles in real-time
7. **Cache**: Caches fetched articles for 24 hours (configurable)

### **Cost Estimates:**

**Google Custom Search:**
- Free tier: 100 searches/day = ~50 similarity checks/day
- After free tier: $5 per 1,000 queries = $0.005 per check

**Bing Search:**
- S1 (Free): 1,000 transactions/month = ~500 checks/month
- S2: 10,000 transactions/month = $7/month

**Typical Check Cost:**
- 1 search query per check
- ~10 article fetches per check
- ~2-4 seconds processing time
- **Total cost: $0.005 - $0.01 per check**

---

## **Problem 3: Local Article Corpus (Optional)**

### Why It's Failing:
- **No article corpus exists** → Nothing to search against
- The `./data/faiss_index` directory doesn't exist
- Vector store is empty

### How to Fix:

You have two options:

#### **Option A: Create Your Own Article Corpus (Recommended for Production)**

1. **Create a script to add articles** (`scripts/add_articles.py`):
```python
#!/usr/bin/env python3
"""Add articles to the corpus for similarity checking."""
import asyncio
from app.core.embeddings import get_embedding_generator
from app.core.vector_store import get_article_store, VectorMetadata
from app.core.chunking import TextChunker

async def add_article(title: str, url: str, article_text: str):
    """Add an article to the corpus."""
    # Initialize components
    embedder = get_embedding_generator()
    chunker = TextChunker(min_words=40, max_words=60, overlap_words=10)
    article_store = get_article_store()

    # Chunk the article
    chunks = chunker.chunk_text(article_text, normalize=True)

    # Generate embeddings
    chunk_texts = [chunk.text for chunk in chunks]
    embeddings = embedder.encode(chunk_texts, normalize=True)

    # Create metadata
    metadata_list = [
        VectorMetadata(
            source_id=url,
            source_type="article",
            chunk_index=i,
            chunk_text=chunk.text,
            title=title,
            identifier=url
        )
        for i, chunk in enumerate(chunks)
    ]

    # Add to store
    article_store.add_vectors(embeddings, metadata_list)
    article_store.save()

    print(f"✓ Added article: {title} ({len(chunks)} chunks)")

# Example usage
async def main():
    # Add your articles here
    await add_article(
        title="Understanding Machine Learning Basics",
        url="https://example.com/ml-basics",
        article_text="""
        Machine learning is a subset of artificial intelligence...
        [Your article text here - at least 100 words]
        """
    )

    await add_article(
        title="Deep Learning for NLP",
        url="https://example.com/deep-learning-nlp",
        article_text="""
        Natural language processing has been transformed by deep learning...
        [Your article text here - at least 100 words]
        """
    )

if __name__ == "__main__":
    asyncio.run(main())
```

2. **Run the script**:
```bash
python scripts/add_articles.py
```

#### **Option B: Use Test/Sample Articles (For Development)**

We can create a script to populate with sample tech articles for testing:

```bash
python scripts/seed_sample_articles.py
```

---

## **Testing After Setup**

### 1. Test YouTube + Web Articles Together:
Now with real-time web search, you don't need a local corpus!
```bash
curl -X POST http://localhost:8000/v1/check \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": "Artificial intelligence and machine learning are revolutionizing software development. Deep learning models enable natural language processing at scale.",
    "sources": ["articles", "youtube"]
  }'
```

### 2. Check the Results:
```bash
curl -X GET http://localhost:8000/v1/check/{check_id} \
  -H "X-API-Key: YOUR_API_KEY"
```

**Expected Results:**
```json
{
  "status": "completed",
  "sources_checked": 15,  // YouTube + Web articles
  "match_count": 5,
  "report": {
    "matches": [
      {
        "source_type": "youtube",
        "source_title": "Introduction to Machine Learning",
        "source_identifier": "https://youtube.com/watch?v=abc123",
        "similarity_score": 0.78
      },
      {
        "source_type": "article",
        "source_title": "Deep Learning in 2024",
        "source_identifier": "https://techblog.com/deep-learning",
        "similarity_score": 0.75,
        "snippet": "Deep learning models have revolutionized AI...",
        "source_metadata": {
          "source": "web_google"  // Shows it came from web search
        }
      },
      {
        "source_type": "article",
        "source_title": "Neural Networks Explained",
        "source_identifier": "https://medium.com/neural-nets",
        "similarity_score": 0.72,
        "source_metadata": {
          "source": "web_bing"  // From Bing search
        }
      }
    ]
  }
}
```

**Note**: Web article matches will include:
- `source_metadata.source`: Shows which search engine found it (`web_google`, `web_bing`, or `local_corpus`)
- `snippet`: Preview of the article content
- `source_identifier`: Full URL to the article

---

## **Debugging Search Issues**

### Check if YouTube API Key is Loaded:
```bash
# In Python shell or script:
from app.config import settings
print(f"YouTube API Key configured: {bool(settings.youtube_api_key)}")
```

### Check Article Corpus Size:
```bash
# Check if vector store exists:
ls -la ./data/faiss_index/

# Count articles in store:
python -c "
from app.core.vector_store import get_article_store
store = get_article_store()
print(f'Article vectors: {store.count()}')
"
```

### Monitor Logs During Search:
```bash
# Watch for errors:
docker-compose logs -f api worker

# Look for:
# - "YouTube API client not initialized" → API key issue
# - "No vectors in store" → Empty corpus
# - YouTube API errors → Quota/permissions issue
```

---

## **YouTube API Quota Limits**

- **Free tier**: 10,000 units/day
- **Video search**: 100 units per request
- **Video metadata**: 1 unit per request
- **Typical similarity check**: ~150-200 units (1 search + 5-10 metadata calls)

**Daily capacity**: ~50-60 similarity checks per day on free tier

To monitor quota:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" → "YouTube Data API v3"
3. View quota usage

---

## **Quick Start Checklist**

- [ ] Get YouTube API key from Google Cloud Console
- [ ] Add `YOUTUBE_API_KEY` to `.env` file
- [ ] Restart application
- [ ] Test YouTube search with curl
- [ ] Create article corpus (add at least 5-10 articles)
- [ ] Test article search
- [ ] Run full similarity check with both sources
- [ ] Verify `sources_checked > 0` and matches are returned

---

## **Still Having Issues?**

### YouTube Search Returns Empty:
- Check API key is correct (no spaces, complete key)
- Verify YouTube Data API v3 is enabled in Google Cloud
- Check quota hasn't been exceeded
- Look for error logs: `docker-compose logs worker`

### Article Search Returns Empty:
- Verify `./data/faiss_index/` directory exists
- Check vector store has data: `ls -la ./data/faiss_index/`
- Ensure articles were added successfully
- Check logs for vector store errors

### Both Sources Return 0 Results:
- Article text might not match any sources (try different topics)
- Similarity threshold might be too high (default: 0.65)
- Try with `"sensitivity": "low"` in request
