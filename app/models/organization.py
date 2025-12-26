"""Organization model."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database import Base


class Organization(Base):
    """Organization/tenant model."""

    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)

    # Subscription tier
    tier = Column(String(50), default="free", nullable=False)  # free, starter, pro, enterprise

    # Privacy settings
    allow_corpus_inclusion = Column(Boolean, default=False, nullable=False)
    store_embeddings = Column(Boolean, default=False, nullable=False)

    # Usage limits
    monthly_check_limit = Column(Integer, default=100, nullable=False)
    current_month_checks = Column(Integer, default=0, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    api_keys = relationship("APIKey", back_populates="organization", cascade="all, delete-orphan")
    checks = relationship("Check", back_populates="organization", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization {self.name} ({self.tier})>"
