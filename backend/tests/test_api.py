from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


def test_member_register_login_and_cart():
    username = "test_member_001"
    register = client.post("/api/v1/auth/member/register", json={"username": username, "password": "Password123!", "confirm_password": "Password123!"})
    assert register.status_code == 201
    login = client.post("/api/v1/auth/member/login", json={"username": username, "password": "Password123!"})
    assert login.status_code == 200
    products = client.get("/api/v1/products")
    assert products.status_code == 200
    product = products.json()["data"]["items"][0]
    add = client.post("/api/v1/cart/items", json={"product_id": product["product_id"], "quantity": 1})
    assert add.status_code == 200
    assert len(add.json()["data"]["items"]) == 1


def test_admin_cookie_and_permission():
    login = client.post("/api/v1/auth/admin/login", json={"username": "admin", "password": "Admin123!"})
    assert login.status_code == 200
    levels = client.get("/api/v1/admin/levels")
    assert levels.status_code == 200

