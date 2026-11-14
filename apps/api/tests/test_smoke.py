from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from tests.conftest import RELEASE, login


def test_content_endpoints(client):
    assert client.get("/healthz").status_code == 200
    import json
    from pathlib import Path

    version = client.get("/api/v1/content/version").json()
    release_manifest = json.loads(
        (Path(__file__).resolve().parents[3] / "data/releases/current/release.json").read_text()
    )
    assert version["release_id"] == release_manifest["release_id"]
    assert version["counts"]["questions"] == 3155
    assert client.get("/api/v1/practice-groups").status_code == 401
    login(client)
    groups = client.get("/api/v1/practice-groups").json()
    assert len(groups) == 5
    assert all(g["group_id"].startswith("psychology-") for g in groups)
    papers = client.get("/api/v1/papers").json()
    assert len(papers) == 14
    assert all(p["paper_id"].startswith("psychology-") for p in papers)


def test_mcq_submit_multiple_answers_updates_daily_once(client):
    from app.core.db import SessionLocal
    from app.users.models import User, UserDailyStat

    phone = login(client)
    created = client.post(
        "/api/v1/attempts", json={"paper_id": "psychology-ap-2025", "mode": "mcq"}
    )
    assert created.status_code == 200, created.text
    state = created.json()
    answers = [
        {
            "question_id": question["question_id"],
            "selected_label": question["options"][0]["label"],
        }
        for question in state["questions"][:2]
    ]
    saved = client.patch(
        f"/api/v1/attempts/{state['attempt']['id']}/answers",
        json={"answers": answers},
    )
    assert saved.status_code == 200, saved.text
    submitted = client.post(
        f"/api/v1/attempts/{state['attempt']['id']}/sections/mcq/submit"
    )
    assert submitted.status_code == 200, submitted.text

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.phone == phone))
        assert user is not None
        daily = db.scalars(
            select(UserDailyStat).where(UserDailyStat.user_id == user.id)
        ).all()
        assert len(daily) == 1
        assert daily[0].answered == 2


def test_topic_inference_for_exam_question():
    from app.content.store import ContentStore
    from app.core.config import get_settings

    store = ContentStore(RELEASE, get_settings())
    topic = store.topic_for_question("psychology-2025-mcq-001")
    assert topic is not None
    assert topic["code"] == "1.4"


def test_bearer_session_and_logout(client):
    login(client)
    token = client.cookies.get("ap_session")
    assert token

    client.cookies.clear()
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["user"]["email_masked"]

    out = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert out.status_code == 200
    after = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after.status_code == 401


def test_email_password_change_and_reset(client):
    import secrets

    email = f"password-{secrets.randbelow(10**8)}@example.com"
    sent = client.post(
        "/api/v1/auth/email/code", json={"email": email, "purpose": "register"}
    )
    assert sent.status_code == 200, sent.text
    registered = client.post(
        "/api/v1/auth/email/register",
        json={"email": email, "code": "246810", "password": "old-password-123"},
    )
    assert registered.status_code == 200, registered.text

    changed = client.post(
        "/api/v1/me/password",
        json={"old_password": "old-password-123", "new_password": "new-password-123"},
    )
    assert changed.status_code == 200, changed.text
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert (
        client.post(
            "/api/v1/auth/email/login",
            json={"email": email, "password": "old-password-123"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/email/login",
            json={"email": email, "password": "new-password-123"},
        ).status_code
        == 200
    )

    sent = client.post(
        "/api/v1/auth/email/code", json={"email": email, "purpose": "reset"}
    )
    assert sent.status_code == 200, sent.text
    reset = client.post(
        "/api/v1/auth/email/reset-password",
        json={"email": email, "code": "246810", "password": "reset-password-123"},
    )
    assert reset.status_code == 200, reset.text
    assert (
        client.post(
            "/api/v1/auth/email/login",
            json={"email": email, "password": "reset-password-123"},
        ).status_code
        == 200
    )


def test_wechat_login_not_configured(client):
    response = client.post(
        "/api/v1/auth/wechat/login",
        json={"code": "fake-login-code"},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "WECHAT_NOT_CONFIGURED"


def _enable_wechat(monkeypatch, openid: str):
    from app.api.v1 import auth as auth_module

    monkeypatch.setattr(auth_module.settings, "wechat_mini_appid", "wx-test-appid")
    monkeypatch.setattr(auth_module.settings, "wechat_mini_secret", "test-secret")
    monkeypatch.setattr(
        auth_module.wechat,
        "jscode2session",
        lambda code: {"openid": openid, "unionid": None},
    )
    return auth_module


def test_wechat_login_creates_virtual_account(client, monkeypatch):
    _enable_wechat(monkeypatch, "openid-virtual")

    response = client.post("/api/v1/auth/wechat/login", json={"code": "login-code"})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["token"]
    assert payload["user"]["email"] is None
    assert payload["user"]["has_password"] is False

    again = client.post("/api/v1/auth/wechat/login", json={"code": "login-code"})
    assert again.status_code == 200, again.text
    assert again.json()["user"]["id"] == payload["user"]["id"]


def test_wechat_bind_links_email_account(client, monkeypatch):
    import secrets

    email = f"wechat-bind-{secrets.randbelow(10**8)}@example.com"
    sent = client.post(
        "/api/v1/auth/email/code", json={"email": email, "purpose": "register"}
    )
    assert sent.status_code == 200, sent.text
    registered = client.post(
        "/api/v1/auth/email/register",
        json={"email": email, "code": "246810", "password": "bind-password-123"},
    )
    assert registered.status_code == 200, registered.text
    user_id = registered.json()["user"]["id"]

    _enable_wechat(monkeypatch, "openid-bind")
    missing_password = client.post(
        "/api/v1/auth/wechat/bind", json={"code": "login-code"}
    )
    assert missing_password.status_code == 400, missing_password.text
    assert missing_password.json()["code"] == "PASSWORD_INVALID"

    bound = client.post(
        "/api/v1/auth/wechat/bind",
        json={"code": "login-code", "password": "bind-password-123"},
    )
    assert bound.status_code == 200, bound.text
    assert bound.json()["status"] == "bound"

    via_wechat = client.post(
        "/api/v1/auth/wechat/login", json={"code": "login-code"}
    )
    assert via_wechat.status_code == 200, via_wechat.text
    assert via_wechat.json()["user"]["id"] == user_id


def test_wechat_bind_merges_virtual_account(client, monkeypatch):
    import secrets

    from app.core.db import SessionLocal
    from app.core.time import utcnow
    from app.users.models import User, UserDailyStat

    email = f"wechat-merge-{secrets.randbelow(10**8)}@example.com"
    sent = client.post(
        "/api/v1/auth/email/code", json={"email": email, "purpose": "register"}
    )
    assert sent.status_code == 200, sent.text
    registered = client.post(
        "/api/v1/auth/email/register",
        json={"email": email, "code": "246810", "password": "merge-bind-password"},
    )
    assert registered.status_code == 200, registered.text
    target_id = registered.json()["user"]["id"]

    _enable_wechat(monkeypatch, "openid-bind-merge")
    virtual = client.post("/api/v1/auth/wechat/login", json={"code": "login-code"})
    assert virtual.status_code == 200, virtual.text
    virtual_id = virtual.json()["user"]["id"]

    with SessionLocal() as db:
        virtual_user = db.get(User, virtual_id)
        assert virtual_user is not None
        db.add(
            UserDailyStat(
                user_id=virtual_user.id,
                day=utcnow().date(),
                answered=4,
                correct=3,
            )
        )
        db.commit()

    bound = client.post(
        "/api/v1/auth/wechat/bind",
        json={"code": "login-code", "password": "merge-bind-password"},
    )
    assert bound.status_code == 200, bound.text
    body = bound.json()
    assert body["status"] == "merged"
    assert body["user"]["id"] == target_id

    with SessionLocal() as db:
        source = db.get(User, virtual_id)
        assert source is not None
        assert source.status == "merged"
        assert source.merged_into_id == target_id
        assert db.scalar(
            select(UserDailyStat).where(UserDailyStat.user_id == target_id)
        ) is not None

    via_wechat = client.post(
        "/api/v1/auth/wechat/login", json={"code": "login-code"}
    )
    assert via_wechat.status_code == 200, via_wechat.text
    assert via_wechat.json()["user"]["id"] == target_id


def test_wechat_bind_conflicts_with_other_email_account(client, monkeypatch):
    import secrets

    _enable_wechat(monkeypatch, "openid-bind-conflict")
    first_email = f"wechat-first-{secrets.randbelow(10**8)}@example.com"
    sent = client.post(
        "/api/v1/auth/email/code", json={"email": first_email, "purpose": "register"}
    )
    assert sent.status_code == 200, sent.text
    first = client.post(
        "/api/v1/auth/email/register",
        json={"email": first_email, "code": "246810", "password": "first-password-123"},
    )
    assert first.status_code == 200, first.text
    bound = client.post(
        "/api/v1/auth/wechat/bind",
        json={"code": "login-code", "password": "first-password-123"},
    )
    assert bound.status_code == 200, bound.text

    client.cookies.clear()
    second_email = f"wechat-second-{secrets.randbelow(10**8)}@example.com"
    sent = client.post(
        "/api/v1/auth/email/code", json={"email": second_email, "purpose": "register"}
    )
    assert sent.status_code == 200, sent.text
    second = client.post(
        "/api/v1/auth/email/register",
        json={"email": second_email, "code": "246810", "password": "second-password-123"},
    )
    assert second.status_code == 200, second.text
    conflict = client.post(
        "/api/v1/auth/wechat/bind",
        json={"code": "login-code", "password": "second-password-123"},
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["code"] == "WECHAT_BOUND_TO_OTHER_ACCOUNT"


def test_wechat_bind_email_merges_virtual_account(client, monkeypatch):
    from app.core.db import SessionLocal
    from app.core.time import utcnow
    from app.users.models import User, UserDailyStat

    email = "merge-target@example.com"
    sent = client.post(
        "/api/v1/auth/email/code", json={"email": email, "purpose": "register"}
    )
    assert sent.status_code == 200, sent.text
    registered = client.post(
        "/api/v1/auth/email/register",
        json={"email": email, "code": "246810", "password": "merge-password-123"},
    )
    assert registered.status_code == 200, registered.text
    target_id = registered.json()["user"]["id"]

    # Drop the email account's cookie so the virtual bearer token is used.
    client.cookies.clear()
    _enable_wechat(monkeypatch, "openid-merge")
    virtual = client.post("/api/v1/auth/wechat/login", json={"code": "login-code"})
    assert virtual.status_code == 200, virtual.text
    virtual_id = virtual.json()["user"]["id"]
    virtual_token = virtual.json()["token"]

    with SessionLocal() as db:
        virtual_user = db.get(User, virtual_id)
        assert virtual_user is not None
        db.add(
            UserDailyStat(
                user_id=virtual_user.id,
                day=utcnow().date(),
                answered=3,
                correct=2,
            )
        )
        db.commit()

    sent = client.post(
        "/api/v1/me/email/code",
        json={"email": email},
        headers={"Authorization": f"Bearer {virtual_token}"},
    )
    assert sent.status_code == 200, sent.text
    bound = client.post(
        "/api/v1/me/email/bind",
        json={"email": email, "code": "246810"},
        headers={"Authorization": f"Bearer {virtual_token}"},
    )
    assert bound.status_code == 200, bound.text
    body = bound.json()
    assert body["merged"] is True
    assert body["user"]["id"] == target_id

    with SessionLocal() as db:
        source = db.get(User, virtual_id)
        assert source is not None
        assert source.status == "merged"
        assert source.merged_into_id == target_id
        assert db.scalar(
            select(UserDailyStat).where(UserDailyStat.user_id == target_id)
        ) is not None

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {virtual_token}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["user"]["id"] == target_id


def test_public_flashcard_preview(client):
    response = client.get("/api/v1/flashcards/preview?limit=20")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload["cards"]) == 20
    assert payload["cards"][0]["term"]
    assert payload["cards"][0]["definition"]
    assert payload["cards"][0]["box"] == 0
    assert payload["cards"][0]["next_due_at"] is None
    assert payload["cards"][0]["ipa"]
    assert payload["cards"][0]["audio_url"]
    audio = client.get(payload["cards"][0]["audio_url"])
    assert audio.status_code == 200
    assert audio.headers["content-type"].startswith("audio/")


def test_content_payload_encryption(client):
    import base64
    import json
    from urllib.parse import urlparse

    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    login(client)
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_raw = private_key.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    response = client.get(
        "/api/v1/papers",
        headers={"X-Content-Pubkey": base64.b64encode(public_raw).decode("ascii")},
    )
    assert response.status_code == 200, response.text
    assert response.headers["x-content-encrypted"] == "1"
    envelope = response.json()
    assert envelope["alg"] == "ECDH-P256+HKDF-SHA256+AES-256-GCM"

    server_public = ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256R1(),
        base64.b64decode(envelope["server_public_key"]),
    )
    shared = private_key.exchange(ec.ECDH(), server_public)
    key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=base64.b64decode(envelope["salt"]),
        info=b"ap-content-v1",
    ).derive(shared)
    plaintext = AESGCM(key).decrypt(
        base64.b64decode(envelope["iv"]),
        base64.b64decode(envelope["ciphertext"]),
        b"ap-content-v1|GET|/api/v1/papers",
    )
    assert len(json.loads(plaintext)) == 14

    invalid = client.get(
        "/api/v1/papers",
        headers={"X-Content-Pubkey": "not-a-real-key"},
    )
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "CONTENT_KEY_INVALID"

    unsigned_asset = urlparse(
        client.app.state.store.asset_url("assets/psychology/images/2018/fig_q011.png")
    )
    assert unsigned_asset.query
    asset = client.get(f"{unsigned_asset.path}?{unsigned_asset.query}")
    assert asset.status_code == 200
    assert asset.headers["content-type"].startswith("image/")
    replacement = "0" if unsigned_asset.query[-1] != "0" else "1"
    tampered = client.get(
        f"{unsigned_asset.path}?{unsigned_asset.query[:-1]}{replacement}"
    )
    assert tampered.status_code == 403


def test_rate_limiter_sliding_window():
    from app.core.rate_limit import limiter

    limiter.reset()
    for _ in range(3):
        allowed, _ = limiter.allow("unit-test", 3, 60)
        assert allowed
    allowed, retry_after = limiter.allow("unit-test", 3, 60)
    assert not allowed
    assert retry_after > 0
    limiter.reset()


def test_auth_me_logout(client):
    assert client.get("/api/v1/me").status_code == 401
    login(client)
    me = client.get("/api/v1/me")
    assert me.status_code == 200
    assert "***@example.com" in me.json()["user"]["email_masked"]
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/me").status_code == 401


def test_subject_active_release_resolution(tmp_path, monkeypatch):
    import json
    from pathlib import Path

    from app.core import config as config_module

    monkeypatch.setattr(config_module, "REPO_ROOT", tmp_path)
    releases = tmp_path / "data" / "releases"
    active = releases / "active"
    active.mkdir(parents=True)
    for subject_id in ("psychology", "statistics"):
        release_id = f"{subject_id}-20261029-001"
        release_dir = releases / release_id
        release_dir.mkdir()
        (release_dir / "release.json").write_text(
            json.dumps(
                {
                    "release_id": release_id,
                    "subject_id": subject_id,
                    "counts": {},
                }
            ),
            encoding="utf-8",
        )
        (active / subject_id).symlink_to(Path("..") / release_id, target_is_directory=True)

    settings = config_module.Settings(content_dir=None)
    assert (
        settings.resolve_content_dir("psychology").resolve()
        == (releases / "psychology-20261029-001").resolve()
    )
    assert (
        settings.resolve_content_dir("statistics").resolve()
        == (releases / "statistics-20261029-001").resolve()
    )


def test_merged_active_release_resolution(tmp_path, monkeypatch):
    import json
    from pathlib import Path

    from app.core import config as config_module

    monkeypatch.setattr(config_module, "REPO_ROOT", tmp_path)
    releases = tmp_path / "data" / "releases"
    release_id = "content-20261030-01"
    release_dir = releases / release_id
    release_dir.mkdir(parents=True)
    (release_dir / "release.json").write_text(
        json.dumps(
            {
                "release_id": release_id,
                "subjects": ["psychology", "statistics"],
                "counts": {},
            }
        ),
        encoding="utf-8",
    )
    (releases / "active").symlink_to(Path("..") / release_id, target_is_directory=True)

    settings = config_module.Settings(content_dir=None)
    assert settings.resolve_content_dir("psychology").resolve() == release_dir.resolve()
    assert settings.resolve_content_dir("statistics").resolve() == release_dir.resolve()


def test_subjects_endpoint_uses_merged_manifest(client, tmp_path, monkeypatch):
    import json

    from app.api.v1 import content as content_api

    repo = tmp_path / "repo"
    releases = repo / "data" / "releases"
    release_dir = releases / "content-20261030-01"
    (release_dir / "assets" / "psychology").mkdir(parents=True)
    (release_dir / "exam.db").write_bytes(b"")
    (release_dir / "release.json").write_text(
        json.dumps(
            {
                "release_id": "content-20261030-01",
                "subjects": ["psychology", "statistics"],
            }
        ),
        encoding="utf-8",
    )
    (releases / "active").symlink_to("content-20261030-01", target_is_directory=True)
    monkeypatch.setattr(content_api, "REPO_ROOT", repo)

    response = client.get("/api/v1/subjects")
    assert response.status_code == 200, response.text
    assert [item["subject_id"] for item in response.json()] == ["psychology", "statistics"]


def test_admin_auth_and_read_views(client):
    from app.core.db import SessionLocal
    from app.core.security import hash_password
    from app.users.models import AdminUser

    with SessionLocal() as db:
        admin = AdminUser(
            username="admin_test",
            email="admin_test@example.com",
            password_hash=hash_password("StrongPass123!"),
            role="super_admin",
            status="active",
        )
        db.add(admin)
        db.commit()

    # A student session does not grant admin access.
    login(client)
    assert client.get("/api/v1/admin/auth/me").status_code == 401

    bad = client.post(
        "/api/v1/admin/auth/login",
        json={"identifier": "admin_test", "password": "wrong-password"},
    )
    assert bad.status_code == 401

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"identifier": "admin_test@example.com", "password": "StrongPass123!"},
    )
    assert login_response.status_code == 200, login_response.text
    assert login_response.json()["admin"]["role"] == "super_admin"
    assert login_response.json()["admin"]["can_edit_content"] is True
    me = client.get("/api/v1/admin/auth/me")
    assert me.status_code == 200
    assert me.json()["admin"]["username"] == "admin_test"

    dashboard = client.get("/api/v1/admin/dashboard")
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["release"]["release_id"]
    assert "stats" in dashboard.json()

    students = client.get("/api/v1/admin/students?limit=10")
    assert students.status_code == 200, students.text
    assert "students" in students.json()

    papers = client.get("/api/v1/admin/content/papers")
    assert papers.status_code == 200, papers.text
    assert papers.json()["papers"]
    paper = next(
        item for item in papers.json()["papers"] if item["paper_id"] == "psychology-ap-2025"
    )
    assert paper["config"]["mcq_count"] == 75

    paper_detail = client.get("/api/v1/admin/content/papers/psychology-ap-2025")
    assert paper_detail.status_code == 200, paper_detail.text
    assert len(paper_detail.json()["questions"]) == 79

    bundle = next(
        item
        for item in papers.json()["papers"]
        if item["paper_id"] == "psychology-unit1-practice-bundle"
    )
    assert bundle["actual_questions"] == 345
    assert bundle["mcq_count"] == 345
    bundle_detail = client.get(
        "/api/v1/admin/content/papers/psychology-unit1-practice-bundle"
    )
    assert bundle_detail.status_code == 200, bundle_detail.text
    bundle_questions = bundle_detail.json()["questions"]
    assert len(bundle_questions) == 345
    assert any(item.get("source_paper_id") for item in bundle_questions)
    practice = bundle_detail.json()["practice"]
    assert practice["mapped"] == 345
    assert practice["usable"] == 342
    assert practice["excluded"] == 3

    subject_list = client.get("/api/v1/admin/subjects?include_disabled=true")
    assert subject_list.status_code == 200, subject_list.text
    subject_items = {
        item["subject_id"]: item for item in subject_list.json()["subjects"]
    }
    assert subject_items["psychology"]["enabled"] is True
    assert subject_items["statistics"]["enabled"] is False

    concepts = client.get("/api/v1/admin/content/knowledge/concepts?limit=5")
    assert concepts.status_code == 200, concepts.text
    assert len(concepts.json()["concepts"]) == 5
    assert concepts.json()["total"] >= 5
    concept_page_1 = client.get(
        "/api/v1/admin/content/knowledge/concepts?limit=2&offset=0"
    ).json()
    concept_page_2 = client.get(
        "/api/v1/admin/content/knowledge/concepts?limit=2&offset=2"
    ).json()
    assert len(concept_page_1["concepts"]) == 2
    assert len(concept_page_2["concepts"]) == 2
    assert concept_page_1["total"] == concept_page_2["total"]
    assert {
        item["cluster_id"] for item in concept_page_1["concepts"]
    }.isdisjoint({item["cluster_id"] for item in concept_page_2["concepts"]})
    search_name = concept_page_1["concepts"][0]["canonical_name"]
    name_only = client.get(
        "/api/v1/admin/content/knowledge/concepts",
        params={"q": search_name, "limit": 50},
    ).json()
    assert all(
        search_name.lower() in item["canonical_name"].lower()
        for item in name_only["concepts"]
    )
    kps = client.get("/api/v1/admin/content/knowledge/kps?limit=5")
    assert kps.status_code == 200, kps.text
    assert len(kps.json()["kps"]) == 5
    assert kps.json()["total"] >= 5

    releases = client.get("/api/v1/admin/releases")
    assert releases.status_code == 200, releases.text
    assert releases.json()["releases"]

    logout = client.post("/api/v1/admin/auth/logout")
    assert logout.status_code == 200
    assert client.get("/api/v1/admin/auth/me").status_code == 401


def test_admin_content_edits_and_creation_overlay(client):
    """Admin edits are app-side overlays, marked and materialized for reads."""
    import shutil
    import uuid as uuid_module

    from app.core.db import SessionLocal
    from app.core.security import hash_password
    from app.services.effective_content import ensure_effective_content
    from app.users.models import (
        AdminContentRecord,
        AdminContentRevision,
        AdminUser,
    )
    from tests.conftest import TEST_EFFECTIVE

    username = f"admin_overlay_{uuid_module.uuid4().hex[:8]}"
    with SessionLocal() as db:
        db.add(
            AdminUser(
                username=username,
                email=f"{username}@example.com",
                password_hash=hash_password("StrongPass123!"),
                role="content_editor",
                status="active",
            )
        )
        db.commit()

    response = client.post(
        "/api/v1/admin/auth/login",
        json={"identifier": username, "password": "StrongPass123!"},
    )
    assert response.status_code == 200, response.text
    try:
        paper = client.get("/api/v1/admin/content/papers/psychology-ap-2025")
        assert paper.status_code == 200, paper.text
        question = paper.json()["questions"][0]
        detail = client.get(
            f"/api/v1/admin/content/questions/{question['question_id']}"
        )
        assert detail.status_code == 200, detail.text
        original_title = paper.json()["title"]

        title = f"Admin Edited Paper {uuid_module.uuid4().hex[:6]}"
        patched_paper = client.patch(
            "/api/v1/admin/content/papers/psychology-ap-2025",
            json={"title": title},
        )
        assert patched_paper.status_code == 200, patched_paper.text
        assert patched_paper.json()["title"] == title
        assert patched_paper.json()["admin_origin"] == "admin_edited"

        # Student reads use the same effective content materialization.
        from tests.conftest import login as student_login

        student_login(client)
        student_paper = client.get("/api/v1/papers/psychology-ap-2025")
        assert student_paper.status_code == 200, student_paper.text
        assert student_paper.json()["title"] == title

        patched_question = client.patch(
            f"/api/v1/admin/content/questions/{question['question_id']}",
            json={
                "stem": "Admin edited stem",
                "context": detail.json()["context"] or "",
                "options": [
                    {
                        "label": option["label"],
                        "content": option["content"],
                        "is_correct": bool(option["is_correct"]),
                        "explanation": option["explanation"],
                        "ai_explanation": option["ai_explanation"],
                    }
                    for option in detail.json()["options"]
                ],
            },
        )
        assert patched_question.status_code == 200, patched_question.text
        assert patched_question.json()["stem"] == "Admin edited stem"
        assert patched_question.json()["admin_origin"] == "admin_edited"

        concepts = client.get("/api/v1/admin/content/knowledge/concepts?limit=5")
        assert concepts.status_code == 200, concepts.text
        concept = concepts.json()["concepts"][0]
        patched_concept = client.patch(
            f"/api/v1/admin/content/knowledge/concepts/{concept['cluster_id']}",
            json={"description": "Admin edited concept description"},
        )
        assert patched_concept.status_code == 200, patched_concept.text
        assert patched_concept.json()["admin_origin"] == "admin_edited"

        kps = client.get("/api/v1/admin/content/knowledge/kps?limit=5")
        assert kps.status_code == 200, kps.text
        kp = kps.json()["kps"][0]
        patched_kp = client.patch(
            f"/api/v1/admin/content/knowledge/kps/{kp['kp_id']}",
            json={"plain_en": "Admin edited KP definition"},
        )
        assert patched_kp.status_code == 200, patched_kp.text
        assert patched_kp.json()["admin_origin"] == "admin_edited"

        name = f"Admin Smoke Concept {uuid_module.uuid4().hex[:6]}"
        created_concept = client.post(
            "/api/v1/admin/content/knowledge/concepts",
            json={
                "canonical_name": name,
                "definition": "A concept created by an administrator.",
                "ap_unit": "1",
                "topic": "1.1",
            },
        )
        assert created_concept.status_code == 200, created_concept.text
        created_concept_payload = created_concept.json()
        assert created_concept_payload["cluster_id"].startswith("psy-admin-c-")
        assert created_concept_payload["admin_origin"] == "admin_created"

        created_question = client.post(
            "/api/v1/admin/content/questions",
            json={
                "paper_id": "psychology-barrons-2027-ch6-review",
                "section": "MCQ",
                "stem": "Admin-created question stem?",
                "context": "",
                "options": [
                    {"label": "A", "content": "First", "is_correct": True},
                    {"label": "B", "content": "Second", "is_correct": False},
                    {"label": "C", "content": "Third", "is_correct": False},
                    {"label": "D", "content": "Fourth", "is_correct": False},
                ],
            },
        )
        assert created_question.status_code == 200, created_question.text
        created_question_payload = created_question.json()
        assert created_question_payload["question_id"].startswith("psy-admin-q-")
        assert created_question_payload["admin_origin"] == "admin_created"
        created_paper = client.get(
            "/api/v1/admin/content/papers/psychology-barrons-2027-ch6-review"
        )
        assert created_paper.status_code == 200, created_paper.text
        assert any(
            item["question_id"] == created_question_payload["question_id"]
            for item in created_paper.json()["questions"]
        )

        linked = client.post(
            f"/api/v1/admin/content/questions/{created_question_payload['question_id']}/concepts",
            json={
                "concept_id": created_concept_payload["cluster_id"],
                "relation_type": "core",
            },
        )
        assert linked.status_code == 200, linked.text
        linked_concepts = linked.json()["concepts"]
        assert any(
            item["concept_id"] == created_concept_payload["cluster_id"]
            and item["admin_origin"] == "admin_created"
            for item in linked_concepts
        )

        # The materialized content is what ContentStore sees.
        with SessionLocal() as db:
            effective = ensure_effective_content(
                db, force_marker_columns=True
            )
        assert (effective / "exam.db").exists()
    finally:
        with SessionLocal() as db:
            db.query(AdminContentRecord).delete()
            db.query(AdminContentRevision).delete()
            db.commit()
        shutil.rmtree(TEST_EFFECTIVE, ignore_errors=True)
        with SessionLocal() as db:
            # Recreate no content pointer; the next request uses the Release.
            ensure_effective_content(db, force_marker_columns=False)
        # The paper title is tested nowhere else, but restore it in the overlay
        # is unnecessary after the records are deleted.
        assert original_title is not None


def test_admin_release_archive_and_restore(client, tmp_path, monkeypatch):
    import json
    from pathlib import Path

    from app.api.v1 import admin as admin_api
    from app.core.db import SessionLocal
    from app.core.security import hash_password
    from app.users.models import AdminUser

    repo = tmp_path / "repo"
    releases = repo / "data" / "releases"
    release_id = "psychology-test-archive"
    release_dir = releases / release_id
    release_dir.mkdir(parents=True)
    (release_dir / "release.json").write_text(
        json.dumps(
            {
                "release_id": release_id,
                "created_at": "2026-01-01T00:00:00+08:00",
                "counts": {"questions": 1},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(admin_api, "REPO_ROOT", repo)
    monkeypatch.setattr(admin_api, "Path", Path)

    with SessionLocal() as db:
        db.add(
            AdminUser(
                username="admin_archive_test",
                email="admin_archive_test@example.com",
                password_hash=hash_password("StrongPass123!"),
                role="super_admin",
                status="active",
            )
        )
        db.commit()

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"identifier": "admin_archive_test", "password": "StrongPass123!"},
    )
    assert login_response.status_code == 200, login_response.text

    archived = client.post(f"/api/v1/admin/releases/{release_id}/archive")
    assert archived.status_code == 200, archived.text
    assert not (releases / release_id).exists()
    assert (releases / ".archive" / release_id / "release.json").exists()

    listing = client.get("/api/v1/admin/releases")
    assert listing.status_code == 200, listing.text
    assert any(item["release_id"] == release_id for item in listing.json()["archived"])
    assert not any(item["release_id"] == release_id for item in listing.json()["releases"])

    restored = client.post(f"/api/v1/admin/releases/{release_id}/restore")
    assert restored.status_code == 200, restored.text
    assert (releases / release_id / "release.json").exists()
    after = client.get("/api/v1/admin/releases")
    assert any(item["release_id"] == release_id for item in after.json()["releases"])


def test_admin_activate_merged_release(client, tmp_path, monkeypatch):
    import json
    from pathlib import Path
    from types import SimpleNamespace

    from app.api.v1 import admin as admin_api
    from app.core.db import SessionLocal
    from app.core.security import hash_password
    from app.users.models import AdminUser, ContentRelease

    repo = tmp_path / "repo"
    releases = repo / "data" / "releases"
    release_id = "content-20261030-99"
    release_dir = releases / release_id
    release_dir.mkdir(parents=True)
    (release_dir / "release.json").write_text(
        json.dumps(
            {
                "release_id": release_id,
                "subjects": ["psychology", "statistics"],
                "counts": {"questions": 2},
                "counts_by_subject": {
                    "psychology": {"questions": 1},
                    "statistics": {"questions": 1},
                },
            }
        ),
        encoding="utf-8",
    )

    old_id = "psychology-old"
    old_dir = releases / old_id
    old_dir.mkdir()
    (old_dir / "release.json").write_text(
        json.dumps({"release_id": old_id, "subject_id": "psychology"}),
        encoding="utf-8",
    )
    legacy_active = releases / "active"
    legacy_active.mkdir()
    (legacy_active / "psychology").symlink_to(Path("..") / old_id, target_is_directory=True)

    monkeypatch.setattr(admin_api, "REPO_ROOT", repo)
    monkeypatch.setattr(
        admin_api,
        "_reload_store_for_subject",
        lambda request, subject_id: SimpleNamespace(release_id=release_id),
    )

    with SessionLocal() as db:
        db.add(
            AdminUser(
                username="admin_activate_test",
                email="admin_activate_test@example.com",
                password_hash=hash_password("StrongPass123!"),
                role="super_admin",
                status="active",
            )
        )
        db.commit()

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"identifier": "admin_activate_test", "password": "StrongPass123!"},
    )
    assert login_response.status_code == 200, login_response.text

    response = client.post(f"/api/v1/admin/releases/{release_id}/activate")
    assert response.status_code == 200, response.text
    assert response.json()["subjects"] == ["psychology", "statistics"]
    assert (releases / "active").is_symlink()
    assert (releases / "active").resolve() == release_dir.resolve()
    assert (releases / "current").resolve() == release_dir.resolve()

    listing = client.get("/api/v1/admin/releases")
    assert listing.status_code == 200, listing.text
    ids = [item["release_id"] for item in listing.json()["releases"]]
    assert ids.count(release_id) == 1
    assert listing.json()["active_release_id"] == release_id

    with SessionLocal() as db:
        row = db.get(ContentRelease, ("statistics", release_id))
        assert row is not None
        assert row.status == "active"
        assert row.counts_json == {"questions": 1}


def test_student_nickname_can_be_set_and_duplicated(client):
    login(client)
    first = client.patch("/api/v1/me", json={"nickname": "  Alex  "})
    assert first.status_code == 200, first.text
    assert first.json()["user"]["nickname"] == "Alex"

    login(client)
    second = client.patch("/api/v1/me", json={"nickname": "Alex"})
    assert second.status_code == 200, second.text
    assert second.json()["user"]["nickname"] == "Alex"

    empty = client.patch("/api/v1/me", json={"nickname": "   "})
    assert empty.status_code == 400

    me = client.get("/api/v1/me").json()
    assert me["user"]["nickname"] == "Alex"


def test_practice_flow(client):
    login(client)
    groups = client.get("/api/v1/practice-groups").json()
    assert groups[0]["title_en"]
    group = groups[0]
    topics = client.get(f"/api/v1/practice-groups/{group['group_id']}/topics").json()
    assert topics
    topic = next(t for t in topics if t["topic_id"].endswith(":1.1"))
    assert topic["question_count"] == 14

    session = client.post(
        "/api/v1/practice-sessions",
        json={"source": "topic", "topic_id": topic["topic_id"], "count": 5},
    )
    assert session.status_code == 200, session.text
    payload = session.json()
    # Topic practice keeps the whole chapter instead of a random 5/20/50 slice.
    assert len(payload["questions"]) == 14
    assert payload["session"]["next_index"] == 0
    q = payload["questions"][0]
    assert q["display_number"] == 1

    answer = client.post(
        f"/api/v1/practice-sessions/{payload['session']['id']}/answers",
        json={"question_id": q["question_id"], "selected_label": q["options"][0]["label"]},
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert "feedback" in body
    assert body["feedback"]["explanation"] is not None

    resumed = client.get(f"/api/v1/practice-sessions/{payload['session']['id']}").json()
    assert resumed["progress"]["answered"] == 1
    assert resumed["session"]["next_index"] == 1

    # The same chapter returns the same in-progress record.
    same = client.post(
        "/api/v1/practice-sessions",
        json={"source": "topic", "topic_id": topic["topic_id"]},
    ).json()
    assert same["session"]["id"] == payload["session"]["id"]

    # Restart abandons the old record and starts from question 1 again.
    restarted = client.post(
        "/api/v1/practice-sessions",
        json={"source": "topic", "topic_id": topic["topic_id"], "restart": True},
    ).json()
    assert restarted["session"]["id"] != payload["session"]["id"]
    assert restarted["session"]["next_index"] == 0
    old = client.get(f"/api/v1/practice-sessions/{payload['session']['id']}").json()
    assert old["session"]["status"] == "abandoned"

    # Answering the final question auto-completes the chapter; no submit step.
    final_answer = None
    for question in restarted["questions"]:
        final_answer = client.post(
            f"/api/v1/practice-sessions/{restarted['session']['id']}/answers",
            json={
                "question_id": question["question_id"],
                "selected_label": question["options"][0]["label"],
            },
        )
        assert final_answer.status_code == 200, final_answer.text
    assert final_answer is not None
    assert final_answer.json()["completed"] is True
    finished = client.get(f"/api/v1/practice-sessions/{restarted['session']['id']}").json()
    assert finished["session"]["status"] == "submitted"
    assert finished["progress"]["answered"] == 14

    dashboard = client.get("/api/v1/me/dashboard").json()
    assert dashboard["overview"]["total_questions"] > 0
    assert len(dashboard["activity"]) == 365
    assert dashboard["activity"][-1]["answered"] >= 1
    assert dashboard["activity_summary"]["active_days"] >= 1
    wrong = client.get("/api/v1/me/wrong-questions").json()
    assert isinstance(wrong, list)


def test_practice_history_and_wrong_detail(client):
    login(client)
    groups = client.get("/api/v1/practice-groups").json()
    topics = client.get(f"/api/v1/practice-groups/{groups[0]['group_id']}/topics").json()
    topic = next(t for t in topics if t["topic_id"].endswith(":1.1"))
    payload = client.post(
        "/api/v1/practice-sessions",
        json={"source": "topic", "topic_id": topic["topic_id"]},
    ).json()
    session_id = payload["session"]["id"]

    wrong_qid = None
    for question in payload["questions"]:
        answer = client.post(
            f"/api/v1/practice-sessions/{session_id}/answers",
            json={
                "question_id": question["question_id"],
                "selected_label": question["options"][0]["label"],
            },
        ).json()
        if not answer["is_correct"]:
            wrong_qid = question["question_id"]
            break
    assert wrong_qid is not None

    history = client.get("/api/v1/me/practice-sessions?limit=10").json()
    assert history[0]["id"] == session_id
    assert history[0]["topic_title_en"]
    assert history[0]["answered"] >= 1

    detail = client.get(f"/api/v1/me/wrong-questions/{wrong_qid}")
    assert detail.status_code == 200, detail.text
    data = detail.json()
    assert data["question"]["question_id"] == wrong_qid
    assert data["question"]["options"]
    assert any(o.get("is_correct") for o in data["question"]["options"])
    assert "concepts" in data["question"]
    generic = client.get(f"/api/v1/me/questions/{wrong_qid}")
    assert generic.status_code == 200, generic.text
    assert generic.json()["options"]
    summary = client.get("/api/v1/me/wrong-questions/summary").json()
    assert summary["all"] >= 1
    assert summary["learning"] >= 1

    wrong_items = client.get("/api/v1/me/wrong-questions?limit=200").json()
    wrong_item = next(item for item in wrong_items if item["question_id"] == wrong_qid)
    assert wrong_item["unit_id"] == "1"
    assert wrong_item["topic_code"] == "1.1"
    assert wrong_item["topic_title_en"]

    client.post(
        "/api/v1/me/notes",
        json={
            "target_type": "question",
            "target_id": wrong_qid,
            "content": "来源信息测试",
        },
    )
    notes = client.get("/api/v1/me/notes?limit=200").json()
    note_item = next(item for item in notes if item["target_id"] == wrong_qid)
    assert note_item["question"]["unit_id"] == "1"
    assert note_item["question"]["topic_code"] == "1.1"
    assert note_item["question"]["topic_title_en"]

    wrong_session = client.post("/api/v1/practice-sessions", json={"source": "wrong", "count": 20})
    assert wrong_session.status_code == 200, wrong_session.text
    wrong_payload = wrong_session.json()
    assert wrong_payload["session"]["source"] == "wrong"
    assert wrong_payload["session"]["group_id"] is None
    assert wrong_qid in [q["question_id"] for q in wrong_payload["questions"]]

    # Wrong practice mixes units, so Topic Concepts must follow the current
    # question instead of relying on a session-level topic.
    topic_context = client.get(
        f"/api/v1/practice-sessions/{wrong_payload['session']['id']}/questions/{wrong_qid}/topic-concepts"
    )
    assert topic_context.status_code == 200, topic_context.text
    topic_context_payload = topic_context.json()
    assert topic_context_payload["topic"]["topic_id"].endswith(":1.1")
    assert topic_context_payload["concepts"]

    correct_label = next(o["label"] for o in data["question"]["options"] if o.get("is_correct"))
    first_correct = client.post(
        f"/api/v1/practice-sessions/{wrong_payload['session']['id']}/answers",
        json={"question_id": wrong_qid, "selected_label": correct_label},
    )
    assert first_correct.status_code == 200
    after_one = client.get("/api/v1/me/wrong-questions?limit=200").json()
    mastered = next(item for item in after_one if item["question_id"] == wrong_qid)
    assert mastered["mastery"] == "reviewing"
    assert mastered["correct_streak"] == 1

    second_session = client.post(
        "/api/v1/practice-sessions",
        json={"source": "wrong", "restart": True},
    ).json()
    second_correct = client.post(
        f"/api/v1/practice-sessions/{second_session['session']['id']}/answers",
        json={"question_id": wrong_qid, "selected_label": correct_label},
    )
    assert second_correct.status_code == 200
    after_two = client.get("/api/v1/me/wrong-questions?limit=200").json()
    mastered = next(item for item in after_two if item["question_id"] == wrong_qid)
    assert mastered["mastery"] == "mastered"
    assert mastered["correct_streak"] >= 2


def test_exam_resume_restart_and_abandoned_review(client):
    login(client)
    created = client.post(
        "/api/v1/attempts", json={"paper_id": "psychology-ap-2025", "mode": "mcq"}
    )
    assert created.status_code == 200, created.text
    state = created.json()
    attempt_id = state["attempt"]["id"]

    paper = client.get("/api/v1/papers/psychology-ap-2025").json()
    assert len(paper["active_attempts"]) == 1
    assert paper["active_attempts"][0]["id"] == attempt_id
    assert paper["active_attempts"][0]["mode"] == "mcq"

    same = client.post(
        "/api/v1/attempts", json={"paper_id": "psychology-ap-2025", "mode": "mcq"}
    ).json()
    assert same["attempt"]["id"] == attempt_id

    restarted = client.post(
        "/api/v1/attempts",
        json={"paper_id": "psychology-ap-2025", "mode": "mcq", "restart": True},
    )
    assert restarted.status_code == 200, restarted.text
    new_id = restarted.json()["attempt"]["id"]
    assert new_id != attempt_id
    old = client.get(f"/api/v1/attempts/{attempt_id}").json()
    assert old["attempt"]["status"] == "abandoned"

    abandoned = client.post(f"/api/v1/attempts/{new_id}/abandon")
    assert abandoned.status_code == 200
    review = client.get(f"/api/v1/attempts/{new_id}/review")
    assert review.status_code == 200, review.text
    data = review.json()
    assert data["attempt"]["status"] == "abandoned"
    assert len(data["mcq_items"]) == 75

    history = client.get("/api/v1/me/attempts?limit=10").json()
    assert history[0]["paper_title"] is not None
    assert history[0]["status"] == "abandoned"


def test_wrong_paper_is_dynamic(client):
    login(client)
    groups = client.get("/api/v1/practice-groups").json()
    topics = client.get(f"/api/v1/practice-groups/{groups[0]['group_id']}/topics").json()
    topic = next(t for t in topics if t["topic_id"].endswith(":1.1"))
    payload = client.post(
        "/api/v1/practice-sessions",
        json={"source": "topic", "topic_id": topic["topic_id"]},
    ).json()
    topic_session_id = payload["session"]["id"]

    wrong_ids: list[str] = []
    answered: set[str] = set()
    for question in payload["questions"]:
        if len(wrong_ids) >= 2:
            break
        answered.add(question["question_id"])
        answer = client.post(
            f"/api/v1/practice-sessions/{topic_session_id}/answers",
            json={
                "question_id": question["question_id"],
                "selected_label": question["options"][0]["label"],
            },
        ).json()
        if not answer["is_correct"]:
            wrong_ids.append(question["question_id"])
    assert len(wrong_ids) == 2

    paper = client.post("/api/v1/practice-sessions", json={"source": "wrong"}).json()
    paper_id = paper["session"]["id"]
    assert len(paper["questions"]) == 2

    # A new wrong question appears in the live paper.
    for question in payload["questions"]:
        if question["question_id"] in answered:
            continue
        answered.add(question["question_id"])
        answer = client.post(
            f"/api/v1/practice-sessions/{topic_session_id}/answers",
            json={
                "question_id": question["question_id"],
                "selected_label": question["options"][0]["label"],
            },
        ).json()
        if not answer["is_correct"]:
            wrong_ids.append(question["question_id"])
            break
    assert len(wrong_ids) == 3

    after_add = client.get(f"/api/v1/practice-sessions/{paper_id}").json()
    assert len(after_add["questions"]) == 3
    assert wrong_ids[2] in {q["question_id"] for q in after_add["questions"]}

    # Marking one as mastered removes it from the live paper.
    mastered = client.post(f"/api/v1/me/wrong-questions/{wrong_ids[0]}/master")
    assert mastered.status_code == 200
    after_master = client.get(f"/api/v1/practice-sessions/{paper_id}").json()
    assert len(after_master["questions"]) == 2
    assert wrong_ids[0] not in {q["question_id"] for q in after_master["questions"]}

    # Unmastering adds it back.
    unmastered = client.post(f"/api/v1/me/wrong-questions/{wrong_ids[0]}/unmaster")
    assert unmastered.status_code == 200
    assert unmastered.json()["mastery"] == "learning"
    after_unmaster = client.get(f"/api/v1/practice-sessions/{paper_id}").json()
    assert len(after_unmaster["questions"]) == 3
    assert wrong_ids[0] in {q["question_id"] for q in after_unmaster["questions"]}

    summary = client.get("/api/v1/me/wrong-questions/summary").json()
    assert summary["active"] == 3
    assert summary["mastered"] == 0


def test_flashcards(client):
    login(client)
    deck = client.get("/api/v1/flashcards?unit_id=1&limit=5")
    assert deck.status_code == 200, deck.text
    data = deck.json()
    assert len(data["cards"]) == 5
    card = data["cards"][0]
    assert card["term"]
    assert card["definition"] or card["quote"]
    assert card["weight"] > 0
    assert 1 <= card["stars"] <= 5

    review = client.post(
        f"/api/v1/flashcards/{card['concept_id']}/review", json={"rating": "known"}
    )
    assert review.status_code == 200, review.text
    result = review.json()
    assert result["box"] == 0
    assert result["seen_count"] == 1
    assert result["next_due_at"]

    today = client.get("/api/v1/flashcards?scope=today&limit=50")
    assert today.status_code == 200, today.text
    today_data = today.json()
    assert today_data["scope"] == "today"
    assert card["concept_id"] in {item["concept_id"] for item in today_data["cards"]}

    again = client.post(f"/api/v1/flashcards/{card['concept_id']}/review", json={"rating": "again"})
    assert again.status_code == 200
    assert again.json()["box"] == 0

    relearn = client.post(
        f"/api/v1/flashcards/{card['concept_id']}/review", json={"rating": "known"}
    )
    assert relearn.status_code == 200
    assert relearn.json()["box"] == 1

    high = client.get("/api/v1/flashcards?min_stars=5&limit=5")
    assert high.status_code == 200, high.text
    high_data = high.json()
    assert high_data["cards"]
    assert all(item["stars"] == 5 for item in high_data["cards"])


def test_flashcard_continuous_queue(client):
    login(client)
    first = client.get("/api/v1/flashcards/next")
    assert first.status_code == 200, first.text
    data = first.json()
    assert data["reason"] == "new"
    assert data["new_today"] == 0
    assert data["new_remaining"] == data["new_limit"]
    assert data["card"] is not None
    card_id = data["card"]["concept_id"]

    reviewed = client.post(f"/api/v1/flashcards/{card_id}/review", json={"rating": "known"})
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["box"] == 0

    second = client.get("/api/v1/flashcards/next")
    assert second.status_code == 200, second.text
    next_data = second.json()
    assert next_data["new_today"] == 1
    assert next_data["new_remaining"] == next_data["new_limit"] - 1
    assert next_data["reason"] == "new"
    assert next_data["card"]["concept_id"] != card_id


def test_email_register_returns_bearer_token(client):
    import secrets

    email = f"bearer-{secrets.randbelow(10**8)}@example.com"
    sent = client.post(
        "/api/v1/auth/email/code", json={"email": email, "purpose": "register"}
    )
    assert sent.status_code == 200, sent.text
    code = sent.json().get("debug_code") or "246810"
    registered = client.post(
        "/api/v1/auth/email/register",
        json={"email": email, "code": code, "password": "bearer-password-123"},
    )
    assert registered.status_code == 200, registered.text
    token = registered.json()["token"]
    assert token

    client.cookies.clear()
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    nxt = client.get(
        "/api/v1/flashcards/next",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert nxt.status_code == 200, nxt.text
    assert nxt.json()["card"] is not None


def test_flashcard_next_units_filter(client):
    login(client)
    one = client.get("/api/v1/flashcards/next?units=1")
    two = client.get("/api/v1/flashcards/next?units=2")
    both = client.get("/api/v1/flashcards/next?units=1,2")
    assert one.status_code == 200, one.text
    assert two.status_code == 200, two.text
    assert both.status_code == 200, both.text
    one_data, two_data, both_data = one.json(), two.json(), both.json()
    assert one_data["card"]["ap_unit"] == "1"
    assert two_data["card"]["ap_unit"] == "2"
    assert both_data["card"]["ap_unit"] in {"1", "2"}
    assert both_data["total"] == one_data["total"] + two_data["total"]

    methods = client.get("/api/v1/flashcards/next?units=methods")
    assert methods.status_code == 200, methods.text
    assert methods.json()["card"]["ap_unit"] in {"0", "EM"}


def test_flashcard_unfamiliar_list(client):
    phone = login(client)

    empty = client.get("/api/v1/flashcards/unfamiliar")
    assert empty.status_code == 200, empty.text
    assert empty.json()["total"] == 0
    assert empty.json()["cards"] == []

    deck = client.get("/api/v1/flashcards?unit_id=1&limit=3").json()["cards"]
    first, second = deck[0], deck[1]
    for card in (first, second):
        rated = client.post(
            f"/api/v1/flashcards/{card['concept_id']}/review",
            json={"rating": "again"},
        )
        assert rated.status_code == 200, rated.text

    listed = client.get("/api/v1/flashcards/unfamiliar?limit=10")
    assert listed.status_code == 200, listed.text
    payload = listed.json()
    assert payload["total"] == 2
    assert {card["concept_id"] for card in payload["cards"]} == {
        first["concept_id"],
        second["concept_id"],
    }
    assert all(card["last_rating"] == "again" for card in payload["cards"])
    assert all(card["term"] for card in payload["cards"])
    assert all(
        card["last_reviewed_at"].endswith("+00:00") for card in payload["cards"]
    )

    client.post(
        f"/api/v1/flashcards/{second['concept_id']}/review",
        json={"rating": "known"},
    )
    after_known = client.get("/api/v1/flashcards/unfamiliar?limit=10").json()
    assert after_known["total"] == 1
    assert after_known["cards"][0]["concept_id"] == first["concept_id"]

    client.post(
        f"/api/v1/flashcards/{first['concept_id']}/review",
        json={"rating": "known"},
    )
    assert client.get("/api/v1/flashcards/unfamiliar").json()["total"] == 0

    for card in (first, second):
        client.post(
            f"/api/v1/flashcards/{card['concept_id']}/review",
            json={"rating": "again"},
        )
    page_one = client.get("/api/v1/flashcards/unfamiliar?limit=1&offset=0").json()
    page_two = client.get("/api/v1/flashcards/unfamiliar?limit=1&offset=1").json()
    assert page_one["total"] == 2
    assert page_one["has_more"] is True
    assert page_two["total"] == 2
    assert page_two["has_more"] is False
    assert page_one["cards"][0]["concept_id"] != page_two["cards"][0]["concept_id"]

    from app.core.db import SessionLocal
    from app.core.time import utcnow
    from app.users.models import FlashcardReview, User

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.phone == phone))
        assert user is not None
        now = utcnow()
        db.add(
            FlashcardReview(
                user_id=user.id,
                concept_id="missing-concept",
                box=0,
                seen_count=1,
                known_count=0,
                last_rating="again",
                last_reviewed_at=now,
                next_due_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()

    assert client.get("/api/v1/flashcards/unfamiliar").json()["total"] == 2

    client.cookies.clear()
    assert client.get("/api/v1/flashcards/unfamiliar").status_code == 401


def test_custom_flashcards(client):
    login(client)
    user_id = client.get("/api/v1/me").json()["user"]["id"]

    created = client.post(
        "/api/v1/flashcards/custom",
        json={
            "term": "Spacing effect",
            "short_meaning": "Study spread over time is remembered better.",
            "detail_meaning": (
                "Distributed practice usually beats cramming for long-term retention."
            ),
        },
    )
    assert created.status_code == 200, created.text
    card = created.json()
    card_id = card["id"]
    assert card["term"] == "Spacing effect"
    assert card["short_meaning"].startswith("Study spread")
    assert card["detail_meaning"].startswith("Distributed practice")
    assert card["box"] == 0
    assert card["next_due_at"] is None

    listing = client.get("/api/v1/flashcards/custom")
    assert listing.status_code == 200, listing.text
    assert listing.json()["total"] == 1
    assert listing.json()["limit"] == 200
    assert listing.json()["cards"][0]["id"] == card_id

    next_card = client.get("/api/v1/flashcards/custom/next")
    assert next_card.status_code == 200, next_card.text
    next_data = next_card.json()
    assert next_data["reason"] == "new"
    assert next_data["card"]["concept_id"] == card_id

    deck = client.get("/api/v1/flashcards/custom/deck?limit=20")
    assert deck.status_code == 200, deck.text
    deck_data = deck.json()
    assert len(deck_data["cards"]) == 1
    deck_card = deck_data["cards"][0]
    assert deck_card["concept_id"] == card_id
    assert deck_card["definition"] == card["short_meaning"]
    assert deck_card["quote"] == card["detail_meaning"]
    assert deck_card["stars"] == 0
    assert deck_data["stats"]["new"] == 1

    known = client.post(f"/api/v1/flashcards/custom/{card_id}/review", json={"rating": "known"})
    assert known.status_code == 200, known.text
    assert known.json()["box"] == 0
    assert known.json()["seen_count"] == 1
    assert known.json()["next_due_at"]

    today = client.get("/api/v1/flashcards/custom/deck?scope=today&limit=50")
    assert today.status_code == 200, today.text
    today_data = today.json()
    assert today_data["scope"] == "today"
    assert card_id in {item["concept_id"] for item in today_data["cards"]}

    after_known = client.get("/api/v1/flashcards/custom/next")
    assert after_known.status_code == 200, after_known.text
    after_data = after_known.json()
    assert after_data["reviewed_today"] == 1
    assert after_data["caught_up"] is True

    again = client.post(f"/api/v1/flashcards/custom/{card_id}/review", json={"rating": "again"})
    assert again.status_code == 200
    assert again.json()["box"] == 0

    known_again = client.post(
        f"/api/v1/flashcards/custom/{card_id}/review", json={"rating": "known"}
    )
    assert known_again.status_code == 200
    assert known_again.json()["box"] == 1

    patched = client.patch(
        f"/api/v1/flashcards/custom/{card_id}",
        json={
            "term": "Spacing effect (edited)",
            "short_meaning": "Spaced study helps memory.",
            "detail_meaning": "Edited detail.",
        },
    )
    assert patched.status_code == 200, patched.text
    patched_card = patched.json()
    assert patched_card["term"] == "Spacing effect (edited)"
    assert patched_card["box"] == 1
    assert patched_card["seen_count"] == 3

    second = client.post(
        "/api/v1/flashcards/custom",
        json={
            "term": "Temporary card",
            "short_meaning": "Delete me.",
            "detail_meaning": "",
        },
    ).json()
    deleted = client.delete(f"/api/v1/flashcards/custom/{second['id']}")
    assert deleted.status_code == 200, deleted.text
    after_delete = client.get("/api/v1/flashcards/custom").json()
    assert after_delete["total"] == 1
    assert all(item["id"] != second["id"] for item in after_delete["cards"])

    # The per-user limit is enforced before insert.
    from app.core.db import SessionLocal
    from app.users.models import UserFlashcard

    with SessionLocal() as db:
        db.add_all(
            UserFlashcard(
                user_id=user_id,
                term=f"Bulk card {index}",
                short_meaning="Bulk short meaning",
                detail_meaning="",
            )
            for index in range(199)
        )
        db.commit()
    limited = client.post(
        "/api/v1/flashcards/custom",
        json={"term": "Over limit", "short_meaning": "No", "detail_meaning": ""},
    )
    assert limited.status_code == 409
    assert limited.json()["code"] == "FLASHCARD_LIMIT"

    # Another user cannot read or mutate this user's card.
    login(client)
    hidden_list = client.get("/api/v1/flashcards/custom").json()
    assert hidden_list["total"] == 0
    other_patch = client.patch(
        f"/api/v1/flashcards/custom/{card_id}",
        json={"term": "Hijacked"},
    )
    assert other_patch.status_code == 404
    other_review = client.post(
        f"/api/v1/flashcards/custom/{card_id}/review", json={"rating": "known"}
    )
    assert other_review.status_code == 404
    other_delete = client.delete(f"/api/v1/flashcards/custom/{card_id}")
    assert other_delete.status_code == 404


def collect_keys(value):
    keys = set()
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str):
                keys.add(k)
            keys |= collect_keys(v)
    elif isinstance(value, list):
        for item in value:
            keys |= collect_keys(item)
    return keys


def test_mcq_exam_flow(client):
    login(client)
    created = client.post(
        "/api/v1/attempts", json={"paper_id": "psychology-ap-2025", "mode": "mcq"}
    )
    assert created.status_code == 200, created.text
    state = created.json()
    assert len(state["questions"]) == 75
    forbidden = {
        "is_correct",
        "explanation",
        "ai_explanation",
        "concepts",
        "rubric",
        "answer_text",
        "correct_label",
        "guidelines",
    }
    assert not (collect_keys(state) & forbidden)
    q = state["questions"][0]
    client.post(
        "/api/v1/me/notes",
        json={
            "target_type": "question",
            "target_id": q["question_id"],
            "content": "考试中不应能看到解析",
        },
    )
    locked = client.get(f"/api/v1/me/questions/{q['question_id']}")
    assert locked.status_code == 409, locked.text
    saved = client.patch(
        f"/api/v1/attempts/{state['attempt']['id']}/answers",
        json={
            "answers": [
                {"question_id": q["question_id"], "selected_label": q["options"][0]["label"]}
            ]
        },
    )
    assert saved.status_code == 200
    # Saving an answer must not grade it or touch the wrong book yet.
    wrong_before = client.get("/api/v1/me/wrong-questions?limit=200").json()
    assert all(item["question_id"] != q["question_id"] for item in wrong_before)
    submitted = client.post(f"/api/v1/attempts/{state['attempt']['id']}/sections/mcq/submit")
    assert submitted.status_code == 200
    unlocked = client.get(f"/api/v1/me/questions/{q['question_id']}")
    assert unlocked.status_code == 200, unlocked.text
    assert unlocked.json()["options"]
    review = client.get(f"/api/v1/attempts/{state['attempt']['id']}/review")
    assert review.status_code == 200
    items = review.json()["mcq_items"]
    assert len(items) == 75
    assert "feedback" in items[0]
    reviewed = next(item for item in items if item["question_id"] == q["question_id"])
    wrong_after = client.get("/api/v1/me/wrong-questions?limit=200").json()
    in_wrong_book = any(item["question_id"] == q["question_id"] for item in wrong_after)
    assert in_wrong_book == (not reviewed["is_correct"])


def test_exam_pause_and_resume(client):
    login(client)
    created = client.post(
        "/api/v1/attempts", json={"paper_id": "psychology-ap-2025", "mode": "mcq"}
    )
    assert created.status_code == 200, created.text
    state = created.json()
    attempt_id = state["attempt"]["id"]
    assert state["paused"] is False
    assert state["remaining_ms"] > 0

    paused = client.post(f"/api/v1/attempts/{attempt_id}/pause")
    assert paused.status_code == 200, paused.text
    paused_state = paused.json()
    assert paused_state["paused"] is True
    assert paused_state["section"]["paused"] is True
    frozen_ms = paused_state["remaining_ms"]
    assert frozen_ms > 0

    fetched = client.get(f"/api/v1/attempts/{attempt_id}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["paused"] is True
    assert fetched.json()["remaining_ms"] == frozen_ms

    # A paused section keeps its old expires_at. Neither lazy finalization nor
    # the background sweep may submit it while the pause is active.
    from app.core.db import SessionLocal
    from app.core.time import utcnow
    from app.jobs.sweep_expired import run_once
    from app.users.models import AttemptSection

    with SessionLocal() as db:
        section = db.scalar(
            select(AttemptSection).where(
                AttemptSection.attempt_id == attempt_id,
                AttemptSection.section == "mcq",
            )
        )
        assert section is not None
        section.expires_at = utcnow() - timedelta(minutes=10)
        db.commit()

    paper = client.get("/api/v1/papers/psychology-ap-2025").json()
    assert any(a["id"] == attempt_id for a in paper["active_attempts"])
    run_once()
    still_paused = client.get(f"/api/v1/attempts/{attempt_id}")
    assert still_paused.status_code == 200, still_paused.text
    assert still_paused.json()["paused"] is True
    assert still_paused.json()["attempt"]["status"] == "in_progress"

    question = paused_state["questions"][0]
    blocked = client.patch(
        f"/api/v1/attempts/{attempt_id}/answers",
        json={"answers": [{"question_id": question["question_id"], "selected_label": "A"}]},
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "SECTION_PAUSED"

    blocked_submit = client.post(f"/api/v1/attempts/{attempt_id}/sections/mcq/submit")
    assert blocked_submit.status_code == 409

    resumed = client.post(f"/api/v1/attempts/{attempt_id}/resume")
    assert resumed.status_code == 200, resumed.text
    resumed_state = resumed.json()
    assert resumed_state["paused"] is False
    assert resumed_state["section"]["paused"] is False
    assert resumed_state["remaining_ms"] > 0

    saved = client.patch(
        f"/api/v1/attempts/{attempt_id}/answers",
        json={
            "answers": [
                {
                    "question_id": question["question_id"],
                    "selected_label": question["options"][0]["label"],
                }
            ]
        },
    )
    assert saved.status_code == 200, saved.text

    client.post(f"/api/v1/attempts/{attempt_id}/pause")
    abandoned = client.post(f"/api/v1/attempts/{attempt_id}/abandon")
    assert abandoned.status_code == 200, abandoned.text
    after = client.get(f"/api/v1/attempts/{attempt_id}").json()
    assert after["attempt"]["status"] == "abandoned"
    assert after["paused"] is False


def test_expired_attempt_is_finalized_before_paper_detail(client):
    from app.core.db import SessionLocal
    from app.core.time import utcnow
    from app.users.models import AttemptSection

    login(client)
    created = client.post(
        "/api/v1/attempts", json={"paper_id": "psychology-ap-2025", "mode": "mcq"}
    )
    assert created.status_code == 200, created.text
    attempt_id = created.json()["attempt"]["id"]

    with SessionLocal() as db:
        section = db.scalar(
            select(AttemptSection).where(
                AttemptSection.attempt_id == attempt_id,
                AttemptSection.section == "mcq",
            )
        )
        assert section is not None
        section.expires_at = utcnow() - timedelta(minutes=10)
        db.commit()

    paper = client.get("/api/v1/papers/psychology-ap-2025").json()
    assert paper["active_attempts"] == []

    state = client.get(f"/api/v1/attempts/{attempt_id}").json()
    assert state["attempt"]["status"] == "submitted"
    assert state["section"]["status"] == "submitted"

    dashboard = client.get("/api/v1/me/dashboard").json()
    continue_item = dashboard["continue"]
    assert not (
        continue_item and continue_item["type"] == "attempt" and continue_item["id"] == attempt_id
    )


def test_full_exam_and_frq_self_grade(client):
    login(client)
    created = client.post(
        "/api/v1/attempts",
        json={
            "paper_id": "psychology-ap-2025",
            "mode": "full",
            "frq_form": "Set 1",
        },
    )
    assert created.status_code == 200, created.text
    state = created.json()
    assert len(state["questions"]) == 75
    mcq_submit = client.post(f"/api/v1/attempts/{state['attempt']['id']}/sections/mcq/submit")
    assert mcq_submit.status_code == 200
    assert mcq_submit.json()["next_section"] == "frq"
    after = client.get(f"/api/v1/attempts/{state['attempt']['id']}").json()
    assert after["attempt"]["current_section"] == "frq"
    assert after["section"]["status"] == "not_started"
    assert after["can_start"] is True
    started = client.post(f"/api/v1/attempts/{state['attempt']['id']}/sections/frq/start")
    assert started.status_code == 200
    frq_state = started.json()
    assert len(frq_state["questions"]) == 2
    frq_q = frq_state["questions"][0]
    client.patch(
        f"/api/v1/attempts/{state['attempt']['id']}/answers",
        json={"answers": [{"question_id": frq_q["question_id"], "frq_text": "A-F answer"}]},
    )
    frq_submit = client.post(f"/api/v1/attempts/{state['attempt']['id']}/sections/frq/submit")
    assert frq_submit.status_code == 200
    review = client.get(f"/api/v1/attempts/{state['attempt']['id']}/review").json()
    assert len(review["frq_items"]) == 2
    scores = []
    for item in review["frq_items"]:
        for part in item["guidelines"]["parts"]:
            scores.append(
                {
                    "question_id": item["question_id"],
                    "part_id": part["part_id"],
                    "points": part["max_points"],
                }
            )
    graded = client.post(
        f"/api/v1/attempts/{state['attempt']['id']}/frq-scores",
        json={"scores": scores},
    )
    assert graded.status_code == 200, graded.text
    assert graded.json()["graded"] is True
    assert graded.json()["frq_total"] == 14
    final = client.get(f"/api/v1/attempts/{state['attempt']['id']}/review").json()
    assert final["attempt"]["status"] == "graded"
    assert final["attempt"]["frq_score"] == 14


def test_2018_frq_completed_manifest(client):
    login(client)
    created = client.post(
        "/api/v1/attempts", json={"paper_id": "psychology-ap-2018", "mode": "frq"}
    )
    assert created.status_code == 200, created.text
    state = created.json()
    assert state["attempt"]["frq_total"] == 14
    q = state["questions"][0]
    client.patch(
        f"/api/v1/attempts/{state['attempt']['id']}/answers",
        json={"answers": [{"question_id": q["question_id"], "frq_text": "answer"}]},
    )
    client.post(f"/api/v1/attempts/{state['attempt']['id']}/sections/frq/submit")
    review = client.get(f"/api/v1/attempts/{state['attempt']['id']}/review").json()
    totals = sorted(item["guidelines"]["rubric"]["total_points"] for item in review["frq_items"])
    assert totals == [7, 7]
    paper = client.get("/api/v1/papers/psychology-ap-2018").json()
    assert paper["frq_warning"] is None


def test_a_to_e_options(client):
    login(client)
    created = client.post(
        "/api/v1/attempts", json={"paper_id": "psychology-ap-2018", "mode": "mcq"}
    )
    assert created.status_code == 200
    counts = {len(q["options"]) for q in created.json()["questions"]}
    assert counts == {5}


def test_notes_and_bookmarks(client):
    login(client)
    groups = client.get("/api/v1/practice-groups").json()
    topics = client.get(f"/api/v1/practice-groups/{groups[0]['group_id']}/topics").json()
    session = client.post(
        "/api/v1/practice-sessions",
        json={"source": "topic", "topic_id": topics[0]["topic_id"], "count": 1},
    ).json()
    qid = session["questions"][0]["question_id"]
    assert client.put(f"/api/v1/me/bookmarks/{qid}").status_code == 200
    assert any(b["question_id"] == qid for b in client.get("/api/v1/me/bookmarks").json())
    note = client.post(
        "/api/v1/me/notes",
        json={"target_type": "question", "target_id": qid, "content": "注意区分概念"},
    )
    assert note.status_code == 200
    notes = client.get("/api/v1/me/notes").json()
    assert any(n["target_id"] == qid for n in notes)
    assert client.delete(f"/api/v1/me/bookmarks/{qid}").status_code == 200


def test_subject_locking_and_free_preview(client):
    login(client, entitle=False)
    groups = client.get("/api/v1/practice-groups").json()
    unit1 = next(item for item in groups if item["unit_id"] == "1")
    unit2 = next(item for item in groups if item["unit_id"] == "2")
    assert unit1["locked"] is False
    assert unit2["locked"] is True

    papers = client.get("/api/v1/papers").json()
    free_paper = next(item for item in papers if item["paper_id"] == "psychology-ap-2018")
    locked_paper = next(item for item in papers if item["paper_id"] == "psychology-ap-2025")
    assert free_paper["locked"] is False
    assert locked_paper["locked"] is True

    group_detail = client.get("/api/v1/practice-groups/psychology-unit2-practice")
    assert group_detail.status_code == 200, group_detail.text
    assert group_detail.json()["locked"] is True
    topics = client.get("/api/v1/practice-groups/psychology-unit2-practice/topics")
    assert topics.status_code == 200, topics.text
    assert topics.json() and all(item["locked"] for item in topics.json())

    paper_detail = client.get("/api/v1/papers/psychology-ap-2025")
    assert paper_detail.status_code == 200, paper_detail.text
    assert paper_detail.json()["locked"] is True

    locked = client.post(
        "/api/v1/attempts",
        json={"paper_id": "psychology-ap-2025", "mode": "mcq"},
    )
    assert locked.status_code == 403
    assert locked.json()["code"] == "SUBJECT_LOCKED"

    allowed = client.post(
        "/api/v1/attempts",
        json={"paper_id": "psychology-ap-2018", "mode": "mcq"},
    )
    assert allowed.status_code == 200, allowed.text


def test_activation_code_generate_redeem_stack_and_void(client):
    from datetime import date, timedelta

    from app.core.db import SessionLocal
    from app.core.security import hash_password
    from app.users.models import AdminUser

    with SessionLocal() as db:
        db.add(
            AdminUser(
                username="admin_codes_test",
                email="admin_codes_test@example.com",
                password_hash=hash_password("StrongPass123!"),
                role="super_admin",
                status="active",
            )
        )
        db.commit()

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"identifier": "admin_codes_test", "password": "StrongPass123!"},
    )
    assert login_response.status_code == 200, login_response.text

    def create_code(duration_days=None, expires_on=None):
        body = {
            "scope_type": "subject",
            "subject_id": "psychology",
            "count": 1,
            "note": "test",
        }
        if duration_days is not None:
            body["duration_days"] = duration_days
        if expires_on is not None:
            body["expires_on"] = expires_on
        response = client.post("/api/v1/admin/codes/batches", json=body)
        assert response.status_code == 200, response.text
        payload = response.json()
        return payload["batch"], payload["codes"][0]

    batch90, code90 = create_code(duration_days=90)
    download = client.get(f"/api/v1/admin/codes/batches/{batch90['id']}/download")
    assert download.status_code == 200, download.text
    assert code90 in download.text
    login(client, entitle=False)

    first = client.post("/api/v1/me/activation-codes/redeem", json={"code": code90})
    assert first.status_code == 200, first.text
    first_expiry = first.json()["subjects"][0]["expires_at"]

    _, code180 = create_code(duration_days=180)
    second = client.post("/api/v1/me/activation-codes/redeem", json={"code": code180})
    assert second.status_code == 200, second.text
    from datetime import datetime

    first_dt = datetime.fromisoformat(first_expiry)
    second_dt = datetime.fromisoformat(second.json()["subjects"][0]["expires_at"])
    assert 179 <= (second_dt - first_dt).total_seconds() / 86400 <= 181

    batch, code30 = create_code(duration_days=30)
    detail = client.get(f"/api/v1/admin/codes/batches/{batch['id']}/codes")
    assert detail.status_code == 200, detail.text
    code_id = detail.json()["codes"][0]["id"]
    voided = client.post(f"/api/v1/admin/codes/{code_id}/void")
    assert voided.status_code == 200, voided.text
    blocked = client.post("/api/v1/me/activation-codes/redeem", json={"code": code30})
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "CODE_VOIDED"

    target = date.today() + timedelta(days=400)
    _, date_code = create_code(expires_on=target.isoformat())
    date_result = client.post("/api/v1/me/activation-codes/redeem", json={"code": date_code})
    assert date_result.status_code == 200, date_result.text
    later = date.today() + timedelta(days=300)
    _, earlier_code = create_code(expires_on=later.isoformat())
    covered = client.post("/api/v1/me/activation-codes/redeem", json={"code": earlier_code})
    assert covered.status_code == 409
    assert covered.json()["code"] == "CODE_ALREADY_COVERED"

    entitlements = client.get("/api/v1/me/entitlements")
    assert entitlements.status_code == 200, entitlements.text
    psychology = next(
        item for item in entitlements.json()["entitlements"] if item["subject_id"] == "psychology"
    )
    assert psychology["active"] is True
    assert psychology["enabled"] is True
    assert psychology["name"] == "AP Psychology"
    assert entitlements.json()["active_count"] >= 1


def test_knowledge_graph_visibility_follows_unit_access(client):
    assert client.get("/api/v1/knowledge-graph").status_code == 401

    login(client, entitle=False)
    free_response = client.get("/api/v1/knowledge-graph")
    assert free_response.status_code == 200, free_response.text
    units = free_response.json()["units"]
    assert len(units) == 5
    unit1 = units[0]
    assert unit1["unit_id"] == "1"
    assert unit1["locked"] is False
    assert unit1["concept_count"] == 197
    assert unit1["topic_count"] == 8
    assert len(unit1["topics"]) == 8
    assert all(t["code"].startswith("1.") for t in unit1["topics"])
    concept = unit1["topics"][0]["concepts"][0]
    assert concept["concept_id"].startswith("psy-")
    assert "definition" in concept
    assert "relations" in concept
    assert "contrast" in concept
    assert "samples" in concept
    assert not any("is_correct" in str(item) for item in concept["samples"])

    # Unit 1 topics carry the PDF/textbook hierarchy. Nodes are English only
    # and concept IDs resolve either to the Topic concepts or the extra
    # mindmap concept payload.
    topic1 = unit1["topics"][0]
    assert topic1["mindmap"]["node_count"] == 25
    assert topic1["mindmap"]["matched_count"] >= 10
    assert topic1["mindmap"]["children"]
    serialized = str(topic1["mindmap"])
    assert not any("\u4e00" <= ch <= "\u9fff" for ch in serialized)
    known_ids = {
        c["concept_id"]
        for topic in unit1["topics"]
        for c in topic["concepts"]
    } | set(unit1["mindmap_concepts"])
    def collect_ids(node):
        if node.get("concept_id"):
            assert node["concept_id"] in known_ids
        for child in node.get("children") or []:
            collect_ids(child)
    for child in topic1["mindmap"]["children"]:
        collect_ids(child)
    assert unit1["mindmap_concepts"]
    assert all(not unit["locked"] or "topics" not in unit for unit in units[1:])
    assert all("mindmap" not in unit for unit in units[1:])
    assert all("mindmap_concepts" not in unit for unit in units[1:])

    # An active subject entitlement unlocks the remaining Units.
    login(client)
    paid_response = client.get("/api/v1/knowledge-graph")
    assert paid_response.status_code == 200, paid_response.text
    paid_units = paid_response.json()["units"]
    assert all(unit["locked"] is False for unit in paid_units)
    assert all(unit.get("topics") for unit in paid_units)


def test_mindmap_leaves_are_clickable_and_22_has_no_duplicate_framing(client):
    login(client)
    units = client.get("/api/v1/knowledge-graph").json()["units"]
    unit2 = next(unit for unit in units if unit["unit_id"] == "2")

    def leaves(topic):
        found = []

        def walk(node):
            children = node.get("children") or []
            if not children:
                found.append(node)
            for child in children:
                walk(child)

        for child in topic["mindmap"]["children"]:
            walk(child)
        return found

    # Every leaf in every unlocked Unit is either a knowledge-DB concept or
    # an explicit AI-assisted supplement.
    for unit in units:
        for topic in unit.get("topics", []):
            if "mindmap" not in topic:
                continue
            assert all(node.get("concept_id") for node in leaves(topic)), (
                unit["unit_id"],
                topic["code"],
            )

    topic22 = next(topic for topic in unit2["topics"] if topic["code"] == "2.2")
    leaf_nodes = leaves(topic22)
    assert leaf_nodes
    assert all(node.get("concept_id") for node in leaf_nodes)
    normalized = [str(node["label"]).strip().lower() for node in leaf_nodes]
    assert normalized.count("framing") == 1
    assert normalized.count("mental set") == 1
    supplement_ids = [
        node["concept_id"]
        for node in leaf_nodes
        if str(node.get("concept_id", "")).startswith("psy-supp-")
    ]
    assert supplement_ids
    for concept_id in supplement_ids:
        payload = unit2["mindmap_concepts"][concept_id]
        assert payload["supplement"] is True
        assert payload["definition"]
        assert payload["review_status"] == "draft"


def test_knowledge_graph_question_preview_is_read_only_and_access_checked(client):
    login(client, entitle=False)
    allowed = client.get("/api/v1/knowledge-graph/questions/psychology-cb26-u1-0208")
    assert allowed.status_code == 200, allowed.text
    payload = allowed.json()
    assert payload["question_id"] == "psychology-cb26-u1-0208"
    assert payload["options"]
    assert "is_correct" not in str(payload)
    assert "answer_text" not in payload or not payload["answer_text"]

    # A question from a locked real paper must not be readable through the
    # knowledge graph just because Unit 1 is free.
    locked = client.get("/api/v1/knowledge-graph/questions/psychology-2025-mcq-001")
    assert locked.status_code == 403, locked.text

    login(client)
    paid = client.get("/api/v1/knowledge-graph/questions/psychology-2025-mcq-001")
    assert paid.status_code == 200, paid.text
    assert paid.json()["options"]


def test_unit_knowledge_graph_is_cached_per_store():
    from app.content.store import ContentStore
    from app.core.config import get_settings

    store = ContentStore(RELEASE, get_settings())
    first = store.unit_knowledge_graph("1")
    second = store.unit_knowledge_graph("1")
    assert first is second
    assert first["concept_count"] == 197


def test_admin_knowledge_graph_editor_drafts_and_student_merge(client):
    """Admin graph drafts live in the app DB and merge into the student graph."""
    import uuid as uuid_module

    from app.core.db import SessionLocal
    from app.core.security import hash_password
    from app.users.models import AdminUser, KnowledgeGraphCustomConcept

    username = f"graph_admin_{uuid_module.uuid4().hex[:8]}"
    with SessionLocal() as db:
        admin = AdminUser(
            username=username,
            email=f"{username}@example.com",
            password_hash=hash_password("StrongPass123!"),
            role="content_editor",
            status="active",
        )
        db.add(admin)
        db.commit()

    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"identifier": username, "password": "StrongPass123!"},
    )
    assert login_response.status_code == 200, login_response.text

    units = client.get("/api/v1/admin/content/knowledge-graph/units")
    assert units.status_code == 200, units.text
    unit1 = next(item for item in units.json()["units"] if item["unit_id"] == "1")
    topic = next(item for item in unit1["topics"] if item["topic_code"] == "1.1")
    assert topic["has_mindmap"] is True

    # Start from a clean draft even if an earlier interrupted test left one.
    client.delete(
        "/api/v1/admin/content/knowledge-graph/topic",
        params={"unit_id": "1", "topic_code": "1.1"},
    )

    base = client.get(
        "/api/v1/admin/content/knowledge-graph/topic",
        params={"unit_id": "1", "topic_code": "1.1"},
    )
    assert base.status_code == 200, base.text
    assert base.json()["source"] == "release"
    assert base.json()["tree"]["children"]

    searched = client.get(
        "/api/v1/admin/content/knowledge-graph/search",
        params={"unit_id": "1", "q": "Genes"},
    )
    assert searched.status_code == 200, searched.text
    concept = next(
        item
        for item in searched.json()["results"]
        if item["kind"] == "concept" and item["name"].lower() == "genes"
    )

    custom_name = f"Admin Draft Concept {uuid_module.uuid4().hex[:6]}"
    created = client.post(
        "/api/v1/admin/content/knowledge-graph/custom-concepts",
        json={
            "unit_id": "1",
            "topic_code": "1.1",
            "name": custom_name,
            "definition": "A concept created by the admin graph editor.",
        },
    )
    assert created.status_code == 200, created.text
    custom = created.json()
    assert custom["concept_id"].startswith("psy-custom-")

    search_custom = client.get(
        "/api/v1/admin/content/knowledge-graph/search",
        params={"unit_id": "1", "q": custom_name},
    )
    assert search_custom.status_code == 200, search_custom.text
    assert any(
        item["concept_id"] == custom["concept_id"]
        for item in search_custom.json()["results"]
    )

    tree = {
        "id": "root-test",
        "label": "Interaction of Heredity and Environment",
        "type": "branch",
        "children": [
            {
                "id": "branch-test",
                "label": "Admin Test Branch",
                "type": "branch",
                "children": [
                    {
                        "id": "concept-test",
                        "label": "Genes",
                        "type": "concept",
                        "concept_id": concept["concept_id"],
                        "children": [],
                    },
                    {
                        "id": "custom-test",
                        "label": custom_name,
                        "type": "supplement",
                        "concept_id": custom["concept_id"],
                        "supplement": {
                            "id": custom["concept_id"],
                            "name": custom_name,
                            "definition": custom["definition"],
                            "source": "admin",
                            "review_status": "draft",
                        },
                        "children": [],
                    },
                ],
            }
        ],
    }
    saved = client.put(
        "/api/v1/admin/content/knowledge-graph/topic",
        json={
            "unit_id": "1",
            "topic_code": "1.1",
            "tree": tree,
            "expected_revision": 0,
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 1
    assert saved.json()["node_count"] == 4

    conflict = client.put(
        "/api/v1/admin/content/knowledge-graph/topic",
        json={
            "unit_id": "1",
            "topic_code": "1.1",
            "tree": tree,
            "expected_revision": 0,
        },
    )
    assert conflict.status_code == 409

    draft = client.get(
        "/api/v1/admin/content/knowledge-graph/topic",
        params={"unit_id": "1", "topic_code": "1.1"},
    )
    assert draft.status_code == 200, draft.text
    assert draft.json()["source"] == "draft"
    assert draft.json()["revision"] == 1

    # The student graph reads the draft without a restart and keeps every leaf
    # clickable, including the admin-created supplement.
    login(client)
    graph = client.get("/api/v1/knowledge-graph")
    assert graph.status_code == 200, graph.text
    student_unit = next(
        item for item in graph.json()["units"] if item["unit_id"] == "1"
    )
    student_topic = next(
        item for item in student_unit["topics"] if item["code"] == "1.1"
    )
    branch = student_topic["mindmap"]["children"][0]
    assert branch["label"] == "Admin Test Branch"
    leaves = []

    def walk(node):
        if not node.get("children"):
            leaves.append(node)
        for child in node.get("children") or []:
            walk(child)

    walk(branch)
    assert {leaf["concept_id"] for leaf in leaves} == {
        concept["concept_id"],
        custom["concept_id"],
    }
    assert all(leaf.get("concept_id") for leaf in leaves)
    custom_payload = student_unit["mindmap_concepts"][custom["concept_id"]]
    assert custom_payload["supplement"] is True
    assert custom_payload["supplement_source"] == "admin"
    assert custom_payload["review_status"] == "draft"
    assert custom_payload["definition"] == custom["definition"]

    reset = client.delete(
        "/api/v1/admin/content/knowledge-graph/topic",
        params={"unit_id": "1", "topic_code": "1.1"},
    )
    assert reset.status_code == 200, reset.text

    login(client)
    restored = client.get("/api/v1/knowledge-graph").json()
    restored_unit = next(item for item in restored["units"] if item["unit_id"] == "1")
    restored_topic = next(
        item for item in restored_unit["topics"] if item["code"] == "1.1"
    )
    assert all(
        child["label"] != "Admin Test Branch"
        for child in restored_topic["mindmap"]["children"]
    )

    with SessionLocal() as db:
        row = db.get(KnowledgeGraphCustomConcept, custom["concept_id"])
        if row is not None:
            db.delete(row)
            db.commit()


def test_admin_graph_save_normalizes_typographic_labels(client):
    """Saving a shipped tree must not fail on curly apostrophes or en dashes."""
    import uuid as uuid_module

    from app.core.db import SessionLocal
    from app.core.security import hash_password
    from app.users.models import AdminUser

    username = f"graph_label_{uuid_module.uuid4().hex[:8]}"
    with SessionLocal() as db:
        db.add(
            AdminUser(
                username=username,
                email=f"{username}@example.com",
                password_hash=hash_password("StrongPass123!"),
                role="content_editor",
                status="active",
            )
        )
        db.commit()
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"identifier": username, "password": "StrongPass123!"},
    )
    assert login_response.status_code == 200, login_response.text

    client.delete(
        "/api/v1/admin/content/knowledge-graph/topic",
        params={"unit_id": "2", "topic_code": "2.8"},
    )
    base = client.get(
        "/api/v1/admin/content/knowledge-graph/topic",
        params={"unit_id": "2", "topic_code": "2.8"},
    )
    assert base.status_code == 200, base.text
    labels = []

    def walk(node):
        labels.append(node["label"])
        for child in node.get("children") or []:
            walk(child)

    walk(base.json()["tree"])
    assert "Spearman's G Factor" in labels
    assert "Gardner's Multiple Intelligences" in labels
    assert all(label.isascii() for label in labels)

    saved = client.put(
        "/api/v1/admin/content/knowledge-graph/topic",
        json={
            "unit_id": "2",
            "topic_code": "2.8",
            "tree": base.json()["tree"],
            "expected_revision": 0,
        },
    )
    assert saved.status_code == 200, saved.text
    client.delete(
        "/api/v1/admin/content/knowledge-graph/topic",
        params={"unit_id": "2", "topic_code": "2.8"},
    )


def test_every_shipped_mindmap_is_admin_saveable(client):
    """Every Release-backed Topic tree must pass the same validation as a save."""
    from app.content.store import ContentStore
    from app.core.config import get_settings
    from app.core.db import SessionLocal
    from app.services.knowledge_graph import _clean_tree, get_editor_tree

    store = ContentStore(RELEASE, get_settings())
    checked = 0
    with SessionLocal() as db:
        for group in store.list_groups():
            unit_id = str(group["unit_id"])
            base = store.unit_mindmaps(unit_id)
            concepts = store.get_unit_concepts(unit_id)
            for topic in store.list_topics(str(group["group_id"])):
                code = str(topic["code"])
                if code not in base:
                    continue
                payload = get_editor_tree(store, db, unit_id, code)
                _clean_tree(
                    payload["tree"],
                    unit_id=unit_id,
                    topic_code=code,
                    concepts=concepts,
                )
                checked += 1
    assert checked == 35
