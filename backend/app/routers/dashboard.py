from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from ..auth import get_current_user, scope_filter
from ..database import get_db
from ..models import (
    Character,
    Idea,
    Production,
    ProductionCharacter,
    PublishAccount,
    PublishStat,
    User,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

TREND_DAYS = 14


def _latest(video: Production):
    if not video.stats:
        return None
    return sorted(video.stats, key=lambda s: s.recorded_at or datetime.min)[-1]


def _collect(db: Session, model, user: User, scope: str = "all"):
    q = db.query(model)
    return scope_filter(q, model, user, scope).all()


def _trend_frame():
    """近 14 天日期轴（由远到近）与日期 → 下标映射。"""
    today = datetime.now().date()
    dates = [today - timedelta(days=i) for i in range(TREND_DAYS - 1, -1, -1)]
    return dates, {d.strftime("%m-%d"): i for i, d in enumerate(dates)}


def _bucket(trend, dt, index):
    if not dt:
        return None
    return index.get(dt.strftime("%m-%d"))


@router.get("")
def summary(
    scope: str = "all",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 惰性自动流转：排期时间到的「已排期」创意进「制作中」
    try:
        from .ideas import _promote_due_ideas
        _promote_due_ideas(db)
    except Exception:
        pass
    ideas = _collect(db, Idea, user, scope)
    productions = scope_filter(
        db.query(Production).options(selectinload(Production.stats)), Production, user, scope
    ).all()
    all_assets = _collect(db, Character, user, scope)
    # 三类资产共用 characters 表，分别统计
    characters = [c for c in all_assets if (c.asset_type or "character") == "character"]
    scene_assets = [c for c in all_assets if c.asset_type == "scene"]
    costume_assets = [c for c in all_assets if c.asset_type == "costume"]

    idea_counts = {"未使用": 0, "已排期": 0, "制作中": 0, "待发布": 0, "已完成": 0}
    idea_backup = 0
    # 内部状态沿用制作三态：制作中 / 待发布 / 已完成；兼容历史「已发布」
    prod_counts = {"制作中": 0, "待发布": 0, "已完成": 0, "已发布": 0}
    plays_total = likes_total = comments_total = shares_total = 0
    published_this_month = 0
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    mine_productions = 0
    mine_published = 0
    mine_plays = 0

    for idea in ideas:
        idea_counts[idea.status] = idea_counts.get(idea.status, 0) + 1
        if idea.is_backup:
            idea_backup += 1

    for v in productions:
        prod_counts[v.status] = prod_counts.get(v.status, 0) + 1
        latest = _latest(v)
        if latest:
            plays_total += latest.plays or 0
            likes_total += latest.likes or 0
            comments_total += latest.comments or 0
            shares_total += latest.shares or 0
        if v.status in ("已发布", "已完成") and v.published_at and v.published_at >= month_start:
            published_this_month += 1
        if v.owner_id == user.id:
            mine_productions += 1
            if v.status in ("已发布", "已完成"):
                mine_published += 1
            if latest:
                mine_plays += latest.plays or 0

    # 人物使用排行（按绑定的制作记录数）
    usage = {}
    for link in db.query(ProductionCharacter).all():
        usage[link.character_id] = usage.get(link.character_id, 0) + 1
    char_rows = [
        {
            "id": c.id,
            "name": c.name,
            "production_count": usage.get(c.id, 0),
            "image_count": len(c.images),
        }
        for c in characters
    ]
    char_rows.sort(key=lambda x: x["production_count"], reverse=True)

    # 平台分布
    platform_counts = {}
    for v in productions:
        key = v.platform or "未标注"
        platform_counts[key] = platform_counts.get(key, 0) + 1

    # ---- 首页两条主线：制作排期趋势 / 账号发布数据趋势 ----
    trend_dates, trend_index = _trend_frame()
    schedule_trend = [
        {"date": d.strftime("%m-%d"), "planned": 0, "completed": 0, "published": 0}
        for d in trend_dates
    ]
    publish_trend = [
        {"date": d.strftime("%m-%d"), "plays": 0, "likes": 0, "count": 0}
        for d in trend_dates
    ]
    for idea in ideas:
        if not idea.planned_at:
            continue
        idx = _bucket(schedule_trend, idea.planned_at, trend_index)
        if idx is not None:
            schedule_trend[idx]["planned"] += 1
    for v in productions:
        for field, key in (("completed_at", "completed"), ("published_at", "published")):
            idx = _bucket(schedule_trend, getattr(v, field, None), trend_index)
            if idx is not None:
                schedule_trend[idx][key] += 1

    accounts = db.query(PublishAccount).all()
    accounts_by_id = {a.id: a for a in accounts}
    accounts_by_name = {a.name: a for a in accounts}
    user_names = {u.id: u.nickname or u.username for u in db.query(User).all()}
    account_ranking = {}
    for v in productions:
        latest = _latest(v)
        if not latest:
            continue
        idx = _bucket(publish_trend, latest.recorded_at, trend_index)
        if idx is not None:
            publish_trend[idx]["plays"] += latest.plays or 0
            publish_trend[idx]["likes"] += latest.likes or 0
            publish_trend[idx]["count"] += 1
        acc = accounts_by_name.get(latest.account or "")
        if not acc and v.publish_account_id:
            acc = accounts_by_id.get(v.publish_account_id)
        name = acc.name if acc else (latest.account or "未分配账号")
        row = account_ranking.setdefault(
            name, {"name": name, "avatar": acc.avatar if acc else "", "plays": 0, "likes": 0, "count": 0}
        )
        row["plays"] += latest.plays or 0
        row["likes"] += latest.likes or 0
        row["count"] += 1
    ranking = sorted(account_ranking.values(), key=lambda x: x["plays"], reverse=True)[:6]

    upcoming = sorted(
        [i for i in ideas if i.status in ("已排期", "制作中")],
        key=lambda i: i.planned_at or i.created_at or datetime.max,
    )[:5]
    upcoming_ideas = [
        {
            "id": i.id,
            "title": i.title or "未命名创意",
            "status": i.status,
            "priority": i.priority or 2,
            "date": i.planned_at.strftime("%m-%d") if i.planned_at else "待定",
            "owner": user_names.get(i.creator_id) or user_names.get(i.owner_id) or "未指定",
            "cover": i.cover or "",
        }
        for i in upcoming
    ]

    return {
        "idea_total": len(ideas),
        "idea_unused": idea_counts["未使用"],
        "idea_scheduled": idea_counts["已排期"],  # 前端展示为「已排期」
        "idea_backup": idea_backup,  # 备选标记数量
        "idea_counts": idea_counts,
        "schedule_total": idea_counts["已排期"] + idea_counts["制作中"],
        "schedule_pending": idea_counts["已排期"],
        "schedule_in_progress": idea_counts["制作中"],
        "schedule_done": idea_counts["待发布"] + idea_counts["已完成"],
        "production_total": len(productions),
        "production_making": prod_counts["制作中"],
        "production_done": prod_counts["待发布"] + prod_counts["已完成"],
        "production_published": prod_counts["已完成"] + prod_counts["已发布"],
        "character_total": len(characters),
        "asset_total": len(all_assets),
        "scene_total": len(scene_assets),
        "costume_total": len(costume_assets),
        "plays_total": plays_total,
        "likes_total": likes_total,
        "comments_total": comments_total,
        "shares_total": shares_total,
        "published_this_month": published_this_month,
        "production_counts": prod_counts,
        "platform_counts": platform_counts,
        "schedule_trend": schedule_trend,
        "publish_trend": publish_trend,
        "account_ranking": ranking,
        "upcoming_ideas": upcoming_ideas,
        "top_characters": [c for c in char_rows if c["production_count"]][:10],
        "mine": {
            "schedule_total": sum(1 for i in ideas if i.owner_id == user.id and i.status in ("已排期", "制作中")),
            "production_total": mine_productions,
            "published_total": mine_published,
            "plays_total": mine_plays,
        },
    }
