"""User identity: Ed25519-backed address derivation and key management.

Each user gets a unique address derived from an Ed25519 keypair::

    private key (32 bytes, ~/.hammerworld/identity)
        -> public key (32 bytes)
        -> SHA-256(pubkey)[:40]
        -> "0x" + 40 hex chars = HAMMERWORLD_ADDRESS

When ``cryptography`` is not installed, falls back to a 32-byte random seed
with SHA-256 derivation — still unique but unable to sign.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from pathlib import Path

_IDENTITY_DIR = Path.home() / ".hammerworld"
_IDENTITY_PATH = _IDENTITY_DIR / "identity"


# ---------------------------------------------------------------------------
# Lazy-load cryptography (same pattern as identity.py)
# ---------------------------------------------------------------------------

_CRYPTO_AVAILABLE = False
_ed25519_private_cls = None
_Encoding = None
_PrivateFormat = None
_PublicFormat = None
_NoEncryption = None

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PrivateFormat, PublicFormat, NoEncryption,
    )
    _ed25519_private_cls = Ed25519PrivateKey
    _Encoding = Encoding
    _PrivateFormat = PrivateFormat
    _PublicFormat = PublicFormat
    _NoEncryption = NoEncryption
    _CRYPTO_AVAILABLE = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ensure_user_identity() -> dict:
    """Load or create the user identity, returning a dict with keys:

    * ``address`` — ``0x`` + 40 hex chars derived from the public key
    * ``public_key_bytes`` — 32 raw bytes (empty if seed-based fallback)
    * ``has_private_key`` — True if Ed25519 keypair is available
    * ``key_path`` — path to the identity file
    """
    _IDENTITY_DIR.mkdir(parents=True, exist_ok=True)

    if _IDENTITY_PATH.exists():
        return _load_identity()

    if _CRYPTO_AVAILABLE:
        return _create_ed25519_identity()
    else:
        return _create_seed_identity()


def get_user_address(identity: dict) -> str:
    """Return the ``0x``-prefixed address from an identity dict."""
    return identity["address"]


# ---------------------------------------------------------------------------
# Internal: create
# ---------------------------------------------------------------------------


def _create_ed25519_identity() -> dict:
    """Generate a new Ed25519 keypair and derive the address."""
    private_key = _ed25519_private_cls.generate()
    public_key = private_key.public_key()

    pub_bytes = public_key.public_bytes(_Encoding.Raw, _PublicFormat.Raw)
    priv_bytes = private_key.private_bytes(
        _Encoding.Raw, _PrivateFormat.Raw, _NoEncryption()
    )

    _IDENTITY_PATH.write_bytes(priv_bytes)
    os.chmod(_IDENTITY_PATH, 0o600)

    addr = _derive_address(pub_bytes)
    return {
        "address": addr,
        "public_key_bytes": pub_bytes,
        "has_private_key": True,
        "key_path": str(_IDENTITY_PATH),
    }


def _create_seed_identity() -> dict:
    """Generate a 32-byte random seed and derive address from it.

    Without cryptography we cannot produce an Ed25519 public key, so the
    address is derived directly from the seed.  No signing is possible but
    the address is still globally unique.
    """
    seed = secrets.token_bytes(32)
    _IDENTITY_PATH.write_bytes(seed)
    os.chmod(_IDENTITY_PATH, 0o600)

    addr = _derive_address(seed)
    return {
        "address": addr,
        "public_key_bytes": b"",
        "has_private_key": False,
        "key_path": str(_IDENTITY_PATH),
    }


# ---------------------------------------------------------------------------
# Internal: load
# ---------------------------------------------------------------------------


def _load_identity() -> dict:
    """Load an existing identity file and derive the address."""
    data = _IDENTITY_PATH.read_bytes()

    if _CRYPTO_AVAILABLE and len(data) == 32:
        try:
            private_key = _ed25519_private_cls.from_private_bytes(data[:32])
            public_key = private_key.public_key()
            pub_bytes = public_key.public_bytes(_Encoding.Raw, _PublicFormat.Raw)
            addr = _derive_address(pub_bytes)
            return {
                "address": addr,
                "public_key_bytes": pub_bytes,
                "has_private_key": True,
                "key_path": str(_IDENTITY_PATH),
            }
        except Exception:
            pass  # fall through to seed-based interpretation

    # Treat as seed (or degraded key)
    seed = data[:32] if len(data) >= 32 else data
    addr = _derive_address(seed)
    return {
        "address": addr,
        "public_key_bytes": b"",
        "has_private_key": False,
        "key_path": str(_IDENTITY_PATH),
    }


# ---------------------------------------------------------------------------
# Internal: derivation
# ---------------------------------------------------------------------------


def _derive_address(key_material: bytes) -> str:
    """Derive a ``0x``-prefixed 40-hex-char address from key material."""
    return "0x" + hashlib.sha256(key_material).hexdigest()[:40]
