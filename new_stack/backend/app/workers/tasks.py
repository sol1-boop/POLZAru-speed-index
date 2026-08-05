import asyncio
from typing import Dict, Any, Optional
from celery import shared_task
from loguru import logger
from app.services.lighthouse_runner import LighthouseRunner
from app.services.budget_service import BudgetService
from app.services.telegram_service import get_telegram_service
from app.services.metrics_parser import MetricsParser
from app.core.database import async_session_maker
from app.models.domain import Domain
from app.models.metric import Metric
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime


@shared_task(bind=True, max_retries=3)
def run_lighthouse_audit_task(self, domain_id: int, url: str, mobile: bool = True):
    """Celery task to run Lighthouse audit for a domain."""
    try:
        logger.info(f"Starting Lighthouse check for domain {domain_id}: {url}")
        
        # Run Lighthouse audit
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            metrics_data = loop.run_until_complete(
                _run_audit_async(url, mobile)
            )
        finally:
            loop.close()
        
        if not metrics_data:
            raise Exception("Failed to get Lighthouse metrics")
        
        # Save results to database
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                _save_metrics_async(domain_id, metrics_data)
            )
        finally:
            loop.close()
        
        # Check budget exceedances and send alerts
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                _check_budget_and_alert_async(domain_id)
            )
        finally:
            loop.close()
        
        logger.info(f"Lighthouse check completed for domain {domain_id}")
        return {"status": "success", "domain_id": domain_id, "metrics": metrics_data}
    
    except Exception as exc:
        logger.error(f"Lighthouse check failed for domain {domain_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


async def _run_audit_async(url: str, mobile: bool) -> Dict[str, Any]:
    """Run Lighthouse audit asynchronously."""
    runner = LighthouseRunner()
    result = await runner.run_audit(url, mobile=mobile, headless=True)
    
    if not result or "audits" not in result:
        return {}
    
    # Extract standardized metrics
    metrics = MetricsParser.extract_metrics_from_lighthouse(result)
    metrics["performance_score"] = result.get("categories", {}).get("performance", 0)
    
    return metrics


async def _save_metrics_async(domain_id: int, metrics_data: Dict[str, Any]):
    """Save lighthouse metrics to database."""
    async with async_session_maker() as session:
        metric = Metric(
            domain_id=domain_id,
            fcp=metrics_data.get("fcp"),
            lcp=metrics_data.get("lcp"),
            ttfb=metrics_data.get("ttfb"),
            tbt=metrics_data.get("tbt"),
            speed_index=metrics_data.get("speed_index"),
            inp=metrics_data.get("inp"),
            performance_score=metrics_data.get("performance_score"),
        )
        session.add(metric)
        await session.commit()


async def _check_budget_and_alert_async(domain_id: int):
    """Check budget exceedances and send Telegram alerts."""
    async with async_session_maker() as session:
        budget_service = BudgetService(session)
        telegram_service = get_telegram_service()
        
        exceedances = await budget_service.check_all_domains_exceedances()
        
        if exceedances and telegram_service:
            sent_count = await telegram_service.send_exceedance_alerts(exceedances)
            logger.info(f"Sent {sent_count} budget exceedance alerts")
        elif exceedances and not telegram_service:
            logger.warning("Budget exceedances found but Telegram not configured")


@shared_task
def check_all_domains_periodic():
    """Scheduled task to check all active domains."""
    logger.info("Running periodic domain checks")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_queue_active_domains())
    finally:
        loop.close()


async def _queue_active_domains():
    """Get active domains and queue lighthouse checks."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Domain).where(Domain.is_active == True)
        )
        domains = result.scalars().all()
        
        for domain in domains:
            run_lighthouse_audit_task.delay(domain.id, domain.url, domain.is_mobile)


@shared_task
def send_budget_alerts_task():
    """Task to check and send budget alerts for all domains."""
    logger.info("Checking budget exceedances")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_send_budget_alerts_async())
    finally:
        loop.close()


async def _send_budget_alerts_async():
    """Check budgets and send alerts asynchronously."""
    async with async_session_maker() as session:
        budget_service = BudgetService(session)
        telegram_service = get_telegram_service()
        
        exceedances = await budget_service.check_all_domains_exceedances()
        
        if exceedances:
            logger.info(f"Found {len(exceedances)} budget exceedances")
            if telegram_service:
                sent_count = await telegram_service.send_exceedance_alerts(exceedances)
                logger.info(f"Successfully sent {sent_count} alerts")
        else:
            logger.info("No budget exceedances found")
