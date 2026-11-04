"""认证、登录态与会员资料接口。"""
from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Response, status
from prisma import Prisma, errors as prisma_errors

from ...core.config import get_settings
from ...core.deps import get_current_member
from ...core.errors import conflict, unauthorized
from ...core.response import ok
from ...core.security import hash_password, verify_password
from ...repositories.prisma import get_client, utcnow
from ...schemas import (
    ChangePasswordRequest,
    LoginRequest,
    ProfileUpdateRequest,
    RegisterRequest,
)
from ...services import points, sessions
from .serializers import public_admin, public_user
from .common import clear_session_cookies, set_admin_cookie, set_member_cookie

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return ok({"status": "ok", "service": get_settings().app_name})


@router.post("/auth/member/register", status_code=status.HTTP_201_CREATED)
async def member_register(
    payload: RegisterRequest,
    response: Response,
    client: Prisma = Depends(get_client),
) -> dict:
    exists = await client.sysuser.find_first(
        where={"username": {"equals": payload.username, "mode": "insensitive"}}
    )
    if exists:
        raise conflict("用户名已存在")
    try:
        user = await client.sysuser.create(
            data={
                "username": payload.username,
                "passwordHash": hash_password(payload.password),
                "levelId": await points.default_level_id(client),
            }
        )
        await client.cart.create(data={"userId": user.userId})
    except prisma_errors.UniqueViolationError:
        raise conflict("用户名已存在") from None
    return ok(public_user(user), "注册成功，请登录")


@router.post("/auth/member/login")
async def member_login(
    payload: LoginRequest,
    response: Response,
    client: Prisma = Depends(get_client),
) -> dict:
    user = await client.sysuser.find_first(
        where={"username": {"equals": payload.username, "mode": "insensitive"}}
    )
    if user is None or not verify_password(payload.password, user.passwordHash):
        raise unauthorized("用户名或密码错误")
    if user.accountStatus != "A":
        raise unauthorized("账号已被禁用，请联系管理员")
    await client.sysuser.update(
        where={"userId": user.userId}, data={"lastLoginTime": utcnow()}
    )
    settings = get_settings()
    token = await sessions.create(
        client, subject_type="member", subject_id=user.userId,
        ttl_hours=settings.session_ttl_hours,
    )
    set_member_cookie(response, token)
    return ok(public_user(user), "登录成功")


@router.post("/auth/admin/login")
async def admin_login(
    payload: LoginRequest,
    response: Response,
    client: Prisma = Depends(get_client),
) -> dict:
    admin = await client.sysadmin.find_first(
        where={"adminName": {"equals": payload.username, "mode": "insensitive"}},
        include={"roles": {"include": {"role": True}}},
    )
    if admin is None or not verify_password(payload.password, admin.passwordHash):
        raise unauthorized("管理员账号或密码错误")
    if admin.status != "A":
        raise unauthorized("管理员账号已被禁用")
    await client.sysadmin.update(
        where={"adminId": admin.adminId}, data={"lastLoginTime": utcnow()}
    )
    settings = get_settings()
    token = await sessions.create(
        client, subject_type="admin", subject_id=admin.adminId,
        ttl_hours=settings.session_ttl_hours,
    )
    set_admin_cookie(response, token)
    return ok(await admin_view(client, admin), "登录成功")


async def admin_view(client: Prisma, admin) -> dict:
    fresh = await client.sysadmin.find_unique(
        where={"adminId": admin.adminId},
        include={"roles": {"include": {"role": True}}},
    )
    return public_admin(fresh or admin)


@router.post("/auth/logout")
async def logout(
    response: Response,
    member_session: str | None = Cookie(default=None),
    admin_session: str | None = Cookie(default=None),
    client: Prisma = Depends(get_client),
) -> dict:
    await sessions.destroy(client, member_session)
    await sessions.destroy(client, admin_session)
    clear_session_cookies(response)
    return ok(message="已退出登录")


@router.get("/auth/me")
async def me(
    member_session: str | None = Cookie(default=None),
    admin_session: str | None = Cookie(default=None),
    client: Prisma = Depends(get_client),
) -> dict:
    session = await sessions.find(client, member_session)
    if session and session.userId and (user := await client.sysuser.find_unique(where={"userId": session.userId}, include={"level": True})):
        if user.accountStatus == "A":
            return ok({"type": "member", "user": public_user(user)})
    session = await sessions.find(client, admin_session)
    if session and session.adminId:
        admin = await client.sysadmin.find_unique(
            where={"adminId": session.adminId},
            include={"roles": {"include": {"role": True}}},
        )
        if admin is not None and admin.status == "A":
            return ok({"type": "admin", "admin": public_admin(admin)})
    raise unauthorized()


@router.post("/auth/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    user=Depends(get_current_member),
    client: Prisma = Depends(get_client),
) -> dict:
    if not verify_password(payload.old_password, user.passwordHash):
        raise unauthorized("旧密码错误")
    await client.sysuser.update(
        where={"userId": user.userId},
        data={"passwordHash": hash_password(payload.new_password), "mustChangePassword": False},
    )
    return ok(message="密码修改成功")


@router.patch("/member/profile")
async def update_profile(
    payload: ProfileUpdateRequest,
    user=Depends(get_current_member),
    client: Prisma = Depends(get_client),
) -> dict:
    await client.sysuser.update(
        where={"userId": user.userId},
        data=payload.model_dump(exclude_unset=True),
    )
    return ok({"user_id": user.userId, "username": user.username, **payload.model_dump(exclude_unset=True)}, "资料已保存")


@router.get("/member/points")
async def member_points(
    user=Depends(get_current_member), client: Prisma = Depends(get_client)
) -> dict:
    rows = await client.pointtransaction.find_many(
        where={"userId": user.userId}, order=[{"createdAt": "desc"}], take=50
    )
    return ok(
        {
            "total_points": user.totalPoints,
            "level_name": user.level.levelName if user.level else None,
            "level_id": user.levelId,
            "transactions": [
                {
                    "id": row.transactionId,
                    "points": row.points,
                    "transaction_type": row.transactionType,
                    "order_id": row.orderId,
                    "created_time": row.createdAt,
                }
                for row in rows
            ],
        }
    )
