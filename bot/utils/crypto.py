from __future__ import annotations

import hashlib
import hmac
import secrets


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hmac_sha256_hex(secret: bytes, data: bytes) -> str:
    return hmac.new(secret, data, hashlib.sha256).hexdigest()


def random_token(nbytes: int = 16) -> str:
    # URL-safe token for callback payload
    return secrets.token_urlsafe(nbytes)

