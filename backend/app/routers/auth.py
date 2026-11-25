from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import (
    create_token,
    get_current_user,
    hash_password,
    is_admin,
    verify_password,
)
from ..database import get_db
from ..models import User
from ..schemas import (
    AvatarIn,
    LoginIn,
    PasswordChangeIn,
    ProfileIn,
    RegisterIn,
    TokenOut,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# 角色预设：角色决定默认权限位，可在用户管理里再单独微调
ROLE_PRESETS = {
    "admin": {"can_create": True, "can_view_all": True},
    "creator": {"can_create": True, "can_view_all": True},
    "viewer": {"can_create": False, "can_view_all": True},
}


@router.post("/register", response_model=TokenOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    username = (data.username or "").strip()
    password = data.password or ""
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少 3 个字符")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已被占用")

    preset = ROLE_PRESETS["creator"]
    user = User(
        username=username,
        password_hash=hash_password(password),
        nickname=(data.nickname or "").strip(),
        role="creator",
        can_create=preset["can_create"],
        can_view_all=preset["can_view_all"],
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": create_token(user.id), "user": UserOut.model_validate(user)}


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == (data.username or "").strip()).first()
    if not user or not verify_password(data.password or "", user.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="该账号已被停用，请联系管理员")
    user.last_login_at = datetime.now()
    db.commit()
    db.refresh(user)
    return {"token": create_token(user.id), "user": UserOut.model_validate(user)}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.get("/permissions", response_model=dict)
def my_permissions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """当前用户的模块角色与权限（菜单 + 按钮），前端据此过滤菜单与按钮。"""
    from ..permissions import user_permissions

    return user_permissions(user, db)


# ---------------- 个人中心 ----------------
@router.put("/profile", response_model=UserOut)
def update_profile(data: ProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """修改自己的资料：昵称 / 手机 / 邮箱。"""
    user.nickname = (data.nickname or "").strip()
    user.phone = (data.phone or "").strip()
    user.email = (data.email or "").strip()
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/password", response_model=UserOut)
def change_password(
    data: PasswordChangeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """修改自己的密码：需校验旧密码。"""
    if not verify_password(data.old_password or "", user.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    new_password = data.new_password or ""
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    if new_password == data.old_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.put("/avatar", response_model=UserOut)
def update_avatar(
    data: AvatarIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """修改自己的头像（传入上传后返回的文件路径）。"""
    user.avatar = (data.avatar or "").strip()
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/sessions", response_model=list)
def sessions(user: User = Depends(get_current_user)):
    """当前账号的登录信息（供个人中心展示）。"""
    return [
        {
            "username": user.username,
            "role": user.role,
            "last_login_at": user.last_login_at,
            "created_at": user.created_at,
            "is_admin": is_admin(user),
        }
    ]
