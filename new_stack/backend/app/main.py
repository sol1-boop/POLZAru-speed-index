from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.core.database import engine, Base
from app.api import api_router
from app.models import User  # Import models to register them


# Create tables on startup (for development)
# In production, use Alembic migrations
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


async def create_initial_admin():
    """Create initial admin user if not exists."""
    from sqlalchemy import select
    from app.core.database import async_session_maker
    from app.core.security import get_password_hash
    
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        admin = result.scalar_one_or_none()
        
        if not admin:
            new_admin = User(
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                is_superuser=True,
                is_active=True,
            )
            session.add(new_admin)
            await session.commit()
            logger.info(f"Initial admin user created: {settings.ADMIN_EMAIL}")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Website Performance Monitoring System",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure properly in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
    
    # Include routers
    app.include_router(api_router, prefix="/api/v1")
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "version": settings.APP_VERSION}
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        logger.info("Application starting up...")
        await create_tables()
        await create_initial_admin()
        logger.info("Application started successfully")
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Application shutting down...")
        await engine.dispose()
    
    return app


app = create_app()
