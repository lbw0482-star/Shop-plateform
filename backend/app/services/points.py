"""积分与会员等级：结算、回退和按积分区间刷新等级。

所有结算通过 point_transaction.idempotency_key 幂等键防重复处理；
等级区间由 member_level 表维护，可被超级管理员调整。
"""
from __future__ import annotations

from prisma import Prisma
from prisma.models import Order


async def active_levels(client: Prisma):
    return await client.memberlevel.find_many(
        where={"status": "A"}, order=[{"minPoints": "asc"}]
    )


async def level_id_for_points(client: Prisma, points: int) -> int:
    """按积分区间返回所属等级；区间可重叠时取满足条件的高档等级。"""
    levels = await active_levels(client)
    if not levels:
        raise RuntimeError("会员等级未初始化，请先运行种子脚本")
    chosen = levels[0]
    for level in levels:
        if points >= level.minPoints and (
            level.maxPoints is None or points <= level.maxPoints
        ):
            chosen = level
    return chosen.levelId


async def default_level_id(client: Prisma) -> int:
    return await level_id_for_points(client, 0)


async def settle_earned(client: Prisma, order: Order) -> bool:
    """订单完成时按明细快照结算积分；幂等键重复时跳过。"""
    key = f"order:{order.orderId}:EARN"
    if await client.pointtransaction.find_first(where={"idempotencyKey": key}):
        return False
    user = await client.sysuser.find_unique_or_raise(where={"userId": order.userId})
    total = max(0, user.totalPoints + order.earnedPoints)
    await client.pointtransaction.create(
        data={
            "userId": user.userId,
            "orderId": order.orderId,
            "points": order.earnedPoints,
            "transactionType": "EARN",
            "idempotencyKey": key,
        }
    )
    await client.sysuser.update(
        where={"userId": user.userId},
        data={
            "totalPoints": total,
            "levelId": await level_id_for_points(client, total),
        },
    )
    return True


async def settle_refund(client: Prisma, order: Order) -> bool:
    """订单退款时回退本单积分并刷新等级；幂等键重复时跳过。"""
    key = f"order:{order.orderId}:REFUND"
    if await client.pointtransaction.find_first(where={"idempotencyKey": key}):
        return False
    user = await client.sysuser.find_unique_or_raise(where={"userId": order.userId})
    total = max(0, user.totalPoints - order.earnedPoints)
    await client.pointtransaction.create(
        data={
            "userId": user.userId,
            "orderId": order.orderId,
            "points": -order.earnedPoints,
            "transactionType": "REFUND",
            "idempotencyKey": key,
        }
    )
    await client.sysuser.update(
        where={"userId": user.userId},
        data={
            "totalPoints": total,
            "levelId": await level_id_for_points(client, total),
        },
    )
    return True
