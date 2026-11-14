from __future__ import annotations

import argparse
import logging
import time
from datetime import timedelta

from sqlalchemy import select

from app.content.store import ContentStore
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.time import as_utc, utcnow
from app.services.exam_engine import GRACE_SECONDS, submit_section
from app.users.models import Attempt, AttemptSection, AttemptSectionPause, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jobs.sweep_expired")


def run_once() -> int:
    settings = get_settings()
    store = ContentStore(settings.resolve_content_dir(), settings)
    db = SessionLocal()
    count = 0
    try:
        cutoff = utcnow() - timedelta(seconds=GRACE_SECONDS)
        paused = {(row.attempt_id, row.section) for row in db.scalars(select(AttemptSectionPause))}
        sections = list(
            db.scalars(
                select(AttemptSection).where(
                    AttemptSection.status == "active",
                    AttemptSection.expires_at.is_not(None),
                )
            )
        )
        for section in sections:
            if as_utc(section.expires_at) > cutoff:
                continue
            if (section.attempt_id, section.section) in paused:
                continue
            attempt = db.get(Attempt, section.attempt_id)
            if not attempt:
                continue
            user = db.get(User, attempt.user_id)
            if not user:
                continue
            try:
                submit_section(db, store, user, attempt.id, section.section, auto=True)
                count += 1
            except Exception:
                logger.exception("failed to auto-submit attempt %s", attempt.id)
                db.rollback()
    finally:
        db.close()
    logger.info("swept %s expired sections", count)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-submit expired exam sections")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    if args.once:
        run_once()
        return 0
    while True:
        run_once()
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
