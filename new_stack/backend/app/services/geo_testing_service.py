"""
Geo-Testing Service
Manages Lighthouse audits from different geographic locations.
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.config import settings
from app.services.lighthouse_runner import LighthouseRunner


class GeoLocation:
    """Represents a geographic location for testing."""
    def __init__(self, code: str, name: str, region: str, proxy: Optional[str] = None):
        self.code = code
        self.name = name
        self.region = region
        self.proxy = proxy  # Proxy URL if needed


# Predefined locations
GEO_LOCATIONS = [
    GeoLocation("us-east", "New York (US East)", "North America"),
    GeoLocation("us-west", "San Francisco (US West)", "North America"),
    GeoLocation("eu-west", "London (Europe)", "Europe"),
    GeoLocation("eu-central", "Frankfurt (Europe)", "Europe"),
    GeoLocation("asia-east", "Tokyo (Asia)", "Asia"),
    GeoLocation("asia-south", "Singapore (Asia)", "Asia"),
    GeoLocation("oceania", "Sydney (Oceania)", "Oceania"),
]


class GeoTestingService:
    """Service for running geo-distributed Lighthouse tests."""

    def __init__(self):
        self.runner = LighthouseRunner()
        self.locations = GEO_LOCATIONS

    async def run_audit_at_location(
        self,
        url: str,
        location_code: str,
        device: str = "desktop"
    ) -> Dict[str, Any]:
        """Run Lighthouse audit at a specific location."""
        location = next((loc for loc in self.locations if loc.code == location_code), None)
        if not location:
            raise ValueError(f"Location {location_code} not found")

        # In a real implementation, this would spin up a worker in the target region
        # or use a proxy service. For now, we simulate it with metadata.
        
        result = await self.runner.run_audit(url, device=device)
        
        # Enrich result with geo information
        result["location"] = {
            "code": location.code,
            "name": location.name,
            "region": location.region
        }
        result["timestamp"] = datetime.utcnow().isoformat()
        
        return result

    async def run_audit_global(
        self,
        url: str,
        locations: Optional[List[str]] = None,
        device: str = "desktop"
    ) -> Dict[str, Any]:
        """Run Lighthouse audit from multiple locations concurrently."""
        if locations is None:
            # Default to major regions: US, EU, Asia
            locations = ["us-east", "eu-west", "asia-east"]
        
        tasks = [
            self.run_audit_at_location(url, loc_code, device)
            for loc_code in locations
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_results.append({
                    "location_code": locations[i],
                    "error": str(result)
                })
            else:
                successful_results.append(result)
        
        # Calculate global statistics
        if successful_results:
            avg_score = sum(r.get("performance_score", 0) for r in successful_results) / len(successful_results)
            min_score = min(r.get("performance_score", 0) for r in successful_results)
            max_score = max(r.get("performance_score", 0) for r in successful_results)
            
            # Find worst performing region
            worst_region = min(successful_results, key=lambda x: x.get("performance_score", 100))
            
            global_stats = {
                "average_score": round(avg_score, 2),
                "min_score": round(min_score, 2),
                "max_score": round(max_score, 2),
                "score_variance": round(max_score - min_score, 2),
                "worst_region": worst_region.get("location", {}).get("name", "Unknown"),
                "worst_region_score": worst_region.get("performance_score", 0),
                "total_locations_tested": len(successful_results),
                "failed_locations": len(failed_results)
            }
        else:
            global_stats = {
                "average_score": 0,
                "min_score": 0,
                "max_score": 0,
                "score_variance": 0,
                "worst_region": "N/A",
                "worst_region_score": 0,
                "total_locations_tested": 0,
                "failed_locations": len(failed_results)
            }
        
        return {
            "url": url,
            "device": device,
            "global_stats": global_stats,
            "results_by_location": successful_results,
            "failed_locations": failed_results,
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_available_locations(self) -> List[Dict[str, str]]:
        """Get list of available testing locations."""
        return [
            {
                "code": loc.code,
                "name": loc.name,
                "region": loc.region
            }
            for loc in self.locations
        ]


geo_testing_service = GeoTestingService()
