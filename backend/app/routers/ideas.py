"""创意库：创作流程第 1 步，负责收集创意视频并承载全流程状态。"""
import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..auth import (
    ensure_owner,
    get_current_user,
    has_permission,
    require_create,
    require_permission,
    scope_filter,
)
from ..database import get_db
from ..douyin import parse_share_text
from ..models import Idea, IdeaComment, Production, PublishStat, User, VoteRecord
from ..schemas import (
    IdeaArrangeIn,
    IdeaCommentIn,
    IdeaCommentOut,
    IdeaDetailOut,
    IdeaIn,
    ParseResultOut,
    ScheduleIn,
    ShareTextIn,
    StatusUpdate,
)
from ..tag_service import collect_tags, drop_tags

router = APIRouter(prefix="/ideas", tags=["ideas"])


def _vote_config(db: Session) -> dict:
    """读取投票规则配置，缺省每人每天 5 票。"""
    try:
        from .settings import _all_settings

        cfg = _all_settings(db).get("vote") or {}
        limit = int(cfg.get("daily_limit", 5))
    except Exception:
        limit = 5
    return {"daily_limit": max(0, limit)}


def _today_start() -> datetime:
    now = datetime.now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _votes_today(db: Session, user_id: int) -> int:
    """统计当前用户今日有效投票数（按记录时间，取消的不计）。"""
    return (
        db.query(VoteRecord)
        .filter(
            VoteRecord.user_id == user_id,
            VoteRecord.active.is_(True),
            VoteRecord.created_at >= _today_start(),
        )
        .count()
    )


def _owner_name(idea: Idea) -> str:
    if not idea.owner:
        return "未归属"
    return idea.owner.nickname or idea.owner.username


def _to_detail(
    idea: Idea,
    user: User,
    db: Session,
    vote_cfg: dict = None,
    used_today: int = None,
) -> IdeaDetailOut:
    out = IdeaDetailOut(
        id=idea.id,
        title=idea.title or "",
        cover=idea.cover or "",
        category_id=idea.category_id,
        category_name=idea.category.name if idea.category else None,
        douyin_url=idea.douyin_url or "",
        video_id=idea.video_id or "",
        share_text=idea.share_text or "",
        author=idea.author or "",
        tags=idea.tags or [],
        status=idea.status or "未使用",
        is_backup=bool(idea.is_backup),
        remark=idea.remark or "",
        like_count=idea.like_count or 0,
        comment_count=idea.comment_count or 0,
        collect_count=idea.collect_count or 0,
        share_count=idea.share_count or 0,
        priority=idea.priority or 2,
        planned_at=idea.planned_at,
        created_at=idea.created_at,
        updated_at=idea.updated_at,
    )
    # 关联制作：按 idea_id 直接查找来源制作记录
    production = (
        db.query(Production)
        .filter(Production.idea_id == idea.id)
        .order_by(Production.id.desc())
        .first()
    )
    if production:
        out.production_id = production.id
        out.production_title = production.title
        out.production_status = production.status
        out.completed_at = production.completed_at
    out.owner_id = idea.owner_id
    out.owner_name = _owner_name(idea)
    out.is_owner = idea.owner_id == user.id
    # 点赞投票：票数 / 当前用户是否已投 / 投票人昵称
    voter_ids = list(idea.voter_ids or [])
    out.votes = len(voter_ids)
    out.voted = user.id in voter_ids
    if voter_ids:
        voters = db.query(User).filter(User.id.in_(voter_ids)).all()
        out.voter_names = [v.display_name for v in voters]
    # 认领标记：废弃 want_ids，仅保留字段兼容（恒为空），前端不再展示认领交互
    want_ids = list(idea.want_ids or [])
    out.wants = len(want_ids)
    out.wanted = user.id in want_ids
    if want_ids:
        wanters = db.query(User).filter(User.id.in_(want_ids)).all()
        out.want_names = [w.display_name for w in wanters]
    # 创作人 = 负责制作视频的人（独立字段 creator_id，与提交人 owner_id 区分）
    out.creator_id = idea.creator_id
    if idea.creator_id:
        creator = db.query(User).get(idea.creator_id)
        out.creator_name = creator.display_name if creator else None
    # 认领权限保留字段兼容，恒为 False（认领机制已废弃）
    out.can_want = False
    out.can_assign = False
    # 状态/创作安排编辑权限：归属人或超管
    out.can_arrange = (idea.owner_id == user.id) or user.role == "admin"
    # 评论条数（系统内讨论，与抖音视频数据的评论数分开统计）
    out.comment_total = db.query(IdeaComment).filter(IdeaComment.idea_id == idea.id).count()
    # 投票规则：上限与今日已用（列表场景由调用方预取，避免逐行查询）
    cfg = vote_cfg if vote_cfg is not None else _vote_config(db)
    used = _votes_today(db, user.id) if used_today is None else used_today
    out.vote_daily_limit = cfg["daily_limit"]
    out.vote_used_today = used
    out.vote_exhausted = used >= cfg["daily_limit"]
    return out


def _apply_in(db: Session, idea: Idea, data: IdeaIn):
    provided = data.model_fields_set

    video_id = ""
    if "douyin_url" in provided:
        m = re.search(r"/video/(\d+)", data.douyin_url or "")
        if m:
            video_id = m.group(1)
    if not video_id and "video_id" in provided:
        video_id = (data.video_id or "").strip()
    if not video_id and "douyin_url" not in provided and "video_id" not in provided:
        video_id = idea.video_id or ""

    old_tags = list(idea.tags or [])
    for field in (
        "title", "cover", "category_id", "douyin_url", "share_text", "author", "remark",
        "like_count", "comment_count", "collect_count", "share_count", "priority", "planned_at",
        "creator_id", "is_backup",
    ):
        if field in provided:
            setattr(idea, field, getattr(data, field))
    # 视频数据不允许负数（新对象入库前默认值为 None，这里统一兜底为 0）
    for field in ("like_count", "comment_count", "collect_count", "share_count"):
        value = getattr(idea, field, None)
        if value is None or value < 0:
            setattr(idea, field, 0)
    if "tags" in provided:
        idea.tags = list(data.tags or [])
    idea.video_id = video_id
    idea.updated_at = datetime.now()

    # 标签库：新增标签自动登记，移除的标签扣减引用
    if "tags" in provided:
        collect_tags(db, idea.tags)
        removed = [t for t in old_tags if t not in (idea.tags or [])]
        if removed:
            drop_tags(db, removed)

    # 同一抖音视频不重复收集
    if idea.video_id:
        dup_q = db.query(Idea).filter(Idea.video_id == idea.video_id)
        if idea.id:
            dup_q = dup_q.filter(Idea.id != idea.id)
        dup = dup_q.first()
        if dup:
            raise HTTPException(
                status_code=400,
                detail=f"该抖音视频已存在于创意「{dup.title or '未命名'}」中，无需重复收集",
            )


@router.get("", response_model=list[IdeaDetailOut])
def list_ideas(
    keyword: str = "",
    status: str = "",
    scope: str = "all",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 惰性自动流转：排期时间到的「已排期」创意自动进「制作中」
    _promote_due_ideas(db)
    q = db.query(Idea).options(joinedload(Idea.owner))
    q = scope_filter(q, Idea, user, scope)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            or_(
                Idea.title.like(like),
                Idea.author.like(like),
                Idea.remark.like(like),
                Idea.douyin_url.like(like),
                Idea.share_text.like(like),
            )
        )
    if status:
        q = q.filter(Idea.status == status)
    rows = q.order_by(Idea.id.desc()).all()
    cfg = _vote_config(db)
    used = _votes_today(db, user.id)
    return [_to_detail(i, user, db, vote_cfg=cfg, used_today=used) for i in rows]


@router.post("", response_model=IdeaDetailOut)
def create_idea(
    data: IdeaIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_create(user)
    require_permission(user, "ideas.create", db)
    idea = Idea(owner_id=user.id, status="未使用")
    _apply_in(db, idea, data)
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return _to_detail(idea, user, db)


@router.post("/parse", response_model=ParseResultOut)
def parse_idea(payload: ShareTextIn, user: User = Depends(get_current_user)):
    """解析抖音链接/分享文案，供创意库新建时使用。

    解析出链接后自动抓取作者、封面与视频数据；抓取失败时优雅降级，
    仍返回文本解析结果并提示手工补充，不阻塞收集流程。
    """
    result = parse_share_text(payload.text, expand=True)
    result.setdefault("author_id", "")
    result.setdefault("cover", "")
    result.setdefault("like_count", 0)
    result.setdefault("comment_count", 0)
    result.setdefault("collect_count", 0)
    result.setdefault("share_count", 0)
    result["fetch_status"] = "manual"

    target = result.get("url") or ""
    if not payload.auto_fetch or not target:
        return result

    try:
        from ..douyin_collector import fetch_video

        fetched = fetch_video(target, channel="auto")
    except Exception:
        fetched = None

    if fetched:
        # 详情接口返回的字段更准，覆盖文本解析的占位值
        if fetched.get("title"):
            result["title"] = fetched["title"]
        if fetched.get("tags"):
            result["tags"] = fetched["tags"]
        if fetched.get("author"):
            result["author"] = fetched["author"]
        if fetched.get("author_id"):
            result["author_id"] = fetched["author_id"]
        if fetched.get("cover"):
            result["cover"] = fetched["cover"]
        if fetched.get("video_id"):
            result["video_id"] = fetched["video_id"]
        result["like_count"] = int(fetched.get("likes") or 0)
        result["comment_count"] = int(fetched.get("comments") or 0)
        result["collect_count"] = int(fetched.get("collects") or 0)
        result["share_count"] = int(fetched.get("shares") or 0)
        result["fetch_status"] = "auto"
        result["message"] = "已自动获取作者、封面与视频数据，可手动调整"
    else:
        result["message"] = (result.get("message") or "") + "；自动抓取未成功，作者/封面/数据请手动补充"

    return result


@router.get("/assignees", response_model=list[dict])
def list_assignees(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """「我想做」指定认领人的候选成员（仅创作角色，超管可用）。"""
    require_permission(user, "ideas.want.assign", db)
    rows = (
        db.query(User)
        .filter(User.is_active.is_(True), User.module_role == "production")
        .order_by(User.id.asc())
        .all()
    )
    return [
        {"id": u.id, "display_name": u.nickname or u.username, "role": u.role}
        for u in rows
    ]


@router.get("/creator-options", response_model=list[dict])
def list_creator_options(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创作安排弹窗的制作人候选：仅「创作」角色的活跃成员。"""
    rows = (
        db.query(User)
        .filter(User.is_active.is_(True), User.module_role == "production")
        .order_by(User.id.asc())
        .all()
    )
    return [
        {"id": u.id, "display_name": u.nickname or u.username, "role": u.role}
        for u in rows
    ]


@router.get("/{idea_id}", response_model=IdeaDetailOut)
def get_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _promote_due_ideas(db)
    idea = db.query(Idea).get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="创意不存在")
    return _to_detail(idea, user, db)


@router.post("/{idea_id}/vote", response_model=IdeaDetailOut)
def toggle_vote(
    idea_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """点赞投票：同一用户再次点击则取消（一人一票，可撤销）。

    任何登录用户均可投票，不要求 create 权限；仅创意归属/可见性由列表层面控制。
    投票规则：每人每天投票次数上限由「配置中心 → 投票规则」决定；取消投票不占用次数。
    """
    require_permission(user, "ideas.vote", db)
    idea = db.query(Idea).get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="创意不存在")
    voter_ids = list(idea.voter_ids or [])
    cfg = _vote_config(db)
    if user.id in voter_ids:
        # 取消投票：删除当天的有效记录，释放一次投票额度（不留残余记录污染基线）
        voter_ids.remove(user.id)
        record = (
            db.query(VoteRecord)
            .filter(VoteRecord.idea_id == idea_id, VoteRecord.user_id == user.id, VoteRecord.active.is_(True))
            .order_by(VoteRecord.id.desc())
            .first()
        )
        if record:
            db.delete(record)
    else:
        used = _votes_today(db, user.id)
        if used >= cfg["daily_limit"]:
            raise HTTPException(
                status_code=400,
                detail=f"今日投票次数已达上限（{cfg['daily_limit']} 次），明天再来吧",
            )
        voter_ids.append(user.id)
        db.add(VoteRecord(idea_id=idea_id, user_id=user.id, active=True, created_at=datetime.now()))
    idea.voter_ids = voter_ids
    idea.updated_at = datetime.now()
    db.commit()
    db.refresh(idea)
    return _to_detail(idea, user, db, vote_cfg=cfg, used_today=_votes_today(db, user.id))


@router.post("/{idea_id}/want", response_model=IdeaDetailOut)
def toggle_want(
    idea_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """「我想做」认领：仅创作者角色可自助认领/取消。

    与点赞投票不同：
    - 不占用每日投票额度，也不受投票次数上限限制
    - 只做标记，不改变流程状态（与「排期」操作互不影响）
    - 单人认领：一条创意同一时间只归属一名创作者，已被他人认领时不可再认领
    """
    require_permission(user, "ideas.want", db)
    idea = db.query(Idea).get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="创意不存在")
    want_ids = list(idea.want_ids or [])
    if user.id in want_ids:
        # 取消自己的认领
        want_ids.remove(user.id)
    else:
        if want_ids:
            owner = db.query(User).get(want_ids[0])
            owner_name = owner.display_name if owner else "他人"
            raise HTTPException(status_code=400, detail=f"该创意已被「{owner_name}」认领")
        want_ids = [user.id]
    idea.want_ids = want_ids
    idea.updated_at = datetime.now()
    db.commit()
    db.refresh(idea)
    return _to_detail(idea, user, db)


@router.put("/{idea_id}/want", response_model=IdeaDetailOut)
def assign_want(
    idea_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """管理员指定「我想做」认领人（可传 null 取消指定）。"""
    require_permission(user, "ideas.want.assign", db)
    idea = db.query(Idea).get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="创意不存在")
    target_id = data.get("user_id")
    if target_id is None:
        idea.want_ids = []
    else:
        target = db.query(User).get(int(target_id))
        if not target:
            raise HTTPException(status_code=404, detail="指定的用户不存在")
        idea.want_ids = [target.id]
    idea.updated_at = datetime.now()
    db.commit()
    db.refresh(idea)
    return _to_detail(idea, user, db)


@router.get("/{idea_id}/comments", response_model=list[IdeaCommentOut])
def list_comments(
    idea_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """评论列表：多人可在同一条创意下发表意见，按时间正序展示。"""
    idea = db.query(Idea).get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="创意不存在")
    rows = (
        db.query(IdeaComment)
        .filter(IdeaComment.idea_id == idea_id)
        .order_by(IdeaComment.id.asc())
        .all()
    )
    result = []
    for c in rows:
        result.append(
            IdeaCommentOut(
                id=c.id,
                idea_id=c.idea_id,
                user_id=c.user_id,
                user_name=(c.user.display_name if c.user else ""),
                content=c.content or "",
                created_at=c.created_at,
                is_owner=c.user_id == user.id,
            )
        )
    return result


@router.post("/{idea_id}/comments", response_model=IdeaCommentOut)
def create_comment(
    idea_id: int,
    data: IdeaCommentIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """发表评论：仅做讨论，不改变创意状态，也不影响排期。"""
    require_permission(user, "ideas.comment", db)
    idea = db.query(Idea).get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="创意不存在")
    content = (data.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="评论内容不能为空")
    if len(content) > 500:
        raise HTTPException(status_code=400, detail="评论内容不能超过 500 字")
    comment = IdeaComment(
        idea_id=idea_id,
        user_id=user.id,
        content=content,
        created_at=datetime.now(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return IdeaCommentOut(
        id=comment.id,
        idea_id=comment.idea_id,
        user_id=comment.user_id,
        user_name=user.display_name,
        content=comment.content,
        created_at=comment.created_at,
        is_owner=True,
    )


@router.delete("/{idea_id}/comments/{comment_id}", response_model=dict)
def delete_comment(
    idea_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除评论：本人或超管可删。"""
    comment = db.query(IdeaComment).get(comment_id)
    if not comment or comment.idea_id != idea_id:
        raise HTTPException(status_code=404, detail="评论不存在")
    if comment.user_id != user.id and not user.role == "admin":
        raise HTTPException(status_code=403, detail="只能删除自己发表的评论")
    db.delete(comment)
    db.commit()
    return {"ok": True}


@router.put("/{idea_id}", response_model=IdeaDetailOut)
def update_idea(
    idea_id: int,
    data: IdeaIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    idea = db.query(Idea).get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="创意不存在")
    ensure_owner(idea, user, "编辑")
    require_permission(user, "ideas.edit", db)
    _apply_in(db, idea, data)
    db.commit()
    db.refresh(idea)
    return _to_detail(idea, user, db)


# 全流程 5 态：未使用 / 已排期 / 制作中 / 待发布 / 已完成
# 「备选库」改为独立备选标记 is_backup，不再是流程状态。
# 创意灵感页状态标签只在「未使用 / 已排期」间切换；创作计划弹窗保存后进入「已排期」；
# 排期时间到（planned_at <= now）由惰性任务 _promote_due_ideas 自动推进到「制作中」。
IDEA_STATUSES = ("未使用", "已排期", "制作中", "待发布", "已完成")
# 创意灵感页状态标签可直接切换的状态（制作及以后由到期任务/视频创作页控制）
IDEA_STATUS_DIRECT = ("未使用", "已排期")


def _promote_due_ideas(db: Session) -> int:
    """惰性自动流转：排期时间已到的「已排期」创意 → 「制作中」并生成制作记录。

    在列表/详情查询时调用，避免依赖后台定时任务；返回本次推进的条数。
    """
    due = (
        db.query(Idea)
        .filter(Idea.status == "已排期", Idea.planned_at.isnot(None), Idea.planned_at <= datetime.now())
        .all()
    )
    if not due:
        return 0
    system_user = db.query(User).order_by(User.id).first()
    for idea in due:
        idea.status = "制作中"
        idea.updated_at = datetime.now()
        _ensure_production(idea, system_user, db)
    db.commit()
    return len(due)


def _ensure_production(idea: Idea, user: User, db: Session):
    """状态推进到「制作中」时，自动生成一条制作记录（幂等）。

    开始时间 produced_at 取创作计划里填的排期时间 planned_at；未填时回退为当前时间。
    """
    existing = db.query(Production).filter(Production.idea_id == idea.id).first()
    if existing:
        # 已存在时补一次开始时间（历史记录可能为空，或用户后来补填了排期日期）
        if existing.produced_at is None and idea.planned_at is not None:
            existing.produced_at = idea.planned_at
        return existing
    production = Production(
        title=idea.title or "",
        cover=idea.cover or "",
        tags=list(idea.tags or []),
        douyin_url=idea.douyin_url or "",
        idea_id=idea.id,
        category_id=idea.category_id,
        status="制作中",
        produced_at=idea.planned_at or datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        owner_id=idea.creator_id or user.id,
    )
    db.add(production)
    return production


@router.put("/{idea_id}/status", response_model=IdeaDetailOut)
def update_idea_status(
    idea_id: int,
    data: StatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创意灵感页点击状态标签切换：仅在「未使用 / 已排期」之间互切。

    「制作中」及以后的状态由创作计划弹窗（/arrange）保存后进「已排期」，
    排期时间到自动流转到「制作中」，不通过本接口直接设置。
    """
    idea = db.query(Idea).get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="创意不存在")
    ensure_owner(idea, user, "修改状态")
    require_permission(user, "ideas.edit", db)
    status = (data.status or "").strip()
    if status not in IDEA_STATUS_DIRECT:
        raise HTTPException(
            status_code=400,
            detail="创意灵感只能切换「未使用 / 已排期」，制作中由排期时间自动推进",
        )
    # 仅初始态可点状态标签切换；制作中及以后由创作计划/视频创作/发布数据控制
    if idea.status not in IDEA_STATUS_DIRECT:
        raise HTTPException(status_code=400, detail="当前状态不支持在灵感页切换，请到对应环节处理")
    idea.status = status
    idea.updated_at = datetime.now()

    db.commit()
    db.refresh(idea)
    return _to_detail(idea, user, db)


@router.put("/{idea_id}/arrange", response_model=IdeaDetailOut)
def arrange_idea(
    idea_id: int,
    data: IdeaArrangeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创作计划弹窗：设置紧急程度 / 创作人 / 制作时间，保存后状态进入「已排期」。

    - 仅归属人或超管可操作。
    - 字段缺省保持原值；显式传 null 清空对应字段。
    - 创作人为独立字段 creator_id（负责制作视频的人）。
    - 保存后状态 = 已排期；排期时间到由 _promote_due_ideas 自动推进到「制作中」并生成制作记录。
    """
    idea = db.query(Idea).get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="创意不存在")
    ensure_owner(idea, user, "修改创作安排")
    require_permission(user, "ideas.edit", db)

    provided = data.model_fields_set
    if "status" in provided and data.status is not None:
        status = (data.status or "").strip()
        if status not in IDEA_STATUSES:
            raise HTTPException(status_code=400, detail="无效状态，可选：" + " / ".join(IDEA_STATUSES))
        idea.status = status
    if "priority" in provided:
        priority = data.priority
        if priority is not None and priority not in (1, 2, 3):
            raise HTTPException(status_code=400, detail="无效优先级，可选：1 高 / 2 中 / 3 低")
        idea.priority = priority or 2
    if "planned_at" in provided:
        idea.planned_at = data.planned_at
    if "creator_id" in provided:
        creator_id = data.creator_id
        if creator_id is None:
            idea.creator_id = None
        else:
            target = db.query(User).get(int(creator_id))
            if not target:
                raise HTTPException(status_code=404, detail="指定的创作人不存在")
            idea.creator_id = target.id

    # 弹窗保存即排期完成：进入「已排期」，制作记录等排期时间到再自动生成
    if "status" not in provided or data.status is None:
        idea.status = "已排期"

    idea.updated_at = datetime.now()
    db.commit()
    db.refresh(idea)
    return _to_detail(idea, user, db)


@router.put("/{idea_id}/backup", response_model=IdeaDetailOut)
def toggle_backup(
    idea_id: int,
    data: dict = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """切换备选标记：纯标记，不改变流程状态。归属人或管理员可操作。"""
    idea = db.query(Idea).get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="创意不存在")
    ensure_owner(idea, user, "修改备选标记")
    require_permission(user, "ideas.edit", db)
    requested = None
    if isinstance(data, dict) and "is_backup" in data:
        requested = bool(data["is_backup"])
    idea.is_backup = (not bool(idea.is_backup)) if requested is None else requested
    idea.updated_at = datetime.now()
    db.commit()
    db.refresh(idea)
    return _to_detail(idea, user, db)


@router.post("/{idea_id}/cancel-plan", response_model=IdeaDetailOut)
def cancel_plan(
    idea_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创作计划弹窗确认取消排期：状态回退「未使用」，清空计划字段并移除制作记录。"""
    idea = db.query(Idea).get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="创意不存在")
    ensure_owner(idea, user, "取消排期")
    require_permission(user, "ideas.edit", db)
    if idea.status not in ("已排期", "制作中"):
        raise HTTPException(status_code=400, detail="仅「已排期 / 制作中」的创意可取消排期")

    idea.status = "未使用"
    idea.creator_id = None
    idea.priority = 2
    idea.planned_at = None
    idea.updated_at = datetime.now()
    production = db.query(Production).filter(Production.idea_id == idea.id).first()
    if production:
        # 仅清理尚未产生发布数据的制作记录
        has_stat = db.query(PublishStat).filter(PublishStat.production_id == production.id).count()
        if not has_stat:
            db.delete(production)

    db.commit()
    db.refresh(idea)
    return _to_detail(idea, user, db)


@router.delete("/{idea_id}")
def delete_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    idea = db.query(Idea).get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="创意不存在")
    ensure_owner(idea, user, "删除")
    require_permission(user, "ideas.delete", db)
    drop_tags(db, idea.tags)
    db.delete(idea)
    db.commit()
    return {"ok": True}


@router.post("/{idea_id}/schedule", response_model=dict)
def schedule_idea(
    idea_id: int,
    data: ScheduleIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创意排期：直接在创意上记录优先级/创作时间并进入「已排期」（不再生成独立计划表）。"""
    require_create(user)
    require_permission(user, "ideas.schedule", db)
    idea = db.query(Idea).get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="创意不存在")
    ensure_owner(idea, user, "排期")
    if idea.status not in ("未使用", "已排期"):
        raise HTTPException(status_code=400, detail="仅未使用 / 已排期的创意可设置排期")

    provided = data.model_fields_set
    if "priority" in provided:
        priority = data.priority
        if priority is not None and priority not in (1, 2, 3):
            raise HTTPException(status_code=400, detail="无效优先级，可选：1 高 / 2 中 / 3 低")
        idea.priority = priority or 2
    if "planned_at" in provided:
        idea.planned_at = data.planned_at
    if "category_id" in provided and data.category_id is not None:
        idea.category_id = data.category_id
    if "remark" in provided and data.remark:
        idea.remark = data.remark
    idea.status = "已排期"
    idea.updated_at = datetime.now()
    db.commit()
    db.refresh(idea)
    return {"id": idea.id, "title": idea.title or "", "idea_id": idea.id, "status": idea.status}
