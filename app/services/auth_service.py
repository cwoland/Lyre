from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import EmailTakenError, InvalidCredentialsError, UnauthorizedError
from app.core.palette import pick_color_cursor
from app.core.security import (
    burn_password_time,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models import RefreshToken, User


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def register_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str,
) -> User:
    user = User(
        email=normalize_email(email),
        password_hash=hash_password(password),
        display_name=display_name.strip(),
        cursor_color=pick_color_cursor(),
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as error:
        await session.rollback()
        raise EmailTakenError("Email is already registered") from error
    return user


async def authenticate_user(session: AsyncSession, *, email: str, password: str) -> User:
    user = await session.scalar(select(User).where(User.email == normalize_email(email)))

    if user is None:
        burn_password_time()
        raise InvalidCredentialsError("Invalid email or password")
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid email or password")
    return user


async def issue_refresh_token(session: AsyncSession, user: User) -> tuple[str, datetime]:
    settings = get_settings()
    now = datetime.now(UTC)
    await session.execute(
        delete(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.expires_at < now,
        )
    )
    raw_token = generate_refresh_token()
    expires_at = now + timedelta(days=settings.refresh_token_ttl_days)
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_token),
            expires_at=expires_at,
        )
    )
    await session.flush()
    return raw_token, expires_at


async def _revoke_all_for_user(session: AsyncSession, user_id: object) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def rotate_refresh_token(
    session: AsyncSession,
    raw_token: str,
) -> tuple[User, str, datetime]:
    stored = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    )
    if stored is None:
        raise UnauthorizedError("Invalid refresh token")

    if stored.revoked_at is not None:
        await _revoke_all_for_user(session, stored.user_id)
        await session.commit()
        raise UnauthorizedError("Refresh token was already used")

    if stored.expires_at <= datetime.now(UTC):
        raise UnauthorizedError("Refresh token expired")

    user = await session.get(User, stored.user_id)
    if user is None:
        raise UnauthorizedError("User not longer exists")

    stored.revoked_at = datetime.now(UTC)
    await session.flush()
    raw_new_token, expires_at = await issue_refresh_token(session, user)
    return user, raw_new_token, expires_at


async def revoke_refresh_token(session: AsyncSession, raw_token: str) -> None:
    stored = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    )
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        await session.flush()
