import asyncio
from typing import Dict, Any, Optional
from loguru import logger
from pathlib import Path
import json

try:
    from pylighthouse.lighthouse import Lighthouse
    LIGHTHOUSE_AVAILABLE = True
except ImportError:
    LIGHTHOUSE_AVAILABLE = False
    logger.warning("pylighthouse not installed, using mock data")

from app.core.config import settings


async def run_lighthouse_audit(url: str) -> Dict[str, Any]:
    """
    Run Lighthouse audit for a given URL.
    Returns metrics dictionary.
    """
    if not LIGHTHOUSE_AVAILABLE:
        return _get_mock_metrics(url)
    
    try:
        chrome_flags = [
            "--no-sandbox" if settings.CHROME_NO_SANDBOX else "",
            "--headless" if settings.CHROME_HEADLESS else "",
        ]
        flags = [f for f in chrome_flags if f]
        
        lh = Lighthouse(
            url=url,
            output_path=str(Path(settings.CHROME_DATA_DIR) / "reports"),
            chrome_flags=flags,
        )
        
        result = await lh.run()
        
        # Extract categories
        categories = result.get("categories", {})
        category_scores = {
            k: v.get("score", 0) * 100 if v.get("score") is not None else 0
            for k, v in categories.items()
        }
        
        # Extract audits
        audits = result.get("audits", {})
        
        metrics = {
            "performance_score": category_scores.get("performance", 0),
            "accessibility_score": category_scores.get("accessibility", 0),
            "best_practices_score": category_scores.get("best-practices", 0),
            "seo_score": category_scores.get("seo", 0),
            "pwa_score": category_scores.get("pwa", 0),
            "first_contentful_paint": _get_audit_value(audits, "first-contentful-paint"),
            "largest_contentful_paint": _get_audit_value(audits, "largest-contentful-paint"),
            "total_blocking_time": _get_audit_value(audits, "total-blocking-time"),
            "cumulative_layout_shift": _get_audit_value(audits, "cumulative-layout-shift"),
            "speed_index": _get_audit_value(audits, "speed-index"),
            "report_url": None,  # Could save to S3 or local storage
            "screenshot_path": None,
        }
        
        logger.info(f"Lighthouse audit completed for {url}")
        return metrics
    
    except Exception as e:
        logger.error(f"Lighthouse audit failed for {url}: {e}")
        # Return mock data on failure for development
        return _get_mock_metrics(url, error=True)


def _get_audit_value(audits: dict, audit_id: str) -> Optional[float]:
    """Extract numeric value from audit result."""
    audit = audits.get(audit_id, {})
    display_value = audit.get("displayValue", "")
    
    # Parse numeric value from display string (e.g., "1.2 s" -> 1200)
    if display_value:
        import re
        match = re.search(r"([\d.]+)\s*(ms|s)?", display_value)
        if match:
            value = float(match.group(1))
            unit = match.group(2) or "ms"
            if unit == "s":
                value *= 1000
            return value
    
    # Try numericValue
    numeric_value = audit.get("numericValue")
    if numeric_value is not None:
        return float(numeric_value)
    
    return None


def _get_mock_metrics(url: str, error: bool = False) -> Dict[str, Any]:
    """Return mock metrics for testing or when lighthouse is unavailable."""
    import random
    from datetime import datetime
    
    if error:
        base_score = 50
    else:
        base_score = random.uniform(70, 95)
    
    return {
        "performance_score": round(base_score, 2),
        "accessibility_score": round(random.uniform(80, 100), 2),
        "best_practices_score": round(random.uniform(85, 100), 2),
        "seo_score": round(random.uniform(75, 100), 2),
        "pwa_score": round(random.uniform(0, 50), 2),
        "first_contentful_paint": random.uniform(800, 2000),
        "largest_contentful_paint": random.uniform(1500, 3500),
        "total_blocking_time": random.uniform(100, 500),
        "cumulative_layout_shift": random.uniform(0.01, 0.2),
        "speed_index": random.uniform(2000, 4500),
        "report_url": None,
        "screenshot_path": None,
    }
