"""留言板接口：发布、审核、回复与公开展示。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from prisma import Prisma

from ...core.deps import (
    ensure_password_changed,
    get_current_admin,
    get_current_member,
)
from ...core.response import ok
from ...repositories.prisma import get_client
from ...schemas import MessageCreateRequest, MessageUpdateRequest, ReplyRequest
from ...services import audit
from ...services import messages as message_service
from .serializers import public_message

router = APIRouter()


@router.get("/messages/public")
async def public_messages(
    client: Prisma = Depends(get_client), _user=Depends(get_current_member)
) -> dict:
    rows = await message_service.public_list(client)
    return ok([public_message(row) for row in rows])


@router.get("/member/messages")
async def member_messages(
    user=Depends(get_current_member), client: Prisma = Depends(get_client)
) -> dict:
    rows = await message_service.member_list(client, user.userId)
    return ok([public_message(row) for row in rows])


@router.post("/member/messages", status_code=201)
async def create_message(
    payload: MessageCreateRequest,
    client: Prisma = Depends(get_client),
    user=Depends(ensure_password_changed),
) -> dict:
    message = await message_service.create(
        client, user_id=user.userId, title=payload.title, content=payload.content
    )
    return ok(public_message(message), "留言已提交，等待审核")


@router.patch("/member/messages/{message_id}")
async def update_message(
    message_id: int,
    payload: MessageUpdateRequest,
    client: Prisma = Depends(get_client),
    user=Depends(get_current_member),
) -> dict:
    message = await message_service.update_member(
        client,
        message_id=message_id,
        user_id=user.userId,
        fields=payload.model_dump(exclude_unset=True),
    )
    return ok(public_message(message), "留言已更新")


@router.delete("/member/messages/{message_id}")
async def delete_message(
    message_id: int,
    client: Prisma = Depends(get_client),
    user=Depends(get_current_member),
) -> dict:
    await message_service.delete_member(
        client, message_id=message_id, user_id=user.userId
    )
    return ok(message="留言已删除")


@router.get("/admin/messages")
async def admin_messages(
    keyword: str | None = None,
    message_status: str | None = Query(default=None, alias="status"),
    client: Prisma = Depends(get_client),
    _admin=Depends(get_current_admin),
) -> dict:
    rows = await message_service.admin_list(
        client, keyword=keyword, status=message_status
    )
    return ok([public_message(row) for row in rows])


@router.post("/admin/messages/{message_id}/approve")
async def approve_message(
    message_id: int,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    message = await message_service.review(
        client, message_id=message_id, admin_id=admin.adminId, status="A"
    )
    await audit.write(client, admin, "APPROVE", "MESSAGE", message_id)
    return ok(public_message(message), "留言已审核显示")


@router.post("/admin/messages/{message_id}/hide")
async def hide_message(
    message_id: int,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    message = await message_service.review(
        client, message_id=message_id, admin_id=admin.adminId, status="H"
    )
    await audit.write(client, admin, "HIDE", "MESSAGE", message_id)
    return ok(public_message(message), "留言已隐藏")


@router.post("/admin/messages/{message_id}/reply")
async def reply_message(
    message_id: int,
    payload: ReplyRequest,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    message = await message_service.reply(
        client, message_id=message_id, admin_id=admin.adminId, content=payload.content
    )
    await audit.write(client, admin, "REPLY", "MESSAGE", message_id)
    return ok(public_message(message), "回复已发布")


@router.delete("/admin/messages/{message_id}")
async def admin_delete_message(
    message_id: int,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    await message_service.admin_delete(client, message_id=message_id)
    await audit.write(client, admin, "DELETE", "MESSAGE", message_id)
    return ok(message="留言已删除")
