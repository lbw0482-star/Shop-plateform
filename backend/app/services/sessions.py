"""服务端会话：登录态保存在 auth_session 表，浏览器只持 HttpOnly Cookie。"""
from __future__ import annotations

import secrets
from datetime import timedelta

from prisma import Prisma
from prisma.models import AuthSession

from ..repositories.prisma import utcnow


async def cleanup_expired(client: Prisma) -> None:
    await client.authsession.delete_many(where={"expiresAt": {"lte": utcnow()}})


async def create(
    client: Prisma, *, subject_type: str, subject_id: int, ttl_hours: int
) -> str:
    """为会员或管理员创建服务端会话，返回会话令牌。"""
    await cleanup_expired(client)
    token = secrets.token_urlsafe(32)
    await client.authsession.create(
        data={
            "sessionId": token,
            "userId": subject_id if subject_type == "member" else None,
            "adminId": subject_id if subject_type == "admin" else None,
            "expiresAt": utcnow() + timedelta(hours=ttl_hours),
        }
    )
    return token


async def find(client: Prisma, token: str | None) -> AuthSession | None:
    if not token:
        return None
    session = await client.authsession.find_unique(where={"sessionId": token})
    if session is None or session.revokedAt is not None or session.expiresAt <= utcnow():
        return None
    return session


async def destroy(client: Prisma, token: str | None) -> None:
    if token:
        await client.authsession.delete_many(where={"sessionId": token})
