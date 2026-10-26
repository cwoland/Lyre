from datetime import UTC, datetime, timedelta
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BoardInvite, BoardMember, BoardRole
from tests.helpers import auth, create_board, register


async def _create_invite(
    client: AsyncClient, token: str, board_id: str, role: str = "editor"
) -> str:
    response = await client.post(
        f"/api/v1/boards/{board_id}/invites",
        json={"role": role},
        headers=auth(token),
    )
    assert response.status_code == 201
    invite_token: str = response.json()["token"]
    return invite_token


async def test_invite_token_is_returned_once(client: AsyncClient) -> None:
    token, _ = await register(client, "owner@example.com")
    board_id = await create_board(client, token)

    created = await client.post(
        f"/api/v1/boards/{board_id}/invites",
        json={"role": "viewer"},
        headers=auth(token),
    )
    listed = await client.get(f"/api/v1/boards/{board_id}/invites", headers=auth(token))

    assert created.json()["status"] == "pending"
    assert "token" in created.json()
    assert "token" not in listed.json()[0]


async def test_editor_cannot_create_invite(client: AsyncClient, session: AsyncSession) -> None:
    owner_token, _ = await register(client, "owner@example.com")
    board_id = await create_board(client, owner_token)
    editor_token, editor_id = await register(client, "editor@example.com")
    session.add(
        BoardMember(board_id=UUID(board_id), user_id=UUID(editor_id), role=BoardRole.editor)
    )
    await session.flush()

    response = await client.post(
        f"/api/v1/boards/{board_id}/invites",
        json={"role": "viewer"},
        headers=auth(editor_token),
    )

    assert response.status_code == 403


async def test_preview_works_without_auth(client: AsyncClient) -> None:
    owner_token, _ = await register(client, "owner@example.com")
    board_id = await create_board(client, owner_token, "Design review")
    invite_token = await _create_invite(client, owner_token, board_id)

    response = await client.get(f"/api/v1/invites/{invite_token}")

    assert response.status_code == 200
    assert response.json()["board_title"] == "Design review"
    assert response.json()["role"] == "editor"


async def test_accept_adds_member_with_invite_role(client: AsyncClient) -> None:
    owner_token, _ = await register(client, "owner@example.com")
    board_id = await create_board(client, owner_token)
    invite_token = await _create_invite(client, owner_token, board_id, "viewer")
    guest_token, _ = await register(client, "guest@example.com")

    response = await client.post(
        f"/api/v1/invites/{invite_token}/accept",
        headers=auth(guest_token),
    )

    assert response.status_code == 200
    assert response.json()["id"] == board_id
    assert response.json()["role"] == "viewer"


async def test_second_accept_by_same_user_is_idempotent(client: AsyncClient) -> None:
    owner_token, _ = await register(client, "owner@example.com")
    board_id = await create_board(client, owner_token)
    invite_token = await _create_invite(client, owner_token, board_id, "viewer")
    guest_token, _ = await register(client, "guest@example.com")

    first = await client.post(f"/api/v1/invites/{invite_token}/accept", headers=auth(guest_token))
    second = await client.post(f"/api/v1/invites/{invite_token}/accept", headers=auth(guest_token))

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["role"] == "viewer"


async def test_used_invite_rejects_another_user(client: AsyncClient) -> None:
    owner_token, _ = await register(client, "owner@example.com")
    board_id = await create_board(client, owner_token)
    invite_token = await _create_invite(client, owner_token, board_id)
    first_token, _ = await register(client, "first@example.com")
    second_token, _ = await register(client, "second@example.com")

    await client.post(f"/api/v1/invites/{invite_token}/accept", headers=auth(first_token))
    response = await client.post(
        f"/api/v1/invites/{invite_token}/accept",
        headers=auth(second_token),
    )

    assert response.status_code == 410
    assert response.json()["error"]["code"] == "invite_invalid"


async def test_revoked_invite_is_gone(client: AsyncClient) -> None:
    owner_token, _ = await register(client, "owner@example.com")
    board_id = await create_board(client, owner_token)
    created = await client.post(
        f"/api/v1/boards/{board_id}/invites",
        json={"role": "editor"},
        headers=auth(owner_token),
    )
    invite_token = created.json()["token"]
    invite_id = created.json()["id"]

    revoked = await client.delete(
        f"/api/v1/boards/{board_id}/invites/{invite_id}",
        headers=auth(owner_token),
    )
    guest_token, _ = await register(client, "guest@example.com")
    response = await client.post(
        f"/api/v1/invites/{invite_token}/accept",
        headers=auth(guest_token),
    )

    assert revoked.status_code == 204
    assert response.status_code == 410


async def test_expired_invite_is_gone(client: AsyncClient, session: AsyncSession) -> None:
    owner_token, _ = await register(client, "owner@example.com")
    board_id = await create_board(client, owner_token)
    created = await client.post(
        f"/api/v1/boards/{board_id}/invites",
        json={"role": "editor"},
        headers=auth(owner_token),
    )
    invite = await session.get(BoardInvite, UUID(created.json()["id"]))
    assert invite is not None
    invite.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await session.flush()

    guest_token, _ = await register(client, "guest@example.com")
    response = await client.post(
        f"/api/v1/invites/{created.json()['token']}/accept",
        headers=auth(guest_token),
    )

    assert response.status_code == 410
