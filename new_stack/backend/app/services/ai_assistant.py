"""
AI Optimization Assistant Service
Provides AI-powered recommendations for performance improvements.
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.config import settings


class AIOptimizationAssistant:
    """Service for generating AI-powered optimization recommendations."""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.openai_url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-4o-mini"

    async def analyze_lighthouse_results(
        self,
        url: str,
        lighthouse_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        performance_score = lighthouse_result.get("performance_score", 0)
        audits = lighthouse_result.get("audits", {})
        
        critical_audits = []
        for audit_id, audit_data in audits.items():
            if isinstance(audit_data, dict):
                score = audit_data.get("score", 1)
                if score is not None and score < 0.5:
                    critical_audits.append({
                        "id": audit_id,
                        "title": audit_data.get("title", audit_id),
                        "description": audit_data.get("description", ""),
                        "score": score
                    })
        
        prompt = self._build_analysis_prompt(url, performance_score, critical_audits)
        
        if self.openai_api_key:
            try:
                ai_response = await self._call_openai(prompt)
                recommendations = self._parse_ai_response(ai_response)
            except Exception as e:
                recommendations = self._generate_rule_based_recommendations(critical_audits)
                recommendations["ai_error"] = str(e)
        else:
            recommendations = self._generate_rule_based_recommendations(critical_audits)
            recommendations["note"] = "AI not configured. Using rule-based analysis."
        
        return {
            "url": url,
            "performance_score": performance_score,
            "analyzed_at": datetime.utcnow().isoformat(),
            "critical_issues_count": len(critical_audits),
            "recommendations": recommendations,
            "estimated_impact": self._calculate_estimated_impact(recommendations)
        }

    def _build_analysis_prompt(self, url: str, score: float, critical_audits: List[Dict[str, Any]]) -> str:
        audits_text = "\n".join([
            f"- {audit['title']}: Score {audit['score']:.2f} ({audit['description']})"
            for audit in critical_audits[:10]
        ])
        
        return f"""You are a web performance expert. Analyze this Lighthouse report:
URL: {url}, Score: {score}/100
Critical Issues: {audits_text}
Provide top 3-5 optimizations with code examples. Return JSON with recommendations array."""

    async def _call_openai(self, prompt: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.openai_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a web performance expert. Respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1500
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.openai_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            import json
            return json.loads(data["choices"][0]["message"]["content"])

    def _parse_ai_response(self, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source": "ai",
            "summary": ai_response.get("summary", ""),
            "items": ai_response.get("recommendations", []),
            "total_count": len(ai_response.get("recommendations", []))
        }

    def _generate_rule_based_recommendations(self, critical_audits: List[Dict[str, Any]]) -> Dict[str, Any]:
        recommendations = []
        audit_rules = {
            "largest-contentful-paint": {
                "title": "Optimize LCP", "priority": "high", "category": "images",
                "description": "LCP is slow. Optimize your largest visible element.",
                "tips": ["Compress images", "Use CDN", "Preload resources"],
                "estimated_improvement_ms": 500, "effort": "medium"
            },
            "cumulative-layout-shift": {
                "title": "Fix CLS", "priority": "high", "category": "css",
                "description": "Page elements are shifting.",
                "tips": ["Add size attributes", "Reserve space for ads"],
                "estimated_improvement_ms": 200, "effort": "low"
            },
            "total-blocking-time": {
                "title": "Reduce TBT", "priority": "high", "category": "javascript",
                "description": "Long tasks blocking main thread.",
                "tips": ["Code splitting", "Defer non-critical JS"],
                "estimated_improvement_ms": 400, "effort": "high"
            }
        }
        
        for audit in critical_audits:
            audit_id = audit.get("id", "")
            if audit_id in audit_rules:
                rule = audit_rules[audit_id].copy()
                rule["related_audit"] = audit_id
                recommendations.append(rule)
        
        if not recommendations:
            recommendations.append({
                "title": "General Optimization", "priority": "medium", "category": "other",
                "description": "Continue monitoring.",
                "tips": ["Enable compression", "Use caching"],
                "estimated_improvement_ms": 150, "effort": "low"
            })
        
        total_improvement = sum(r.get("estimated_improvement_ms", 0) for r in recommendations)
        return {
            "source": "rule-based",
            "summary": f"Found {len(recommendations)} opportunities ({total_improvement}ms improvement).",
            "items": recommendations,
            "total_count": len(recommendations)
        }

    def _calculate_estimated_impact(self, recommendations: Dict[str, Any]) -> Dict[str, Any]:
        items = recommendations.get("items", [])
        total_improvement_ms = sum(item.get("estimated_improvement_ms", 0) for item in items)
        high_priority_count = sum(1 for item in items if item.get("priority") == "high")
        return {
            "total_potential_improvement_ms": total_improvement_ms,
            "high_priority_items": high_priority_count,
            "total_items": len(items),
            "estimated_score_increase": min(20, total_improvement_ms // 100)
        }


ai_assistant = AIOptimizationAssistant()
