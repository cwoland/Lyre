from datetime import UTC, datetime
from typing import Annotated, Final

from fastapi import APIRouter, Cookie, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.core.security import create_access_token
from app.models import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.services import auth_service


REFRESH_COOKIE_NAME: Final = "lyre_refresh"

router = APIRouter(prefix="/auth", tags=["auth"])

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)]


def _cookie_path() -> str:
    return f"{get_settings().api_prefix}/auth"


def _set_refresh_cookie(response: Response, token: str, expires_at: datetime) -> None:
    settings = get_settings()
    max_age = int((expires_at - datetime.now(UTC)).total_seconds())
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=_cookie_path(),
    )


def _auth_response(user: User) -> AuthResponse:
    access_token, expires_in = create_access_token(user.id)
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        expires_in=expires_in,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, summary="Register")
async def register(
    payload: RegisterRequest, response: Response, session: SessionDep
) -> AuthResponse:
    user = await auth_service.register_user(
        session,
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
    )
    raw_token, expires_at = await auth_service.issue_refresh_token(session, user)
    await session.commit()
    _set_refresh_cookie(response, raw_token, expires_at)
    return _auth_response(user)


@router.post("/login", summary="Log in")
async def login(payload: LoginRequest, response: Response, session: SessionDep) -> AuthResponse:
    user = await auth_service.authenticate_user(
        session,
        email=payload.email,
        password=payload.password,
    )
    raw_token, expires_at = await auth_service.issue_refresh_token(session, user)
    await session.commit()
    _set_refresh_cookie(response, raw_token, expires_at)
    return _auth_response(user)


@router.post("/refresh", summary="Rotate tokens")
async def refresh(
    response: Response,
    session: SessionDep,
    refresh_token: RefreshCookie = None,
) -> AuthResponse:
    if refresh_token is None:
        raise UnauthorizedError("Missing refresh token")

    user, raw_token, expires_at = await auth_service.rotate_refresh_token(session, refresh_token)
    await session.commit()
    _set_refresh_cookie(response, raw_token, expires_at)
    return _auth_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Log out")
async def logout(
    response: Response,
    session: SessionDep,
    refresh_token: RefreshCookie = None,
) -> None:
    if refresh_token is not None:
        await auth_service.revoke_refresh_token(session, refresh_token)
        await session.commit()
    response.delete_cookie(REFRESH_COOKIE_NAME, path=_cookie_path())


@router.get("/me", summary="Current user")
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
