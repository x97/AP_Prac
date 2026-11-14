"""Signed, expiring URLs for content assets."""

from __future__ import annotations

import hashlib
import hmac
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import Request

ASSET_PREFIX = "assets/"


def normalize_asset_path(path: str) -> str:
    path = path.replace("\\", "/").lstrip("/")
    if path.startswith(ASSET_PREFIX):
        path = path[len(ASSET_PREFIX) :]
    return path


def _signature(secret: str, path: str, expires: int) -> str:
    message = f"{path}|{expires}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def sign_asset_url(path: str, base_url: str, secret: str, ttl_seconds: int) -> str:
    path = normalize_asset_path(path)
    expires = int(time.time()) + max(60, ttl_seconds)
    signature = _signature(secret, path, expires)
    base = (base_url or "/assets").rstrip("/")
    return f"{base}/{quote(path, safe='/')}?exp={expires}&sig={signature}"


def verify_asset_request(request: Request, path: str, secret: str) -> bool:
    expires_raw = request.query_params.get("exp", "")
    signature = request.query_params.get("sig", "")
    try:
        expires = int(expires_raw)
    except ValueError:
        return False
    if expires < int(time.time()):
        return False
    expected = _signature(secret, normalize_asset_path(path), expires)
    return hmac.compare_digest(expected, signature)


def resolve_asset_file(assets_root: Path, path: str) -> Path | None:
    normalized = normalize_asset_path(path)
    root = assets_root.resolve()
    target = (root / normalized).resolve()
    if root != target and root not in target.parents:
        return None
    if not target.is_file():
        return None
    return target
