"""Server Configuration and Environment Management."""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from pydantic import BaseModel, Field


def _default_db_url() -> str:
    env_val = os.getenv("KEYFORGE_DB_URL")
    if env_val:
        if env_val.startswith("postgres://"):
            return env_val.replace("postgres://", "postgresql://", 1)
        return env_val
    if "VERCEL" in os.environ or "AWS_LAMBDA_FUNCTION_NAME" in os.environ:
        return "sqlite:////tmp/keyforge.db"
    return "sqlite:///./keyforge.db"


class ServerSettings(BaseModel):
    """Global configuration settings for KeyForge Server."""

    env: str = Field(default="development")
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    database_url: str = Field(default_factory=_default_db_url)
    jwt_secret: str = Field(
        default_factory=lambda: os.getenv(
            "KEYFORGE_JWT_SECRET", secrets.token_hex(32)
        )
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=1440)  # 24 hours
    admin_default_username: str = Field(
        default_factory=lambda: os.getenv("KEYFORGE_ADMIN_USER", "admin")
    )
    admin_default_password: str = Field(
        default_factory=lambda: os.getenv("KEYFORGE_ADMIN_PASS", "KeyForgeAdmin2026!")
    )
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_validate_rpm: int = Field(default=120)  # 120 per min per IP
    rate_limit_activate_rpm: int = Field(default=30)   # 30 per min per IP
    rate_limit_login_rpm: int = Field(default=10)      # 10 per min per IP
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["*"])


settings = ServerSettings()
