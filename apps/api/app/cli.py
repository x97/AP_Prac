"""Administrative CLI for creating and maintaining admin accounts.

Usage:
  cd apps/api
  python -m app.cli create-admin
  python -m app.cli list-admins
  python -m app.cli reset-password --username admin
"""

from __future__ import annotations

import argparse
import getpass
import re
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.db import SessionLocal, init_db
from app.core.security import hash_password
from app.users.models import AdminUser

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,64}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ROLES = ("super_admin", "content_editor", "analyst", "support")


def _prompt_password() -> str:
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters")
    return password


def _password(value: Optional[str]) -> str:
    return value if value else _prompt_password()


def _find_admin(db, username: str) -> AdminUser:  # noqa: ANN001
    admin = db.scalar(select(AdminUser).where(func.lower(AdminUser.username) == username.lower()))
    if not admin:
        raise SystemExit(f"Admin not found: {username}")
    return admin


def create_admin(args: argparse.Namespace) -> int:
    username = (args.username or input("Username: ")).strip()
    email = (args.email or input("Email: ")).strip().lower()
    if not USERNAME_RE.match(username):
        raise SystemExit("Username must be 3-64 characters: letters, numbers, _ . -")
    if not EMAIL_RE.match(email):
        raise SystemExit("Invalid email")
    password = _password(args.password)
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters")

    init_db()
    with SessionLocal() as db:
        existing = db.scalar(
            select(AdminUser).where(
                or_(
                    func.lower(AdminUser.username) == username.lower(),
                    func.lower(AdminUser.email) == email,
                )
            )
        )
        if existing:
            raise SystemExit("Username or email already exists")
        admin = AdminUser(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=args.role,
            status="active",
        )
        db.add(admin)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise SystemExit("Username or email already exists") from exc
        db.refresh(admin)
        print(f"Created admin: {admin.username} <{admin.email}> role={admin.role} id={admin.id}")
    return 0


def reset_password(args: argparse.Namespace) -> int:
    init_db()
    with SessionLocal() as db:
        admin = _find_admin(db, args.username)
        password = _password(args.password)
        if len(password) < 8:
            raise SystemExit("Password must be at least 8 characters")
        admin.password_hash = hash_password(password)
        from app.core.time import utcnow

        admin.password_changed_at = utcnow()
        db.commit()
        print(f"Password updated for {admin.username}")
    return 0


def set_status(args: argparse.Namespace, status: str) -> int:
    init_db()
    with SessionLocal() as db:
        admin = _find_admin(db, args.username)
        admin.status = status
        db.commit()
        print(f"{admin.username}: status={status}")
    return 0


def list_admins(_: argparse.Namespace) -> int:
    init_db()
    with SessionLocal() as db:
        admins = list(db.scalars(select(AdminUser).order_by(AdminUser.created_at)))
        if not admins:
            print("No admin accounts")
            return 0
        print(f"{'USERNAME':20} {'EMAIL':32} {'ROLE':16} {'STATUS':10} LAST LOGIN")
        for admin in admins:
            last = admin.last_login_at.isoformat() if admin.last_login_at else "-"
            print(f"{admin.username:20} {admin.email:32} {admin.role:16} {admin.status:10} {last}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AP Psychology admin CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-admin", help="Create an admin account")
    create.add_argument("--username")
    create.add_argument("--email")
    create.add_argument("--password", help="Avoid on shared shells; prompt is safer")
    create.add_argument("--role", choices=ROLES, default="super_admin")
    create.set_defaults(func=create_admin)

    reset = sub.add_parser("reset-password", help="Reset an admin password")
    reset.add_argument("--username", required=True)
    reset.add_argument("--password", help="Avoid on shared shells; prompt is safer")
    reset.set_defaults(func=reset_password)

    disable = sub.add_parser("disable-admin", help="Disable an admin account")
    disable.add_argument("--username", required=True)
    disable.set_defaults(func=lambda args: set_status(args, "disabled"))

    enable = sub.add_parser("enable-admin", help="Enable an admin account")
    enable.add_argument("--username", required=True)
    enable.set_defaults(func=lambda args: set_status(args, "active"))

    listing = sub.add_parser("list-admins", help="List admin accounts")
    listing.set_defaults(func=list_admins)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
