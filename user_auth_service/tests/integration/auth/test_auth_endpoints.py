def test_register_and_login_success(client):
    register_response = client.post(
        "/auth/register",
        json={
            "username": "John",
            "email": "JOHN@EXAMPLE.COM",
            "password": "secret123",
        },
    )
    assert register_response.status_code == 201
    register_data = register_response.json()["data"]
    assert register_data["token_type"] == "bearer"
    assert register_data["user"]["email"] == "john@example.com"
    assert register_data["user"]["username"] == "John"
    assert register_data["access_token"]
    assert register_data["refresh_token"]

    login_response = client.post(
        "/auth/login",
        json={
            "email": "john@example.com",
            "password": "secret123",
        },
    )
    assert login_response.status_code == 200
    login_data = login_response.json()["data"]
    assert login_data["token_type"] == "bearer"
    assert login_data["user"]["email"] == "john@example.com"


def test_register_returns_conflict_for_duplicate_email(client):
    payload = {
        "username": "johnny",
        "email": "john@example.com",
        "password": "secret123",
    }
    first_response = client.post("/auth/register", json=payload)
    assert first_response.status_code == 201

    second_response = client.post(
        "/auth/register",
        json={
            "username": "another",
            "email": payload["email"],
            "password": payload["password"],
        },
    )
    assert second_response.status_code == 409
    assert second_response.json()["error"]["message"] == "email already exists"


def test_login_returns_401_for_invalid_credentials(client):
    client.post(
        "/auth/register",
        json={
            "username": "john",
            "email": "john@example.com",
            "password": "secret123",
        },
    )

    login_response = client.post(
        "/auth/login",
        json={
            "email": "john@example.com",
            "password": "wrong-password",
        },
    )
    assert login_response.status_code == 401
    assert login_response.json()["error"]["message"] == "invalid credentials"


def test_refresh_rotates_token_and_invalidates_old_one(client):
    register_response = client.post(
        "/auth/register",
        json={
            "username": "john",
            "email": "john@example.com",
            "password": "secret123",
        },
    )
    first_refresh_token = register_response.json()["data"]["refresh_token"]

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": first_refresh_token},
    )
    assert refresh_response.status_code == 200
    second_refresh_token = refresh_response.json()["data"]["refresh_token"]
    assert second_refresh_token != first_refresh_token

    old_token_response = client.post(
        "/auth/refresh",
        json={"refresh_token": first_refresh_token},
    )
    assert old_token_response.status_code == 401
    assert old_token_response.json()["error"]["message"] == "invalid refresh token"


def test_logout_revokes_refresh_token(client):
    register_response = client.post(
        "/auth/register",
        json={
            "username": "john",
            "email": "john@example.com",
            "password": "secret123",
        },
    )
    refresh_token = register_response.json()["data"]["refresh_token"]

    logout_response = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout_response.status_code == 200
    assert logout_response.json()["data"] == {"revoked": True}

    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 401
    assert refresh_response.json()["error"]["message"] == "invalid refresh token"


def test_me_returns_current_user_by_access_token(client):
    register_response = client.post(
        "/auth/register",
        json={
            "username": "john",
            "email": "john@example.com",
            "password": "secret123",
        },
    )
    access_token = register_response.json()["data"]["access_token"]

    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_response.status_code == 200
    user = me_response.json()["data"]
    assert user["email"] == "john@example.com"
    assert user["username"] == "john"
