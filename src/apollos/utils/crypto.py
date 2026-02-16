"""AES-256-GCM encryption for OAuth tokens and secrets.

Environment variable: APOLLOS_VAULT_MASTER_KEY (32+ character random string).
NEVER commit this key.
"""

import base64
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def _get_master_key() -> str:
    """Read master key from env var at runtime. Never store in Django settings (anti-pattern #4)."""
    key = os.environ.get("APOLLOS_VAULT_MASTER_KEY", "")
    if not key or len(key) < 32:
        raise ValueError("APOLLOS_VAULT_MASTER_KEY must be set and at least 32 characters")
    return key


def derive_key(master_key: str, context: str) -> bytes:
    """Derive a purpose-specific key using HKDF."""
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=context.encode(),
    ).derive(master_key.encode())


def encrypt_token(plaintext: str) -> str:
    """AES-256-GCM encryption. Returns base64-encoded nonce+ciphertext."""
    key = derive_key(_get_master_key(), "mcp-token-encryption")
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt AES-256-GCM token."""
    key = derive_key(_get_master_key(), "mcp-token-encryption")
    data = base64.b64decode(encrypted)
    nonce, ct = data[:12], data[12:]
    return AESGCM(key).decrypt(nonce, ct, None).decode()
