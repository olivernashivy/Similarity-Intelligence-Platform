#!/usr/bin/env python3
"""Check if search sources are properly configured."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.core.vector_store import get_article_store, get_youtube_store
from app.core.embeddings import get_embedding_generator


def check_youtube_setup():
    """Check if YouTube API is configured."""
    print("\n" + "="*80)
    print("YOUTUBE SEARCH CONFIGURATION")
    print("="*80)

    if settings.youtube_api_key:
        print("✅ YouTube API Key: CONFIGURED")
        print(f"   Key prefix: {settings.youtube_api_key[:20]}...")
        print(f"   Max videos per search: {settings.max_youtube_videos}")
        print(f"   Max video duration: {settings.max_video_duration_minutes} minutes")

        # Try to initialize client
        try:
            from app.core.youtube import YouTubeTranscriptFetcher
            fetcher = YouTubeTranscriptFetcher()
            if fetcher.youtube_client:
                print("✅ YouTube API Client: INITIALIZED")
                return True
            else:
                print("❌ YouTube API Client: FAILED TO INITIALIZE")
                print("   Check if your API key is valid")
                return False
        except Exception as e:
            print(f"❌ YouTube API Client: ERROR - {e}")
            return False
    else:
        print("❌ YouTube API Key: NOT CONFIGURED")
        print("\n📝 To fix:")
        print("   1. Get API key from: https://console.cloud.google.com/")
        print("   2. Enable YouTube Data API v3")
        print("   3. Add to .env file: YOUTUBE_API_KEY=your-key-here")
        print("   4. Restart the application")
        print("\n   See SETUP_SEARCH_SOURCES.md for detailed instructions")
        return False


def check_article_corpus():
    """Check if article corpus is configured."""
    print("\n" + "="*80)
    print("ARTICLE CORPUS CONFIGURATION")
    print("="*80)

    try:
        article_store = get_article_store()
        count = article_store.count()

        if count > 0:
            print(f"✅ Article Corpus: {count} vectors indexed")
            print(f"   Vector store path: {settings.vector_store_path}")
            print(f"   Embedding model: {settings.embedding_model}")
            print(f"   Embedding dimension: {settings.embedding_dimension}")
            return True
        else:
            print("❌ Article Corpus: EMPTY (0 vectors)")
            print(f"   Vector store path: {settings.vector_store_path}")
            print("\n📝 To fix:")
            print("   1. Run: python scripts/seed_sample_articles.py")
            print("   2. Or add your own articles using scripts/add_article.py")
            print("\n   See SETUP_SEARCH_SOURCES.md for detailed instructions")
            return False

    except Exception as e:
        print(f"❌ Article Corpus: ERROR - {e}")
        print(f"   Vector store path: {settings.vector_store_path}")
        print("\n📝 To fix:")
        print("   1. Create the vector store directory")
        print("   2. Run: python scripts/seed_sample_articles.py")
        return False


def check_embeddings():
    """Check if embedding model is working."""
    print("\n" + "="*80)
    print("EMBEDDING MODEL")
    print("="*80)

    try:
        embedder = get_embedding_generator()
        print(f"✅ Embedding Model: {settings.embedding_model}")
        print(f"   Dimension: {settings.embedding_dimension}")

        # Test embedding generation
        test_text = ["This is a test sentence."]
        embeddings = embedder.encode(test_text, normalize=True)
        print(f"✅ Test Embedding: Generated successfully ({embeddings.shape})")
        return True

    except Exception as e:
        print(f"❌ Embedding Model: ERROR - {e}")
        print("\n📝 To fix:")
        print("   1. Install sentence-transformers: pip install sentence-transformers")
        print("   2. Download model will happen automatically on first run")
        return False


def check_celery_worker():
    """Check if Celery worker is running."""
    print("\n" + "="*80)
    print("CELERY WORKER (for async processing)")
    print("="*80)

    try:
        from app.tasks.celery_app import celery_app

        # Try to ping workers
        inspect = celery_app.control.inspect()
        stats = inspect.stats()

        if stats:
            worker_count = len(stats)
            print(f"✅ Celery Workers: {worker_count} worker(s) active")
            for worker_name in stats.keys():
                print(f"   - {worker_name}")
            return True
        else:
            print("❌ Celery Workers: NO WORKERS FOUND")
            print("\n📝 To fix:")
            print("   1. Start Celery worker: celery -A app.tasks.celery_app worker --loglevel=info")
            print("   2. Or using Docker: docker-compose up -d worker")
            return False

    except Exception as e:
        print(f"⚠️  Celery Workers: CANNOT CHECK - {e}")
        print("   (This is normal if running without Celery)")
        return None


def main():
    """Run all checks."""
    print("\n" + "="*80)
    print("SIMILARITY SEARCH SETUP DIAGNOSTIC")
    print("="*80)

    results = {
        "YouTube API": check_youtube_setup(),
        "Article Corpus": check_article_corpus(),
        "Embedding Model": check_embeddings(),
        "Celery Worker": check_celery_worker()
    }

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    configured_count = sum(1 for v in results.values() if v is True)
    total_count = sum(1 for v in results.values() if v is not None)

    for component, status in results.items():
        if status is True:
            print(f"✅ {component}")
        elif status is False:
            print(f"❌ {component}")
        else:
            print(f"⚠️  {component} (optional)")

    print(f"\n{configured_count}/{total_count} required components configured")

    # Overall status
    print("\n" + "="*80)
    if results["YouTube API"] or results["Article Corpus"]:
        if results["YouTube API"] and results["Article Corpus"]:
            print("🎉 EXCELLENT! Both YouTube and Article search are configured!")
            print("   You can search both sources simultaneously.")
        elif results["YouTube API"]:
            print("✅ PARTIAL: YouTube search is ready, but no article corpus.")
            print("   Searches will only check YouTube videos.")
            print("   Run: python scripts/seed_sample_articles.py")
        else:
            print("✅ PARTIAL: Article corpus is ready, but no YouTube API.")
            print("   Searches will only check against articles.")
            print("   Add YouTube API key to .env file")
    else:
        print("❌ NOT READY: Neither YouTube nor Article search is configured!")
        print("   Searches will return 0 sources checked.")
        print("\n   QUICK FIX:")
        print("   1. Get YouTube API key: https://console.cloud.google.com/")
        print("   2. Add to .env: YOUTUBE_API_KEY=your-key")
        print("   3. Run: python scripts/seed_sample_articles.py")
        print("   4. Restart application")

    print("="*80)
    print("\n📚 For detailed setup instructions, see: SETUP_SEARCH_SOURCES.md\n")


if __name__ == "__main__":
    main()
