"""标签库：全局标签字典，供各页面下拉调用。

- 读：所有登录用户可读
- 写：超管可增删改；其它角色的业务数据保存时会自动登记标签
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user, is_admin
from ..database import get_db
from ..models import Tag, User
from ..schemas import TagIn, TagOptionOut, TagOut
from ..tag_service import normalize_tag, rebuild_usage_count

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagOut])
def list_tags(
    keyword: str = "",
    category: str = "",
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Tag)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(Tag.name.like(like))
    if category:
        q = q.filter(Tag.category == category)
    rows = q.order_by(Tag.usage_count.desc(), Tag.name).limit(limit).all()
    return [TagOut.model_validate(r) for r in rows]


@router.get("/options", response_model=list[TagOptionOut])
def tag_options(
    keyword: str = "",
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """给前端标签选择器的轻量下拉数据（不含 id，按使用次数排序）。"""
    q = db.query(Tag)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(Tag.name.like(like))
    rows = q.order_by(Tag.usage_count.desc(), Tag.name).limit(limit).all()
    return [
        TagOptionOut(name=r.name, category=r.category or "通用", usage_count=r.usage_count or 0)
        for r in rows
    ]


@router.get("/categories")
def tag_categories(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """已使用的标签分类，供配置中心标签库分组展示。"""
    rows = db.query(Tag.category).distinct().all()
    names = sorted({(r[0] or "通用") for r in rows})
    return {"items": names}


@router.post("", response_model=TagOut)
def create_tag(
    data: TagIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    name = normalize_tag(data.name)
    if not name:
        raise HTTPException(status_code=400, detail="标签名不能为空")
    exists = db.query(Tag).filter(Tag.name == name).first()
    if exists:
        raise HTTPException(status_code=400, detail=f"标签「{name}」已存在")
    tag = Tag(
        name=name,
        category=(data.category or "通用").strip() or "通用",
        usage_count=0,
        source="manual",
        owner_id=user.id,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagOut.model_validate(tag)


@router.put("/{tag_id}", response_model=TagOut)
def update_tag(
    tag_id: int,
    data: TagIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="仅超级管理员可修改标签库")
    tag = db.query(Tag).get(tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    name = normalize_tag(data.name)
    if not name:
        raise HTTPException(status_code=400, detail="标签名不能为空")
    dup = db.query(Tag).filter(Tag.name == name, Tag.id != tag_id).first()
    if dup:
        raise HTTPException(status_code=400, detail=f"标签「{name}」已存在")
    tag.name = name
    tag.category = (data.category or tag.category or "通用").strip() or "通用"
    db.commit()
    db.refresh(tag)
    return TagOut.model_validate(tag)


@router.delete("/{tag_id}")
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="仅超级管理员可删除标签")
    tag = db.query(Tag).get(tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    db.delete(tag)
    db.commit()
    rebuild_usage_count(db)
    db.commit()
    return {"ok": True}


@router.post("/sync")
def sync_tags(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """按各业务表实际引用重算标签计数，并登记尚未收录的标签。"""
    from ..models import Character, Idea, Production

    counter: dict = {}
    for model in (Idea, Production, Character):
        for row in db.query(model).all():
            for raw in row.tags or []:
                name = normalize_tag(raw)
                if name:
                    counter[name] = counter.get(name, 0) + 1

    now = db.query(Tag).all()
    known = {r.name for r in now}
    for name, count in counter.items():
        if name in known:
            continue
        db.add(Tag(name=name, category="通用", usage_count=count, source="auto"))
    db.commit()
    rebuild_usage_count(db)
    db.commit()
    return {"ok": True, "total": len(counter)}
