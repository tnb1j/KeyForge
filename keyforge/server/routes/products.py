"""Product Catalog and Licensing Policy Management Endpoints."""

from __future__ import annotations

import json
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from keyforge.core.crypto import generate_keypair
from keyforge.core.profiles import ProductProfile, get_default_profile
from keyforge.server.audit import log_audit_event
from keyforge.server.auth import get_current_admin, require_roles
from keyforge.server.db.database import get_db
from keyforge.server.db.models import AdminUserModel, ProductModel, SigningKeyModel

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


class CreateProductRequest(BaseModel):
    id: str = Field(..., description="Unique slug for the product, e.g. my-app")
    name: str = Field(..., description="Display name of the product")
    version: str = Field(default="1.0.0")
    description: str = Field(default="")
    profile_preset: str | None = Field(default=None, description="Preset template: desktop, saas_api, air_gapped")
    custom_profile: dict[str, Any] | None = Field(default=None, description="Full custom ProductProfile JSON dict")


class UpdateProductRequest(BaseModel):
    name: str | None = None
    version: str | None = None
    description: str | None = None
    custom_profile: dict[str, Any] | None = None


@router.get("")
def list_products(
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(get_current_admin),
):
    """List all registered products and their configurations."""
    prods = db.query(ProductModel).all()
    return [p.to_dict() for p in prods]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_product(
    req: CreateProductRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(require_roles("SUPER_ADMIN", "LICENSE_MANAGER")),
):
    """Register a new product with an active profile and auto-generate initial Ed25519 signing keypair."""
    prod_id = req.id.strip().lower()
    existing = db.query(ProductModel).filter_by(id=prod_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with ID '{prod_id}' already exists",
        )

    # Determine profile
    if req.custom_profile:
        profile = ProductProfile.from_dict(req.custom_profile)
        profile.product.id = prod_id
        profile.product.name = req.name
        profile.product.version = req.version
    elif req.profile_preset:
        profile = get_default_profile(req.profile_preset)
        profile.product.id = prod_id
        profile.product.name = req.name
        profile.product.version = req.version
    else:
        profile = get_default_profile("desktop")
        profile.product.id = prod_id
        profile.product.name = req.name
        profile.product.version = req.version

    # Generate initial Ed25519 keypair for the product
    keypair = generate_keypair(version=1)
    signing_key = SigningKeyModel(
        key_id=keypair.key_id,
        product_id=prod_id,
        version=1,
        algorithm="Ed25519",
        public_key_pem=keypair.public_key_pem,
        public_key_hex=keypair.public_key_hex,
        private_key_pem=keypair.private_key_pem or "",
        fingerprint=keypair.fingerprint,
        status="active",
    )

    product = ProductModel(
        id=prod_id,
        name=req.name.strip(),
        version=req.version.strip(),
        description=req.description.strip(),
        profile_json=profile.to_json(),
        active_key_id=keypair.key_id,
    )

    db.add(product)
    db.add(signing_key)
    db.commit()

    log_audit_event(
        db=db,
        event_type="product.created",
        actor_id=current_user.username,
        product_id=prod_id,
        ip_address=request.client.host if request.client else None,
        reason=f"Created product {req.name}",
    )

    return product.to_dict()


@router.get("/{product_id}")
def get_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(get_current_admin),
):
    """Retrieve detailed product information and policy configuration."""
    prod = db.query(ProductModel).filter_by(id=product_id).first()
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found",
        )
    return prod.to_dict()


@router.put("/{product_id}")
def update_product(
    product_id: str,
    req: UpdateProductRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(require_roles("SUPER_ADMIN", "LICENSE_MANAGER")),
):
    """Update product metadata or licensing configuration profile."""
    prod = db.query(ProductModel).filter_by(id=product_id).first()
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found",
        )

    if req.name is not None:
        prod.name = req.name.strip()
    if req.version is not None:
        prod.version = req.version.strip()
    if req.description is not None:
        prod.description = req.description.strip()
    if req.custom_profile is not None:
        profile = ProductProfile.from_dict(req.custom_profile)
        prod.profile_json = profile.to_json()

    db.commit()

    log_audit_event(
        db=db,
        event_type="product.updated",
        actor_id=current_user.username,
        product_id=product_id,
        ip_address=request.client.host if request.client else None,
        reason="Updated product settings",
    )

    return prod.to_dict()


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(require_roles("SUPER_ADMIN")),
):
    """Delete product and associated licenses and keys."""
    prod = db.query(ProductModel).filter_by(id=product_id).first()
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found",
        )

    db.delete(prod)
    db.commit()

    log_audit_event(
        db=db,
        event_type="product.deleted",
        actor_id=current_user.username,
        product_id=product_id,
        ip_address=request.client.host if request.client else None,
        reason="Deleted product",
    )
    return None
