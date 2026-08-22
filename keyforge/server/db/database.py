"""Database Engine Initialization, Session Management, and Seed Setup."""

from __future__ import annotations

import json
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from keyforge.core.crypto import generate_keypair, secure_random_id
from keyforge.core.profiles import get_default_profile
from keyforge.server.config import settings
from keyforge.server.db.models import (
    AdminUserModel,
    Base,
    ProductModel,
    SigningKeyModel,
)

# Connect to database (SQLite support check_same_thread=False)
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all database tables and seed baseline admin user and product."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if Admin user exists
        admin = db.query(AdminUserModel).filter_by(username=settings.admin_default_username).first()
        if not admin:
            from keyforge.server.auth import hash_password

            admin_user = AdminUserModel(
                id=secure_random_id("usr", 8),
                username=settings.admin_default_username,
                password_hash=hash_password(settings.admin_default_password),
                role="SUPER_ADMIN",
                is_active=True,
            )
            db.add(admin_user)
            db.commit()

        # Ensure products have valid active signing keys (self-healing)
        products = db.query(ProductModel).all()
        if not products:
            profile = get_default_profile("desktop")
            keypair = generate_keypair(version=1, key_id="key-v1-desktop-init")

            db_key = SigningKeyModel(
                key_id=keypair.key_id,
                product_id="desktop-app",
                version=1,
                algorithm="Ed25519",
                public_key_pem=keypair.public_key_pem,
                public_key_hex=keypair.public_key_hex,
                private_key_pem=keypair.private_key_pem or "",
                fingerprint=keypair.fingerprint,
                status="active",
            )

            db_prod = ProductModel(
                id="desktop-app",
                name="Desktop Application",
                version="1.0.0",
                description="Default sample desktop application with offline Ed25519 validation",
                profile_json=profile.to_json(),
                active_key_id=keypair.key_id,
            )
            db.add(db_prod)
            db.add(db_key)
            db.commit()
        else:
            for p in products:
                key_exists = (
                    db.query(SigningKeyModel).filter_by(key_id=p.active_key_id).first()
                    if p.active_key_id
                    else None
                )
                if not key_exists:
                    keypair = generate_keypair(version=1, key_id=f"key-v1-{p.id}-auto")
                    db_key = SigningKeyModel(
                        key_id=keypair.key_id,
                        product_id=p.id,
                        version=1,
                        algorithm="Ed25519",
                        public_key_pem=keypair.public_key_pem,
                        public_key_hex=keypair.public_key_hex,
                        private_key_pem=keypair.private_key_pem or "",
                        fingerprint=keypair.fingerprint,
                        status="active",
                    )
                    p.active_key_id = keypair.key_id
                    db.add(db_key)
                    db.commit()
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency yielding a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
