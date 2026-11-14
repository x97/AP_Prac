#!/usr/bin/env python3
"""Migrate the app SQLite database from phone-login to email-login.

SQLite cannot drop ``NOT NULL`` from ``users.phone`` in place, so this script
rebuilds ``users`` and ``user_identities`` while preserving every row. A
consistent backup is written next to the database before any change.

Usage:
    python scripts/migrate_auth_email.py [--db data/app/app.db]
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "data" / "app" / "app.db"


def table_columns(conn: sqlite3.Connection, table: str) -> dict[str, sqlite3.Row]:
    return {row["name"]: row for row in conn.execute(f'PRAGMA table_info("{table}")')}


def backup_database(conn: sqlite3.Connection, db_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = db_path.with_name(f"{db_path.name}.bak-{stamp}")
    with sqlite3.connect(target) as backup:
        conn.backup(backup)
    return target


USERS_DDL = """
CREATE TABLE users_new (
    id VARCHAR(36) NOT NULL,
    phone VARCHAR(32),
    email VARCHAR(254),
    email_verified_at DATETIME,
    password_hash VARCHAR(255),
    password_changed_at DATETIME,
    nickname VARCHAR(64),
    role VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL,
    merged_into_id VARCHAR(36),
    created_at DATETIME NOT NULL,
    last_login_at DATETIME,
    PRIMARY KEY (id),
    UNIQUE (phone),
    UNIQUE (email),
    FOREIGN KEY(merged_into_id) REFERENCES users (id) ON DELETE SET NULL
)
"""

IDENTITIES_DDL = """
CREATE TABLE user_identities_new (
    id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    provider VARCHAR(16) NOT NULL,
    app_id VARCHAR(64) NOT NULL DEFAULT '',
    provider_uid VARCHAR(128) NOT NULL,
    unionid VARCHAR(128),
    phone VARCHAR(32),
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_identity_provider UNIQUE (provider, app_id, provider_uid),
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
"""

VERIFICATION_CODES_DDL = """
CREATE TABLE IF NOT EXISTS verification_codes (
    id VARCHAR(36) NOT NULL,
    identifier VARCHAR(254) NOT NULL,
    channel VARCHAR(16) NOT NULL,
    purpose VARCHAR(24) NOT NULL,
    code_hash VARCHAR(64) NOT NULL,
    expires_at DATETIME NOT NULL,
    consumed_at DATETIME,
    attempts INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    ip VARCHAR(64),
    PRIMARY KEY (id)
)
"""

MERGE_LOGS_DDL = """
CREATE TABLE IF NOT EXISTS account_merge_logs (
    id VARCHAR(36) NOT NULL,
    source_user_id VARCHAR(36) NOT NULL,
    target_user_id VARCHAR(36) NOT NULL,
    moved_counts JSON,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id)
)
"""


def rebuild_users(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS users_new")
    conn.execute(USERS_DDL)
    conn.execute(
        """
        INSERT INTO users_new (
            id, phone, email, email_verified_at, password_hash,
            password_changed_at, nickname, role, status, merged_into_id,
            created_at, last_login_at
        )
        SELECT
            id, phone, NULL, NULL, NULL,
            NULL, nickname, role, status, NULL,
            created_at, last_login_at
        FROM users
        """
    )
    conn.execute("DROP TABLE users")
    conn.execute("ALTER TABLE users_new RENAME TO users")


def rebuild_identities(conn: sqlite3.Connection) -> None:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_identities'"
    ).fetchone()
    conn.execute("DROP TABLE IF EXISTS user_identities_new")
    conn.execute(IDENTITIES_DDL)
    if exists:
        conn.execute(
            """
            INSERT INTO user_identities_new (
                id, user_id, provider, app_id, provider_uid, unionid, phone, created_at
            )
            SELECT id, user_id, provider, '', provider_uid, unionid, phone, created_at
            FROM user_identities
            """
        )
        conn.execute("DROP TABLE user_identities")
    conn.execute("ALTER TABLE user_identities_new RENAME TO user_identities")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_identities_user_id "
        "ON user_identities (user_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_identities_unionid "
        "ON user_identities (unionid)"
    )


def migrate(db_path: Path) -> None:
    if not db_path.exists():
        raise SystemExit(f"database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    try:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if "users" not in tables:
            print("users table is missing; start the API once to create a fresh schema")
            return

        users_cols = table_columns(conn, "users")
        identities_cols = (
            table_columns(conn, "user_identities")
            if "user_identities" in tables
            else {}
        )
        needs_users = "email" not in users_cols or users_cols["phone"]["notnull"] != 0
        needs_identities = "app_id" not in identities_cols
        if not needs_users and not needs_identities:
            print("schema already migrated; creating any missing auxiliary tables")

        backup_path = backup_database(conn, db_path)
        print(f"backup written: {backup_path}")

        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN IMMEDIATE")
        try:
            if needs_users:
                rebuild_users(conn)
            if needs_identities:
                rebuild_identities(conn)
            conn.execute(VERIFICATION_CODES_DDL)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_verification_identifier_created "
                "ON verification_codes (identifier, created_at)"
            )
            conn.execute(MERGE_LOGS_DDL)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_account_merge_logs_source_user_id "
                "ON account_merge_logs (source_user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_account_merge_logs_target_user_id "
                "ON account_merge_logs (target_user_id)"
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        violations = list(conn.execute("PRAGMA foreign_key_check"))
        if violations:
            raise SystemExit(f"foreign key check failed: {violations}")

        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        identity_count = conn.execute(
            "SELECT COUNT(*) FROM user_identities"
        ).fetchone()[0]
        print(f"migration complete: users={user_count}, identities={identity_count}")
    finally:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    migrate(args.db.resolve())


if __name__ == "__main__":
    main()
