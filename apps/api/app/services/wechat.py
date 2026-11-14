"""Small WeChat mini-program API client.

Login only needs ``jscode2session``. ``get_phone_number`` is kept as an optional
profile-enrichment helper; it is no longer part of the login flow.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import normalize_phone

WECHAT_API = "https://api.weixin.qq.com"
_TOKEN_LOCK = threading.Lock()
_token_cache: dict[str, Any] = {"token": "", "expires_at": 0.0}


def _config() -> tuple[str, str]:
    settings = get_settings()
    if not settings.wechat_mini_appid or not settings.wechat_mini_secret:
        raise AppError(
            503,
            "WECHAT_NOT_CONFIGURED",
            "微信登录尚未配置 WECHAT_MINI_APPID / WECHAT_MINI_SECRET",
        )
    return settings.wechat_mini_appid, settings.wechat_mini_secret


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.request(method, f"{WECHAT_API}{path}", **kwargs)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AppError(
            502,
            "WECHAT_API_ERROR",
            "微信登录服务暂时不可用，请稍后重试",
        ) from exc
    if not isinstance(payload, dict):
        raise AppError(502, "WECHAT_API_ERROR", "微信登录服务返回异常")
    return payload


def _raise_wechat_error(payload: dict[str, Any]) -> None:
    raw = payload.get("errcode")
    if raw in (None, 0, "0"):
        return
    try:
        errcode = int(raw)
    except (TypeError, ValueError):
        errcode = -1
    if errcode in (40029, 40163):
        raise AppError(400, "WECHAT_CODE_INVALID", "微信登录凭证已失效，请重试")
    if errcode == 45011:
        raise AppError(429, "WECHAT_RATE_LIMITED", "微信登录请求过于频繁，请稍后重试")
    raise AppError(502, "WECHAT_API_ERROR", "微信登录服务暂时不可用，请稍后重试")


def _get_access_token(*, force_refresh: bool = False) -> str:
    """Use WeChat's stable_token endpoint and cache it in-process.

    A single API process is enough for this project. When several workers run,
    the stable token API tolerates a cached token per worker better than the
    legacy token endpoint, which invalidates the previous token.
    """
    now = time.monotonic()
    with _TOKEN_LOCK:
        if not force_refresh and _token_cache["token"] and _token_cache["expires_at"] > now:
            return str(_token_cache["token"])

    appid, secret = _config()
    payload = _request(
        "POST",
        "/cgi-bin/stable_token",
        json={
            "grant_type": "client_credential",
            "appid": appid,
            "secret": secret,
            "force_refresh": bool(force_refresh),
        },
    )
    _raise_wechat_error(payload)
    token = str(payload.get("access_token") or "")
    if not token:
        raise AppError(502, "WECHAT_API_ERROR", "微信登录服务未返回 access_token")
    expires_in = int(payload.get("expires_in") or 7200)
    with _TOKEN_LOCK:
        _token_cache["token"] = token
        _token_cache["expires_at"] = time.monotonic() + max(60, expires_in - 120)
    return token


def jscode2session(code: str) -> dict[str, Any]:
    """Exchange wx.login's one-time code for openid/unionid."""
    appid, secret = _config()
    payload = _request(
        "GET",
        "/sns/jscode2session",
        params={
            "appid": appid,
            "secret": secret,
            "js_code": code,
            "grant_type": "authorization_code",
        },
    )
    _raise_wechat_error(payload)
    openid = str(payload.get("openid") or "")
    if not openid:
        raise AppError(502, "WECHAT_API_ERROR", "微信登录服务未返回 openid")
    return {
        "openid": openid,
        "unionid": payload.get("unionid"),
    }


def get_phone_number(phone_code: str) -> str:
    """Exchange getPhoneNumber's one-time code for a verified phone."""
    token = _get_access_token()
    payload = _request(
        "POST",
        "/wxa/business/getuserphonenumber",
        params={"access_token": token},
        json={"code": phone_code},
    )

    # An access token can expire/rotate between requests. Refresh once and
    # retry; never expose the raw WeChat error to the client.
    errcode = payload.get("errcode")
    if errcode in (40001, 42001):
        token = _get_access_token(force_refresh=True)
        payload = _request(
            "POST",
            "/wxa/business/getuserphonenumber",
            params={"access_token": token},
            json={"code": phone_code},
        )

    _raise_wechat_error(payload)
    info = payload.get("phone_info") or {}
    if not isinstance(info, dict):
        raise AppError(502, "WECHAT_API_ERROR", "微信登录服务未返回手机号")
    pure_phone = str(info.get("purePhoneNumber") or "")
    country_code = str(info.get("countryCode") or "86").lstrip("+")
    candidate = pure_phone or str(info.get("phoneNumber") or "")
    if not candidate:
        raise AppError(502, "WECHAT_API_ERROR", "微信登录服务未返回手机号")
    if not candidate.startswith("+"):
        candidate = f"+{country_code}{candidate}"
    return normalize_phone(candidate)
