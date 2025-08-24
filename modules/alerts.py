"""Budget exceedance checks for metrics."""

import logging
from datetime import datetime

from .budget import load_budget, get_latest_metrics

logger = logging.getLogger(__name__)


def check_exceedances():
    """Return list of domains with metrics exceeding their budget."""
    budget_data = load_budget()
    exceeded = []
    for domain_data in budget_data:
        domain = domain_data["domain"]
        budget_metrics = domain_data.get("budget", {})
        latest_metrics = get_latest_metrics(domain)
        if not latest_metrics:
            logger.warning("Метрики для %s не найдены, пропуск.", domain)
            continue
        domain_exceeded = {}
        for metric, threshold in budget_metrics.items():
            if metric in latest_metrics and latest_metrics[metric] > threshold:
                domain_exceeded[metric] = {
                    "actual": latest_metrics[metric],
                    "budget": threshold,
                }
        if domain_exceeded:
            exceeded.append({
                "domain": domain,
                "exceeded_metrics": domain_exceeded,
                "timestamp": datetime.now().isoformat(),
            })
    return exceeded
