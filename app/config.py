"""Application configuration using Pydantic settings."""
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "Similarity Intelligence Platform"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    # API
    api_v1_prefix: str = "/v1"
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/similarity_platform"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis & Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Security
    secret_key: str = Field(..., min_length=32)
    api_key_hash_algorithm: str = "bcrypt"
    rate_limit_per_minute: int = 60

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    vector_store_path: str = "./data/faiss_index"

    # YouTube API
    youtube_api_key: str = ""

    # Processing Limits
    max_article_words: int = 1500
    max_chunk_words: int = 60
    min_chunk_words: int = 40
    chunk_overlap_words: int = 10
    max_candidate_sources: int = 100
    max_youtube_videos: int = 5
    max_video_duration_minutes: int = 30

    # Similarity Thresholds
    similarity_threshold_low: float = 0.65
    similarity_threshold_medium: float = 0.75
    similarity_threshold_high: float = 0.85

    # Cost Control
    target_cost_per_check_usd: float = 0.004
    embedding_cache_ttl_hours: int = 24
    submission_embedding_ttl_days: int = 7

    # Privacy
    store_raw_articles: bool = False
    snippet_max_length: int = 300
    auto_delete_submissions: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"


# Global settings instance
settings = Settings()
