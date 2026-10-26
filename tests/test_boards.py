from uuid import UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BoardMember, BoardRole
from tests.helpers import auth, create_board, register

BOARDS = "/api/v1/boards"


async def test_create_board_makes_creator_owner(client: AsyncClient) -> None:
    token, user_id = await register(client, "owner@example.com")

    created = await client.post(BOARDS, json={"title": "Sprint"}, headers=auth(token))

    assert created.status_code == 201
    assert created.json()["owner_id"] == user_id

    listed = await client.get(BOARDS, headers=auth(token))
    assert [item["role"] for item in listed.json()] == ["owner"]


async def test_board_limit_applies_to_owned_boards(client: AsyncClient) -> None:
    token, _ = await register(client, "owner@example.com")
    for index in range(5):
        await create_board(client, token, f"Board {index}")

    response = await client.post(BOARDS, json={"title": "Sixth"}, headers=auth(token))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "limit_exceeded"
    assert response.json()["error"]["details"] == {"limit": 5}


async def test_non_member_cannot_tell_board_exists(client: AsyncClient) -> None:
    owner_token, _ = await register(client, "owner@example.com")
    board_id = await create_board(client, owner_token)
    stranger_token, _ = await register(client, "stranger@example.com")

    response = await client.get(f"{BOARDS}/{board_id}", headers=auth(stranger_token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_viewer_cannot_rename_board(client: AsyncClient, session: AsyncSession) -> None:
    owner_token, _ = await register(client, "owner@example.com")
    board_id = await create_board(client, owner_token)
    viewer_token, viewer_id = await register(client, "viewer@example.com")
    session.add(
        BoardMember(board_id=UUID(board_id), user_id=UUID(viewer_id), role=BoardRole.viewer)
    )
    await session.flush()

    response = await client.patch(
        f"{BOARDS}/{board_id}",
        json={"title": "Hijacked"},
        headers=auth(viewer_token),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_owner_deletes_board(client: AsyncClient) -> None:
    token, _ = await register(client, "owner@example.com")
    board_id = await create_board(client, token)

    assert (await client.delete(f"{BOARDS}/{board_id}", headers=auth(token))).status_code == 204
    assert (await client.get(f"{BOARDS}/{board_id}", headers=auth(token))).status_code == 404
