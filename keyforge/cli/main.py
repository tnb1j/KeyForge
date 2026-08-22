"""KeyForge Administrative Command-Line Interface (CLI)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
import uvicorn

from keyforge import __version__
from keyforge.core.crypto import (
    Ed25519KeyManager,
    KeyPair,
    generate_keypair,
    secure_random_id,
    sign_payload,
)
from keyforge.core.key_generator import generate_human_key
from keyforge.core.license_model import (
    LicensePayload,
    LicenseType,
    SignedLicense,
    ValidationStatus,
)
from keyforge.core.profiles import get_default_profile
from keyforge.core.validator import LicenseValidator
from keyforge.server.config import settings
from keyforge.server.db.database import SessionLocal, init_db
from keyforge.server.db.models import (
    AuditEventModel,
    LicenseModel,
    ProductModel,
    SigningKeyModel,
)


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the KeyForge Licensing Server."""
    print(f"[*] Initializing KeyForge Server v{__version__} on {args.host}:{args.port}...")
    init_db()
    uvicorn.run(
        "keyforge.server.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def cmd_product_list(args: argparse.Namespace) -> None:
    """List registered products."""
    db = SessionLocal()
    try:
        prods = db.query(ProductModel).all()
        print(f"\nRegistered Products ({len(prods)}):")
        print(f"{'ID':<20} {'NAME':<30} {'VERSION':<10} {'ACTIVE KEY':<24}")
        print("-" * 88)
        for p in prods:
            print(f"{p.id:<20} {p.name:<30} {p.version:<10} {str(p.active_key_id):<24}")
    finally:
        db.close()


def cmd_key_list(args: argparse.Namespace) -> None:
    """List public verification keys."""
    db = SessionLocal()
    try:
        keys = db.query(SigningKeyModel).all()
        print(f"\nCryptographic Signing Keys ({len(keys)}):")
        print(f"{'KEY ID':<24} {'PRODUCT':<18} {'VER':<5} {'STATUS':<10} {'FINGERPRINT':<20}")
        print("-" * 82)
        for k in keys:
            print(f"{k.key_id:<24} {k.product_id:<18} {k.version:<5} {k.status:<10} {k.fingerprint[:16]}...")
    finally:
        db.close()


def cmd_license_issue(args: argparse.Namespace) -> None:
    """Issue a new license from the CLI."""
    db = SessionLocal()
    try:
        prod = db.query(ProductModel).filter_by(id=args.product).first()
        if not prod or not prod.active_key_id:
            print(f"[!] Error: Product '{args.product}' or active key not found.", file=sys.stderr)
            return

        key_rec = db.query(SigningKeyModel).filter_by(key_id=prod.active_key_id).first()
        profile = get_default_profile("desktop")

        lic_id = secure_random_id("lic", 8)
        raw_key = generate_human_key(profile.key_format)
        features = [f.strip() for f in args.features.split(",")] if args.features else ["core", "export"]

        now_utc = datetime.now(timezone.utc)
        payload = LicensePayload(
            schema_version=1,
            license_id=lic_id,
            license_key=raw_key,
            product_id=args.product,
            license_type=LicenseType(args.type),
            edition=args.edition,
            customer_id=args.customer,
            issued_at=now_utc.isoformat(),
            features=features,
            max_devices=args.devices,
            key_version=key_rec.version,
        )

        sig_b64, _ = sign_payload(payload.to_dict(), key_rec.private_key_pem)
        signed_lic = SignedLicense(
            schema_version=1,
            key_id=key_rec.key_id,
            algorithm="Ed25519",
            payload=payload,
            signature=sig_b64,
        )

        db_lic = LicenseModel(
            id=lic_id,
            license_key_raw=raw_key,
            license_key_masked=raw_key[:4] + "****" + raw_key[-4:],
            product_id=args.product,
            customer_id=args.customer,
            license_type=args.type,
            edition=args.edition,
            status="active",
            issued_at=now_utc,
            features_json=json.dumps(features),
            max_devices=args.devices,
            key_id=key_rec.key_id,
            key_version=key_rec.version,
            signature=sig_b64,
            signed_token=signed_lic.to_token(),
        )
        db.add(db_lic)
        db.commit()

        print("\n[+] License Issued Successfully:")
        print(f"    License ID:   {lic_id}")
        print(f"    License Key:  {raw_key}")
        print(f"    Product:      {args.product}")
        print(f"    Customer:     {args.customer}")
        print(f"    Token:        {signed_lic.to_token()}\n")
    finally:
        db.close()


def cmd_license_inspect(args: argparse.Namespace) -> None:
    """Inspect and decode a license token or file."""
    try:
        signed_lic = SignedLicense.from_token(args.token)
        print("\n[+] Decoded License Claims:")
        print(json.dumps(signed_lic.to_dict(), indent=2))
    except Exception as e:
        print(f"[!] Failed to decode license: {e}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="keyforge",
        description="KeyForge Universal Licensing Platform Management CLI",
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Serve command
    p_serve = subparsers.add_parser("serve", help="Start KeyForge API & Dashboard Server")
    p_serve.add_argument("--host", default=settings.host, help="Bind host")
    p_serve.add_argument("--port", type=int, default=settings.port, help="Bind port")
    p_serve.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # Products command
    p_prod = subparsers.add_parser("products", help="Manage products")
    p_prod.add_argument("action", choices=["list"], help="Product action")

    # Keys command
    p_key = subparsers.add_parser("keys", help="Manage signing keys")
    p_key.add_argument("action", choices=["list"], help="Key vault action")

    # License issue command
    p_issue = subparsers.add_parser("issue", help="Issue a new software license")
    p_issue.add_argument("--product", default="desktop-app", help="Product ID")
    p_issue.add_argument("--customer", required=True, help="Customer ID / Email")
    p_issue.add_argument("--type", default="subscription", choices=["subscription", "lifetime", "trial", "enterprise"])
    p_issue.add_argument("--edition", default="pro", help="Product edition")
    p_issue.add_argument("--features", default="core,export,automation", help="Comma-separated features")
    p_issue.add_argument("--devices", type=int, default=3, help="Max allowed devices")

    # License inspect command
    p_insp = subparsers.add_parser("inspect", help="Inspect and decode a license token")
    p_insp.add_argument("token", help="Armored token (kf1...)")

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "products":
        cmd_product_list(args)
    elif args.command == "keys":
        cmd_key_list(args)
    elif args.command == "issue":
        cmd_license_issue(args)
    elif args.command == "inspect":
        cmd_license_inspect(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
