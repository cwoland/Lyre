from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import InviteInvalidError, LimitExceededError, NotFoundError
from app.core.security import generate_invite_token, hash_opaque_token
from app.models import Board, BoardInvite, BoardMember, BoardRole, InviteStatus, User


async def create_invite(
    session: AsyncSession,
    *,
    board_id: UUID,
    created_by: UUID,
    role: BoardRole,
    ttl_hours: int,
) -> tuple[BoardInvite, str]:
    raw_token = generate_invite_token()
    invite = BoardInvite(
        board_id=board_id,
        token_hash=hash_opaque_token(raw_token),
        role=role,
        created_by=created_by,
        expires_at=datetime.now(UTC) + timedelta(hours=ttl_hours),
    )
    session.add(invite)
    await session.flush()
    return invite, raw_token


async def list_invites(session: AsyncSession, board_id: UUID) -> list[BoardInvite]:
    rows = await session.execute(
        select(BoardInvite)
        .where(BoardInvite.board_id == board_id)
        .order_by(BoardInvite.created_at.desc())
    )
    return list(rows.scalars().all())


async def revoke_invite(session: AsyncSession, *, board_id: UUID, invite_id: UUID) -> None:
    invite = await session.get(BoardInvite, invite_id)
    if invite is None or invite.board_id != board_id:
        raise NotFoundError("Invite not found")
    if invite.revoked_at is None:
        invite.revoked_at = datetime.now(UTC)
        await session.flush()


async def _load_invite(session: AsyncSession, raw_token: str) -> BoardInvite:
    invite = await session.scalar(
        select(BoardInvite).where(BoardInvite.token_hash == hash_opaque_token(raw_token))
    )
    if invite is None:
        raise NotFoundError("Invite not found")
    return invite


async def preview_invite(session: AsyncSession, raw_token: str) -> tuple[Board, BoardInvite]:
    invite = await _load_invite(session, raw_token)
    if invite.status is not InviteStatus.pending:
        raise InviteInvalidError("Invite is no longer valid", details={"status": invite.status})

    board = await session.get(Board, invite.board_id)
    if board is None:
        raise NotFoundError("Board not found")
    return board, invite


async def accept_invite(session: AsyncSession, raw_token: str, user: User) -> BoardMember:
    invite = await _load_invite(session, raw_token)
    existing = await session.get(BoardMember, (invite.board_id, user.id))

    if invite.status is InviteStatus.used:
        if invite.used_by == user.id and existing is not None:
            return existing
        raise InviteInvalidError("Invite was already used", details={"status": invite.status})

    if invite.status is not InviteStatus.pending:
        raise InviteInvalidError("Invite is no longer valid", details={"status": invite.status})

    invite.used_at = datetime.now(UTC)
    invite.used_by = user.id

    if existing is not None:
        await session.flush()
        return existing

    settings = get_settings()
    members = await session.scalar(
        select(func.count()).select_from(BoardMember).where(BoardMember.board_id == invite.board_id)
    )
    if (members or 0) >= settings.max_board_members:
        raise LimitExceededError(
            "Board member limit reached",
            details={"limit": settings.max_board_members},
        )

    membership = BoardMember(board_id=invite.board_id, user_id=user.id, role=invite.role)
    session.add(membership)
    await session.flush()
    return membership
