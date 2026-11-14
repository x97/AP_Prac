from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.schemas import (
    EmailCodeRequest,
    EmailLoginRequest,
    EmailRegisterRequest,
    EmailResetRequest,
    WechatBindRequest,
    WechatLoginRequest,
)
from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.security import (
    clear_session_cookie,
    client_ip,
    create_session,
    hash_password,
    hash_token,
    normalize_email,
    request_token,
    resolve_merged_user,
    revoke_user_sessions,
    set_session_cookie,
    validate_password,
    verify_password,
)
from app.core.time import utcnow
from app.services import account_merge, verification_codes, wechat
from app.users.models import User, UserIdentity, UserSession
from app.users.payload import user_payload

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _find_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.scalar(select(User).where(User.email == email))


def _session_payload(
    db: Session, user: User, request: Request, response: Response | None = None
) -> dict:
    token = create_session(db, user, request, settings)
    db.commit()
    if response is not None:
        set_session_cookie(response, token, settings)
    return {
        "token": token,
        "expires_in": settings.session_days * 24 * 3600,
        "user": user_payload(user),
    }


@router.post("/email/code")
def send_email_code(
    body: EmailCodeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    email = normalize_email(body.email)
    return verification_codes.issue_code(
        db,
        identifier=email,
        purpose=body.purpose,
        ip=client_ip(request),
        settings=settings,
    )


@router.post("/email/register")
def register_with_email(
    body: EmailRegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    email = normalize_email(body.email)
    validate_password(body.password, settings)
    verification_codes.verify_code(
        db,
        identifier=email,
        purpose="register",
        code=body.code,
        settings=settings,
    )

    if _find_user_by_email(db, email):
        # The code proved mailbox ownership, so telling the owner the address
        # is already registered is safe. Persist the consumption first.
        db.commit()
        raise AppError(
            409,
            "EMAIL_ALREADY_REGISTERED",
            "该邮箱已注册，请直接登录或找回密码",
        )

    user = User(
        email=email,
        email_verified_at=utcnow(),
        password_hash=hash_password(body.password),
        password_changed_at=utcnow(),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            409,
            "EMAIL_ALREADY_REGISTERED",
            "该邮箱已注册，请直接登录或找回密码",
        ) from exc

    return _session_payload(db, user, request, response)


@router.post("/email/login")
def login_with_email(
    body: EmailLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    email = normalize_email(body.email)
    user = _find_user_by_email(db, email)
    if (
        not user
        or not user.password_hash
        or user.status != "active"
        or not verify_password(body.password, user.password_hash)
    ):
        raise AppError(401, "EMAIL_OR_PASSWORD_INVALID", "邮箱或密码不正确")

    return _session_payload(db, user, request, response)


@router.post("/email/reset-password")
def reset_password_with_email(
    body: EmailResetRequest,
    db: Session = Depends(get_db),
):
    email = normalize_email(body.email)
    validate_password(body.password, settings)
    verification_codes.verify_code(
        db,
        identifier=email,
        purpose="reset",
        code=body.code,
        settings=settings,
    )

    user = _find_user_by_email(db, email)
    if not user or user.status != "active":
        db.commit()
        raise AppError(400, "EMAIL_CODE_INVALID", "验证码无效，请重新获取")

    user.password_hash = hash_password(body.password)
    user.password_changed_at = utcnow()
    if not user.email_verified_at:
        user.email_verified_at = utcnow()
    revoke_user_sessions(db, user.id)
    db.commit()
    return {"ok": True}


def _wechat_identity(
    db: Session, *, app_id: str, openid: str, unionid: Optional[str]
) -> Optional[UserIdentity]:
    identity = db.scalar(
        select(UserIdentity).where(
            UserIdentity.provider == "wechat_mini",
            UserIdentity.app_id == app_id,
            UserIdentity.provider_uid == openid,
        )
    )
    if identity:
        return identity
    # Rows created before app_id existed are still valid for the current app.
    identity = db.scalar(
        select(UserIdentity)
        .where(
            UserIdentity.provider == "wechat_mini",
            UserIdentity.provider_uid == openid,
            UserIdentity.app_id.in_([app_id, ""]),
        )
        .order_by(UserIdentity.created_at)
        .limit(1)
    )
    if identity and not identity.app_id:
        identity.app_id = app_id
    if identity:
        return identity
    if not unionid:
        return None
    identity = db.scalar(
        select(UserIdentity)
        .where(UserIdentity.unionid == unionid)
        .order_by(UserIdentity.created_at)
        .limit(1)
    )
    if identity:
        # Same WeChat person in another app: attach a new identity row rather
        # than creating a second account.
        db.add(
            UserIdentity(
                user_id=identity.user_id,
                provider="wechat_mini",
                app_id=app_id,
                provider_uid=openid,
                unionid=unionid,
            )
        )
        db.flush()
    return identity


@router.post("/wechat/login")
def wechat_login(
    body: WechatLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Exchange wx.login's code for a session.

    No phone number is requested. A first-time WeChat user gets a virtual
    account (``email IS NULL``); binding an email later upgrades or merges it.
    """
    if not settings.wechat_mini_appid or not settings.wechat_mini_secret:
        raise AppError(
            503,
            "WECHAT_NOT_CONFIGURED",
            "微信登录尚未配置 WECHAT_MINI_APPID / WECHAT_MINI_SECRET",
        )

    wx_session = wechat.jscode2session(body.code)
    openid = wx_session["openid"]
    unionid = wx_session.get("unionid")
    identity = _wechat_identity(
        db, app_id=settings.wechat_mini_appid, openid=openid, unionid=unionid
    )

    if identity:
        user = resolve_merged_user(db, db.get(User, identity.user_id))
        if not user:
            raise AppError(409, "WECHAT_IDENTITY_BROKEN", "微信账号绑定状态异常")
    else:
        user = User()
        db.add(user)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise AppError(500, "USER_CREATE_FAILED", "登录失败，请重试") from exc
        db.add(
            UserIdentity(
                user_id=user.id,
                provider="wechat_mini",
                app_id=settings.wechat_mini_appid,
                provider_uid=openid,
                unionid=unionid,
            )
        )
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            identity = _wechat_identity(
                db, app_id=settings.wechat_mini_appid, openid=openid, unionid=unionid
            )
            user = resolve_merged_user(db, db.get(User, identity.user_id)) if identity else None
            if not user:
                raise AppError(500, "WECHAT_BIND_FAILED", "微信账号绑定失败，请重试")

    if user.status != "active":
        raise AppError(403, "ACCOUNT_DISABLED", "账号不可用，请联系客服")

    return _session_payload(db, user, request)


def _find_wechat_identity_for_bind(
    db: Session, *, app_id: str, openid: str, unionid: Optional[str]
) -> Optional[UserIdentity]:
    identity = db.scalar(
        select(UserIdentity).where(
            UserIdentity.provider == "wechat_mini",
            UserIdentity.app_id == app_id,
            UserIdentity.provider_uid == openid,
        )
    )
    if identity:
        return identity
    if not unionid:
        return None
    return db.scalar(
        select(UserIdentity)
        .where(UserIdentity.unionid == unionid)
        .order_by(UserIdentity.created_at)
        .limit(1)
    )


def _require_current_password(user: User, password: Optional[str]) -> None:
    if user.password_hash and (
        not password or not verify_password(password, user.password_hash)
    ):
        raise AppError(400, "PASSWORD_INVALID", "请输入正确的当前密码")


def _ensure_no_other_wechat(
    db: Session, *, user_id: str, app_id: str, openid: str
) -> None:
    other = db.scalar(
        select(UserIdentity).where(
            UserIdentity.user_id == user_id,
            UserIdentity.provider == "wechat_mini",
            UserIdentity.app_id == app_id,
            UserIdentity.provider_uid != openid,
        )
    )
    if other:
        raise AppError(409, "WECHAT_ALREADY_BOUND", "当前账号已绑定其他微信")


@router.post("/wechat/bind")
def bind_wechat(
    body: WechatBindRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Attach the current WeChat to an email account after email login.

    The mini program calls this right after email login/registration so the
    next WeChat one-click login resolves to the same account instead of
    creating a fresh virtual account. Binding a WeChat that already owns a
    virtual account merges that account into the email account.
    """
    if not settings.wechat_mini_appid or not settings.wechat_mini_secret:
        raise AppError(
            503,
            "WECHAT_NOT_CONFIGURED",
            "微信登录尚未配置 WECHAT_MINI_APPID / WECHAT_MINI_SECRET",
        )
    if not user.email:
        raise AppError(400, "EMAIL_REQUIRED", "请先绑定邮箱后再关联微信")
    if user.status != "active":
        raise AppError(403, "ACCOUNT_DISABLED", "账号不可用，请联系客服")

    wx_session = wechat.jscode2session(body.code)
    openid = wx_session["openid"]
    unionid = wx_session.get("unionid")
    app_id = settings.wechat_mini_appid
    identity = _find_wechat_identity_for_bind(
        db, app_id=app_id, openid=openid, unionid=unionid
    )

    if identity:
        owner = resolve_merged_user(db, db.get(User, identity.user_id))
        if not owner:
            raise AppError(409, "WECHAT_IDENTITY_BROKEN", "微信账号绑定状态异常")
        if owner.id == user.id:
            if identity.app_id == app_id and identity.provider_uid == openid:
                return {"user": user_payload(user), "status": "already_bound"}
            # Same WeChat via unionid in another app: add this app's identity.
            _require_current_password(user, body.password)
            _ensure_no_other_wechat(
                db, user_id=user.id, app_id=app_id, openid=openid
            )
            db.add(
                UserIdentity(
                    user_id=user.id,
                    provider="wechat_mini",
                    app_id=app_id,
                    provider_uid=openid,
                    unionid=unionid,
                )
            )
            try:
                db.flush()
            except IntegrityError as exc:
                db.rollback()
                raise AppError(
                    409,
                    "WECHAT_BIND_CONFLICT",
                    "微信绑定状态已变化，请重试",
                ) from exc
            db.commit()
            return {"user": user_payload(user), "status": "bound"}
        if owner.email is None and owner.status == "active":
            _require_current_password(user, body.password)
            _ensure_no_other_wechat(
                db, user_id=user.id, app_id=app_id, openid=openid
            )
            counts = account_merge.merge_users(db, owner, user)
            db.commit()
            return {
                "user": user_payload(user),
                "status": "merged",
                "merge_counts": counts,
            }
        raise AppError(
            409,
            "WECHAT_BOUND_TO_OTHER_ACCOUNT",
            "该微信已绑定其他账号，请直接使用微信登录",
        )

    _require_current_password(user, body.password)
    _ensure_no_other_wechat(db, user_id=user.id, app_id=app_id, openid=openid)
    db.add(
        UserIdentity(
            user_id=user.id,
            provider="wechat_mini",
            app_id=app_id,
            provider_uid=openid,
            unionid=unionid,
        )
    )
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            409, "WECHAT_ALREADY_BOUND", "该微信已绑定其他账号，请直接使用微信登录"
        ) from exc
    db.commit()
    return {"user": user_payload(user), "status": "bound"}


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token = request_token(request)
    if token:
        session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
        if session:
            db.delete(session)
            db.commit()
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"user": user_payload(user)}
