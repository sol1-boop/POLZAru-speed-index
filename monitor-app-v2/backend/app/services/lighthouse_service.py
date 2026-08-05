from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Domain, LighthouseMetric
from app.workers.tasks import run_lighthouse_audit_task
import logging

logger = logging.getLogger(__name__)


async def run_lighthouse_audit(db: AsyncSession, domain_id: int):
    """Trigger a Lighthouse audit for a domain (queues Celery task)."""
    
    # Get domain to verify it exists
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()
    
    if not domain:
        logger.error(f"Domain {domain_id} not found")
        return None
    
    # Queue the audit task
    task = run_lighthouse_audit_task.delay(domain_id)
    
    logger.info(f"Lighthouse audit queued for domain {domain_id}, task_id: {task.id}")
    
    return {"task_id": task.id, "status": "queued"}


async def execute_lighthouse_audit(domain_id: int):
    """Execute Lighthouse audit (called from Celery task)."""
    # This will be implemented with actual Lighthouse logic
    # For now, return mock data
    from datetime import datetime
    
    # Mock metrics - in real implementation, this would run Chrome/Lighthouse
    mock_metrics = {
        "performance_score": 85.0,
        "accessibility_score": 92.0,
        "best_practices_score": 88.0,
        "seo_score": 95.0,
        "pwa_score": 50.0,
        "first_contentful_paint": 1200.0,
        "largest_contentful_paint": 2500.0,
        "time_to_interactive": 3000.0,
        "total_blocking_time": 150.0,
        "cumulative_layout_shift": 0.05,
    }
    
    # Save to database
    async with AsyncSession() as session:
        metric = LighthouseMetric(
            domain_id=domain_id,
            **mock_metrics,
            report_url=None  # Would contain URL to full report
        )
        
        session.add(metric)
        await session.commit()
        await session.refresh(metric)
        
        logger.info(f"Audit completed for domain {domain_id}, performance: {mock_metrics['performance_score']}")
        
        return {
            "id": metric.id,
            "metrics": mock_metrics,
            "checked_at": metric.checked_at.isoformat()
        }
