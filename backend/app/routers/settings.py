"""系统配置：站点信息、默认值、提示词模板等。

读：所有登录用户可读（前端需要默认值）。
写：仅超管。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_permission
from ..database import get_db
from ..models import Production, SystemSetting, User
from ..schemas import SettingOut, SettingUpdateIn

router = APIRouter(prefix="/settings", tags=["settings"])

# 系统默认配置（首次读取时落库，后续以库中值为准）
DEFAULT_SETTINGS = {
    "site": {
        "name": "视频资产管理",
        "subtitle": "Assets Console",
        "logo": "",
        "footer": "v1.3 · 本地部署",
    },
    "defaults": {
        "platform": "硬核",
        "priority": 2,
        "plan_status": "待制作",
        "production_status": "制作中",
        "scope": "all",
    },
    "prompt": {
        "segments": ["人物背景", "场景背景", "人物着装", "镜头背景"],
        "template": {
            "人物背景": "",
            "场景背景": "",
            "人物着装": "",
            "镜头背景": "",
        },
    },
    "douyin": {
        "auto_resolve": True,
        "auto_parse_title": True,
        "reject_duplicate": True,
        # 发布数据页拉取作品列表时，已导入作品默认勾选；仅勾选的才写入/更新。
        "auto_check_imported": True,
    },
    # 自动更新机制：每天到点更新在线账号资料、写入账号快照，并同步发布数据作品
    "auto_update": {
        "enabled": True,
        "hour": 8,
        "minute": 0,
        "video_limit": 20,
        "sync_publish_data": True,
    },
    "security": {
        "password_min_length": 6,
        "session_days": 7,
    },
    # 投票规则：每人每天投票次数上限（创意灵感点赞投票）
    "vote": {
        "daily_limit": 5,
    },
    "welcome": {
        "city": "深圳",
        "latitude": None,
        "longitude": None,
    },
    # 制作平台选项（制作记录 / 列表筛选 / 概览分布共用）
    # image 为上传的图片 URL（不再定死 Element Plus 图标）；每项 display 保留兼容，
    # 实际展示方式由模块级 platform_display 统一控制
    "platforms": [
        {"name": "硬核", "color": "#4a7cc4", "image": "", "display": "full"},
        {"name": "小云雀", "color": "#7b62c9", "image": "", "display": "full"},
        {"name": "三方平台", "color": "#3da377", "image": "", "display": "full"},
    ],
    # 发布平台选项（成品页标记已发布时选择，与制作平台分开）
    "publish_platforms": [
        {"name": "抖音", "color": "#e05c4b", "image": "", "display": "full"},
        {"name": "小红书", "color": "#ff7b6b", "image": "", "display": "full"},
        {"name": "B站", "color": "#4a7cc4", "image": "", "display": "full"},
        {"name": "视频号", "color": "#3da377", "image": "", "display": "full"},
    ],
    # 发布账号选项（发布数据录入时选择）
    "publish_accounts": [],
    # 三个模块各自的统一显示方式：full 全显 / label 标签 / icon 图标
    # 集中存于 platform_display（兼容历史键名），作用于各模块下全部选项，不再逐项设置
    "platform_display": {
        "mode": "full",     # 兼容旧字段
        "category": "full", # 视频分类
        "platform": "full", # 制作平台
        "publish": "full",  # 发布平台
    },
    # 角色权限自定义矩阵（覆盖内置定义，见 permissions.py）
    "role_permissions": {},
}


def normalize_auto_update(value) -> dict:
    """校验并补齐自动更新配置；无效值回退到默认，避免定时任务读脏数据。"""
    raw = value if isinstance(value, dict) else {}
    default = DEFAULT_SETTINGS["auto_update"]
    try:
        hour = int(raw.get("hour", default["hour"]))
    except (TypeError, ValueError):
        hour = default["hour"]
    try:
        minute = int(raw.get("minute", default["minute"]))
    except (TypeError, ValueError):
        minute = default["minute"]
    try:
        video_limit = int(raw.get("video_limit", default["video_limit"]))
    except (TypeError, ValueError):
        video_limit = default["video_limit"]
    return {
        "enabled": bool(raw.get("enabled", default["enabled"])),
        "hour": hour if 0 <= hour <= 23 else default["hour"],
        "minute": minute if 0 <= minute <= 59 else default["minute"],
        "video_limit": video_limit if 1 <= video_limit <= 100 else default["video_limit"],
        "sync_publish_data": bool(raw.get("sync_publish_data", default["sync_publish_data"])),
    }


def _ensure_defaults(db: Session) -> None:
    existing = {row.key for row in db.query(SystemSetting).all()}
    for key, value in DEFAULT_SETTINGS.items():
        if key not in existing:
            db.add(SystemSetting(key=key, value=value))
    db.commit()
    _backfill_platform_icons(db)


# 平台默认图标：制作平台与发布平台各自一套，配置缺失时按名称就近匹配
_PLATFORM_ICON_BY_NAME = {
    "硬核": "Monitor",
    "小云雀": "MagicStick",
    "三方平台": "Connection",
    "抖音": "Promotion",
    "小红书": "Star",
    "B站": "VideoCamera",
    "视频号": "ChatDotRound",
}


def _backfill_platform_icons(db: Session) -> None:
    """为已保存的平台配置补齐新字段：image（上传图片）与 display（每项独立展示方式）。

    旧配置里可能只有固定 Element 图标名 icon，保留该字段兼容，但前端不再依赖它；
    image / display 只补缺失项，不覆盖用户已上传的图片与已选展示方式。
    """
    changed = False
    for key in ("platforms", "publish_platforms"):
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not row or not isinstance(row.value, list):
            continue
        updated = []
        dirty = False
        for item in row.value:
            if isinstance(item, dict):
                new_item = dict(item)
                if "image" not in new_item:
                    new_item["image"] = ""
                    dirty = True
                if new_item.get("display") not in ("full", "label", "icon"):
                    new_item["display"] = "full"
                    dirty = True
                updated.append(new_item)
                continue
            updated.append(item)
        if dirty:
            row.value = updated
            changed = True
    if changed:
        db.commit()


def _all_settings(db: Session) -> dict:
    _ensure_defaults(db)
    rows = db.query(SystemSetting).all()
    data = {
        key: (dict(value) if isinstance(value, dict) else list(value) if isinstance(value, list) else value)
        for key, value in DEFAULT_SETTINGS.items()
    }
    for row in rows:
        # 内部运行标记不暴露给前端
        if row.key.startswith("_auto_update_"):
            continue
        value = row.value
        if isinstance(value, dict):
            merged = dict(data.get(row.key, {}))
            merged.update(value)
            data[row.key] = merged
        else:
            data[row.key] = value
    data["auto_update"] = normalize_auto_update(data.get("auto_update"))
    return data


@router.get("")
def get_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """读取全部配置（所有登录用户可读）。"""
    return _all_settings(db)


@router.delete("/option")
def delete_option(
    key: str,
    name: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除配置选项（仅超管）：制作平台 / 发布平台。

    已被业务记录引用的选项直接拒绝删除，避免留下悬空的平台名。
    """
    require_permission(user, "settings.manage", db)
    if key not in ("platforms", "publish_platforms"):
        raise HTTPException(status_code=400, detail="该配置项不支持删除选项")
    target = (name or "").strip()
    if not target:
        raise HTTPException(status_code=400, detail="平台名称不能为空")

    used = db.query(Production).filter(Production.platform == target).count()
    if key == "publish_platforms":
        used += db.query(Production).filter(Production.publish_platform == target).count()
    if used:
        raise HTTPException(status_code=400, detail=f"该平台已被 {used} 条记录使用，无法删除")

    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not row or not isinstance(row.value, list):
        raise HTTPException(status_code=404, detail="平台配置不存在")
    updated = []
    for p in row.value:
        pname = (p.get("name") if isinstance(p, dict) else p) or ""
        if str(pname).strip() != target:
            updated.append(p)
    if len(updated) == len(row.value):
        raise HTTPException(status_code=404, detail="平台不存在")
    row.value = updated
    db.commit()
    return {"ok": True, "options": updated}


@router.get("/{key}")
def get_setting(key: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    data = _all_settings(db)
    if key not in data:
        raise HTTPException(status_code=404, detail="配置项不存在")
    return {key: data[key]}


@router.put("")
def update_setting(
    data: SettingUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新单个配置项（仅超管）。"""
    require_permission(user, "settings.manage", db)
    if not data.key:
        raise HTTPException(status_code=400, detail="配置键不能为空")
    if data.key not in DEFAULT_SETTINGS:
        raise HTTPException(status_code=400, detail="未知的配置项")

    row = db.query(SystemSetting).filter(SystemSetting.key == data.key).first()
    if not row:
        row = SystemSetting(key=data.key, value=data.value if data.value is not None else {})
        db.add(row)
    else:
        # dict 配置做字段级合并；list 等其它类型整体覆盖
        if isinstance(row.value, dict) and isinstance(data.value, dict):
            merged = dict(row.value)
            merged.update(data.value)
            row.value = merged
        else:
            row.value = data.value if data.value is not None else {}
    if data.key == "auto_update":
        row.value = normalize_auto_update(row.value)
    db.commit()
    db.refresh(row)
    return SettingOut.model_validate(row)


@router.post("/reset")
def reset_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """恢复默认配置（仅超管）。"""
    require_permission(user, "settings.manage", db)
    db.query(SystemSetting).delete()
    db.commit()
    _ensure_defaults(db)
    return _all_settings(db)
