"""Data models for YouTube similarity detection."""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class TranscriptSegment(BaseModel):
    """A segment of video transcript with timing information."""

    text: str
    start: float = Field(..., description="Start time in seconds")
    duration: float = Field(..., description="Duration in seconds")

    @property
    def end(self) -> float:
        """End time of the segment."""
        return self.start + self.duration


class TranscriptChunk(BaseModel):
    """A processed chunk of transcript for embedding."""

    text: str
    start: float
    end: float
    video_id: str
    chunk_index: int


class VideoMetadata(BaseModel):
    """Metadata for a YouTube video."""

    video_id: str
    title: str
    channel_name: str
    duration_seconds: int
    url: str

    @property
    def youtube_url(self) -> str:
        """Full YouTube URL."""
        return f"https://www.youtube.com/watch?v={self.video_id}"


class SimilarityMatch(BaseModel):
    """A similarity match between article and video transcript."""

    video_id: str
    video_title: str
    channel_name: str
    video_url: str
    timestamp_start: float
    timestamp_end: float
    transcript_snippet: str = Field(..., max_length=300)
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    matched_chunks_count: int

    @property
    def timestamp_range(self) -> str:
        """Human-readable timestamp range."""
        start_min = int(self.timestamp_start // 60)
        start_sec = int(self.timestamp_start % 60)
        end_min = int(self.timestamp_end // 60)
        end_sec = int(self.timestamp_end % 60)
        return f"{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}"


class VideoSimilarityResult(BaseModel):
    """Aggregated similarity results for a single video."""

    video_id: str
    video_title: str
    channel_name: str
    video_url: str
    max_similarity: float
    matched_chunks_count: int
    coverage_percentage: float = Field(..., description="Percentage of video duration with matches")
    matches: List[SimilarityMatch]


class ArticleAnalysisRequest(BaseModel):
    """Request to analyze an article for YouTube similarities."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=100, max_length=50000)
    author: Optional[str] = None
    url: Optional[HttpUrl] = None


class ArticleAnalysisResponse(BaseModel):
    """Response containing similarity analysis results."""

    article_title: str
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    videos_analyzed: int
    matches_found: int
    results: List[VideoSimilarityResult]
    message: str = "Possible similarity to spoken content"
    keywords_extracted: List[str]


class KeywordExtractionResult(BaseModel):
    """Keywords and keyphrases extracted from article."""

    title_weighted_terms: List[str]
    named_entities: List[str]
    tfidf_phrases: List[str]
    all_keywords: List[str]
