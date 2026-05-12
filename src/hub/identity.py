"""Ed25519 identity management for authenticated P2P discovery announcements.

Uses the ``cryptography`` library for Ed25519 key generation, signing, and
verification.  When ``cryptography`` is not installed the module degrades
gracefully — peer_id falls back to a random hash and announcements carry no
signature (``verified: false`` on the server side).
"""
from __future__ import annotations

import base64
import hashlib
import os
import time
from pathlib import Path
from typing import Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Ed25519 helpers (lazy-load cryptography)
# ---------------------------------------------------------------------------

_CRYPTOGRAPHY_AVAILABLE = False
_ed25519_private_cls = None
_ed25519_public_cls = None
_Encoding = None
_PrivateFormat = None
_PublicFormat = None
_NoEncryption = None
_InvalidSignature = None

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        PrivateFormat,
        PublicFormat,
        NoEncryption,
    )
    from cryptography.exceptions import InvalidSignature as _InvalidSig
    _ed25519_private_cls = Ed25519PrivateKey
    _ed25519_public_cls = Ed25519PublicKey
    _Encoding = Encoding
    _PrivateFormat = PrivateFormat
    _PublicFormat = PublicFormat
    _NoEncryption = NoEncryption
    _InvalidSignature = _InvalidSig
    _CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# IdentityManager
# ---------------------------------------------------------------------------

class IdentityError(Exception):
    """Base exception for identity-related errors."""


class IdentityNotAvailableError(IdentityError):
    """Raised when a signing operation is attempted without cryptography."""


class IdentityManager:
    """Manage an Ed25519 keypair for P2P identity.

    Parameters
    ----------
    key_path:
        Path to a file holding the PKCS#8 DER-encoded Ed25519 private key.
        If the file exists the key is loaded.  If it doesn't exist a new
        keypair is generated and persisted.  When ``None`` (the default)
        and *cryptography* is unavailable the manager operates in degraded
        mode (``available == False``).
    """

    def __init__(self, key_path: Optional[Union[str, Path]] = None):
        self._key_path = Path(key_path) if key_path else None
        self._private_key = None   # Ed25519PrivateKey | None
        self._public_key = None    # Ed25519PublicKey | None
        self._peer_id = ""

        if not _CRYPTOGRAPHY_AVAILABLE or self._key_path is None:
            self._init_degraded()
        else:
            self._init_from_path()

    # -- public properties ----------------------------------------------------

    @property
    def available(self) -> bool:
        """True when Ed25519 signing is available."""
        return self._private_key is not None

    @property
    def peer_id(self) -> str:
        """Stable peer identifier derived from the public key (or random)."""
        return self._peer_id

    @property
    def public_key_bytes(self) -> bytes:
        """Raw 32-byte Ed25519 public key (or empty bytes in degraded mode)."""
        if self._public_key is not None:
            return self._public_key.public_bytes(_Encoding.Raw, _PublicFormat.Raw)
        return b""

    # -- signing --------------------------------------------------------------

    def sign(self, message: bytes) -> bytes:
        """Sign *message* with the Ed25519 private key.

        Raises :exc:`IdentityNotAvailableError` in degraded mode.
        """
        if self._private_key is None:
            raise IdentityNotAvailableError("cryptography library not available")
        assert _ed25519_private_cls is not None
        return self._private_key.sign(message)

    # -- announcement payload -------------------------------------------------

    def get_announce_payload(self, address: str, port: int) -> dict:
        """Build the ``timestamp`` / ``public_key`` / ``signature`` block
        that can be merged into a discovery announce request body.

        Returns an empty dict in degraded mode.
        """
        if not self.available:
            return {}

        ts = time.time()
        message = f"{ts:.6f}:{address}:{port}".encode()
        sig = self.sign(message)
        return {
            "timestamp": ts,
            "public_key": base64.b64encode(self.public_key_bytes).decode(),
            "signature": base64.b64encode(sig).decode(),
        }

    # -- internal -------------------------------------------------------------

    def _init_degraded(self):
        self._peer_id = _random_peer_id()
        if self._key_path and not _CRYPTOGRAPHY_AVAILABLE:
            import logging
            logging.warning(
                "cryptography not installed — P2P identity disabled.  "
                "Install with: pip install cryptography"
            )

    def _init_from_path(self):
        assert self._key_path is not None
        assert _ed25519_private_cls is not None
        assert _ed25519_public_cls is not None

        if self._key_path.exists() and self._key_path.stat().st_size >= 32:
            data = self._key_path.read_bytes()
            self._private_key = _ed25519_private_cls.from_private_bytes(data[:32])
            self._public_key = self._private_key.public_key()
        else:
            self._private_key = _ed25519_private_cls.generate()
            self._public_key = self._private_key.public_key()
            # Persist raw 32-byte private key
            priv_bytes = self._private_key.private_bytes(
                _Encoding.Raw, _PrivateFormat.Raw, _NoEncryption())
            self._key_path.parent.mkdir(parents=True, exist_ok=True)
            self._key_path.write_bytes(priv_bytes)
            os.chmod(self._key_path, 0o600)

        self._peer_id = _pubkey_to_peer_id(self._public_key)


# ---------------------------------------------------------------------------
# Verification (module-level — used by the server side)
# ---------------------------------------------------------------------------

def verify_announce_payload(
    peer_id: str,
    address: str,
    port: int,
    timestamp: float,
    public_key_b64: str,
    signature_b64: str,
    max_age: float = 60.0,
) -> Tuple[bool, str]:
    """Verify a signed discovery announcement.

    Returns ``(True, "")`` on success or ``(False, "reason")`` on failure.
    """
    if not _CRYPTOGRAPHY_AVAILABLE:
        return False, "cryptography not available on server"

    # 1. Anti-replay: timestamp must be within max_age
    if abs(time.time() - timestamp) > max_age:
        return False, f"timestamp expired ({max_age}s window)"

    # 2. Decode public key and verify peer_id binding
    try:
        pk_bytes = base64.b64decode(public_key_b64)
    except Exception:
        return False, "invalid public_key base64"

    expected_id = _raw_pubkey_to_peer_id(pk_bytes)
    if expected_id != peer_id:
        return False, "public_key does not match peer_id"

    # 3. Reconstruct and verify signature
    try:
        sig_bytes = base64.b64decode(signature_b64)
    except Exception:
        return False, "invalid signature base64"

    message = f"{timestamp:.6f}:{address}:{port}".encode()
    try:
        pk: Ed25519PublicKey = Ed25519PublicKey.from_public_bytes(pk_bytes)  # type: ignore[name-defined]
        pk.verify(sig_bytes, message)
    except _InvalidSignature:
        return False, "signature verification failed"
    except Exception as exc:
        return False, f"verification error: {exc}"

    return True, ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pubkey_to_peer_id(pk) -> str:
    return _raw_pubkey_to_peer_id(pk.public_bytes(_Encoding.Raw, _PublicFormat.Raw))


def _raw_pubkey_to_peer_id(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()[:40]


def _random_peer_id() -> str:
    return hashlib.sha256(os.urandom(32)).hexdigest()[:40]
