from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.core.database import get_db
from app.models import Domain, LighthouseMetric, Alert
from app.schemas import DashboardSummary, LighthouseMetricResponse, AlertResponse
from app.services.auth import get_current_user
from app.models import User

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard summary for current user."""
    # Total domains
    total_result = await db.execute(
        select(func.count(Domain.id)).where(Domain.owner_id == current_user.id)
    )
    total_domains = total_result.scalar() or 0
    
    # Active domains
    active_result = await db.execute(
        select(func.count(Domain.id)).where(
            Domain.owner_id == current_user.id,
            Domain.is_active == True
        )
    )
    active_domains = active_result.scalar() or 0
    
    # Total checks (metrics)
    domain_ids_result = await db.execute(
        select(Domain.id).where(Domain.owner_id == current_user.id)
    )
    domain_ids = [row[0] for row in domain_ids_result.fetchall()]
    
    if domain_ids:
        checks_result = await db.execute(
            select(func.count(LighthouseMetric.id)).where(
                LighthouseMetric.domain_id.in_(domain_ids)
            )
        )
        total_checks = checks_result.scalar() or 0
        
        # Average performance score
        avg_result = await db.execute(
            select(func.avg(LighthouseMetric.performance_score)).where(
                LighthouseMetric.domain_id.in_(domain_ids)
            )
        )
        avg_performance = avg_result.scalar()
    else:
        total_checks = 0
        avg_performance = None
    
    # Unresolved alerts
    alerts_result = await db.execute(
        select(func.count(Alert.id)).where(
            Alert.domain_id.in_(domain_ids) if domain_ids else False,
            Alert.is_resolved == False
        )
    )
    alerts_count = alerts_result.scalar() or 0
    
    return DashboardSummary(
        total_domains=total_domains,
        active_domains=active_domains,
        total_checks=total_checks,
        alerts_count=alerts_count,
        avg_performance_score=round(avg_performance, 2) if avg_performance else None,
    )


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent alerts for current user's domains."""
    # Get user's domain IDs
    domain_ids_result = await db.execute(
        select(Domain.id).where(Domain.owner_id == current_user.id)
    )
    domain_ids = [row[0] for row in domain_ids_result.fetchall()]
    
    if not domain_ids:
        return []
    
    # Get alerts
    result = await db.execute(
        select(Alert)
        .where(Alert.domain_id.in_(domain_ids))
        .order_by(Alert.created_at.desc())
        .limit(limit)
    )
    alerts = result.scalars().all()
    
    return alerts
