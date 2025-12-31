"""Usage logging model."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class UsageLog(Base):
    """API usage tracking model."""

    __tablename__ = "usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    check_id = Column(UUID(as_uuid=True), ForeignKey("checks.id", ondelete="SET NULL"), nullable=True, index=True)

    # Request details
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)

    # Resource usage
    processing_time_ms = Column(Float, nullable=True)
    embeddings_generated = Column(Integer, default=0, nullable=False)
    vector_queries = Column(Integer, default=0, nullable=False)

    # Cost tracking
    estimated_cost_usd = Column(Float, nullable=True)

    # Additional metadata
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(50), nullable=True)
    log_metadata = Column(JSON, default=dict, nullable=False)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    organization = relationship("Organization", back_populates="usage_logs")
    check = relationship("Check")

    def __repr__(self):
        return f"<UsageLog {self.method} {self.endpoint} ({self.status_code})>"
