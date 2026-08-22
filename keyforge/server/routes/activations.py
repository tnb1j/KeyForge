"""Device Activation, Heartbeat Validation, and Seat Management Endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from keyforge.core.crypto import secure_random_id, sign_payload
from keyforge.core.license_model import (
    ActivationReceipt,
    LicenseStatus,
    ValidationResult,
    ValidationStatus,
)
from keyforge.core.validator import _check_version_compatibility, _parse_iso_datetime
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
from keyforge.server.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/licenses", tags=["Activations"])


def _mask_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.*.*"
    return "masked_ip"


class ActivateRequest(BaseModel):
    license_key: str
    product_id: str
    installation_id: str
    device_fingerprint: str
    device_name: Optional[str] = None
    platform: Optional[str] = None
    client_version: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class ValidateRequest(BaseModel):
    license_key: str
    product_id: str
    installation_id: Optional[str] = None
    client_version: Optional[str] = None


class DeactivateRequest(BaseModel):
    license_key: str
    installation_id: str
    reason: Optional[str] = "User initiated deactivation"


@router.post("/activate")
def activate_device(
    req: ActivateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Activate a software installation on a specific client machine/device."""
    limiter.check_rate_limit(request, action="activate", max_requests_per_minute=30)

    # Lookup license by raw key or ID
    lic = db.query(LicenseModel).filter(
        (LicenseModel.license_key_raw == req.license_key.strip())
        | (LicenseModel.id == req.license_key.strip())
    ).first()

    if not lic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or unrecognized license key",
        )

    # Validate product match
    if lic.product_id != req.product_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"License does not belong to product '{req.product_id}'",
        )

    # Validate license status
    if lic.status == "revoked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="License has been revoked by administrator",
        )
    if lic.status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="License is temporarily suspended",
        )

    now = datetime.now(timezone.utc)

    # Check expiration
    if lic.expires_at and now > lic.expires_at.replace(tzinfo=timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"License expired at {lic.expires_at.isoformat()}",
        )

    # Check version policy
    allowed_vers = json.loads(lic.allowed_versions_json)
    if req.client_version and not _check_version_compatibility(req.client_version, allowed_vers):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Client version '{req.client_version}' is not permitted by license policy ({allowed_vers})",
        )

    # Check if installation is already activated on this license
    existing_act = db.query(ActivationModel).filter_by(
        license_id=lic.id, installation_id=req.installation_id.strip()
    ).first()

    key_record = db.query(SigningKeyModel).filter_by(key_id=lic.key_id).first()
    if not key_record:
        raise HTTPException(status_code=500, detail="Signing key missing")

    if existing_act:
        existing_act.status = "active"
        existing_act.last_heartbeat_at = now
        existing_act.client_version = req.client_version
        existing_act.ip_address_masked = _mask_ip(request.client.host if request.client else None)
        db.commit()

        receipt_payload = {
            "activation_id": existing_act.id,
            "license_id": lic.id,
            "product_id": lic.product_id,
            "installation_id": existing_act.installation_id,
            "device_fingerprint": existing_act.device_fingerprint,
            "activated_at": existing_act.activated_at.isoformat(),
            "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
        }
        sig, _ = sign_payload(receipt_payload, key_record.private_key_pem)

        receipt = ActivationReceipt(
            activation_id=existing_act.id,
            license_id=lic.id,
            product_id=lic.product_id,
            installation_id=existing_act.installation_id,
            device_fingerprint=existing_act.device_fingerprint,
            activated_at=existing_act.activated_at.isoformat(),
            expires_at=lic.expires_at.isoformat() if lic.expires_at else None,
            key_id=key_record.key_id,
            signature=sig,
        )

        return {
            "success": True,
            "message": "Installation reactivated successfully",
            "license": lic.to_dict(include_token=True),
            "activation": receipt.to_dict(),
        }

    # Count current active seats
    active_count = db.query(ActivationModel).filter_by(
        license_id=lic.id, status="active"
    ).count()

    if active_count >= lic.max_devices:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Activation seat limit reached ({active_count}/{lic.max_devices} devices active). Deactivate an existing device to proceed.",
        )

    act_id = secure_random_id("act", 8)
    new_act = ActivationModel(
        id=act_id,
        license_id=lic.id,
        installation_id=req.installation_id.strip(),
        device_fingerprint=req.device_fingerprint.strip(),
        device_name=req.device_name,
        platform=req.platform,
        client_version=req.client_version,
        ip_address_masked=_mask_ip(request.client.host if request.client else None),
        status="active",
        activated_at=now,
        last_heartbeat_at=now,
        metadata_json=json.dumps(req.metadata or {}),
    )
    db.add(new_act)
    db.commit()

    receipt_payload = {
        "activation_id": act_id,
        "license_id": lic.id,
        "product_id": lic.product_id,
        "installation_id": req.installation_id.strip(),
        "device_fingerprint": req.device_fingerprint.strip(),
        "activated_at": now.isoformat(),
        "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
    }
    sig, _ = sign_payload(receipt_payload, key_record.private_key_pem)

    receipt = ActivationReceipt(
        activation_id=act_id,
        license_id=lic.id,
        product_id=lic.product_id,
        installation_id=req.installation_id.strip(),
        device_fingerprint=req.device_fingerprint.strip(),
        activated_at=now.isoformat(),
        expires_at=lic.expires_at.isoformat() if lic.expires_at else None,
        key_id=key_record.key_id,
        signature=sig,
    )

    log_audit_event(
        db=db,
        event_type="license.activated",
        actor_id=lic.customer_id,
        actor_type="client",
        license_id=lic.id,
        product_id=lic.product_id,
        ip_address=request.client.host if request.client else None,
        reason=f"Activated device {req.device_name or req.installation_id}",
        details={"installation_id": req.installation_id, "platform": req.platform},
    )

    return {
        "success": True,
        "message": "Device activated successfully",
        "license": lic.to_dict(include_token=True),
        "activation": receipt.to_dict(),
    }


@router.post("/validate")
def validate_license_online(
    req: ValidateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Online validation and heartbeat check."""
    limiter.check_rate_limit(request, action="validate", max_requests_per_minute=120)

    lic = db.query(LicenseModel).filter(
        (LicenseModel.license_key_raw == req.license_key.strip())
        | (LicenseModel.id == req.license_key.strip())
    ).first()

    if not lic:
        return ValidationResult(
            is_valid=False,
            status=ValidationStatus.UNKNOWN_LICENSE,
            message="License not found",
        ).to_dict()

    if lic.product_id != req.product_id.strip():
        return ValidationResult(
            is_valid=False,
            status=ValidationStatus.PRODUCT_MISMATCH,
            message="Product mismatch",
            license_id=lic.id,
            product_id=lic.product_id,
        ).to_dict()

    if lic.status == "revoked":
        return ValidationResult(
            is_valid=False,
            status=ValidationStatus.REVOKED,
            message="License has been revoked",
            license_id=lic.id,
            product_id=lic.product_id,
        ).to_dict()

    if lic.status == "suspended":
        return ValidationResult(
            is_valid=False,
            status=ValidationStatus.SUSPENDED,
            message="License is suspended",
            license_id=lic.id,
            product_id=lic.product_id,
        ).to_dict()

    now = datetime.now(timezone.utc)
    is_exp = False
    days_left = None
    if lic.expires_at:
        exp_utc = lic.expires_at.replace(tzinfo=timezone.utc)
        if now > exp_utc:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.EXPIRED,
                message=f"License expired at {lic.expires_at.isoformat()}",
                license_id=lic.id,
                product_id=lic.product_id,
                expires_at=lic.expires_at.isoformat(),
                days_remaining=0,
                is_expired=True,
            ).to_dict()
        diff = exp_utc - now
        days_left = max(0, diff.days)

    # Check version policy
    allowed_vers = json.loads(lic.allowed_versions_json)
    if req.client_version and not _check_version_compatibility(req.client_version, allowed_vers):
        return ValidationResult(
            is_valid=False,
            status=ValidationStatus.VERSION_NOT_SUPPORTED,
            message=f"Version '{req.client_version}' not supported",
            license_id=lic.id,
            product_id=lic.product_id,
        ).to_dict()

    # Update heartbeat if installation_id provided
    if req.installation_id:
        act = db.query(ActivationModel).filter_by(
            license_id=lic.id, installation_id=req.installation_id.strip()
        ).first()
        if act and act.status == "active":
            act.last_heartbeat_at = now
            db.commit()

    active_devices = db.query(ActivationModel).filter_by(
        license_id=lic.id, status="active"
    ).count()

    features = json.loads(lic.features_json)
    metadata = json.loads(lic.metadata_json)

    return ValidationResult(
        is_valid=True,
        status=ValidationStatus.VALID,
        message="License is active and valid",
        license_id=lic.id,
        product_id=lic.product_id,
        edition=lic.edition,
        features=features,
        expires_at=lic.expires_at.isoformat() if lic.expires_at else None,
        days_remaining=days_left,
        is_expired=False,
        allowed_devices=lic.max_devices,
        active_devices=active_devices,
        customer_id=lic.customer_id,
        metadata=metadata,
    ).to_dict()


@router.post("/deactivate")
def deactivate_device(
    req: DeactivateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Deactivate an installation and free up a device seat."""
    lic = db.query(LicenseModel).filter(
        (LicenseModel.license_key_raw == req.license_key.strip())
        | (LicenseModel.id == req.license_key.strip())
    ).first()

    if not lic:
        raise HTTPException(status_code=404, detail="License not found")

    act = db.query(ActivationModel).filter_by(
        license_id=lic.id, installation_id=req.installation_id.strip()
    ).first()

    if not act:
        return {"success": True, "message": "Installation was not active"}

    act.status = "deactivated"
    db.commit()

    log_audit_event(
        db=db,
        event_type="license.deactivated",
        actor_id=lic.customer_id,
        actor_type="client",
        license_id=lic.id,
        product_id=lic.product_id,
        ip_address=request.client.host if request.client else None,
        reason=req.reason,
        details={"installation_id": req.installation_id},
    )

    return {"success": True, "message": "Device deactivated successfully"}


@router.get("/{license_id}/devices")
def list_license_devices(
    license_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(get_current_admin),
):
    """List all registered device activations for a license."""
    lic = db.query(LicenseModel).filter(
        (LicenseModel.id == license_id) | (LicenseModel.license_key_raw == license_id)
    ).first()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")

    acts = db.query(ActivationModel).filter_by(license_id=lic.id).all()
    return [a.to_dict() for a in acts]


@router.delete("/{license_id}/devices/{installation_id}")
def revoke_device_activation(
    license_id: str,
    installation_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(require_roles("SUPER_ADMIN", "LICENSE_MANAGER", "SUPPORT")),
):
    """Administratively revoke or remove a specific device activation."""
    lic = db.query(LicenseModel).filter(
        (LicenseModel.id == license_id) | (LicenseModel.license_key_raw == license_id)
    ).first()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")

    act = db.query(ActivationModel).filter_by(
        license_id=lic.id, installation_id=installation_id.strip()
    ).first()
    if not act:
        raise HTTPException(status_code=404, detail="Device activation not found")

    db.delete(act)
    db.commit()

    log_audit_event(
        db=db,
        event_type="license.device_revoked",
        actor_id=current_user.username,
        license_id=lic.id,
        product_id=lic.product_id,
        ip_address=request.client.host if request.client else None,
        reason=f"Revoked seat for installation {installation_id}",
    )
    return {"message": "Device activation removed successfully"}


@router.post("/{license_id}/reset-devices")
def reset_all_devices(
    license_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUserModel = Depends(require_roles("SUPER_ADMIN", "LICENSE_MANAGER", "SUPPORT")),
):
    """Clear all active device activations for a license."""
    lic = db.query(LicenseModel).filter(
        (LicenseModel.id == license_id) | (LicenseModel.license_key_raw == license_id)
    ).first()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")

    count = db.query(ActivationModel).filter_by(license_id=lic.id).delete()
    db.commit()

    log_audit_event(
        db=db,
        event_type="license.devices_reset",
        actor_id=current_user.username,
        license_id=lic.id,
        product_id=lic.product_id,
        ip_address=request.client.host if request.client else None,
        reason=f"Reset {count} active device seats",
    )
    return {"message": f"Successfully reset {count} device activations"}
