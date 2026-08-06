"""
AI Optimization Assistant
Анализ метрик Lighthouse и генерация рекомендаций по оптимизации
"""
from typing import Dict, List, Optional
from loguru import logger


class AIOptimizationAssistant:
    """AI-ассистент для анализа производительности и генерации рекомендаций"""
    
    # База знаний проблем и решений
    KNOWLEDGE_BASE = {
        "lcp": {
            "threshold": 2.5,
            "unit": "s",
            "issues": [
                {
                    "condition": lambda m: m.get("lcp", 0) > 4.0,
                    "severity": "critical",
                    "title": "Критически медленный LCP",
                    "description": "Largest Contentful Paint превышает 4 секунды",
                    "recommendations": [
                        "Оптимизируйте загрузку главного изображения (используйте WebP/AVIF)",
                        "Настройте preload для критических ресурсов",
                        "Уменьшите размер CSS/JS блокирующих рендеринг",
                        "Используйте CDN для статических ресурсов",
                        "Проверьте время ответа сервера (TTFB)"
                    ]
                },
                {
                    "condition": lambda m: 2.5 < m.get("lcp", 0) <= 4.0,
                    "severity": "warning",
                    "title": "LCP требует улучшения",
                    "description": "Largest Contentful Paint между 2.5 и 4 секундами",
                    "recommendations": [
                        "Добавьте lazy loading для изображений ниже fold",
                        "Оптимизируйте шрифты (font-display: swap)",
                        "Минимизируйте главный поток"
                    ]
                }
            ]
        },
        "fid": {
            "threshold": 100,
            "unit": "ms",
            "issues": [
                {
                    "condition": lambda m: m.get("fid", 0) > 300,
                    "severity": "critical",
                    "title": "Критическая задержка ввода",
                    "description": "First Input Delay превышает 300ms",
                    "recommendations": [
                        "Разбейте длинные задачи JavaScript (>50ms)",
                        "Используйте Web Workers для тяжелых вычислений",
                        "Отложите загрузку не критического JS",
                        "Минимизируйте работу главного потока при загрузке"
                    ]
                },
                {
                    "condition": lambda m: 100 < m.get("fid", 0) <= 300,
                    "severity": "warning",
                    "title": "Задержка ввода выше нормы",
                    "description": "First Input Delay между 100 и 300ms",
                    "recommendations": [
                        "Оптимизируйте обработчики событий",
                        "Используйте debounce/throttle для частых событий",
                        "Проверьте сторонние скрипты"
                    ]
                }
            ]
        },
        "cls": {
            "threshold": 0.1,
            "unit": "",
            "issues": [
                {
                    "condition": lambda m: m.get("cls", 0) > 0.25,
                    "severity": "critical",
                    "title": "Критические сдвиги макета",
                    "description": "Cumulative Layout Shift превышает 0.25",
                    "recommendations": [
                        "Добавьте явные размеры для изображений и видео",
                        "Зарезервируйте место для динамического контента",
                        "Избегайте вставки контента над существующим",
                        "Используйте aspect-ratio в CSS",
                        "Оптимизируйте загрузку веб-шрифтов"
                    ]
                },
                {
                    "condition": lambda m: 0.1 < m.get("cls", 0) <= 0.25,
                    "severity": "warning",
                    "title": "Сдвиги макета заметны",
                    "description": "Cumulative Layout Shift между 0.1 и 0.25",
                    "recommendations": [
                        "Проверьте рекламу и виджеты",
                        "Добавьте skeleton loaders",
                        "Используйте transform вместо position изменений"
                    ]
                }
            ]
        },
        "fcp": {
            "threshold": 1.8,
            "unit": "s",
            "issues": [
                {
                    "condition": lambda m: m.get("fcp", 0) > 3.0,
                    "severity": "critical",
                    "title": "Очень медленная первая отрисовка",
                    "description": "First Contentful Paint превышает 3 секунды",
                    "recommendations": [
                        "Оптимизируйте критический путь рендеринга",
                        "Минимизируйте CSS и JS",
                        "Используйте inline critical CSS",
                        "Настройте кэширование браузера"
                    ]
                },
                {
                    "condition": lambda m: 1.8 < m.get("fcp", 0) <= 3.0,
                    "severity": "warning",
                    "title": "Первая отрисовка медленная",
                    "description": "First Contentful Paint между 1.8 и 3 секундами",
                    "recommendations": [
                        "Уменьшите размер HTML",
                        "Оптимизируйте загрузку шрифтов",
                        "Проверьте блокирующие ресурсы"
                    ]
                }
            ]
        },
        "performance_score": {
            "threshold": 90,
            "unit": "points",
            "issues": [
                {
                    "condition": lambda m: m.get("performance_score", 0) < 50,
                    "severity": "critical",
                    "title": "Критически низкая производительность",
                    "description": "Общий балл производительности ниже 50",
                    "recommendations": [
                        "Проведите полный аудит производительности",
                        "Рассмотрите переход на современный фреймворк",
                        "Оптимизируйте изображения и видео",
                        "Настройте серверную оптимизацию (gzip, brotli)",
                        "Используйте HTTP/2 или HTTP/3"
                    ]
                },
                {
                    "condition": lambda m: 50 <= m.get("performance_score", 0) < 75,
                    "severity": "warning",
                    "title": "Производительность требует работы",
                    "description": "Общий балл между 50 и 75",
                    "recommendations": [
                        "Сфокусируйтесь на Core Web Vitals",
                        "Оптимизируйте JavaScript bundle",
                        "Настройте code splitting"
                    ]
                }
            ]
        }
    }
    
    async def analyze(self, metrics: Dict) -> Dict:
        """Проанализировать метрики и вернуть рекомендации"""
        logger.info("Analyzing metrics with AI assistant")
        
        issues_found = []
        recommendations = set()
        
        for metric_name, config in self.KNOWLEDGE_BASE.items():
            for issue in config["issues"]:
                if issue["condition"](metrics):
                    issues_found.append({
                        "metric": metric_name,
                        "severity": issue["severity"],
                        "title": issue["title"],
                        "description": issue["description"],
                        "threshold": f"{config['threshold']}{config['unit']}",
                        "current_value": metrics.get(metric_name, 0)
                    })
                    recommendations.update(issue["recommendations"])
        
        # Сортировать проблемы по серьезности
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        issues_found.sort(key=lambda x: severity_order.get(x["severity"], 3))
        
        # Добавить общие рекомендации
        general_recommendations = self._get_general_recommendations(metrics)
        all_recommendations = list(recommendations) + general_recommendations
        
        # Удалить дубликаты
        all_recommendations = list(dict.fromkeys(all_recommendations))
        
        return {
            "summary": {
                "total_issues": len(issues_found),
                "critical": sum(1 for i in issues_found if i["severity"] == "critical"),
                "warnings": sum(1 for i in issues_found if i["severity"] == "warning"),
                "performance_score": metrics.get("performance_score", 0)
            },
            "issues": issues_found,
            "recommendations": all_recommendations,
            "priority_actions": all_recommendations[:5]  # Топ-5 приоритетных действий
        }
    
    def _get_general_recommendations(self, metrics: Dict) -> List[str]:
        """Получить общие рекомендации на основе всех метрик"""
        recommendations = []
        
        score = metrics.get("performance_score", 0)
        
        if score < 90:
            recommendations.append("Настройте автоматический мониторинг производительности в CI/CD")
        
        if metrics.get("lcp", 0) > 2.5 and metrics.get("fcp", 0) > 1.8:
            recommendations.append("Рассмотрите использование SSR или SSG для ускорения первой отрисовки")
        
        if metrics.get("cls", 0) > 0.1:
            recommendations.append("Внедрите визуальные тесты для обнаружения сдвигов макета")
        
        # Проверка на наличие возможностей для PWA
        if score >= 75:
            recommendations.append("Рассмотрите внедрение Service Worker для офлайн-режима")
        
        return recommendations
    
    async def generate_report(self, metrics: Dict, domain: str) -> str:
        """Сгенерировать текстовый отчет с рекомендациями"""
        analysis = await self.analyze(metrics)
        
        lines = [
            f"# 📊 Performance Audit Report",
            f"**Domain:** {domain}",
            f"**Date:** {self._get_current_date()}",
            "",
            f"## Summary",
            f"- Performance Score: **{metrics.get('performance_score', 0):.1f}/100**",
            f"- Issues Found: **{analysis['summary']['total_issues']}**",
            f"  - 🔴 Critical: {analysis['summary']['critical']}",
            f"  - 🟡 Warnings: {analysis['summary']['warnings']}",
            ""
        ]
        
        if analysis["issues"]:
            lines.append("## Issues Detected")
            for issue in analysis["issues"]:
                emoji = "🔴" if issue["severity"] == "critical" else "🟡"
                lines.append(f"{emoji} **{issue['title']}**")
                lines.append(f"   - Metric: {issue['metric']}")
                lines.append(f"   - Current: {issue['current_value']} (Threshold: {issue['threshold']})")
                lines.append(f"   - {issue['description']}")
                lines.append("")
        
        if analysis["recommendations"]:
            lines.append("## Recommendations")
            for i, rec in enumerate(analysis["recommendations"], 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
        
        if analysis["priority_actions"]:
            lines.append("## 🎯 Priority Actions (Top 5)")
            for i, action in enumerate(analysis["priority_actions"], 1):
                lines.append(f"{i}. {action}")
        
        lines.append("")
        lines.append("---")
        lines.append("_Generated by Monitor App AI Assistant v2.0_")
        
        return "\n".join(lines)
    
    def _get_current_date(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
