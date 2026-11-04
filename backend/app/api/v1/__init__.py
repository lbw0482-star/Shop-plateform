"""API v1 聚合路由。"""
from fastapi import APIRouter

from . import admin, auth, cart, catalog, messages, orders, profile

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(catalog.router)
api_router.include_router(cart.router)
api_router.include_router(orders.router)
api_router.include_router(messages.router)
api_router.include_router(admin.router)
