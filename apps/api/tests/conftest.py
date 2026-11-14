from __future__ import annotations

import os
import shutil
from datetime import timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "data" / "releases" / "current"
TEST_DB = Path("/tmp/ap_psych_api_test.db")
TEST_EFFECTIVE = Path("/tmp/ap_psych_effective_test")

if TEST_DB.exists():
    TEST_DB.unlink()
if TEST_EFFECTIVE.exists():
    shutil.rmtree(TEST_EFFECTIVE, ignore_errors=True)

os.environ.setdefault("CONTENT_DIR", str(RELEASE))
os.environ.setdefault("DATABASE_URL", f"sqlite+pysqlite:///{TEST_DB}")
os.environ.setdefault("EMAIL_PROVIDER", "dev")
os.environ.setdefault("EXPOSE_DEV_OTP", "true")
os.environ.setdefault("DEV_OTP_CODE", "246810")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("AUTO_CREATE_TABLES", "true")
os.environ.setdefault("EFFECTIVE_CONTENT_DIR", str(TEST_EFFECTIVE))
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("OTP_IP_PER_HOUR", "1000")
os.environ.setdefault("OTP_EMAIL_PER_MINUTE", "10")
os.environ.setdefault("OTP_EMAIL_PER_HOUR", "100")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.core.time import utcnow  # noqa: E402
from app.main import app  # noqa: E402
from app.users.models import User, UserEntitlement  # noqa: E402

_counter = 0


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def grant_entitlement(phone: str, subject_id: str = "psychology", days: int = 365) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.phone == phone))
        if not user:
            raise AssertionError("test user not found")
        row = db.scalar(
            select(UserEntitlement).where(
                UserEntitlement.user_id == user.id,
                UserEntitlement.subject_id == subject_id,
            )
        )
        expires_at = utcnow() + timedelta(days=days)
        if row:
            row.expires_at = expires_at
        else:
            db.add(
                UserEntitlement(
                    user_id=user.id,
                    subject_id=subject_id,
                    expires_at=expires_at,
                    source="test",
                )
            )
        db.commit()


def login(client: TestClient, entitle: bool = True) -> str:
    """Register an email account and return its synthetic legacy phone.

    Tests written before the email migration look users up by ``User.phone``,
    so the helper keeps a unique phone value on the row while authenticating
    through the email flow.
    """
    global _counter
    _counter += 1
    email = f"test{_counter}@example.com"
    phone = f"+86139{_counter:08d}"
    r = client.post(
        "/api/v1/auth/email/code", json={"email": email, "purpose": "register"}
    )
    assert r.status_code == 200, r.text
    code = r.json().get("debug_code") or "246810"
    r = client.post(
        "/api/v1/auth/email/register",
        json={"email": email, "code": code, "password": "test-password-123"},
    )
    assert r.status_code == 200, r.text

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            raise AssertionError("test user not found")
        user.phone = phone
        db.commit()

    if entitle:
        grant_entitlement(phone)
    return phone
