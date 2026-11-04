"""认证与权限依赖：服务端会话、角色边界和强制改密约束。"""
from __future__ import annotations

from fastapi import Cookie, Depends
from prisma import Prisma
from prisma.models import SysAdmin, SysUser

from ..repositories.prisma import get_client
from ..services import sessions
from .config import Settings
from .errors import bad_request, forbidden, unauthorized

MEMBER_COOKIE = "member_session"
ADMIN_COOKIE = "admin_session"

ADMIN_ROLES_INCLUDE = {"roles": {"include": {"role": True}}}


def admin_role_codes(admin: SysAdmin) -> list[str]:
    return [link.role.roleCode for link in admin.roles or [] if link.role]


def is_super_admin(admin: SysAdmin) -> bool:
    return "SUPER_ADMIN" in admin_role_codes(admin)


async def get_current_member(
    member_session: str | None = Cookie(default=None),
    client: Prisma = Depends(get_client),
) -> SysUser:
    session = await sessions.find(client, member_session)
    if session is None or session.userId is None:
        raise unauthorized()
    user = await client.sysuser.find_unique(
        where={"userId": session.userId}, include={"level": True}
    )
    if user is None or user.accountStatus != "A":
        raise unauthorized("会员账号不可用")
    return user


async def ensure_password_changed(
    user: SysUser = Depends(get_current_member),
) -> SysUser:
    """管理员重置临时密码后，禁止购物、下单、留言直到修改密码。"""
    if user.mustChangePassword:
        raise bad_request("初始密码尚未修改，请先修改临时密码")
    return user


async def get_current_admin(
    admin_session: str | None = Cookie(default=None),
    client: Prisma = Depends(get_client),
) -> SysAdmin:
    session = await sessions.find(client, admin_session)
    if session is None or session.adminId is None:
        raise unauthorized()
    admin = await client.sysadmin.find_unique(
        where={"adminId": session.adminId}, include=ADMIN_ROLES_INCLUDE
    )
    if admin is None or admin.status != "A":
        raise unauthorized("管理员账号不可用")
    return admin


async def require_super_admin(
    admin: SysAdmin = Depends(get_current_admin),
) -> SysAdmin:
    if not is_super_admin(admin):
        raise forbidden("需要超级管理员权限")
    return admin


def session_cookie_kwargs(settings: Settings) -> dict:
    return {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "max_age": settings.session_ttl_hours * 60 * 60,
        "path": "/",
    }
