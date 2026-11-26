"""Production entrypoint: FastAPI backend + prebuilt Vue frontend on one port.

Run from the backend directory:
    python -m uvicorn serve:app --host 0.0.0.0 --port 8000
"""

from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.main import app

BACKEND_DIR = Path(__file__).resolve().parent
DIST_DIR = BACKEND_DIR.parent / "frontend" / "dist"

if not (DIST_DIR / "index.html").is_file():
    raise RuntimeError(
        f"Frontend build not found at {DIST_DIR}. "
        "Run 'npm install && npm run build' inside frontend first."
    )

# Static assets emitted by Vite (JS / CSS bundles).
app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    """Serve root static files, then fall back to index.html for Vue Router."""
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail="Not Found")

    # Guard against path traversal: resolve and verify it stays inside dist.
    if full_path:
        candidate = (DIST_DIR / full_path).resolve()
        if candidate.is_file() and DIST_DIR.resolve() in candidate.parents:
            return FileResponse(candidate)

    return FileResponse(DIST_DIR / "index.html")
