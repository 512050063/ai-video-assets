"""视频创作流程状态机。

唯一权威状态放在 productions.status；创意灵感状态只是它的投影。
所有状态写入必须经由本模块的 transition / bind_publish / unbind_publish，
禁止在路由里直接给 status 赋值，避免多处双写导致状态漂移。
"""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import DouyinImport, Idea, Production, PublishStat

STATUS_MAKING = "制作中"
STATUS_PENDING = "待发布"
STATUS_ABANDONED = "废弃"
STATUS_PUBLISHED = "已完成"

DISPLAY_STATUS = {
    STATUS_ABANDONED: "已废弃",
    STATUS_PUBLISHED: "已发布",
}

# 人工可触发的流转。已发布只能由绑定事件进入，只能由解绑事件退出。
MANUAL_TRANSITIONS = {
    STATUS_MAKING: {STATUS_PENDING},
    STATUS_PENDING: {STATUS_MAKING, STATUS_ABANDONED},
    STATUS_ABANDONED: {STATUS_PENDING},
    STATUS_PUBLISHED: set(),
}


def status_label(status: str) -> str:
    """内部状态 → 对外展示文案。"""
    return DISPLAY_STATUS.get(status, status or "")


def has_binding(db: Session, production: Production) -> bool:
    """是否已绑定发布数据（唯一标识字段或任一张绑定表中有记录）。"""
    if getattr(production, "published_video_id", ""):
        return True
    if db.query(PublishStat).filter(PublishStat.production_id == production.id).count():
        return True
    return bool(
        db.query(DouyinImport)
        .filter(DouyinImport.production_id == production.id)
        .count()
    )


def _sync_idea(db: Session, production: Production, status: str) -> None:
    """把制作记录状态投影到来源创意，保持两页展示一致。"""
    if not production.idea_id:
        return
    idea = db.query(Idea).get(production.idea_id)
    if idea and idea.status != status:
        idea.status = status
        idea.updated_at = datetime.now()


def transition(
    db: Session,
    production: Production,
    target: str,
    *,
    reason: str = "manual",
    completed_at=None,
    from_status: str | None = None,
) -> Production:
    """执行一次受约束的状态迁移，并同步时间字段与来源创意。

    reason=manual 为人工流转；bind / unbind 为发布数据绑定事件。
    """
    current = from_status or production.status or STATUS_MAKING
    if target not in {STATUS_MAKING, STATUS_PENDING, STATUS_ABANDONED, STATUS_PUBLISHED}:
        raise HTTPException(status_code=400, detail=f"无效流程状态: {target}")

    if reason == "bind":
        if current == STATUS_PUBLISHED:
            return production
    elif reason == "unbind":
        if current != STATUS_PUBLISHED:
            return production
        if target != STATUS_PENDING:
            raise HTTPException(status_code=400, detail="取消关联只能回退到「待发布」")
    elif current == STATUS_PUBLISHED:
        raise HTTPException(status_code=400, detail="已发布状态已锁定，请先取消发布数据关联")
    elif target == STATUS_PUBLISHED:
        raise HTTPException(status_code=400, detail="已发布状态只能由发布数据绑定触发")
    elif target not in MANUAL_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=400,
            detail=f"不允许从「{status_label(current)}」改为「{status_label(target)}」",
        )

    now = datetime.now()
    if target == STATUS_MAKING:
        production.produced_at = production.produced_at or now
        production.completed_at = None
        production.published_at = None
    elif target == STATUS_PENDING:
        production.completed_at = completed_at or production.completed_at or now
        production.published_at = None
    elif target == STATUS_ABANDONED:
        production.published_at = None
    elif target == STATUS_PUBLISHED:
        production.published_at = production.published_at or now
        production.completed_at = production.completed_at or now
    production.status = target
    production.updated_at = now
    _sync_idea(db, production, target)
    return production


def bind_publish(db: Session, production: Production, video_id: str = "") -> Production:
    """绑定发布数据：这是进入「已发布」的唯一入口。"""
    if video_id:
        production.published_video_id = video_id
    return transition(db, production, STATUS_PUBLISHED, reason="bind")


def clear_binding_video(production: Production, video_id: str) -> None:
    """解绑具体作品时，先清掉锁定标识，再判断是否还有其他绑定。"""
    if video_id and production.published_video_id == video_id:
        production.published_video_id = ""


def unbind_publish(db: Session, production: Production) -> Production:
    """取消发布数据关联：这是退出「已发布」的唯一入口。"""
    production.published_video_id = ""
    return transition(db, production, STATUS_PENDING, reason="unbind")
