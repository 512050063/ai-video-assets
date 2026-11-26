"""素材共享：自定义素材库 + 共享素材。

- 素材库（标签）可点击加号新建，如「人物库」「服装库」「场景库」。
- 素材归属某个素材库，含图片与标签，可被多人共享引用。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import ensure_owner, get_current_user, require_create, require_permission, scope_filter
from ..database import get_db
from ..models import Character, Material, MaterialLibrary, User
from ..schemas import MaterialIn, MaterialLibraryIn, MaterialOut, MaterialPatchIn

router = APIRouter(prefix="/material-libraries", tags=["material-libraries"])


def _owner_name(owner) -> str:
    if not owner:
        return "未归属"
    return owner.nickname or owner.username


def _library_out(db: Session, lib: MaterialLibrary, user: User):
    count = db.query(Material).filter(Material.library_id == lib.id).count()
    return {
        "id": lib.id,
        "name": lib.name or "",
        "color": lib.color or "#4a7cc4",
        "sort": lib.sort or 0,
        "owner_id": lib.owner_id,
        "owner_name": _owner_name(lib.owner),
        "is_owner": lib.owner_id == user.id,
        "material_count": count,
        "usage_count": 0,
    }


@router.get("", response_model=list)
def list_libraries(
    scope: str = "all",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(MaterialLibrary)
    q = scope_filter(q, MaterialLibrary, user, scope)
    rows = q.order_by(MaterialLibrary.sort, MaterialLibrary.id).all()
    return [_library_out(db, lib, user) for lib in rows]


@router.post("", response_model=dict)
def create_library(
    data: MaterialLibraryIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_create(user)
    require_permission(user, "materials.create", db)
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="素材库名称不能为空")
    if db.query(MaterialLibrary).filter(MaterialLibrary.name == name).first():
        raise HTTPException(status_code=400, detail="素材库已存在")
    lib = MaterialLibrary(
        name=name,
        color=data.color or "#4a7cc4",
        sort=data.sort if data.sort else db.query(MaterialLibrary).count(),
        owner_id=user.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(lib)
    db.commit()
    db.refresh(lib)
    return _library_out(db, lib, user)


@router.put("/{library_id}", response_model=dict)
def update_library(
    library_id: int,
    data: MaterialLibraryIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lib = db.query(MaterialLibrary).get(library_id)
    if not lib:
        raise HTTPException(status_code=404, detail="素材库不存在")
    ensure_owner(lib, user, "编辑")
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="素材库名称不能为空")
    dup = db.query(MaterialLibrary).filter(MaterialLibrary.name == name, MaterialLibrary.id != library_id).first()
    if dup:
        raise HTTPException(status_code=400, detail="素材库已存在")
    if "name" in data.model_fields_set:
        lib.name = name
    if "color" in data.model_fields_set:
        lib.color = data.color or "#4a7cc4"
    lib.updated_at = datetime.now()
    db.commit()
    db.refresh(lib)
    return _library_out(db, lib, user)


@router.delete("/{library_id}")
def delete_library(
    library_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lib = db.query(MaterialLibrary).get(library_id)
    if not lib:
        raise HTTPException(status_code=404, detail="素材库不存在")
    ensure_owner(lib, user, "删除")
    used = db.query(Material).filter(Material.library_id == library_id).count()
    if used:
        raise HTTPException(status_code=400, detail=f"该素材库下有 {used} 个素材，请先移动或删除")
    db.delete(lib)
    db.commit()
    return {"ok": True}


# ---------------- 共享素材 ----------------
def _material_out(db: Session, m: Material, user: User) -> MaterialOut:
    lib = db.query(MaterialLibrary).get(m.library_id)
    return MaterialOut(
        id=m.id,
        library_id=m.library_id,
        library_name=(lib.name if lib else ""),
        name=m.name or "",
        description=m.description or "",
        tags=m.tags or [],
        images=m.images or [],
        owner_id=m.owner_id,
        owner_name=_owner_name(m.owner),
        is_owner=m.owner_id == user.id,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


@router.get("/{library_id}/materials", response_model=list[MaterialOut])
def list_materials(
    library_id: int,
    keyword: str = "",
    scope: str = "all",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Material).filter(Material.library_id == library_id)
    q = scope_filter(q, Material, user, scope)
    if keyword:
        q = q.filter(Material.name.like(f"%{keyword}%"))
    # 素材图片按上传时间倒序，同时间按 id 倒序保持稳定
    rows = q.order_by(Material.created_at.desc(), Material.id.desc()).all()
    return [_material_out(db, m, user) for m in rows]


@router.post("/{library_id}/materials", response_model=MaterialOut)
def create_material(
    library_id: int,
    data: MaterialIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_create(user)
    require_permission(user, "materials.create", db)
    lib = db.query(MaterialLibrary).get(library_id)
    if not lib:
        raise HTTPException(status_code=404, detail="素材库不存在")
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="素材名称不能为空")
    m = Material(
        library_id=library_id,
        name=name,
        description=data.description or "",
        tags=list(data.tags or []),
        images=list(data.images or []),
        owner_id=user.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _material_out(db, m, user)


@router.put("/materials/{material_id}", response_model=MaterialOut)
def update_material(
    material_id: int,
    data: MaterialIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = db.query(Material).get(material_id)
    if not m:
        raise HTTPException(status_code=404, detail="素材不存在")
    ensure_owner(m, user, "编辑")
    require_permission(user, "materials.edit", db)
    provided = data.model_fields_set
    if "name" in provided:
        m.name = (data.name or "").strip() or m.name
    if "description" in provided:
        m.description = data.description or ""
    if "tags" in provided:
        m.tags = list(data.tags or [])
    if "images" in provided:
        m.images = list(data.images or [])
    m.updated_at = datetime.now()
    db.commit()
    db.refresh(m)
    return _material_out(db, m, user)


@router.patch("/materials/{material_id}", response_model=MaterialOut)
def patch_material(
    material_id: int,
    data: MaterialPatchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """素材卡片内改名 / 改备注 / 拖到别的库：只更新传入字段。"""
    m = db.query(Material).get(material_id)
    if not m:
        raise HTTPException(status_code=404, detail="素材不存在")
    ensure_owner(m, user, "编辑")
    provided = data.model_fields_set
    if "name" in provided and data.name is not None:
        name = (data.name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="素材名称不能为空")
        m.name = name
    if "description" in provided and data.description is not None:
        m.description = data.description
    if "library_id" in provided and data.library_id is not None:
        if not db.query(MaterialLibrary).get(data.library_id):
            raise HTTPException(status_code=404, detail="目标素材库不存在")
        m.library_id = data.library_id
    m.updated_at = datetime.now()
    db.commit()
    db.refresh(m)
    return _material_out(db, m, user)


@router.delete("/materials/{material_id}")
def delete_material(
    material_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = db.query(Material).get(material_id)
    if not m:
        raise HTTPException(status_code=404, detail="素材不存在")
    ensure_owner(m, user, "删除")
    require_permission(user, "materials.delete", db)
    db.delete(m)
    db.commit()
    return {"ok": True}
