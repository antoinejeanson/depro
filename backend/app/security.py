"""Password hashing, session tokens and cookie settings."""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error

SESSION_COOKIE = "depro_session"
SESSION_DAYS = 30

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except Argon2Error:
        return False


def new_token() -> str:
    """A new random session token (stored in the cookie, never in the DB)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """The value actually stored in the sessions table."""
    return hashlib.sha256(token.encode()).hexdigest()


def session_max_age() -> int:
    return SESSION_DAYS * 24 * 3600
