from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.users.models import (
    AccountMergeLog,
    ActivationCodeRedemption,
    Attempt,
    Bookmark,
    Event,
    FlashcardReview,
    Note,
    PracticeSession,
    QuestionReport,
    User,
    UserDailyStat,
    UserEntitlement,
    UserFlashcard,
    UserIdentity,
    UserQuestionStat,
    UserSession,
    WrongQuestion,
)


def _move_simple(db: Session, model, source_id: str, target_id: str) -> int:
    result = db.execute(
        update(model).where(model.user_id == source_id).values(user_id=target_id)
    )
    return int(result.rowcount or 0)


def _merge_wrong_questions(db: Session, source_id: str, target_id: str) -> int:
    rows = list(db.scalars(select(WrongQuestion).where(WrongQuestion.user_id == source_id)))
    for row in rows:
        existing = db.get(WrongQuestion, (target_id, row.question_id))
        if not existing:
            row.user_id = target_id
            continue
        existing.wrong_count += row.wrong_count
        existing.correct_streak = max(existing.correct_streak, row.correct_streak)
        existing.last_wrong_at = max(
            [value for value in (existing.last_wrong_at, row.last_wrong_at) if value],
            default=None,
        )
        existing.mastered_at = existing.mastered_at or row.mastered_at
        if row.updated_at and (
            not existing.updated_at or row.updated_at > existing.updated_at
        ):
            existing.mastery = row.mastery
        db.delete(row)
    return len(rows)


def _merge_question_stats(db: Session, source_id: str, target_id: str) -> int:
    rows = list(
        db.scalars(select(UserQuestionStat).where(UserQuestionStat.user_id == source_id))
    )
    for row in rows:
        existing = db.get(UserQuestionStat, (target_id, row.question_id))
        if not existing:
            row.user_id = target_id
            continue
        existing.attempts += row.attempts
        existing.correct_count += row.correct_count
        if row.last_answered_at and (
            not existing.last_answered_at
            or row.last_answered_at > existing.last_answered_at
        ):
            existing.last_answered_at = row.last_answered_at
            existing.last_is_correct = row.last_is_correct
            existing.last_correct_at = row.last_correct_at
            existing.unit_id = row.unit_id or existing.unit_id
            existing.primary_topic_id = row.primary_topic_id or existing.primary_topic_id
            existing.content_release_id = row.content_release_id
        db.delete(row)
    return len(rows)


def _merge_daily_stats(db: Session, source_id: str, target_id: str) -> int:
    rows = list(db.scalars(select(UserDailyStat).where(UserDailyStat.user_id == source_id)))
    for row in rows:
        existing = db.get(UserDailyStat, (target_id, row.day))
        if not existing:
            row.user_id = target_id
            continue
        existing.answered += row.answered
        existing.correct += row.correct
        db.delete(row)
    return len(rows)


def _merge_flashcard_reviews(db: Session, source_id: str, target_id: str) -> int:
    rows = list(
        db.scalars(select(FlashcardReview).where(FlashcardReview.user_id == source_id))
    )
    for row in rows:
        existing = db.get(FlashcardReview, (target_id, row.concept_id))
        if not existing:
            row.user_id = target_id
            continue
        existing.box = max(existing.box, row.box)
        existing.seen_count += row.seen_count
        existing.known_count += row.known_count
        if row.last_reviewed_at and (
            not existing.last_reviewed_at
            or row.last_reviewed_at > existing.last_reviewed_at
        ):
            existing.last_reviewed_at = row.last_reviewed_at
            existing.last_rating = row.last_rating
        if row.next_due_at and (
            not existing.next_due_at or row.next_due_at < existing.next_due_at
        ):
            existing.next_due_at = row.next_due_at
        existing.created_at = min(existing.created_at, row.created_at)
        db.delete(row)
    return len(rows)


def _merge_user_flashcards(db: Session, source_id: str, target_id: str) -> int:
    existing_by_term = {
        card.term.strip().lower(): card
        for card in db.scalars(
            select(UserFlashcard).where(UserFlashcard.user_id == target_id)
        )
    }
    rows = list(db.scalars(select(UserFlashcard).where(UserFlashcard.user_id == source_id)))
    for row in rows:
        key = row.term.strip().lower()
        existing = existing_by_term.get(key)
        if not existing:
            row.user_id = target_id
            existing_by_term[key] = row
            continue
        existing.box = max(existing.box, row.box)
        existing.seen_count += row.seen_count
        existing.known_count += row.known_count
        if row.last_reviewed_at and (
            not existing.last_reviewed_at
            or row.last_reviewed_at > existing.last_reviewed_at
        ):
            existing.last_reviewed_at = row.last_reviewed_at
            existing.last_rating = row.last_rating
        if row.next_due_at and (
            not existing.next_due_at or row.next_due_at < existing.next_due_at
        ):
            existing.next_due_at = row.next_due_at
        if not existing.detail_meaning:
            existing.detail_meaning = row.detail_meaning
        db.delete(row)
    return len(rows)


def _merge_entitlements(db: Session, source_id: str, target_id: str) -> int:
    rows = list(
        db.scalars(select(UserEntitlement).where(UserEntitlement.user_id == source_id))
    )
    for row in rows:
        existing = db.scalar(
            select(UserEntitlement).where(
                UserEntitlement.user_id == target_id,
                UserEntitlement.subject_id == row.subject_id,
            )
        )
        if not existing:
            row.user_id = target_id
            continue
        if row.expires_at and (
            not existing.expires_at or row.expires_at > existing.expires_at
        ):
            existing.expires_at = row.expires_at
            existing.source = row.source
            existing.last_code_id = row.last_code_id
        db.delete(row)
    return len(rows)


def _merge_bookmarks(db: Session, source_id: str, target_id: str) -> int:
    rows = list(db.scalars(select(Bookmark).where(Bookmark.user_id == source_id)))
    for row in rows:
        existing = db.get(Bookmark, (target_id, row.question_id))
        if existing:
            existing.created_at = min(existing.created_at, row.created_at)
            db.delete(row)
        else:
            row.user_id = target_id
    return len(rows)


def _merge_notes(db: Session, source_id: str, target_id: str) -> int:
    rows = list(db.scalars(select(Note).where(Note.user_id == source_id)))
    for row in rows:
        existing = db.scalar(
            select(Note).where(
                Note.user_id == target_id,
                Note.target_type == row.target_type,
                Note.target_id == row.target_id,
            )
        )
        if not existing:
            row.user_id = target_id
            continue
        if row.updated_at and (
            not existing.updated_at or row.updated_at > existing.updated_at
        ):
            existing.content = row.content
            existing.updated_at = row.updated_at
        db.delete(row)
    return len(rows)


def merge_users(db: Session, source: User, target: User) -> dict[str, int]:
    """Merge ``source`` into ``target`` in one transaction.

    The source row is kept as a tombstone (``status='merged'`` and
    ``merged_into_id``) because a hard delete cascades through every user-owned
    table and would silently drop anything a future migration misses.
    """
    if source.id == target.id:
        return {}
    if source.status == "merged" and source.merged_into_id:
        if source.merged_into_id == target.id:
            return {}
        raise ValueError("source account was already merged into another account")

    counts: dict[str, int] = {}
    counts["identities"] = _move_simple(db, UserIdentity, source.id, target.id)
    counts["sessions"] = _move_simple(db, UserSession, source.id, target.id)
    counts["attempts"] = _move_simple(db, Attempt, source.id, target.id)
    counts["practice_sessions"] = _move_simple(db, PracticeSession, source.id, target.id)
    counts["activation_redemptions"] = _move_simple(
        db, ActivationCodeRedemption, source.id, target.id
    )
    counts["events"] = _move_simple(db, Event, source.id, target.id)
    counts["question_reports"] = _move_simple(db, QuestionReport, source.id, target.id)
    counts["wrong_questions"] = _merge_wrong_questions(db, source.id, target.id)
    counts["question_stats"] = _merge_question_stats(db, source.id, target.id)
    counts["daily_stats"] = _merge_daily_stats(db, source.id, target.id)
    counts["flashcard_reviews"] = _merge_flashcard_reviews(db, source.id, target.id)
    counts["user_flashcards"] = _merge_user_flashcards(db, source.id, target.id)
    counts["entitlements"] = _merge_entitlements(db, source.id, target.id)
    counts["bookmarks"] = _merge_bookmarks(db, source.id, target.id)
    counts["notes"] = _merge_notes(db, source.id, target.id)

    # Keep the profile a student filled in on the account being retired.
    for field in (
        "nickname",
        "grade",
        "region",
        "target_score",
        "studied_psychology",
        "study_mode",
        "exam_time",
    ):
        if getattr(target, field) is None and getattr(source, field) is not None:
            setattr(target, field, getattr(source, field))
    if target.profile_completed_at is None and source.profile_completed_at is not None:
        target.profile_completed_at = source.profile_completed_at

    source.status = "merged"
    source.merged_into_id = target.id
    source.email = None
    source.password_hash = None
    source.email_verified_at = None
    source.last_login_at = utcnow()

    db.add(
        AccountMergeLog(
            source_user_id=source.id,
            target_user_id=target.id,
            moved_counts=counts,
        )
    )
    db.flush()
    return counts
