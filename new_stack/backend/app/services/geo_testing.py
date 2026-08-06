"""
Geo-Testing Service
Запуск Lighthouse тестов из разных локаций через прокси
"""
import asyncio
from typing import Dict, List, Optional
from loguru import logger


class GeoLocation:
    """Конфигурация геолокации"""
    def __init__(self, name: str, city: str, country: str, proxy: str, timezone: str):
        self.name = name
        self.city = city
        self.country = country
        self.proxy = proxy  # Формат: http://user:pass@ip:port
        self.timezone = timezone


# Предопределенные локации
GEO_LOCATIONS = {
    "moscow": GeoLocation("Moscow", "Moscow", "RU", "http://proxy-moscow:8080", "Europe/Moscow"),
    "london": GeoLocation("London", "London", "GB", "http://proxy-london:8080", "Europe/London"),
    "new_york": GeoLocation("New York", "New York", "US", "http://proxy-ny:8080", "America/New_York"),
    "singapore": GeoLocation("Singapore", "Singapore", "SG", "http://proxy-sg:8080", "Asia/Singapore"),
    "sydney": GeoLocation("Sydney", "Sydney", "AU", "http://proxy-sydney:8080", "Australia/Sydney"),
}


class GeoTestingService:
    """Сервис гео-тестирования"""
    
    def __init__(self):
        self.locations = GEO_LOCATIONS
    
    async def run_audit_from_location(
        self, 
        url: str, 
        location_key: str,
        chrome_args: Optional[List[str]] = None
    ) -> Dict:
        """Запустить Lighthouse аудит из определенной локации"""
        if location_key not in self.locations:
            raise ValueError(f"Unknown location: {location_key}")
        
        location = self.locations[location_key]
        logger.info(f"Running audit from {location.city}, {location.country}")
        
        # Добавить аргументы Chrome для прокси
        extra_args = [
            f"--proxy-server={location.proxy}",
            f"--timezone={location.timezone}",
            "--accept-lang=en-US,en"
        ]
        
        if chrome_args:
            extra_args.extend(chrome_args)
        
        # Запустить аудит с прокси
        from app.services.lighthouse_runner import LighthouseRunner
        
        runner = LighthouseRunner()
        result = await runner.run_audit(url, chrome_args=extra_args)
        
        # Добавить информацию о локации в результат
        result["geo"] = {
            "location": location.name,
            "city": location.city,
            "country": location.country,
            "timezone": location.timezone
        }
        
        return result
    
    async def run_audit_multi_location(
        self,
        url: str,
        locations: List[str],
        concurrency: int = 3
    ) -> Dict[str, Dict]:
        """Запустить аудит одновременно из нескольких локаций"""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def run_with_semaphore(location_key: str) -> tuple:
            async with semaphore:
                try:
                    result = await self.run_audit_from_location(url, location_key)
                    return (location_key, result, None)
                except Exception as e:
                    logger.error(f"Error testing from {location_key}: {e}")
                    return (location_key, None, str(e))
        
        tasks = [run_with_semaphore(loc) for loc in locations]
        results = await asyncio.gather(*tasks)
        
        output = {
            "url": url,
            "locations": {},
            "summary": {}
        }
        
        scores_by_location = {}
        
        for location_key, result, error in results:
            if error:
                output["locations"][location_key] = {"error": error}
                scores_by_location[location_key] = None
            else:
                output["locations"][location_key] = result
                scores_by_location[location_key] = result["metrics"].get("performance_score", 0)
        
        # Рассчитать статистику
        valid_scores = [s for s in scores_by_location.values() if s is not None]
        if valid_scores:
            output["summary"] = {
                "avg_score": sum(valid_scores) / len(valid_scores),
                "min_score": min(valid_scores),
                "max_score": max(valid_scores),
                "variance": max(valid_scores) - min(valid_scores)
            }
        
        return output
    
    def get_available_locations(self) -> List[Dict]:
        """Вернуть список доступных локаций"""
        return [
            {
                "key": key,
                "name": loc.name,
                "city": loc.city,
                "country": loc.country,
                "timezone": loc.timezone
            }
            for key, loc in self.locations.items()
        ]
    
    async def compare_locations(
        self,
        url: str,
        baseline_location: str = "moscow",
        compare_locations: Optional[List[str]] = None
    ) -> Dict:
        """Сравнить производительность между локациями"""
        if compare_locations is None:
            compare_locations = ["london", "new_york", "singapore"]
        
        all_locations = [baseline_location] + compare_locations
        results = await self.run_audit_multi_location(url, all_locations)
        
        baseline_result = results["locations"].get(baseline_location)
        if not baseline_result or "error" in baseline_result:
            return {"error": f"Failed to get baseline from {baseline_location}"}
        
        baseline_score = baseline_result["metrics"].get("performance_score", 0)
        
        comparison = {
            "url": url,
            "baseline": baseline_location,
            "comparisons": []
        }
        
        for loc in compare_locations:
            loc_result = results["locations"].get(loc)
            if loc_result and "error" not in loc_result:
                loc_score = loc_result["metrics"].get("performance_score", 0)
                delta = loc_score - baseline_score
                
                comparison["comparisons"].append({
                    "location": loc,
                    "score": loc_score,
                    "delta": delta,
                    "better": delta > 0,
                    "details": loc_result["metrics"]
                })
        
        return comparison
