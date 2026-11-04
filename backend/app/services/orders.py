"""订单业务规则：状态机、库存事务、模拟支付、售后与积分结算。

下单/支付/取消/退款等状态流转全部在数据库事务中完成；库存扣减使用
带条件的原子 UPDATE（stock_qty >= 数量且上架状态），杜绝负库存与
超卖；积分结算幂等键防重复。前置状态校验失败即回滚。
"""
from __future__ import annotations

import secrets
from datetime import time, date, datetime, timezone
from decimal import Decimal
from typing import Any

from prisma import Prisma
from prisma.models import Order, OrderItem, Product

from ..core.errors import bad_request, forbidden, not_found
from ..repositories.prisma import utcnow
from . import points

ORDER_INCLUDE = {"items": True, "payments": True}

CONTACT_FIELD_MAP = {
    "receiver_name": "receiverName",
    "receiver_phone": "receiverPhone",
    "receiver_address": "receiverAddress",
    "remark": "remark",
}


async def fetch_order(client: Prisma, order_id: int) -> Order:
    order = await client.order.find_unique(
        where={"orderId": order_id}, include=ORDER_INCLUDE
    )
    if order is None:
        raise not_found("订单不存在")
    return order


def order_where(
    *,
    user_id: int | None = None,
    keyword: str | None = None,
    status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """构造订单查询条件：订单号关键字、状态和下单日期区间。"""
    where: dict[str, Any] = {}
    if user_id is not None:
        where["userId"] = user_id
    if status:
        where["orderStatus"] = status
    if keyword:
        where["orderNo"] = {"contains": keyword}
    time_filter: dict[str, datetime] = {}
    if start_date:
        time_filter["gte"] = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    if end_date:
        time_filter["lte"] = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
    if time_filter:
        where["orderTime"] = time_filter
    return where


async def _restore_stock(client: Prisma, items: list[OrderItem]) -> None:
    for item in items:
        await client.product.update_many(
            where={"productId": item.productId},
            data={"stockQty": {"increment": item.quantity}},
        )


async def create_order(
    client: Prisma,
    *,
    user_id: int,
    item_ids: list[int],
    receiver_name: str,
    receiver_phone: str,
    receiver_address: str,
    payment_method: str,
    remark: str | None,
) -> Order:
    """购物车批量结算：事务内校验并锁定库存、写订单与明细快照。"""
    async with client.tx() as tx:
        cart = await tx.cart.find_first(where={"userId": user_id})
        if cart is None:
            raise bad_request("购物车为空")
        requested = list(dict.fromkeys(item_ids))
        rows = await tx.cartitem.find_many(
            where={"cartId": cart.cartId, "cartItemId": {"in": requested}},
            include={"product": True},
        )
        if len(rows) != len(requested):
            raise bad_request("购物车商品无效")

        snapshots: list[dict[str, Any]] = []
        total = Decimal("0")
        earned = 0
        for item in sorted(rows, key=lambda value: value.productId):
            product: Product | None = item.product
            name = product.productName if product else "未知商品"
            if product is None or product.productStatus != "O":
                raise bad_request(f"商品 {name} 已下架或不存在")
            if product.stockQty < item.quantity:
                raise bad_request(f"商品 {product.productName} 库存不足")
            locked = await tx.product.update_many(
                where={
                    "productId": product.productId,
                    "productStatus": "O",
                    "stockQty": {"gte": item.quantity},
                },
                data={"stockQty": {"decrement": item.quantity}},
            )
            if locked != 1:
                raise bad_request(f"商品 {product.productName} 库存不足，请刷新购物车")
            subtotal = (product.unitPrice * item.quantity).quantize(Decimal("0.01"))
            total += subtotal
            earned += product.productPoints * item.quantity
            snapshots.append(
                {
                    "productId": product.productId,
                    "productNameSnapshot": product.productName,
                    "unitPrice": product.unitPrice,
                    "quantity": item.quantity,
                    "itemPoints": product.productPoints,
                    "subtotal": subtotal,
                }
            )

        order = await tx.order.create(
            data={
                "orderNo": f"M{utcnow().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(3).upper()}",
                "userId": user_id,
                "receiverName": receiver_name,
                "receiverPhone": receiver_phone,
                "receiverAddress": receiver_address,
                "paymentMethod": payment_method,
                "paymentStatus": "U",
                "orderStatus": "W",
                "totalAmount": total,
                "earnedPoints": earned,
                "remark": remark,
            }
        )
        for payload in snapshots:
            await tx.orderitem.create(data={"orderId": order.orderId, **payload})
        await tx.cartitem.delete_many(
            where={"cartId": cart.cartId, "cartItemId": {"in": requested}}
        )
        await tx.cart.update(
            where={"cartId": cart.cartId}, data={"updatedTime": utcnow()}
        )
        return await fetch_order(tx, order.orderId)


async def update_unpaid_order(
    client: Prisma,
    *,
    order_id: int,
    user_id: int,
    contact: dict[str, Any],
    item_quantities: dict[int, int],
) -> Order:
    """未付款订单修改：联系信息快照与商品数量（重新校验库存）。"""
    async with client.tx() as tx:
        order = await tx.order.find_unique_or_raise(
            where={"orderId": order_id}, include={"items": True}
        )
        if order.userId != user_id:
            raise forbidden("无权操作该订单")
        if order.orderStatus != "W" or order.paymentStatus != "U":
            raise bad_request("只有待付款订单可以修改")

        data: dict[str, Any] = {
            CONTACT_FIELD_MAP[key]: value
            for key, value in contact.items()
            if key in CONTACT_FIELD_MAP and value is not None
        }
        data["updatedTime"] = utcnow()
        if item_quantities:
            existing = {item.productId: item for item in order.items}
            for product_id, quantity in item_quantities.items():
                item = existing.get(product_id)
                if item is None:
                    raise bad_request("订单明细中不存在该商品")
                delta = quantity - item.quantity
                if delta == 0:
                    continue
                product = await tx.product.find_unique_or_raise(
                    where={"productId": product_id}
                )
                if product.productStatus != "O":
                    raise bad_request(f"商品 {product.productName} 已下架，无法调整数量")
                if delta > 0:
                    locked = await tx.product.update_many(
                        where={
                            "productId": product_id,
                            "productStatus": "O",
                            "stockQty": {"gte": delta},
                        },
                        data={"stockQty": {"decrement": delta}},
                    )
                    if locked != 1:
                        raise bad_request(f"商品 {product.productName} 库存不足")
                else:
                    await tx.product.update_many(
                        where={"productId": product_id},
                        data={"stockQty": {"increment": -delta}},
                    )
                await tx.orderitem.update(
                    where={"orderItemId": item.orderItemId},
                    data={
                        "quantity": quantity,
                        "subtotal": (product.unitPrice * quantity).quantize(
                            Decimal("0.01")
                        ),
                    },
                )
            rows = await tx.orderitem.find_many(where={"orderId": order_id})
            data["totalAmount"] = sum(
                (row.subtotal for row in rows), Decimal("0")
            )
            data["earnedPoints"] = sum(row.itemPoints * row.quantity for row in rows)
        await tx.order.update(where={"orderId": order_id}, data=data)
        return await fetch_order(tx, order_id)


async def member_cancel_order(
    client: Prisma, *, order_id: int, user_id: int, reason: str = "会员取消"
) -> Order:
    async with client.tx() as tx:
        order = await tx.order.find_unique_or_raise(
            where={"orderId": order_id}, include={"items": True}
        )
        if order.userId != user_id:
            raise forbidden("无权操作该订单")
        if order.orderStatus not in {"W", "C"}:
            raise bad_request("当前订单状态不可取消")
        await _cancel(tx, order, reason)
        return await fetch_order(tx, order_id)


async def admin_cancel_order(client: Prisma, *, order_id: int) -> Order:
    async with client.tx() as tx:
        order = await tx.order.find_unique_or_raise(
            where={"orderId": order_id}, include={"items": True}
        )
        if order.orderStatus not in {"C", "P"}:
            raise bad_request("当前订单状态不可取消")
        await _cancel(tx, order, "管理员取消")
        return await fetch_order(tx, order_id)


async def _cancel(client: Prisma, order: Order, reason: str) -> None:
    await _restore_stock(client, order.items)
    data: dict[str, Any] = {
        "orderStatus": "X",
        "cancelReason": reason,
        "updatedTime": utcnow(),
    }
    if order.paymentStatus == "P":
        data["paymentStatus"] = "R"
        data["refundTime"] = utcnow()
    await client.order.update(where={"orderId": order.orderId}, data=data)
    await client.paymentrecord.update_many(
        where={"orderId": order.orderId, "paymentStatus": "S"},
        data={"paymentStatus": "R"},
    )


async def pay_order(
    client: Prisma, *, order_id: int, user_id: int, success: bool
) -> tuple[Order, str]:
    """模拟支付：成功转待确认，失败/取消恢复库存；均写入支付流水。"""
    async with client.tx() as tx:
        order = await tx.order.find_unique_or_raise(
            where={"orderId": order_id}, include={"items": True}
        )
        if order.userId != user_id:
            raise forbidden("无权操作该订单")
        if order.orderStatus != "W" or order.paymentStatus != "U":
            raise bad_request("订单当前不可支付")
        payment_no = f"PAY{utcnow().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(3).upper()}"
        record_data: dict[str, Any] = {
            "orderId": order.orderId,
            "paymentNo": payment_no,
            "paymentMethod": order.paymentMethod,
            "paymentAmount": order.totalAmount,
        }
        if success:
            await tx.paymentrecord.create(
                data={
                    **record_data,
                    "paymentStatus": "S",
                    "paidTime": utcnow(),
                    "transactionReference": f"MOCK{payment_no}",
                }
            )
            await tx.order.update(
                where={"orderId": order.orderId},
                data={"paymentStatus": "P", "orderStatus": "C", "updatedTime": utcnow()},
            )
            payment_status = "S"
        else:
            await _restore_stock(tx, order.items)
            await tx.paymentrecord.create(data={**record_data, "paymentStatus": "F"})
            await tx.order.update(
                where={"orderId": order.orderId},
                data={
                    "paymentStatus": "F",
                    "orderStatus": "X",
                    "cancelReason": "模拟支付失败",
                    "updatedTime": utcnow(),
                },
            )
            payment_status = "F"
        return await fetch_order(tx, order.orderId), payment_status


async def apply_refund(
    client: Prisma, *, order_id: int, user_id: int, reason: str
) -> Order:
    async with client.tx() as tx:
        order = await tx.order.find_unique_or_raise(where={"orderId": order_id})
        if order.userId != user_id:
            raise forbidden("无权操作该订单")
        if order.orderStatus != "F":
            raise bad_request("只有已完成订单可以申请售后")
        await tx.order.update(
            where={"orderId": order_id},
            data={"orderStatus": "R", "refundReason": reason, "updatedTime": utcnow()},
        )
        return await fetch_order(tx, order_id)


async def admin_confirm_order(client: Prisma, order_id: int) -> Order:
    async with client.tx() as tx:
        order = await tx.order.find_unique_or_raise(where={"orderId": order_id})
        if order.orderStatus != "C":
            raise bad_request("只有待确认订单可以确认")
        await tx.order.update(
            where={"orderId": order_id}, data={"orderStatus": "P", "updatedTime": utcnow()}
        )
        return await fetch_order(tx, order_id)


async def admin_complete_order(client: Prisma, order_id: int) -> Order:
    async with client.tx() as tx:
        order = await tx.order.find_unique_or_raise(where={"orderId": order_id})
        if order.orderStatus != "P":
            raise bad_request("只有已确认订单可以完成")
        await tx.order.update(
            where={"orderId": order_id},
            data={"orderStatus": "F", "completedTime": utcnow(), "updatedTime": utcnow()},
        )
        settled = await fetch_order(tx, order_id)
        await points.settle_earned(tx, settled)
        return await fetch_order(tx, order_id)


async def admin_refund_order(client: Prisma, order_id: int) -> Order:
    async with client.tx() as tx:
        order = await tx.order.find_unique_or_raise(where={"orderId": order_id})
        if order.orderStatus != "R":
            raise bad_request("当前订单不在售后处理中")
        await tx.paymentrecord.update_many(
            where={"orderId": order_id, "paymentStatus": "S"},
            data={"paymentStatus": "R"},
        )
        await tx.order.update(
            where={"orderId": order_id},
            data={
                "orderStatus": "D",
                "paymentStatus": "R",
                "refundTime": utcnow(),
                "updatedTime": utcnow(),
            },
        )
        settled = await fetch_order(tx, order_id)
        await points.settle_refund(tx, settled)
        return await fetch_order(tx, order_id)
