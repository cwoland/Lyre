from httpx import AsyncClient

PASSWORD = "correct-horse-battery"


async def register(client: AsyncClient, email: str) -> tuple[str, str]:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": email.split("@")[0]},
    )
    body = response.json()
    return body["access_token"], body["user"]["id"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def create_board(client: AsyncClient, token: str, title: str = "Sprint") -> str:
    response = await client.post("/api/v1/boards", json={"title": title}, headers=auth(token))
    board_id: str = response.json()["id"]
    return board_id
