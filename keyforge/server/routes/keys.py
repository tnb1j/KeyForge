"""Cryptographic Key Management and Public Verification Key Vault Endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from keyforge.core.crypto import generate_keypair
from keyforge.server.audit import log_audit_event
from keyforge.server.auth import get_current_admin, require_roles
from keyforge.server.db.database import get_db
from keyforge.server.db.models import AdminUserModel, ProductModel, SigningKeyModel

router = APIRouter(prefix="/api/v1/keys", tags=["Key Vault"])


@router.get("")
def list_public_keys(db: Session = Depends(get_db)):
    """List all public verification keys across all products (Public/Client-Safe)."""
    keys = db.query(SigningKeyModel).all()
    return [k.to_public_dict() for k in keys]


@router.get("/{product_id}/active")
def get_active_product_key(product_id: str, db: Session = Depends(get_db)):
    """Retrieve the current active public verification key for a given product."""
    product = db.query(ProductModel).filter_by(id=product_id).first()
    if not product or not product.active_key_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active signing key found for product '{product_id}'",
        )

    key = db.query(SigningKeyModel).filter_by(key_id=product.active_key_id).first()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signing key record missing from vault",
        )

    return key.to_public_dict()


@router.post("/{product_id}/rotate")
def rotate_signing_key(
    product_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(require_roles("SUPER_ADMIN")),
):
    """Rotate the product's Ed25519 signing key.

    Generates a new keypair, increments the key version, marks prior active key as 'rotated',
    and updates the active product key. Previous keys remain valid for verifying existing licenses.
    """
    product = db.query(ProductModel).filter_by(id=product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found",
        )

    current_active_key = None
    if product.active_key_id:
        current_active_key = db.query(SigningKeyModel).filter_by(key_id=product.active_key_id).first()

    next_version = (current_active_key.version + 1) if current_active_key else 1

    if current_active_key:
        current_active_key.status = "rotated"

    new_keypair = generate_keypair(version=next_version)
    new_db_key = SigningKeyModel(
        key_id=new_keypair.key_id,
        product_id=product_id,
        version=next_version,
        algorithm="Ed25519",
        public_key_pem=new_keypair.public_key_pem,
        public_key_hex=new_keypair.public_key_hex,
        private_key_pem=new_keypair.private_key_pem or "",
        fingerprint=new_keypair.fingerprint,
        status="active",
    )

    product.active_key_id = new_keypair.key_id
    db.add(new_db_key)
    db.commit()

    log_audit_event(
        db=db,
        event_type="key.rotated",
        actor_id=current_user.username,
        product_id=product_id,
        ip_address=request.client.host if request.client else None,
        reason=f"Rotated key to version {next_version} ({new_keypair.key_id})",
    )

    return {
        "message": "Key rotated successfully",
        "new_key": new_db_key.to_public_dict(),
        "previous_key_id": current_active_key.key_id if current_active_key else None,
    }
