"""
API Endpoints для Enterprise фич (CI/CD, Гео, AI)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
import hashlib
import hmac
import json

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.domain import User, UserRole
from app.services.cicd_service import CICDService
from app.services.geo_testing_service import GeoTestingService
from app.services.ai_assistant import AIOptimizationAssistant as AIAssistant
from app.schemas.response import ResponseModel

router = APIRouter()

cicd_service = CICDService()
geo_service = GeoTestingService()
ai_service = AIAssistant()


# Helper class для webhook payload (можно вынести в schemas)
class WebhookPayload:
    def __init__(self, data: Dict[str, Any]):
        self.action = data.get("action", "")
        self.pull_request = type('PR', (), {"number": data.get("pull_request", {}).get("number", 0)})()
    
    @classmethod
    def model_validate_json(cls, json_str: str):
        import json
        data = json.loads(json_str)
        return cls(data)


# --- CI/CD Webhooks ---

@router.post("/webhooks/github", response_model=ResponseModel)
async def github_webhook(
    request: Request,
    x_hub_signature: str = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    db: AsyncSession = Depends(get_db)
):
    """
    Обработка вебхуков от GitHub (Pull Request events).
    Проверяет подпись, парсит payload и оставляет комментарий в PR.
    """
    body = await request.body()
    
    # Верификация подписи (если настроен секрет)
    if not cicd_service.verify_signature(body, x_hub_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    try:
        payload = WebhookPayload.model_validate_json(body.decode())
        
        if payload.action == "opened" or payload.action == "synchronize":
            # Запускаем анализ (в реальном проекте - через Celery task)
            report = await cicd_service.process_pull_request(payload)
            
            return {
                "status": "success",
                "message": f"Comment posted to PR #{payload.pull_request.number}",
                "data": report
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"status": "ignored", "message": "Event type not supported"}


@router.post("/webhooks/gitlab", response_model=ResponseModel)
async def gitlab_webhook(
    request: Request,
    x_gitlab_token: str = Header(None, alias="X-Gitlab-Token"),
    db: AsyncSession = Depends(get_db)
):
    """Обработка вебхуков от GitLab."""
    body = await request.body()
    
    # Простая проверка токена
    # В продакшене сравнивать с хешем из настроек проекта
    if x_gitlab_token and not cicd_service.verify_gitlab_token(x_gitlab_token):
        raise HTTPException(status_code=403, detail="Invalid token")
    
    # Логика аналогична GitHub
    return {"status": "success", "message": "GitLab webhook received"}


# --- Гео-тестирование ---

@router.get("/domains/{domain_id}/geo-test", response_model=ResponseModel)
async def start_geo_test(
    domain_id: int,
    locations: Optional[str] = None,  # comma-separated list e.g. "us-east,eu-west"
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Запустить тесты производительности из разных регионов.
    Требует прав Admin или Developer.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.DEVELOPER]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    location_list = locations.split(",") if locations else None
    
    try:
        # В реальности это асинхронная задача Celery
        # Здесь эмулируем запуск
        result = await geo_service.run_global_audit(
            domain_url="https://example.com",  # Нужно достать из БД по domain_id
            locations=location_list
        )
        
        return {
            "status": "success",
            "message": "Geo-audit completed",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geo-test failed: {str(e)}")


@router.get("/domains/{domain_id}/geo-stats", response_model=ResponseModel)
async def get_geo_stats(
    domain_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить статистику по регионам за последние тесты."""
    # Эмуляция данных
    stats = {
        "global_avg_performance": 85,
        "worst_region": "asia-south",
        "variance": 12.5,
        "regions": [
            {"name": "us-east", "score": 92, "latency": 45},
            {"name": "eu-west", "score": 88, "latency": 60},
            {"name": "asia-south", "score": 65, "latency": 210},
        ]
    }
    return {"status": "success", "data": stats}


# --- AI Ассистент ---

@router.post("/domains/{domain_id}/ai-analyze", response_model=ResponseModel)
async def ai_analyze_domain(
    domain_id: int,
    metric_type: str = "performance",  # performance, accessibility, best-practices, seo
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить AI-рекомендации по улучшению метрик домена.
    Использует последние данные Lighthouse + OpenAI (или rule-based fallback).
    """
    try:
        # Эмуляция получения последних метрик из БД
        mock_lhr = {
            "categories": {
                "performance": {"score": 0.65},
                "accessibility": {"score": 0.90}
            },
            "audits": {
                "largest-contentful-paint": {"numericValue": 4500},
                "cumulative-layout-shift": {"numericValue": 0.25},
                "unused-javascript": {"details": {"items": [{"url": "bundle.js", "wastedBytes": 150000}]}},
                "uses-optimized-images": {"details": {"items": [{"url": "hero.jpg", "wastedBytes": 50000}]}}
            }
        }
        
        recommendations = await ai_service.generate_recommendations(mock_lhr, metric_type)
        
        return {
            "status": "success",
            "data": {
                "score": mock_lhr["categories"][metric_type]["score"],
                "recommendations": recommendations,
                "estimated_improvement": "15-20%"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")


@router.get("/ai/status", response_model=ResponseModel)
async def check_ai_status():
    """Проверить доступность AI сервиса и наличие ключей."""
    return {
        "status": "success",
        "data": {
            "openai_configured": ai_service.is_openai_available(),
            "fallback_mode": not ai_service.is_openai_available(),
            "model": ai_service.model_name
        }
    }
