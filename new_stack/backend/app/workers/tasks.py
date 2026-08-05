import asyncio
from celery import shared_task
from loguru import logger
from app.services.lighthouse import run_lighthouse_audit
from app.core.database import async_session_maker
from app.models import LighthouseMetric, Domain
from sqlalchemy import select


@shared_task(bind=True, max_retries=3)
def run_lighthouse_check(self, domain_id: int, url: str):
    """Celery task to run Lighthouse audit for a domain."""
    try:
        logger.info(f"Starting Lighthouse check for domain {domain_id}: {url}")
        
        # Run synchronous lighthouse in thread pool
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            metrics_data = loop.run_until_complete(run_lighthouse_audit(url))
        finally:
            loop.close()
        
        # Save results to database
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(save_metrics(domain_id, metrics_data))
        finally:
            loop.close()
        
        logger.info(f"Lighthouse check completed for domain {domain_id}")
        return {"status": "success", "domain_id": domain_id}
    
    except Exception as exc:
        logger.error(f"Lighthouse check failed for domain {domain_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


async def save_metrics(domain_id: int, metrics_data: dict):
    """Save lighthouse metrics to database."""
    async with async_session_maker() as session:
        metric = LighthouseMetric(
            domain_id=domain_id,
            performance_score=metrics_data.get("performance_score"),
            accessibility_score=metrics_data.get("accessibility_score"),
            best_practices_score=metrics_data.get("best_practices_score"),
            seo_score=metrics_data.get("seo_score"),
            pwa_score=metrics_data.get("pwa_score"),
            first_contentful_paint=metrics_data.get("first_contentful_paint"),
            largest_contentful_paint=metrics_data.get("largest_contentful_paint"),
            total_blocking_time=metrics_data.get("total_blocking_time"),
            cumulative_layout_shift=metrics_data.get("cumulative_layout_shift"),
            speed_index=metrics_data.get("speed_index"),
            report_url=metrics_data.get("report_url"),
            screenshot_path=metrics_data.get("screenshot_path"),
        )
        session.add(metric)
        await session.commit()


@shared_task
def check_domain_periodic():
    """Scheduled task to check all active domains."""
    logger.info("Running periodic domain checks")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_get_active_domains_and_queue())
    finally:
        loop.close()


async def _get_active_domains_and_queue():
    """Get active domains and queue lighthouse checks."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Domain).where(Domain.is_active == True)
        )
        domains = result.scalars().all()
        
        for domain in domains:
            run_lighthouse_check.delay(domain.id, domain.url)
