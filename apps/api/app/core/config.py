from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parents[2]  # apps/api
REPO_ROOT = Path(__file__).resolve().parents[4]  # repo root


def release_includes_subject(path: Path, subject_id: str) -> bool:
    """Return True when a Release manifest contains the given subject.

    Legacy per-subject Releases use ``subject_id``; merged Releases use a
    ``subjects`` array. Both formats are accepted here.
    """
    try:
        payload = json.loads((path / "release.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if str(payload.get("subject_id") or "") == subject_id:
        return True
    subjects = payload.get("subjects")
    return isinstance(subjects, list) and subject_id in {str(item) for item in subjects}


class Settings(BaseSettings):
    app_env: str = "dev"
    secret_key: str = "dev-secret-change-me"
    database_url: Optional[str] = None
    content_dir: Optional[Path] = None
    effective_content_dir: Optional[Path] = None
    asset_base_url: str = "/assets"
    email_provider: str = "dev"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_starttls: bool = True
    smtp_ssl: bool = False
    dev_otp_code: str = "246810"
    expose_dev_otp: bool = True
    password_min_length: int = 8
    cookie_secure: bool = False
    session_days: int = 30
    admin_cookie_name: str = "ap_admin_session"
    admin_session_hours: int = 12
    admin_content_write_enabled: bool = False
    flashcard_new_per_day: int = 60
    auto_create_tables: bool = True
    cors_origins: str = "http://localhost:3000"
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5
    otp_email_per_minute: int = 1
    otp_email_per_hour: int = 5
    otp_ip_per_hour: int = 20
    # Content payload encryption: off / optional / required.
    # "optional" encrypts when the client sends X-Content-Pubkey; production
    # should set CONTENT_ENCRYPTION_MODE=required.
    content_encryption_mode: str = "optional"
    content_encryption_prefixes: str = (
        "/api/v1/attempts,/api/v1/practice-sessions,"
        "/api/v1/practice-groups,/api/v1/papers,"
        "/api/v1/knowledge-graph,"
        "/api/v1/me,/api/v1/flashcards,/api/v1/question-reports"
    )
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 600
    asset_signing_required: bool = True
    asset_url_ttl_seconds: int = 7200
    asset_signing_key: str = ""
    wechat_mini_appid: str = ""
    wechat_mini_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=str(API_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def data_dir(self) -> Path:
        return REPO_ROOT / "data"

    @property
    def app_db_path(self) -> Path:
        return self.data_dir / "app" / "app.db"

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite+pysqlite:///{self.app_db_path}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def content_encryption_prefix_list(self) -> list[str]:
        return [x.strip() for x in self.content_encryption_prefixes.split(",") if x.strip()]

    @property
    def resolved_asset_signing_key(self) -> str:
        return self.asset_signing_key or self.secret_key

    @property
    def effective_root(self) -> Path:
        path = (
            Path(self.effective_content_dir)
            if self.effective_content_dir
            else Path("data/app/effective")
        )
        if not path.is_absolute():
            path = REPO_ROOT / path
        return path

    def _base_content_dir(self, subject_id: str) -> Path:
        if self.content_dir:
            path = Path(self.content_dir)
            if not path.is_absolute():
                path = REPO_ROOT / path
            return path
        releases = REPO_ROOT / "data" / "releases"
        # Merged design: ``active`` is one global symlink to the current
        # Release. Every enabled subject reads that same snapshot.
        active = releases / "active"
        if (active / "release.json").exists():
            if release_includes_subject(active, subject_id):
                return active
            # The merged active Release is authoritative. Do not silently serve
            # an older per-subject Release that still happens to exist.
            raise RuntimeError(
                f"Subject {subject_id} is not in the active Release; set CONTENT_DIR "
                "or activate a Release that includes it"
            )
        # Transitional P1.0 layout: ``active/<subject>`` per-subject pointers.
        subject_pointer = active / subject_id
        if (subject_pointer / "release.json").exists():
            return subject_pointer
        # Legacy single-subject pointer, still used by local dev and tests.
        current = releases / "current"
        if (current / "release.json").exists() and release_includes_subject(current, subject_id):
            return current
        candidates = (
            [
                p
                for p in releases.iterdir()
                if p.is_dir() and not p.name.startswith(".") and (p / "release.json").exists()
            ]
            if releases.exists()
            else []
        )
        matching = [
            candidate for candidate in candidates if release_includes_subject(candidate, subject_id)
        ]
        if matching:
            return max(matching, key=lambda p: p.stat().st_mtime)
        raise RuntimeError(f"No content release found for subject {subject_id}; set CONTENT_DIR")

    def resolve_base_content_dir(self, subject_id: str = "psychology") -> Path:
        """The immutable Release directory, ignoring any effective overlay."""
        return self._base_content_dir(subject_id)

    def resolve_content_dir(self, subject_id: str = "psychology") -> Path:
        """Return the effective content directory.

        Admin edits are materialized into ``effective_root/<subject>/<release-rN>``
        and exposed through a ``current`` symlink. If no effective overlay exists
        (or it belongs to a different Release), the immutable Release is used.
        """
        base = self._base_content_dir(subject_id)
        pointer = self.effective_root / subject_id / "current"
        try:
            base_manifest = json.loads((base / "release.json").read_text(encoding="utf-8"))
            effective_manifest = json.loads(
                (pointer / "release.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return base
        base_release_id = str(base_manifest.get("release_id") or base.name)
        effective_release_id = str(
            effective_manifest.get("release_id") or pointer.resolve().name
        )
        if base_release_id != effective_release_id:
            return base
        if not release_includes_subject(pointer, subject_id):
            return base
        return pointer


@lru_cache
def get_settings() -> Settings:
    return Settings()
