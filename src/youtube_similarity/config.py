"""Configuration management for YouTube similarity detection."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # YouTube API Configuration
    youtube_api_key: str = ""

    # OpenAI Configuration
    openai_api_key: str = ""

    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # Similarity Detection Settings
    max_videos_per_check: int = 10
    max_video_duration_minutes: int = 20
    similarity_threshold: float = 0.80
    chunk_size_words: int = 50
    max_transcript_length: int = 10000

    # Cache Settings
    cache_enabled: bool = True
    cache_ttl_hours: int = 24

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    # Embedding Model
    embedding_model: str = "text-embedding-3-small"

    @property
    def cache_ttl_seconds(self) -> int:
        """Convert cache TTL from hours to seconds."""
        return self.cache_ttl_hours * 3600

    @property
    def max_video_duration_seconds(self) -> int:
        """Convert max video duration from minutes to seconds."""
        return self.max_video_duration_minutes * 60


# Global settings instance
settings = Settings()
