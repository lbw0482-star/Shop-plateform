"""会员地址簿：下单时可复用联系人信息，订单创建后保存快照。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from prisma import Prisma
from prisma.models import MemberAddress

from ...core.deps import get_current_member
from ...core.errors import forbidden, not_found
from ...core.response import ok
from ...repositories.prisma import get_client, utcnow
from ...schemas import MemberAddressCreateRequest, MemberAddressUpdateRequest
from .serializers import public_address

router = APIRouter()

# 请求模型为 snake_case，Prisma 模型字段为 camelCase
ADDRESS_FIELD_MAP = {
    "receiver_name": "receiverName",
    "receiver_phone": "receiverPhone",
    "address_detail": "addressDetail",
    "is_default": "isDefault",
}


def _owned(address: MemberAddress | None, user_id: int) -> MemberAddress:
    if address is None:
        raise not_found("地址不存在")
    if address.userId != user_id:
        raise forbidden("无权操作该地址")
    return address


@router.get("/member/addresses")
async def list_addresses(
    user=Depends(get_current_member), client: Prisma = Depends(get_client)
) -> dict:
    rows = await client.memberaddress.find_many(
        where={"userId": user.userId},
        order=[{"isDefault": "desc"}, {"createdTime": "desc"}],
    )
    return ok([public_address(row) for row in rows])


@router.post("/member/addresses", status_code=201)
async def create_address(
    payload: MemberAddressCreateRequest,
    user=Depends(get_current_member),
    client: Prisma = Depends(get_client),
) -> dict:
    data = {ADDRESS_FIELD_MAP[key]: value for key, value in payload.model_dump().items()}
    if data["isDefault"]:
        await client.memberaddress.update_many(
            where={"userId": user.userId, "isDefault": True}, data={"isDefault": False}
        )
    address = await client.memberaddress.create(data={"userId": user.userId, **data})
    return ok(public_address(address), "地址已保存")


@router.patch("/member/addresses/{address_id}")
async def update_address(
    address_id: int,
    payload: MemberAddressUpdateRequest,
    user=Depends(get_current_member),
    client: Prisma = Depends(get_client),
) -> dict:
    address = _owned(
        await client.memberaddress.find_unique(where={"addressId": address_id}),
        user.userId,
    )
    fields = {ADDRESS_FIELD_MAP[key]: value for key, value in payload.model_dump(exclude_unset=True).items()}
    if fields.get("isDefault"):
        await client.memberaddress.update_many(
            where={"userId": user.userId, "isDefault": True}, data={"isDefault": False}
        )
    updated = await client.memberaddress.update(
        where={"addressId": address_id},
        data={**fields, "updatedTime": utcnow()},
    )
    return ok(public_address(updated), "地址已更新")


@router.post("/member/addresses/{address_id}/default")
async def set_default_address(
    address_id: int,
    user=Depends(get_current_member),
    client: Prisma = Depends(get_client),
) -> dict:
    address = _owned(
        await client.memberaddress.find_unique(where={"addressId": address_id}),
        user.userId,
    )
    await client.memberaddress.update_many(
        where={"userId": user.userId, "isDefault": True}, data={"isDefault": False}
    )
    updated = await client.memberaddress.update(
        where={"addressId": address.addressId}, data={"isDefault": True}
    )
    return ok(public_address(updated), "已设为默认地址")


@router.delete("/member/addresses/{address_id}")
async def delete_address(
    address_id: int,
    user=Depends(get_current_member),
    client: Prisma = Depends(get_client),
) -> dict:
    address = _owned(
        await client.memberaddress.find_unique(where={"addressId": address_id}),
        user.userId,
    )
    await client.memberaddress.delete(where={"addressId": address.addressId})
    return ok(message="地址已删除")
