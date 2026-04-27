from __future__ import annotations

from bot.utils.crypto import hmac_sha256_hex


def test_hmac_signature_is_stable() -> None:
    secret = b"secret"
    data = b"chat:1:2:token"
    s1 = hmac_sha256_hex(secret, data)
    s2 = hmac_sha256_hex(secret, data)
    assert s1 == s2
    assert len(s1) == 64

