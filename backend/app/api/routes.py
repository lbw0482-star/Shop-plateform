from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, File, HTTPException, Query, Response, UploadFile, status

from ..core.config import Settings, get_settings
from ..core.deps import ADMIN_COOKIE, MEMBER_COOKIE, get_current_admin, get_current_member, get_store, require_super_admin, session_cookie_kwargs
from ..core.response import ok, page
from ..core.security import hash_password, verify_password
from ..db import Admin, CartItem, Category, Message, Order, OrderItem, Product, Store, User, now
from ..schemas import (
    AdminCreateRequest,
    AdminStatusRequest,
    CartItemRequest,
    CartItemUpdateRequest,
    CategoryCreateRequest,
    ChangePasswordRequest,
    CheckoutPreviewRequest,
    LevelUpdateRequest,
    LoginRequest,
    MessageCreateRequest,
    MessageUpdateRequest,
    OrderCreateRequest,
    OrderUpdateRequest,
    ProductCreateRequest,
    ProductUpdateRequest,
    ProfileUpdateRequest,
    RefundApplyRequest,
    RegisterRequest,
    ReplyRequest,
    ResetPasswordRequest,
)


router = APIRouter()
settings: Settings = get_settings()


def _error(message: str, code: int = 400) -> HTTPException:
    return HTTPException(status_code=code, detail=message)


def _set_cookie(response: Response, name: str, token: str) -> None:
    response.set_cookie(name, token, **session_cookie_kwargs(settings))


def _clear_cookie(response: Response, name: str) -> None:
    response.delete_cookie(name, path="/")


def _audit(db: Store, admin: Admin, operation_type: str, target_type: str, target_id: object | None = None, detail: str | None = None) -> None:
    db.audit_logs.append({
        "admin_id": admin.admin_id,
        "operation_type": operation_type,
        "target_type": target_type,
        "target_id": str(target_id) if target_id is not None else None,
        "operation_detail": detail,
        "operation_time": now(),
    })


def _user_view(db: Store, user: User) -> dict:
    return db.public_user(user)


def _admin_view(db: Store, admin: Admin) -> dict:
    return db.public_admin(admin)


def _product_or_404(db: Store, product_id: int) -> Product:
    product = db.products.get(product_id)
    if product is None:
        raise _error("商品不存在", 404)
    return product


def _order_or_404(db: Store, order_id: int) -> Order:
    order = db.orders.get(order_id)
    if order is None:
        raise _error("订单不存在", 404)
    return order


@router.get("/health")
async def health() -> dict:
    return ok({"status": "ok", "service": settings.app_name})


# Authentication -----------------------------------------------------------


@router.post("/auth/member/register", status_code=status.HTTP_201_CREATED)
async def member_register(payload: RegisterRequest, response: Response, db: Store = Depends(get_store)) -> dict:
    if any(user.username.lower() == payload.username.lower() for user in db.users.values()):
        raise _error("用户名已存在", 409)
    user = User(db._id("user"), payload.username, hash_password(payload.password))
    db.users[user.user_id] = user
    db.carts[user.user_id] = []
    return ok(_user_view(db, user), "注册成功，请登录")


@router.post("/auth/member/login")
async def member_login(payload: LoginRequest, response: Response, db: Store = Depends(get_store)) -> dict:
    user = next((x for x in db.users.values() if x.username.lower() == payload.username.lower()), None)
    if user is None or not verify_password(payload.password, user.password_hash) or user.account_status != "A":
        raise _error("用户名或密码错误", 401)
    user.last_login_time = now()
    token = db.create_session("member", user.user_id, settings.session_ttl_hours)
    _set_cookie(response, MEMBER_COOKIE, token)
    return ok(_user_view(db, user), "登录成功")


@router.post("/auth/admin/login")
async def admin_login(payload: LoginRequest, response: Response, db: Store = Depends(get_store)) -> dict:
    admin = next((x for x in db.admins.values() if x.admin_name.lower() == payload.username.lower()), None)
    if admin is None or not verify_password(payload.password, admin.password_hash) or admin.status != "A":
        raise _error("管理员账号或密码错误", 401)
    admin.last_login_time = now()
    token = db.create_session("admin", admin.admin_id, settings.session_ttl_hours)
    _set_cookie(response, ADMIN_COOKIE, token)
    return ok(_admin_view(db, admin), "登录成功")


@router.post("/auth/logout")
async def logout(
    response: Response,
    member_session: str | None = Cookie(default=None),
    admin_session: str | None = Cookie(default=None),
    db: Store = Depends(get_store),
) -> dict:
    db.destroy_session(member_session)
    db.destroy_session(admin_session)
    _clear_cookie(response, MEMBER_COOKIE)
    _clear_cookie(response, ADMIN_COOKIE)
    return ok(message="已退出登录")


@router.get("/auth/me")
async def me(
    member_session: str | None = Cookie(default=None),
    admin_session: str | None = Cookie(default=None),
    db: Store = Depends(get_store),
) -> dict:
    if session := db.get_session(member_session):
        if session.subject_type == "member" and (user := db.users.get(session.subject_id)):
            return ok({"type": "member", "user": _user_view(db, user)})
    if session := db.get_session(admin_session):
        if session.subject_type == "admin" and (admin := db.admins.get(session.subject_id)):
            return ok({"type": "admin", "admin": _admin_view(db, admin)})
    raise _error("请先登录", 401)


@router.post("/auth/change-password")
async def change_password(payload: ChangePasswordRequest, user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    if not verify_password(payload.old_password, user.password_hash):
        raise _error("旧密码错误", 400)
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    return ok(message="密码修改成功")


@router.patch("/member/profile")
async def update_profile(payload: ProfileUpdateRequest, user: User = Depends(get_current_member)) -> dict:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    return ok({"user_id": user.user_id, "username": user.username, "gender": user.gender, "email": user.email, "phone": user.phone})


# Product and category -----------------------------------------------------


@router.get("/categories")
async def categories(db: Store = Depends(get_store), _user: User = Depends(get_current_member)) -> dict:
    return ok([vars(x) for x in sorted(db.categories.values(), key=lambda item: item.sort_no) if x.status == "A"])


@router.get("/admin/categories")
async def admin_categories(_admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    return ok([vars(x) for x in sorted(db.categories.values(), key=lambda item: item.sort_no)])


@router.get("/products")
async def products(
    keyword: str | None = None,
    category_id: int | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    recommend: bool | None = None,
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Store = Depends(get_store),
    _user: User = Depends(get_current_member),
) -> dict:
    records = [x for x in db.products.values() if x.product_status == "O"]
    if keyword:
        records = [x for x in records if keyword.lower() in x.product_name.lower() or keyword.lower() in x.product_code.lower()]
    if category_id is not None:
        records = [x for x in records if x.category_id == category_id]
    if min_price is not None:
        records = [x for x in records if x.unit_price >= min_price]
    if max_price is not None:
        records = [x for x in records if x.unit_price <= max_price]
    if recommend is not None:
        records = [x for x in records if x.recommend_flag == recommend]
    records.sort(key=lambda x: x.product_id, reverse=True)
    start = (page_no - 1) * page_size
    return ok(page([db.public_product(x) for x in records[start:start + page_size]], len(records), page_no, page_size))


@router.get("/products/{product_id}")
async def product_detail(product_id: int, db: Store = Depends(get_store), _user: User = Depends(get_current_member)) -> dict:
    product = _product_or_404(db, product_id)
    if product.product_status != "O":
        raise _error("商品已下架", 404)
    return ok(db.public_product(product))


@router.post("/admin/categories", status_code=201)
async def create_category(payload: CategoryCreateRequest, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    if any(x.category_name == payload.category_name for x in db.categories.values()):
        raise _error("分类名称已存在", 409)
    category = Category(db._id("category"), payload.category_name, payload.description, payload.sort_no)
    db.categories[category.category_id] = category
    _audit(db, admin, "CREATE", "CATEGORY", category.category_id)
    return ok(vars(category))


@router.post("/admin/products", status_code=201)
async def create_product(payload: ProductCreateRequest, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    if any(x.product_code == payload.product_code for x in db.products.values()):
        raise _error("商品编号已存在", 409)
    if payload.category_id not in db.categories:
        raise _error("分类不存在", 404)
    product = Product(db._id("product"), payload.product_code, payload.product_name, payload.category_id, payload.stock_qty, payload.unit_price, payload.product_intro, payload.recommend_flag, payload.product_points, payload.main_image_url)
    db.products[product.product_id] = product
    _audit(db, admin, "CREATE", "PRODUCT", product.product_id)
    return ok(db.public_product(product))


@router.get("/admin/products")
async def admin_products(
    keyword: str | None = None,
    product_status: str | None = None,
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _admin: Admin = Depends(get_current_admin),
    db: Store = Depends(get_store),
) -> dict:
    records = list(db.products.values())
    if keyword:
        needle = keyword.lower()
        records = [x for x in records if needle in x.product_name.lower() or needle in x.product_code.lower()]
    if product_status:
        records = [x for x in records if x.product_status == product_status]
    records.sort(key=lambda x: x.product_id, reverse=True)
    start = (page_no - 1) * page_size
    return ok(page([db.public_product(x) for x in records[start:start + page_size]], len(records), page_no, page_size))


@router.patch("/admin/products/{product_id}")
async def update_product(product_id: int, payload: ProductUpdateRequest, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    product = _product_or_404(db, product_id)
    values = payload.model_dump(exclude_unset=True)
    if "category_id" in values and values["category_id"] not in db.categories:
        raise _error("分类不存在", 404)
    for key, value in values.items():
        setattr(product, key, value)
    product.updated_time = now()
    _audit(db, admin, "UPDATE", "PRODUCT", product_id)
    return ok(db.public_product(product))


@router.post("/admin/products/{product_id}/listing")
async def listing_product(product_id: int, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    product = _product_or_404(db, product_id)
    product.product_status = "O"
    product.listing_date = now()
    _audit(db, admin, "LIST", "PRODUCT", product_id)
    return ok(db.public_product(product))


@router.post("/admin/products/{product_id}/off-shelf")
async def off_shelf_product(product_id: int, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    product = _product_or_404(db, product_id)
    product.product_status = "X"
    _audit(db, admin, "OFF_SHELF", "PRODUCT", product_id)
    return ok(db.public_product(product))


@router.post("/admin/products/{product_id}/image", status_code=201)
async def upload_product_image(product_id: int, image: UploadFile = File(...), admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    product = _product_or_404(db, product_id)
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise _error("只支持 JPG、PNG 或 WEBP 图片")
    content = await image.read()
    if len(content) > 5 * 1024 * 1024:
        raise _error("图片不能超过 5MB")
    upload_dir = get_settings().upload_dir
    from pathlib import Path
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    suffix = "." + (image.filename or "upload.jpg").rsplit(".", 1)[-1].lower()
    filename = f"product-{product_id}-{int(now().timestamp())}{suffix}"
    (Path(upload_dir) / filename).write_bytes(content)
    product.main_image_url = f"/uploads/{filename}"
    _audit(db, admin, "UPLOAD_IMAGE", "PRODUCT", product_id)
    return ok({"url": product.main_image_url})


# Cart ---------------------------------------------------------------------


def _cart_items(db: Store, user_id: int) -> list[CartItem]:
    return db.carts.setdefault(user_id, [])


def _cart_view(db: Store, user_id: int) -> dict:
    items = _cart_items(db, user_id)
    result = []
    total = Decimal("0")
    for item in items:
        product = db.products.get(item.product_id)
        if not product:
            continue
        subtotal = product.unit_price * item.quantity
        total += subtotal
        result.append({
            "id": item.cart_item_id,
            "cart_item_id": item.cart_item_id,
            "product_id": product.product_id,
            "product_name": product.product_name,
            "unit_price": str(product.unit_price),
            "stock_qty": product.stock_qty,
            "product": db.public_product(product),
            "quantity": item.quantity,
            "subtotal": str(subtotal),
        })
    return {"items": result, "total_amount": str(total)}


@router.get("/cart")
async def get_cart(user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    return ok(_cart_view(db, user.user_id))


@router.post("/cart/items")
async def add_cart_item(payload: CartItemRequest, user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    product = _product_or_404(db, payload.product_id)
    if product.product_status != "O":
        raise _error("商品未上架")
    items = _cart_items(db, user.user_id)
    existing = next((x for x in items if x.product_id == payload.product_id), None)
    quantity = (existing.quantity if existing else 0) + payload.quantity
    if quantity > product.stock_qty:
        raise _error("库存不足")
    if existing:
        existing.quantity = quantity
        existing.updated_time = now()
    else:
        items.append(CartItem(db._id("cart_item"), payload.product_id, payload.quantity))
    return ok(_cart_view(db, user.user_id))


@router.patch("/cart/items/{item_id}")
async def update_cart_item(item_id: int, payload: CartItemUpdateRequest, user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    item = next((x for x in _cart_items(db, user.user_id) if x.cart_item_id == item_id), None)
    if item is None:
        raise _error("购物车商品不存在", 404)
    product = _product_or_404(db, item.product_id)
    if payload.quantity > product.stock_qty:
        raise _error("库存不足")
    item.quantity = payload.quantity
    item.updated_time = now()
    return ok(_cart_view(db, user.user_id))


@router.delete("/cart/items/{item_id}")
async def delete_cart_item(item_id: int, user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    items = _cart_items(db, user.user_id)
    before = len(items)
    db.carts[user.user_id] = [x for x in items if x.cart_item_id != item_id]
    if len(db.carts[user.user_id]) == before:
        raise _error("购物车商品不存在", 404)
    return ok(_cart_view(db, user.user_id))


@router.delete("/cart/items")
async def clear_cart(user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    db.carts[user.user_id] = []
    return ok(_cart_view(db, user.user_id))


@router.post("/cart/checkout-preview")
async def checkout_preview(payload: CheckoutPreviewRequest, user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    items = [x for x in _cart_items(db, user.user_id) if x.cart_item_id in payload.item_ids]
    if len(items) != len(set(payload.item_ids)):
        raise _error("购物车商品无效")
    total = Decimal("0")
    rows = []
    for item in items:
        product = _product_or_404(db, item.product_id)
        if product.product_status != "O" or item.quantity > product.stock_qty:
            raise _error(f"商品 {product.product_name} 库存不足或已下架")
        subtotal = product.unit_price * item.quantity
        total += subtotal
        rows.append({"cart_item_id": item.cart_item_id, "product": db.public_product(product), "quantity": item.quantity, "subtotal": str(subtotal)})
    return ok({"items": rows, "total_amount": str(total)})


# Orders and payments ------------------------------------------------------


@router.post("/orders", status_code=201)
async def create_order(payload: OrderCreateRequest, user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    async with db.lock:
        cart = _cart_items(db, user.user_id)
        selected = [x for x in cart if x.cart_item_id in payload.item_ids]
        if len(selected) != len(set(payload.item_ids)):
            raise _error("购物车商品无效")
        snapshots: list[OrderItem] = []
        total = Decimal("0")
        earned = 0
        for item in sorted(selected, key=lambda value: value.product_id):
            product = _product_or_404(db, item.product_id)
            if product.product_status != "O" or product.stock_qty < item.quantity:
                raise _error(f"商品 {product.product_name} 库存不足或已下架")
            product.stock_qty -= item.quantity
            subtotal = product.unit_price * item.quantity
            total += subtotal
            earned += product.product_points * item.quantity
            snapshots.append(OrderItem(db._id("order_item"), product.product_id, product.product_name, product.unit_price, item.quantity, product.product_points, subtotal))
        order_id = db._id("order")
        order = Order(order_id, f"M{now().strftime('%Y%m%d%H%M%S')}{order_id:05d}", user.user_id, now(), payload.receiver_name, payload.receiver_phone, payload.receiver_address, payload.payment_method, "U", "W", total, earned, payload.remark, snapshots)
        db.orders[order_id] = order
        db.carts[user.user_id] = [x for x in cart if x.cart_item_id not in payload.item_ids]
        return ok(db.public_order(order), "订单创建成功")


@router.get("/orders")
async def member_orders(status_code: str | None = Query(default=None, alias="status"), page_no: int = Query(default=1, alias="page", ge=1), page_size: int = Query(default=20, ge=1, le=100), user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    records = [x for x in db.orders.values() if x.user_id == user.user_id]
    if status_code:
        records = [x for x in records if x.order_status == status_code]
    records.sort(key=lambda x: x.order_time, reverse=True)
    start = (page_no - 1) * page_size
    return ok(page([db.public_order(x) for x in records[start:start + page_size]], len(records), page_no, page_size))


@router.get("/orders/{order_id}")
async def member_order_detail(order_id: int, user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    order = _order_or_404(db, order_id)
    if order.user_id != user.user_id:
        raise _error("无权访问该订单", 403)
    return ok(db.public_order(order))


@router.patch("/orders/{order_id}")
async def update_order(order_id: int, payload: OrderUpdateRequest, user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    order = _order_or_404(db, order_id)
    if order.user_id != user.user_id:
        raise _error("无权访问该订单", 403)
    if order.order_status != "W":
        raise _error("只有待付款订单可以修改")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, key, value)
    return ok(db.public_order(order))


def _restore_order_stock(db: Store, order: Order) -> None:
    for item in order.items:
        if product := db.products.get(item.product_id):
            product.stock_qty += item.quantity


@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: int, user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    order = _order_or_404(db, order_id)
    if order.user_id != user.user_id:
        raise _error("无权操作该订单", 403)
    if order.order_status not in {"W", "C"}:
        raise _error("当前订单状态不可取消")
    _restore_order_stock(db, order)
    order.order_status = "X"
    order.cancel_reason = "会员取消"
    return ok(db.public_order(order))


@router.post("/orders/{order_id}/pay")
async def pay_order(order_id: int, success: bool = True, user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    order = _order_or_404(db, order_id)
    if order.user_id != user.user_id:
        raise _error("无权操作该订单", 403)
    if order.order_status != "W" or order.payment_status != "U":
        raise _error("订单当前不可支付")
    if success:
        order.payment_status = "P"
        order.order_status = "C"
        payment_status = "S"
    else:
        order.payment_status = "F"
        order.order_status = "X"
        payment_status = "F"
        _restore_order_stock(db, order)
    return ok({"order": db.public_order(order), "payment_status": payment_status}, "支付成功" if success else "支付失败，订单已取消")


@router.post("/orders/{order_id}/refund-apply")
async def refund_apply(order_id: int, payload: RefundApplyRequest, user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    order = _order_or_404(db, order_id)
    if order.user_id != user.user_id:
        raise _error("无权操作该订单", 403)
    if order.order_status != "F":
        raise _error("只有已完成订单可以申请售后")
    order.order_status = "R"
    order.refund_reason = payload.reason
    return ok(db.public_order(order), "售后申请已提交")


@router.get("/admin/orders")
async def admin_orders(page_no: int = Query(default=1, alias="page", ge=1), page_size: int = Query(default=20, ge=1, le=100), _admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    records = sorted(db.orders.values(), key=lambda x: x.order_time, reverse=True)
    start = (page_no - 1) * page_size
    return ok(page([db.public_order(x) for x in records[start:start + page_size]], len(records), page_no, page_size))


@router.post("/admin/orders/{order_id}/confirm")
async def confirm_order(order_id: int, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    order = _order_or_404(db, order_id)
    if order.order_status != "C":
        raise _error("只有待确认订单可以确认")
    order.order_status = "P"
    _audit(db, admin, "CONFIRM", "ORDER", order_id)
    return ok(db.public_order(order))


@router.post("/admin/orders/{order_id}/complete")
async def complete_order(order_id: int, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    order = _order_or_404(db, order_id)
    if order.order_status != "P":
        raise _error("只有已确认订单可以完成")
    order.order_status = "F"
    order.completed_time = now()
    user = db.users[order.user_id]
    key = f"order:{order.order_id}:EARN"
    if not any(x["idempotency_key"] == key for x in db.point_transactions):
        user.total_points += order.earned_points
        db.point_transactions.append({"idempotency_key": key, "user_id": user.user_id, "points": order.earned_points, "type": "EARN", "order_id": order.order_id, "created_time": now()})
        user.level_id = db.level_for_points(user.total_points).level_id
    _audit(db, admin, "COMPLETE", "ORDER", order_id)
    return ok(db.public_order(order))


@router.post("/admin/orders/{order_id}/cancel")
async def admin_cancel_order(order_id: int, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    order = _order_or_404(db, order_id)
    if order.order_status not in {"C", "P"}:
        raise _error("当前订单状态不可取消")
    _restore_order_stock(db, order)
    order.order_status = "X"
    order.cancel_reason = "管理员取消"
    _audit(db, admin, "CANCEL", "ORDER", order_id)
    return ok(db.public_order(order))


@router.post("/admin/orders/{order_id}/refund")
async def admin_refund_order(order_id: int, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    order = _order_or_404(db, order_id)
    if order.order_status != "R":
        raise _error("当前订单不在售后处理中")
    order.order_status = "D"
    order.payment_status = "R"
    order.refund_time = now()
    user = db.users[order.user_id]
    key = f"order:{order.order_id}:REFUND"
    if not any(x["idempotency_key"] == key for x in db.point_transactions):
        user.total_points = max(0, user.total_points - order.earned_points)
        db.point_transactions.append({"idempotency_key": key, "user_id": user.user_id, "points": -order.earned_points, "type": "REFUND", "order_id": order.order_id, "created_time": now()})
        user.level_id = db.level_for_points(user.total_points).level_id
    _audit(db, admin, "REFUND", "ORDER", order_id)
    return ok(db.public_order(order))


# Messages -----------------------------------------------------------------


def _message_view(message: Message, db: Store) -> dict:
    return {
        "id": message.message_id,
        "message_id": message.message_id,
        "user_id": message.user_id,
        "username": db.users[message.user_id].username if message.user_id in db.users else None,
        "title": message.title,
        "content": message.content,
        "message_status": message.message_status,
        "created_time": message.created_time,
        "updated_time": message.updated_time,
        "review_time": message.review_time,
        "replies": message.replies,
    }


@router.get("/messages/public")
async def public_messages(db: Store = Depends(get_store), _user: User = Depends(get_current_member)) -> dict:
    return ok([_message_view(x, db) for x in sorted(db.messages.values(), key=lambda item: item.created_time, reverse=True) if x.message_status == "A"])


@router.get("/member/messages")
async def member_messages(user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    return ok([_message_view(x, db) for x in sorted(db.messages.values(), key=lambda item: item.created_time, reverse=True) if x.user_id == user.user_id and x.message_status != "D"])


@router.post("/member/messages", status_code=201)
async def create_message(payload: MessageCreateRequest, user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    message = Message(db._id("message"), user.user_id, payload.title, payload.content)
    db.messages[message.message_id] = message
    return ok(_message_view(message, db), "留言已提交，等待审核")


@router.patch("/member/messages/{message_id}")
async def update_message(message_id: int, payload: MessageUpdateRequest, user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    message = db.messages.get(message_id)
    if message is None or message.user_id != user.user_id:
        raise _error("留言不存在", 404)
    if message.message_status != "P":
        raise _error("只有待审核留言可以修改")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(message, key, value)
    message.updated_time = now()
    return ok(_message_view(message, db))


@router.delete("/member/messages/{message_id}")
async def delete_message(message_id: int, user: User = Depends(get_current_member), db: Store = Depends(get_store)) -> dict:
    message = db.messages.get(message_id)
    if message is None or message.user_id != user.user_id:
        raise _error("留言不存在", 404)
    if message.message_status != "P":
        raise _error("只有待审核留言可以删除")
    message.message_status = "D"
    return ok(message="留言已删除")


@router.get("/admin/messages")
async def admin_messages(_admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    return ok([_message_view(x, db) for x in sorted(db.messages.values(), key=lambda item: item.created_time, reverse=True)])


@router.post("/admin/messages/{message_id}/approve")
async def approve_message(message_id: int, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    message = db.messages.get(message_id)
    if message is None:
        raise _error("留言不存在", 404)
    message.message_status = "A"
    message.reviewer_admin_id = admin.admin_id
    message.review_time = now()
    _audit(db, admin, "APPROVE", "MESSAGE", message_id)
    return ok(_message_view(message, db))


@router.post("/admin/messages/{message_id}/hide")
async def hide_message(message_id: int, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    message = db.messages.get(message_id)
    if message is None:
        raise _error("留言不存在", 404)
    message.message_status = "H"
    message.reviewer_admin_id = admin.admin_id
    message.review_time = now()
    _audit(db, admin, "HIDE", "MESSAGE", message_id)
    return ok(_message_view(message, db))


@router.post("/admin/messages/{message_id}/reply")
async def reply_message(message_id: int, payload: ReplyRequest, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    message = db.messages.get(message_id)
    if message is None:
        raise _error("留言不存在", 404)
    reply = {"reply_id": db._id("reply"), "admin_id": admin.admin_id, "admin_name": admin.real_name or admin.admin_name, "content": payload.content, "created_time": now()}
    message.replies.append(reply)
    _audit(db, admin, "REPLY", "MESSAGE", message_id)
    return ok(_message_view(message, db))


@router.delete("/admin/messages/{message_id}")
async def admin_delete_message(message_id: int, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    message = db.messages.get(message_id)
    if message is None:
        raise _error("留言不存在", 404)
    message.message_status = "D"
    _audit(db, admin, "DELETE", "MESSAGE", message_id)
    return ok(message="留言已删除")


# Administration -----------------------------------------------------------


@router.get("/admin/users")
async def admin_users(page_no: int = Query(default=1, alias="page", ge=1), page_size: int = Query(default=20, ge=1, le=100), _admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    records = sorted(db.users.values(), key=lambda x: x.user_id, reverse=True)
    start = (page_no - 1) * page_size
    return ok(page([_user_view(db, x) for x in records[start:start + page_size]], len(records), page_no, page_size))


@router.post("/admin/users/{user_id}/reset-password")
async def reset_user_password(user_id: int, payload: ResetPasswordRequest, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    user = db.users.get(user_id)
    if user is None:
        raise _error("会员不存在", 404)
    user.password_hash = hash_password(payload.temporary_password)
    user.must_change_password = True
    _audit(db, admin, "RESET_PASSWORD", "USER", user_id)
    return ok(message="临时密码已设置")


@router.post("/admin/users/{user_id}/enable")
async def enable_user(user_id: int, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    user = db.users.get(user_id)
    if user is None:
        raise _error("会员不存在", 404)
    user.account_status = "A"
    _audit(db, admin, "ENABLE", "USER", user_id)
    return ok(_user_view(db, user))


@router.post("/admin/users/{user_id}/disable")
async def disable_user(user_id: int, admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    user = db.users.get(user_id)
    if user is None:
        raise _error("会员不存在", 404)
    user.account_status = "I"
    _audit(db, admin, "DISABLE", "USER", user_id)
    return ok(_user_view(db, user))


@router.get("/admin/levels")
async def admin_levels(_admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    return ok([vars(x) for x in sorted(db.levels.values(), key=lambda item: item.sort_no)])


@router.patch("/admin/levels/{level_id}")
async def update_level(level_id: int, payload: LevelUpdateRequest, admin: Admin = Depends(require_super_admin), db: Store = Depends(get_store)) -> dict:
    level = db.levels.get(level_id)
    if level is None:
        raise _error("会员等级不存在", 404)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(level, key, value)
    _audit(db, admin, "UPDATE", "LEVEL", level_id)
    return ok(vars(level))


@router.get("/admin/admins")
async def admin_list(admin: Admin = Depends(require_super_admin), db: Store = Depends(get_store)) -> dict:
    return ok([_admin_view(db, x) for x in db.admins.values()])


@router.post("/admin/admins", status_code=201)
async def create_admin(payload: AdminCreateRequest, admin: Admin = Depends(require_super_admin), db: Store = Depends(get_store)) -> dict:
    if any(x.admin_name.lower() == payload.admin_name.lower() for x in db.admins.values()):
        raise _error("管理员账号已存在", 409)
    new_admin = Admin(db._id("admin"), payload.admin_name, hash_password(payload.password), payload.real_name, [payload.role_code])
    db.admins[new_admin.admin_id] = new_admin
    _audit(db, admin, "CREATE", "ADMIN", new_admin.admin_id)
    return ok(_admin_view(db, new_admin))


@router.patch("/admin/admins/{admin_id}/status")
async def set_admin_status(admin_id: int, payload: AdminStatusRequest, admin: Admin = Depends(require_super_admin), db: Store = Depends(get_store)) -> dict:
    target = db.admins.get(admin_id)
    if target is None:
        raise _error("管理员不存在", 404)
    target.status = payload.status
    _audit(db, admin, "STATUS", "ADMIN", admin_id)
    return ok(_admin_view(db, target))


@router.get("/admin/audit-logs")
async def audit_logs(_admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    return ok(list(reversed(db.audit_logs)))


@router.get("/admin/statistics")
async def statistics(_admin: Admin = Depends(get_current_admin), db: Store = Depends(get_store)) -> dict:
    return ok({
        "member_count": len(db.users),
        "product_count": len(db.products),
        "listed_product_count": sum(x.product_status == "O" for x in db.products.values()),
        "order_count": len(db.orders),
        "message_count": len(db.messages),
        "paid_amount": str(sum((x.total_amount for x in db.orders.values() if x.payment_status == "P"), Decimal("0"))),
    })

