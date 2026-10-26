from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NotFoundError
from app.models import BoardMember, BoardRole, User


async def list_members(session: AsyncSession, board_id: UUID) -> list[tuple[BoardMember, User]]:
    rows = await session.execute(
        select(BoardMember, User)
        .join(User, User.id == BoardMember.user_id)
        .where(BoardMember.board_id == board_id)
        .order_by(BoardMember.created_at)
    )
    return [(member, user) for member, user in rows.all()]


async def _get_member(session: AsyncSession, board_id: UUID, user_id: UUID) -> BoardMember:
    membership = await session.get(BoardMember, (board_id, user_id))
    if membership is None:
        raise NotFoundError("Member not found")
    return membership


async def change_member_role(
    session: AsyncSession,
    *,
    board_id: UUID,
    user_id: UUID,
    role: BoardRole,
) -> tuple[BoardMember, User]:
    membership = await _get_member(session, board_id, user_id)
    if membership.role is BoardRole.owner:
        raise ForbiddenError("Board owner role cannot be changed")

    membership.role = role
    await session.flush()

    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("Member not found")
    return membership, user


async def remove_member(
    session: AsyncSession,
    *,
    board_id: UUID,
    user_id: UUID,
    requester: BoardMember,
) -> None:
    membership = await _get_member(session, board_id, user_id)
    if membership.role is BoardRole.owner:
        raise ForbiddenError("Board owner cannot be removed")

    is_self = user_id == requester.user_id
    is_owner = requester.role is BoardRole.owner
    if not (is_self or is_owner):
        raise ForbiddenError("Only the owner can remove other members")

    await session.delete(membership)
    await session.flush()
