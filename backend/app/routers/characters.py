from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import ensure_owner, get_current_user, require_create, require_permission, scope_filter
from ..database import get_db
from ..models import Character, CharacterImage, Production, ProductionCharacter, User
from ..schemas import CharacterDetailOut, CharacterIn, CharacterPatchIn

router = APIRouter(prefix="/characters", tags=["characters"])


def _sync_images(db: Session, character: Character, images: list):
    character.images.clear()
    db.flush()
    for i, img in enumerate(images):
        character.images.append(
            CharacterImage(file_path=img.file_path, sort=img.sort if img.sort else i)
        )


VALID_ASSET_TYPES = ("character", "scene", "costume")


def _detail(db: Session, c: Character, user: User) -> CharacterDetailOut:
    item = CharacterDetailOut(
        id=c.id,
        name=c.name or "",
        asset_type=(c.asset_type or "character"),
        description=c.description or "",
        tags=c.tags or [],
        created_at=c.created_at,
        updated_at=c.updated_at,
    )
    item.images = [
        {"id": i.id, "file_path": i.file_path, "sort": i.sort} for i in c.images
    ]
    item.production_count = (
        db.query(ProductionCharacter)
        .filter(ProductionCharacter.character_id == c.id)
        .count()
    )
    item.owner_id = c.owner_id
    item.owner_name = (c.owner.nickname or c.owner.username) if c.owner else "未归属"
    item.is_owner = c.owner_id == user.id
    return item


@router.get("", response_model=list[CharacterDetailOut])
def list_characters(
    scope: str = "all",
    keyword: str = "",
    asset_type: str = "character",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Character)
    q = scope_filter(q, Character, user, scope)
    # asset_type=all 时返回三类全部，否则按指定类型过滤
    if asset_type and asset_type != "all":
        q = q.filter(Character.asset_type == asset_type)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(Character.name.like(like))
    # 资产库图片按上传时间倒序，同时间按 id 倒序保持稳定
    rows = q.order_by(Character.created_at.desc(), Character.id.desc()).all()
    out = []
    for c in rows:
        _ = c.images
        out.append(_detail(db, c, user))
    return out


@router.post("", response_model=CharacterDetailOut)
def create_character(
    data: CharacterIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_create(user)
    require_permission(user, "characters.create", db)
    asset_type = data.asset_type if data.asset_type in VALID_ASSET_TYPES else "character"
    c = Character(
        name=data.name,
        asset_type=asset_type,
        description=data.description,
        tags=data.tags or [],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        owner_id=user.id,
    )
    db.add(c)
    db.flush()
    _sync_images(db, c, data.images)
    db.commit()
    db.refresh(c)
    return _detail(db, c, user)


@router.put("/{character_id}", response_model=CharacterDetailOut)
def update_character(
    character_id: int,
    data: CharacterIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = db.query(Character).get(character_id)
    if not c:
        raise HTTPException(status_code=404, detail="人物不存在")
    ensure_owner(c, user, "编辑")
    require_permission(user, "characters.edit", db)
    c.name = data.name
    c.asset_type = data.asset_type if data.asset_type in VALID_ASSET_TYPES else (c.asset_type or "character")
    c.description = data.description
    c.tags = data.tags or []
    c.updated_at = datetime.now()
    _sync_images(db, c, data.images)
    db.commit()
    db.refresh(c)
    return _detail(db, c, user)


@router.patch("/{character_id}", response_model=CharacterDetailOut)
def patch_character(
    character_id: int,
    data: CharacterPatchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """卡片内直接改名 / 改备注：只更新传入字段，不触碰图片与标签。"""
    c = db.query(Character).get(character_id)
    if not c:
        raise HTTPException(status_code=404, detail="人物不存在")
    ensure_owner(c, user, "编辑")
    require_permission(user, "characters.edit", db)
    provided = data.model_fields_set
    if "name" in provided and data.name is not None:
        name = (data.name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="名称不能为空")
        c.name = name
    if "description" in provided and data.description is not None:
        c.description = data.description
    c.updated_at = datetime.now()
    db.commit()
    db.refresh(c)
    return _detail(db, c, user)


@router.delete("/{character_id}")
def delete_character(
    character_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = db.query(Character).get(character_id)
    if not c:
        raise HTTPException(status_code=404, detail="人物不存在")
    ensure_owner(c, user, "删除")
    require_permission(user, "characters.delete", db)
    used = (
        db.query(ProductionCharacter)
        .filter(ProductionCharacter.character_id == character_id)
        .count()
    )
    if used:
        raise HTTPException(status_code=400, detail=f"有 {used} 条制作记录正在使用该人物，无法删除")
    db.delete(c)
    db.commit()
    return {"ok": True}
