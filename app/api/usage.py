"""Usage tracking endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.organization import Organization
from app.models.check import Check
from app.schemas.usage import UsageResponse, UsageStats
from app.api.dependencies import get_current_organization
from app.utils.helpers import get_current_billing_period

router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get("", response_model=UsageResponse)
async def get_usage_stats(
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
):
    """
    Get usage statistics for your organization.

    Returns information about:
    - Current month's usage
    - Remaining checks
    - Total lifetime usage
    - Estimated costs
    """
    # Get current billing period
    period_start, period_end = get_current_billing_period()

    # Calculate remaining checks
    remaining_checks = max(
        0,
        organization.monthly_check_limit - organization.current_month_checks
    )

    # Get total checks all time
    total_checks_result = await db.execute(
        select(func.count(Check.id))
        .where(Check.organization_id == organization.id)
        .where(Check.status == "completed")
    )
    total_checks_all_time = total_checks_result.scalar() or 0

    # Calculate total cost
    total_cost_result = await db.execute(
        select(func.sum(Check.estimated_cost_usd))
        .where(Check.organization_id == organization.id)
        .where(Check.status == "completed")
    )
    total_cost_all_time = total_cost_result.scalar() or 0.0

    # Build stats
    stats = UsageStats(
        current_month_checks=organization.current_month_checks,
        monthly_check_limit=organization.monthly_check_limit,
        remaining_checks=remaining_checks,
        total_checks_all_time=total_checks_all_time,
        total_cost_all_time_usd=round(total_cost_all_time, 4),
        tier=organization.tier,
        period_start=period_start,
        period_end=period_end
    )

    return UsageResponse(
        organization_id=str(organization.id),
        stats=stats
    )
