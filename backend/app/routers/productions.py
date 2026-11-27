from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from ..auth import ensure_owner, get_current_user, is_admin, require_create, require_permission, scope_filter
from ..database import get_db
from ..models import (
    Category,
    Character,
    Idea,
    Production,
    ProductionAsset,
    ProductionCharacter,
    PublishAccount,
    SystemSetting,
    User,
)
from ..schemas import (
    CharacterLinkOut,
    ProductionDetailOut,
    ProductionIn,
    ProductionListItem,
    ProductionListOut,
)
from ..tag_service import collect_tags, drop_tags
from ..workflow import (
    STATUS_ABANDONED,
    STATUS_MAKING,
    STATUS_PENDING,
    STATUS_PUBLISHED,
    transition,
)

router = APIRouter(prefix="/productions", tags=["productions"])

VALID_STATUSES = {STATUS_MAKING, STATUS_PENDING, STATUS_ABANDONED, STATUS_PUBLISHED}
# 制作记录状态与创意全流程状态一致；发布数据另用 data_status 管理正常/隐藏/删除
# 兜底平台：配置中心可维护任意制作平台，实际校验以 system_settings.platforms 为准
VALID_PLATFORMS = {"硬核", "小云雀", "三方平台"}
VALID_ASSET_TYPES = {"cover", "reference_shot", "output"}


def _valid_platforms(db: Session) -> set:
    """读取配置中心维护的制作平台名称；配置缺失时回退到内置平台。"""
    row = db.query(SystemSetting).filter(SystemSetting.key == "platforms").first()
    if row and isinstance(row.value, list):
        names = {
            item.get("name")
            for item in row.value
            if isinstance(item, dict) and item.get("name")
        }
        if names:
            return names
    return set(VALID_PLATFORMS)


def _sync_characters(db: Session, production: Production, links: list):
    """重建人物绑定关系（多对多）。"""
    production.links.clear()
    # 先把旧绑定落库删除，避免与新绑定撞唯一约束
    db.flush()
    seen = set()
    for i, link in enumerate(links):
        if link.character_id in seen:
            continue
        seen.add(link.character_id)
        ch = db.query(Character).get(link.character_id)
        if not ch:
            raise HTTPException(status_code=400, detail=f"人物不存在: {link.character_id}")
        production.links.append(
            ProductionCharacter(
                character_id=link.character_id,
                role=link.role,
                sort=link.sort if link.sort else i,
            )
        )


def _sync_assets(db: Session, production: Production, assets: list):
    production.assets.clear()
    db.flush()
    for a in assets:
        if a.type not in VALID_ASSET_TYPES:
            raise HTTPException(status_code=400, detail=f"无效附件类型: {a.type}")
        production.assets.append(
            ProductionAsset(type=a.type, file_path=a.file_path, sort=a.sort)
        )


def _apply_in(db: Session, production: Production, data: ProductionIn):
    # 只应用「请求里显式带了」的字段，避免部分更新把没传的字段用默认值覆盖掉
    # （历史 Bug：PUT {"status":"已完成"} 会把 idea_id / 人物绑定 / platform / prompt 全清空）
    provided = data.model_fields_set

    if "status" in provided and data.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"无效状态: {data.status}")
    if "platform" in provided and data.platform and data.platform not in _valid_platforms(db):
        allowed = sorted(_valid_platforms(db))
        raise HTTPException(
            status_code=400, detail=f"无效创作平台: {data.platform}（可选 {'/'.join(allowed)}）"
        )
    if "category_id" in provided and data.category_id is not None and not db.query(Category).get(data.category_id):
        raise HTTPException(status_code=400, detail="分类不存在")
    if "idea_id" in provided and data.idea_id is not None and not db.query(Idea).get(data.idea_id):
        raise HTTPException(status_code=400, detail="创意不存在")
    if "publish_account_id" in provided and data.publish_account_id is not None:
        if not db.query(PublishAccount).get(data.publish_account_id):
            raise HTTPException(status_code=400, detail="发布账号不存在")
    if "owner_id" in provided and data.owner_id is not None:
        if not db.query(User).get(data.owner_id):
            raise HTTPException(status_code=400, detail="制作人不存在")
    # 完成日期不能晚于今天（不能提前完成）；前端日期控件已禁用未来日期，后端兜底防止绕过
    if "completed_at" in provided and data.completed_at is not None:
        if data.completed_at.date() > datetime.now().date():
            raise HTTPException(status_code=400, detail="完成日期不能晚于今天，不能提前完成")

    old_tags = list(production.tags or [])
    for field in (
        "title", "cover", "author", "douyin_url", "video_file", "idea_id", "category_id",
        "platform", "publish_platform", "publish_account_id", "owner_id", "status",
        "reference_url", "duration", "produced_at", "completed_at",
        "published_at", "published_url", "remark",
    ):
        if field in provided:
            setattr(production, field, getattr(data, field))
    if "tags" in provided:
        production.tags = list(data.tags or [])
    if "prompt" in provided:
        production.prompt = [{"seg": p.seg, "text": p.text} for p in data.prompt]
    production.updated_at = datetime.now()

    # 标签库：新增标签自动登记，移除的标签扣减引用
    if "tags" in provided:
        collect_tags(db, production.tags)
        removed = [t for t in old_tags if t not in (production.tags or [])]
        if removed:
            drop_tags(db, removed)

    # ---- 时间信息随状态自动流转 ----
    # 制作中 → 开始时间；待发布/废弃 → 完成时间；已完成 → 发布时间（并补齐完成时间）
    now = datetime.now()
    if production.status == STATUS_MAKING and production.produced_at is None:
        production.produced_at = now
    if production.status in (STATUS_PENDING, STATUS_ABANDONED) and production.completed_at is None:
        production.completed_at = now
    if production.status == "已完成":
        if production.published_at is None:
            production.published_at = now
        if production.completed_at is None:
            production.completed_at = now
    # 状态回退时清空后续时间，保持数据一致
    if production.status != "已完成":
        production.published_at = None
    if production.status == "制作中":
        production.completed_at = None

    # 创意全流程状态联动：制作记录状态直接回写来源创意（权威状态）
    if production.idea_id:
        idea = db.query(Idea).get(production.idea_id)
        if idea and idea.status != production.status:
            idea.status = production.status
            idea.updated_at = now


def _character_links(production: Production) -> list:
    out = []
    for link in production.links:
        ch = link.character
        cover = ch.images[0].file_path if (ch and ch.images) else None
        out.append(
            {
                "id": link.id,
                "character_id": link.character_id,
                "character_name": ch.name if ch else "",
                "character_cover": cover,
                "role": link.role or "",
                "sort": link.sort,
            }
        )
    return out


def _owner_name(production: Production) -> str:
    if not production.owner:
        return "未归属"
    return production.owner.nickname or production.owner.username


def _base_fields(production: Production) -> dict:
    """从 ORM 对象提取基础字段（避开 ORM 关系属性与 schema 的耦合）。"""
    return {
        "id": production.id,
        "title": production.title or "",
        "cover": production.cover or "",
        "author": production.author or "",
        "tags": list(production.tags or []),
        "douyin_url": production.douyin_url or "",
        "video_file": production.video_file or "",
        "idea_id": production.idea_id,
        "category_id": production.category_id,
        "platform": production.platform or "",
        "publish_platform": production.publish_platform or "",
        "publish_account_id": production.publish_account_id,
        "status": production.status or "制作中",
        "published_video_id": production.published_video_id or "",
        "data_status": production.data_status or "正常",
        "prompt": production.prompt or [],
        "reference_url": production.reference_url or "",
        "duration": production.duration,
        "produced_at": production.produced_at,
        "completed_at": production.completed_at,
        "published_at": production.published_at,
        "published_url": production.published_url or "",
        "remark": production.remark or "",
        "created_at": production.created_at,
        "updated_at": production.updated_at,
    }


def _account_name(production: Production) -> Optional[str]:
    if production.publish_account:
        return production.publish_account.name
    return None


def _resolve_author(production: Production) -> str:
    """作者展示：优先制作记录自身 author，历史数据回退到来源创意作者。"""
    if production.author:
        return production.author
    if production.idea and production.idea.author:
        return production.idea.author
    return ""


def _to_item(production: Production, user: User) -> ProductionListItem:
    item = ProductionListItem(**_base_fields(production))
    item.author = _resolve_author(production)
    item.category_name = production.category.name if production.category else None
    item.idea_title = production.idea.title if production.idea else None
    item.idea_douyin_url = production.idea.douyin_url if production.idea else None
    item.characters = _character_links(production)
    item.cover_path = next((a.file_path for a in production.assets if a.type == "cover"), None)
    item.output_path = next((a.file_path for a in production.assets if a.type == "output"), None)
    item.publish_account_name = _account_name(production)
    item.owner_id = production.owner_id
    item.owner_name = _owner_name(production)
    item.is_owner = production.owner_id == user.id
    return item


def _to_detail(production: Production, user: User) -> ProductionDetailOut:
    out = ProductionDetailOut(**_base_fields(production))
    out.author = _resolve_author(production)
    out.category_name = production.category.name if production.category else None
    out.idea_title = production.idea.title if production.idea else None
    out.idea_douyin_url = production.idea.douyin_url if production.idea else None
    out.characters = _character_links(production)
    out.publish_account_name = _account_name(production)
    out.assets = [
        {"id": a.id, "type": a.type, "file_path": a.file_path, "sort": a.sort}
        for a in production.assets
    ]
    out.owner_id = production.owner_id
    out.owner_name = _owner_name(production)
    out.is_owner = production.owner_id == user.id
    return out


@router.get("", response_model=ProductionListOut)
def list_productions(
    keyword: str = "",
    status: str = "",
    stage: str = "",
    platform: str = "",
    character_id: Optional[int] = None,
    scope: str = "all",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Production).options(
        joinedload(Production.idea),
        joinedload(Production.category),
        joinedload(Production.owner),
        joinedload(Production.publish_account),
        selectinload(Production.links).joinedload(ProductionCharacter.character).joinedload(Character.images),
        selectinload(Production.assets),
    )
    q = scope_filter(q, Production, user, scope)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(or_(Production.title.like(like), Production.remark.like(like)))
    if status:
        q = q.filter(Production.status == status)
    # 视频创作页看 制作中 / 待发布 / 废弃（active）；发布数据页看 待发布 / 废弃 / 已完成
    if stage == "making":
        q = q.filter(Production.status == STATUS_MAKING)
    elif stage == "active":
        q = q.filter(Production.status.in_([STATUS_MAKING, STATUS_PENDING, STATUS_ABANDONED]))
    elif stage == "finished":
        q = q.filter(Production.status.in_([STATUS_PENDING, STATUS_ABANDONED, STATUS_PUBLISHED]))
    if platform:
        q = q.filter(Production.platform == platform)
    if character_id is not None:
        q = q.join(ProductionCharacter).filter(ProductionCharacter.character_id == character_id)

    total = q.count()
    # 视频创作列表按排期/开始时间倒序（produced_at），无开始时间的记录排在最后
    rows = (
        q.order_by(Production.produced_at.desc().nullslast(), Production.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": [_to_item(p, user) for p in rows], "total": total}


@router.post("", response_model=ProductionDetailOut)
def create_production(
    data: ProductionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_create(user)
    require_permission(user, "productions.create", db)
    # 无来源（未关联创意）的手动新建：必填校验 + 字段兜底
    if getattr(data, "idea_id", None) is None:
        missing = []
        if not (data.title or "").strip():
            missing.append("视频名称")
        if not data.category_id:
            missing.append("类型")
        if not data.characters:
            missing.append("人物模型")
        if not (data.platform or "").strip():
            missing.append("创作平台")
        if not any((p.text or "").strip() for p in data.prompt):
            missing.append("提示词")
        if missing:
            raise HTTPException(status_code=400, detail="请填写：" + "、".join(missing))
    production = Production(owner_id=user.id)
    _apply_in(db, production, data)
    if production.status == STATUS_PUBLISHED:
        raise HTTPException(status_code=400, detail="已发布状态只能由发布数据绑定触发")
    # 显式兜底默认状态：SQLAlchemy 列默认值要 flush 后才生效，这里提前设好，
    # 保证「制作中」自动写开始时间的逻辑能命中
    if not production.status:
        production.status = STATUS_MAKING
        production.produced_at = datetime.now()
    # 创作人默认当前登录者；作者缺省同样取当前登录者（显式传入时以传入为准）
    if not production.author:
        production.author = user.nickname or user.username
    db.add(production)
    db.flush()
    _sync_characters(db, production, data.characters)
    _sync_assets(db, production, data.assets)
    db.commit()
    db.refresh(production)
    return _to_detail(production, user)


@router.get("/{production_id}", response_model=ProductionDetailOut)
def get_production(
    production_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    production = db.query(Production).get(production_id)
    if not production:
        raise HTTPException(status_code=404, detail="制作记录不存在")
    return _to_detail(production, user)


@router.put("/{production_id}", response_model=ProductionDetailOut)
def update_production(
    production_id: int,
    data: ProductionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    production = db.query(Production).get(production_id)
    if not production:
        raise HTTPException(status_code=404, detail="制作记录不存在")
    ensure_owner(production, user, "编辑")
    # 制作人归属只允许管理员改，避免普通成员把记录转给他人
    if "owner_id" in data.model_fields_set and not is_admin(user):
        raise HTTPException(status_code=403, detail="仅管理员可修改制作人")
    old_status = production.status
    _apply_in(db, production, data)
    # 状态变更统一走状态机：校验合法流转、时间戳与来源创意同步
    if "status" in data.model_fields_set and data.status != old_status:
        transition(
            db, production, data.status,
            completed_at=data.completed_at, from_status=old_status,
        )
    # 人物绑定 / 附件同样只在显式传入时才同步，避免部分更新清空关联
    if "characters" in data.model_fields_set:
        _sync_characters(db, production, data.characters)
    if "assets" in data.model_fields_set:
        _sync_assets(db, production, data.assets)
    db.commit()
    db.refresh(production)
    return _to_detail(production, user)


@router.delete("/{production_id}")
def delete_production(
    production_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    production = db.query(Production).get(production_id)
    if not production:
        raise HTTPException(status_code=404, detail="制作记录不存在")
    ensure_owner(production, user, "删除")
    drop_tags(db, production.tags)
    db.delete(production)
    db.commit()
    return {"ok": True}
