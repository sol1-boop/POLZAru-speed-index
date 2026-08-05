from celery import Task
from app.workers import celery_app
from app.core.database import async_session_maker
import asyncio


class SQLAlchemyTask(Task):
    """Base Celery task with database session."""
    
    _db = None
    
    @property
    def db(self):
        if self._db is None:
            self._db = async_session_maker()
        return self._db
    
    def after_return(self, *args, **kwargs):
        if self._db is not None:
            asyncio.run(self._db.close())
            self._db = None


@celery_app.task(base=SQLAlchemyTask, bind=True)
def run_lighthouse_audit_task(self, domain_id: int):
    """Celery task to run Lighthouse audit asynchronously."""
    from app.services.lighthouse_service import execute_lighthouse_audit
    
    try:
        result = asyncio.run(execute_lighthouse_audit(domain_id))
        return {"status": "success", "domain_id": domain_id, "result": result}
    except Exception as e:
        return {"status": "error", "domain_id": domain_id, "error": str(e)}


@celery_app.task(base=SQLAlchemyTask, bind=True)
def cleanup_old_metrics_task(self, days: int = 30):
    """Celery task to cleanup old metrics."""
    from sqlalchemy import delete
    from datetime import datetime, timedelta
    from app.models import LighthouseMetric
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    async def _cleanup():
        async with async_session_maker() as session:
            stmt = delete(LighthouseMetric).where(
                LighthouseMetric.checked_at < cutoff_date
            )
            await session.execute(stmt)
            await session.commit()
    
    asyncio.run(_cleanup())
    return {"status": "success", "cleaned_before": cutoff_date.isoformat()}
