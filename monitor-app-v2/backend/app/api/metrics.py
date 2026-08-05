from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.core.database import get_db
from app.models import LighthouseMetric
from app.schemas import LighthouseMetricResponse

router = APIRouter(prefix="/metrics", tags=["Metrics"])


async def get_current_user_id():
    """Placeholder for getting current user from JWT token."""
    return 1


@router.get("/", response_model=List[LighthouseMetricResponse])
async def get_all_metrics(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Get latest metrics for all user's domains."""
    from app.models import Domain
    
    result = await db.execute(
        select(LighthouseMetric)
        .join(Domain)
        .where(Domain.owner_id == current_user_id)
        .order_by(LighthouseMetric.checked_at.desc())
        .limit(limit)
    )
    metrics = result.scalars().all()
    return metrics


@router.get("/average")
async def get_average_metrics(
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Get average metrics across all domains."""
    from app.models import Domain
    from sqlalchemy import func
    
    result = await db.execute(
        select(
            func.avg(LighthouseMetric.performance_score),
            func.avg(LighthouseMetric.accessibility_score),
            func.avg(LighthouseMetric.best_practices_score),
            func.avg(LighthouseMetric.seo_score),
        )
        .join(Domain)
        .where(Domain.owner_id == current_user_id)
    )
    
    row = result.first()
    
    return {
        "performance": round(row[0], 2) if row[0] else 0,
        "accessibility": round(row[1], 2) if row[1] else 0,
        "best_practices": round(row[2], 2) if row[2] else 0,
        "seo": round(row[3], 2) if row[3] else 0,
    }
