"""Structured Security and Administrative Audit Logging."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session

from keyforge.core.crypto import secure_random_id
from keyforge.server.db.models import AuditEventModel

logger = logging.getLogger("keyforge.audit")


def log_audit_event(
    db: Session,
    event_type: str,
    actor_id: str,
    actor_type: str = "admin",
    license_id: str | None = None,
    product_id: str | None = None,
    ip_address: str | None = None,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditEventModel:
    """Record an immutable security audit event into the database."""
    safe_details = dict(details or {})

    # Redact sensitive parameters
    for sensitive_key in ["password", "private_key", "secret", "token", "api_key"]:
        if sensitive_key in safe_details:
            safe_details[sensitive_key] = "[REDACTED]"

    event = AuditEventModel(
        id=secure_random_id("aud", 8),
        event_type=event_type,
        actor_id=actor_id,
        actor_type=actor_type,
        license_id=license_id,
        product_id=product_id,
        ip_address=ip_address,
        timestamp=datetime.now(timezone.utc),
        reason=reason,
        details_json=json.dumps(safe_details),
    )
    db.add(event)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to persist audit log: {e}")

    logger.info(
        f"[AUDIT] {event_type} | Actor: {actor_id} ({actor_type}) | License: {license_id} | Reason: {reason}"
    )
    return event
