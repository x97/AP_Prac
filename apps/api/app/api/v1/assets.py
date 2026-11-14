from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

from app.core.assets import resolve_asset_file, verify_asset_request
from app.core.config import get_settings

router = APIRouter(tags=["assets"])


@router.get("/assets/{path:path}")
def content_asset(path: str, request: Request):
    settings = get_settings()
    if settings.asset_signing_required and not verify_asset_request(
        request, path, settings.resolved_asset_signing_key
    ):
        return JSONResponse(
            status_code=403,
            content={"code": "ASSET_SIGNATURE_INVALID", "message": "资源链接无效或已过期"},
        )
    assets_root = settings.resolve_content_dir() / "assets"
    target = resolve_asset_file(assets_root, path)
    if target is None:
        return JSONResponse(
            status_code=404,
            content={"code": "ASSET_NOT_FOUND", "message": "资源不存在"},
        )
    return FileResponse(
        target,
        headers={"Cache-Control": "private, max-age=600"},
    )
