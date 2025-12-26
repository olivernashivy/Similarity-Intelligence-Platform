"""Cache service for storing transcript embeddings using Redis."""

import logging
import json
import pickle
from typing import Optional, List, Any
import numpy as np
import redis
from redis.exceptions import RedisError

from ..config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Manages caching of transcript embeddings and metadata.

    Uses Redis for:
    - Caching video transcript embeddings by video ID
    - Storing processed transcript chunks
    - TTL-based expiration
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None
    ):
        """
        Initialize cache service.

        Args:
            host: Redis host (uses settings if not provided)
            port: Redis port (uses settings if not provided)
            db: Redis database number (uses settings if not provided)
            password: Redis password (uses settings if not provided)
        """
        self.enabled = settings.cache_enabled
        self.ttl = settings.cache_ttl_seconds

        if not self.enabled:
            logger.info("Cache is disabled")
            self.client = None
            return

        # Connection parameters
        host = host or settings.redis_host
        port = port or settings.redis_port
        db = db or settings.redis_db
        password = password or settings.redis_password

        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=False,  # We'll handle encoding ourselves
                socket_connect_timeout=5,
                socket_timeout=5
            )

            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis at {host}:{port}")

        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning("Cache will be disabled")
            self.enabled = False
            self.client = None

    def _make_key(self, prefix: str, identifier: str) -> str:
        """
        Create cache key with prefix.

        Args:
            prefix: Key prefix
            identifier: Unique identifier

        Returns:
            Cache key
        """
        return f"youtube_similarity:{prefix}:{identifier}"

    def get_video_embeddings(
        self,
        video_id: str
    ) -> Optional[List[np.ndarray]]:
        """
        Get cached embeddings for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            List of embedding vectors or None if not cached
        """
        if not self.enabled or not self.client:
            return None

        key = self._make_key("embeddings", video_id)

        try:
            data = self.client.get(key)
            if data:
                embeddings = pickle.loads(data)
                logger.debug(f"Cache hit for video {video_id} embeddings")
                return embeddings

        except Exception as e:
            logger.error(f"Error retrieving cached embeddings: {e}")

        return None

    def set_video_embeddings(
        self,
        video_id: str,
        embeddings: List[np.ndarray]
    ) -> bool:
        """
        Cache embeddings for a video.

        Args:
            video_id: YouTube video ID
            embeddings: List of embedding vectors

        Returns:
            True if successfully cached
        """
        if not self.enabled or not self.client:
            return False

        key = self._make_key("embeddings", video_id)

        try:
            data = pickle.dumps(embeddings)
            self.client.setex(key, self.ttl, data)
            logger.debug(f"Cached embeddings for video {video_id}")
            return True

        except Exception as e:
            logger.error(f"Error caching embeddings: {e}")
            return False

    def get_video_chunks(
        self,
        video_id: str
    ) -> Optional[List[dict]]:
        """
        Get cached transcript chunks for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            List of chunk dictionaries or None if not cached
        """
        if not self.enabled or not self.client:
            return None

        key = self._make_key("chunks", video_id)

        try:
            data = self.client.get(key)
            if data:
                chunks = json.loads(data)
                logger.debug(f"Cache hit for video {video_id} chunks")
                return chunks

        except Exception as e:
            logger.error(f"Error retrieving cached chunks: {e}")

        return None

    def set_video_chunks(
        self,
        video_id: str,
        chunks: List[dict]
    ) -> bool:
        """
        Cache transcript chunks for a video.

        Args:
            video_id: YouTube video ID
            chunks: List of chunk dictionaries

        Returns:
            True if successfully cached
        """
        if not self.enabled or not self.client:
            return False

        key = self._make_key("chunks", video_id)

        try:
            data = json.dumps(chunks)
            self.client.setex(key, self.ttl, data)
            logger.debug(f"Cached chunks for video {video_id}")
            return True

        except Exception as e:
            logger.error(f"Error caching chunks: {e}")
            return False

    def invalidate_video(self, video_id: str) -> bool:
        """
        Invalidate all cached data for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            True if successfully invalidated
        """
        if not self.enabled or not self.client:
            return False

        try:
            keys = [
                self._make_key("embeddings", video_id),
                self._make_key("chunks", video_id)
            ]
            self.client.delete(*keys)
            logger.info(f"Invalidated cache for video {video_id}")
            return True

        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return False

    def clear_all(self) -> bool:
        """
        Clear all cached data (use with caution).

        Returns:
            True if successfully cleared
        """
        if not self.enabled or not self.client:
            return False

        try:
            # Find all keys with our prefix
            pattern = self._make_key("*", "*")
            keys = self.client.keys(pattern)

            if keys:
                self.client.delete(*keys)
                logger.warning(f"Cleared {len(keys)} cached entries")

            return True

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self.enabled or not self.client:
            return {"enabled": False}

        try:
            info = self.client.info()
            pattern = self._make_key("*", "*")
            key_count = len(self.client.keys(pattern))

            return {
                "enabled": True,
                "connected": True,
                "total_keys": key_count,
                "used_memory": info.get("used_memory_human", "N/A"),
                "ttl_hours": settings.cache_ttl_hours
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "enabled": True,
                "connected": False,
                "error": str(e)
            }
