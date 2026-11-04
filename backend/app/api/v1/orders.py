"""订单与模拟支付接口：会员端和后台处理。"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from prisma import Prisma

from ...core.deps import ensure_password_changed, get_current_admin, get_current_member
from ...core.errors import forbidden, not_found
from ...core.response import ok, page
from ...repositories.prisma import get_client
from ...schemas import (
    OrderCreateRequest,
    OrderUpdateRequest,
    RefundApplyRequest,
)
from ...services import audit, orders as order_service
from .serializers import public_order

router = APIRouter()

ORDER_LIST_INCLUDE = {"items": True, "user": True, "payments": True}


def _pagination(page_no: int, page_size: int) -> dict[str, int]:
    return {"skip": (page_no - 1) * page_size, "take": page_size}


async def _member_order(client: Prisma, order_id: int, user_id: int):
    order = await client.order.find_unique(
        where={"orderId": order_id}, include=ORDER_LIST_INCLUDE
    )
    if order is None:
        raise not_found("订单不存在")
    if order.userId != user_id:
        raise forbidden("无权访问该订单")
    return order


@router.post("/orders", status_code=201)
async def create_order(
    payload: OrderCreateRequest,
    client: Prisma = Depends(get_client),
    user=Depends(ensure_password_changed),
) -> dict:
    order = await order_service.create_order(
        client,
        user_id=user.userId,
        item_ids=payload.item_ids,
        receiver_name=payload.receiver_name,
        receiver_phone=payload.receiver_phone,
        receiver_address=payload.receiver_address,
        payment_method=payload.payment_method,
        remark=payload.remark,
    )
    return ok(public_order(order), "订单创建成功")


@router.get("/orders")
async def member_orders(
    keyword: str | None = None,
    status_code: str | None = Query(default=None, alias="status"),
    start_date: date | None = Query(default=None, alias="start_date"),
    end_date: date | None = Query(default=None, alias="end_date"),
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    client: Prisma = Depends(get_client),
    user=Depends(get_current_member),
) -> dict:
    where = order_service.order_where(
        user_id=user.userId,
        keyword=keyword,
        status=status_code,
        start_date=start_date,
        end_date=end_date,
    )
    total = await client.order.count(where=where)
    rows = await client.order.find_many(
        where=where, include=ORDER_LIST_INCLUDE, order=[{"orderTime": "desc"}],
        **_pagination(page_no, page_size),
    )
    return ok(page([public_order(row) for row in rows], total, page_no, page_size))


@router.get("/orders/{order_id}")
async def member_order_detail(
    order_id: int,
    client: Prisma = Depends(get_client),
    user=Depends(get_current_member),
) -> dict:
    order = await _member_order(client, order_id, user.userId)
    return ok(public_order(order))


@router.patch("/orders/{order_id}")
async def update_order(
    order_id: int,
    payload: OrderUpdateRequest,
    client: Prisma = Depends(get_client),
    user=Depends(ensure_password_changed),
) -> dict:
    contact = payload.model_dump(exclude_unset=True, exclude={"items"})
    quantities: dict[int, int] = {}
    if payload.items:
        quantities = {item.product_id: item.quantity for item in payload.items}
    order = await order_service.update_unpaid_order(
        client,
        order_id=order_id,
        user_id=user.userId,
        contact=contact,
        item_quantities=quantities,
    )
    return ok(public_order(order), "订单已更新")


@router.post("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    client: Prisma = Depends(get_client),
    user=Depends(get_current_member),
) -> dict:
    order = await order_service.member_cancel_order(
        client, order_id=order_id, user_id=user.userId
    )
    return ok(public_order(order), "订单已取消")


@router.post("/orders/{order_id}/pay")
async def pay_order(
    order_id: int,
    success: bool = Query(default=True),
    client: Prisma = Depends(get_client),
    user=Depends(ensure_password_changed),
) -> dict:
    order, payment_status = await order_service.pay_order(
        client, order_id=order_id, user_id=user.userId, success=success
    )
    message = "支付成功" if success else "支付失败，订单已取消"
    return ok({"order": public_order(order), "payment_status": payment_status}, message)


@router.post("/orders/{order_id}/refund-apply")
async def refund_apply(
    order_id: int,
    payload: RefundApplyRequest,
    client: Prisma = Depends(get_client),
    user=Depends(get_current_member),
) -> dict:
    order = await order_service.apply_refund(
        client, order_id=order_id, user_id=user.userId, reason=payload.reason
    )
    return ok(public_order(order), "售后申请已提交")


@router.get("/admin/orders")
async def admin_orders(
    keyword: str | None = None,
    status_code: str | None = Query(default=None, alias="status"),
    start_date: date | None = Query(default=None, alias="start_date"),
    end_date: date | None = Query(default=None, alias="end_date"),
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    client: Prisma = Depends(get_client),
    _admin=Depends(get_current_admin),
) -> dict:
    where = order_service.order_where(
        keyword=keyword,
        status=status_code,
        start_date=start_date,
        end_date=end_date,
    )
    total = await client.order.count(where=where)
    rows = await client.order.find_many(
        where=where, include=ORDER_LIST_INCLUDE, order=[{"orderTime": "desc"}],
        **_pagination(page_no, page_size),
    )
    return ok(page([public_order(row) for row in rows], total, page_no, page_size))


@router.get("/admin/orders/{order_id}")
async def admin_order_detail(
    order_id: int,
    client: Prisma = Depends(get_client),
    _admin=Depends(get_current_admin),
) -> dict:
    order = await client.order.find_unique(
        where={"orderId": order_id}, include=ORDER_LIST_INCLUDE
    )
    if order is None:
        raise not_found("订单不存在")
    return ok(public_order(order))


@router.post("/admin/orders/{order_id}/confirm")
async def confirm_order(
    order_id: int,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    order = await order_service.admin_confirm_order(client, order_id)
    await audit.write(client, admin, "CONFIRM", "ORDER", order_id)
    return ok(public_order(order), "订单已确认")


@router.post("/admin/orders/{order_id}/complete")
async def complete_order(
    order_id: int,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    order = await order_service.admin_complete_order(client, order_id)
    await audit.write(client, admin, "COMPLETE", "ORDER", order_id)
    return ok(public_order(order), "订单已完成并结算积分")


@router.post("/admin/orders/{order_id}/cancel")
async def admin_cancel_order(
    order_id: int,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    order = await order_service.admin_cancel_order(client, order_id=order_id)
    await audit.write(client, admin, "CANCEL", "ORDER", order_id)
    return ok(public_order(order), "订单已取消并恢复库存")


@router.post("/admin/orders/{order_id}/refund")
async def admin_refund_order(
    order_id: int,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    order = await order_service.admin_refund_order(client, order_id)
    await audit.write(client, admin, "REFUND", "ORDER", order_id)
    return ok(public_order(order), "退款完成，积分已回退")
