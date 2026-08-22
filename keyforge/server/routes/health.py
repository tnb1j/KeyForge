"""Health and Diagnostics Routes."""

from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from keyforge import __version__
from keyforge.server.db.database import get_db

router = APIRouter(prefix="/api/v1/health", tags=["Health"])


@router.get("")
def health_check(db: Session = Depends(get_db)):
    """Check service health and database connectivity."""
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "KeyForge Licensing Server",
        "version": __version__,
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
