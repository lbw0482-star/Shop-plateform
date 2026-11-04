"""统一业务错误：服务层与路由层使用 DomainError 表达业务异常。"""
from __future__ import annotations

from fastapi import status


class DomainError(Exception):
    def __init__(self, message: str, code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.code = code
        super().__init__(message)


def bad_request(message: str = "请求不合法") -> DomainError:
    return DomainError(message, status.HTTP_400_BAD_REQUEST)


def not_found(message: str = "资源不存在") -> DomainError:
    return DomainError(message, status.HTTP_404_NOT_FOUND)


def forbidden(message: str = "无权访问") -> DomainError:
    return DomainError(message, status.HTTP_403_FORBIDDEN)


def unauthorized(message: str = "请先登录") -> DomainError:
    return DomainError(message, status.HTTP_401_UNAUTHORIZED)


def conflict(message: str) -> DomainError:
    return DomainError(message, status.HTTP_409_CONFLICT)
