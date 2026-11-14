"""Response hardening: content encryption envelope + cache/security headers."""

from __future__ import annotations

import json

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from app.core.content_crypto import aad_for, encrypt_for_client, get_client_public_key


def _is_secure_path(path: str, prefixes: list[str]) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes)


async def _response_body(response) -> bytes | None:
    body = getattr(response, "body", None)
    if body is not None:
        return body
    iterator = getattr(response, "body_iterator", None)
    if iterator is None:
        return None
    chunks: list[bytes] = []
    async for chunk in iterator:
        chunks.append(chunk if isinstance(chunk, bytes) else str(chunk).encode("utf-8"))
    return b"".join(chunks)


async def content_encryption_middleware(request: Request, call_next):
    from app.core.config import get_settings

    settings = get_settings()
    mode = settings.content_encryption_mode.lower().strip()
    secure_path = _is_secure_path(request.url.path, settings.content_encryption_prefix_list)
    client_key = get_client_public_key(request)

    if secure_path and mode == "required" and not client_key:
        return JSONResponse(
            status_code=428,
            content={
                "code": "CONTENT_KEY_REQUIRED",
                "message": "客户端未提供内容解密公钥",
            },
        )
    if not secure_path or not client_key or mode == "off":
        return await call_next(request)

    response = await call_next(request)
    if response.status_code >= 400:
        return response
    body = await _response_body(response)
    content_type = response.headers.get("content-type", "")
    if not body or "application/json" not in content_type:
        return response

    try:
        envelope = encrypt_for_client(
            body,
            client_key,
            aad_for(request.method, request.url.path),
        )
    except (ValueError, TypeError):
        return JSONResponse(
            status_code=400,
            content={
                "code": "CONTENT_KEY_INVALID",
                "message": "内容解密公钥不合法",
            },
        )

    headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in {"content-length", "content-encoding", "content-type", "etag"}
    }
    headers["X-Content-Encrypted"] = "1"
    headers["Cache-Control"] = "private, no-store"
    return Response(
        content=json.dumps(envelope, separators=(",", ":")).encode("utf-8"),
        status_code=response.status_code,
        headers=headers,
        media_type="application/json",
    )


async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "private, no-store")
        response.headers.setdefault("Pragma", "no-cache")
    return response
