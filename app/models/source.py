"""Source model for reference content."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class Source(Base):
    """Reference source model (articles, YouTube videos)."""

    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Source identification
    source_type = Column(String(50), nullable=False, index=True)  # article, youtube
    external_id = Column(String(255), nullable=True, index=True)  # URL, video ID, etc.

    # Content metadata
    title = Column(String(500), nullable=True)
    author = Column(String(255), nullable=True)
    language = Column(String(10), default="en", nullable=False)
    word_count = Column(Integer, nullable=True)

    # YouTube-specific
    video_duration_seconds = Column(Integer, nullable=True)
    channel_name = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=True)

    # Processing metadata
    chunk_count = Column(Integer, default=0, nullable=False)
    embedding_model = Column(String(100), nullable=True)

    # Privacy & lifecycle
    is_public = Column(Boolean, default=True, nullable=False)
    organization_id = Column(UUID(as_uuid=True), nullable=True)  # If private source

    # Additional metadata
    metadata = Column(JSON, default=dict, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Composite indexes
    __table_args__ = (
        Index('idx_source_type_external_id', 'source_type', 'external_id'),
        Index('idx_source_type_language', 'source_type', 'language'),
    )

    def __repr__(self):
        return f"<Source {self.source_type}: {self.title or self.external_id}>"
