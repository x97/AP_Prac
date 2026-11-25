from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from ipaddress import ip_address
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import (
    admin,
    admin_graph,
    admin_plans,
    assets,
    attempts,
    auth,
    content,
    custom_flashcards,
    flashcards,
    me,
    practice,
    study_calendar,
)
from app.content.store import ContentStore
from app.core.config import get_settings
from app.core.db import engine, init_db
from app.core.errors import AppError, app_error_handler, error_payload
from app.core.http_security import (
    content_encryption_middleware,
    security_headers_middleware,
)
from app.core.logging import request_id_middleware
from app.core.rate_limit import rate_limit_middleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env == "prod" and settings.email_provider == "dev":
        raise RuntimeError("Refusing to start production with EMAIL_PROVIDER=dev")
    content_dir = settings.resolve_content_dir()
    logger.info("content release: %s", content_dir)
    app.state.store = ContentStore(content_dir, settings)
    init_db()
    app.state.content_dir = content_dir
    # Knowledge graph payloads are immutable for a Release and access is
    # filtered per user. Build the per-Unit JSON caches once at startup so the
    # first graph request does not pay the SQLite scan/serialization cost.
    warmed = 0
    for group in app.state.store.list_groups():
        unit_id = str(group.get("unit_id") or "")
        if not unit_id:
            continue
        try:
            app.state.store.unit_knowledge_graph(unit_id)
            warmed += 1
        except Exception:  # noqa: BLE001
            logger.exception("failed to warm knowledge graph for unit %s", unit_id)
    logger.info("knowledge graph cache warmed: %s units", warmed)
    yield


app = FastAPI(
    title="AP Psychology API",
    version="0.1.0",
    lifespan=lifespan,
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _is_dev_lan_origin(origin: str) -> bool:
    parsed = urlparse(origin)
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False
    if host == "localhost":
        return True
    try:
        address = ip_address(host)
    except ValueError:
        return False
    return address.is_private or address.is_loopback


@app.middleware("http")
async def origin_guard(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin:
            host = request.headers.get("host", "")
            allowed = set(settings.cors_origin_list)
            if host:
                allowed.add(f"http://{host}")
                allowed.add(f"https://{host}")
            allowed_origin = origin in allowed
            # Local dev is often opened through the machine's LAN IP
            # (e.g. phone on the same Wi-Fi). Production stays exact-match.
            if not allowed_origin and settings.app_env != "prod" and _is_dev_lan_origin(origin):
                allowed_origin = True
            if not allowed_origin:
                return JSONResponse(
                    status_code=403,
                    content=error_payload(request, "ORIGIN_REJECTED", "请求来源不被允许"),
                )
    return await call_next(request)


app.middleware("http")(request_id_middleware)
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(content_encryption_middleware)
app.middleware("http")(security_headers_middleware)


@app.exception_handler(AppError)
async def _app_error(request: Request, exc: AppError):
    return app_error_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=error_payload(request, "VALIDATION_ERROR", "请求参数不正确", exc.errors()),
    )


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    logger.exception("unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content=error_payload(request, "INTERNAL_ERROR", "服务器内部错误"),
    )


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/readyz")
def readyz(request: Request):
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    store = getattr(request.app.state, "store", None)
    if store is None:
        return JSONResponse(status_code=503, content={"ok": False, "reason": "content not loaded"})
    return {"ok": True, "release_id": store.release_id}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(content.router, prefix="/api/v1")
app.include_router(practice.router, prefix="/api/v1")
app.include_router(attempts.router, prefix="/api/v1")
app.include_router(flashcards.router, prefix="/api/v1")
app.include_router(custom_flashcards.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(admin_graph.router, prefix="/api/v1")
app.include_router(admin_plans.router, prefix="/api/v1")
app.include_router(study_calendar.router, prefix="/api/v1")
app.include_router(me.router, prefix="/api/v1")
app.include_router(assets.router)
