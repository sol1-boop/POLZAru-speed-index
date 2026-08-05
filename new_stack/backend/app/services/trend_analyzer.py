"""
Сервис анализа трендов и обнаружения аномалий.
Реализует логику "Умных алертов".
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TrendAnalyzer:
    """Анализирует исторические данные метрик на предмет деградации."""

    @staticmethod
    def check_degradation_streak(
        metrics_history: List[Dict[str, Any]], 
        metric_name: str, 
        threshold: float, 
        streak_length: int = 3
    ) -> bool:
        """
        Проверяет, ухудшалась ли метрика последние N раз подряд.
        
        :param metrics_history: Список метрик, отсортированный по дате (новые последние).
        :param metric_name: Имя метрики (например, 'largest_contentful_paint').
        :param threshold: Пороговое значение ухудшения (в мс или единицах).
        :param streak_length: Количество последовательных ухудшений для триггера.
        :return: True если обнаружена деградация.
        """
        if len(metrics_history) < streak_length + 1:
            return False

        # Берем последние N+1 записей
        recent = metrics_history[-(streak_length + 1):]
        
        streak = 0
        for i in range(1, len(recent)):
            prev_val = recent[i-1].get(metric_name)
            curr_val = recent[i].get(metric_name)

            if prev_val is None or curr_val is None:
                continue

            # Для метрик времени (LCP, FCP) ухудшение = рост значения
            if curr_val > prev_val and (curr_val - prev_val) > threshold:
                streak += 1
            else:
                streak = 0 # Сброс серии

        return streak >= streak_length

    @staticmethod
    def generate_alert_message(domain: str, metric: str, trend: str) -> str:
        """Генерирует человекопонятное сообщение об аномалии."""
        return f"⚠️ Обнаружена тенденция {trend} метрики {metric} для {domain}."
