"""留言板业务规则：发布待审核、审核公开、回复与维护本人留言。"""
from __future__ import annotations

from typing import Any

from prisma import Prisma
from prisma.models import MemberMessage

from ..core.errors import bad_request, not_found
from ..repositories.prisma import utcnow

MESSAGE_INCLUDE: dict[str, Any] = {
    "user": True,
    "reviewer": True,
    "replies": {"include": {"admin": True}, "orderBy": [{"createdTime": "asc"}]},
}


async def public_list(client: Prisma) -> list[MemberMessage]:
    return await client.membermessage.find_many(
        where={"messageStatus": "A"},
        include=MESSAGE_INCLUDE,
        order=[{"createdTime": "desc"}],
    )


async def member_list(client: Prisma, user_id: int) -> list[MemberMessage]:
    return await client.membermessage.find_many(
        where={"userId": user_id, "messageStatus": {"not": "D"}},
        include=MESSAGE_INCLUDE,
        order=[{"createdTime": "desc"}],
    )


async def admin_list(
    client: Prisma, *, keyword: str | None = None, status: str | None = None
) -> list[MemberMessage]:
    where: dict[str, Any] = {}
    if status:
        where["messageStatus"] = status
    if keyword:
        where["OR"] = [
            {"title": {"contains": keyword}},
            {"content": {"contains": keyword}},
            {"user": {"is": {"username": {"contains": keyword}}}},
        ]
    return await client.membermessage.find_many(
        where=where, include=MESSAGE_INCLUDE, order=[{"createdTime": "desc"}]
    )


async def _get(client: Prisma, message_id: int) -> MemberMessage:
    message = await client.membermessage.find_unique(
        where={"messageId": message_id}, include=MESSAGE_INCLUDE
    )
    if message is None:
        raise not_found("留言不存在")
    return message


async def create(
    client: Prisma, *, user_id: int, title: str, content: str
) -> MemberMessage:
    message = await client.membermessage.create(
        data={"userId": user_id, "title": title, "content": content},
        include=MESSAGE_INCLUDE,
    )
    return message


async def update_member(
    client: Prisma, *, message_id: int, user_id: int, fields: dict[str, Any]
) -> MemberMessage:
    message = await _get(client, message_id)
    if message.userId != user_id:
        raise not_found("留言不存在")
    if message.messageStatus != "P":
        raise bad_request("只有待审核留言可以修改")
    return await client.membermessage.update(
        where={"messageId": message_id},
        data={**fields, "updatedTime": utcnow()},
        include=MESSAGE_INCLUDE,
    )


async def delete_member(
    client: Prisma, *, message_id: int, user_id: int
) -> None:
    message = await _get(client, message_id)
    if message.userId != user_id:
        raise not_found("留言不存在")
    if message.messageStatus != "P":
        raise bad_request("只有待审核留言可以删除")
    await client.membermessage.update(
        where={"messageId": message_id},
        data={"messageStatus": "D", "updatedTime": utcnow()},
    )


async def review(
    client: Prisma, *, message_id: int, admin_id: int, status: str
) -> MemberMessage:
    """管理员审核：A 显示 / H 隐藏，并记录审核人与时间。"""
    await _get(client, message_id)
    return await client.membermessage.update(
        where={"messageId": message_id},
        data={
            "messageStatus": status,
            "reviewerAdminId": admin_id,
            "reviewTime": utcnow(),
            "updatedTime": utcnow(),
        },
        include=MESSAGE_INCLUDE,
    )


async def reply(
    client: Prisma, *, message_id: int, admin_id: int, content: str
) -> MemberMessage:
    await _get(client, message_id)
    await client.messagereply.create(
        data={"messageId": message_id, "adminId": admin_id, "content": content}
    )
    return await _get(client, message_id)


async def admin_delete(client: Prisma, *, message_id: int) -> None:
    await _get(client, message_id)
    await client.membermessage.update(
        where={"messageId": message_id},
        data={"messageStatus": "D", "updatedTime": utcnow()},
    )
