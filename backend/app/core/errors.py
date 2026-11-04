from fastapi import HTTPException, status


class DomainError(Exception):
    def __init__(self, message: str, code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.code = code
        super().__init__(message)


def not_found(message: str = "资源不存在") -> DomainError:
    return DomainError(message, status.HTTP_404_NOT_FOUND)


def forbidden(message: str = "无权访问") -> DomainError:
    return DomainError(message, status.HTTP_403_FORBIDDEN)


def unauthorized(message: str = "请先登录") -> DomainError:
    return DomainError(message, status.HTTP_401_UNAUTHORIZED)


def raise_http(error: DomainError) -> None:
    raise HTTPException(status_code=error.code, detail=error.message)

