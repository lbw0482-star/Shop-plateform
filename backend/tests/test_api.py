"""API 集成测试：依赖已初始化的 PostgreSQL（先运行 scripts/seed.py）。

覆盖 SRS 验收标准：注册唯一性、未登录拦截、购物车结算、库存约束、
模拟支付分支、后台订单流转、积分结算与回退、留言审核、权限边界、
强制改密与订单查询过滤。
"""
from __future__ import annotations

import asyncio
import io
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.repositories import prisma as prisma_repo

client = TestClient(app, raise_server_exceptions=True)
client.__enter__()  # 保持 lifespan 打开：全程复用同一个 Prisma 连接


def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def register_and_login() -> tuple[str, str, dict]:
    username = unique("member")
    password = "Password123!"
    register = client.post(
        "/api/v1/auth/member/register",
        json={"username": username, "password": password, "confirm_password": password},
    )
    assert register.status_code == 201, register.text
    login = client.post(
        "/api/v1/auth/member/login", json={"username": username, "password": password}
    )
    assert login.status_code == 200, login.text
    return username, password, login.cookies


def admin_cookies() -> dict:
    login = client.post(
        "/api/v1/auth/admin/login", json={"username": "admin", "password": "Admin123!"}
    )
    assert login.status_code == 200, login.text
    return login.cookies


def add_to_cart(cookies: dict, product_id: int, quantity: int = 1) -> dict:
    response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product_id, "quantity": quantity},
        cookies=cookies,
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def listed_product() -> dict:
    products = client.get("/api/v1/products", cookies=admin_cookies())
    assert products.status_code == 200, products.text
    items = products.json()["data"]["items"]
    assert items, "请先运行 scripts/seed.py"
    return items[0]


def create_order(cookies: dict, product_id: int, quantity: int = 1) -> dict:
    cart = add_to_cart(cookies, product_id, quantity)
    item_ids = [item["cart_item_id"] for item in cart["items"]]
    response = client.post(
        "/api/v1/orders",
        json={
            "item_ids": item_ids,
            "receiver_name": "测试收货人",
            "receiver_phone": "13800001111",
            "receiver_address": "北京市 testData 1 号",
            "payment_method": "SIMULATED_ONLINE",
        },
        cookies=cookies,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


# ------------------------------------------------------------- acceptance --


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


def test_duplicate_username_rejected():
    username = unique("member")
    password = "Password123!"
    first = client.post(
        "/api/v1/auth/member/register",
        json={"username": username, "password": password, "confirm_password": password},
    )
    assert first.status_code == 201
    duplicate = client.post(
        "/api/v1/auth/member/register",
        json={"username": username.upper(), "password": password, "confirm_password": password},
    )
    assert duplicate.status_code == 409


def test_protected_routes_require_login():
    assert client.get("/api/v1/products").status_code == 401
    assert client.get("/api/v1/cart").status_code == 401
    assert client.get("/api/v1/orders").status_code == 401


def test_member_register_login_and_cart():
    username, password, cookies = register_and_login()
    me = client.get("/api/v1/auth/me", cookies=cookies)
    assert me.status_code == 200
    assert me.json()["data"]["user"]["username"] == username
    product = listed_product()
    cart = add_to_cart(cookies, product["product_id"], 2)
    assert cart["items"][0]["quantity"] == 2
    checkout = client.post(
        "/api/v1/cart/checkout-preview",
        json={"item_ids": [cart["items"][0]["cart_item_id"]]},
        cookies=cookies,
    )
    assert checkout.status_code == 200


def test_cart_stock_and_status_rules():
    cookies = register_and_login()[2]
    product = listed_product()
    blocked = client.post(
        "/api/v1/cart/items",
        json={"product_id": product["product_id"], "quantity": product["stock_qty"] + 1},
        cookies=cookies,
    )
    assert blocked.status_code == 400


def test_order_lifecycle_points_and_stock():
    cookies = register_and_login()[2]
    product = listed_product()
    before = product["stock_qty"]
    order = create_order(cookies, product["product_id"])
    assert order["order_status"] == "W"
    assert order["total_amount"] == str(Decimal(product["unit_price"]) * 1)

    paid = client.post(f"/api/v1/orders/{order['order_id']}/pay", cookies=cookies)
    assert paid.status_code == 200
    body = paid.json()["data"]
    assert body["payment_status"] == "S"
    assert body["order"]["order_status"] == "C"
    records = client.get(
        f"/api/v1/admin/orders/{order['order_id']}", cookies=admin_cookies()
    )
    assert records.json()["data"]["payments"], "支付流水未落库"

    confirmed = client.post(
        f"/api/v1/admin/orders/{order['order_id']}/confirm", cookies=admin_cookies()
    )
    assert confirmed.json()["data"]["order_status"] == "P"
    completed = client.post(
        f"/api/v1/admin/orders/{order['order_id']}/complete", cookies=admin_cookies()
    )
    assert completed.json()["data"]["order_status"] == "F"

    me = client.get("/api/v1/auth/me", cookies=cookies)
    assert me.json()["data"]["user"]["total_points"] >= order["earned_points"]

    listed = client.get("/api/v1/products", cookies=admin_cookies()).json()["data"]["items"]
    after = next(p for p in listed if p["product_id"] == product["product_id"])
    assert after["stock_qty"] == before - 1

    # 重复结算积分（幂等）：再次 complete 会被前置状态拦截，积分不变
    points_before = me.json()["data"]["user"]["total_points"]
    again = client.post(
        f"/api/v1/admin/orders/{order['order_id']}/complete", cookies=admin_cookies()
    )
    assert again.status_code == 400
    me_again = client.get("/api/v1/auth/me", cookies=cookies)
    assert me_again.json()["data"]["user"]["total_points"] == points_before


def test_pay_failure_restores_stock_and_records_payment():
    cookies = register_and_login()[2]
    product = listed_product()
    before = product["stock_qty"]
    order = create_order(cookies, product["product_id"])
    failed = client.post(
        f"/api/v1/orders/{order['order_id']}/pay?success=false", cookies=cookies
    )
    assert failed.status_code == 200
    data = failed.json()["data"]
    assert data["payment_status"] == "F"
    assert data["order"]["order_status"] == "X"
    detail = client.get(
        f"/api/v1/orders/{order['order_id']}", cookies=cookies
    ).json()["data"]
    assert detail["payments"][0]["payment_status"] == "F"
    assert detail["payments"][0]["payment_no"]
    listed = client.get("/api/v1/products", cookies=admin_cookies()).json()["data"]["items"]
    after = next(p for p in listed if p["product_id"] == product["product_id"])
    assert after["stock_qty"] == before


def test_cancel_restores_stock():
    cookies = register_and_login()[2]
    product = listed_product()
    before = product["stock_qty"]
    order = create_order(cookies, product["product_id"])
    cancelled = client.post(f"/api/v1/orders/{order['order_id']}/cancel", cookies=cookies)
    assert cancelled.json()["data"]["order_status"] == "X"
    listed = client.get("/api/v1/products", cookies=admin_cookies()).json()["data"]["items"]
    after = next(p for p in listed if p["product_id"] == product["product_id"])
    assert after["stock_qty"] == before


def test_order_search_by_no_and_status():
    cookies = register_and_login()[2]
    order = create_order(cookies, listed_product()["product_id"])
    found = client.get(
        f"/api/v1/orders?keyword={order['order_no']}", cookies=cookies
    )
    assert found.status_code == 200
    items = found.json()["data"]["items"]
    assert items and items[0]["order_no"] == order["order_no"]
    empty = client.get(
        f"/api/v1/orders?keyword={unique('nope')}", cookies=cookies
    )
    assert empty.json()["data"]["total"] == 0


def test_unpaid_order_update_revalidates_stock():
    cookies = register_and_login()[2]
    product = listed_product()
    order = create_order(cookies, product["product_id"])
    updated = client.patch(
        f"/api/v1/orders/{order['order_id']}",
        json={
            "receiver_address": "上海市浦东新区新区路 9 号",
            "items": [
                {"product_id": product["product_id"], "quantity": product["stock_qty"] + 5}
            ],
        },
        cookies=cookies,
    )
    assert updated.status_code == 400
    ok_update = client.patch(
        f"/api/v1/orders/{order['order_id']}",
        json={"receiver_address": "上海市浦东新区新区路 9 号"},
        cookies=cookies,
    )
    assert ok_update.status_code == 200
    assert ok_update.json()["data"]["receiver_address"].startswith("上海市")


def test_refund_flow_rolls_back_points():
    cookies = register_and_login()[2]
    order = create_order(cookies, listed_product()["product_id"])
    client.post(f"/api/v1/orders/{order['order_id']}/pay", cookies=cookies)
    client.post(f"/api/v1/admin/orders/{order['order_id']}/confirm", cookies=admin_cookies())
    client.post(f"/api/v1/admin/orders/{order['order_id']}/complete", cookies=admin_cookies())
    points_after_complete = client.get("/api/v1/auth/me", cookies=cookies).json()["data"]["user"]["total_points"]

    applied = client.post(
        f"/api/v1/orders/{order['order_id']}/refund-apply",
        json={"reason": "商品包装破损"},
        cookies=cookies,
    )
    assert applied.json()["data"]["order_status"] == "R"
    refunded = client.post(
        f"/api/v1/admin/orders/{order['order_id']}/refund", cookies=admin_cookies()
    )
    assert refunded.json()["data"]["order_status"] == "D"
    assert refunded.json()["data"]["payment_status"] == "R"
    points_after_refund = client.get("/api/v1/auth/me", cookies=cookies).json()["data"]["user"]["total_points"]
    assert points_after_refund == points_after_complete - order["earned_points"]


def test_message_moderation_flow():
    cookies = register_and_login()[2]
    title = unique("留言标题")
    created = client.post(
        "/api/v1/member/messages",
        json={"title": title, "content": "等待审核的留言内容"},
        cookies=cookies,
    )
    assert created.status_code == 201
    message_id = created.json()["data"]["message_id"]
    public = client.get("/api/v1/messages/public", cookies=cookies).json()["data"]
    assert all(item["message_id"] != message_id for item in public)

    admin = client.post(
        f"/api/v1/admin/messages/{message_id}/reply",
        json={"content": "收到，正在处理中"},
        cookies=admin_cookies(),
    )
    assert admin.status_code == 200
    approved = client.post(
        f"/api/v1/admin/messages/{message_id}/approve", cookies=admin_cookies()
    )
    assert approved.status_code == 200
    public = client.get("/api/v1/messages/public", cookies=cookies).json()["data"]
    target = next(item for item in public if item["message_id"] == message_id)
    assert target["replies"] and target["replies"][0]["content"] == "收到，正在处理中"

    own = client.get("/api/v1/member/messages", cookies=cookies).json()["data"]
    mine = next(item for item in own if item["message_id"] == message_id)
    assert mine["message_status"] == "A"


def test_must_change_password_blocks_shopping():
    username, password, cookies = register_and_login()
    user_id = client.get("/api/v1/auth/me", cookies=cookies).json()["data"]["user"]["user_id"]
    reset = client.post(
        f"/api/v1/admin/users/{user_id}/reset-password",
        json={"temporary_password": "Welcome@123"},
        cookies=admin_cookies(),
    )
    assert reset.status_code == 200
    login = client.post(
        "/api/v1/auth/member/login", json={"username": username, "password": "Welcome@123"}
    )
    assert login.status_code == 200
    forced_cookies = login.cookies
    assert login.json()["data"]["user"]["must_change_password"] is True
    product = listed_product()
    blocked = client.post(
        "/api/v1/cart/items",
        json={"product_id": product["product_id"], "quantity": 1},
        cookies=forced_cookies,
    )
    assert blocked.status_code == 400
    changed = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "Welcome@123", "new_password": "NewPass@123", "confirm_password": "NewPass@123"},
        cookies=forced_cookies,
    )
    assert changed.status_code == 200
    allowed = client.post(
        "/api/v1/cart/items",
        json={"product_id": product["product_id"], "quantity": 1},
        cookies=forced_cookies,
    )
    assert allowed.status_code == 200


def test_admin_permission_boundary():
    oper_login = client.post(
        "/api/v1/auth/admin/login", json={"username": "operator", "password": "Oper12345!"}
    )
    oper = oper_login.cookies
    assert client.get("/api/v1/admin/audit-logs", cookies=oper).status_code == 403
    assert client.get("/api/v1/admin/admins", cookies=oper).status_code == 403
    level_patch = client.patch(
        "/api/v1/admin/levels/1",
        json={"min_points": 0},
        cookies=oper,
    )
    assert level_patch.status_code == 403
    assert client.get("/api/v1/admin/levels", cookies=oper).status_code == 200
    assert client.get("/api/v1/admin/orders", cookies=oper).status_code == 200


def test_level_rules_update_and_members_listing():
    super_admin = admin_cookies()
    row = client.patch(
        "/api/v1/admin/levels/2",
        json={"min_points": 1200, "max_points": 5999},
        cookies=super_admin,
    )
    assert row.status_code == 200
    updated = client.get("/api/v1/admin/levels", cookies=super_admin).json()["data"]
    silver = next(level for level in updated if level["level_id"] == 2)
    assert silver["min_points"] == 1200 and silver["max_points"] == 5999
    # 还原
    client.patch(
        "/api/v1/admin/levels/2",
        json={"min_points": 1000, "max_points": 4999},
        cookies=super_admin,
    )


def test_adjust_points_and_level():
    cookies = register_and_login()[2]
    user_id = client.get("/api/v1/auth/me", cookies=cookies).json()["data"]["user"]["user_id"]
    adjusted = client.post(
        f"/api/v1/admin/users/{user_id}/adjust-points",
        json={"points": 5200, "reason": "活动奖励"},
        cookies=admin_cookies(),
    )
    assert adjusted.status_code == 200
    level_name = adjusted.json()["data"]["level_name"]
    assert level_name == "金牌会员"
    point_rows = client.get("/api/v1/member/points", cookies=cookies).json()["data"]
    assert any(row["transaction_type"] == "ADJUST" for row in point_rows["transactions"])


def test_address_book_crud():
    cookies = register_and_login()[2]
    created = client.post(
        "/api/v1/member/addresses",
        json={"receiver_name": "测试人", "receiver_phone": "13900002222", "address_detail": "广州市天河区科韵路 18 号", "is_default": True},
        cookies=cookies,
    )
    assert created.status_code == 201
    address_id = created.json()["data"]["address_id"]
    updated = client.patch(
        f"/api/v1/member/addresses/{address_id}",
        json={"receiver_name": "测试人二号"},
        cookies=cookies,
    )
    assert updated.json()["data"]["receiver_name"] == "测试人二号"
    listed = client.get("/api/v1/member/addresses", cookies=cookies).json()["data"]
    assert any(item["address_id"] == address_id for item in listed)
    deleted = client.delete(f"/api/v1/member/addresses/{address_id}", cookies=cookies)
    assert deleted.status_code == 200


def test_category_update_and_disable():
    admin = admin_cookies()
    created = client.post(
        "/api/v1/admin/categories",
        json={"category_name": unique("测试分类"), "description": "临时分类"},
        cookies=admin,
    )
    assert created.status_code == 201
    category_id = created.json()["data"]["category_id"]
    renamed = client.patch(
        f"/api/v1/admin/categories/{category_id}",
        json={"category_name": unique("改名分类"), "status": "I"},
        cookies=admin,
    )
    assert renamed.status_code == 200
    assert renamed.json()["data"]["status"] == "I"
    member_view = client.get("/api/v1/categories", cookies=register_and_login()[2]).json()["data"]
    assert all(item["category_id"] != category_id for item in member_view)


def test_product_image_upload_and_delete():
    admin = admin_cookies()
    product_id = listed_product()["product_id"]
    payload = io.BytesIO(
        b"\x89PNG\r\n\x1a\n" + b"0" * 64
    )
    uploaded = client.post(
        f"/api/v1/admin/products/{product_id}/images",
        files={"image": ("test.png", payload, "image/png")},
        data={"is_main": "false", "sort_no": "9"},
        cookies=admin,
    )
    assert uploaded.status_code == 201, uploaded.text
    image_id = uploaded.json()["data"]["image_id"]
    listed = client.get(f"/api/v1/admin/products/{product_id}/images", cookies=admin).json()["data"]
    assert any(row["image_id"] == image_id for row in listed)
    deleted = client.delete(f"/api/v1/admin/product-images/{image_id}", cookies=admin)
    assert deleted.status_code == 200


def test_product_search_filters():
    cookies = register_and_login()[2]
    all_rows = client.get("/api/v1/products?page_size=100", cookies=cookies).json()["data"]
    target = all_rows["items"][0]
    by_name = client.get(
        f"/api/v1/products?keyword={target['product_name']}", cookies=cookies
    ).json()["data"]
    assert by_name["total"] >= 1
    detail = client.get(
        f"/api/v1/products/{target['product_id']}", cookies=cookies
    ).json()["data"]
    assert detail["product_id"] == target["product_id"]
    assert detail["images"] is not None


def test_admin_statistics():
    stats = client.get("/api/v1/admin/statistics", cookies=admin_cookies()).json()["data"]
    assert stats["member_count"] >= 1
    assert "paid_amount" in stats


async def test_concurrent_orders_cannot_oversell():
    """并发下单不会产生负库存：库存 1 的商品仅一单成功。"""
    connected_here = not prisma_repo.client.is_connected()
    if connected_here:
        await prisma_repo.connect()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            login = await http.post(
                "/api/v1/auth/admin/login",
                json={"username": "admin", "password": "Admin123!"},
            )
            admin = login.cookies
            product = (await http.get("/api/v1/products?page_size=100", cookies=admin)).json()["data"]["items"][0]
            original_stock = product["stock_qty"]
            await http.patch(
                f"/api/v1/admin/products/{product['product_id']}",
                json={"stock_qty": 1},
                cookies=admin,
            )
            results = []

            async def buyer() -> None:
                username = unique("member")
                await http.post(
                    "/api/v1/auth/member/register",
                    json={"username": username, "password": "Password123!", "confirm_password": "Password123!"},
                )
                member_login = await http.post(
                    "/api/v1/auth/member/login",
                    json={"username": username, "password": "Password123!"},
                )
                cookies = member_login.cookies
                cart = await http.post(
                    "/api/v1/cart/items",
                    json={"product_id": product["product_id"], "quantity": 1},
                    cookies=cookies,
                )
                item_ids = [item["cart_item_id"] for item in cart.json()["data"]["items"]]
                order = await http.post(
                    "/api/v1/orders",
                    json={
                        "item_ids": item_ids,
                        "receiver_name": "并发", "receiver_phone": "13700003333",
                        "receiver_address": "并发地址 1",
                        "payment_method": "SIMULATED_ONLINE",
                    },
                    cookies=cookies,
                )
                results.append(order.status_code)

            await asyncio.gather(buyer(), buyer())
            assert sorted(results) == [201, 400]
            stock = (await http.get("/api/v1/products?page_size=100", cookies=admin)).json()["data"]["items"]
            after = next(p for p in stock if p["product_id"] == product["product_id"])
            assert after["stock_qty"] == 0
            await http.patch(
                f"/api/v1/admin/products/{product['product_id']}",
                json={"stock_qty": original_stock},
                cookies=admin,
            )
    finally:
        if connected_here:
            await prisma_repo.disconnect()
