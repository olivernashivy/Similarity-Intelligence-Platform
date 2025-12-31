"""Similarity check endpoints."""
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.organization import Organization
from app.models.check import Check
from app.models.match import Match
from app.schemas.check import (
    CheckCreate,
    CheckResponse,
    SimilarityReport,
    MatchResponse,
    MatchedChunk
)
from app.api.dependencies import get_current_organization
from app.utils.helpers import calculate_ttl_expiry

router = APIRouter(prefix="/check", tags=["Similarity Checks"])


@router.post("", response_model=CheckResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_similarity_check(
    request: CheckCreate,
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit an article for similarity checking.

    This endpoint creates an async job and returns immediately with a job ID.
    Use GET /check/{job_id} to retrieve results.

    **Cost**: ~$0.004 per check

    **Processing time**: 15-30 seconds average
    """
    # Check monthly quota
    if organization.current_month_checks >= organization.monthly_check_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly check limit ({organization.monthly_check_limit}) exceeded"
        )

    # Count words
    word_count = len(request.article_text.split())

    # Create check record
    check = Check(
        organization_id=organization.id,
        status="pending",
        language=request.language,
        word_count=word_count,
        check_articles="articles" in request.sources,
        check_youtube="youtube" in request.sources,
        sensitivity=request.sensitivity,
        store_embeddings=request.store_embeddings and organization.allow_corpus_inclusion,
        check_metadata=request.metadata or {},
        expires_at=calculate_ttl_expiry(days=7)
    )

    db.add(check)

    # Increment usage counter
    organization.current_month_checks += 1

    await db.commit()
    await db.refresh(check)

    # Queue Celery task
    from app.tasks.similarity_check import process_similarity_check
    process_similarity_check.delay(str(check.id), request.article_text)

    # Return response
    return CheckResponse(
        check_id=check.id,
        status=check.status,
        language=check.language,
        word_count=check.word_count,
        chunk_count=check.chunk_count,
        created_at=check.created_at,
        started_at=check.started_at,
        completed_at=check.completed_at
    )


@router.get("/{check_id}", response_model=CheckResponse)
async def get_similarity_check(
    check_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve results for a similarity check.

    Returns the current status and results (if completed).
    """
    # Get check
    result = await db.execute(
        select(Check)
        .where(Check.id == check_id)
        .where(Check.organization_id == organization.id)
    )
    check = result.scalar_one_or_none()

    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check not found"
        )

    # Build response
    response_data = {
        "check_id": check.id,
        "status": check.status,
        "language": check.language,
        "word_count": check.word_count,
        "chunk_count": check.chunk_count,
        "created_at": check.created_at,
        "started_at": check.started_at,
        "completed_at": check.completed_at,
        "error_message": check.error_message
    }

    # If completed, include full report
    if check.status == "completed":
        # Get matches
        matches_result = await db.execute(
            select(Match)
            .where(Match.check_id == check.id)
            .order_by(Match.similarity_score.desc())
        )
        matches = matches_result.scalars().all()

        # Build match responses
        match_responses = []
        for match in matches:
            # Parse matched chunks
            matched_chunks = [
                MatchedChunk(**chunk) for chunk in match.matched_chunks[:5]
            ]

            match_responses.append(
                MatchResponse(
                    source_type=match.source_type,
                    source_title=match.source_title,
                    source_identifier=match.source_identifier,
                    similarity_score=match.similarity_score,
                    match_count=match.match_count,
                    max_chunk_similarity=match.max_chunk_similarity,
                    avg_chunk_similarity=match.avg_chunk_similarity,
                    snippet=match.snippet,
                    explanation=match.explanation,
                    risk_contribution=match.risk_contribution,
                    matched_chunks=matched_chunks
                )
            )

        # Generate summary
        summary = _generate_summary(check, matches)

        # Build report
        report = SimilarityReport(
            similarity_score=check.similarity_score or 0.0,
            risk_level=check.risk_level or "low",
            match_count=check.match_count,
            sources_checked=check.sources_checked,
            matches=match_responses,
            summary=summary,
            processing_time_seconds=check.processing_time_seconds,
            estimated_cost_usd=check.estimated_cost_usd
        )

        response_data["report"] = report

    return CheckResponse(**response_data)


def _generate_summary(check: Check, matches: list) -> str:
    """Generate human-readable summary."""
    if check.risk_level == "low":
        return (
            f"Analysis complete. Your content shows low similarity to existing sources. "
            f"Found {check.match_count} minor matches across {check.sources_checked} sources checked."
        )
    elif check.risk_level == "medium":
        return (
            f"Analysis complete. Your content shows moderate similarity to existing sources. "
            f"Found {check.match_count} matches across {check.sources_checked} sources. "
            f"Review the highlighted sections for editorial considerations."
        )
    else:  # high
        return (
            f"Analysis complete. Your content shows high similarity to existing sources. "
            f"Found {check.match_count} significant matches across {check.sources_checked} sources. "
            f"We recommend reviewing these matches carefully before publication."
        )
