"""后台管理接口：会员、等级、管理员、角色、审计日志和统计。

按 SRS 权限边界：会员资料/积分调整与商品、订单、留言为普通管理员可操作；
等级规则、管理员账号、角色与操作日志仅超级管理员可维护。
"""
from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, Query
from prisma import Prisma, errors as prisma_errors
from prisma.models import SysAdmin, SysUser

from ...core.deps import (
    admin_role_codes,
    get_current_admin,
    require_super_admin,
)
from ...core.errors import bad_request, conflict, not_found
from ...core.response import ok, page
from ...core.security import hash_password
from ...repositories.prisma import get_client, utcnow
from ...schemas import (
    AdjustPointsRequest,
    AdminCreateRequest,
    AdminStatusRequest,
    AdminUpdateRequest,
    AdminUserUpdateRequest,
    LevelUpdateRequest,
    ResetPasswordRequest,
)
from ...services import audit, points
from .serializers import public_admin, public_user

router = APIRouter()

USER_ORDER_INCLUDE = {"level": True}
ADMIN_ROLES_INCLUDE = {"roles": {"include": {"role": True}}}

# 等级请求模型为 snake_case，Prisma 模型字段为 camelCase（同名键无需转换）
LEVEL_FIELD_MAP = {
    "level_name": "levelName",
    "min_points": "minPoints",
    "max_points": "maxPoints",
}


def _pagination(page_no: int, page_size: int) -> dict[str, int]:
    return {"skip": (page_no - 1) * page_size, "take": page_size}


async def _user_or_404(client: Prisma, user_id: int) -> SysUser:
    user = await client.sysuser.find_unique(
        where={"userId": user_id}, include=USER_ORDER_INCLUDE
    )
    if user is None:
        raise not_found("会员不存在")
    return user


async def _admin_or_404(client: Prisma, admin_id: int) -> SysAdmin:
    admin = await client.sysadmin.find_unique(
        where={"adminId": admin_id}, include=ADMIN_ROLES_INCLUDE
    )
    if admin is None:
        raise not_found("管理员不存在")
    return admin


# ---------------------------------------------------------------- members --


@router.get("/admin/users")
async def admin_users(
    keyword: str | None = None,
    account_status: str | None = Query(default=None, alias="status"),
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    client: Prisma = Depends(get_client),
    _admin=Depends(get_current_admin),
) -> dict:
    where: dict[str, Any] = {}
    if account_status:
        where["accountStatus"] = account_status
    if keyword:
        where["OR"] = [
            {"username": {"contains": keyword}},
            {"email": {"contains": keyword}},
            {"phone": {"contains": keyword}},
        ]
    total = await client.sysuser.count(where=where)
    rows = await client.sysuser.find_many(
        where=where, include=USER_ORDER_INCLUDE, order=[{"userId": "desc"}],
        **_pagination(page_no, page_size),
    )
    return ok(page([public_user(row) for row in rows], total, page_no, page_size))


@router.get("/admin/users/{user_id}")
async def admin_user_detail(
    user_id: int, client: Prisma = Depends(get_client), _admin=Depends(get_current_admin)
) -> dict:
    user = await _user_or_404(client, user_id)
    order_count = await client.order.count(where={"userId": user_id})
    data = public_user(user)
    data["order_count"] = order_count
    return ok(data)


@router.patch("/admin/users/{user_id}")
async def admin_update_user(
    user_id: int,
    payload: AdminUserUpdateRequest,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    await _user_or_404(client, user_id)
    fields = payload.model_dump(exclude_unset=True)
    if "account_status" in fields and fields["account_status"] == "I":
        await sessions_destroy_for_user(client, user_id)
    await client.sysuser.update(where={"userId": user_id}, data=fields)
    await audit.write(client, admin, "UPDATE", "USER", user_id)
    return ok(public_user(await _user_or_404(client, user_id)), "会员资料已更新")


async def sessions_destroy_for_user(client: Prisma, user_id: int) -> None:
    """禁用会员时撤销其未过期会话。"""
    await client.authsession.delete_many(where={"userId": user_id})


@router.post("/admin/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    payload: ResetPasswordRequest,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    await _user_or_404(client, user_id)
    await client.sysuser.update(
        where={"userId": user_id},
        data={
            "passwordHash": hash_password(payload.temporary_password),
            "mustChangePassword": True,
        },
    )
    await sessions_destroy_for_user(client, user_id)
    await audit.write(client, admin, "RESET_PASSWORD", "USER", user_id)
    return ok(message="临时密码已设置，会员下次登录必须修改")


@router.post("/admin/users/{user_id}/enable")
async def enable_user(
    user_id: int,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    await _user_or_404(client, user_id)
    await client.sysuser.update(
        where={"userId": user_id}, data={"accountStatus": "A"}
    )
    await audit.write(client, admin, "ENABLE", "USER", user_id)
    return ok(public_user(await _user_or_404(client, user_id)), "会员已启用")


@router.post("/admin/users/{user_id}/disable")
async def disable_user(
    user_id: int,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    await _user_or_404(client, user_id)
    await client.sysuser.update(
        where={"userId": user_id}, data={"accountStatus": "I"}
    )
    await sessions_destroy_for_user(client, user_id)
    await audit.write(client, admin, "DISABLE", "USER", user_id)
    return ok(public_user(await _user_or_404(client, user_id)), "会员已禁用")


@router.post("/admin/users/{user_id}/adjust-points")
async def adjust_points(
    user_id: int,
    payload: AdjustPointsRequest,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    if payload.points == 0:
        raise bad_request("积分调整值不能为 0")
    user = await _user_or_404(client, user_id)
    total = max(0, user.totalPoints + payload.points)
    async with client.tx() as tx:
        key = f"manual:{admin.adminId}:{utcnow().isoformat()}:{secrets.token_hex(4)}"
        await tx.pointtransaction.create(
            data={
                "userId": user_id,
                "points": payload.points,
                "transactionType": "ADJUST",
                "idempotencyKey": key,
                "createdAt": utcnow(),
            }
        )
        await tx.sysuser.update(
            where={"userId": user_id},
            data={"totalPoints": total, "levelId": await points.level_id_for_points(tx, total)},
        )
    await audit.write(
        client, admin, "ADJUST_POINTS", "USER", user_id,
        detail=f"{payload.points:+d} 分：{payload.reason}",
    )
    return ok(public_user(await _user_or_404(client, user_id)), "积分已调整")


# ----------------------------------------------------------------- levels --


@router.get("/admin/levels")
async def admin_levels(
    client: Prisma = Depends(get_client), _admin=Depends(get_current_admin)
) -> dict:
    rows = await client.memberlevel.find_many(order=[{"sortNo": "asc"}])
    return ok(
        [
            {
                "id": row.levelId,
                "level_id": row.levelId,
                "level_name": row.levelName,
                "min_points": row.minPoints,
                "max_points": row.maxPoints,
                "sort_no": row.sortNo,
                "status": row.status,
            }
            for row in rows
        ]
    )


@router.patch("/admin/levels/{level_id}")
async def update_level(
    level_id: int,
    payload: LevelUpdateRequest,
    admin=Depends(require_super_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    level = await client.memberlevel.find_unique(where={"levelId": level_id})
    if level is None:
        raise not_found("会员等级不存在")
    fields = payload.model_dump(exclude_unset=True)
    max_points = fields.get("max_points", level.maxPoints)
    min_points = fields.get("min_points", level.minPoints)
    if max_points is not None and min_points > max_points:
        raise bad_request("积分下限不能大于上限")
    data = {LEVEL_FIELD_MAP.get(key, key): value for key, value in fields.items()}
    await client.memberlevel.update(where={"levelId": level_id}, data=data)
    await audit.write(client, admin, "UPDATE", "LEVEL", level_id)
    return ok(
        {
            "id": level_id,
            "level_id": level_id,
            **fields,
            "min_points": min_points,
            "max_points": max_points,
        },
        "等级规则已更新",
    )


# ----------------------------------------------------------------- admins --


@router.get("/admin/admins")
async def admin_list(
    client: Prisma = Depends(get_client),
    _admin=Depends(require_super_admin),
) -> dict:
    rows = await client.sysadmin.find_many(include=ADMIN_ROLES_INCLUDE)
    return ok([public_admin(row) for row in rows])


@router.post("/admin/admins", status_code=201)
async def create_admin(
    payload: AdminCreateRequest,
    admin=Depends(require_super_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    exists = await client.sysadmin.find_first(
        where={"adminName": {"equals": payload.admin_name, "mode": "insensitive"}}
    )
    if exists:
        raise conflict("管理员账号已存在")
    role = await client.sysrole.find_first(where={"roleCode": payload.role_code})
    if role is None:
        raise not_found("角色不存在，请先初始化角色数据")
    try:
        created = await client.sysadmin.create(
            data={
                "adminName": payload.admin_name,
                "passwordHash": hash_password(payload.password),
                "realName": payload.real_name,
                "roles": {"create": {"roleId": role.roleId}},
            }
        )
    except prisma_errors.UniqueViolationError:
        raise conflict("管理员账号已存在") from None
    await audit.write(client, admin, "CREATE", "ADMIN", created.adminId)
    return ok(public_admin(await _admin_or_404(client, created.adminId)))


@router.patch("/admin/admins/{admin_id}")
async def update_admin(
    admin_id: int,
    payload: AdminUpdateRequest,
    admin=Depends(require_super_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    target = await _admin_or_404(client, admin_id)
    fields = payload.model_dump(exclude_unset=True)
    data: dict[str, Any] = {}
    for key in ("real_name", "email", "phone"):
        if key in fields:
            data[{"real_name": "realName", "email": "email", "phone": "phone"}[key]] = fields[key]
    if fields.get("password"):
        data["passwordHash"] = hash_password(fields["password"])
    if data:
        await client.sysadmin.update(where={"adminId": admin_id}, data=data)
    if fields.get("role_code"):
        role = await client.sysrole.find_first(where={"roleCode": fields["role_code"]})
        if role is None:
            raise not_found("角色不存在")
        await client.sysadminrole.delete_many(where={"adminId": admin_id})
        await client.sysadminrole.create(
            data={"adminId": admin_id, "roleId": role.roleId}
        )
    await audit.write(client, admin, "UPDATE", "ADMIN", admin_id)
    return ok(public_admin(await _admin_or_404(client, admin_id)), "管理员已更新")


@router.patch("/admin/admins/{admin_id}/status")
async def set_admin_status(
    admin_id: int,
    payload: AdminStatusRequest,
    admin=Depends(require_super_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    target = await _admin_or_404(client, admin_id)
    if target.adminId == admin.adminId and payload.status == "I":
        raise bad_request("不能禁用当前登录的管理员账号")
    await client.sysadmin.update(
        where={"adminId": admin_id}, data={"status": payload.status}
    )
    if payload.status == "I":
        await client.authsession.delete_many(where={"adminId": admin_id})
    await audit.write(client, admin, "STATUS", "ADMIN", admin_id)
    return ok(public_admin(await _admin_or_404(client, admin_id)), "状态已更新")


@router.get("/admin/roles")
async def role_list(
    client: Prisma = Depends(get_client), _admin=Depends(require_super_admin)
) -> dict:
    rows = await client.sysrole.find_many(order=[{"roleId": "asc"}])
    return ok(
        [
            {
                "id": row.roleId,
                "role_id": row.roleId,
                "role_code": row.roleCode,
                "role_name": row.roleName,
                "description": row.description,
                "status": row.status,
            }
            for row in rows
        ]
    )


# ------------------------------------------------------------ logs & stats --


@router.get("/admin/audit-logs")
async def audit_logs(
    operation_type: str | None = None,
    target_type: str | None = None,
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    client: Prisma = Depends(get_client),
    _admin=Depends(require_super_admin),
) -> dict:
    where: dict[str, Any] = {}
    if operation_type:
        where["operationType"] = operation_type
    if target_type:
        where["targetType"] = target_type
    total = await client.auditlog.count(where=where)
    rows = await client.auditlog.find_many(
        where=where, include={"admin": True}, order=[{"logId": "desc"}],
        **_pagination(page_no, page_size),
    )
    return ok(
        page(
            [
                {
                    "log_id": row.logId,
                    "admin_id": row.adminId,
                    "admin_name": row.admin.adminName if row.admin else None,
                    "operation_type": row.operationType,
                    "target_type": row.targetType,
                    "target_id": row.targetId,
                    "operation_detail": row.operationDetail,
                    "operation_time": row.operationTime,
                }
                for row in rows
            ],
            total,
            page_no,
            page_size,
        )
    )


@router.get("/admin/statistics")
async def statistics(
    client: Prisma = Depends(get_client), _admin=Depends(get_current_admin)
) -> dict:
    from decimal import Decimal

    paid_rows = await client.paymentrecord.find_many(where={"paymentStatus": "S"})
    paid_amount = sum((row.paymentAmount for row in paid_rows), Decimal("0"))
    return ok(
        {
            "member_count": await client.sysuser.count(),
            "product_count": await client.product.count(),
            "listed_product_count": await client.product.count(where={"productStatus": "O"}),
            "order_count": await client.order.count(),
            "message_count": await client.membermessage.count(where={"messageStatus": {"not": "D"}}),
            "paid_amount": str(paid_amount),
        }
    )
