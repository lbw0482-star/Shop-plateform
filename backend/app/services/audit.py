"""管理员关键操作审计日志（audit_log 表）。"""
from __future__ import annotations

from typing import Any

from prisma import Prisma
from prisma.models import SysAdmin


async def write(
    client: Prisma,
    admin: SysAdmin,
    operation_type: str,
    target_type: str,
    target_id: Any = None,
    detail: str | None = None,
) -> None:
    await client.auditlog.create(
        data={
            "adminId": admin.adminId,
            "operationType": operation_type,
            "targetType": target_type,
            "targetId": str(target_id) if target_id is not None else None,
            "operationDetail": detail,
        }
    )
