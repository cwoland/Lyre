from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import BoardOwnerDep, CurrentUser, SessionDep
from app.models import BoardInvite
from app.schemas.board import BoardListItem
from app.schemas.invite import (
    InviteCreate,
    InviteCreatedResponse,
    InvitePreview,
    InviteResponse,
)
from app.services import board_service, invite_service

board_invites_router = APIRouter(prefix="/boards/{board_id}/invites", tags=["invites"])
invites_router = APIRouter(prefix="/invites", tags=["invites"])


def _invite_response(invite: BoardInvite) -> InviteResponse:
    return InviteResponse(
        id=invite.id,
        board_id=invite.board_id,
        role=invite.role,
        status=invite.status,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


@board_invites_router.post("", status_code=status.HTTP_201_CREATED, summary="Create invite")
async def create_invite(
    board_id: UUID,
    payload: InviteCreate,
    session: SessionDep,
    membership: BoardOwnerDep,
) -> InviteCreatedResponse:
    invite, raw_token = await invite_service.create_invite(
        session,
        board_id=board_id,
        created_by=membership.user_id,
        role=payload.role,
        ttl_hours=payload.ttl_hours,
    )
    await session.commit()
    return InviteCreatedResponse(**_invite_response(invite).model_dump(), token=raw_token)


@board_invites_router.get("", summary="List invites")
async def list_invites(
    board_id: UUID,
    session: SessionDep,
    membership: BoardOwnerDep,
) -> list[InviteResponse]:
    invites = await invite_service.list_invites(session, board_id)
    return [_invite_response(invite) for invite in invites]


@board_invites_router.delete(
    "/{invite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke invite",
)
async def revoke_invite(
    board_id: UUID,
    invite_id: UUID,
    session: SessionDep,
    membership: BoardOwnerDep,
) -> None:
    await invite_service.revoke_invite(session, board_id=board_id, invite_id=invite_id)
    await session.commit()


@invites_router.get("/{token}", summary="Preview invite")
async def preview_invite(token: str, session: SessionDep) -> InvitePreview:
    board, invite = await invite_service.preview_invite(session, token)
    return InvitePreview(
        board_id=board.id,
        board_title=board.title,
        role=invite.role,
        expires_at=invite.expires_at,
    )


@invites_router.post("/{token}/accept", summary="Accept invite")
async def accept_invite(
    token: str,
    session: SessionDep,
    user: CurrentUser,
) -> BoardListItem:
    membership = await invite_service.accept_invite(session, token, user)
    board = await board_service.get_board(session, membership.board_id)
    await session.commit()
    return BoardListItem(
        id=board.id,
        title=board.title,
        owner_id=board.owner_id,
        created_at=board.created_at,
        updated_at=board.updated_at,
        role=membership.role,
    )
