"""Prisma Client 生命周期与依赖注入。

应用启动时建立连接（FastAPI lifespan），路由通过 ``get_client`` 依赖获取
已连接的 Prisma Client；事务由服务层通过 ``client.tx()`` 管理。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

from prisma import Prisma

client = Prisma()


async def connect() -> None:
    await client.connect()


async def disconnect() -> None:
    await client.disconnect()


def get_client() -> Prisma:
    """FastAPI 依赖：返回已连接的 Prisma Client。"""
    return client


def utcnow() -> datetime:
    """Prisma 引擎返回带 UTC 时区标记的 datetime，统一使用 aware UTC。"""
    return datetime.now(timezone.utc)
