"""Accounts: identity API + hosted login SPA."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import app.env_loader  # noqa: F401
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.api import auth_router, users
from app.auth import public_jwks
from app.avatar_storage import UPLOADS_ROOT, ensure_avatar_dir
from app.db import DATABASE_URL_ERROR, engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if engine is None:
        raise RuntimeError(DATABASE_URL_ERROR)
    logger.info("Connected to database: %s", engine.url.render_as_string(hide_password=True))
    ensure_avatar_dir()
    yield


_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
]
_cors = os.getenv("CORS_ORIGINS", "").strip()
if _cors:
    _origins.extend(s.strip() for s in _cors.split(",") if s.strip())

app = FastAPI(
    title="Accounts",
    description="Shared identity service for sibling apps",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api")
app.include_router(users.router, prefix="/api")


@app.get("/.well-known/jwks.json")
def jwks():
    return public_jwks()


@app.get("/health")
def health():
    return {"ok": True}


ensure_avatar_dir()
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_ROOT)), name="uploads")

_FRONTEND_DIST = os.getenv("FRONTEND_DIST", "").strip()
if not _FRONTEND_DIST:
    # Default: repo frontend/dist relative to service/
    candidate = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if candidate.is_dir():
        _FRONTEND_DIST = str(candidate)

if _FRONTEND_DIST and Path(_FRONTEND_DIST).is_dir():
    _dist = Path(_FRONTEND_DIST)

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        # Don't shadow API / well-known / uploads
        if full_path.startswith(("api/", ".well-known/", "uploads/", "health")):
            return ORJSONResponse({"detail": "Not found"}, status_code=404)
        file_path = _dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        index = _dist / "index.html"
        if index.is_file():
            return FileResponse(index)
        return ORJSONResponse({"detail": "Frontend not built"}, status_code=404)
