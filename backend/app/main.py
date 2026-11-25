import logging
import os

import jwt
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .auto_update_service import start_auto_update_scheduler
from .database import Base, SessionLocal, UPLOAD_DIR, engine, run_migrations
from .models import (
    Category,
    Character,
    CharacterImage,
    Material,
    MaterialLibrary,
    OperationLog,
    Production,
    PublishAccount,
    User,
)
from .routers import (
    auth,
    auto_update,
    categories,
    characters,
    dashboard,
    douyin_collect,
    ideas,
    material_libraries,
    operation_logs,
    productions,
    publish_accounts,
    publish_stats,
    roles,
    settings,
    tags,
    upload,
    users,
)
from .auth import ALGORITHM, SECRET_KEY, hash_password

app = FastAPI(title="AI视频资产管理")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(ideas.router, prefix=API_PREFIX)
app.include_router(productions.router, prefix=API_PREFIX)
app.include_router(publish_stats.router, prefix=API_PREFIX)
app.include_router(publish_accounts.router, prefix=API_PREFIX)
app.include_router(tags.router, prefix=API_PREFIX)
app.include_router(douyin_collect.router, prefix=API_PREFIX)
app.include_router(categories.router, prefix=API_PREFIX)
app.include_router(characters.router, prefix=API_PREFIX)
app.include_router(material_libraries.router, prefix=API_PREFIX)
app.include_router(upload.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(roles.router, prefix=API_PREFIX)
app.include_router(settings.router, prefix=API_PREFIX)
app.include_router(auto_update.router, prefix=API_PREFIX)
app.include_router(operation_logs.router, prefix=API_PREFIX)

# ---------------- 操作日志：自动记录所有写操作 ----------------
_LOG_MODULES = (
    ("/operation-logs", "操作日志"),
    ("/publish-accounts", "我的账号"),
    ("/auto-update", "自动更新"),
    ("/publish-stats", "发布数据"),
    ("/material-libraries", "素材共享"),
    ("/douyin", "抖音采集"),
    ("/productions", "视频创作"),
    ("/characters", "人物资产"),
    ("/categories", "配置中心"),
    ("/ideas", "创意灵感"),
    ("/settings", "配置中心"),
    ("/tags", "配置中心"),
    ("/users", "用户管理"),
    ("/roles", "角色权限"),
    ("/upload", "文件上传"),
    ("/auth", "账号认证"),
)


def _log_module(path: str) -> str:
    for prefix, name in _LOG_MODULES:
        if path.startswith(API_PREFIX + prefix) or path == API_PREFIX + prefix:
            return name
    return "其他"


_LOG_RESOURCES = {
    "ideas": "创意",
    "productions": "视频制作",
    "publish-stats": "发布数据",
    "publish-accounts": "发布账号",
    "auto-update": "自动更新",
    "characters": "人物资产",
    "material-libraries": "素材",
    "categories": "视频分类",
    "tags": "话题标签",
    "users": "用户",
    "roles": "角色权限",
    "settings": "系统配置",
    "upload": "图片文件",
    "auth": "账号",
    "douyin": "抖音数据",
}


def _log_action(method: str, path: str = "") -> str:
    # 采集 / 同步 / 重置这类动作不是「新增」，统一记为「执行」
    if "/douyin/" in path or path.endswith("/sync") or path.endswith("/reset") or "/auth/" in path:
        return "执行"
    return {
        "POST": "新增",
        "PUT": "编辑",
        "PATCH": "编辑",
        "DELETE": "删除",
    }.get(method, "执行")


def _log_summary(method: str, path: str) -> str:
    """把接口路径翻译成人话：新增了「创意」、上传了「图片文件」……"""
    parts = path[len(API_PREFIX) + 1:].strip("/").split("/") if path.startswith(API_PREFIX + "/") else []
    resource = parts[0] if parts else ""
    label = _LOG_RESOURCES.get(resource, "数据")
    ident = parts[1] if len(parts) > 1 and parts[1].isdigit() else ""

    # 抖音采集按子动作细分，日志里一眼能看出做了什么
    if resource == "douyin":
        sub = parts[1] if len(parts) > 1 else ""
        label = {
            "login": "抖音扫码登录",
            "videos": "抖音作品列表",
            "account": "抖音账号资料",
            "stats": "抖音作品数据",
            "config": "抖音采集配置",
        }.get(sub, "抖音数据")
    if resource == "auth" and path.endswith("/password"):
        label = "登录密码"
    if resource == "settings" and path.endswith("/reset"):
        return "恢复了默认配置"
    if resource == "tags" and path.endswith("/sync"):
        return "同步了话题标签引用计数"
    if resource == "publish-stats" and path.endswith("/import-douyin"):
        return "导入了抖音作品"

    target = f"{label} #{ident}" if ident else label
    if resource == "upload":
        verb = "上传了"
    elif method == "POST" and resource == "douyin":
        verb = "采集了"
    elif method == "POST":
        verb = "新增了"
    elif method in ("PUT", "PATCH"):
        verb = "修改了"
    elif method == "DELETE":
        verb = "删除了"
    else:
        verb = "执行了"
    return f"{verb}「{target}」"


@app.middleware("http")
async def audit_operation(request: Request, call_next):
    path = request.url.path
    to_log = (
        request.method in ("POST", "PUT", "PATCH", "DELETE")
        and path.startswith(API_PREFIX + "/")
        and not path.startswith(API_PREFIX + "/operation-logs")
        # 登录时还没有 token，记录下来也只有空操作人，属于噪音
        and path != API_PREFIX + "/auth/login"
    )
    response = await call_next(request)
    if not to_log:
        return response
    try:
        username = ""
        user_id = None
        authz = request.headers.get("authorization", "")
        if authz.lower().startswith("bearer "):
            payload = jwt.decode(authz[7:].strip(), SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("uid")
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first() if user_id else None
                if user:
                    username = user.display_name
            finally:
                db.close()
        resource = path[len(API_PREFIX) + 1:].strip("/").split("/")
        db = SessionLocal()
        try:
            db.add(
                OperationLog(
                    module=_log_module(path),
                    action=_log_action(request.method, path),
                    target=(resource[0] if resource else "")[:120],
                    summary=_log_summary(request.method, path)[:300],
                    method=request.method,
                    path=path[:300],
                    username=username,
                    user_id=user_id,
                    status_code=response.status_code,
                    ip=(request.client.host if request.client else "")[:60],
                )
            )
            db.commit()
        finally:
            db.close()
    except Exception as exc:  # 日志失败不影响业务
        logging.warning("记录操作日志失败: %s", exc)
    return response


os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

DEFAULT_CATEGORIES = ["舞蹈", "段子", "颜值", "剧情", "其他"]
CATEGORY_COLORS = ["#7b62c9", "#e05c4b", "#4a7cc4", "#3da377", "#d08a3e"]

# 素材共享默认库：资产库重组后由「人物资产 + 素材共享」承载
DEFAULT_MATERIAL_LIBRARIES = [
    {"name": "人物库", "color": "#4a7cc4", "sort": 0, "legacy": "character"},
    {"name": "服装库", "color": "#7b62c9", "sort": 1, "legacy": "costume"},
    {"name": "场景库", "color": "#3da377", "sort": 2, "legacy": "scene"},
]

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    run_migrations()
    db = SessionLocal()
    try:
        if not db.query(Category).count():
            for i, name in enumerate(DEFAULT_CATEGORIES):
                db.add(Category(name=name, color=CATEGORY_COLORS[i % len(CATEGORY_COLORS)],
                                sort=i, owner_id=None))
        # 素材共享：首次启动写入默认素材库，并把历史场景 / 服装资产迁移为共享素材
        if not db.query(MaterialLibrary).count():
            created_libs = {}
            for item in DEFAULT_MATERIAL_LIBRARIES:
                lib = MaterialLibrary(
                    name=item["name"], color=item["color"], sort=item["sort"], owner_id=None
                )
                db.add(lib)
                db.flush()
                created_libs[item["legacy"]] = lib.id
            db.flush()
            legacy = db.query(Character).filter(Character.asset_type.in_(["scene", "costume"])).all()
            for c in legacy:
                lib_id = created_libs.get(c.asset_type or "costume")
                if not lib_id:
                    continue
                db.add(Material(
                    library_id=lib_id,
                    name=c.name or "",
                    description=c.description or "",
                    tags=list(c.tags or []),
                    images=[
                        {"file_path": img.file_path, "sort": img.sort or i}
                        for i, img in enumerate(db.query(CharacterImage)
                                                .filter(CharacterImage.character_id == c.id)
                                                .order_by(CharacterImage.sort).all())
                    ],
                    owner_id=c.owner_id,
                ))
        # 发布账号：不预置演示账号，清空后的交付包由使用者自行添加
        # 已完成（已发布）的历史视频按发布平台自动归属到对应账号
        accounts = db.query(PublishAccount).all()
        if accounts:
            for production in db.query(Production).filter(Production.status.in_(["已发布", "已完成"])).all():
                if production.publish_account_id:
                    continue
                matched = next(
                    (a for a in accounts if a.platform and a.platform == production.publish_platform),
                    None,
                )
                if matched:
                    production.publish_account_id = matched.id
        # 确保存在超管账号 admin / admin123456
        if not db.query(User).filter(User.role == "admin").count():
            db.add(
                User(
                    username="admin",
                    password_hash=hash_password("admin123456"),
                    nickname="超级管理员",
                    role="admin",
                    can_create=True,
                    can_view_all=True,
                    is_active=True,
                )
            )
            db.commit()
            print("[INIT] 超管账号已创建: admin / admin123456")
        db.commit()
    finally:
        db.close()
    # 每日自动更新调度：读取配置中心时间，在线账号更新资料 + 快照 + 发布数据
    start_auto_update_scheduler()


@app.get("/api/health")
def health():
    return {"ok": True}
