"""HTTP 视图序列化：统一Decimal、日期与关系的输出形状。"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from prisma.models import (
    CartItem,
    MemberAddress,
    MemberMessage,
    Order,
    PaymentRecord,
    Product,
    ProductCategory,
    SysAdmin,
    SysUser,
)


def _money(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def public_user(user: SysUser) -> dict[str, Any]:
    return {
        "id": user.userId,
        "user_id": user.userId,
        "username": user.username,
        "display_name": user.username,
        "role": "MEMBER",
        "gender": user.gender,
        "email": user.email,
        "phone": user.phone,
        "total_points": user.totalPoints,
        "level_name": user.level.levelName if user.level else None,
        "account_status": user.accountStatus,
        "must_change_password": user.mustChangePassword,
        "register_time": user.registerTime,
        "last_login_time": user.lastLoginTime,
    }


def public_admin(admin: SysAdmin) -> dict[str, Any]:
    roles = [link.role.roleCode for link in admin.roles or [] if link.role]
    return {
        "id": admin.adminId,
        "admin_id": admin.adminId,
        "admin_name": admin.adminName,
        "username": admin.adminName,
        "display_name": admin.realName or admin.adminName,
        "real_name": admin.realName,
        "email": admin.email,
        "phone": admin.phone,
        "role": "SUPER_ADMIN" if "SUPER_ADMIN" in roles else "OPER_ADMIN",
        "roles": roles,
        "status": admin.status,
        "last_login_time": admin.lastLoginTime,
    }


def public_category(category: ProductCategory) -> dict[str, Any]:
    return {
        "id": category.categoryId,
        "category_id": category.categoryId,
        "category_name": category.categoryName,
        "description": category.description,
        "sort_no": category.sortNo,
        "status": category.status,
        "created_time": category.createdTime,
    }


def public_product(product: Product) -> dict[str, Any]:
    images = [
        {
            "id": image.imageId,
            "image_id": image.imageId,
            "image_url": image.imageUrl,
            "is_main": image.isMain,
            "sort_no": image.sortNo,
        }
        for image in product.images or []
    ]
    return {
        "id": product.productId,
        "product_id": product.productId,
        "product_code": product.productCode,
        "product_name": product.productName,
        "category_id": product.categoryId,
        "category_name": product.category.categoryName
        if product.category
        else None,
        "stock_qty": product.stockQty,
        "unit_price": _money(product.unitPrice),
        "product_intro": product.productIntro,
        "recommend_flag": product.recommendFlag,
        "product_points": product.productPoints,
        "main_image_url": product.mainImageUrl,
        "product_status": product.productStatus,
        "listing_date": product.listingDate,
        "created_time": product.createdTime,
        "updated_time": product.updatedTime,
        "images": images,
    }


def cart_row(item: CartItem) -> dict[str, Any]:
    product = item.product
    subtotal = item.product.unitPrice * item.quantity if product else Decimal("0")
    return {
        "id": item.cartItemId,
        "cart_item_id": item.cartItemId,
        "product_id": item.productId,
        "product": public_product(product) if product else None,
        "product_name": product.productName if product else "未知商品",
        "unit_price": _money(product.unitPrice) if product else "0",
        "stock_qty": product.stockQty if product else 0,
        "quantity": item.quantity,
        "subtotal": _money(subtotal),
    }


def cart_view(items: list[CartItem], total: str) -> dict[str, Any]:
    return {"items": [cart_row(item) for item in items], "total_amount": total}


def public_payment(payment: PaymentRecord) -> dict[str, Any]:
    return {
        "payment_id": payment.paymentId,
        "order_id": payment.orderId,
        "payment_no": payment.paymentNo,
        "payment_method": payment.paymentMethod,
        "payment_amount": _money(payment.paymentAmount),
        "payment_status": payment.paymentStatus,
        "paid_time": payment.paidTime,
        "transaction_reference": payment.transactionReference,
        "created_time": payment.createdTime,
    }


def public_order(order: Order) -> dict[str, Any]:
    return {
        "id": order.orderId,
        "order_id": order.orderId,
        "order_no": order.orderNo,
        "user_id": order.userId,
        "username": order.user.username if order.user else None,
        "order_time": order.orderTime,
        "receiver_name": order.receiverName,
        "receiver_phone": order.receiverPhone,
        "receiver_address": order.receiverAddress,
        "payment_method": order.paymentMethod,
        "payment_status": order.paymentStatus,
        "order_status": order.orderStatus,
        "total_amount": _money(order.totalAmount),
        "earned_points": order.earnedPoints,
        "remark": order.remark,
        "items": [
            {
                "order_item_id": item.orderItemId,
                "product_id": item.productId,
                "product_name_snapshot": item.productNameSnapshot,
                "unit_price": _money(item.unitPrice),
                "quantity": item.quantity,
                "item_points": item.itemPoints,
                "subtotal": _money(item.subtotal),
            }
            for item in order.items or []
        ],
        "payments": [public_payment(p) for p in order.payments or []],
        "cancel_reason": order.cancelReason,
        "refund_reason": order.refundReason,
        "refund_time": order.refundTime,
        "completed_time": order.completedTime,
        "updated_time": order.updatedTime,
    }


def public_message(message: MemberMessage) -> dict[str, Any]:
    replies = []
    for reply in message.replies or []:
        replies.append(
            {
                "reply_id": reply.replyId,
                "admin_id": reply.adminId,
                "admin_name": (reply.admin.realName or reply.admin.adminName)
                if reply.admin
                else None,
                "content": reply.content,
                "created_time": reply.createdTime,
            }
        )
    return {
        "id": message.messageId,
        "message_id": message.messageId,
        "user_id": message.userId,
        "username": message.user.username if message.user else None,
        "title": message.title,
        "content": message.content,
        "message_status": message.messageStatus,
        "created_time": message.createdTime,
        "updated_time": message.updatedTime,
        "reviewer_admin_id": message.reviewerAdminId,
        "reviewer_name": (message.reviewer.realName or message.reviewer.adminName)
        if message.reviewer
        else None,
        "review_time": message.reviewTime,
        "replies": replies,
        "reply_content": replies[-1]["content"] if replies else None,
    }


def public_address(address: MemberAddress) -> dict[str, Any]:
    return {
        "id": address.addressId,
        "address_id": address.addressId,
        "receiver_name": address.receiverName,
        "receiver_phone": address.receiverPhone,
        "address_detail": address.addressDetail,
        "is_default": address.isDefault,
        "created_time": address.createdTime,
    }
