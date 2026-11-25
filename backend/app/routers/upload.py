import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..auth import get_current_user
from ..database import UPLOAD_DIR
from ..models import User

router = APIRouter(prefix="/upload", tags=["upload"])

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".avi"}


@router.post("")
async def upload(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in IMAGE_EXTS | VIDEO_EXTS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    sub = datetime.now().strftime("%Y-%m")
    save_dir = os.path.join(UPLOAD_DIR, sub)
    os.makedirs(save_dir, exist_ok=True)

    fname = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(save_dir, fname)
    with open(save_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)

    return {"url": f"/uploads/{sub}/{fname}", "filename": file.filename}
