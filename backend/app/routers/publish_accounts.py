"""发布账号：独立模块（从配置中心拆出）。

字段：账号名称 / 发布平台 / 平台账号 ID / 头像 / 标签 / 备注
      视频数量 / 获赞 / 粉丝（可由抖音采集通道自动回填，也可手工维护）
      状态（正常/搁置/废弃） / 更新节奏（日更/隔日更/周更） / 责任人（绑定创作者）
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..auth import ensure_owner, get_current_user, require_create, require_permission, scope_filter
from ..database import get_db
from ..models import Idea, Production, PublishAccount, PublishAccountSnapshot, User
from ..schemas import PublishAccountIn, PublishAccountOut, UpdateReminderOut
from ..tag_service import collect_tags

router = APIRouter(prefix="/publish-accounts", tags=["publish-accounts"])

VALID_ACCOUNT_STATUS = {"正常", "搁置", "废弃"}
VALID_RHYTHM = {"日更", "隔日更", "周更"}
RHYTHM_DAYS = {"日更": 1, "隔日更": 2, "周更": 7}


def _responsible_name(account: PublishAccount) -> str:
    if not account.responsible:
        return ""
    return account.responsible.nickname or account.responsible.username


def _to_out(account: PublishAccount, user: User, latest=None, previous=None) -> PublishAccountOut:
    out = PublishAccountOut.model_validate(account)
    out.tags = list(account.tags or [])
    out.responsible_name = _responsible_name(account)
    # 增量基准：优先用最新快照自带的 prev_*（首次更新也能算）；旧数据回退到倒数第二条快照
    if latest is not None:
        if getattr(latest, "prev_video_count", None) is not None:
            base = {
                "video_count": latest.prev_video_count or 0,
                "likes_count": latest.prev_likes_count or 0,
                "followers_count": latest.prev_followers_count or 0,
            }
        elif previous is not None:
            base = {
                "video_count": previous.video_count or 0,
                "likes_count": previous.likes_count or 0,
                "followers_count": previous.followers_count or 0,
            }
        else:
            base = None
        if base is not None:
            out.deltas = {
                "video_count": (account.video_count or 0) - base["video_count"],
                "likes_count": (account.likes_count or 0) - base["likes_count"],
                "followers_count": (account.followers_count or 0) - base["followers_count"],
            }
    return out


def _apply_in(db: Session, account: PublishAccount, data: PublishAccountIn):
    provided = data.model_fields_set
    for field in (
        "name", "platform", "account_id", "avatar", "note",
        "video_count", "likes_count", "followers_count", "douyin_uid", "sec_uid", "home_url",
        "status", "update_rhythm", "responsible_id",
    ):
        if field in provided:
            # 名称为空时保留原值，避免部分更新把账号名清空
            if field == "name" and not (data.name or "").strip():
                continue
            setattr(account, field, getattr(data, field))
    if "status" in provided and account.status not in VALID_ACCOUNT_STATUS:
        raise HTTPException(status_code=400, detail=f"无效账号状态: {account.status}")
    if "update_rhythm" in provided and account.update_rhythm not in VALID_RHYTHM:
        raise HTTPException(status_code=400, detail=f"无效更新节奏: {account.update_rhythm}")
    if "responsible_id" in provided and account.responsible_id:
        if not db.query(User).get(account.responsible_id):
            raise HTTPException(status_code=400, detail="责任人不存在")
    if "tags" in provided:
        account.tags = list(data.tags or [])
    account.updated_at = datetime.now()


def _snapshot_bases(db: Session, account_ids: list[int]) -> dict:
    """批量取每个账号的最新快照与倒数第二条快照。

    返回 ``{account_id: (latest, previous)}``；最新快照自带 prev_* 时即为增量基准，
    否则回退用倒数第二条（兼容历史库）。一次查询避免 N+1。
    """
    if not account_ids:
        return {}
    rows = (
        db.query(PublishAccountSnapshot)
        .filter(PublishAccountSnapshot.account_id.in_(account_ids))
        .order_by(
            PublishAccountSnapshot.account_id.asc(),
            PublishAccountSnapshot.snapshot_at.desc(),
            PublishAccountSnapshot.id.desc(),
        )
        .all()
    )
    result = {}
    for row in rows:
        entry = result.setdefault(row.account_id, [None, None])
        if entry[0] is None:
            entry[0] = row
        elif entry[1] is None:
            entry[1] = row
    return result


@router.get("", response_model=list[PublishAccountOut])
def list_accounts(
    keyword: str = "",
    platform: str = "",
    scope: str = "all",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(PublishAccount).options(joinedload(PublishAccount.responsible))
    q = scope_filter(q, PublishAccount, user, scope)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            or_(
                PublishAccount.name.like(like),
                PublishAccount.account_id.like(like),
                PublishAccount.note.like(like),
            )
        )
    if platform:
        q = q.filter(PublishAccount.platform == platform)
    rows = q.order_by(PublishAccount.id.desc()).all()
    bases = _snapshot_bases(db, [a.id for a in rows])
    result = []
    for a in rows:
        latest, previous = bases.get(a.id, (None, None))
        result.append(_to_out(a, user, latest, previous))
    return result


@router.get("/creators", response_model=list[dict])
def list_creators(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """责任人下拉：仅「创作」角色的活跃成员，登录用户均可读取。"""
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


@router.get("/reminders", response_model=list[UpdateReminderOut])
def account_reminders(
    scope: str = "all",
    only_due: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新提醒：按账号更新节奏与最近发布时间，计算是否到期需要更新。

    仅统计「正常」状态账号；搁置 / 废弃不参与提醒。
    最近一次发布时间取已发布视频的 published_at。
    """
    q = db.query(PublishAccount).options(joinedload(PublishAccount.responsible))
    q = scope_filter(q, PublishAccount, user, scope)
    q = q.filter(PublishAccount.status == "正常")
    accounts = q.all()

    # 批量取每个账号最近一次发布时间（已发布视频）
    account_ids = [a.id for a in accounts]
    latest_published = {}
    if account_ids:
        rows = (
            db.query(Production.publish_account_id, Production.published_at)
            .filter(
                Production.publish_account_id.in_(account_ids),
                Production.status.in_(["已发布", "已完成"]),
                Production.published_at.isnot(None),
            )
            .all()
        )
        for aid, published_at in rows:
            if aid not in latest_published or published_at > latest_published[aid]:
                latest_published[aid] = published_at

    today = datetime.now().date()
    result = []
    for account in accounts:
        # 抖音账号离线：自动更新会跳过，页头消息优先提示重新扫码，不再重复提示排期
        is_douyin = (
            "抖音" in (account.platform or "")
            or bool(account.douyin_uid)
            or bool(account.sec_uid)
            or "douyin.com" in (account.home_url or "")
        )
        if is_douyin and account.douyin_login_status != "已登录":
            result.append(
                UpdateReminderOut(
                    account_id=account.id,
                    account_name=account.name,
                    platform=account.platform or "",
                    avatar=account.avatar or "",
                    status=account.status or "正常",
                    update_rhythm=account.update_rhythm or "日更",
                    responsible_id=account.responsible_id,
                    responsible_name=_responsible_name(account),
                    last_published_at=None,
                    days_since=-1,
                    due_in_days=0,
                    is_due=True,
                    reason="账号离线，自动更新已跳过，请重新扫码登录",
                    kind="offline",
                    is_offline=True,
                    action_label="去登录",
                )
            )
            continue

        rhythm = account.update_rhythm or "日更"
        interval = RHYTHM_DAYS.get(rhythm, 1)
        last = latest_published.get(account.id)
        if last:
            days_since = (today - last.date()).days
            due_in = interval - days_since
        else:
            days_since = -1
            due_in = 0  # 从未发布视为已到期
        is_due = days_since < 0 or days_since >= interval
        if only_due and not is_due:
            continue
        if days_since < 0:
            reason = "从未发布，去排期第一条视频"
        elif is_due:
            reason = f"已 {days_since} 天未更新（{rhythm}），去排期"
        else:
            reason = f"距下次更新还有 {due_in} 天"
        result.append(
            UpdateReminderOut(
                account_id=account.id,
                account_name=account.name,
                platform=account.platform or "",
                avatar=account.avatar or "",
                status=account.status or "正常",
                update_rhythm=rhythm,
                responsible_id=account.responsible_id,
                responsible_name=_responsible_name(account),
                last_published_at=last,
                days_since=days_since,
                due_in_days=due_in,
                is_due=is_due,
                reason=reason,
                kind="schedule",
                is_offline=False,
                action_label="去排期",
            )
        )
    result.sort(key=lambda r: (not r.is_offline, not r.is_due, -r.days_since, r.account_id))
    return result


@router.post("/{account_id}/schedule", response_model=dict)
def schedule_from_reminder(
    account_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新提醒 → 联动创意灵感：为账号一键生成一条「未使用 + 备选标记」创意。"""
    require_create(user)
    account = db.query(PublishAccount).get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="发布账号不存在")
    title = f"{account.name} · {account.update_rhythm or '日更'}更新"
    # 制作人只能选「创作」角色：优先用账号责任人，其次取任一创作角色成员
    creator_id = account.responsible_id
    valid_creator = (
        db.query(User)
        .filter(User.id == creator_id, User.is_active.is_(True), User.module_role == "production")
        .first()
        if creator_id
        else None
    )
    if not valid_creator:
        creator_id = (
            db.query(User.id)
            .filter(User.is_active.is_(True), User.module_role == "production")
            .order_by(User.id.asc())
            .scalar()
        )
    if not creator_id:
        creator_id = user.id
    idea = Idea(
        title=title,
        status="未使用",
        is_backup=True,
        priority=2,
        remark=f"由账号「{account.name}」更新提醒一键排期生成",
        creator_id=creator_id,
        owner_id=user.id,
        cover="", douyin_url="", video_id="", share_text="", author="", tags=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return {"id": idea.id, "title": idea.title, "status": idea.status, "account_id": account.id}


@router.post("", response_model=PublishAccountOut)
def create_account(
    data: PublishAccountIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_create(user)
    require_permission(user, "publish-accounts.create", db)
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="账号名称不能为空")
    account = PublishAccount(owner_id=user.id)
    _apply_in(db, account, data)
    account.name = name
    db.add(account)
    db.flush()
    collect_tags(db, account.tags)
    db.commit()
    db.refresh(account)
    return _to_out(account, user)


@router.get("/{account_id}", response_model=PublishAccountOut)
def get_account(
    account_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    account = db.query(PublishAccount).get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="发布账号不存在")
    return _to_out(account, user)


@router.put("/{account_id}", response_model=PublishAccountOut)
def update_account(
    account_id: int,
    data: PublishAccountIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    account = db.query(PublishAccount).get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="发布账号不存在")
    ensure_owner(account, user, "编辑")
    require_permission(user, "publish-accounts.edit", db)
    _apply_in(db, account, data)
    collect_tags(db, account.tags)
    db.commit()
    db.refresh(account)
    return _to_out(account, user)


@router.delete("/{account_id}")
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    account = db.query(PublishAccount).get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="发布账号不存在")
    ensure_owner(account, user, "删除")
    require_permission(user, "publish-accounts.delete", db)
    used = db.query(Production).filter(Production.publish_account_id == account_id).count()
    if used:
        raise HTTPException(
            status_code=400, detail=f"该发布账号下有 {used} 条关联记录，无法删除"
        )
    # 历史快照随账号一起清理，避免留下孤立记录
    db.query(PublishAccountSnapshot).filter(PublishAccountSnapshot.account_id == account_id).delete()
    db.delete(account)
    db.commit()
    return {"ok": True}


@router.get("/{account_id}/videos")
def account_videos(
    account_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """该账号下的视频记录，用于账号详情抽屉。"""
    account = db.query(PublishAccount).get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="发布账号不存在")
    rows = (
        db.query(Production)
        .filter(Production.publish_account_id == account_id)
        .order_by(Production.published_at.desc().nullslast(), Production.id.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": p.id,
                "title": p.title or "",
                "cover": p.cover or "",
                "tags": list(p.tags or []),
                "video_file": p.video_file or "",
                "publish_platform": p.publish_platform or "",
                "published_at": p.published_at,
                "status": p.status,
            }
            for p in rows
        ],
        "total": len(rows),
    }
