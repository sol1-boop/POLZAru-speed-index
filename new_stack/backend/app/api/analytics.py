"""
API эндпоинты для аналитики и графиков.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models.domain import Domain
from app.models.metric import LighthouseMetric
from app.services.trend_analyzer import TrendAnalyzer
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/domains/{domain_id}/trends")
async def get_domain_trends(
    domain_id: int,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получает исторические данные метрик для построения графиков.
    Возвращает данные за последние N дней.
    """
    # Проверка прав доступа к домену
    result = await db.execute(
        select(Domain).where(Domain.id == domain_id, Domain.owner_id == current_user.id)
    )
    domain = result.scalar_one_or_none()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found or access denied")

    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(LighthouseMetric)
        .where(
            LighthouseMetric.domain_id == domain_id,
            LighthouseMetric.created_at >= cutoff_date
        )
        .order_by(LighthouseMetric.created_at.asc())
    )
    metrics = result.scalars().all()

    # Форматирование данных для графиков (Chart.js / Recharts)
    chart_data = []
    for m in metrics:
        chart_data.append({
            "date": m.created_at.isoformat(),
            "performance": m.performance_score,
            "accessibility": m.accessibility_score,
            "best_practices": m.best_practices_score,
            "seo": m.seo_score,
            "lcp": m.largest_contentful_paint,
            "fid": m.first_input_delay,
            "cls": m.cumulative_layout_shift,
            "fcp": m.first_contentful_paint
        })

    return {
        "domain": domain.url,
        "period_days": days,
        "data_points": len(chart_data),
        "metrics": chart_data
    }

@router.get("/domains/{domain_id}/anomalies")
async def detect_anomalies(
    domain_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Анализирует последние метрики на предмет аномалий (умные алерты).
    """
    # Получаем последние 10 замеров
    result = await db.execute(
        select(LighthouseMetric)
        .where(LighthouseMetric.domain_id == domain_id)
        .order_by(LighthouseMetric.created_at.desc())
        .limit(10)
    )
    metrics = result.scalars().all()

    if len(metrics) < 4:
        return {"anomalies": [], "message": "Недостаточно данных для анализа"}

    # Конвертируем в dict для анализатора
    history = [
        {
            "largest_contentful_paint": m.largest_contentful_paint,
            "cumulative_layout_shift": m.cumulative_layout_shift,
            "first_contentful_paint": m.first_contentful_paint
        }
        for m in reversed(metrics) # Сортируем от старых к новым
    ]

    anomalies = []
    
    # Проверка LCP (порог 500мс)
    if TrendAnalyzer.check_degradation_streak(history, "largest_contentful_paint", 500.0):
        anomalies.append({
            "metric": "LCP",
            "type": "degradation_streak",
            "message": TrendAnalyzer.generate_alert_message("Domain", "LCP", "ухудшения")
        })

    # Проверка CLS (порог 0.05)
    if TrendAnalyzer.check_degradation_streak(history, "cumulative_layout_shift", 0.05):
        anomalies.append({
            "metric": "CLS",
            "type": "degradation_streak",
            "message": TrendAnalyzer.generate_alert_message("Domain", "CLS", "ухудшения")
        })

    return {
        "domain_id": domain_id,
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies
    }
