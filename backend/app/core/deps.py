from fastapi import Cookie, Depends, HTTPException, status

from .config import Settings, get_settings
from ..db import Admin, Session, Store, User, store


MEMBER_COOKIE = "member_session"
ADMIN_COOKIE = "admin_session"


def get_store() -> Store:
    return store


def _session_or_401(token: str | None, expected_type: str, db: Store) -> Session:
    session = db.get_session(token)
    if session is None or session.subject_type != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    return session


def get_current_member(
    member_session: str | None = Cookie(default=None),
    db: Store = Depends(get_store),
) -> User:
    session = _session_or_401(member_session, "member", db)
    user = db.users.get(session.subject_id)
    if user is None or user.account_status != "A":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="会员账号不可用")
    return user


def get_current_admin(
    admin_session: str | None = Cookie(default=None),
    db: Store = Depends(get_store),
) -> Admin:
    session = _session_or_401(admin_session, "admin", db)
    admin = db.admins.get(session.subject_id)
    if admin is None or admin.status != "A":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="管理员账号不可用")
    return admin


def require_super_admin(admin: Admin = Depends(get_current_admin)) -> Admin:
    if "SUPER_ADMIN" not in admin.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要超级管理员权限")
    return admin


def session_cookie_kwargs(settings: Settings) -> dict:
    return {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "max_age": settings.session_ttl_hours * 60 * 60,
        "path": "/",
    }

