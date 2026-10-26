from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import BoardMember, BoardRole, User

_bearer = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token")

    user_id = decode_access_token(credentials.credentials)
    user = await session.get(User, user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_board_membership(
    board_id: UUID,
    session: SessionDep,
    user: CurrentUser,
) -> BoardMember:
    membership = await session.get(BoardMember, (board_id, user.id))
    if membership is None:
        raise NotFoundError("Board not found")
    return membership


BoardMemberDep = Annotated[BoardMember, Depends(get_board_membership)]


def require_board_role(*roles: BoardRole) -> Callable[[BoardMember], BoardMember]:
    allowed = frozenset(roles)

    def dependency(membership: BoardMemberDep) -> BoardMember:
        if membership.role not in allowed:
            raise ForbiddenError("Insufficient board role")
        return membership

    return dependency


BoardOwnerDep = Annotated[BoardMember, Depends(require_board_role(BoardRole.owner))]
BoardEditorDep = Annotated[
    BoardMember, Depends(require_board_role(BoardRole.owner, BoardRole.editor))
]
