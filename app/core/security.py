import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Final
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings
from app.core.errors import UnauthorizedError


_hasher: Final = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)

_DUMMY_HASH: Final = _hasher.hash("timing-attack-placeholder")

ACCESS_TOKEN_TYPE: Final = "access"
REFRESH_TOKEN_BYTES: Final = 48


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def burn_password_time() -> None:
    verify_password("timing-attack-placeholder", _DUMMY_HASH)


def create_access_token(user_id: UUID) -> tuple[str, int]:
    settings = get_settings()
    ttl = timedelta(minutes=settings.access_token_ttl_minutes)
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "typ": ACCESS_TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, int(ttl.total_seconds())


def decode_access_token(token: str) -> UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as error:
        raise UnauthorizedError("Invalid or expired token") from error

    if payload.get("typ") != ACCESS_TOKEN_TYPE:
        raise UnauthorizedError("Invalid token type")

    try:
        return UUID(str(payload["sub"]))
    except (KeyError, ValueError) as error:
        raise UnauthorizedError("Invalid token subject") from error


def generate_refresh_token(token: str) -> str:
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
