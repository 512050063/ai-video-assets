from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import ensure_owner, get_current_user, require_create
from ..database import get_db
from ..models import Category, Idea, Production, User
from ..schemas import CategoryIn, CategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Category).order_by(Category.sort, Category.id).all()


@router.post("", response_model=CategoryOut)
def create_category(
    data: CategoryIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_create(user)
    if db.query(Category).filter(Category.name == data.name).first():
        raise HTTPException(status_code=400, detail="分类已存在")
    c = Category(
        name=data.name,
        color=(data.color or "#7b62c9"),
        image=data.image or "",
        display=data.display if data.display in ("full", "label", "icon") else "full",
        sort=data.sort,
        owner_id=user.id,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    data: CategoryIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = db.query(Category).get(category_id)
    if not c:
        raise HTTPException(status_code=404, detail="分类不存在")
    ensure_owner(c, user, "编辑")
    c.name = data.name
    provided = data.model_fields_set
    if "color" in provided:
        c.color = data.color or "#7b62c9"
    if "image" in provided:
        c.image = data.image or ""
    if "display" in provided:
        c.display = data.display if data.display in ("full", "label", "icon") else "full"
    c.sort = data.sort
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = db.query(Category).get(category_id)
    if not c:
        raise HTTPException(status_code=404, detail="分类不存在")
    ensure_owner(c, user, "删除")
    used = db.query(Production).filter(Production.category_id == category_id).count()
    used += db.query(Idea).filter(Idea.category_id == category_id).count()
    if used:
        raise HTTPException(status_code=400, detail=f"该分类下有 {used} 条记录，无法删除")
    db.delete(c)
    db.commit()
    return {"ok": True}
