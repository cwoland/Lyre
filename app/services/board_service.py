from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import LimitExceededError, NotFoundError
from app.models import Board, BoardMember, BoardRole, User


async def get_board(session: AsyncSession, board_id: UUID) -> Board:
    board = await session.get(Board, board_id)
    if board is None:
        raise NotFoundError("Board not found")
    return board


async def create_board(session: AsyncSession, owner: User, *, title: str) -> Board:
    settings = get_settings()
    owned = await session.scalar(
        select(func.count()).select_from(Board).where(Board.owner_id == owner.id)
    )
    if (owned or 0) >= settings.max_boards_per_owner:
        raise LimitExceededError(
            "Board limit reached",
            details={"limit": settings.max_boards_per_owner},
        )

    board = Board(owner_id=owner.id, title=title.strip())
    session.add(board)
    await session.flush()
    session.add(BoardMember(board_id=board.id, user_id=owner.id, role=BoardRole.owner))
    await session.flush()
    return board


async def list_boards(session: AsyncSession, user: User) -> list[tuple[Board, BoardRole]]:
    rows = await session.execute(
        select(Board, BoardMember.role)
        .join(BoardMember, BoardMember.board_id == Board.id)
        .where(BoardMember.user_id == user.id)
        .order_by(Board.created_at.desc())
    )
    return [(board, role) for board, role in rows.all()]


async def rename_board(session: AsyncSession, board_id: UUID, *, title: str) -> Board:
    board = await get_board(session, board_id)
    board.title = title.strip()
    await session.flush()
    return board


async def delete_board(session: AsyncSession, board_id: UUID) -> None:
    board = await get_board(session, board_id)
    await session.delete(board)
    await session.flush()
