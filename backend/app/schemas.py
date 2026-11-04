from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(APIModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_\-\u4e00-\u9fff]+$")
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        return self


class LoginRequest(APIModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(APIModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("两次输入的新密码不一致")
        return self


class ResetPasswordRequest(APIModel):
    temporary_password: str = Field(min_length=8, max_length=128)


class ProfileUpdateRequest(APIModel):
    gender: Literal["M", "F", "U"] | None = None
    email: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=20)


class CategoryCreateRequest(APIModel):
    category_name: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=200)
    sort_no: int = Field(default=0, ge=0)


class ProductCreateRequest(APIModel):
    product_code: str = Field(min_length=1, max_length=30)
    product_name: str = Field(min_length=1, max_length=100)
    category_id: int
    stock_qty: int = Field(default=0, ge=0)
    unit_price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    product_intro: str | None = Field(default=None, max_length=2000)
    recommend_flag: bool = False
    product_points: int = Field(default=0, ge=0)
    main_image_url: str | None = Field(default=None, max_length=255)


class ProductUpdateRequest(APIModel):
    product_name: str | None = Field(default=None, min_length=1, max_length=100)
    category_id: int | None = None
    stock_qty: int | None = Field(default=None, ge=0)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    product_intro: str | None = Field(default=None, max_length=2000)
    recommend_flag: bool | None = None
    product_points: int | None = Field(default=None, ge=0)
    main_image_url: str | None = Field(default=None, max_length=255)


class CartItemRequest(APIModel):
    product_id: int
    quantity: int = Field(gt=0, le=999)


class CartItemUpdateRequest(APIModel):
    quantity: int = Field(gt=0, le=999)


class CheckoutPreviewRequest(APIModel):
    item_ids: list[int] = Field(min_length=1)


class OrderCreateRequest(APIModel):
    item_ids: list[int] = Field(min_length=1)
    receiver_name: str = Field(min_length=1, max_length=50)
    receiver_phone: str = Field(min_length=5, max_length=20)
    receiver_address: str = Field(min_length=1, max_length=255)
    payment_method: Literal["SIMULATED_ONLINE", "SIMULATED_BALANCE"] = "SIMULATED_ONLINE"
    remark: str | None = Field(default=None, max_length=500)


class OrderUpdateRequest(APIModel):
    receiver_name: str | None = Field(default=None, min_length=1, max_length=50)
    receiver_phone: str | None = Field(default=None, min_length=5, max_length=20)
    receiver_address: str | None = Field(default=None, min_length=1, max_length=255)
    remark: str | None = Field(default=None, max_length=500)


class RefundApplyRequest(APIModel):
    reason: str = Field(min_length=1, max_length=200)


class MessageCreateRequest(APIModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=2000)


class MessageUpdateRequest(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None = Field(default=None, min_length=1, max_length=2000)


class ReplyRequest(APIModel):
    content: str = Field(min_length=1, max_length=2000)


class LevelUpdateRequest(APIModel):
    level_name: str | None = Field(default=None, min_length=1, max_length=30)
    min_points: int | None = Field(default=None, ge=0)
    max_points: int | None = Field(default=None, ge=0)
    status: Literal["A", "I"] | None = None


class AdminCreateRequest(APIModel):
    admin_name: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    real_name: str | None = Field(default=None, max_length=50)
    role_code: Literal["OPER_ADMIN", "SUPER_ADMIN"] = "OPER_ADMIN"


class AdminStatusRequest(APIModel):
    status: Literal["A", "I"]


class UserView(APIModel):
    user_id: int
    username: str
    gender: str
    email: str | None
    phone: str | None
    total_points: int
    level_name: str
    account_status: str
    must_change_password: bool


class AdminView(APIModel):
    admin_id: int
    admin_name: str
    real_name: str | None
    roles: list[str]
    status: str

