"""Check/similarity schemas."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class CheckCreate(BaseModel):
    """Request schema for creating a similarity check."""

    article_text: str = Field(
        ...,
        min_length=100,
        description="The article text to check for similarity"
    )

    language: str = Field(
        default="en",
        pattern="^[a-z]{2}$",
        description="Two-letter language code (ISO 639-1)"
    )

    sources: List[str] = Field(
        default=["articles", "youtube"],
        description="Sources to check against: articles, youtube"
    )

    sensitivity: str = Field(
        default="medium",
        pattern="^(low|medium|high)$",
        description="Sensitivity level for matching: low, medium, high"
    )

    store_embeddings: bool = Field(
        default=False,
        description="Whether to store embeddings for future use (requires opt-in)"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata for tracking purposes"
    )

    @field_validator("article_text")
    @classmethod
    def validate_article_length(cls, v: str) -> str:
        """Validate article is within word limit."""
        words = len(v.split())
        if words > 1500:  # MAX_ARTICLE_WORDS
            raise ValueError(f"Article exceeds maximum word limit of 1500 (got {words} words)")
        return v

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, v: List[str]) -> List[str]:
        """Validate source types."""
        valid_sources = {"articles", "youtube"}
        for source in v:
            if source not in valid_sources:
                raise ValueError(f"Invalid source type: {source}. Must be one of {valid_sources}")
        if not v:
            raise ValueError("At least one source must be specified")
        return v


class MatchedChunk(BaseModel):
    """Individual chunk match."""

    submission_text: str = Field(..., description="Text from submitted article")
    source_text: str = Field(..., description="Matching text from source")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")
    timestamp: Optional[str] = Field(None, description="Timestamp for YouTube matches (MM:SS format)")


class MatchResponse(BaseModel):
    """Similarity match response."""

    source_type: str = Field(..., description="Type of source: article or youtube")
    source_title: Optional[str] = Field(None, description="Title of the matching source")
    source_identifier: Optional[str] = Field(None, description="URL or video ID")

    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Overall similarity score")
    match_count: int = Field(..., ge=1, description="Number of matching chunks")
    max_chunk_similarity: float = Field(..., ge=0.0, le=1.0)
    avg_chunk_similarity: float = Field(..., ge=0.0, le=1.0)

    snippet: Optional[str] = Field(None, max_length=300, description="Short excerpt from source")
    explanation: Optional[str] = Field(None, description="Why this was flagged")
    risk_contribution: Optional[str] = Field(None, pattern="^(low|medium|high)$")

    matched_chunks: List[MatchedChunk] = Field(
        default_factory=list,
        max_length=5,
        description="Sample of matching chunks (max 5)"
    )

    class Config:
        from_attributes = True


class SimilarityReport(BaseModel):
    """Detailed similarity analysis report."""

    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Overall similarity score (0-100)"
    )

    risk_level: str = Field(
        ...,
        pattern="^(low|medium|high)$",
        description="Risk level: low, medium, high"
    )

    match_count: int = Field(..., ge=0, description="Total number of matches found")
    sources_checked: int = Field(..., ge=0, description="Number of sources checked")

    matches: List[MatchResponse] = Field(
        default_factory=list,
        description="Detailed match results"
    )

    summary: str = Field(..., description="Human-readable summary of findings")

    processing_time_seconds: Optional[float] = Field(None, ge=0.0)
    estimated_cost_usd: Optional[float] = Field(None, ge=0.0)


class CheckStatus(BaseModel):
    """Status of a similarity check job."""

    status: str = Field(
        ...,
        pattern="^(pending|processing|completed|failed|cancelled)$",
        description="Current job status"
    )

    progress: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Progress percentage (0-100)"
    )

    message: Optional[str] = Field(None, description="Status message")


class CheckResponse(BaseModel):
    """Response for a similarity check."""

    check_id: UUID = Field(..., description="Unique identifier for this check")
    status: str = Field(..., description="Job status")

    # Input metadata
    language: str
    word_count: int
    chunk_count: int

    # Results (only when completed)
    report: Optional[SimilarityReport] = Field(
        None,
        description="Similarity report (only available when status is 'completed')"
    )

    # Error info (only when failed)
    error_message: Optional[str] = Field(None, description="Error message if status is 'failed'")

    # Timestamps
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
