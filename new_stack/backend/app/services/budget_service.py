"""
Budget Service

Manages performance budgets and checks for exceedances.
Adapted from legacy modules/budget.py and modules/alerts.py
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.domain import Domain
from app.models.metric import Metric

logger = logging.getLogger(__name__)


class BudgetService:
    """Service for managing performance budgets and checking exceedances."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_domain_budget(self, domain_id: int) -> Optional[Dict[str, float]]:
        """Get budget settings for a specific domain."""
        result = await self.db.execute(
            select(Domain).where(Domain.id == domain_id)
        )
        domain = result.scalar_one_or_none()
        
        if not domain:
            return None
            
        return domain.budget_metrics or {}

    async def get_latest_metrics(self, domain_id: int) -> Optional[Dict[str, float]]:
        """Get the latest metrics for a domain."""
        result = await self.db.execute(
            select(Metric)
            .where(Metric.domain_id == domain_id)
            .order_by(Metric.timestamp.desc())
            .limit(1)
        )
        metric = result.scalar_one_or_none()
        
        if not metric:
            return None
            
        return {
            "fcp": metric.fcp,
            "lcp": metric.lcp,
            "ttfb": metric.ttfb,
            "tbt": metric.tbt,
            "speed_index": metric.speed_index,
            "inp": metric.inp,
        }

    async def check_exceedances_for_domain(
        self,
        domain_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Check if latest metrics exceed budget for a domain.
        
        Returns:
            Dictionary with domain info and exceeded metrics, or None
        """
        domain_result = await self.db.execute(
            select(Domain).where(Domain.id == domain_id)
        )
        domain = domain_result.scalar_one_or_none()
        
        if not domain:
            logger.warning(f"Domain {domain_id} not found")
            return None
        
        budget = domain.budget_metrics or {}
        if not budget:
            return None
        
        # Get latest metrics
        metrics = await self.get_latest_metrics(domain_id)
        if not metrics:
            logger.warning(f"No metrics found for domain {domain.url}")
            return None
        
        exceeded_metrics = {}
        
        # Map metric names
        metric_mapping = {
            "fcp": "first-contentful-paint",
            "lcp": "largest-contentful-paint",
            "ttfb": "server-response-time",
            "tbt": "total-blocking-time",
            "speed_index": "speed-index",
            "inp": "interaction-to-next-paint",
        }
        
        for metric_key, budget_value in budget.items():
            if metric_key in metrics and metrics[metric_key] is not None:
                actual_value = metrics[metric_key]
                if actual_value > budget_value:
                    metric_name = metric_mapping.get(metric_key, metric_key)
                    exceeded_metrics[metric_name] = {
                        "actual": actual_value,
                        "budget": budget_value,
                    }
        
        if exceeded_metrics:
            return {
                "domain_id": domain.id,
                "domain_url": domain.url,
                "exceeded_metrics": exceeded_metrics,
                "timestamp": datetime.utcnow().isoformat(),
            }
        
        return None

    async def check_all_domains_exceedances(
        self
    ) -> List[Dict[str, Any]]:
        """
        Check all domains for budget exceedances.
        
        Returns:
            List of dictionaries with exceedance information
        """
        result = await self.db.execute(select(Domain))
        domains = result.scalars().all()
        
        exceedances = []
        
        for domain in domains:
            if not domain.budget_metrics:
                continue
                
            exceedance = await self.check_exceedances_for_domain(domain.id)
            if exceedance:
                exceedances.append(exceedance)
        
        return exceedances

    async def update_domain_budget(
        self,
        domain_id: int,
        budget_metrics: Dict[str, float]
    ) -> Optional[Domain]:
        """Update budget settings for a domain."""
        result = await self.db.execute(
            select(Domain).where(Domain.id == domain_id)
        )
        domain = result.scalar_one_or_none()
        
        if not domain:
            return None
        
        domain.budget_metrics = budget_metrics
        await self.db.commit()
        await self.db.refresh(domain)
        
        return domain
