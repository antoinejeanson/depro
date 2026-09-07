"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routers import auth


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


@app.get("/api/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
