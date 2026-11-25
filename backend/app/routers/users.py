"""用户管理：仅超管可访问。

覆盖账号的增删改查、角色与权限位调整、密码重置、启停用。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user, hash_password, require_permission
from ..database import get_db
from ..models import Character, Production, User
from ..permissions import (
    DEFAULT_MODULE_ROLE,
    ROLE_KEYS,
    ROLE_TO_MODULE,
    apply_role_preset,
)
from ..schemas import (
    PasswordResetIn,
    UserCreateIn,
    UserListItem,
    UserOut,
    UserUpdateIn,
)

router = APIRouter(prefix="/users", tags=["users"])

VALID_ROLES = {"admin", "creator", "viewer"}


def require_admin(user: User, db: Session = None) -> None:
    """用户管理准入：具备 users.manage 按钮权限即可（超管 / super 角色恒有）。"""
    require_permission(user, "users.manage", db)


def _to_item(user: User, db: Session) -> UserListItem:
    base = UserOut.model_validate(user).model_dump()
    base["production_count"] = db.query(Production).filter(Production.owner_id == user.id).count()
    base["character_count"] = db.query(Character).filter(Character.owner_id == user.id).count()
    return UserListItem(**base)


@router.get("", response_model=list)
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user, db)
    users = db.query(User).order_by(User.id.asc()).all()
    return [_to_item(u, db) for u in users]


@router.post("", response_model=UserOut)
def create_user(data: UserCreateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user, db)
    username = (data.username or "").strip()
    password = data.password or ""
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少 3 个字符")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    if data.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"角色必须是 {'/'.join(sorted(VALID_ROLES))} 之一")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已被占用")

    # 新的统一入口：前端只提交「角色权限」(module_role)，由角色决定菜单、按钮与功能限制。
    # 未显式传 module_role 时按旧 role 兼容映射，保证老客户端与既有调用不受影响。
    role_key_explicit = "module_role" in data.model_fields_set
    role_key = data.module_role if role_key_explicit else ROLE_TO_MODULE.get(data.role, DEFAULT_MODULE_ROLE)
    if role_key not in ROLE_KEYS:
        raise HTTPException(status_code=400, detail=f"角色权限必须是 {'/'.join(ROLE_KEYS)} 之一")

    new_user = User(
        username=username,
        password_hash=hash_password(password),
        nickname=(data.nickname or "").strip(),
        role=data.role,
        can_create=data.can_create if data.role != "viewer" else False,
        can_view_all=data.can_view_all,
        module_role=role_key,
        phone=(data.phone or "").strip(),
        email=(data.email or "").strip(),
        is_active=True,
    )
    if role_key_explicit:
        apply_role_preset(new_user, role_key)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserOut.model_validate(new_user)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_admin(user, db)
    target = db.query(User).get(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 统一角色权限入口：提交 module_role 即以它为准，角色与功能限制由它派生
    if "module_role" in data.model_fields_set:
        if data.module_role not in ROLE_KEYS:
            raise HTTPException(status_code=400, detail=f"角色权限必须是 {'/'.join(ROLE_KEYS)} 之一")
        if (
            target.role == "admin"
            and data.module_role != "super"
            and db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count() <= 1
        ):
            raise HTTPException(status_code=400, detail="系统至少需要保留一个启用中的超管账号")
        apply_role_preset(target, data.module_role)

    # 旧 role 字段仅作兼容：未提交 module_role 时仍按原逻辑处理
    if data.role is not None:
        if data.role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail="角色不合法")
        if (
            target.role == "admin"
            and data.role != "admin"
            and db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count() <= 1
        ):
            raise HTTPException(status_code=400, detail="系统至少需要保留一个启用中的超管账号")
        target.role = data.role
        if data.role == "admin":
            target.can_create = True
            target.can_view_all = True
        elif data.role == "viewer" and data.can_create is None:
            target.can_create = False
        if "module_role" not in data.model_fields_set:
            target.module_role = ROLE_TO_MODULE.get(data.role, DEFAULT_MODULE_ROLE)

    if data.can_create is not None:
        target.can_create = data.can_create
    if data.can_view_all is not None:
        target.can_view_all = data.can_view_all
    if data.nickname is not None:
        target.nickname = data.nickname.strip()
    if data.phone is not None:
        target.phone = data.phone.strip()
    if data.email is not None:
        target.email = data.email.strip()
    if data.is_active is not None:
        if target.id == user.id and not data.is_active:
            raise HTTPException(status_code=400, detail="不能停用当前登录的账号")
        if (
            not data.is_active
            and target.role == "admin"
            and db.query(User).filter(User.role == "admin", User.is_active == True).count() <= 1
        ):
            raise HTTPException(status_code=400, detail="系统至少需要保留一个启用中的超管账号")
        target.is_active = data.is_active

    db.commit()
    db.refresh(target)
    return UserOut.model_validate(target)


@router.post("/{user_id}/reset-password", response_model=UserOut)
def reset_password(
    user_id: int,
    data: PasswordResetIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_admin(user, db)
    target = db.query(User).get(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    new_password = data.new_password or ""
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    target.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(target)
    return UserOut.model_validate(target)


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user, db)
    target = db.query(User).get(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录的账号")
    if target.role == "admin":
        remaining = db.query(User).filter(User.role == "admin", User.id != user_id).count()
        if remaining == 0:
            raise HTTPException(status_code=400, detail="系统至少需要保留一个超管账号")
    db.delete(target)
    db.commit()
    return {"ok": True}
