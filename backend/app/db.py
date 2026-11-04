"""Small repository used by the course project.

The API is deliberately independent from a generated Prisma client so it can be
started for a classroom demo without Docker. ``prisma/schema.prisma`` remains
the source of truth for PostgreSQL and the repository can be replaced by the
generated client without changing the HTTP layer.
"""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from .core.security import hash_password


def now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Session:
    token: str
    subject_type: str
    subject_id: int
    expires_at: datetime


@dataclass
class Level:
    level_id: int
    level_name: str
    min_points: int
    max_points: int | None
    sort_no: int
    status: str = "A"


@dataclass
class User:
    user_id: int
    username: str
    password_hash: str
    must_change_password: bool = False
    gender: str = "U"
    email: str | None = None
    phone: str | None = None
    register_time: datetime = field(default_factory=now)
    total_points: int = 0
    level_id: int = 1
    account_status: str = "A"
    last_login_time: datetime | None = None


@dataclass
class Admin:
    admin_id: int
    admin_name: str
    password_hash: str
    real_name: str | None
    roles: list[str]
    status: str = "A"
    last_login_time: datetime | None = None


@dataclass
class Category:
    category_id: int
    category_name: str
    description: str | None = None
    sort_no: int = 0
    status: str = "A"


@dataclass
class Product:
    product_id: int
    product_code: str
    product_name: str
    category_id: int
    stock_qty: int
    unit_price: Decimal
    product_intro: str | None
    recommend_flag: bool
    product_points: int
    main_image_url: str | None = None
    product_status: str = "D"
    listing_date: datetime | None = None
    created_time: datetime = field(default_factory=now)
    updated_time: datetime | None = None


@dataclass
class CartItem:
    cart_item_id: int
    product_id: int
    quantity: int
    add_time: datetime = field(default_factory=now)
    updated_time: datetime | None = None


@dataclass
class OrderItem:
    order_item_id: int
    product_id: int
    product_name_snapshot: str
    unit_price: Decimal
    quantity: int
    item_points: int
    subtotal: Decimal


@dataclass
class Order:
    order_id: int
    order_no: str
    user_id: int
    order_time: datetime
    receiver_name: str
    receiver_phone: str
    receiver_address: str
    payment_method: str
    payment_status: str
    order_status: str
    total_amount: Decimal
    earned_points: int
    remark: str | None
    items: list[OrderItem]
    cancel_reason: str | None = None
    refund_reason: str | None = None
    refund_time: datetime | None = None
    completed_time: datetime | None = None


@dataclass
class Message:
    message_id: int
    user_id: int
    title: str
    content: str
    message_status: str = "P"
    created_time: datetime = field(default_factory=now)
    updated_time: datetime | None = None
    reviewer_admin_id: int | None = None
    review_time: datetime | None = None
    replies: list[dict[str, Any]] = field(default_factory=list)


class Store:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.next_ids = {
            "user": 1,
            "admin": 1,
            "category": 1,
            "product": 1,
            "cart_item": 1,
            "order": 1,
            "order_item": 1,
            "message": 1,
            "reply": 1,
        }
        self.levels: dict[int, Level] = {}
        self.users: dict[int, User] = {}
        self.admins: dict[int, Admin] = {}
        self.categories: dict[int, Category] = {}
        self.products: dict[int, Product] = {}
        self.carts: dict[int, list[CartItem]] = {}
        self.orders: dict[int, Order] = {}
        self.messages: dict[int, Message] = {}
        self.sessions: dict[str, Session] = {}
        self.audit_logs: list[dict[str, Any]] = []
        self.point_transactions: list[dict[str, Any]] = []
        self._seed()

    def _id(self, key: str) -> int:
        value = self.next_ids[key]
        self.next_ids[key] += 1
        return value

    def _seed(self) -> None:
        for level in (
            Level(1, "普通会员", 0, 999, 1),
            Level(2, "银牌会员", 1000, 4999, 2),
            Level(3, "金牌会员", 5000, 9999, 3),
            Level(4, "钻石会员", 10000, None, 4),
        ):
            self.levels[level.level_id] = level
        admin = Admin(self._id("admin"), "admin", hash_password("Admin123!"), "系统管理员", ["SUPER_ADMIN"])
        self.admins[admin.admin_id] = admin
        category = Category(self._id("category"), "日用百货", "默认商品分类", 1)
        self.categories[category.category_id] = category
        for code, name, price, stock, points in (
            ("DEMO-001", "轻量保温杯", Decimal("89.00"), 50, 89),
            ("DEMO-002", "桌面收纳盒", Decimal("39.90"), 80, 39),
            ("DEMO-003", "帆布购物袋", Decimal("29.90"), 120, 29),
        ):
            product = Product(
                self._id("product"), code, name, category.category_id, stock, price,
                "适合课程演示的示例商品。", code == "DEMO-001", points,
                f"/uploads/{code.lower()}.jpg", "O", now(), now(), now(),
            )
            self.products[product.product_id] = product

    def cleanup_sessions(self) -> None:
        current = now()
        for token, session in list(self.sessions.items()):
            if session.expires_at <= current:
                self.sessions.pop(token, None)

    def create_session(self, subject_type: str, subject_id: int, ttl_hours: int) -> str:
        self.cleanup_sessions()
        token = secrets.token_urlsafe(32)
        self.sessions[token] = Session(token, subject_type, subject_id, now() + timedelta(hours=ttl_hours))
        return token

    def get_session(self, token: str | None) -> Session | None:
        if not token:
            return None
        self.cleanup_sessions()
        session = self.sessions.get(token)
        if session and session.expires_at > now():
            return session
        return None

    def destroy_session(self, token: str | None) -> None:
        if token:
            self.sessions.pop(token, None)

    def level_for_points(self, points: int) -> Level:
        active = sorted((x for x in self.levels.values() if x.status == "A"), key=lambda x: x.min_points)
        selected = active[0]
        for level in active:
            if points >= level.min_points and (level.max_points is None or points <= level.max_points):
                selected = level
        return selected

    def public_product(self, product: Product) -> dict[str, Any]:
        return {
            "id": product.product_id,
            "product_id": product.product_id,
            "product_code": product.product_code,
            "product_name": product.product_name,
            "category_id": product.category_id,
            "category_name": self.categories.get(product.category_id).category_name if product.category_id in self.categories else None,
            "stock_qty": product.stock_qty,
            "unit_price": str(product.unit_price),
            "product_intro": product.product_intro,
            "recommend_flag": product.recommend_flag,
            "product_points": product.product_points,
            "main_image_url": product.main_image_url,
            "product_status": product.product_status,
            "listing_date": product.listing_date,
        }

    def public_user(self, user: User) -> dict[str, Any]:
        return {
            "id": user.user_id,
            "user_id": user.user_id,
            "username": user.username,
            "display_name": user.username,
            "role": "MEMBER",
            "gender": user.gender,
            "email": user.email,
            "phone": user.phone,
            "total_points": user.total_points,
            "level_name": self.levels[user.level_id].level_name,
            "account_status": user.account_status,
            "must_change_password": user.must_change_password,
        }

    def public_admin(self, admin: Admin) -> dict[str, Any]:
        return {
            "id": admin.admin_id,
            "admin_id": admin.admin_id,
            "admin_name": admin.admin_name,
            "username": admin.admin_name,
            "display_name": admin.real_name or admin.admin_name,
            "role": "SUPER_ADMIN" if "SUPER_ADMIN" in admin.roles else "OPER_ADMIN",
            "real_name": admin.real_name,
            "roles": admin.roles,
            "status": admin.status,
        }

    def public_order(self, order: Order) -> dict[str, Any]:
        return {
            "id": order.order_id,
            "order_id": order.order_id,
            "order_no": order.order_no,
            "user_id": order.user_id,
            "order_time": order.order_time,
            "receiver_name": order.receiver_name,
            "receiver_phone": order.receiver_phone,
            "receiver_address": order.receiver_address,
            "payment_method": order.payment_method,
            "payment_status": order.payment_status,
            "order_status": order.order_status,
            "total_amount": str(order.total_amount),
            "earned_points": order.earned_points,
            "remark": order.remark,
            "items": [
                {
                    "order_item_id": item.order_item_id,
                    "product_id": item.product_id,
                    "product_name_snapshot": item.product_name_snapshot,
                    "unit_price": str(item.unit_price),
                    "quantity": item.quantity,
                    "item_points": item.item_points,
                    "subtotal": str(item.subtotal),
                }
                for item in order.items
            ],
            "cancel_reason": order.cancel_reason,
            "refund_reason": order.refund_reason,
            "refund_time": order.refund_time,
            "completed_time": order.completed_time,
        }


store = Store()

