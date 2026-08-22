"""Privacy-Preserving Device and Installation Identification."""

from __future__ import annotations

import hashlib
import platform
import uuid
from pathlib import Path


def get_installation_id(storage_dir: Path | None = None) -> str:
    """Retrieve or generate a persistent, anonymous installation UUID."""
    if storage_dir is None:
        storage_dir = Path.home() / ".keyforge"
    storage_dir.mkdir(parents=True, exist_ok=True)
    id_file = storage_dir / ".inst_id"

    if id_file.exists():
        try:
            return id_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    new_id = f"inst_{uuid.uuid4().hex}"
    try:
        id_file.write_text(new_id, encoding="utf-8")
    except Exception:
        pass
    return new_id


def get_device_fingerprint() -> str:
    """Generate a privacy-preserving SHA-256 device identifier hash."""
    sys_info = [
        platform.system(),
        platform.machine(),
        platform.processor() or "unknown_proc",
    ]
    raw_str = ":".join(sys_info)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
