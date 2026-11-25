"""自动更新：手动触发、历史快照查询与运行状态。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user, is_admin
from ..auto_update_service import _LAST_RUN_KEY, run_auto_update
from ..database import get_db
from ..models import PublishAccount, PublishAccountSnapshot, SystemSetting, User
from ..schemas import AccountSnapshotOut, AutoUpdateRunIn, AutoUpdateRunOut

router = APIRouter(prefix="/auto-update", tags=["auto-update"])


@router.post("/run", response_model=AutoUpdateRunOut)
def run_now(
    data: AutoUpdateRunIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """手动执行一次自动更新（仅超管）；离线账号仍会被跳过。"""
    if not is_admin(user):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="仅超级管理员可执行自动更新")
    result = run_auto_update(db, account_ids=data.account_ids, force=data.force)
    return AutoUpdateRunOut.model_validate(result)


@router.get("/snapshots", response_model=list[AccountSnapshotOut])
def list_snapshots(
    account_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=300),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """账号历史快照：默认全部，可按账号筛选，按时间倒序。"""
    q = db.query(PublishAccountSnapshot)
    if account_id is not None:
        q = q.filter(PublishAccountSnapshot.account_id == account_id)
    rows = (
        q.order_by(PublishAccountSnapshot.snapshot_at.desc(), PublishAccountSnapshot.id.desc())
        .limit(limit)
        .all()
    )
    return [AccountSnapshotOut.model_validate(row) for row in rows]


@router.get("/status", response_model=dict)
def auto_update_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """读取最近一次自动更新结果，供配置中心与页头提示使用。"""
    from .settings import _all_settings

    row = db.query(SystemSetting).filter(SystemSetting.key == _LAST_RUN_KEY).first()
    accounts = db.query(PublishAccount).filter(PublishAccount.status == "正常").count()
    return {
        "config": _all_settings(db).get("auto_update", {}),
        "last_run": dict(row.value) if row and isinstance(row.value, dict) else None,
        "active_accounts": accounts,
    }
