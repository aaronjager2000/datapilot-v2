import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.redis import get_redis_client
from app.db.session import async_session_maker
from app.db.init_db import init_db
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.tenant import TenantMiddleware
from app.services.auth.jwt import jwt_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Datapilot application...")

    # Initialize Redis client for JWT service
    redis_client = get_redis_client()
    if redis_client:
        jwt_service.redis = redis_client
        logger.info("JWT service initialized with Redis client")
    else:
        logger.warning("Redis client not available - token blacklisting disabled")

    # Initialize database
    try:
        async with async_session_maker() as db:
            await init_db(db)
        logger.info("Database initialization complete")
    except Exception as exc:
        logger.error(f"Database initialization failed: {exc}", exc_info=True)

    yield

    # Shutdown
    logger.info("Shutting down Datapilot application...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multi-tenant data intelligence platform for small to mid-sized organizations",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware (order matters - they execute in reverse order)
# Rate limiting (first to execute, blocks early if limit exceeded)
redis_client = get_redis_client()
app.add_middleware(
    RateLimitMiddleware,
    redis_client=redis_client,
    default_limit=100,
    default_window=60,
    authenticated_limit=1000,
    authenticated_window=60,
)

# Tenant middleware (extracts tenant context after auth)
app.add_middleware(TenantMiddleware)

# Logging middleware (logs all requests/responses)
app.add_middleware(LoggingMiddleware)

# Error handler (catches all exceptions, executes last)
app.add_middleware(ErrorHandlerMiddleware)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
async def health_check():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "version": settings.APP_VERSION,
            "service": "datapilot-api"
        }
    )


@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Welcome to Datapilot API",
        "version": settings.APP_VERSION,
        "docs": f"{settings.API_V1_PREFIX}/docs"
    }
