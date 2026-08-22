"""Audit Trail Exploration and System Statistics Endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from keyforge.server.auth import get_current_admin
from keyforge.server.db.database import get_db
from keyforge.server.db.models import (
    ActivationModel,
    AdminUserModel,
    AuditEventModel,
    LicenseModel,
    ProductModel,
)

router = APIRouter(prefix="/api/v1", tags=["Audit & Stats"])


@router.get("/audit")
def list_audit_events(
    event_type: Optional[str] = None,
    license_id: Optional[str] = None,
    product_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(get_current_admin),
):
    """Retrieve security and administrative audit log events."""
    query = db.query(AuditEventModel)
    if event_type:
        query = query.filter(AuditEventModel.event_type == event_type)
    if license_id:
        query = query.filter(AuditEventModel.license_id == license_id)
    if product_id:
        query = query.filter(AuditEventModel.product_id == product_id)
    if actor_id:
        query = query.filter(AuditEventModel.actor_id == actor_id)

    total = query.count()
    items = (
        query.order_by(AuditEventModel.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [item.to_dict() for item in items],
    }


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(get_current_admin),
):
    """Aggregated operational and licensing metrics for the admin dashboard."""
    now = datetime.now(timezone.utc)
    total_licenses = db.query(LicenseModel).count()
    active_licenses = (
        db.query(LicenseModel)
        .filter(
            LicenseModel.status == "active",
            (LicenseModel.expires_at.is_(None)) | (LicenseModel.expires_at > now),
        )
        .count()
    )
    revoked_licenses = (
        db.query(LicenseModel).filter(LicenseModel.status == "revoked").count()
    )
    suspended_licenses = (
        db.query(LicenseModel).filter(LicenseModel.status == "suspended").count()
    )
    expired_licenses = (
        db.query(LicenseModel)
        .filter(
            LicenseModel.status == "active",
            LicenseModel.expires_at.isnot(None),
            LicenseModel.expires_at <= now,
        )
        .count()
    )

    total_activations = (
        db.query(ActivationModel).filter(ActivationModel.status == "active").count()
    )
    total_products = db.query(ProductModel).count()
    total_audit_events = db.query(AuditEventModel).count()

    recent_events = (
        db.query(AuditEventModel)
        .order_by(AuditEventModel.timestamp.desc())
        .limit(10)
        .all()
    )

    return {
        "licenses": {
            "total": total_licenses,
            "active": active_licenses,
            "expired": expired_licenses,
            "revoked": revoked_licenses,
            "suspended": suspended_licenses,
        },
        "activations": {
            "active_devices": total_activations,
        },
        "products_count": total_products,
        "audit_events_count": total_audit_events,
        "recent_audit_events": [e.to_dict() for e in recent_events],
    }
