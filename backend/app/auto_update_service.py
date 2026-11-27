"""账号自动更新服务：每日定时更新在线账号资料、写账号快照，并同步发布数据。

设计要点：
1. 离线账号跳过采集，页头「更新提醒」会展示离线消息，提示重新扫码；
2. 在线账号复用自己的 Playwright profile 采集，成功后写 PublishAccountSnapshot；
3. 发布数据只按 video_id 更新 DouyinImport / PublishStat，不写账号快照；
4. 调度器为轻量后台线程，不引入额外依赖，同一天同一配置只执行一次。
"""
import logging
import os
import threading
import time
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .database import SessionLocal
from .douyin_collector import CollectError, fetch_account, fetch_account_videos
from .models import DouyinImport, Production, PublishAccount, PublishAccountSnapshot, PublishStat, SystemSetting
from .routers.settings import normalize_auto_update

logger = logging.getLogger(__name__)

_RUN_LOCK = threading.Lock()
_SCHEDULER_LOCK = threading.Lock()
_SCHEDULER_STARTED = False
_LAST_RUN_KEY = "_auto_update_last_run"


def _int(value, default: int = 0) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return default


def _float(value):
    """采集作品的时长（秒）：非法或为 0 时留空，不伪造数据。"""
    try:
        v = float(value or 0)
        return round(v, 1) if v > 0 else None
    except (TypeError, ValueError):
        return None


def _is_douyin_account(account: PublishAccount) -> bool:
    platform = (account.platform or "").strip()
    return (
        "抖音" in platform
        or bool(account.douyin_uid)
        or bool(account.sec_uid)
        or "douyin.com" in (account.home_url or "")
    )


def _account_query(account: PublishAccount) -> str:
    """已登录账号优先用 sec_uid 主页，避免抖音号变更导致抓不到。"""
    sec_uid = (account.sec_uid or "").strip()
    return (
        (f"https://www.douyin.com/user/{sec_uid}" if sec_uid else "")
        or (account.home_url or "").strip()
        or (account.douyin_uid or "").strip()
        or (account.account_id or "").strip()
    )


def _mark_offline(account: PublishAccount, message: str) -> dict:
    """离线账号只标记状态，不覆盖已有作品数 / 获赞 / 粉丝数据。"""
    if account.douyin_login_status == "已登录":
        account.douyin_login_status = "需验证"
    return {
        "account_id": account.id,
        "account_name": account.name,
        "status": "offline",
        "message": message,
    }


def _apply_account_info(account: PublishAccount, info: dict) -> None:
    """采集结果回填；关键指标为 0 时保留原值，避免接口偶发空数据把账号清空。"""
    for field in ("name", "avatar", "douyin_uid", "sec_uid", "home_url"):
        value = (info or {}).get(field)
        if value:
            setattr(account, field, value)
    for field in ("followers_count", "likes_count", "video_count"):
        value = _int((info or {}).get(field))
        if value:
            setattr(account, field, value)
    now = datetime.now()
    account.douyin_login_status = "已登录"
    account.last_synced_at = now
    account.updated_at = now


def create_account_snapshot(
    account: PublishAccount,
    source: str = "manual",
    note: str = "",
    fetched_video_count: int = 0,
    previous: dict = None,
) -> PublishAccountSnapshot:
    """写一条账号资料快照；自动任务与手动「更新」共用同一份历史记录。

    ``previous`` 为更新前的作品数 / 获赞 / 粉丝，写入快照后即可自包含地算出本次增量，
    不必依赖「倒数第二条快照」，首次更新同样能显示变化量。
    """
    prev = previous or {}
    return PublishAccountSnapshot(
        account_id=account.id,
        account_name=account.name,
        avatar=account.avatar or "",
        douyin_uid=account.douyin_uid or "",
        sec_uid=account.sec_uid or "",
        video_count=account.video_count or 0,
        likes_count=account.likes_count or 0,
        followers_count=account.followers_count or 0,
        prev_video_count=prev.get("video_count", account.video_count or 0),
        prev_likes_count=prev.get("likes_count", account.likes_count or 0),
        prev_followers_count=prev.get("followers_count", account.followers_count or 0),
        fetched_video_count=fetched_video_count,
        source=source,
        note=note[:300],
        snapshot_at=datetime.now(),
    )


def get_auto_update_config(db: Session) -> dict:
    """读取配置中心的自动更新配置（归一化）；手动更新也复用其中的采集条数。"""
    from .routers.settings import _all_settings

    return normalize_auto_update(_all_settings(db).get("auto_update"))


def sync_account_publish_videos(
    db: Session,
    account: PublishAccount,
    video_limit: int,
    fetch_fn=None,
) -> tuple:
    """采集指定账号最新作品并写入发布数据表；返回 (created, updated, fetched, hidden, restored)。

    手动「更新」与自动任务共用：均按配置中心的 video_limit 重新获取最新作品，
    已导入的按 video_id 更新、未导入的新增，已匹配创作的同步播放数据。
    采集完整（抓到列表末尾）时按差集对账隐藏状态：本次未出现的历史作品标「隐藏」，
    重新出现的恢复「正常」（平台为准）。采集失败时抛出 CollectError，由调用方决定是否降级。
    """
    fetch_list = fetch_fn or fetch_account_videos
    query = _account_query(account)
    if not query:
        return 0, 0, 0, 0, 0
    profile_key = (account.douyin_profile or "").strip() or f"account_{account.id}"
    info = fetch_list(query, video_limit, profile_key=profile_key) or {}
    videos = info.get("videos") or []
    created, updated = _sync_publish_videos(db, videos, account, video_limit)
    hidden, restored = reconcile_hidden_videos(
        db, account, videos, bool(info.get("list_complete"))
    )
    return created, updated, len(videos), hidden, restored


def _sync_publish_videos(
    db: Session,
    videos: list,
    account: PublishAccount,
    limit: int,
) -> tuple:
    """把采集作品按 video_id 写入发布数据表；已匹配作品同步最新数据快照。

    返回 (created, updated)。这里只更新 DouyinImport / PublishStat，
    不生成账号历史快照，避免发布数据与我的账号快照重复。
    """
    seen = set()
    prepared = []
    for raw in (videos or [])[: max(0, limit)]:
        if not isinstance(raw, dict):
            continue
        video_id = str(raw.get("video_id") or "").strip()
        if not video_id or video_id in seen:
            continue
        seen.add(video_id)
        prepared.append({
            "video_id": video_id,
            "title": str(raw.get("title") or "").strip() or "未命名作品",
            "cover": str(raw.get("cover") or "").strip(),
            "tags": list(raw.get("tags") or []),
            "plays": _int(raw.get("plays")),
            "likes": _int(raw.get("likes")),
            "comments": _int(raw.get("comments")),
            "collects": _int(raw.get("collects")),
            "shares": _int(raw.get("shares")),
            "create_time": raw.get("create_time"),
            "duration": _float(raw.get("duration")),
        })

    if not prepared:
        return 0, 0

    video_ids = [item["video_id"] for item in prepared]
    existing_rows = (
        db.query(DouyinImport).filter(DouyinImport.video_id.in_(video_ids)).all()
        if video_ids else []
    )
    by_video_id = {row.video_id: row for row in existing_rows}
    existing_stats = (
        db.query(PublishStat).filter(PublishStat.video_id.in_(video_ids)).all()
        if video_ids else {}
    )
    stats_by_video_id = {stat.video_id: stat for stat in existing_stats}

    created = 0
    updated = 0
    for item in prepared:
        row = by_video_id.get(item["video_id"])
        if row:
            row.title = item["title"]
            if item["cover"]:
                row.cover = item["cover"]
            row.tags = item["tags"]
            row.plays = item["plays"]
            row.likes = item["likes"]
            row.comments = item["comments"]
            row.collects = item["collects"]
            row.shares = item["shares"]
            row.duration = item["duration"]
            if item["create_time"] is not None:
                try:
                    row.create_time = int(item["create_time"])
                except (TypeError, ValueError):
                    pass
            row.account_id = account.id
            row.account_name = account.name
            updated += 1
        else:
            create_time = None
            if item["create_time"] is not None:
                try:
                    create_time = int(item["create_time"])
                except (TypeError, ValueError):
                    create_time = None
            row = DouyinImport(
                video_id=item["video_id"],
                title=item["title"],
                cover=item["cover"],
                tags=item["tags"],
                plays=item["plays"],
                likes=item["likes"],
                comments=item["comments"],
                collects=item["collects"],
                shares=item["shares"],
                create_time=create_time,
                duration=item["duration"],
                account_id=account.id,
                account_name=account.name,
                status="待匹配",
                data_status="正常",
            )
            db.add(row)
            by_video_id[item["video_id"]] = row
            created += 1

        # 已手动匹配到创作记录的作品：同步最新播放数据，不新增快照行
        stat = stats_by_video_id.get(item["video_id"])
        if stat:
            stat.plays = item["plays"]
            stat.likes = item["likes"]
            stat.comments = item["comments"]
            stat.collects = item["collects"]
            stat.shares = item["shares"]
            stat.account = account.name
            stat.recorded_at = datetime.now()

    return created, updated


def reconcile_hidden_videos(
    db: Session,
    account: PublishAccount,
    videos: list,
    list_complete: bool,
) -> tuple:
    """按「本次公开列表」对账该账号已录入作品的隐藏状态（平台为准）。

    抖音隐藏 / 删除的作品不会出现在公开列表里，无法直接读取其状态，只能靠差集推断：
      - 本次出现的作品 → 恢复「正常」（覆盖历史手动标记，平台为准）；
      - 本次未出现、但库里是「正常」的历史作品 → 标记「隐藏」。

    仅当 list_complete 为真（采集脚本确认抓到列表末尾、未被 limit 截断）且本次
    确实抓到作品时才执行，避免网络抖动 / 分页截断把正常作品批量误标为隐藏。
    作用范围严格限定在该账号名下，不影响其他账号或手工录入（无 account_id）的记录。

    返回 (hidden, restored) 两个计数。
    """
    if not list_complete:
        return 0, 0
    current_ids = set()
    for raw in (videos or []):
        if not isinstance(raw, dict):
            continue
        vid = str(raw.get("video_id") or "").strip()
        if vid:
            current_ids.add(vid)
    if not current_ids:
        return 0, 0

    rows = db.query(DouyinImport).filter(DouyinImport.account_id == account.id).all()
    hidden = 0
    restored = 0
    for row in rows:
        old = row.data_status or "正常"
        in_list = row.video_id in current_ids
        new = "正常" if in_list else "隐藏"
        if new == old:
            continue
        row.data_status = new
        if row.production_id:
            prod = db.query(Production).get(row.production_id)
            if prod:
                prod.data_status = new
                prod.updated_at = datetime.now()
        if in_list:
            restored += 1
        else:
            hidden += 1
    return hidden, restored


def run_auto_update(
    db: Session,
    account_ids: Optional[list] = None,
    force: bool = False,
    fetch_account_fn=None,
    fetch_videos_fn=None,
) -> dict:
    """执行一次自动更新；fetch_* 参数便于测试注入，不传则走真实采集通道。"""
    if not _RUN_LOCK.acquire(blocking=False):
        return {"ok": False, "message": "上一次自动更新尚未结束", "details": []}

    fetch_info = fetch_account_fn or fetch_account
    fetch_list = fetch_videos_fn or fetch_account_videos
    now = datetime.now()
    try:
        cfg = get_auto_update_config(db)
        if not force and not cfg["enabled"]:
            return {"ok": False, "message": "自动更新已关闭", "ran_at": now, "details": []}

        query = db.query(PublishAccount).filter(PublishAccount.status == "正常")
        if account_ids:
            ids = [int(x) for x in account_ids if str(x).isdigit()]
            if not ids:
                return {"ok": False, "message": "没有可更新的账号", "ran_at": now, "details": []}
            query = query.filter(PublishAccount.id.in_(ids))
        accounts = query.order_by(PublishAccount.id.asc()).all()

        total = 0
        updated = 0
        offline = 0
        failed = 0
        videos_created = 0
        videos_updated = 0
        details = []

        for account in accounts:
            if not _is_douyin_account(account):
                continue
            total += 1

            # 离线账号：推送页头消息由 /publish-accounts/reminders 实时生成，这里只跳过
            if account.douyin_login_status != "已登录":
                offline += 1
                details.append(_mark_offline(account, "账号离线，自动更新已跳过，请重新扫码"))
                continue
            collect_query = _account_query(account)
            if not collect_query:
                offline += 1
                details.append(_mark_offline(account, "未保存抖音号 / 主页，请重新扫码登录"))
                continue

            profile_key = (account.douyin_profile or "").strip() or f"account_{account.id}"
            account.douyin_profile = profile_key
            before = {
                "video_count": account.video_count or 0,
                "likes_count": account.likes_count or 0,
                "followers_count": account.followers_count or 0,
            }
            try:
                info = fetch_info(collect_query, "auto", profile_key=profile_key) or {}
            except CollectError as exc:
                failed += 1
                account.douyin_login_status = "需验证"
                details.append({
                    "account_id": account.id,
                    "account_name": account.name,
                    "status": "failed",
                    "message": exc.message,
                })
                continue
            except Exception as exc:  # pragma: no cover
                failed += 1
                details.append({
                    "account_id": account.id,
                    "account_name": account.name,
                    "status": "failed",
                    "message": f"采集异常：{exc}",
                })
                continue

            _apply_account_info(account, info)

            fetched_count = 0
            video_note = ""
            if cfg["sync_publish_data"]:
                try:
                    video_info = fetch_list(collect_query, cfg["video_limit"], profile_key=profile_key) or {}
                    videos = video_info.get("videos") or []
                    created, changed = _sync_publish_videos(
                        db, videos, account, cfg["video_limit"]
                    )
                    videos_created += created
                    videos_updated += changed
                    fetched_count = len(videos)
                    hidden, restored = reconcile_hidden_videos(
                        db, account, videos, bool(video_info.get("list_complete"))
                    )
                    if hidden or restored:
                        video_note = f"隐藏状态对账：新隐藏 {hidden} 条、恢复 {restored} 条"
                except CollectError as exc:
                    video_note = f"发布数据同步失败：{exc.message}"
                    if getattr(exc, "need_login", False):
                        account.douyin_login_status = "需验证"
                        failed += 1
                except Exception as exc:  # pragma: no cover
                    video_note = f"发布数据同步异常：{exc}"

            db.add(create_account_snapshot(
                account,
                source="auto",
                note=video_note,
                fetched_video_count=fetched_count,
                previous=before,
            ))
            updated += 1
            details.append({
                "account_id": account.id,
                "account_name": account.name,
                "status": "updated",
                "message": video_note or f"已更新，采集到 {fetched_count} 条作品",
                "video_count": account.video_count or 0,
                "likes_count": account.likes_count or 0,
                "followers_count": account.followers_count or 0,
            })

        db.commit()
        message = (
            f"自动更新完成：在线更新 {updated} 个账号，离线跳过 {offline} 个，"
            f"失败 {failed} 个；发布数据新增 {videos_created} 条、更新 {videos_updated} 条"
        )
        return {
            "ok": updated > 0 or (total == 0),
            "message": message,
            "total": total,
            "updated": updated,
            "offline": offline,
            "failed": failed,
            "videos_created": videos_created,
            "videos_updated": videos_updated,
            "ran_at": now,
            "details": details,
        }
    except Exception as exc:  # pragma: no cover
        db.rollback()
        logger.exception("自动更新执行失败")
        return {"ok": False, "message": f"自动更新失败：{exc}", "ran_at": now, "details": []}
    finally:
        _RUN_LOCK.release()


def _read_last_run(db: Session) -> dict:
    row = db.query(SystemSetting).filter(SystemSetting.key == _LAST_RUN_KEY).first()
    if not row or not isinstance(row.value, dict):
        return {}
    return dict(row.value)


def _write_last_run(db: Session, signature: str, result: dict) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == _LAST_RUN_KEY).first()
    value = {
        "signature": signature,
        "at": datetime.now().isoformat(timespec="seconds"),
        "updated": int(result.get("updated") or 0),
        "offline": int(result.get("offline") or 0),
        "message": str(result.get("message") or "")[:300],
    }
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=_LAST_RUN_KEY, value=value))
    db.commit()


def _scheduler_loop() -> None:
    # 启动后先等一会儿，避免与建表 / 迁移 / 首页首屏请求争抢数据库连接
    time.sleep(20)
    while True:
        db = None
        try:
            db = SessionLocal()
            from .routers.settings import _all_settings

            cfg = normalize_auto_update(_all_settings(db).get("auto_update"))
            now = datetime.now()
            signature = f"{now.date().isoformat()}|{cfg['hour']:02d}:{cfg['minute']:02d}"
            if (
                cfg["enabled"]
                and now.hour == cfg["hour"]
                and now.minute == cfg["minute"]
                and _read_last_run(db).get("signature") != signature
            ):
                logger.info("开始执行每日自动更新任务：%s", signature)
                result = run_auto_update(db)
                _write_last_run(db, signature, result)
                logger.info("每日自动更新结束：%s", result.get("message"))
        except Exception:  # pragma: no cover
            logger.exception("自动更新调度检查失败")
        finally:
            if db is not None:
                db.close()
        time.sleep(20)


def start_auto_update_scheduler() -> None:
    """FastAPI 启动时调用；进程内只启动一次调度线程。"""
    global _SCHEDULER_STARTED
    if os.getenv("DISABLE_AUTO_UPDATE_SCHEDULER") == "1":
        return
    with _SCHEDULER_LOCK:
        if _SCHEDULER_STARTED:
            return
        _SCHEDULER_STARTED = True
    thread = threading.Thread(target=_scheduler_loop, name="auto-update-scheduler", daemon=True)
    thread.start()
