"""路由共享工具：会话 Cookie 写入与清除。"""
from __future__ import annotations

from fastapi import Response

from ...core.config import get_settings
from ...core.deps import ADMIN_COOKIE, MEMBER_COOKIE, session_cookie_kwargs


def set_member_cookie(response: Response, token: str) -> None:
    response.set_cookie(MEMBER_COOKIE, token, **session_cookie_kwargs(get_settings()))


def set_admin_cookie(response: Response, token: str) -> None:
    response.set_cookie(ADMIN_COOKIE, token, **session_cookie_kwargs(get_settings()))


def clear_session_cookies(response: Response) -> None:
    for name in (MEMBER_COOKIE, ADMIN_COOKIE):
        response.delete_cookie(name, path="/")
