import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Board, BoardMember, BoardRole, User


async def _add_user(session: AsyncSession, email: str) -> User:
    user = User(
        email=email,
        password_hash="not-a-real-hash",
        display_name="admin",
        cursor_color="#ff0066",
    )
    session.add(user)
    await session.flush()
    return user


async def test_board_membership_roundtrip(session: AsyncSession) -> None:
    user = await _add_user(session, "owner@example.com")
    board = Board(owner_id=user.id, title="Sprint 1")
    session.add(board)
    await session.flush()

    session.add(BoardMember(board_id=board.id, user_id=user.id, role=BoardRole.owner))
    await session.flush()

    member = (await session.execute(select(BoardMember))).scalar_one()
    assert member.role is BoardRole.owner
    assert member.created_at is not None


async def test_email_is_unique(session: AsyncSession) -> None:
    await _add_user(session, "dup@example.com")
    session.add(
        User(
            email="dup@example.com",
            password_hash="not-a-real-hash",
            display_name="Clone",
            cursor_color="#00aaff",
        )
    )

    with pytest.raises(IntegrityError):
        await session.flush()
