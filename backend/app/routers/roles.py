"""角色权限：模块角色的菜单 / 按钮权限矩阵（仅超管可写）。

- GET  /roles                     读取角色列表与权限矩阵（登录用户可读自己那份）
- GET  /roles/mine                当前用户的有效权限（菜单 + 按钮）
- PUT  /roles/{role_key}          保存自定义权限矩阵（仅超管）
- PUT  /roles/users/{user_id}     调整用户的模块角色（仅超管）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_permission
from ..database import get_db
from ..models import SystemSetting, User
from ..permissions import (
    BUTTON_DEFS,
    MENU_DEFS,
    ROLE_DEFS,
    ROLE_KEYS,
    default_role_permissions,
    apply_role_preset,
    load_role_permissions,
    user_permissions,
)
from ..schemas import RoleAssignIn, RolePermissionUpdateIn, RolePermissionOut

router = APIRouter(prefix="/roles", tags=["roles"])


def require_admin(user: User, db: Session = None) -> None:
    """角色权限管理准入：具备 roles.manage 按钮权限即可。"""
    require_permission(user, "roles.manage", db)


@router.get("", response_model=list[RolePermissionOut])
def list_roles(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """角色列表与权限矩阵（读）。"""
    matrix = load_role_permissions(db)
    result = []
    for defn in ROLE_DEFS:
        cfg = matrix.get(defn["key"]) or {}
        result.append(
            RolePermissionOut(
                key=defn["key"],
                name=cfg.get("name") or defn["name"],
                desc=cfg.get("desc") or defn["desc"],
                builtin=True,
                menus=list(cfg.get("menus") or []),
                buttons=list(cfg.get("buttons") or []),
            )
        )
    return result


@router.get("/mine", response_model=dict)
def my_permissions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """当前用户的有效权限（前端据此过滤菜单与按钮）。"""
    return user_permissions(user, db)


@router.get("/catalog", response_model=dict)
def permission_catalog(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """可勾选项目录：菜单定义 + 按钮定义。"""
    return {"menus": MENU_DEFS, "buttons": BUTTON_DEFS}


@router.put("/{role_key}", response_model=RolePermissionOut)
def update_role(
    role_key: str,
    data: RolePermissionUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """保存单个角色的自定义权限（仅超管）。

    「超管」角色的菜单与按钮恒为全量，不可被裁剪，避免把系统锁死。
    """
    require_admin(user, db)
    if role_key not in ROLE_KEYS:
        raise HTTPException(status_code=404, detail="角色不存在")

    matrix = load_role_permissions(db)
    base = default_role_permissions()
    current = matrix.get(role_key) or base[role_key]

    menus = list(data.menus if data.menus is not None else current["menus"])
    buttons = list(data.buttons if data.buttons is not None else current["buttons"])
    if role_key == "super":
        menus = list(base["super"]["menus"])
        buttons = list(base["super"]["buttons"])

    payload = {
        role_key: {
            "name": (data.name or current["name"]),
            "desc": (data.desc if data.desc is not None else current["desc"]),
            "menus": menus,
            "buttons": buttons,
        }
    }
    row = db.query(SystemSetting).filter(SystemSetting.key == "role_permissions").first()
    if row:
        merged = dict(row.value) if isinstance(row.value, dict) else {}
        merged.update(payload)
        row.value = merged
    else:
        db.add(SystemSetting(key="role_permissions", value=payload))
    db.commit()
    return RolePermissionOut(
        key=role_key,
        name=payload[role_key]["name"],
        desc=payload[role_key]["desc"],
        builtin=True,
        menus=payload[role_key]["menus"],
        buttons=payload[role_key]["buttons"],
    )


@router.put("/users/{user_id}", response_model=dict)
def assign_user_role(
    user_id: int,
    data: RoleAssignIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """调整用户的模块角色（仅超管）。"""
    require_admin(user, db)
    if data.module_role not in ROLE_KEYS:
        raise HTTPException(status_code=400, detail=f"角色必须是 {'/'.join(ROLE_KEYS)} 之一")
    target = db.query(User).get(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if (
        target.role == "admin"
        and data.module_role != "super"
        and db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count() <= 1
    ):
        raise HTTPException(status_code=400, detail="系统至少需要保留一个启用中的超管账号")
    apply_role_preset(target, data.module_role)
    db.commit()
    db.refresh(target)
    return {"ok": True, "user_id": target.id, "module_role": target.module_role}
