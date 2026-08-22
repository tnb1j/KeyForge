"""Authentication and API Key Management Endpoints."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from keyforge.core.crypto import secure_random_id
from keyforge.server.audit import log_audit_event
from keyforge.server.auth import (
    create_access_token,
    get_current_admin,
    hash_password,
    verify_password,
)
from keyforge.server.db.database import get_db
from keyforge.server.db.models import AdminUserModel
from keyforge.server.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in_minutes: int
    user: dict


class CreateApiKeyResponse(BaseModel):
    api_key: str
    created_at: str
    warning: str


@router.post("/login", response_model=LoginResponse)
def login(
    req: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate administrator with username and password."""
    limiter.check_rate_limit(request, action="login", max_requests_per_minute=10)

    user = db.query(AdminUserModel).filter_by(username=req.username.strip()).first()
    if not user or not verify_password(req.password, user.password_hash):
        log_audit_event(
            db=db,
            event_type="auth.failed_login",
            actor_id=req.username,
            actor_type="client",
            ip_address=request.client.host if request.client else None,
            reason="Invalid credentials",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(subject=user.username, role=user.role)

    log_audit_event(
        db=db,
        event_type="auth.login",
        actor_id=user.username,
        actor_type="admin",
        ip_address=request.client.host if request.client else None,
        reason="Successful password authentication",
    )

    return LoginResponse(
        access_token=token,
        token_type="Bearer",
        expires_in_minutes=1440,
        user=user.to_dict(),
    )


@router.get("/me")
def get_me(current_user: AdminUserModel = Depends(get_current_admin)):
    """Retrieve current authenticated administrator profile."""
    return current_user.to_dict()


@router.post("/api-key", response_model=CreateApiKeyResponse)
def generate_api_key(
    current_user: AdminUserModel = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Generate a high-entropy API key for backend programmatic access."""
    raw_api_key = f"kf_live_{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(raw_api_key.encode("utf-8")).hexdigest()

    current_user.api_key_hash = key_hash
    db.commit()

    log_audit_event(
        db=db,
        event_type="auth.api_key_created",
        actor_id=current_user.username,
        actor_type="admin",
        reason="Generated new integration API key",
    )

    return CreateApiKeyResponse(
        api_key=raw_api_key,
        created_at=datetime.now(timezone.utc).isoformat(),
        warning="Save this API key now; it cannot be displayed again.",
    )
