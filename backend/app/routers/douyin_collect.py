"""抖音采集接口：账号资料抓取与视频数据抓取。

所有失败都会返回结构化提示（`manual_required`），由前端引导手工录入，
不会静默失败，也不会阻塞主流程。
"""
import threading
import time
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_permission
from ..auto_update_service import (
    create_account_snapshot,
    get_auto_update_config,
    reconcile_hidden_videos,
    sync_account_publish_videos,
)
from ..database import SessionLocal, get_db
from ..douyin_collector import (
    CollectError,
    fetch_account,
    fetch_account_videos,
    fetch_video,
    login_douyin,
    new_temp_profile_key,
)
from ..models import DouyinImport, Production, PublishAccount, PublishStat, User
from ..workflow import bind_publish
from ..schemas import (
    DouyinAccountFetchIn,
    DouyinAccountFetchOut,
    DouyinAccountSyncOneIn,
    DouyinAccountSyncOut,
    DouyinAccountVideosIn,
    DouyinVideosBatchIn,
    DouyinLoginIn,
    DouyinStatsFetchIn,
    DouyinStatsFetchOut,
    DouyinVideoAccountIn,
    DouyinVideosFetchIn,
    DouyinVideosFetchOut,
)

router = APIRouter(prefix="/douyin", tags=["douyin"])

# 远程扫码会话：服务端无头浏览器抓二维码，前端轮询状态并展示二维码。
# 会话只在内存中保存短时状态，登录态仍持久化在 data/douyin_profiles 目录。
_LOGIN_SESSIONS = {}
_LOGIN_LOCK = threading.Lock()
_LOGIN_TTL = 15 * 60


def _account_profile(db: Session, account_id: Optional[int]) -> tuple:
    """返回 (profile_key, account)；未指定账号时使用公共登录态。"""
    if not account_id:
        return "", None
    account = db.query(PublishAccount).get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="发布账号不存在")
    key = (account.douyin_profile or "").strip() or f"account_{account.id}"
    account.douyin_profile = key
    return key, account


def _capture_account_values(account) -> dict:
    """采集前记录账号三项指标，作为快照的增量基准。"""
    return {
        "video_count": account.video_count or 0,
        "likes_count": account.likes_count or 0,
        "followers_count": account.followers_count or 0,
    }


def _mark_login_state(account, ok: bool) -> None:
    """采集结果反写登录状态，方便前端提示该账号是否需要重新扫码。"""
    if not account:
        return
    # 采集成功只说明登录态可用；登录时间由扫码接口单独写入
    account.douyin_login_status = "已登录" if ok else "需验证"


@router.post("/account/fetch", response_model=DouyinAccountFetchOut)
def fetch_account_info(
    data: DouyinAccountFetchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按抖音号 / sec_uid / 主页链接抓取账号资料（粉丝、获赞、作品数）。"""
    profile_key, account = _account_profile(db, data.account_id)
    try:
        info = fetch_account(data.query, data.channel, profile_key=profile_key)
    except CollectError as exc:
        _mark_login_state(account, False)
        db.commit()
        return DouyinAccountFetchOut(
            ok=False,
            channel=exc.channel,
            message=exc.message,
            need_login=exc.need_login,
            data={"manual_hint": exc.manual_hint, "manual_required": True},
        )
    except Exception as exc:  # pragma: no cover
        return DouyinAccountFetchOut(
            ok=False,
            message=f"采集异常：{exc}",
            data={"manual_hint": "请手工填写账号信息", "manual_required": True},
        )
    _mark_login_state(account, True)
    db.commit()
    return DouyinAccountFetchOut(ok=True, channel=info.get("channel", ""), message="获取成功", data=info)


def _sync_account(db: Session, account: PublishAccount) -> None:
    """抓取单个账号资料并回填；失败抛出 CollectError 由调用方处理。"""
    query = account.home_url or account.douyin_uid or account.account_id
    if not query:
        raise CollectError("未填写抖音号或主页链接", manual_hint="请先扫码登录或在账号资料中填写抖音号")
    profile_key = (account.douyin_profile or "").strip() or f"account_{account.id}"
    account.douyin_profile = profile_key
    info = fetch_account(query, "auto", profile_key=profile_key)
    account.name = info.get("name") or account.name
    account.avatar = info.get("avatar") or account.avatar
    account.douyin_uid = info.get("douyin_uid") or account.douyin_uid
    account.sec_uid = info.get("sec_uid") or account.sec_uid
    account.home_url = info.get("home_url") or account.home_url
    account.followers_count = int(info.get("followers_count") or 0)
    account.likes_count = int(info.get("likes_count") or 0)
    account.video_count = int(info.get("video_count") or 0)
    account.last_synced_at = datetime.now()
    account.updated_at = datetime.now()
    _mark_login_state(account, True)


@router.post("/account/sync-one", response_model=dict)
def sync_one_account(
    data: DouyinAccountSyncOneIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新单个发布账号：抓取资料回填作品数 / 获赞 / 粉丝等。"""
    account = db.query(PublishAccount).get(data.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="发布账号不存在")
    snapshot = None
    before = _capture_account_values(account)
    videos_created = 0
    videos_updated = 0
    videos_fetched = 0
    video_note = ""
    try:
        _sync_account(db, account)
        # 账号更新作为总入口：同步发布数据（按配置中心的采集条数）
        cfg = get_auto_update_config(db)
        if cfg["sync_publish_data"]:
            try:
                videos_created, videos_updated, videos_fetched, hidden, restored = sync_account_publish_videos(
                    db, account, cfg["video_limit"]
                )
                video_note = f"同步发布数据 {videos_fetched} 条（新增 {videos_created} / 更新 {videos_updated}）"
                if hidden or restored:
                    video_note += f"；隐藏状态对账：新隐藏 {hidden} 条、恢复 {restored} 条"
            except CollectError as exc:
                video_note = f"发布数据同步失败：{exc.message}"
                if getattr(exc, "need_login", False):
                    _mark_login_state(account, False)
        snapshot = create_account_snapshot(
            account, source="manual", note="手动点击更新；" + video_note,
            fetched_video_count=videos_fetched, previous=before
        )
        db.add(snapshot)
        db.commit()
    except CollectError as exc:
        _mark_login_state(account, False)
        db.commit()
        return {
            "ok": False,
            "message": exc.message,
            "need_login": exc.need_login,
            "manual_hint": exc.manual_hint,
        }
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "message": f"采集异常：{exc}"}
    message = "已更新账号数据" + ("；" + video_note if video_note else "")
    return {
        "ok": True,
        "message": message,
        "videos_created": videos_created,
        "videos_updated": videos_updated,
        "snapshot_id": snapshot.id if snapshot else None,
        "account": {
            "id": account.id,
            "name": account.name,
            "avatar": account.avatar,
            "video_count": account.video_count,
            "likes_count": account.likes_count,
            "followers_count": account.followers_count,
            "last_synced_at": account.last_synced_at.isoformat(timespec="seconds") if account.last_synced_at else None,
        },
    }


@router.post("/account/sync-all", response_model=DouyinAccountSyncOut)
def sync_all_accounts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量同步抖音账号资料：逐个抓取并回填，返回成功/失败明细。"""
    accounts = db.query(PublishAccount).all()
    targets = []
    for account in accounts:
        platform = account.platform or ""
        home = account.home_url or ""
        if "抖音" in platform or "douyin.com" in home or account.douyin_uid:
            targets.append(account)
    succeeded = 0
    failed = []
    cfg = get_auto_update_config(db)
    videos_created_total = 0
    videos_updated_total = 0
    for account in targets:
        query = account.home_url or account.douyin_uid or account.account_id
        if not query:
            failed.append({"id": account.id, "name": account.name, "message": "未填写抖音号或主页链接"})
            continue
        try:
            before = _capture_account_values(account)
            _sync_account(db, account)
            note = "批量更新账号资料"
            fetched_video_count = 0
            if cfg["sync_publish_data"]:
                try:
                    created, updated, fetched, hidden, restored = sync_account_publish_videos(
                        db, account, cfg["video_limit"]
                    )
                    videos_created_total += created
                    videos_updated_total += updated
                    fetched_video_count = fetched
                    note += f"；同步发布数据 {fetched} 条"
                    if hidden or restored:
                        note += f"；隐藏对账：新隐藏 {hidden} 条、恢复 {restored} 条"
                except CollectError as exc:
                    note += f"；发布数据同步失败：{exc.message}"
                    if getattr(exc, "need_login", False):
                        _mark_login_state(account, False)
            db.add(create_account_snapshot(
                account, source="manual", note=note,
                fetched_video_count=fetched_video_count, previous=before
            ))
            succeeded += 1
        except CollectError as exc:
            _mark_login_state(account, False)
            failed.append({
                "id": account.id,
                "name": account.name,
                "message": exc.message,
                "need_login": exc.need_login,
            })
        except Exception as exc:  # pragma: no cover
            failed.append({"id": account.id, "name": account.name, "message": f"采集异常：{exc}"})
    db.commit()
    return DouyinAccountSyncOut(
        total=len(targets), succeeded=succeeded, failed=failed,
        videos_created=videos_created_total, videos_updated=videos_updated_total,
    )


@router.post("/videos/fetch", response_model=DouyinVideosFetchOut)
def fetch_account_videos_info(
    data: DouyinVideosFetchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按抖音号 / 主页链接批量抓取账号作品的播放数据（供前端预览后写入）。"""
    profile_key, account = _account_profile(db, data.account_id)
    try:
        info = fetch_account_videos(data.query, data.limit, profile_key=profile_key)
    except CollectError as exc:
        _mark_login_state(account, False)
        db.commit()
        return DouyinVideosFetchOut(
            ok=False,
            channel=exc.channel,
            message=exc.message,
            need_login=exc.need_login,
            data={"manual_hint": exc.manual_hint},
        )
    except Exception as exc:  # pragma: no cover
        return DouyinVideosFetchOut(
            ok=False,
            message=f"采集异常：{exc}",
            data={"manual_hint": "请手工录入本次数据快照"},
        )
    _mark_login_state(account, True)
    db.commit()
    videos = _mark_imported_flags(db, info.get("videos") or [])
    info = dict(info)
    info["videos"] = videos
    return DouyinVideosFetchOut(
        ok=True,
        channel=info.get("channel", ""),
        message=f"获取到 {len(videos)} 条作品",
        data=info,
    )


def _account_video_query(account) -> str:
    """已登录账号取作品用的主页 / 抖音号，优先用扫码回填的 sec_uid。"""
    sec_uid = (account.sec_uid or "").strip()
    return (
        (f"https://www.douyin.com/user/{sec_uid}" if sec_uid else "")
        or (account.home_url or "").strip()
        or (account.douyin_uid or "").strip()
        or (account.account_id or "").strip()
    )


def _mark_imported_flags(db: Session, videos: list) -> list:
    """给采集结果标记 imported / import_id，供前端自动勾选「已导入」作品。"""
    items = [v for v in (videos or []) if isinstance(v, dict)]
    ids = sorted({str(v.get("video_id") or "").strip() for v in items if v.get("video_id")})
    imported = {}
    if ids:
        rows = db.query(DouyinImport).filter(DouyinImport.video_id.in_(ids)).all()
        imported = {r.video_id: r.id for r in rows}
    for item in items:
        import_id = imported.get(str(item.get("video_id") or "").strip())
        item["import_id"] = import_id
        item["imported"] = bool(import_id)
    return items


@router.post("/videos/from-account", response_model=DouyinVideosFetchOut)
def fetch_videos_by_account(
    data: DouyinAccountVideosIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """用发布账号已保存的扫码登录态直接抓取该账号作品列表与播放数据。

    前端「发布数据 → 获取抖音列表」使用：不需要再手工输入抖音号 / 主页链接。
    """
    account = db.query(PublishAccount).get(data.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="发布账号不存在")
    profile_key = (account.douyin_profile or "").strip() or f"account_{account.id}"
    account.douyin_profile = profile_key
    query = _account_video_query(account)
    if not query:
        _mark_login_state(account, False)
        db.commit()
        return DouyinVideosFetchOut(
            ok=False,
            message="该账号未保存抖音主页 / 抖音号，请先到「我的账号」重新扫码登录",
            data={"manual_hint": "扫码登录会自动写入账号主页与抖音号"},
        )
    try:
        info = fetch_account_videos(query, data.limit, profile_key=profile_key)
    except CollectError as exc:
        _mark_login_state(account, False)
        db.commit()
        return DouyinVideosFetchOut(
            ok=False,
            channel=exc.channel,
            message=exc.message,
            need_login=exc.need_login,
            data={"manual_hint": exc.manual_hint},
        )
    except Exception as exc:  # pragma: no cover
        return DouyinVideosFetchOut(
            ok=False,
            message=f"采集异常：{exc}",
            data={"manual_hint": "请稍后重试或手工录入数据快照"},
        )
    _mark_login_state(account, True)
    account.last_synced_at = datetime.now()
    db.commit()
    videos = _mark_imported_flags(db, info.get("videos") or [])
    info = dict(info)
    info["videos"] = videos
    return DouyinVideosFetchOut(
        ok=True,
        channel=info.get("channel", "browser"),
        message=f"获取到 {len(videos)} 条作品",
        data=info,
    )


@router.post("/videos/fetch-all", response_model=dict)
def fetch_videos_batch(
    data: DouyinVideosBatchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按发布数据页账号标签批量拉取作品列表与播放数据。

    前端选中「全部账号」时传入所有抖音账号 ID；选中单个账号时只传该账号 ID。
    每个账号复用自己的 Playwright profile，失败账号不影响其它账号。
    """
    ids = list(dict.fromkeys(int(x) for x in (data.account_ids or [])))
    if not ids:
        return {"ok": False, "message": "没有可采集的账号", "need_login": False, "accounts": [], "videos": []}
    rows = db.query(PublishAccount).filter(PublishAccount.id.in_(ids)).all()
    by_id = {a.id: a for a in rows}

    results = []
    videos = []
    need_login = False
    for account_id in ids:
        account = by_id.get(account_id)
        if not account:
            results.append({"account_id": account_id, "name": f"#{account_id}", "ok": False,
                            "message": "发布账号不存在", "need_login": False, "videos": []})
            continue
        query = _account_video_query(account)
        if not query:
            _mark_login_state(account, False)
            results.append({"account_id": account_id, "name": account.name, "ok": False,
                            "message": "未保存抖音主页 / 抖音号，请先重新扫码登录",
                            "need_login": True, "videos": []})
            need_login = True
            continue
        profile_key = (account.douyin_profile or "").strip() or f"account_{account.id}"
        account.douyin_profile = profile_key
        try:
            info = fetch_account_videos(query, data.limit, profile_key=profile_key)
        except CollectError as exc:
            _mark_login_state(account, False)
            need_login = need_login or bool(exc.need_login)
            results.append({"account_id": account_id, "name": account.name, "ok": False,
                            "message": exc.message, "need_login": bool(exc.need_login), "videos": []})
            continue
        except Exception as exc:  # pragma: no cover
            results.append({"account_id": account_id, "name": account.name, "ok": False,
                            "message": f"采集异常：{exc}", "need_login": False, "videos": []})
            continue
        _mark_login_state(account, True)
        account.last_synced_at = datetime.now()
        account_videos = []
        for video in (info.get("videos") or []):
            item = dict(video)
            item["account_id"] = account.id
            item["account_name"] = account.name
            account_videos.append(item)
        videos.extend(account_videos)
        # 采集完整时按公开列表对账已录入作品的隐藏状态（平台为准），
        # 让用户「获取抖音数据」后即可看到隐藏同步结果，无需先导入。
        hidden, restored = reconcile_hidden_videos(
            db, account, info.get("videos") or [], bool(info.get("list_complete"))
        )
        note = f"获取到 {len(account_videos)} 条作品"
        if hidden or restored:
            note += f"；隐藏状态已同步：新隐藏 {hidden} 条、恢复 {restored} 条"
        results.append({"account_id": account_id, "name": account.name, "ok": True,
                        "message": note, "need_login": False,
                        "videos": account_videos, "hidden": hidden, "restored": restored})
    db.commit()
    videos = _mark_imported_flags(db, videos)

    succeeded = sum(1 for r in results if r["ok"])
    failed = [r for r in results if not r["ok"]]
    message = f"共获取 {len(videos)} 条作品（成功 {succeeded} 个账号"
    message += f"，失败 {len(failed)} 个" if failed else ""
    message += "）"
    if failed:
        message += "｜" + "；".join(f"{r['name']}：{r['message']}" for r in failed[:3])
    return {
        "ok": succeeded > 0,
        "message": message,
        "need_login": need_login,
        "accounts": results,
        "videos": videos,
    }


@router.post("/account/apply", response_model=dict)
def apply_account_info(
    account_id: int,
    data: DouyinAccountFetchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """抓取账号资料并直接回填到指定发布账号。"""
    account = db.query(PublishAccount).get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="发布账号不存在")
    profile_key, _ = _account_profile(db, account.id)
    try:
        info = fetch_account(data.query, data.channel, profile_key=profile_key)
    except CollectError as exc:
        raise HTTPException(status_code=400, detail=f"{exc.message}｜{exc.manual_hint}")
    account.name = info.get("name") or account.name
    account.avatar = info.get("avatar") or account.avatar
    account.douyin_uid = info.get("douyin_uid") or account.douyin_uid
    account.sec_uid = info.get("sec_uid") or account.sec_uid
    account.home_url = info.get("home_url") or account.home_url
    account.followers_count = int(info.get("followers_count") or 0)
    account.likes_count = int(info.get("likes_count") or 0)
    account.video_count = int(info.get("video_count") or 0)
    account.last_synced_at = datetime.now()
    account.updated_at = datetime.now()
    db.commit()
    db.refresh(account)
    return {
        "ok": True,
        "channel": info.get("channel", ""),
        "account": {
            "id": account.id,
            "name": account.name,
            "avatar": account.avatar,
            "followers_count": account.followers_count,
            "likes_count": account.likes_count,
            "video_count": account.video_count,
        },
    }


@router.post("/stats/fetch", response_model=DouyinStatsFetchOut)
def fetch_stats_info(
    data: DouyinStatsFetchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按作品链接抓取视频数据（播放 / 点赞 / 评论 / 转发）。"""
    profile_key, account = _account_profile(db, data.account_id)
    try:
        info = fetch_video(data.url, data.channel, profile_key=profile_key)
    except CollectError as exc:
        _mark_login_state(account, False)
        db.commit()
        return DouyinStatsFetchOut(
            ok=False,
            channel=exc.channel,
            message=exc.message,
            need_login=exc.need_login,
            data={"manual_hint": exc.manual_hint, "manual_required": True},
        )
    except Exception as exc:  # pragma: no cover
        return DouyinStatsFetchOut(
            ok=False,
            message=f"采集异常：{exc}",
            data={"manual_hint": "请手工录入本次数据快照", "manual_required": True},
        )
    _mark_login_state(account, True)
    db.commit()
    return DouyinStatsFetchOut(ok=True, channel=info.get("channel", ""), message="获取成功", data=info)


@router.post("/stats/apply", response_model=dict)
def apply_stats_info(
    data: DouyinStatsFetchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """抓取视频数据并写入该视频的最新数据快照。"""
    production = db.query(Production).get(data.production_id) if data.production_id else None
    if not production:
        raise HTTPException(status_code=404, detail="视频记录不存在")
    profile_key, account = _account_profile(db, data.account_id or production.publish_account_id)
    try:
        info = fetch_video(
            data.url or production.published_url or production.douyin_url,
            data.channel,
            profile_key=profile_key,
        )
    except CollectError as exc:
        raise HTTPException(status_code=400, detail=f"{exc.message}｜{exc.manual_hint}")
    _mark_login_state(account, True)

    stat = PublishStat(
        production_id=production.id,
        plays=max(0, int(info.get("plays") or 0)),
        likes=max(0, int(info.get("likes") or 0)),
        comments=max(0, int(info.get("comments") or 0)),
        shares=max(0, int(info.get("shares") or 0)),
        account=(production.publish_account.name if production.publish_account else ""),
        source="auto",
        recorded_at=datetime.now(),
    )
    db.add(stat)
    db.flush()
    bind_publish(db, production, info.get("video_id") or "")
    # 顺带回填封面与标题（采集到的更准）
    if info.get("cover") and not production.cover:
        production.cover = info["cover"]
    db.commit()
    db.refresh(stat)
    return {"ok": True, "channel": info.get("channel", ""), "stat": stat.id}


@router.post("/account/from-video", response_model=dict)
def create_account_from_video(
    data: DouyinVideoAccountIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """视频扫码：按作品链接解析作者，自动建号或回填已有账号。"""
    from ..auth import require_create, require_permission

    require_create(user)
    require_permission(user, "publish-accounts.create", db)
    url = (data.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="请先扫描二维码或粘贴视频链接")
    try:
        info = fetch_video(url, data.channel)
    except CollectError as exc:
        return {
            "ok": False,
            "need_login": exc.need_login,
            "message": exc.message,
            "manual_hint": exc.manual_hint,
        }
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "message": f"解析失败：{exc}"}

    author = (info.get("author") or "").strip()
    author_id = (info.get("author_id") or "").strip()
    if not author and not author_id:
        return {
            "ok": False,
            "message": "未能从视频中识别出作者，请改用手动添加",
        }

    # 按抖音号去重：命中则回填，未命中则新建
    conditions = []
    if author_id:
        conditions.append(or_(PublishAccount.douyin_uid == author_id, PublishAccount.account_id == author_id))
    account = db.query(PublishAccount).filter(or_(*conditions)).first() if conditions else None
    created = account is None
    if created:
        account = PublishAccount(
            name=author or author_id or "抖音账号",
            platform="抖音",
            account_id=author_id,
            douyin_uid=author_id,
            status="正常",
            update_rhythm="日更",
            owner_id=user.id,
            note=f"视频扫码添加：{url[:120]}",
        )
        db.add(account)
        db.flush()
    else:
        if author and not account.name:
            account.name = author
        if not account.note:
            account.note = f"视频扫码添加：{url[:120]}"
    account.updated_at = datetime.now()
    db.commit()
    db.refresh(account)
    return {
        "ok": True,
        "created": created,
        "account_id": account.id,
        "account_name": account.name,
        "author": author,
        "video": {
            "title": info.get("title", ""),
            "cover": info.get("cover", ""),
            "plays": info.get("plays", 0),
        },
    }


def _enrich_stats_into(result: dict, home_url: str, profile_key: str) -> bool:
    """用账号登录态补抓作品/获赞/粉丝，写入 result。返回是否拿到有效数据。"""
    query = (result.get("sec_uid") or result.get("douyin_uid") or home_url or "").strip()
    if not query:
        return False
    try:
        extra = fetch_account(query, "browser", profile_key=profile_key)
    except Exception:
        return False
    got = False
    for field in ("video_count", "likes_count", "followers_count"):
        value = int(extra.get(field) or 0)
        if value:
            result[field] = value
            got = True
    return got


def _enrich_login_result(
    session_id: str,
    profile_key: str,
    home_url: str,
    payload: dict,
    update_fn,
) -> None:
    """后台线程：登录确认后补抓统计数据，更新账号并推进会话到 success。

    补抓失败不会影响登录态：账号保持已登录、数据为 0，
    会话带 stats_enrich_failed 标记，前端提示用户点「更新」按钮重试。
    保持 payload 外层结构（created/account_name）不变，供前端成功提示使用。
    """
    data = payload.setdefault("data", {})
    enriched = _enrich_stats_into(data, home_url, profile_key)
    if enriched:
        db = SessionLocal()
        try:
            account_id = payload.get("account_id")
            account = db.query(PublishAccount).get(account_id) if account_id else None
            if account:
                for field in ("video_count", "likes_count", "followers_count"):
                    value = int(data.get(field) or 0)
                    if value:
                        setattr(account, field, value)
                account.douyin_login_status = "已登录"
                account.updated_at = datetime.now()
                db.commit()
        except Exception:
            pass
        finally:
            db.close()
    update_fn(
        status="success",
        message="扫码成功，账号资料已同步" if enriched else "扫码成功，但账号资料同步失败，可点击「更新」按钮重试",
        result=payload,
        stats_enrich_failed=not enriched,
    )


def _apply_login_result(
    db: Session,
    user_id: int,
    account_id: Optional[int],
    profile_key: str,
    result: dict,
    defer_stats: bool = False,
) -> dict:
    """扫码成功后匹配/新建账号并回填资料；同步与异步入口共用。

    defer_stats=True 时跳过耗时的统计补抓（由后台线程稍后完成），
    用于远程扫码「先关窗、后补数据」的两阶段流程。
    """
    user = db.query(User).get(user_id)
    created = False
    if account_id:
        profile_key, account = _account_profile(db, account_id)
    else:
        account = None

    if account is None:
        sec_uid = (result.get("sec_uid") or "").strip()
        douyin_uid = (result.get("douyin_uid") or "").strip()
        conditions = []
        if sec_uid:
            conditions.append(PublishAccount.sec_uid == sec_uid)
        if douyin_uid:
            conditions.append(or_(PublishAccount.douyin_uid == douyin_uid, PublishAccount.account_id == douyin_uid))
        if conditions:
            account = db.query(PublishAccount).filter(or_(*conditions)).first()
        if account is None:
            account = PublishAccount(
                name=(result.get("name") or "抖音账号").strip() or "抖音账号",
                platform="抖音",
                account_id=douyin_uid,
                douyin_uid=douyin_uid,
                sec_uid=sec_uid,
                avatar=result.get("avatar") or "",
                status="正常",
                update_rhythm="日更",
                owner_id=user_id,
            )
            db.add(account)
            db.flush()
            created = True

    # 扫码目录（临时 key）直接作为该账号专属登录态保存，后续采集直接复用，
    # 全程不改名、不删除目录，避免历史残留目录触发批量删除守卫。
    have_stats = any(int(result.get(f) or 0) for f in ("video_count", "likes_count", "followers_count"))
    account.douyin_profile = profile_key
    # 两阶段流程：资料尚未补齐时先标记为同步中，前端显示加载态；登录态本身已有效
    account.douyin_login_status = "资料同步中" if defer_stats and not have_stats else "已登录"
    account.douyin_login_at = datetime.now()
    account.last_synced_at = datetime.now()
    for field in ("name", "douyin_uid", "sec_uid", "avatar"):
        value = result.get(field)
        if value and (created or field != "name" or not account.name):
            setattr(account, field, value)
    if not account.account_id and result.get("douyin_uid"):
        account.account_id = result["douyin_uid"]
    if result.get("sec_uid") and not account.home_url:
        account.home_url = f"https://www.douyin.com/user/{result['sec_uid']}"

    # 作品数 / 获赞 / 粉丝：扫码读不到时用该账号登录态补抓一次账号资料。
    # defer_stats=True 时跳过，交给后台线程 _enrich_login_result 异步补齐。
    if not have_stats and not defer_stats:
        _enrich_stats_into(result, account.home_url, profile_key)
    for field in ("video_count", "likes_count", "followers_count"):
        value = int(result.get(field) or 0)
        if value:
            setattr(account, field, value)
    account.updated_at = datetime.now()
    db.commit()
    db.refresh(account)
    return {
        "ok": True,
        "created": created,
        "account_id": account.id,
        "account_name": account.name,
        "data": result,
        "owner": user.username if user else "",
    }


def _login_worker(
    session_id: str,
    account_id: Optional[int],
    profile_key: str,
    user_id: int,
    holder: dict,
) -> None:
    """后台执行无头扫码：回调二维码、轮询登录态，最后写库。"""

    def update(**changes):
        with _LOGIN_LOCK:
            session = _LOGIN_SESSIONS.get(session_id)
            if not session or session.get("status") == "cancelled":
                return
            session.update(changes)
            session["updated_at"] = time.time()

    def on_qr(event: dict):
        image = (event.get("data") or "").strip()
        # Node 端优先返回 img.src 原始 data URL；兼容旧的纯 base64 输出。
        # 注意不要重复套前缀，否则前端拿到双重前缀会显示不出来。
        qr = image if image.startswith("data:") else (
            f"data:image/png;base64,{image}" if image else "")
        with _LOGIN_LOCK:
            session = _LOGIN_SESSIONS.get(session_id)
            if not session or session.get("status") == "cancelled":
                return
            session["qr_seq"] = int(session.get("qr_seq") or 0) + 1
            session.update(
                status="waiting_scan",
                qr=qr,
                qr_seq=session["qr_seq"],
                kind=event.get("kind") or "qr",
                message="请用手机抖音扫描页面上的二维码",
                updated_at=time.time(),
            )

    try:
        result = login_douyin(
            profile_key,
            qr_callback=on_qr,
            qr_mode=True,
            proc_holder=holder,
        )
    except CollectError as exc:
        update(
            status="failed",
            message=exc.message,
            manual_hint=exc.manual_hint,
            need_login=exc.need_login,
        )
        return
    except Exception as exc:
        update(status="failed", message=f"登录流程失败：{exc}")
        return

    if not result or not result.get("logged_in"):
        update(
            status="failed",
            need_login=True,
            message="未获取到抖音登录态，已取消建号",
            manual_hint="请重新扫码，或改用手动添加",
        )
        return

    # 两阶段：先建号、确认登录态，立即推进到 logged_in 让前端关窗；
    # 耗时的作品/获赞/粉丝补抓交给后台线程，完成后再推进到 success。
    db = SessionLocal()
    try:
        payload = _apply_login_result(db, user_id, account_id, profile_key, result, defer_stats=True)
    except Exception as exc:
        update(status="failed", message=f"保存登录态失败：{exc}")
        return
    finally:
        db.close()

    have_stats = any(int((payload.get("data") or {}).get(f) or 0) for f in ("video_count", "likes_count", "followers_count"))
    if have_stats:
        # Node 端 readSelfUser 已带齐统计数据，无需补抓，直接完成
        update(
            status="success",
            message="扫码成功，账号资料已同步",
            result=payload,
            stats_enrich_failed=False,
        )
        return

    update(
        status="logged_in",
        message="登录成功，正在同步账号资料…",
        result=payload,
        stats_enrich_failed=False,
    )
    enrich_payload = dict(payload)
    enrich_payload["data"] = dict(payload.get("data") or {})
    home_url = (result.get("home_url") or "").strip() or (
        f"https://www.douyin.com/user/{result['sec_uid']}" if result.get("sec_uid") else ""
    )
    threading.Thread(
        target=_enrich_login_result,
        args=(session_id, profile_key, home_url, enrich_payload, update),
        daemon=True,
    ).start()


@router.post("/login/start", response_model=dict)
def douyin_login_start(
    data: DouyinLoginIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """启动远程扫码会话：后端无头打开抖音并把二维码推送到网页。"""
    if data.account_id:
        profile_key, _ = _account_profile(db, data.account_id)
    else:
        profile_key = new_temp_profile_key()

    session_id = uuid.uuid4().hex
    now = time.time()
    holder = {}
    with _LOGIN_LOCK:
        for key in list(_LOGIN_SESSIONS):
            if now - _LOGIN_SESSIONS[key].get("created_at", 0) > _LOGIN_TTL:
                _LOGIN_SESSIONS.pop(key, None)
        _LOGIN_SESSIONS[session_id] = {
            "status": "starting",
            "created_at": now,
            "updated_at": now,
            "account_id": data.account_id,
            "profile_key": profile_key,
            "holder": holder,
            "qr": "",
            "qr_seq": 0,
            "kind": "qr",
            "message": "正在打开抖音登录页（首次加载约需半分钟），请稍候…",
            "result": None,
        }
    threading.Thread(
        target=_login_worker,
        args=(session_id, data.account_id, profile_key, user.id, holder),
        daemon=True,
    ).start()
    return {"ok": True, "session": session_id}


@router.get("/login/status", response_model=dict)
def douyin_login_status(
    session: str,
    qr_seq: int = -1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """轮询远程扫码状态；qr 字段是 data URL，同一张图只传一次。"""
    with _LOGIN_LOCK:
        state = dict(_LOGIN_SESSIONS.get(session) or {})
    if not state:
        raise HTTPException(status_code=404, detail="扫码会话不存在或已过期")
    current_seq = int(state.get("qr_seq") or 0)
    return {
        "ok": state.get("status") == "success",
        "status": state.get("status"),
        "qr": state.get("qr") or "" if current_seq != qr_seq else "",
        "qr_seq": current_seq,
        "kind": state.get("kind") or "qr",
        "message": state.get("message") or "",
        "manual_hint": state.get("manual_hint") or "",
        "need_login": bool(state.get("need_login")),
        "stats_enrich_failed": bool(state.get("stats_enrich_failed")),
        "result": state.get("result"),
    }


@router.post("/login/cancel", response_model=dict)
def douyin_login_cancel(
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """关闭弹窗时终止后台扫码进程，避免遗留无头浏览器。"""
    session_id = str(data.get("session") or "")
    with _LOGIN_LOCK:
        state = _LOGIN_SESSIONS.get(session_id)
        if not state:
            return {"ok": False, "message": "会话不存在或已结束"}
        state["status"] = "cancelled"
        holder = state.get("holder") or {}
    proc = holder.get("proc")
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate()
        except Exception:
            pass
    return {"ok": True}


@router.post("/login", response_model=dict)
def douyin_login(
    data: DouyinLoginIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """兼容原同步接口：在服务主机直接弹浏览器窗口扫码。"""
    if data.account_id:
        profile_key, account = _account_profile(db, data.account_id)
    else:
        profile_key = new_temp_profile_key()
        account = None
    try:
        result = login_douyin(profile_key)
    except CollectError as exc:
        _mark_login_state(account, False)
        db.commit()
        return {
            "ok": False,
            "need_login": exc.need_login,
            "message": exc.message,
            "manual_hint": exc.manual_hint,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"登录流程失败：{exc}")

    # 防御：登录态未确认时绝不建号、绝不标记为已登录
    if not result or not result.get("logged_in"):
        _mark_login_state(account, False)
        db.commit()
        return {
            "ok": False,
            "need_login": True,
            "message": "未获取到抖音登录态，已取消建号",
            "manual_hint": "请确认部署环境已安装 Node.js / Playwright / Chromium，且后端可打开图形窗口，然后重新扫码",
        }
    return _apply_login_result(db, user.id, data.account_id, profile_key, result)


@router.post("/config", response_model=dict)
def save_douyin_config(
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """保存官方开放平台凭据（需 settings.manage 权限）。"""
    require_permission(user, "settings.manage", db)
    from ..models import SystemSetting

    allowed = ("app_id", "app_secret", "access_token", "open_id")
    clean = {k: str(data.get(k) or "").strip() for k in allowed}
    row = db.query(SystemSetting).filter(SystemSetting.key == "douyin_official").first()
    if not row:
        row = SystemSetting(key="douyin_official", value=clean)
        db.add(row)
    else:
        merged = dict(row.value) if isinstance(row.value, dict) else {}
        merged.update(clean)
        row.value = merged
    db.commit()
    return {"ok": True, "config": clean}
