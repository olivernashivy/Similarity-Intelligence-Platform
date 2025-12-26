"""Usage tracking schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UsageStats(BaseModel):
    """Usage statistics for an organization."""

    current_month_checks: int = Field(..., ge=0, description="Checks used this month")
    monthly_check_limit: int = Field(..., ge=0, description="Monthly check limit")
    remaining_checks: int = Field(..., ge=0, description="Remaining checks this month")

    total_checks_all_time: int = Field(..., ge=0, description="Total checks ever")
    total_cost_all_time_usd: float = Field(..., ge=0.0, description="Total estimated cost")

    tier: str = Field(..., description="Subscription tier")
    period_start: datetime = Field(..., description="Current billing period start")
    period_end: datetime = Field(..., description="Current billing period end")


class UsageResponse(BaseModel):
    """Usage response."""

    organization_id: str
    stats: UsageStats

    class Config:
        from_attributes = True
