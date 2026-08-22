"""Pluggable Local License Storage Adapters (File, Memory, Windows DPAPI)."""

from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import platform
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


class BaseLicenseStorage(ABC):
    """Abstract base class for persistent client license storage."""

    @abstractmethod
    def save_license(self, license_data: str) -> None:
        """Persist license token or JSON string."""
        pass

    @abstractmethod
    def load_license(self) -> Optional[str]:
        """Load persisted license token or JSON string."""
        pass

    @abstractmethod
    def clear_license(self) -> None:
        """Remove stored license."""
        pass


class MemoryLicenseStorage(BaseLicenseStorage):
    """Volatile in-memory license storage."""

    def __init__(self) -> None:
        self._data: Optional[str] = None

    def save_license(self, license_data: str) -> None:
        self._data = license_data

    def load_license(self) -> Optional[str]:
        return self._data

    def clear_license(self) -> None:
        self._data = None


class FileLicenseStorage(BaseLicenseStorage):
    """Local filesystem storage with integrity checksum verification."""

    def __init__(self, file_path: str | Path | None = None) -> None:
        if file_path is None:
            home = Path.home()
            self.file_path = home / ".keyforge" / "license.lic"
        else:
            self.file_path = Path(file_path)

        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def save_license(self, license_data: str) -> None:
        payload_bytes = license_data.encode("utf-8")
        chk = hashlib.sha256(payload_bytes).hexdigest()
        container = {
            "version": 1,
            "data": license_data,
            "checksum": chk,
        }
        self.file_path.write_text(json.dumps(container, indent=2), encoding="utf-8")

    def load_license(self) -> Optional[str]:
        if not self.file_path.exists():
            return None
        try:
            raw = self.file_path.read_text(encoding="utf-8")
            container = json.loads(raw)
            data = container.get("data", "")
            expected_chk = container.get("checksum", "")
            actual_chk = hashlib.sha256(data.encode("utf-8")).hexdigest()
            if actual_chk != expected_chk:
                return None  # Tampered or corrupted file
            return data
        except Exception:
            return None

    def clear_license(self) -> None:
        if self.file_path.exists():
            try:
                self.file_path.unlink()
            except OSError:
                pass


class WindowsDPAPILicenseStorage(BaseLicenseStorage):
    """Windows Data Protection API (DPAPI) storage using machine/user encryption keys."""

    def __init__(self, file_path: str | Path | None = None) -> None:
        if file_path is None:
            appdata = os.getenv("APPDATA", str(Path.home()))
            self.file_path = Path(appdata) / "KeyForge" / "encrypted_license.dat"
        else:
            self.file_path = Path(file_path)

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.is_windows = platform.system() == "Windows"
        self._fallback = FileLicenseStorage(self.file_path.with_suffix(".lic"))

    def _dpapi_protect(self, data: bytes) -> bytes:
        if not self.is_windows:
            return data

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", ctypes.c_ulong),
                ("pbData", ctypes.POINTER(ctypes.c_char)),
            ]

        in_blob = DATA_BLOB(len(data), ctypes.cast(ctypes.c_char_p(data), ctypes.POINTER(ctypes.c_char)))
        out_blob = DATA_BLOB()

        crypt32 = ctypes.windll.crypt32
        # CRYPTPROTECT_UI_FORBIDDEN = 0x1
        if crypt32.CryptProtectData(ctypes.byref(in_blob), "KeyForgeLicense", None, None, None, 0x1, ctypes.byref(out_blob)):
            encrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)
            return encrypted
        raise OSError("DPAPI encryption failed")

    def _dpapi_unprotect(self, encrypted_data: bytes) -> bytes:
        if not self.is_windows:
            return encrypted_data

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", ctypes.c_ulong),
                ("pbData", ctypes.POINTER(ctypes.c_char)),
            ]

        in_blob = DATA_BLOB(
            len(encrypted_data),
            ctypes.cast(ctypes.c_char_p(encrypted_data), ctypes.POINTER(ctypes.c_char)),
        )
        out_blob = DATA_BLOB()

        crypt32 = ctypes.windll.crypt32
        if crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0x1, ctypes.byref(out_blob)):
            decrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)
            return decrypted
        raise OSError("DPAPI decryption failed")

    def save_license(self, license_data: str) -> None:
        if not self.is_windows:
            self._fallback.save_license(license_data)
            return

        try:
            encrypted = self._dpapi_protect(license_data.encode("utf-8"))
            self.file_path.write_bytes(encrypted)
        except Exception:
            self._fallback.save_license(license_data)

    def load_license(self) -> Optional[str]:
        if not self.is_windows:
            return self._fallback.load_license()

        if not self.file_path.exists():
            return self._fallback.load_license()

        try:
            encrypted = self.file_path.read_bytes()
            decrypted = self._dpapi_unprotect(encrypted)
            return decrypted.decode("utf-8")
        except Exception:
            return self._fallback.load_license()

    def clear_license(self) -> None:
        if self.file_path.exists():
            try:
                self.file_path.unlink()
            except OSError:
                pass
        self._fallback.clear_license()
