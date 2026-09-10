"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.routers import auth, export, tags, tasks, timeboxes


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="depro API",
    description="To-do planning for recovering procrastinators.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(timeboxes.timeboxes_router, prefix="/api")
app.include_router(timeboxes.series_router, prefix="/api")
app.include_router(export.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


def _web_dist() -> Path | None:
    """Built frontend directory (DEPRO_WEB_DIST), if it exists."""
    raw = os.environ.get("DEPRO_WEB_DIST")
    if raw and (Path(raw) / "index.html").is_file():
        return Path(raw)
    return None


WEB_DIST = _web_dist()

if WEB_DIST is not None:
    if (WEB_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"))

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        """Serve the SPA for any non-API path (client-side routing)."""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (WEB_DIST / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(WEB_DIST.resolve()):
            return FileResponse(candidate)
        return FileResponse(WEB_DIST / "index.html")
