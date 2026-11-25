"""平台操作日志：查询与清理。

写操作由 main.py 的审计中间件自动落库，这里只提供查看/清空接口。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import get_current_user, is_admin
from ..database import get_db
from ..models import OperationLog, User

router = APIRouter(prefix="/operation-logs", tags=["operation-logs"])


def _serialize(row: OperationLog) -> dict:
    return {
        "id": row.id,
        "module": row.module or "其他",
        "action": row.action or "操作",
        "target": row.target or "",
        "summary": row.summary or f"{row.action or '执行'}了「{row.target or '数据'}」",
        "username": row.username or "系统",
        "status_code": row.status_code or 200,
        "created_at": row.created_at.isoformat(timespec="seconds") if row.created_at else "",
    }


@router.get("")
def list_logs(
    module: str = "",
    keyword: str = "",
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """超管看全部；其他成员只见自己的操作记录。返回分页结构。"""
    q = db.query(OperationLog)
    if not is_admin(user):
        q = q.filter(or_(OperationLog.user_id == user.id, OperationLog.username == user.display_name))
    if module:
        q = q.filter(OperationLog.module == module)
    kw = (keyword or "").strip()
    if kw:
        like = f"%{kw}%"
        q = q.filter(
            or_(
                OperationLog.username.like(like),
                OperationLog.module.like(like),
                OperationLog.summary.like(like),
            )
        )
    total = q.count()
    current = max(1, int(page or 1))
    size = max(1, min(int(page_size or 10), 100))
    rows = (
        q.order_by(OperationLog.created_at.desc(), OperationLog.id.desc())
        .offset((current - 1) * size)
        .limit(size)
        .all()
    )
    return {"items": [_serialize(r) for r in rows], "total": total, "page": current, "page_size": size}


@router.get("/modules")
def list_modules(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """已产生日志的模块清单，用于前端筛选下拉。"""
    q = db.query(OperationLog.module).distinct()
    if not is_admin(user):
        q = q.filter(or_(OperationLog.user_id == user.id, OperationLog.username == user.display_name))
    return sorted({(r[0] or "其他") for r in q.all()})


@router.delete("")
def clear_logs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """清空操作日志（仅超管）。"""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="仅超级管理员可清空操作日志")
    count = db.query(OperationLog).delete()
    db.commit()
    return {"ok": True, "deleted": count}
