from __future__ import annotations

import hashlib
import hmac
import secrets
from base64 import b64decode, b64encode

from app.config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        settings.password_hash_iterations,
    )
    return (
        f"pbkdf2_sha256${settings.password_hash_iterations}$"
        f"{b64encode(salt).decode('utf-8')}${b64encode(derived).decode('utf-8')}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        b64decode(salt_text.encode("utf-8")),
        int(iterations_text),
    )
    return hmac.compare_digest(digest_text, b64encode(derived).decode("utf-8"))


def generate_session_token() -> str:
    return f"{settings.auth_token_prefix}{secrets.token_urlsafe(32)}"


def digest_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
