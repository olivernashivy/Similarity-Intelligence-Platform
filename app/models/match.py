"""Match model for similarity results."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class Match(Base):
    """Similarity match result."""

    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    check_id = Column(UUID(as_uuid=True), ForeignKey("checks.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True, index=True)

    # Match details
    source_type = Column(String(50), nullable=False)  # article, youtube
    source_title = Column(String(500), nullable=True)
    source_identifier = Column(String(255), nullable=True)  # URL, video ID, etc.

    # Similarity metrics
    similarity_score = Column(Float, nullable=False)  # 0.0 - 1.0
    match_count = Column(Integer, default=1, nullable=False)  # Number of matching chunks
    max_chunk_similarity = Column(Float, nullable=False)
    avg_chunk_similarity = Column(Float, nullable=False)

    # Match context
    matched_chunks = Column(JSON, default=list, nullable=False)
    # Format: [{"submission_text": "...", "source_text": "...", "score": 0.95, "timestamp": "..."}, ...]

    # Explanation
    snippet = Column(Text, nullable=True)  # Short excerpt from source (≤300 chars)
    explanation = Column(Text, nullable=True)  # Why this was flagged

    # Risk assessment
    risk_contribution = Column(String(20), nullable=True)  # low, medium, high

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    check = relationship("Check", back_populates="matches")
    source = relationship("Source")

    def __repr__(self):
        return f"<Match check={self.check_id} score={self.similarity_score:.2f}>"
