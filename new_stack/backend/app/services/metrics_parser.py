"""
Metrics Parser Service

Parses and processes Lighthouse metrics.
Adapted from legacy modules/metrics.py with improved parsing.
"""

import logging
import re
import statistics
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class MetricsParser:
    """Service for parsing and processing Lighthouse metrics."""

    @staticmethod
    def parse_metric_value(
        value: Any,
        target_unit: str = "s"
    ) -> Optional[float]:
        """
        Parse metric value from Lighthouse result.
        
        Args:
            value: Raw metric value (string or number)
            target_unit: Target unit ('s' for seconds, 'ms' for milliseconds)
            
        Returns:
            Numeric value in target unit or None
        """
        if value is None:
            return None
            
        # Handle numeric values directly
        if isinstance(value, (int, float)):
            return float(value)
        
        if not isinstance(value, str):
            logger.error(f"Unexpected value type: {type(value)}")
            return None
        
        try:
            # Clean up the string
            value = value.replace("\u00A0", " ").strip()
            
            # Handle TTFB special format
            if "Root document took" in value:
                value = value.replace("Root document took", "").strip()
            
            # Extract numeric part using regex
            match = re.search(r"([\d,\.]+)", value)
            if not match:
                logger.error(f"Could not extract number from: {value}")
                return None
            
            number_str = match.group(1).replace(",", "")
            number = float(number_str)
            
            # Detect source unit and convert
            value_lower = value.lower()
            
            if target_unit == "ms":
                if "ms" in value_lower or "миллисек" in value_lower:
                    return number
                if "s" in value_lower or "сек" in value_lower:
                    return number * 1000
                return number
                
            elif target_unit == "s":
                if "ms" in value_lower or "миллисек" in value_lower:
                    return number / 1000
                if "s" in value_lower or "сек" in value_lower:
                    return number
                return number
                
            return number
            
        except ValueError as e:
            logger.error(f"Error parsing metric '{value}': {e}")
            return None

    @staticmethod
    def extract_metrics_from_lighthouse(
        lighthouse_result: Dict[str, Any]
    ) -> Dict[str, Optional[float]]:
        """
        Extract standardized metrics from Lighthouse result.
        
        Args:
            lighthouse_result: Raw Lighthouse audit result
            
        Returns:
            Dictionary with standardized metric values in seconds
        """
        audits = lighthouse_result.get("audits", {})
        
        def get_numeric(audit_id: str) -> Optional[float]:
            audit = audits.get(audit_id, {})
            # Prefer numericValue if available
            numeric_value = audit.get("numericValue")
            if numeric_value is not None:
                # Lighthouse returns ms for most metrics
                return numeric_value / 1000.0  # Convert to seconds
            
            # Fallback to displayValue parsing
            display_value = audit.get("displayValue")
            return MetricsParser.parse_metric_value(display_value, target_unit="s")
        
        return {
            "fcp": get_numeric("first-contentful-paint"),
            "lcp": get_numeric("largest-contentful-paint"),
            "ttfb": get_numeric("server-response-time"),
            "tbt": get_numeric("total-blocking-time"),
            "speed_index": get_numeric("speed-index"),
            "inp": get_numeric("interaction-to-next-paint"),
        }

    @staticmethod
    def calculate_statistics(values: List[Optional[float]]) -> Dict[str, Optional[float]]:
        """
        Calculate statistics for a list of metric values.
        
        Args:
            values: List of metric values (may contain None)
            
        Returns:
            Dictionary with min, median, p75, p95, max
        """
        # Filter out None values
        clean_values = [v for v in values if v is not None]
        
        if not clean_values:
            return {
                "min": None,
                "median": None,
                "percentile_75": None,
                "percentile_95": None,
                "max": None,
                "count": 0,
            }
        
        clean_values.sort()
        n = len(clean_values)
        
        # Calculate percentiles
        if n >= 2:
            percentiles = statistics.quantiles(clean_values, n=100)
            p75 = round(percentiles[74], 2) if len(percentiles) > 74 else None
            p95 = round(percentiles[94], 2) if len(percentiles) > 94 else None
        else:
            p75 = None
            p95 = None
        
        return {
            "min": round(min(clean_values), 2),
            "median": round(statistics.median(clean_values), 2),
            "percentile_75": p75,
            "percentile_95": p95,
            "max": round(max(clean_values), 2),
            "count": n,
        }

    @staticmethod
    def compute_domain_stats(
        metrics_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compute comprehensive statistics for domain metrics history.
        
        Args:
            metrics_history: List of metric records from database
            
        Returns:
            Dictionary with dates, raw metrics, and statistics
        """
        dates = []
        fcp_values = []
        lcp_values = []
        ttfb_values = []
        tbt_values = []
        speed_index_values = []
        inp_values = []
        
        for record in metrics_history:
            dates.append(record.get("timestamp"))
            fcp_values.append(record.get("fcp"))
            lcp_values.append(record.get("lcp"))
            ttfb_values.append(record.get("ttfb"))
            tbt_values.append(record.get("tbt"))
            speed_index_values.append(record.get("speed_index"))
            inp_values.append(record.get("inp"))
        
        return {
            "dates": dates,
            "metrics": {
                "fcp": fcp_values,
                "lcp": lcp_values,
                "ttfb": ttfb_values,
                "tbt": tbt_values,
                "speed_index": speed_index_values,
                "inp": inp_values,
            },
            "stats": {
                "fcp": MetricsParser.calculate_statistics(fcp_values),
                "lcp": MetricsParser.calculate_statistics(lcp_values),
                "ttfb": MetricsParser.calculate_statistics(ttfb_values),
                "tbt": MetricsParser.calculate_statistics(tbt_values),
                "speed_index": MetricsParser.calculate_statistics(speed_index_values),
                "inp": MetricsParser.calculate_statistics(inp_values),
            }
        }
