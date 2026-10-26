from uuid import UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BoardMember, BoardRole
from tests.helpers import auth, create_board, register


async def _add_member(
    session: AsyncSession,
    board_id: str,
    user_id: str,
    role: BoardRole,
) -> None:
    session.add(BoardMember(board_id=UUID(board_id), user_id=UUID(user_id), role=role))
    await session.flush()


async def test_members_list_contains_owner(client: AsyncClient) -> None:
    token, user_id = await register(client, "owner@example.com")
    board_id = await create_board(client, token)

    response = await client.get(f"/api/v1/boards/{board_id}/members", headers=auth(token))

    assert response.status_code == 200
    assert response.json() == [
        {
            "user_id": user_id,
            "display_name": "owner",
            "email": "owner@example.com",
            "cursor_color": response.json()[0]["cursor_color"],
            "role": "owner",
            "joined_at": response.json()[0]["joined_at"],
        }
    ]


async def test_owner_changes_member_role(client: AsyncClient, session: AsyncSession) -> None:
    owner_token, _ = await register(client, "owner@example.com")
    board_id = await create_board(client, owner_token)
    _, editor_id = await register(client, "editor@example.com")
    await _add_member(session, board_id, editor_id, BoardRole.editor)

    response = await client.patch(
        f"/api/v1/boards/{board_id}/members/{editor_id}",
        json={"role": "viewer"},
        headers=auth(owner_token),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "viewer"


async def test_owner_role_cannot_be_changed(client: AsyncClient) -> None:
    owner_token, owner_id = await register(client, "owner@example.com")
    board_id = await create_board(client, owner_token)

    response = await client.patch(
        f"/api/v1/boards/{board_id}/members/{owner_id}",
        json={"role": "viewer"},
        headers=auth(owner_token),
    )

    assert response.status_code == 403


async def test_role_owner_is_rejected_by_schema(client: AsyncClient, session: AsyncSession) -> None:
    owner_token, _ = await register(client, "owner@example.com")
    board_id = await create_board(client, owner_token)
    _, editor_id = await register(client, "editor@example.com")
    await _add_member(session, board_id, editor_id, BoardRole.editor)

    response = await client.patch(
        f"/api/v1/boards/{board_id}/members/{editor_id}",
        json={"role": "owner"},
        headers=auth(owner_token),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_member_can_leave_board(client: AsyncClient, session: AsyncSession) -> None:
    owner_token, _ = await register(client, "owner@example.com")
    board_id = await create_board(client, owner_token)
    editor_token, editor_id = await register(client, "editor@example.com")
    await _add_member(session, board_id, editor_id, BoardRole.editor)

    left = await client.delete(
        f"/api/v1/boards/{board_id}/members/{editor_id}",
        headers=auth(editor_token),
    )

    assert left.status_code == 204
    assert (
        await client.get(f"/api/v1/boards/{board_id}", headers=auth(editor_token))
    ).status_code == 404


async def test_editor_cannot_remove_another_member(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    owner_token, _ = await register(client, "owner@example.com")
    board_id = await create_board(client, owner_token)
    editor_token, editor_id = await register(client, "editor@example.com")
    _, viewer_id = await register(client, "viewer@example.com")
    await _add_member(session, board_id, editor_id, BoardRole.editor)
    await _add_member(session, board_id, viewer_id, BoardRole.viewer)

    response = await client.delete(
        f"/api/v1/boards/{board_id}/members/{viewer_id}",
        headers=auth(editor_token),
    )

    assert response.status_code == 403
