import sys
from pathlib import Path
import pytest

# Ensure keyforge package and sdk/python are discoverable
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "sdk" / "python"))

from keyforge.core.crypto import Ed25519KeyManager, generate_keypair
from keyforge.core.key_generator import (
    AlphabetType,
    ChecksumType,
    KeyFormatConfig,
)
from keyforge.core.license_model import LicensePayload, LicenseType, SignedLicense
from keyforge.core.profiles import get_default_profile
from keyforge.core.validator import LicenseValidator


@pytest.fixture
def master_keypair():
    """Generate a standard Ed25519 keypair for test cases."""
    return generate_keypair(version=1, key_id="key-test-v1")


@pytest.fixture
def key_manager(master_keypair):
    """Key manager pre-loaded with the test keypair."""
    km = Ed25519KeyManager()
    km.add_key(master_keypair, set_active=True)
    return km


@pytest.fixture
def standard_profile():
    """Default desktop product profile."""
    return get_default_profile("desktop")


@pytest.fixture
def validator(master_keypair, standard_profile):
    """Validator instance configured with test public key."""
    return LicenseValidator(public_key=master_keypair, profile=standard_profile)
