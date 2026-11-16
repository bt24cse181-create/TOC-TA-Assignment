"""Main FastAPI application entrypoint for WorkflowGuard."""

import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1 import api_v1_router
from app.core.config import settings
from app.core.database import DatabaseConnectionError, sanitize_db_error

logging.basicConfig(
    level=logging.INFO if not settings.APP_DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("workflowguard.app")

app = FastAPI(
    title=settings.APP_NAME,
    description="WorkflowGuard: Anomaly Detection in Process Workflows Using Automata and Machine Learning",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handlers
@app.exception_handler(DatabaseConnectionError)
async def db_connection_error_handler(request: Request, exc: DatabaseConnectionError):
    """Handle database connectivity failures without exposing sensitive credentials."""
    logger.error(f"Database connection error on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "Database Service Unavailable",
            "message": "The system could not communicate with the relational database. Please verify MySQL service status.",
            "detail": exc.message,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """Sanitize and mask credentials in unhandled database errors."""
    safe_msg = sanitize_db_error(exc)
    logger.error(f"SQLAlchemy error on {request.url.path}: {safe_msg}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Database Error",
            "message": "A database operation failed during request processing.",
            "detail": safe_msg if settings.APP_DEBUG else "Internal server error occurred.",
        },
    )


# Mount versioned API routes
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
def root():
    """Service status and navigation endpoints."""
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "documentation": "/docs",
        "api_v1": f"{settings.API_V1_PREFIX}",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
