from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import BoardMemberDep, BoardOwnerDep, CurrentUser, SessionDep
from app.models import Board, BoardRole
from app.schemas.board import BoardCreate, BoardListItem, BoardResponse, BoardUpdate
from app.services import board_service

router = APIRouter(prefix="/boards", tags=["boards"])


def _list_item(board: Board, role: BoardRole) -> BoardListItem:
    return BoardListItem(
        id=board.id,
        title=board.title,
        owner_id=board.owner_id,
        created_at=board.created_at,
        updated_at=board.updated_at,
        role=role,
    )


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create board")
async def create_board(
    payload: BoardCreate,
    session: SessionDep,
    user: CurrentUser,
) -> BoardResponse:
    board = await board_service.create_board(session, user, title=payload.title)
    await session.commit()
    return BoardResponse.model_validate(board)


@router.get("", summary="List my boards")
async def list_boards(session: SessionDep, user: CurrentUser) -> list[BoardListItem]:
    rows = await board_service.list_boards(session, user)
    return [_list_item(board, role) for board, role in rows]


@router.get("/{board_id}", summary="Get board")
async def get_board(
    board_id: UUID,
    session: SessionDep,
    membership: BoardMemberDep,
) -> BoardListItem:
    board = await board_service.get_board(session, board_id)
    return _list_item(board, membership.role)


@router.patch("/{board_id}", summary="Rename board")
async def rename_board(
    board_id: UUID,
    payload: BoardUpdate,
    session: SessionDep,
    membership: BoardOwnerDep,
) -> BoardResponse:
    board = await board_service.rename_board(session, board_id, title=payload.title)
    await session.commit()
    return BoardResponse.model_validate(board)


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete board")
async def delete_board(
    board_id: UUID,
    session: SessionDep,
    membership: BoardOwnerDep,
) -> None:
    await board_service.delete_board(session, board_id)
    await session.commit()
