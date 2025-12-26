"""Check/job model."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, Float, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class Check(Base):
    """Similarity check job model."""

    __tablename__ = "checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Status
    status = Column(String(50), default="pending", nullable=False, index=True)
    # pending, processing, completed, failed, cancelled

    # Input metadata
    language = Column(String(10), default="en", nullable=False)
    word_count = Column(Integer, nullable=False)
    chunk_count = Column(Integer, default=0, nullable=False)

    # Check options
    check_articles = Column(Boolean, default=True, nullable=False)
    check_youtube = Column(Boolean, default=True, nullable=False)
    sensitivity = Column(String(20), default="medium", nullable=False)  # low, medium, high
    store_embeddings = Column(Boolean, default=False, nullable=False)

    # Results
    similarity_score = Column(Float, nullable=True)  # 0-100
    risk_level = Column(String(20), nullable=True)  # low, medium, high
    match_count = Column(Integer, default=0, nullable=False)

    # Processing metadata
    sources_checked = Column(Integer, default=0, nullable=False)
    processing_time_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    # Cost tracking
    estimated_cost_usd = Column(Float, nullable=True)

    # Additional metadata
    metadata = Column(JSON, default=dict, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # TTL for auto-deletion

    # Relationships
    organization = relationship("Organization", back_populates="checks")
    matches = relationship("Match", back_populates="check", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Check {self.id} ({self.status})>"

    @property
    def is_complete(self) -> bool:
        """Check if job is complete."""
        return self.status in ["completed", "failed", "cancelled"]

    @property
    def duration_seconds(self) -> float:
        """Calculate job duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0
