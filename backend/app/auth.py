import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

SECRET_KEY = os.environ.get("AVM_SECRET_KEY", "ai-video-assets-local-secret-key")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7
PBKDF2_ITERATIONS = 120000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"pbkdf2${PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, digest = stored.split("$")
        if algo != "pbkdf2":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        )
        return hmac.compare_digest(dk.hex(), digest)
    except Exception:
        return False


def create_token(user_id: int) -> str:
    payload = {
        "uid": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="请先登录")
    token = authorization[7:].strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="登录凭证无效")
    user = db.query(User).get(payload.get("uid"))
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


# ---------------- 权限模型 ----------------
# 角色与能力：
#   admin   —— 超管：可读全部、可写全部、可管理他人数据
#   creator —— 普通创作者：可读全部、可创建，写操作仅限自己创建的数据
#   viewer  —— 只读观察者：可读全部，不可创建/修改/删除
#
# 用户表字段 can_create / can_view_all 用于把普通用户降级为只读或限定数据可见范围。


def is_admin(user: User) -> bool:
    return user.role == "admin"


def can_create(user: User) -> bool:
    """是否有创建新资产的权限（超管恒为真）。"""
    if is_admin(user):
        return True
    return bool(user.can_create)


def can_view_all(user: User) -> bool:
    """是否能看到他人创建的数据（超管恒为真）。"""
    if is_admin(user):
        return True
    return bool(user.can_view_all)


def require_create(user: User) -> None:
    if not can_create(user):
        raise HTTPException(status_code=403, detail="当前账号为只读权限，无法创建内容")


def is_privileged(user: User) -> bool:
    """是否超管级别：真超管（role=admin）或模块角色 super。

    模块角色 super 是角色权限页可配置的最高档，拥有它等同于超管，
    因此数据所有权、日志范围等原本只看 is_admin 的地方也应对其放行。
    """
    if is_admin(user):
        return True
    return user_module_role(user) == "super"


def ensure_owner(resource, user: User, action: str = "操作"):
    """资源的创建者或超管级别账号可以修改/删除。"""
    if is_privileged(user):
        return
    if resource.owner_id is None:
        return
    if resource.owner_id != user.id:
        raise HTTPException(
            status_code=403, detail=f"只能{action}自己创建的资产，如需操作他人资产请联系管理员"
        )


def scope_filter(query, model, user: User, scope: str = "all"):
    """按可见范围过滤查询。

    scope = "all"  全库（受 can_view_all 限制）
    scope = "mine" 仅自己创建的
    """
    if scope == "mine":
        return query.filter(model.owner_id == user.id)
    if not can_view_all(user):
        return query.filter(model.owner_id == user.id)
    return query


# ---------------- 模块角色权限 ----------------
# 模块角色（super / inspiration / production / operation）决定可见菜单与可用按钮，
# 与上方的数据权限（role / can_create / can_view_all）互补：前者管「看什么、点什么」，
# 后者管「能改谁的数据」。详见 permissions.py。


def has_permission(user: User, button_key: str, db: Session = None) -> bool:
    """用户是否具备某个按钮权限（超管恒为真）。"""
    if is_admin(user):
        return True
    from .permissions import user_permissions

    perms = user_permissions(user, db)
    return button_key in perms["buttons"]


def require_permission(user: User, button_key: str, db: Session = None) -> None:
    """校验按钮权限，不足则抛 403。"""
    if has_permission(user, button_key, db):
        return
    raise HTTPException(status_code=403, detail=f"当前角色（{user_module_role(user)}）没有「{button_key}」操作权限")


def can_access_menu(user: User, menu_key: str, db: Session = None) -> bool:
    """用户是否可见某个菜单（超管恒为真）。"""
    if is_admin(user):
        return True
    from .permissions import user_permissions

    perms = user_permissions(user, db)
    return menu_key in perms["menus"]


def user_module_role(user: User) -> str:
    from .permissions import user_module_role as _resolve

    return _resolve(user)


def require_button(button_key: str):
    """生成一个 FastAPI 依赖：校验按钮权限，不足直接 403。"""

    def _dependency(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> User:
        require_permission(user, button_key, db)
        return user

    return _dependency

