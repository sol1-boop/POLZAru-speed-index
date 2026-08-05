from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.domains import router as domains_router
from app.api.dashboard import router as dashboard_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(domains_router, prefix="/domains")
api_router.include_router(dashboard_router)
