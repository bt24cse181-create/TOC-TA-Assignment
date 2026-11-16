"""Health check API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, verify_connection
from app.engine.ml_engine import MLEngine

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health_check(db: Session = Depends(get_db)):
    """System health check verifying database and ML model readiness."""
    db_status = "error"
    try:
        conn_info = verify_connection()
        db_status = conn_info.get("status", "unknown")
    except Exception as exc:
        db_status = f"unhealthy: {type(exc).__name__}"

    ml_status = "unavailable"
    threshold = None
    try:
        mle = MLEngine.load()
        if mle.is_trained:
            ml_status = "ready"
            threshold = mle.threshold
    except Exception:
        ml_status = "not_loaded"

    return {
        "status": "operational" if db_status == "connected" else "degraded",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": {
            "status": db_status,
            "target": settings.DB_NAME,
        },
        "ml_engine": {
            "status": ml_status,
            "threshold": threshold,
        },
    }
