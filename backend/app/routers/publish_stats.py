from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload, selectinload

from ..auth import ensure_owner, get_current_user, require_permission, scope_filter
from ..database import get_db
from ..models import DouyinImport, Idea, Production, PublishAccount, PublishStat, User
from ..workflow import (
    STATUS_PENDING,
    bind_publish,
    clear_binding_video,
    has_binding,
    unbind_publish,
)
from ..schemas import (
    DataStatusUpdate,
    DouyinImportIn,
    DouyinImportItemOut,
    DouyinImportMatchIn,
    DouyinImportOut,
    DouyinImportUpdate,
    PublishStatBatchIn,
    PublishStatBatchOut,
    PublishStatIn,
    PublishStatOut,
    PublishStatUpdate,
)

router = APIRouter(prefix="/publish-stats", tags=["publish-stats"])

VALID_DATA_STATUS = {"正常", "隐藏"}


def _latest_stat(production: Production) -> Optional[PublishStat]:
    if not production.stats:
        return None
    return sorted(production.stats, key=lambda s: s.recorded_at or datetime.min)[-1]


@router.get("", response_model=list[PublishStatOut])
def list_stats(
    production_id: Optional[int] = None,
    scope: str = "all",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(PublishStat).join(Production)
    q = scope_filter(q, Production, user, scope)
    if production_id is not None:
        q = q.filter(PublishStat.production_id == production_id)
    rows = q.order_by(PublishStat.recorded_at.desc()).all()
    return [PublishStatOut.model_validate(s) for s in rows]


def _account_key(publish_account_id, account_name: str) -> str:
    """账号分组键：优先绑定账号 ID，兼容旧的快照账号名，未归属单列。"""
    if publish_account_id:
        return f"id:{publish_account_id}"
    if account_name:
        return f"name:{account_name}"
    return "none"


def _account_label(publish_account_name: str, account_name: str) -> str:
    return (publish_account_name or account_name or "未分配账号").strip() or "未分配账号"


@router.get("/summary")
def summary(
    scope: str = "all",
    account_key: str = "",
    data_status: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """已发布视频的数据汇总：按账号分组可选，逐条最新数据 + 总计 + 账号分组列表。

    「隐藏」记录会显示但不计入 KPI 总计；账号资料中的作品数可能大于已录入条数，
    差额通过 unrecorded_count 返回，不再伪装成「隐藏」标签数量。
    """
    q = db.query(Production).options(
        joinedload(Production.idea),
        joinedload(Production.category),
        joinedload(Production.publish_account),
        joinedload(Production.owner),
        selectinload(Production.stats),
    )
    q = scope_filter(q, Production, user, scope)
    q = q.filter(Production.status == "已完成")
    # 状态计数需覆盖全部状态（不受 data_status 筛选影响），故此处只排除已删除记录
    q = q.filter(Production.data_status != "删除")

    # 抖音采集作品直接显示在发布数据表：先取出本范围内的采集行，已关联的创作记录不再重复成行
    iq = db.query(DouyinImport).options(joinedload(DouyinImport.owner))
    iq = scope_filter(iq, DouyinImport, user, scope)
    import_rows = iq.order_by(DouyinImport.created_at.desc(), DouyinImport.id.desc()).all()
    matched_production_ids = {r.production_id for r in import_rows if r.production_id}

    rows = []
    total = {"plays": 0, "likes": 0, "comments": 0, "collects": 0, "shares": 0}
    normal_count = 0  # 正常记录数：统计口径只认正常，隐藏仅用于展示
    accounts = {}
    # 去掉「删除」状态：只统计正常/隐藏，计数不受当前 data_status 筛选影响
    status_counts = {"正常": 0, "隐藏": 0}
    for p in q.order_by(Production.published_at.desc().nullslast(), Production.id.desc()).all():
        if p.id in matched_production_ids:
            continue
        latest = _latest_stat(p)
        row_status = p.data_status or "正常"
        account_name = (latest.account if latest else "") or ""
        acc_name = (p.publish_account.name if p.publish_account else "") or account_name
        key = _account_key(p.publish_account_id, account_name)
        label = _account_label(acc_name, account_name)
        group = accounts.setdefault(
            key,
            {
                "key": key,
                "name": label,
                "count": 0,
                "plays": 0,
                "likes": 0,
                "comments": 0,
                "collects": 0,
                "shares": 0,
                "followers": 0,
                "avatar": "",
                "is_registered": False,
            },
        )
        acc_metrics = {
            "plays": latest.plays if latest else 0,
            "likes": latest.likes if latest else 0,
            "comments": latest.comments if latest else 0,
            "collects": latest.collects if latest else 0,
            "shares": latest.shares if latest else 0,
        }
        # 账号分组指标同样只统计正常记录
        if row_status == "正常":
            group["count"] += 1
            for k, v in acc_metrics.items():
                group[k] += v
        if account_key and account_key != key:
            continue
        # KPI 与条数只统计「正常」记录：隐藏 / 删除不计入，且不受 data_status 筛选影响
        # （切换「隐藏」筛选时统计不应归零，仍展示正常视频的成果）
        if row_status == "正常":
            normal_count += 1
            for k in total:
                total[k] += acc_metrics[k]
        # 状态计数覆盖全部状态，不受当前 data_status 筛选影响（只统计正常/隐藏）
        if row_status in status_counts:
            status_counts[row_status] += 1
        # 状态筛选只影响展示行，不影响计数
        if data_status and row_status != data_status:
            continue
        item = {
            "production_id": p.id,
            "stat_id": (latest.id if latest else None),
            "title": p.title or "",
            "cover": p.cover or "",
            "tags": list(p.tags or []),
            "video_file": p.video_file or "",
            "category_id": p.category_id,
            "category_name": p.category.name if p.category else None,
            "platform": p.platform,
            "publish_platform": p.publish_platform,
            "publish_account_id": p.publish_account_id,
            "publish_account_name": (p.publish_account.name if p.publish_account else ""),
            "account_key": key,
            "data_status": row_status,
            "published_at": p.published_at,
            "published_url": p.published_url,
            "owner_name": (p.owner.nickname or p.owner.username) if p.owner else "未归属",
            "duration": p.duration,
            "plays": latest.plays if latest else 0,
            "likes": latest.likes if latest else 0,
            "comments": latest.comments if latest else 0,
            "collects": latest.collects if latest else 0,
            "shares": latest.shares if latest else 0,
            "account": (latest.account if latest else "") or "",
            "source": (latest.source if latest else "manual") or "manual",
            "recorded_at": latest.recorded_at if latest else None,
            "snapshot_count": len(p.stats),
        }
        rows.append(item)

    # 抖音采集行：作为发布数据表格中的普通一行，第二行显示匹配到的参考视频名称（未匹配为「未配置」）
    import_accounts = {a.id: a for a in db.query(PublishAccount).all()}
    video_ids = [r.video_id for r in import_rows if r.video_id]
    stats_by_video_id = {}
    if video_ids:
        stats_by_video_id = {
            s.video_id: s
            for s in db.query(PublishStat).filter(PublishStat.video_id.in_(video_ids)).all()
        }
    matched_productions = {}
    if matched_production_ids:
        matched_productions = {
            p.id: p
            for p in db.query(Production)
            .options(
                joinedload(Production.idea),
                joinedload(Production.category),
                joinedload(Production.publish_account),
                joinedload(Production.owner),
            )
            .filter(Production.id.in_(matched_production_ids))
            .all()
        }
    for r in import_rows:
        prod = matched_productions.get(r.production_id) if r.production_id else None
        stat = stats_by_video_id.get(r.video_id)
        row_status = (prod.data_status if prod else r.data_status) or "正常"
        acc = import_accounts.get(r.account_id) if r.account_id else None
        key = _account_key(r.account_id, r.account_name)
        label = _account_label(acc.name if acc else "", r.account_name)
        group = accounts.setdefault(
            key,
            {
                "key": key,
                "name": label,
                "count": 0,
                "plays": 0,
                "likes": 0,
                "comments": 0,
                "collects": 0,
                "shares": 0,
                "followers": 0,
                "avatar": (acc.avatar if acc else "") or "",
                "is_registered": bool(acc),
            },
        )
        metrics = {
            "plays": stat.plays if stat else r.plays,
            "likes": stat.likes if stat else r.likes,
            "comments": stat.comments if stat else r.comments,
            "collects": stat.collects if stat else r.collects,
            "shares": stat.shares if stat else r.shares,
        }
        # 账号分组指标同样只统计正常记录
        if row_status == "正常":
            group["count"] += 1
            for k, v in metrics.items():
                group[k] += v
        if account_key and account_key != key:
            continue
        # KPI 与条数只统计「正常」记录：隐藏 / 删除不计入，且不受 data_status 筛选影响
        if row_status == "正常":
            normal_count += 1
            for k in total:
                total[k] += metrics[k]
        # 状态计数覆盖全部状态，不受 data_status 筛选影响（只统计正常/隐藏）
        if row_status in status_counts:
            status_counts[row_status] += 1
        # 状态筛选只影响展示行，不影响计数；已删除记录不展示
        if row_status == "删除" or (data_status and row_status != data_status):
            continue
        published_at = None
        if r.create_time:
            try:
                published_at = datetime.fromtimestamp(int(r.create_time))
            except (ValueError, OSError, TypeError):
                published_at = None
        owner_name = "未配置" if not prod else "未归属"
        if prod and prod.owner:
            owner_name = prod.owner.nickname or prod.owner.username or "未归属"
        item = {
            "production_id": r.production_id,
            "stat_id": stat.id if stat else None,
            "import_id": r.id,
            "video_id": r.video_id,
            "title": r.title or "未命名作品",
            "cover": r.cover or "",
            "reference_title": (prod.title if prod else "") or "",
            # 话题标签与时长均取抖音已发布视频自身的采集数据，不回退到关联创作记录
            "tags": list(r.tags or []),
            "video_file": (prod.video_file or "") if prod else "",
            "category_id": (prod.category_id if prod else None),
            "category_name": (prod.category.name if prod and prod.category else None),
            "platform": (prod.platform if prod else "") or "",
            "publish_platform": (prod.publish_platform if prod else "") or "抖音",
            "publish_account_id": r.account_id,
            "publish_account_name": (acc.name if acc else "") or r.account_name or "",
            "account_key": key,
            "data_status": row_status,
            "published_at": published_at or (prod.published_at if prod else None),
            "published_url": (prod.published_url if prod else "") or "",
            "owner_name": owner_name,
            "duration": r.duration,
            "source": "auto",
            "account": r.account_name or (acc.name if acc else ""),
            "recorded_at": (stat.recorded_at if stat else None),
            "snapshot_count": (1 if stat else 0),
            **metrics,
        }
        rows.append(item)

    # 发布数据列表按发布时间倒序；时间相同或缺失时按导入/创作 id 倒序保持稳定
    rows.sort(
        key=lambda x: (
            x.get("published_at") or datetime.min,
            x.get("import_id") or x.get("production_id") or 0,
        ),
        reverse=True,
    )

    # 账号分组：以「我的账号」中已添加的账号为准，未发过视频的账号也要显示（作品数量取账号资料）
    aq = db.query(PublishAccount)
    aq = scope_filter(aq, PublishAccount, user, scope)
    for a in aq.order_by(PublishAccount.id).all():
        key = _account_key(a.id, "")
        group = accounts.setdefault(
            key,
            {
                "key": key,
                "name": a.name or "",
                "count": 0,
                "plays": 0,
                "likes": 0,
                "comments": 0,
                "collects": 0,
                "shares": 0,
                "followers": 0,
                "avatar": a.avatar or "",
                "is_registered": True,
            },
        )
        group["name"] = a.name or group["name"]
        group["count"] = int(a.video_count or 0)
        group["followers"] = int(a.followers_count or 0)
        group["avatar"] = a.avatar or ""
        group["is_registered"] = True

    # 账号分组：已添加账号排前，按作品数倒序，便于前端渲染 tab
    account_groups = sorted(
        accounts.values(),
        key=lambda g: (not g["is_registered"], g["key"] == "none", -g["count"], g["name"]),
    )
    total["followers"] = sum(
        int(g.get("followers") or 0)
        for g in account_groups
        if not account_key or g["key"] == account_key
    )

    # 「全部」保持账号资料作品总数；「隐藏」只统计已录入的隐藏行，
    # 账号作品数与已录入条数的差额单独返回，不再伪装成隐藏数据。
    selected_group = next((g for g in account_groups if g["key"] == account_key), None) if account_key else None
    works_total = int(selected_group["count"]) if selected_group else 0
    actual_normal = status_counts["正常"]
    actual_hidden = status_counts["隐藏"]
    status_counts["全部"] = max(actual_normal + actual_hidden, works_total)
    unrecorded_count = max(0, status_counts["全部"] - actual_normal - actual_hidden)
    status_counts["隐藏"] = actual_hidden

    return {
        "items": rows,
        "total": total,
        # count 为统计口径：只算正常记录，隐藏 / 删除不计入（KPI 卡片直接取此值）
        "count": normal_count,
        "row_count": len(rows),  # 当前筛选下实际展示行数
        "accounts": account_groups,
        "account_key": account_key,
        "data_status": data_status,
        "status_counts": status_counts,
        "unrecorded_count": unrecorded_count,  # 账号作品数 - 已录入条数（未录入，不计入隐藏）
    }


@router.put("/status/{production_id}")
def update_data_status(
    production_id: int,
    data: DataStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """切换数据中心记录状态：正常 / 隐藏（不再提供删除状态）。"""
    if data.status not in VALID_DATA_STATUS:
        raise HTTPException(status_code=400, detail=f"无效记录状态: {data.status}")
    production = db.query(Production).get(production_id)
    if not production:
        raise HTTPException(status_code=404, detail="制作记录不存在")
    ensure_owner(production, user, "修改数据状态")
    require_permission(user, "publish-stats.edit", db)
    production.data_status = data.status
    production.updated_at = datetime.now()
    for imp in db.query(DouyinImport).filter(DouyinImport.production_id == production_id).all():
        imp.data_status = data.status
    db.commit()
    db.refresh(production)
    return {
        "ok": True,
        "production_id": production_id,
        "data_status": production.data_status,
    }


def _advance_production(db: Session, production: Production, video_id: str = "") -> None:
    """写入发布数据即绑定事件：由统一状态机推进到「已发布」。"""
    bind_publish(db, production, video_id)


def _apply_stat_values(stat: PublishStat, data: PublishStatIn) -> None:
    stat.plays = max(0, data.plays)
    stat.likes = max(0, data.likes)
    stat.comments = max(0, data.comments)
    stat.collects = max(0, data.collects)
    stat.shares = max(0, data.shares)
    stat.account = (data.account or "").strip()
    stat.source = data.source or "manual"
    stat.video_id = (data.video_id or "").strip()
    stat.recorded_at = data.recorded_at or datetime.now()


def _upsert_stat(db: Session, production: Production, data: PublishStatIn) -> tuple:
    """带 video_id 的采集数据按作品唯一 ID 去重：已存在就更新那条，否则新增。

    video_id 为空（手工录入）时不按作品去重，保持每次录入一条快照的历史留痕。
    返回 (stat, is_new)。
    """
    video_id = (data.video_id or "").strip()
    existing = None
    if video_id:
        existing = db.query(PublishStat).filter(PublishStat.video_id == video_id).first()
    if existing:
        _apply_stat_values(existing, data)
        _advance_production(db, production, video_id)
        return existing, False
    stat = PublishStat(
        production_id=production.id,
        plays=max(0, data.plays),
        likes=max(0, data.likes),
        comments=max(0, data.comments),
        collects=max(0, data.collects),
        shares=max(0, data.shares),
        account=(data.account or "").strip(),
        source=(data.source or "manual"),
        video_id=video_id,
        recorded_at=data.recorded_at or datetime.now(),
    )
    db.add(stat)
    _advance_production(db, production, video_id)
    return stat, True


@router.post("", response_model=PublishStatOut)
def create_stat(
    data: PublishStatIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    production = db.query(Production).get(data.production_id)
    if not production:
        raise HTTPException(status_code=404, detail="制作记录不存在")
    ensure_owner(production, user, "记录数据")
    require_permission(user, "publish-stats.create", db)
    stat, _ = _upsert_stat(db, production, data)
    db.commit()
    db.refresh(stat)
    return stat


@router.post("/batch", response_model=PublishStatBatchOut)
def batch_create_stats(
    data: PublishStatBatchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量写入快照：带 video_id 的作品按唯一 ID 去重更新；无效或无权限记录跳过。"""
    require_permission(user, "publish-stats.create", db)
    created = 0
    updated = 0
    skipped = 0
    seen = {}  # 同一批次内 video_id 去重
    for item in data.items:
        production = db.query(Production).get(item.production_id)
        if not production:
            skipped += 1
            continue
        try:
            ensure_owner(production, user, "批量记录数据")
        except HTTPException:
            skipped += 1
            continue
        video_id = (item.video_id or "").strip()
        if video_id and video_id in seen:
            _apply_stat_values(seen[video_id], item)
            updated += 1
            continue
        stat, is_new = _upsert_stat(db, production, item)
        if video_id:
            seen[video_id] = stat
        if is_new:
            created += 1
        else:
            updated += 1
    if created or updated:
        db.commit()
    message = f"新增 {created} 条、更新 {updated} 条快照"
    if skipped:
        message += f"，跳过 {skipped} 条无效记录"
    return PublishStatBatchOut(
        ok=created + updated > 0,
        created=created,
        updated=updated,
        skipped=skipped,
        message=message,
    )


def _import_item_out(row: DouyinImport, db: Session) -> DouyinImportItemOut:
    out = DouyinImportItemOut.model_validate(row)
    if row.production_id:
        prod = db.query(Production).get(row.production_id)
        out.production_title = (prod.title if prod else "") or ""
    return out


@router.post("/import-douyin", response_model=DouyinImportOut)
def import_douyin_videos(
    data: DouyinImportIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """把抖音采集的作品导入「待匹配池」，不做自动匹配。

    导入后作品停留在待匹配状态，用户在发布数据表格里手动选一条创作记录
    完成匹配；按作品唯一 ID video_id 去重，重复导入只更新、不重复新建。
    """
    require_permission(user, "productions.create", db)
    created = 0
    updated = 0
    skipped = 0
    seen = set()
    for v in data.videos:
        video_id = (v.video_id or "").strip()
        if not video_id:
            skipped += 1
            continue
        if video_id in seen:  # 同一批次内重复
            skipped += 1
            continue
        seen.add(video_id)

        row = db.query(DouyinImport).filter(DouyinImport.video_id == video_id).first()
        if row:
            row.title = v.title or row.title
            row.cover = v.cover or row.cover
            row.tags = list(v.tags or [])
            row.plays = max(0, v.plays)
            row.likes = max(0, v.likes)
            row.comments = max(0, v.comments)
            row.collects = max(0, v.collects)
            row.shares = max(0, v.shares)
            row.create_time = v.create_time
            row.duration = v.duration
            row.account_id = v.account_id
            row.account_name = v.account_name or ""
            if v.data_status:
                row.data_status = v.data_status
            updated += 1
            continue

        db.add(
            DouyinImport(
                video_id=video_id,
                title=(v.title or "未命名作品").strip() or "未命名作品",
                cover=(v.cover or "").strip(),
                tags=list(v.tags or []),
                plays=max(0, v.plays),
                likes=max(0, v.likes),
                comments=max(0, v.comments),
                collects=max(0, v.collects),
                shares=max(0, v.shares),
                create_time=v.create_time,
                duration=v.duration,
                account_id=v.account_id,
                account_name=(v.account_name or "").strip(),
                status="待匹配",
                data_status=v.data_status or "正常",
                owner_id=user.id,
            )
        )
        created += 1

    if created or updated:
        db.commit()
    message = f"导入完成：新增 {created} 条、更新 {updated} 条待匹配作品"
    if skipped:
        message += f"，跳过 {skipped} 条"
    return DouyinImportOut(
        ok=created + updated > 0,
        created=created,
        updated=updated,
        skipped=skipped,
        message=message,
    )


@router.get("/imports", response_model=list[DouyinImportItemOut])
def list_imports(
    status: str = "",
    scope: str = "all",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出待匹配池：默认全部，可传 status=待匹配 / 已匹配。"""
    q = db.query(DouyinImport)
    q = scope_filter(q, DouyinImport, user, scope)
    if status:
        q = q.filter(DouyinImport.status == status)
    rows = q.order_by(DouyinImport.created_at.desc(), DouyinImport.id.desc()).all()
    return [_import_item_out(r, db) for r in rows]


@router.put("/imports/{import_id}", response_model=DouyinImportItemOut)
def update_import(
    import_id: int,
    data: DouyinImportUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """直接在发布数据表里编辑一条抖音采集行的数据。"""
    require_permission(user, "publish-stats.edit", db)
    row = db.query(DouyinImport).get(import_id)
    if not row:
        raise HTTPException(status_code=404, detail="采集记录不存在")
    if row.production_id:
        production = db.query(Production).get(row.production_id)
        if production:
            ensure_owner(production, user, "修改数据")
    row.plays = max(0, data.plays)
    row.likes = max(0, data.likes)
    row.comments = max(0, data.comments)
    row.collects = max(0, data.collects)
    row.shares = max(0, data.shares)
    row.account_name = (data.account_name or "").strip()
    # 已关联创作记录时，同一行的数据快照同步更新，避免表格显示旧值
    stat = db.query(PublishStat).filter(PublishStat.video_id == row.video_id).first()
    if stat:
        stat.plays = row.plays
        stat.likes = row.likes
        stat.comments = row.comments
        stat.collects = row.collects
        stat.shares = row.shares
        stat.account = row.account_name
    db.commit()
    db.refresh(row)
    return _import_item_out(row, db)


@router.put("/imports/{import_id}/status", response_model=dict)
def update_import_status(
    import_id: int,
    data: DataStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """未关联创作记录的采集行也能直接切换数据状态。"""
    if data.status not in VALID_DATA_STATUS:
        raise HTTPException(status_code=400, detail=f"无效记录状态: {data.status}")
    require_permission(user, "publish-stats.edit", db)
    row = db.query(DouyinImport).get(import_id)
    if not row:
        raise HTTPException(status_code=404, detail="采集记录不存在")
    row.data_status = data.status
    if row.production_id:
        production = db.query(Production).get(row.production_id)
        if production:
            ensure_owner(production, user, "修改数据状态")
            production.data_status = data.status
            production.updated_at = datetime.now()
    db.commit()
    return {"ok": True, "import_id": import_id, "data_status": row.data_status}


@router.get("/match-options")
def match_options(
    scope: str = "all",
    exclude_production_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """匹配弹窗候选项：仅返回未关联到发布数据的「待发布」创作记录。

    已被采集作品或数据快照关联的创作记录不再作为候选；当前已关联项由前端
    单独置顶展示，可通过 exclude_production_id 从候选列表中剔除。
    """
    linked_ids = {
        row[0]
        for row in db.query(DouyinImport.production_id)
        .filter(DouyinImport.production_id.isnot(None))
        .all()
    }
    linked_ids |= {
        row[0]
        for row in db.query(PublishStat.production_id)
        .filter(PublishStat.production_id.isnot(None))
        .all()
    }

    q = db.query(Production).options(joinedload(Production.owner), joinedload(Production.category))
    q = scope_filter(q, Production, user, scope)
    q = q.filter(Production.status == "待发布")
    if linked_ids:
        q = q.filter(~Production.id.in_(linked_ids))
    if exclude_production_id is not None:
        q = q.filter(Production.id != exclude_production_id)
    rows = q.order_by(Production.updated_at.desc().nullslast(), Production.id.desc()).all()

    return {
        "items": [
            {
                "id": p.id,
                "title": p.title or "未命名视频",
                "cover": p.cover or "",
                "author": p.author or "",
                "owner_name": (p.owner.nickname or p.owner.username) if p.owner else "未归属",
                "category_name": p.category.name if p.category else "",
                "status": p.status or "",
            }
            for p in rows
        ]
    }


@router.post("/imports/{import_id}/match", response_model=DouyinImportItemOut)
def match_import(
    import_id: int,
    data: DouyinImportMatchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """手动把待匹配作品关联到一条创作记录：改状态为已完成 + 写入数据快照。"""
    require_permission(user, "publish-stats.create", db)
    require_permission(user, "productions.edit", db)
    row = db.query(DouyinImport).get(import_id)
    if not row:
        raise HTTPException(status_code=404, detail="待匹配作品不存在")
    production = db.query(Production).get(data.production_id)
    if not production:
        raise HTTPException(status_code=404, detail="创作记录不存在")
    ensure_owner(production, user, "关联抖音作品")

    published_at = None
    if row.create_time:
        try:
            published_at = datetime.fromtimestamp(int(row.create_time))
        except (ValueError, OSError, TypeError):
            published_at = None

    # 重新匹配：旧创作记录若没有其他数据快照，退回「待发布」，避免残留一条已完成空记录
    old_pid = row.production_id
    if old_pid and old_pid != production.id:
        old_production = db.query(Production).get(old_pid)
        if old_production:
            other_stats = (
                db.query(PublishStat)
                .filter(PublishStat.production_id == old_pid, PublishStat.video_id != row.video_id)
                .count()
            )
            other_imports = (
                db.query(DouyinImport)
                .filter(DouyinImport.production_id == old_pid, DouyinImport.id != import_id)
                .count()
            )
            if not other_stats and not other_imports:
                clear_binding_video(old_production, row.video_id)
                unbind_publish(db, old_production)

    # 关联创作记录：状态由 _upsert_stat 的绑定事件统一推进到「已发布」
    row.production_id = production.id
    row.status = "已匹配"
    row.data_status = production.data_status or "正常"
    row.matched_at = datetime.now()
    if row.account_id:
        production.publish_account_id = row.account_id
    if not production.publish_platform:
        production.publish_platform = "抖音"

    # 数据快照按 video_id 去重写入
    stat_in = PublishStatIn(
        production_id=production.id,
        plays=row.plays,
        likes=row.likes,
        comments=row.comments,
        collects=row.collects,
        shares=row.shares,
        account=row.account_name or "",
        source="auto",
        video_id=row.video_id,
        recorded_at=published_at,
    )
    # 同一作品若已有快照（重新匹配时），把快照挪到新的创作记录上，不重复建行
    existing_stat = db.query(PublishStat).filter(PublishStat.video_id == row.video_id).first()
    if existing_stat and existing_stat.production_id != production.id:
        existing_stat.production_id = production.id
    _upsert_stat(db, production, stat_in)
    db.commit()
    db.refresh(row)
    return _import_item_out(row, db)


@router.post("/imports/{import_id}/unmatch", response_model=dict)
def unmatch_import(
    import_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """取消发布数据与创作记录的关联：创作记录回退「待发布」，来源创意同步回退。"""
    require_permission(user, "publish-stats.create", db)
    row = db.query(DouyinImport).get(import_id)
    if not row:
        raise HTTPException(status_code=404, detail="待匹配作品不存在")
    production_id = row.production_id
    if not production_id:
        return {"ok": True, "import_id": import_id, "production_id": None}

    production = db.query(Production).get(production_id)
    if production:
        ensure_owner(production, user, "取消关联")
    # 该作品对应的数据快照随解绑移除，否则仍视为已发布
    for stat in db.query(PublishStat).filter(
        PublishStat.production_id == production_id, PublishStat.video_id == row.video_id
    ).all():
        db.delete(stat)
    row.production_id = None
    row.status = "待匹配"
    row.matched_at = None
    db.flush()
    if production:
        clear_binding_video(production, row.video_id)
        if not has_binding(db, production):
            unbind_publish(db, production)
    db.commit()
    return {"ok": True, "import_id": import_id, "production_id": None}


@router.delete("/imports/{import_id}", response_model=dict)
def delete_import(
    import_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """从待匹配池移除一条作品（不删除已关联的创作记录 / 数据）。"""
    row = db.query(DouyinImport).get(import_id)
    if not row:
        raise HTTPException(status_code=404, detail="待匹配作品不存在")
    db.delete(row)
    db.commit()
    return {"ok": True, "id": import_id}


@router.put("/{stat_id}", response_model=PublishStatOut)
def update_stat(
    stat_id: int,
    data: PublishStatUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """修改一条数据快照（数据中心「编辑」操作）。"""
    stat = db.query(PublishStat).get(stat_id)
    if not stat:
        raise HTTPException(status_code=404, detail="数据记录不存在")
    production = db.query(Production).get(stat.production_id)
    if production:
        ensure_owner(production, user, "修改数据")
    require_permission(user, "publish-stats.edit", db)

    if "plays" in data.model_fields_set:
        stat.plays = max(0, data.plays)
    if "likes" in data.model_fields_set:
        stat.likes = max(0, data.likes)
    if "comments" in data.model_fields_set:
        stat.comments = max(0, data.comments)
    if "collects" in data.model_fields_set:
        stat.collects = max(0, data.collects)
    if "shares" in data.model_fields_set:
        stat.shares = max(0, data.shares)
    if "account" in data.model_fields_set:
        stat.account = (data.account or "").strip()
    if data.recorded_at is not None:
        stat.recorded_at = data.recorded_at

    # 表格里同一行也可能来自抖音采集，保持采集行的数据同步
    if stat.video_id:
        imp = db.query(DouyinImport).filter(DouyinImport.video_id == stat.video_id).first()
        if imp:
            imp.plays = stat.plays
            imp.likes = stat.likes
            imp.comments = stat.comments
            imp.collects = stat.collects
            imp.shares = stat.shares
            if stat.account:
                imp.account_name = stat.account

    db.commit()
    db.refresh(stat)
    return stat


@router.delete("/{stat_id}")
def delete_stat(
    stat_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stat = db.query(PublishStat).get(stat_id)
    if not stat:
        raise HTTPException(status_code=404, detail="数据记录不存在")
    production = db.query(Production).get(stat.production_id)
    if production:
        ensure_owner(production, user, "删除")
    require_permission(user, "publish-stats.delete", db)
    if stat.video_id:
        imp = db.query(DouyinImport).filter(DouyinImport.video_id == stat.video_id).first()
        if imp:
            db.delete(imp)
    db.delete(stat)
    db.flush()
    if production:
        clear_binding_video(production, stat.video_id)
        if not has_binding(db, production):
            unbind_publish(db, production)
    db.commit()
    return {"ok": True}
