"""License Lifecycle Management Endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from keyforge.core.crypto import secure_random_id, sign_payload
from keyforge.core.key_generator import generate_human_key
from keyforge.core.license_model import (
    LicensePayload,
    LicenseStatus,
    LicenseType,
    SignedLicense,
)
from keyforge.core.profiles import ProductProfile
from keyforge.server.audit import log_audit_event
from keyforge.server.auth import get_current_admin, require_roles
from keyforge.server.db.database import get_db
from keyforge.server.db.models import (
    ActivationModel,
    AdminUserModel,
    LicenseModel,
    ProductModel,
    SigningKeyModel,
)

router = APIRouter(prefix="/api/v1/licenses", tags=["Licenses"])


def _mask_key(key: str) -> str:
    """Produce a privacy-masked license key for lists and non-privileged displays."""
    parts = key.split("-")
    if len(parts) >= 3:
        masked = [parts[0]] + ["****"] * (len(parts) - 2) + [parts[-1]]
        return "-".join(masked)
    if len(key) > 8:
        return key[:4] + "****" + key[-4:]
    return "****"


class IssueLicenseRequest(BaseModel):
    product_id: str
    customer_id: str
    customer_email: Optional[str] = None
    license_type: LicenseType = LicenseType.SUBSCRIPTION
    edition: str = "standard"
    features: Optional[List[str]] = None
    max_devices: Optional[int] = None
    duration_days: Optional[int] = None
    not_before: Optional[str] = None
    expires_at: Optional[str] = None
    allowed_versions: Optional[List[str]] = None
    metadata: Optional[dict[str, Any]] = None


class BatchIssueRequest(BaseModel):
    product_id: str
    quantity: int = Field(default=10, ge=1, le=10000)
    customer_id_prefix: str = "batch_user"
    license_type: LicenseType = LicenseType.SUBSCRIPTION
    edition: str = "standard"
    features: Optional[List[str]] = None
    max_devices: Optional[int] = None
    duration_days: Optional[int] = None
    allowed_versions: Optional[List[str]] = None
    metadata: Optional[dict[str, Any]] = None


class ActionReasonRequest(BaseModel):
    reason: Optional[str] = "Administrative action"


class RenewLicenseRequest(BaseModel):
    extend_days: Optional[int] = None
    new_expires_at: Optional[str] = None
    reason: Optional[str] = "Subscription renewal"


class TransferLicenseRequest(BaseModel):
    new_customer_id: str
    new_customer_email: Optional[str] = None
    reset_devices: bool = True
    reason: Optional[str] = "License ownership transfer"


@router.get("")
def list_licenses(
    product_id: Optional[str] = None,
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(get_current_admin),
):
    """List, search, and filter licenses with pagination."""
    query = db.query(LicenseModel)
    if product_id:
        query = query.filter(LicenseModel.product_id == product_id)
    if status:
        query = query.filter(LicenseModel.status == status.lower())
    if customer_id:
        query = query.filter(LicenseModel.customer_id == customer_id)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (LicenseModel.license_key_raw.ilike(s))
            | (LicenseModel.customer_id.ilike(s))
            | (LicenseModel.customer_email.ilike(s))
            | (LicenseModel.id.ilike(s))
        )

    total = query.count()
    items = query.order_by(LicenseModel.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [item.to_dict(include_token=False) for item in items],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def issue_license(
    req: IssueLicenseRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(require_roles("SUPER_ADMIN", "LICENSE_MANAGER")),
):
    """Issue a new cryptographically signed software license."""
    product = db.query(ProductModel).filter_by(id=req.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{req.product_id}' not found",
        )

    profile = ProductProfile.from_dict(json.loads(product.profile_json))

    # Resolve signing key
    if not product.active_key_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No active signing key configured for product '{req.product_id}'",
        )

    key_record = db.query(SigningKeyModel).filter_by(key_id=product.active_key_id).first()
    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signing key record missing",
        )

    # Determine features
    features = req.features
    if features is None:
        features = profile.features.editions.get(req.edition, profile.features.default_features)

    # Determine max devices
    max_dev = req.max_devices
    if max_dev is None:
        max_dev = profile.activation.max_devices_default

    # Determine expiration
    now_utc = datetime.now(timezone.utc)
    expires_at_str = req.expires_at
    if not expires_at_str and req.license_type != LicenseType.LIFETIME:
        days = req.duration_days
        if days is None:
            days = (
                profile.expiration.default_trial_days
                if req.license_type == LicenseType.TRIAL
                else profile.expiration.default_subscription_days
            )
        expires_at_str = (now_utc + timedelta(days=days)).isoformat()

    # Generate unique human key
    license_key = ""
    for _ in range(10):
        candidate = generate_human_key(profile.key_format)
        if not db.query(LicenseModel).filter_by(license_key_raw=candidate).first():
            license_key = candidate
            break
    if not license_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate a unique license key after multiple attempts",
        )

    license_id = secure_random_id("lic", 8)

    # Construct payload
    payload = LicensePayload(
        schema_version=1,
        license_id=license_id,
        license_key=license_key,
        product_id=req.product_id,
        license_type=req.license_type,
        edition=req.edition,
        customer_id=req.customer_id.strip(),
        customer_email=req.customer_email.strip() if req.customer_email else None,
        issued_at=now_utc.isoformat(),
        not_before=req.not_before,
        expires_at=expires_at_str,
        features=features,
        max_devices=max_dev,
        max_activations=max_dev,
        allowed_versions=req.allowed_versions or ["*"],
        metadata=req.metadata or {},
        key_version=key_record.version,
    )

    # Sign payload
    sig_b64, _ = sign_payload(payload.to_dict(), key_record.private_key_pem)

    signed_lic = SignedLicense(
        schema_version=1,
        key_id=key_record.key_id,
        algorithm="Ed25519",
        payload=payload,
        signature=sig_b64,
    )

    signed_token = signed_lic.to_token()

    db_license = LicenseModel(
        id=license_id,
        license_key_raw=license_key,
        license_key_masked=_mask_key(license_key),
        product_id=req.product_id,
        customer_id=req.customer_id.strip(),
        customer_email=req.customer_email.strip() if req.customer_email else None,
        license_type=req.license_type.value,
        edition=req.edition,
        status="active",
        issued_at=now_utc,
        not_before=datetime.fromisoformat(req.not_before) if req.not_before else None,
        expires_at=datetime.fromisoformat(expires_at_str) if expires_at_str else None,
        features_json=json.dumps(features),
        max_devices=max_dev,
        max_activations=max_dev,
        allowed_versions_json=json.dumps(req.allowed_versions or ["*"]),
        metadata_json=json.dumps(req.metadata or {}),
        key_id=key_record.key_id,
        key_version=key_record.version,
        signature=sig_b64,
        signed_token=signed_token,
    )

    db.add(db_license)
    db.commit()

    log_audit_event(
        db=db,
        event_type="license.issued",
        actor_id=current_user.username,
        license_id=license_id,
        product_id=req.product_id,
        ip_address=request.client.host if request.client else None,
        reason="Issued new license",
        details={"type": req.license_type.value, "customer_id": req.customer_id},
    )

    return db_license.to_dict(include_token=True)


@router.post("/batch", status_code=status.HTTP_201_CREATED)
def batch_issue_licenses(
    req: BatchIssueRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(require_roles("SUPER_ADMIN", "LICENSE_MANAGER")),
):
    """Batch generate up to 10,000 licenses with bulk insertion and guaranteed uniqueness."""
    product = db.query(ProductModel).filter_by(id=req.product_id).first()
    if not product or not product.active_key_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product or active signing key not found for '{req.product_id}'",
        )

    key_record = db.query(SigningKeyModel).filter_by(key_id=product.active_key_id).first()
    profile = ProductProfile.from_dict(json.loads(product.profile_json))

    now_utc = datetime.now(timezone.utc)
    features = req.features or profile.features.editions.get(req.edition, profile.features.default_features)
    max_dev = req.max_devices or profile.activation.max_devices_default

    expires_at_str = None
    if req.license_type != LicenseType.LIFETIME:
        days = req.duration_days or profile.expiration.default_subscription_days
        expires_at_str = (now_utc + timedelta(days=days)).isoformat()

    created_licenses = []
    for i in range(req.quantity):
        cust_id = f"{req.customer_id_prefix}_{i+1:04d}"
        lic_id = secure_random_id("lic", 8)
        key_str = generate_human_key(profile.key_format)

        payload = LicensePayload(
            schema_version=1,
            license_id=lic_id,
            license_key=key_str,
            product_id=req.product_id,
            license_type=req.license_type,
            edition=req.edition,
            customer_id=cust_id,
            issued_at=now_utc.isoformat(),
            expires_at=expires_at_str,
            features=features,
            max_devices=max_dev,
            max_activations=max_dev,
            allowed_versions=req.allowed_versions or ["*"],
            metadata=req.metadata or {},
            key_version=key_record.version,
        )

        sig_b64, _ = sign_payload(payload.to_dict(), key_record.private_key_pem)
        signed_lic = SignedLicense(
            schema_version=1,
            key_id=key_record.key_id,
            algorithm="Ed25519",
            payload=payload,
            signature=sig_b64,
        )

        m = LicenseModel(
            id=lic_id,
            license_key_raw=key_str,
            license_key_masked=_mask_key(key_str),
            product_id=req.product_id,
            customer_id=cust_id,
            license_type=req.license_type.value,
            edition=req.edition,
            status="active",
            issued_at=now_utc,
            expires_at=datetime.fromisoformat(expires_at_str) if expires_at_str else None,
            features_json=json.dumps(features),
            max_devices=max_dev,
            max_activations=max_dev,
            allowed_versions_json=json.dumps(req.allowed_versions or ["*"]),
            metadata_json=json.dumps(req.metadata or {}),
            key_id=key_record.key_id,
            key_version=key_record.version,
            signature=sig_b64,
            signed_token=signed_lic.to_token(),
        )
        created_licenses.append(m)

    db.bulk_save_objects(created_licenses)
    db.commit()

    log_audit_event(
        db=db,
        event_type="license.batch_issued",
        actor_id=current_user.username,
        product_id=req.product_id,
        ip_address=request.client.host if request.client else None,
        reason=f"Batch issued {req.quantity} licenses",
    )

    return {
        "quantity": req.quantity,
        "product_id": req.product_id,
        "licenses": [lic.to_dict(include_token=False) for lic in created_licenses[:20]],
        "message": f"Successfully issued {req.quantity} licenses (showing first {min(20, req.quantity)})",
    }


@router.get("/{license_id}")
def get_license(
    license_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(get_current_admin),
):
    """Get full license details and signed payload."""
    lic = db.query(LicenseModel).filter(
        (LicenseModel.id == license_id) | (LicenseModel.license_key_raw == license_id)
    ).first()
    if not lic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License '{license_id}' not found",
        )
    return lic.to_dict(include_token=True)


@router.post("/{license_id}/suspend")
def suspend_license(
    license_id: str,
    req: ActionReasonRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(require_roles("SUPER_ADMIN", "LICENSE_MANAGER", "SUPPORT")),
):
    """Temporarily suspend a license."""
    lic = db.query(LicenseModel).filter_by(id=license_id).first()
    if not lic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")

    lic.status = "suspended"
    db.commit()

    log_audit_event(
        db=db,
        event_type="license.suspended",
        actor_id=current_user.username,
        license_id=license_id,
        product_id=lic.product_id,
        ip_address=request.client.host if request.client else None,
        reason=req.reason,
    )
    return lic.to_dict(include_token=False)


@router.post("/{license_id}/reactivate")
def reactivate_license(
    license_id: str,
    req: ActionReasonRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(require_roles("SUPER_ADMIN", "LICENSE_MANAGER", "SUPPORT")),
):
    """Reactivate a suspended license."""
    lic = db.query(LicenseModel).filter_by(id=license_id).first()
    if not lic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")

    lic.status = "active"
    db.commit()

    log_audit_event(
        db=db,
        event_type="license.reactivated",
        actor_id=current_user.username,
        license_id=license_id,
        product_id=lic.product_id,
        ip_address=request.client.host if request.client else None,
        reason=req.reason,
    )
    return lic.to_dict(include_token=False)


@router.post("/{license_id}/revoke")
def revoke_license(
    license_id: str,
    req: ActionReasonRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(require_roles("SUPER_ADMIN", "LICENSE_MANAGER")),
):
    """Revoke a license permanently."""
    lic = db.query(LicenseModel).filter_by(id=license_id).first()
    if not lic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")

    lic.status = "revoked"
    db.commit()

    log_audit_event(
        db=db,
        event_type="license.revoked",
        actor_id=current_user.username,
        license_id=license_id,
        product_id=lic.product_id,
        ip_address=request.client.host if request.client else None,
        reason=req.reason,
    )
    return lic.to_dict(include_token=False)


@router.post("/{license_id}/renew")
def renew_license(
    license_id: str,
    req: RenewLicenseRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(require_roles("SUPER_ADMIN", "LICENSE_MANAGER")),
):
    """Renew or extend a license and re-sign cryptographic payload."""
    lic = db.query(LicenseModel).filter_by(id=license_id).first()
    if not lic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")

    key_record = db.query(SigningKeyModel).filter_by(key_id=lic.key_id).first()
    if not key_record:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Signing key not found")

    now = datetime.now(timezone.utc)
    base_time = now
    if lic.expires_at:
        exp_utc = lic.expires_at.replace(tzinfo=timezone.utc) if lic.expires_at.tzinfo is None else lic.expires_at.astimezone(timezone.utc)
        if exp_utc > now:
            base_time = exp_utc

    if req.new_expires_at:
        new_exp = datetime.fromisoformat(req.new_expires_at)
    elif req.extend_days:
        new_exp = base_time + timedelta(days=req.extend_days)
    else:
        new_exp = base_time + timedelta(days=365)

    lic.expires_at = new_exp
    lic.status = "active"

    # Re-sign payload
    payload = LicensePayload(
        schema_version=1,
        license_id=lic.id,
        license_key=lic.license_key_raw,
        product_id=lic.product_id,
        license_type=LicenseType(lic.license_type),
        edition=lic.edition,
        customer_id=lic.customer_id,
        customer_email=lic.customer_email,
        issued_at=lic.issued_at.isoformat(),
        not_before=lic.not_before.isoformat() if lic.not_before else None,
        expires_at=new_exp.isoformat(),
        features=json.loads(lic.features_json),
        max_devices=lic.max_devices,
        max_activations=lic.max_activations,
        allowed_versions=json.loads(lic.allowed_versions_json),
        metadata=json.loads(lic.metadata_json),
        key_version=lic.key_version,
    )

    sig_b64, _ = sign_payload(payload.to_dict(), key_record.private_key_pem)
    signed_lic = SignedLicense(
        schema_version=1,
        key_id=lic.key_id,
        algorithm="Ed25519",
        payload=payload,
        signature=sig_b64,
    )

    lic.signature = sig_b64
    lic.signed_token = signed_lic.to_token()
    db.commit()

    log_audit_event(
        db=db,
        event_type="license.renewed",
        actor_id=current_user.username,
        license_id=license_id,
        product_id=lic.product_id,
        ip_address=request.client.host if request.client else None,
        reason=req.reason,
        details={"new_expires_at": new_exp.isoformat()},
    )
    return lic.to_dict(include_token=True)


@router.post("/{license_id}/transfer")
def transfer_license(
    license_id: str,
    req: TransferLicenseRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(require_roles("SUPER_ADMIN", "LICENSE_MANAGER")),
):
    """Transfer license ownership to a new customer and optionally reset active seats."""
    lic = db.query(LicenseModel).filter_by(id=license_id).first()
    if not lic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")

    old_customer = lic.customer_id
    lic.customer_id = req.new_customer_id.strip()
    if req.new_customer_email:
        lic.customer_email = req.new_customer_email.strip()

    if req.reset_devices:
        db.query(ActivationModel).filter_by(license_id=license_id).delete()

    db.commit()

    log_audit_event(
        db=db,
        event_type="license.transferred",
        actor_id=current_user.username,
        license_id=license_id,
        product_id=lic.product_id,
        ip_address=request.client.host if request.client else None,
        reason=req.reason,
        details={"previous_customer": old_customer, "new_customer": req.new_customer_id},
    )
    return lic.to_dict(include_token=True)


@router.get("/{license_id}/export")
def export_license(
    license_id: str,
    format: str = Query(default="json", pattern="^(json|token|lic_file|raw_key)$"),
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(get_current_admin),
):
    """Export license in various distribution formats."""
    lic = db.query(LicenseModel).filter(
        (LicenseModel.id == license_id) | (LicenseModel.license_key_raw == license_id)
    ).first()
    if not lic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")

    if format == "raw_key":
        return {"license_key": lic.license_key_raw}
    elif format == "token":
        return {"token": lic.signed_token}
    elif format == "lic_file":
        payload = LicensePayload(
            schema_version=1,
            license_id=lic.id,
            license_key=lic.license_key_raw,
            product_id=lic.product_id,
            license_type=LicenseType(lic.license_type),
            edition=lic.edition,
            customer_id=lic.customer_id,
            customer_email=lic.customer_email,
            issued_at=lic.issued_at.isoformat(),
            not_before=lic.not_before.isoformat() if lic.not_before else None,
            expires_at=lic.expires_at.isoformat() if lic.expires_at else None,
            features=json.loads(lic.features_json),
            max_devices=lic.max_devices,
            max_activations=lic.max_activations,
            allowed_versions=json.loads(lic.allowed_versions_json),
            metadata=json.loads(lic.metadata_json),
            key_version=lic.key_version,
        )
        signed_lic = SignedLicense(
            schema_version=1,
            key_id=lic.key_id,
            algorithm="Ed25519",
            payload=payload,
            signature=lic.signature,
        )
        return {
            "filename": f"{lic.product_id}_{lic.id}.lic",
            "content": signed_lic.to_json(indent=2),
        }

    return lic.to_dict(include_token=True)
