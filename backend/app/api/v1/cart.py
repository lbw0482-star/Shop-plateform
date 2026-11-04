"""购物车接口：数量校验和库存判断在服务层完成。"""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from prisma import Prisma

from ...core.deps import ensure_password_changed, get_current_member
from ...core.response import ok
from ...repositories.prisma import get_client
from ...schemas import CartItemRequest, CartItemUpdateRequest, CheckoutPreviewRequest
from ...services import cart as cart_service
from .serializers import cart_view, public_product

router = APIRouter()


async def _view(client: Prisma, user_id: int) -> dict:
    items = await cart_service.cart_items(client, user_id)
    total = sum(
        (row.product.unitPrice * row.quantity for row in items if row.product),
        Decimal("0"),
    )
    return cart_view(items, str(total))


@router.get("/cart")
async def get_cart(
    client: Prisma = Depends(get_client),
    user=Depends(get_current_member),
) -> dict:
    return ok(await _view(client, user.userId))


@router.post("/cart/items")
async def add_cart_item(
    payload: CartItemRequest,
    client: Prisma = Depends(get_client),
    user=Depends(ensure_password_changed),
) -> dict:
    await cart_service.add_item(
        client, user_id=user.userId, product_id=payload.product_id,
        quantity=payload.quantity,
    )
    return ok(await _view(client, user.userId), "已加入购物车")


@router.patch("/cart/items/{item_id}")
async def update_cart_item(
    item_id: int,
    payload: CartItemUpdateRequest,
    client: Prisma = Depends(get_client),
    user=Depends(ensure_password_changed),
) -> dict:
    await cart_service.update_item(
        client, user_id=user.userId, item_id=item_id, quantity=payload.quantity
    )
    return ok(await _view(client, user.userId))


@router.delete("/cart/items/{item_id}")
async def delete_cart_item(
    item_id: int,
    client: Prisma = Depends(get_client),
    user=Depends(ensure_password_changed),
) -> dict:
    await cart_service.remove_item(client, user_id=user.userId, item_id=item_id)
    return ok(await _view(client, user.userId))


@router.delete("/cart/items")
async def clear_cart(
    client: Prisma = Depends(get_client), user=Depends(ensure_password_changed)
) -> dict:
    await cart_service.clear(client, user.userId)
    return ok(await _view(client, user.userId))


@router.post("/cart/checkout-preview")
async def checkout_preview(
    payload: CheckoutPreviewRequest,
    client: Prisma = Depends(get_client),
    user=Depends(ensure_password_changed),
) -> dict:
    rows = await cart_service.checkout_preview(
        client, user_id=user.userId, item_ids=payload.item_ids
    )
    total = sum(row["subtotal"] for row in rows)
    return ok(
        {
            "items": [
                {
                    "cart_item_id": row["cart_item_id"],
                    "product": public_product(row["product"]),
                    "quantity": row["quantity"],
                    "subtotal": str(row["subtotal"]),
                }
                for row in rows
            ],
            "total_amount": str(total),
        }
    )
