"""商品中心：分类、商品、上下架、图片与会员端搜索。"""
from __future__ import annotations

import secrets
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from prisma import Prisma, errors as prisma_errors
from prisma.models import Product

from ...core.deps import get_current_admin, get_current_member
from ...core.config import get_settings
from ...core.errors import bad_request, conflict, not_found
from ...core.response import ok, page
from ...repositories.prisma import get_client, utcnow
from ...schemas import (
    CategoryCreateRequest,
    CategoryUpdateRequest,
    ProductCreateRequest,
    ProductUpdateRequest,
)
from ...services import audit
from .serializers import public_category, public_product

router = APIRouter()

PRODUCT_INCLUDE = {"category": True}
PRODUCT_DETAIL_INCLUDE = {"category": True, "images": {"orderBy": [{"sortNo": "asc"}]}}

# 分类请求模型为 snake_case，Prisma 模型字段为 camelCase（同名键无需转换）
CATEGORY_FIELD_MAP = {
    "category_name": "categoryName",
    "sort_no": "sortNo",
}


def _product_filters(
    *,
    keyword: str | None = None,
    category_id: int | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    recommend: bool | None = None,
    product_status: str | None = None,
) -> dict[str, Any]:
    where: dict[str, Any] = {}
    if product_status:
        where["productStatus"] = product_status
    if keyword:
        where["OR"] = [
            {"productName": {"contains": keyword}},
            {"productCode": {"contains": keyword}},
        ]
    if category_id is not None:
        where["categoryId"] = category_id
    price_filter: dict[str, Decimal] = {}
    if min_price is not None:
        price_filter["gte"] = min_price
    if max_price is not None:
        price_filter["lte"] = max_price
    if price_filter:
        where["unitPrice"] = price_filter
    if recommend is not None:
        where["recommendFlag"] = recommend
    return where


async def _product_or_404(client: Prisma, product_id: int, **include) -> Product:
    product = await client.product.find_unique(
        where={"productId": product_id}, include=include or None
    )
    if product is None:
        raise not_found("商品不存在")
    return product


@router.get("/categories")
async def categories(
    client: Prisma = Depends(get_client),
    _user=Depends(get_current_member),
) -> dict:
    rows = await client.productcategory.find_many(
        where={"status": "A"}, order=[{"sortNo": "asc"}]
    )
    return ok([public_category(row) for row in rows])


@router.get("/products")
async def products(
    keyword: str | None = None,
    category_id: int | None = None,
    min_price: Decimal | None = Query(default=None, alias="min_price", ge=0),
    max_price: Decimal | None = Query(default=None, alias="max_price", ge=0),
    recommend: bool | None = None,
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    client: Prisma = Depends(get_client),
    _user=Depends(get_current_member),
) -> dict:
    where = _product_filters(
        keyword=keyword,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        recommend=recommend,
        product_status="O",
    )
    total = await client.product.count(where=where)
    rows = await client.product.find_many(
        where=where, include=PRODUCT_INCLUDE, order=[{"productId": "desc"}],
        skip=(page_no - 1) * page_size, take=page_size,
    )
    return ok(page([public_product(row) for row in rows], total, page_no, page_size))


@router.get("/products/{product_id}")
async def product_detail(
    product_id: int,
    client: Prisma = Depends(get_client),
    _user=Depends(get_current_member),
) -> dict:
    product = await _product_or_404(client, product_id, **PRODUCT_DETAIL_INCLUDE)
    if product.productStatus != "O":
        raise not_found("商品已下架")
    return ok(public_product(product))


@router.get("/admin/categories")
async def admin_categories(
    client: Prisma = Depends(get_client),
    _admin=Depends(get_current_admin),
) -> dict:
    rows = await client.productcategory.find_many(order=[{"sortNo": "asc"}])
    return ok([public_category(row) for row in rows])


@router.post("/admin/categories", status_code=201)
async def create_category(
    payload: CategoryCreateRequest,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    exists = await client.productcategory.find_first(
        where={"categoryName": {"equals": payload.category_name, "mode": "insensitive"}}
    )
    if exists:
        raise conflict("分类名称已存在")
    try:
        category = await client.productcategory.create(
            data={
                CATEGORY_FIELD_MAP.get(key, key): value
                for key, value in payload.model_dump(exclude_unset=True).items()
            }
        )
    except prisma_errors.UniqueViolationError:
        raise conflict("分类名称已存在") from None
    await audit.write(client, admin, "CREATE", "CATEGORY", category.categoryId)
    return ok(public_category(category))


@router.patch("/admin/categories/{category_id}")
async def update_category(
    category_id: int,
    payload: CategoryUpdateRequest,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    category = await client.productcategory.find_unique(where={"categoryId": category_id})
    if category is None:
        raise not_found("分类不存在")
    fields = payload.model_dump(exclude_unset=True)
    data = {
        CATEGORY_FIELD_MAP.get(key, key): value for key, value in fields.items()
    }
    name = fields.get("category_name")
    if name and name.lower() != category.categoryName.lower():
        exists = await client.productcategory.find_first(
            where={"categoryName": {"equals": name, "mode": "insensitive"}}
        )
        if exists:
            raise conflict("分类名称已存在")
    try:
        updated = await client.productcategory.update(
            where={"categoryId": category_id}, data=data
        )
    except prisma_errors.UniqueViolationError:
        raise conflict("分类名称已存在") from None
    if updated is None:
        raise not_found("分类不存在")
    await audit.write(client, admin, "UPDATE", "CATEGORY", category_id)
    return ok(public_category(updated))


@router.post("/admin/products", status_code=201)
async def create_product(
    payload: ProductCreateRequest,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    category = await client.productcategory.find_unique(
        where={"categoryId": payload.category_id}
    )
    if category is None or category.status != "A":
        raise bad_request("分类不存在或已停用")
    exists = await client.product.find_first(
        where={"productCode": {"equals": payload.product_code, "mode": "insensitive"}}
    )
    if exists:
        raise conflict("商品编号已存在")
    try:
        product = await client.product.create(
            data={**payload.model_dump(exclude_unset=True), "productStatus": "D"}
        )
    except prisma_errors.UniqueViolationError:
        raise conflict("商品编号已存在") from None
    await audit.write(client, admin, "CREATE", "PRODUCT", product.productId)
    return ok(
        public_product(await _product_or_404(client, product.productId, **PRODUCT_INCLUDE))
    )


@router.get("/admin/products")
async def admin_products(
    keyword: str | None = None,
    product_status: str | None = None,
    category_id: int | None = None,
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    client: Prisma = Depends(get_client),
    _admin=Depends(get_current_admin),
) -> dict:
    where = _product_filters(
        keyword=keyword, category_id=category_id, product_status=product_status
    )
    total = await client.product.count(where=where)
    rows = await client.product.find_many(
        where=where, include=PRODUCT_INCLUDE, order=[{"productId": "desc"}],
        skip=(page_no - 1) * page_size, take=page_size,
    )
    return ok(page([public_product(row) for row in rows], total, page_no, page_size))


@router.patch("/admin/products/{product_id}")
async def update_product(
    product_id: int,
    payload: ProductUpdateRequest,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    await _product_or_404(client, product_id)
    fields = payload.model_dump(exclude_unset=True)
    if "category_id" in fields:
        category = await client.productcategory.find_unique(
            where={"categoryId": fields["category_id"]}
        )
        if category is None or category.status != "A":
            raise bad_request("分类不存在或已停用")
    updated = await client.product.update(
        where={"productId": product_id},
        data={**fields, "updatedTime": utcnow()},
    )
    if updated is None:
        raise not_found("商品不存在")
    await audit.write(client, admin, "UPDATE", "PRODUCT", product_id)
    return ok(public_product(await _product_or_404(client, product_id, **PRODUCT_INCLUDE)))


@router.post("/admin/products/{product_id}/listing")
async def listing_product(
    product_id: int,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    await _product_or_404(client, product_id)
    await client.product.update(
        where={"productId": product_id},
        data={"productStatus": "O", "listingDate": utcnow(), "updatedTime": utcnow()},
    )
    await audit.write(client, admin, "LIST", "PRODUCT", product_id)
    return ok(public_product(await _product_or_404(client, product_id, **PRODUCT_INCLUDE)))


@router.post("/admin/products/{product_id}/off-shelf")
async def off_shelf_product(
    product_id: int,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    await _product_or_404(client, product_id)
    await client.product.update(
        where={"productId": product_id},
        data={"productStatus": "X", "updatedTime": utcnow()},
    )
    await audit.write(client, admin, "OFF_SHELF", "PRODUCT", product_id)
    return ok(public_product(await _product_or_404(client, product_id, **PRODUCT_INCLUDE)))


@router.get("/admin/products/{product_id}/images")
async def product_images(
    product_id: int,
    client: Prisma = Depends(get_client),
    _admin=Depends(get_current_admin),
) -> dict:
    await _product_or_404(client, product_id)
    rows = await client.productimage.find_many(
        where={"productId": product_id}, order=[{"sortNo": "asc"}]
    )
    return ok(
        [
            {
                "id": row.imageId,
                "image_id": row.imageId,
                "image_url": row.imageUrl,
                "is_main": row.isMain,
                "sort_no": row.sortNo,
                "created_time": row.createdTime,
            }
            for row in rows
        ]
    )


@router.post("/admin/products/{product_id}/images", status_code=201)
async def upload_product_image(
    product_id: int,
    image: UploadFile = File(...),
    is_main: bool = Form(default=False),
    sort_no: int = Form(default=0, ge=0),
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    await _product_or_404(client, product_id)
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise bad_request("只支持 JPG、PNG 或 WEBP 图片")
    content = await image.read()
    if len(content) > 5 * 1024 * 1024:
        raise bad_request("图片不能超过 5MB")
    upload_dir = get_settings().upload_dir
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    suffix = "." + (image.filename or "upload.jpg").rsplit(".", 1)[-1].lower()
    filename = f"product-{product_id}-{int(utcnow().timestamp())}{secrets.token_hex(2)}{suffix}"
    (Path(upload_dir) / filename).write_bytes(content)
    url = f"/uploads/{filename}"
    async with client.tx() as tx:
        if is_main:
            await tx.productimage.update_many(
                where={"productId": product_id, "isMain": True},
                data={"isMain": False},
            )
        row = await tx.productimage.create(
            data={
                "productId": product_id,
                "imageUrl": url,
                "isMain": is_main,
                "sortNo": sort_no,
            }
        )
        if is_main:
            await tx.product.update(
                where={"productId": product_id},
                data={"mainImageUrl": url, "updatedTime": utcnow()},
            )
    await audit.write(client, admin, "UPLOAD_IMAGE", "PRODUCT", product_id)
    return ok({"url": url, "image_id": row.imageId}, "图片已上传")


@router.delete("/admin/product-images/{image_id}")
async def delete_product_image(
    image_id: int,
    admin=Depends(get_current_admin),
    client: Prisma = Depends(get_client),
) -> dict:
    image = await client.productimage.find_unique(where={"imageId": image_id})
    if image is None:
        raise not_found("图片不存在")
    await client.productimage.delete(where={"imageId": image_id})
    product = await client.product.find_unique(where={"productId": image.productId})
    if product and product.mainImageUrl == image.imageUrl:
        await client.product.update(
            where={"productId": image.productId}, data={"mainImageUrl": None}
        )
    await audit.write(client, admin, "DELETE_IMAGE", "PRODUCT", image.productId)
    return ok(message="图片已删除")
