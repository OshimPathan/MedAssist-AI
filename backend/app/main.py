"""
MedAssist AI - Main Application Entry Point
FastAPI application with WebSocket support for real-time communication
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database.connection import connect_db, disconnect_db

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    try:
        await connect_db()
        logger.info("Database connected")
    except Exception as e:
        logger.warning(f"Database not available: {e}. Running in limited mode.")

    yield

    # Shutdown
    logger.info("Shutting down application")
    try:
        await disconnect_db()
        logger.info("Database disconnected")
    except Exception:
        pass


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Real-Time Intelligent Hospital Communication & Emergency Response System",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting Middleware
from app.utils.rate_limiter import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Detailed health check with LLM provider info"""
    from app.ai_engine.llm_client import llm_client
    await llm_client._detect_provider()
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "database": "connected",
        "llm_provider": llm_client.provider or "none (using template fallbacks)",
        "llm_model": llm_client.model or "n/a",
        "llm_info": llm_client.provider_info,
    }


# Import and register routers
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.doctors import router as doctors_router
from app.api.appointments import router as appointments_router
from app.api.emergency import router as emergency_router
from app.api.admin import router as admin_router
from app.api.knowledge import router as knowledge_router
from app.api.triage import router as triage_router
from app.api.compliance import router as compliance_router
from app.api.analytics import router as analytics_router

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(doctors_router, prefix="/api/doctors", tags=["Doctors"])
app.include_router(appointments_router, prefix="/api/appointments", tags=["Appointments"])
app.include_router(emergency_router, prefix="/api/emergency", tags=["Emergency"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(knowledge_router, prefix="/api/knowledge", tags=["Knowledge Base"])
app.include_router(triage_router, prefix="/api/triage", tags=["Triage"])
app.include_router(compliance_router, prefix="/api/compliance", tags=["GDPR & Compliance"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
