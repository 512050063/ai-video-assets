"""模块角色与权限矩阵。

设计
----
系统存在两套互补的权限概念：

1. **数据权限**（users 表）
   - `role`：超管 / 创作者 / 只读，决定「能做什么级别的写操作」「能否管理他人数据」
   - `can_create` / `can_view_all`：把普通用户降级为只读或限定可见范围

2. **模块角色**（users.module_role）
   - 决定「能看到哪些菜单」「能按哪些按钮」，即岗位分工
   - 取值：super（超管）/ inspiration（灵感）/ production（创作）/ operation（运营）

模块角色矩阵定义在 `DEFAULT_ROLE_PERMISSIONS`，可由超管在「角色权限」页保存自定义覆盖，
覆盖结果存在 system_settings 的 `role_permissions` 键中。

菜单键与前端路由一一对应（frontend/src/router/index.js 的 name），
按钮键采用 `模块.动作` 形式，前端通过 `v-permission` 指令 / `auth.can()` 使用。
"""

# ---------------- 菜单（模块）定义 ----------------
# key 与前端路由 name 保持一致，前端据此过滤侧边栏与拦截路由
MENU_DEFS = [
    {"key": "dashboard", "title": "首页", "group": "概览"},
    {"key": "ideas", "title": "创意灵感", "group": "创作流程"},
    {"key": "productions", "title": "视频创作", "group": "创作流程"},
    {"key": "publish-stats", "title": "数据中心", "group": "创作流程"},
    {"key": "publish-accounts", "title": "我的账号", "group": "我的"},
    {"key": "characters", "title": "人物资产", "group": "资产库"},
    {"key": "materials", "title": "素材共享", "group": "资产库"},
    {"key": "users", "title": "用户管理", "group": "系统"},
    {"key": "roles", "title": "角色权限", "group": "系统"},
    {"key": "settings", "title": "配置中心", "group": "系统"},
]

MENU_KEYS = [m["key"] for m in MENU_DEFS]

# ---------------- 按钮（动作）定义 ----------------
# 按模块分组，便于前端按模块渲染权限勾选表
BUTTON_DEFS = [
    {"key": "ideas.create", "label": "收集创意", "module": "ideas"},
    {"key": "ideas.edit", "label": "编辑创意", "module": "ideas"},
    {"key": "ideas.delete", "label": "删除创意", "module": "ideas"},
    {"key": "ideas.schedule", "label": "排期为计划", "module": "ideas"},
    {"key": "ideas.vote", "label": "点赞投票", "module": "ideas"},
    {"key": "ideas.comment", "label": "发表评论", "module": "ideas"},
    {"key": "ideas.want", "label": "认领我想做", "module": "ideas"},
    {"key": "ideas.want.assign", "label": "指定认领人", "module": "ideas"},
    {"key": "productions.create", "label": "新建制作", "module": "productions"},
    {"key": "productions.edit", "label": "编辑制作", "module": "productions"},
    {"key": "productions.delete", "label": "删除制作", "module": "productions"},
    {"key": "publish-stats.create", "label": "录入数据", "module": "publish-stats"},
    {"key": "publish-stats.edit", "label": "编辑数据", "module": "publish-stats"},
    {"key": "publish-stats.delete", "label": "删除数据", "module": "publish-stats"},
    {"key": "publish-accounts.create", "label": "新建账号", "module": "publish-accounts"},
    {"key": "publish-accounts.edit", "label": "编辑账号", "module": "publish-accounts"},
    {"key": "publish-accounts.delete", "label": "删除账号", "module": "publish-accounts"},
    {"key": "characters.create", "label": "新建人物资产", "module": "characters"},
    {"key": "characters.edit", "label": "编辑人物资产", "module": "characters"},
    {"key": "characters.delete", "label": "删除人物资产", "module": "characters"},
    {"key": "materials.create", "label": "新建素材", "module": "materials"},
    {"key": "materials.edit", "label": "编辑素材", "module": "materials"},
    {"key": "materials.delete", "label": "删除素材", "module": "materials"},
    {"key": "users.manage", "label": "管理用户", "module": "users"},
    {"key": "settings.manage", "label": "修改配置", "module": "settings"},
    {"key": "roles.manage", "label": "管理角色权限", "module": "roles"},
]

BUTTON_KEYS = [b["key"] for b in BUTTON_DEFS]

# ---------------- 角色定义 ----------------
# name 为岗位名称，desc 说明分工，menus / buttons 为该角色的可见菜单与可用按钮
ROLE_DEFS = [
    {
        "key": "super",
        "name": "超管",
        "desc": "全量权限：所有菜单与按钮，负责系统配置与人员管理",
        "menus": list(MENU_KEYS),
        "buttons": list(BUTTON_KEYS),
    },
    {
        "key": "inspiration",
        "name": "灵感",
        "desc": "负责创意收集与讨论：收集创意、评论投票、维护人物与素材资产",
        "menus": ["dashboard", "ideas", "characters", "materials"],
        "buttons": [
            "ideas.create", "ideas.edit", "ideas.vote", "ideas.comment",
            "characters.create", "characters.edit", "characters.delete",
            "materials.create", "materials.edit", "materials.delete",
        ],
    },
    {
        "key": "production",
        "name": "创作",
        "desc": "负责视频生产：认领「我想做」、安排创作排期、制作视频并绑定资产",
        "menus": ["dashboard", "ideas", "productions", "characters", "materials"],
        "buttons": [
            "ideas.vote", "ideas.comment", "ideas.want", "ideas.schedule",
            "productions.create", "productions.edit", "productions.delete",
            "characters.create", "characters.edit",
            "materials.create", "materials.edit",
        ],
    },
    {
        "key": "operation",
        "name": "运营",
        "desc": "负责发布与数据：维护发布账号、录入发布数据、查看数据中心",
        "menus": ["dashboard", "ideas", "publish-stats", "publish-accounts"],
        "buttons": [
            "ideas.vote", "ideas.comment",
            "publish-stats.create", "publish-stats.edit", "publish-stats.delete",
            "publish-accounts.create", "publish-accounts.edit", "publish-accounts.delete",
        ],
    },
]

ROLE_KEYS = [r["key"] for r in ROLE_DEFS]
ROLE_MAP = {r["key"]: r for r in ROLE_DEFS}
DEFAULT_MODULE_ROLE = "production"

# 兼容旧数据：role 为 admin 的账号默认落在「超管」模块角色
ROLE_TO_MODULE = {
    "admin": "super",
    "creator": "production",
    "viewer": "operation",
}

# 统一角色权限：module_role（角色权限）是唯一来源，旧字段 role / can_create / can_view_all
# 只作为兼容映射保留。功能限制由「角色权限」页的按钮矩阵控制，不再单独设置开关。
ROLE_PRESETS = {
    "super": {"role": "admin", "can_create": True, "can_view_all": True},
    "inspiration": {"role": "creator", "can_create": True, "can_view_all": True},
    "production": {"role": "creator", "can_create": True, "can_view_all": True},
    "operation": {"role": "creator", "can_create": True, "can_view_all": True},
}


def apply_role_preset(user, role_key: str) -> bool:
    """按角色权限同步用户：设置模块角色并派生旧数据字段与功能限制。"""
    preset = ROLE_PRESETS.get(role_key)
    if not preset:
        return False
    user.module_role = role_key
    user.role = preset["role"]
    user.can_create = preset["can_create"]
    user.can_view_all = preset["can_view_all"]
    return True


def _normalize_menus(value) -> list:
    if not isinstance(value, (list, tuple)):
        return []
    return [m for m in value if m in MENU_KEYS]


def _normalize_buttons(value) -> list:
    if not isinstance(value, (list, tuple)):
        return []
    return [b for b in value if b in BUTTON_KEYS]


def default_role_permissions() -> dict:
    """内置角色矩阵（可被超管自定义覆盖）。"""
    return {
        r["key"]: {
            "name": r["name"],
            "desc": r["desc"],
            "menus": list(r["menus"]),
            "buttons": list(r["buttons"]),
        }
        for r in ROLE_DEFS
    }


def load_role_permissions(db) -> dict:
    """读取角色权限矩阵：数据库自定义覆盖优先，内置定义为兜底。"""
    matrix = default_role_permissions()
    try:
        from .models import SystemSetting

        row = db.query(SystemSetting).filter(SystemSetting.key == "role_permissions").first()
        if row and isinstance(row.value, dict):
            for key, cfg in row.value.items():
                if key not in matrix or not isinstance(cfg, dict):
                    continue
                merged = dict(matrix[key])
                if "menus" in cfg:
                    merged["menus"] = _normalize_menus(cfg["menus"])
                if "buttons" in cfg:
                    merged["buttons"] = _normalize_buttons(cfg["buttons"])
                if "name" in cfg:
                    merged["name"] = str(cfg["name"]) or merged["name"]
                if "desc" in cfg:
                    merged["desc"] = str(cfg["desc"])
                matrix[key] = merged
    except Exception:
        pass
    return matrix


def user_module_role(user) -> str:
    """取用户的模块角色，超管账号恒为 super。"""
    if getattr(user, "role", "") == "admin":
        return "super"
    role = getattr(user, "module_role", "") or ""
    if role in ROLE_MAP:
        return role
    return ROLE_TO_MODULE.get(getattr(user, "role", ""), DEFAULT_MODULE_ROLE)


def user_permissions(user, db=None) -> dict:
    """返回用户的有效权限：{menus: [...], buttons: [...], role, role_name}。"""
    role_key = user_module_role(user)
    matrix = load_role_permissions(db) if db is not None else default_role_permissions()
    cfg = matrix.get(role_key) or default_role_permissions()[DEFAULT_MODULE_ROLE]
    return {
        "role": role_key,
        "role_name": cfg.get("name", role_key),
        "menus": list(cfg.get("menus") or []),
        "buttons": list(cfg.get("buttons") or []),
    }
