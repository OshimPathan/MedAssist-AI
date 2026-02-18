"""
MedAssist AI - Data Encryption Utilities
Encryption/decryption for sensitive patient data (PII) at rest
Uses Fernet symmetric encryption (AES-128-CBC)
"""

import base64
import hashlib
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Derive a Fernet-compatible key from SECRET_KEY
_KEY = base64.urlsafe_b64encode(
    hashlib.sha256(settings.SECRET_KEY.encode()).digest()[:32]
)

_fernet = None


def _get_fernet():
    """Lazy-load Fernet cipher"""
    global _fernet
    if _fernet is None:
        from cryptography.fernet import Fernet
        _fernet = Fernet(_KEY)
    return _fernet


def encrypt_field(plaintext: str) -> str:
    """Encrypt a sensitive field (phone, email, etc.) for DB storage"""
    if not plaintext:
        return plaintext
    try:
        f = _get_fernet()
        return f.encrypt(plaintext.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return plaintext  # Fail open to avoid data loss


def decrypt_field(ciphertext: str) -> str:
    """Decrypt a previously encrypted field"""
    if not ciphertext:
        return ciphertext
    try:
        f = _get_fernet()
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        # May be unencrypted legacy data
        return ciphertext


def hash_pii(value: str) -> str:
    """
    One-way hash for PII lookup (e.g., searching by phone without storing it in plaintext).
    Uses SHA-256 with the app's secret as salt.
    """
    salted = f"{settings.SECRET_KEY}:{value}"
    return hashlib.sha256(salted.encode()).hexdigest()


def mask_phone(phone: str) -> str:
    """Mask a phone number for display: +91****1234"""
    if not phone or len(phone) < 4:
        return "****"
    return phone[:3] + "****" + phone[-4:]


def mask_email(email: str) -> str:
    """Mask an email for display: u***@domain.com"""
    if not email or "@" not in email:
        return "****"
    local, domain = email.rsplit("@", 1)
    return local[0] + "***@" + domain
