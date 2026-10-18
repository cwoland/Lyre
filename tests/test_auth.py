from httpx import AsyncClient

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
COOKIE = "lyre_refresh"

CREDENTIALS = {
    "email": "anton@example.com",
    "password": "correct-horse-battery",
    "display_name": "Anton",
}


async def test_register_returns_token_and_sets_cookie(client: AsyncClient) -> None:
    response = await client.post(REGISTER, json=CREDENTIALS)

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == CREDENTIALS["email"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["user"]["cursor_color"].startswith("#")
    assert COOKIE in response.cookies


async def test_register_rejects_duplicate_email_case_insensitively(client: AsyncClient) -> None:
    await client.post(REGISTER, json=CREDENTIALS)

    response = await client.post(REGISTER, json={**CREDENTIALS, "email": "ANTON@example.com"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


async def test_register_rejects_short_password(client: AsyncClient) -> None:
    response = await client.post(REGISTER, json={**CREDENTIALS, "password": "short"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_login_rejects_wrong_password(client: AsyncClient) -> None:
    await client.post(REGISTER, json=CREDENTIALS)

    response = await client.post(
        LOGIN,
        json={"email": CREDENTIALS["email"], "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_me_requires_bearer_token(client: AsyncClient) -> None:
    response = await client.get(ME)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_me_returns_current_user(client: AsyncClient) -> None:
    token = (await client.post(REGISTER, json=CREDENTIALS)).json()["access_token"]

    response = await client.get(ME, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["display_name"] == "Anton"


async def test_refresh_rotates_token_and_detects_reuse(client: AsyncClient) -> None:
    await client.post(REGISTER, json=CREDENTIALS)
    first_token = client.cookies[COOKIE]

    rotated = await client.post(REFRESH)
    second_token = client.cookies[COOKIE]

    assert rotated.status_code == 200
    assert second_token != first_token

    client.cookies.set(COOKIE, first_token)
    reused = await client.post(REFRESH)
    assert reused.status_code == 401

    client.cookies.set(COOKIE, second_token)
    after_breach = await client.post(REFRESH)
    assert after_breach.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    await client.post(REGISTER, json=CREDENTIALS)

    assert (await client.post(LOGOUT)).status_code == 204
    assert (await client.post(REFRESH)).status_code == 401
