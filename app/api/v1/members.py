from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import BoardMemberDep, BoardOwnerDep, SessionDep
from app.models import BoardMember, User
from app.schemas.member import MemberResponse, MemberRoleUpdate
from app.services import member_service

router = APIRouter(prefix="/boards/{board_id}/members", tags=["members"])


def _member_response(membership: BoardMember, user: User) -> MemberResponse:
    return MemberResponse(
        user_id=user.id,
        display_name=user.display_name,
        email=user.email,
        cursor_color=user.cursor_color,
        role=membership.role,
        joined_at=membership.created_at,
    )


@router.get("", summary="List members")
async def list_members(
    board_id: UUID,
    session: SessionDep,
    membership: BoardMemberDep,
) -> list[MemberResponse]:
    rows = await member_service.list_members(session, board_id)
    return [_member_response(member, user) for member, user in rows]


@router.patch("/{user_id}", summary="Change member role")
async def change_member_role(
    board_id: UUID,
    user_id: UUID,
    payload: MemberRoleUpdate,
    session: SessionDep,
    membership: BoardOwnerDep,
) -> MemberResponse:
    member, user = await member_service.change_member_role(
        session,
        board_id=board_id,
        user_id=user_id,
        role=payload.role,
    )
    await session.commit()
    return _member_response(member, user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove member")
async def remove_member(
    board_id: UUID,
    user_id: UUID,
    session: SessionDep,
    membership: BoardMemberDep,
) -> None:
    await member_service.remove_member(
        session,
        board_id=board_id,
        user_id=user_id,
        requester=membership,
    )
    await session.commit()
