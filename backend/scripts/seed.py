"""数据库种子：初始化等级、角色、管理员、分类、商品与演示数据。

运行：python scripts/seed.py（需要 backend/.env 中的 PostgreSQL 连接）
幂等：全部采用 upsert，可重复执行。
"""
from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password  # noqa: E402
from app.repositories.prisma import client, utcnow  # noqa: E402

LEVELS = [
    {"levelName": "普通会员", "minPoints": 0, "maxPoints": 999, "sortNo": 1},
    {"levelName": "银牌会员", "minPoints": 1000, "maxPoints": 4999, "sortNo": 2},
    {"levelName": "金牌会员", "minPoints": 5000, "maxPoints": 9999, "sortNo": 3},
    {"levelName": "钻石会员", "minPoints": 10000, "maxPoints": None, "sortNo": 4},
]

ROLES = [
    {
        "roleCode": "SUPER_ADMIN",
        "roleName": "超级管理员",
        "description": "维护管理员账号、角色和会员等级规则",
    },
    {
        "roleCode": "OPER_ADMIN",
        "roleName": "普通管理员",
        "description": "处理会员、商品、订单和留言",
    },
]

ADMINS = [
    {"adminName": "admin", "password": "Admin123!", "realName": "系统管理员", "role": "SUPER_ADMIN"},
    {"adminName": "operator", "password": "Oper12345!", "realName": "运营专员", "role": "OPER_ADMIN"},
]

CATEGORIES = [
    {"categoryName": "家居生活", "description": "让家更温柔的日常器物", "sortNo": 1},
    {"categoryName": "厨房茶饮", "description": "茶器、咖啡馆与厨房好物", "sortNo": 2},
    {"categoryName": "出行通勤", "description": "随身与通勤小品", "sortNo": 3},
]

PRODUCTS = [
    {
        "productCode": "HOME-1001", "productName": "轻量保温杯", "category": "厨房茶饮",
        "stockQty": 50, "unitPrice": Decimal("89.00"), "productIntro": "316 不锈钢单层轻量杯身，一杯热茶走全天。",
        "recommendFlag": True, "productPoints": 89, "images": ["/uploads/seed/home-1001-1.jpg"],
    },
    {
        "productCode": "HOME-1002", "productName": "桌面收纳盒", "category": "家居生活",
        "stockQty": 80, "unitPrice": Decimal("39.90"), "productIntro": "可叠加的分格收纳，把桌面留给自己。",
        "recommendFlag": True, "productPoints": 39, "images": ["/uploads/seed/home-1002-1.jpg"],
    },
    {
        "productCode": "HOME-1003", "productName": "帆布购物袋", "category": "出行通勤",
        "stockQty": 120, "unitPrice": Decimal("29.90"), "productIntro": "加厚双层帆布，装得下生活也装得下菜。",
        "recommendFlag": False, "productPoints": 29, "images": [],
    },
    {
        "productCode": "HOME-1004", "productName": "手冲咖啡壶", "category": "厨房茶饮",
        "stockQty": 30, "unitPrice": Decimal("128.00"), "productIntro": "细口控流，新手也能稳定绕圈。",
        "recommendFlag": True, "productPoints": 128, "images": ["/uploads/seed/home-1004-1.jpg"],
    },
    {
        "productCode": "HOME-1005", "productName": "亚麻桌旗", "category": "家居生活",
        "stockQty": 60, "unitPrice": Decimal("59.00"), "productIntro": "水洗亚麻，越用越软。",
        "recommendFlag": False, "productPoints": 59, "images": [],
    },
    {
        "productCode": "HOME-1006", "productName": "便携茶具套装", "category": "厨房茶饮",
        "stockQty": 40, "unitPrice": Decimal("99.00"), "productIntro": "一壶两杯一收纳，出差也能喝口热茶。",
        "recommendFlag": False, "productPoints": 99, "images": [],
    },
]

DEMO_MEMBER = {"username": "demo", "password": "Demo12345!", "email": "demo@example.com", "phone": "13800000000"}


async def main() -> None:
    await client.connect()
    try:
        for level in LEVELS:
            await client.memberlevel.upsert(
                where={"levelName": level["levelName"]},
                data={"create": {**level, "status": "A"}, "update": level},
            )
        default_level = await client.memberlevel.find_first_or_raise(
            where={"minPoints": 0}
        )
        for role in ROLES:
            await client.sysrole.upsert(
                where={"roleCode": role["roleCode"]},
                data={"create": {**role, "status": "A"}, "update": role},
            )
        for item in ADMINS:
            role = await client.sysrole.find_first_or_raise(where={"roleCode": item["role"]})
            await client.sysadmin.upsert(
                where={"adminName": item["adminName"]},
                data={
                    "create": {
                        "adminName": item["adminName"],
                        "passwordHash": hash_password(item["password"]),
                        "realName": item["realName"],
                        "status": "A",
                        "roles": {"create": {"roleId": role.roleId}},
                    },
                    "update": {
                        "passwordHash": hash_password(item["password"]),
                        "realName": item["realName"],
                        "status": "A",
                    },
                },
            )
        for item in CATEGORIES:
            await client.productcategory.upsert(
                where={"categoryName": item["categoryName"]},
                data={"create": {**item, "status": "A"}, "update": item},
            )
        for item in PRODUCTS:
            category = await client.productcategory.find_first_or_raise(
                where={"categoryName": item["category"]}
            )
            await client.product.upsert(
                where={"productCode": item["productCode"]},
                data={
                    "create": {
                        "productCode": item["productCode"],
                        "productName": item["productName"],
                        "categoryId": category.categoryId,
                        "stockQty": item["stockQty"],
                        "unitPrice": item["unitPrice"],
                        "productIntro": item["productIntro"],
                        "recommendFlag": item["recommendFlag"],
                        "productPoints": item["productPoints"],
                        "productStatus": "O",
                        "listingDate": utcnow(),
                        "mainImageUrl": item["images"][0] if item["images"] else None,
                    },
                    "update": {
                        "productName": item["productName"],
                        "categoryId": category.categoryId,
                        "productIntro": item["productIntro"],
                        "recommendFlag": item["recommendFlag"],
                        "productPoints": item["productPoints"],
                        "productStatus": "O",
                    },
                },
            )
            product = await client.product.find_unique_or_raise(
                where={"productCode": item["productCode"]}, include={"images": True}
            )
            for url in item["images"]:
                exists = any(image.imageUrl == url for image in product.images)
                if not exists:
                    await client.productimage.create(
                        data={
                            "productId": product.productId,
                            "imageUrl": url,
                            "isMain": url == item["images"][0],
                        }
                    )
        await client.sysuser.upsert(
            where={"username": DEMO_MEMBER["username"]},
            data={
                "create": {
                    "username": DEMO_MEMBER["username"],
                    "passwordHash": hash_password(DEMO_MEMBER["password"]),
                    "email": DEMO_MEMBER["email"],
                    "phone": DEMO_MEMBER["phone"],
                    "gender": "U",
                    "levelId": default_level.levelId,
                },
                "update": {},
            },
        )
        member = await client.sysuser.find_unique_or_raise(
            where={"username": DEMO_MEMBER["username"]}, include={"carts": True}
        )
        if not member.carts:
            await client.cart.create(data={"userId": member.userId})
        address = await client.memberaddress.find_first(where={"userId": member.userId})
        if address is None:
            await client.memberaddress.create(
                data={
                    "userId": member.userId,
                    "receiverName": "李晓晓",
                    "receiverPhone": "13800000000",
                    "addressDetail": "北京市朝阳区示例路 1 号院 2 号楼 501",
                    "isDefault": True,
                }
            )
        pending = await client.membermessage.find_first(
            where={"title": "什么时候上新冬季款？"}
        )
        if pending is None:
            await client.membermessage.create(
                data={
                    "userId": member.userId,
                    "title": "什么时候上新冬季款？",
                    "content": "保温杯很好用，希望出个冬季新配色。",
                }
            )
        approved = await client.membermessage.find_first(
            where={"title": "包装很用心", "userId": member.userId}
        )
        operator = await client.sysadmin.find_first_or_raise(where={"adminName": "operator"})
        if approved is None:
            approved = await client.membermessage.create(
                data={
                    "userId": member.userId,
                    "title": "包装很用心",
                    "content": "第一次在会员商店下单，包装和物流都很稳。",
                    "messageStatus": "A",
                    "reviewerAdminId": operator.adminId,
                    "reviewTime": utcnow(),
                }
            )
            await client.messagereply.create(
                data={
                    "messageId": approved.messageId,
                    "adminId": operator.adminId,
                    "content": "感谢支持，每单都有专人打包，欢迎常来。",
                }
            )
        print("种子数据完成：admin / Admin123!  operator / Oper12345!  demo / Demo12345!")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
