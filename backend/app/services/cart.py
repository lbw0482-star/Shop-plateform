"""购物车业务规则：每人一辆活动购物车、同商品合并数量、库存与上架校验。"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from prisma import Prisma
from prisma.models import Cart, CartItem, Product

from ..core.errors import bad_request, not_found
from ..repositories.prisma import utcnow


async def _ensure_cart(client: Prisma, user_id: int) -> Cart:
    cart = await client.cart.find_first(where={"userId": user_id})
    if cart is None:
        cart = await client.cart.create(data={"userId": user_id})
    return cart


async def cart_items(client: Prisma, user_id: int) -> list[CartItem]:
    cart = await client.cart.find_first(where={"userId": user_id})
    if cart is None:
        return []
    return await client.cartitem.find_many(
        where={"cartId": cart.cartId},
        include={"product": True},
        order=[{"addTime": "asc"}],
    )


async def add_item(
    client: Prisma, *, user_id: int, product_id: int, quantity: int
) -> None:
    product: Product | None = await client.product.find_unique(
        where={"productId": product_id}
    )
    if product is None:
        raise not_found("商品不存在")
    if product.productStatus != "O":
        raise bad_request("商品未上架")
    cart = await _ensure_cart(client, user_id)
    existing = await client.cartitem.find_first(
        where={"cartId": cart.cartId, "productId": product_id}
    )
    merged = (existing.quantity if existing else 0) + quantity
    if merged > product.stockQty:
        raise bad_request("库存不足")
    if existing:
        await client.cartitem.update(
            where={"cartItemId": existing.cartItemId},
            data={"quantity": merged, "updatedTime": utcnow()},
        )
    else:
        await client.cartitem.create(
            data={
                "cartId": cart.cartId,
                "productId": product_id,
                "quantity": quantity,
            }
        )
    await client.cart.update(
        where={"cartId": cart.cartId}, data={"updatedTime": utcnow()}
    )


async def update_item(
    client: Prisma, *, user_id: int, item_id: int, quantity: int
) -> None:
    item = await client.cartitem.find_unique(
        where={"cartItemId": item_id},
        include={"cart": True, "product": True},
    )
    if item is None or item.cart.userId != user_id:
        raise not_found("购物车商品不存在")
    product = item.product
    if product is None:
        raise not_found("商品不存在")
    if product.productStatus != "O":
        raise bad_request("商品已下架，请移除该商品")
    if quantity > product.stockQty:
        raise bad_request("库存不足")
    await client.cartitem.update(
        where={"cartItemId": item_id},
        data={"quantity": quantity, "updatedTime": utcnow()},
    )
    await client.cart.update(
        where={"cartId": item.cartId}, data={"updatedTime": utcnow()}
    )


async def remove_item(client: Prisma, *, user_id: int, item_id: int) -> None:
    item = await client.cartitem.find_unique(
        where={"cartItemId": item_id}, include={"cart": True}
    )
    if item is None or item.cart.userId != user_id:
        raise not_found("购物车商品不存在")
    await client.cartitem.delete(where={"cartItemId": item_id})


async def clear(client: Prisma, user_id: int) -> None:
    cart = await client.cart.find_first(where={"userId": user_id})
    if cart is not None:
        await client.cartitem.delete_many(where={"cartId": cart.cartId})


async def checkout_preview(
    client: Prisma, *, user_id: int, item_ids: list[int]
) -> list[dict[str, Any]]:
    """批量结算预览：校验选中商品的上架状态与库存。"""
    cart = await client.cart.find_first(where={"userId": user_id})
    requested = list(dict.fromkeys(item_ids))
    rows: list[CartItem] = []
    if cart is not None:
        rows = await client.cartitem.find_many(
            where={"cartId": cart.cartId, "cartItemId": {"in": requested}},
            include={"product": True},
        )
    if len(rows) != len(requested):
        raise bad_request("购物车商品无效")
    preview: list[dict[str, Any]] = []
    for item in sorted(rows, key=lambda value: value.cartItemId):
        product = item.product
        name = product.productName if product else "未知商品"
        if product is None or product.productStatus != "O":
            raise bad_request(f"商品 {name} 已下架或不存在")
        if item.quantity > product.stockQty:
            raise bad_request(f"商品 {product.productName} 库存不足")
        preview.append(
            {
                "cart_item_id": item.cartItemId,
                "product": product,
                "quantity": item.quantity,
                "subtotal": (product.unitPrice * item.quantity).quantize(
                    Decimal("0.01")
                ),
            }
        )
    return preview
