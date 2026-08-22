"""Authentication, Password Hashing, JWT Tokens, and RBAC Authorization."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Header, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from keyforge.server.config import settings
from keyforge.server.db.database import get_db
from keyforge.server.db.models import AdminUserModel

ph = PasswordHasher()
security_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password securely using Argon2id."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2id hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    s_padded = s + "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s_padded.encode("ascii"))


def create_access_token(
    subject: str, role: str, expires_minutes: int | None = None
) -> str:
    """Create a signed HMAC-SHA256 JWT access token."""
    exp_mins = expires_minutes or settings.jwt_expire_minutes
    now = int(time.time())
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + (exp_mins * 60),
    }
    header = {"alg": "HS256", "typ": "JWT"}

    hdr_b64 = _b64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload).encode("utf-8"))
    msg = f"{hdr_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(settings.jwt_secret.encode("utf-8"), msg, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{hdr_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify and decode HMAC-SHA256 JWT access token."""
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token structure",
        )

    hdr_b64, payload_b64, sig_b64 = parts
    msg = f"{hdr_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(
        settings.jwt_secret.encode("utf-8"), msg, hashlib.sha256
    ).digest()

    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token encoding"
        )

    if not hmac.compare_digest(actual_sig, expected_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature"
        )

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    now = int(time.time())
    if payload.get("exp", 0) < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )

    return payload


def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Security(security_bearer),
    db: Session = Depends(get_db),
) -> AdminUserModel:
    """FastAPI Dependency for authenticating admin users via Bearer token or API Key."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()

    # Check if this is an API key (e.g. kf_live_...)
    if token.startswith("kf_live_"):
        key_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        user = db.query(AdminUserModel).filter_by(api_key_hash=key_hash, is_active=True).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key"
            )
        return user

    # Otherwise decode JWT
    payload = decode_access_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing user identity in token"
        )

    user = db.query(AdminUserModel).filter_by(username=username, is_active=True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found or inactive"
        )

    return user


def require_roles(*allowed_roles: str):
    """Decorator dependency to enforce Role-Based Access Control (RBAC)."""

    def role_checker(
        current_user: AdminUserModel = Depends(get_current_admin),
    ) -> AdminUserModel:
        if current_user.role == "SUPER_ADMIN":
            return current_user
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {list(allowed_roles)}",
            )
        return current_user

    return role_checker
