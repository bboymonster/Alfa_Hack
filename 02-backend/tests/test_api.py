from datetime import UTC, datetime, timedelta

import jwt
import pytest


def get_feed(client, headers, **params):
    response = client.get("/api/feed", headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def register(client, **changes):
    body = {
        "email": "new@example.com",
        "password": "new-password-123",
        "full_name": "Новый пользователь",
        "company_id": "U_1595",
        "role": "CFO",
    }
    return client.post("/api/auth/register", json=body | changes)


def test_health_and_openapi_are_available_without_login(client):
    assert client.get("/health").json() == {
        "status": "ok",
        "mode": "mock",
        "storage": "memory",
        "ai": "mock",
    }
    schema = client.get("/openapi.json").json()
    assert "/api/feed" in schema["paths"]
    assert schema["paths"]["/api/feed"]["get"]["security"] == [{"HTTPBearer": []}]
    assert client.get("/docs").status_code == 200


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/auth/me"),
        ("get", "/api/companies"),
        ("get", "/api/feed"),
        ("get", "/api/feed/missing"),
        ("post", "/api/feed/missing/favorite"),
        ("post", "/api/feed/missing/ask"),
    ],
)
def test_protected_routes_require_login(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_demo_login_and_profile_do_not_expose_passwords(client, headers):
    profile = client.get("/api/auth/me", headers=headers).json()
    assert profile["email"] == "alfa-hack-2026"
    assert profile["current_company_id"] == "U_1595"
    assert len(profile["allowed_company_ids"]) == 3
    assert "password" not in str(profile)
    assert "hashed_password" not in str(profile)


@pytest.mark.parametrize("email", ["missing@example.com", "alfa-hack-2026"])
def test_bad_credentials_have_same_error(client, email):
    response = client.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный логин или пароль."


def test_registration_login_and_duplicate_email(client):
    response = register(client)
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["allowed_company_ids"] == ["U_1595"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    login = client.post(
        "/api/auth/login", json={"email": "NEW@example.com", "password": "new-password-123"}
    )
    assert login.status_code == 200
    assert register(client, email="NEW@example.com").status_code == 409


@pytest.mark.parametrize("kind", ["expired", "tampered", "missing_exp"])
def test_invalid_tokens_are_rejected(client, headers, kind):
    settings = client.app.state.settings
    user = client.get("/api/auth/me", headers=headers).json()
    now = datetime.now(UTC)
    payload = {"sub": user["id"], "iat": now, "exp": now + timedelta(minutes=5)}
    key = settings.jwt_secret_key
    if kind == "expired":
        payload["exp"] = now - timedelta(seconds=1)
    elif kind == "tampered":
        key = "different-signing-key-with-32-characters"
    else:
        del payload["exp"]
    token = jwt.encode(payload, key, algorithm="HS256")
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_companies_and_personalized_feed(client, headers):
    companies = client.get("/api/companies", headers=headers).json()
    assert {company["synthetic_u"] for company in companies} == {"U_1595", "U_1465", "DEMO_LOCAL"}
    retail = get_feed(client, headers, company_id="U_1595", role="CFO")
    local = get_feed(client, headers, company_id="DEMO_LOCAL", role="CFO")
    assert retail["total"] == local["total"] == 3
    assert retail["items"][0]["news"]["id"] == local["items"][0]["news"]["id"]
    assert retail["items"][0]["id"] != local["items"][0]["id"]
    assert "есть кредитные продукты" in retail["items"][0]["insight"]["why_it_matters"]
    assert "нет кредитных продуктов" in local["items"][0]["insight"]["why_it_matters"]
    accountant = get_feed(client, headers, role="ACCOUNTANT")
    assert accountant["items"][0]["news"]["category"] == "Регулирование"


def test_pagination_category_and_empty_pages(client, headers):
    first = get_feed(client, headers, page_size=1)
    second = get_feed(client, headers, page_size=1, page=2)
    assert first["total"] == 3
    assert first["total_pages"] == 3
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert get_feed(client, headers, page=99)["items"] == []
    logistics = get_feed(client, headers, category="Логистика")
    assert logistics["total"] == 1
    assert logistics["items"][0]["news"]["category"] == "Логистика"
    assert get_feed(client, headers, category="Неизвестная категория")["total_pages"] == 0


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 101}, {"role": "ADMIN"}])
def test_invalid_feed_parameters(client, headers, params):
    assert client.get("/api/feed", params=params, headers=headers).status_code == 422


def test_details_and_unknown_resources(client, headers):
    item = get_feed(client, headers)["items"][0]
    detail = client.get(f"/api/feed/{item['id']}", headers=headers)
    assert detail.json() == item
    assert client.get("/api/feed/missing", headers=headers).status_code == 404
    assert (
        client.get("/api/feed", params={"company_id": "MISSING"}, headers=headers).status_code
        == 404
    )


def test_company_access_is_checked_for_list_details_chat_and_favorites(client, headers):
    other_item = get_feed(client, headers, company_id="DEMO_LOCAL")["items"][0]
    token = register(client).json()["access_token"]
    restricted = {"Authorization": f"Bearer {token}"}
    companies = client.get("/api/companies", headers=restricted).json()
    assert [company["synthetic_u"] for company in companies] == ["U_1595"]
    assert (
        client.get("/api/feed", params={"company_id": "DEMO_LOCAL"}, headers=restricted).status_code
        == 403
    )
    path = f"/api/feed/{other_item['id']}"
    assert client.get(path, headers=restricted).status_code == 403
    assert (
        client.post(
            path + "/ask", json={"question": "Что изменилось?"}, headers=restricted
        ).status_code
        == 403
    )
    assert (
        client.post(path + "/favorite", json={"is_favorite": True}, headers=restricted).status_code
        == 403
    )


def test_favorites_are_idempotent_private_and_shared_across_roles(client, headers):
    item = get_feed(client, headers)["items"][0]
    path = f"/api/feed/{item['id']}/favorite"
    for _ in range(2):
        assert client.post(path, json={"is_favorite": True}, headers=headers).json() == {
            "id": item["id"],
            "is_favorite": True,
        }
    saved = get_feed(client, headers, favorites_only=True)
    assert saved["total"] == 1
    assert saved["items"][0]["is_favorite"] is True
    cfo_view = get_feed(client, headers, role="CFO", favorites_only=True)
    assert cfo_view["items"][0]["news"]["id"] == item["news"]["id"]
    another_login = client.post(
        "/api/auth/login", json={"email": "cfo@alfabusiness.ru", "password": "password123"}
    )
    another = {"Authorization": f"Bearer {another_login.json()['access_token']}"}
    assert get_feed(client, another, favorites_only=True)["total"] == 0
    assert client.post(path, json={"is_favorite": False}, headers=headers).status_code == 200
    assert get_feed(client, headers, favorites_only=True)["items"] == []


def test_chat_is_explicitly_mock_and_has_no_fake_bank_citations(client, headers):
    item = get_feed(client, headers)["items"][0]
    assert item["is_demo"] is True
    assert item["insight"]["alfa_bank_position"] is None
    assert item["insight"]["alfa_report_url"] is None
    assert item["insight"]["traceability"]["verified_sources"] == []
    response = client.post(
        f"/api/feed/{item['id']}/ask",
        json={"question": "  Как это влияет на компанию?  "},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["is_demo"] is True
    assert "Ваш вопрос: «Как это влияет на компанию?»" in response.json()["answer"]


def test_request_validation(client, headers):
    item_id = get_feed(client, headers)["items"][0]["id"]
    assert (
        client.post(
            f"/api/feed/{item_id}/ask", json={"question": "   "}, headers=headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/feed/{item_id}/favorite", json={"is_favorite": "false"}, headers=headers
        ).status_code
        == 422
    )
    assert register(client, password="short").status_code == 422
    assert register(client, email="not-an-email").status_code == 422
    assert register(client, unexpected=True).status_code == 422
    assert register(client, company_id="MISSING").status_code == 404


@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://localhost:5173"])
def test_frontend_can_send_json_and_bearer_token(client, origin):
    response = client.options(
        "/api/feed",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_unknown_origin_is_not_allowed(client):
    response = client.options(
        "/api/feed",
        headers={
            "Origin": "https://unconfigured.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
