from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.time import utcnow


def new_id() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    # Login identifiers. ``email`` is NULL for a WeChat-only (virtual) account;
    # ``phone`` is legacy profile data and no longer participates in login.
    phone: Mapped[Optional[str]] = mapped_column(String(32), unique=True)
    email: Mapped[Optional[str]] = mapped_column(String(254), unique=True, index=True)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    nickname: Mapped[Optional[str]] = mapped_column(String(64))
    # Student profile collected on first sign-in. NULL means "not answered
    # yet", which is why studied_psychology is a nullable Boolean.
    grade: Mapped[Optional[str]] = mapped_column(String(32))
    region: Mapped[Optional[str]] = mapped_column(String(64))
    target_score: Mapped[Optional[int]] = mapped_column(Integer)
    studied_psychology: Mapped[Optional[bool]] = mapped_column(Boolean)
    study_mode: Mapped[Optional[str]] = mapped_column(String(32))
    exam_time: Mapped[Optional[str]] = mapped_column(String(16))
    teacher_note: Mapped[Optional[str]] = mapped_column(Text)
    profile_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    role: Mapped[str] = mapped_column(String(16), default="student", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    # Set on a source account after it is merged into another account. The row
    # is kept as a tombstone so stale references still resolve.
    merged_into_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("provider", "app_id", "provider_uid", name="uq_identity_provider"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    # openid is scoped to one WeChat app; keep the appid in the key so a future
    # official-account or second mini-program cannot collide with this one.
    app_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    provider_uid: Mapped[str] = mapped_column(String(128), nullable=False)
    unionid: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class UserSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (Index("idx_sessions_expires", "expires_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ip: Mapped[Optional[str]] = mapped_column(String(64))
    user_agent: Mapped[Optional[str]] = mapped_column(String(256))


class VerificationCode(Base):
    __tablename__ = "verification_codes"
    __table_args__ = (
        Index("idx_verification_identifier_created", "identifier", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    identifier: Mapped[str] = mapped_column(String(254), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), default="email", nullable=False)
    purpose: Mapped[str] = mapped_column(String(24), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    ip: Mapped[Optional[str]] = mapped_column(String(64))


class AccountMergeLog(Base):
    __tablename__ = "account_merge_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    target_user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    moved_counts: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = (
        Index("idx_attempt_user_paper", "user_id", "paper_id", "status"),
        Index("idx_attempt_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    paper_id: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(8), nullable=False)
    frq_form: Mapped[Optional[str]] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(24), default="in_progress", nullable=False)
    current_section: Mapped[Optional[str]] = mapped_column(String(8))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    mcq_score: Mapped[Optional[int]] = mapped_column(Integer)
    mcq_total: Mapped[Optional[int]] = mapped_column(Integer)
    frq_score: Mapped[Optional[int]] = mapped_column(Integer)
    frq_total: Mapped[Optional[int]] = mapped_column(Integer)
    content_release_id: Mapped[str] = mapped_column(String(64), nullable=False)
    config_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class AttemptSection(Base):
    __tablename__ = "attempt_sections"
    __table_args__ = (UniqueConstraint("attempt_id", "section", name="uq_attempt_section"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), index=True
    )
    section: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="not_started", nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finalized_reason: Mapped[Optional[str]] = mapped_column(String(16))
    score: Mapped[Optional[int]] = mapped_column(Integer)
    total: Mapped[Optional[int]] = mapped_column(Integer)


class AttemptSectionPause(Base):
    __tablename__ = "attempt_section_pauses"

    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), primary_key=True
    )
    section: Mapped[str] = mapped_column(String(8), primary_key=True)
    remaining_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    paused_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class AttemptQuestion(Base):
    __tablename__ = "attempt_questions"

    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    section: Mapped[str] = mapped_column(String(8), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    display_number: Mapped[int] = mapped_column(Integer, nullable=False)


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"

    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    selected_label: Mapped[Optional[str]] = mapped_column(String(4))
    frq_text: Mapped[Optional[str]] = mapped_column(Text)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    time_spent_ms: Mapped[Optional[int]] = mapped_column(Integer)
    server_saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class AttemptFrqScore(Base):
    __tablename__ = "attempt_frq_scores"

    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    part_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    max_points: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class PracticeSession(Base):
    __tablename__ = "practice_sessions"
    __table_args__ = (Index("idx_practice_user_updated", "user_id", "updated_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    group_id: Mapped[Optional[str]] = mapped_column(String(64))
    topic_id: Mapped[Optional[str]] = mapped_column(String(96))
    status: Mapped[str] = mapped_column(String(16), default="in_progress", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    score: Mapped[Optional[int]] = mapped_column(Integer)
    total: Mapped[Optional[int]] = mapped_column(Integer)
    content_release_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class PracticeSessionQuestion(Base):
    __tablename__ = "practice_session_questions"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_label: Mapped[Optional[str]] = mapped_column(String(4))
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class WrongQuestion(Base):
    __tablename__ = "wrong_questions"
    __table_args__ = (Index("idx_wrong_user_mastery", "user_id", "mastery", "last_wrong_at"),)

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    unit_id: Mapped[Optional[str]] = mapped_column(String(16))
    primary_topic_id: Mapped[Optional[str]] = mapped_column(String(96))
    content_release_id: Mapped[str] = mapped_column(String(64), nullable=False)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mastery: Mapped[str] = mapped_column(String(16), default="learning", nullable=False)
    last_wrong_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    mastered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (Index("idx_bookmark_user_created", "user_id", "created_at"),)

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", name="uq_note_target"),
        Index("idx_note_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class UserQuestionStat(Base):
    __tablename__ = "user_question_stats"
    __table_args__ = (Index("idx_uqs_user_last", "user_id", "last_answered_at"),)

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    unit_id: Mapped[Optional[str]] = mapped_column(String(16))
    primary_topic_id: Mapped[Optional[str]] = mapped_column(String(96))
    content_release_id: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    last_answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_correct_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class UserDailyStat(Base):
    __tablename__ = "user_daily_stats"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    answered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class FlashcardReview(Base):
    __tablename__ = "flashcard_reviews"
    __table_args__ = (Index("idx_flashcard_user_due", "user_id", "next_due_at"),)

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    concept_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    box: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    seen_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    known_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_rating: Mapped[Optional[str]] = mapped_column(String(8))
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class UserFlashcard(Base):
    __tablename__ = "user_flashcards"
    __table_args__ = (
        Index("idx_user_flashcard_user_updated", "user_id", "updated_at"),
        Index("idx_user_flashcard_user_due", "user_id", "next_due_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    term: Mapped[str] = mapped_column(String(200), nullable=False)
    short_meaning: Mapped[str] = mapped_column(Text, nullable=False)
    detail_meaning: Mapped[str] = mapped_column(Text, default="", nullable=False)
    box: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    seen_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    known_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_rating: Mapped[Optional[str]] = mapped_column(String(8))
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="content_editor", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AdminSession(Base):
    __tablename__ = "admin_sessions"
    __table_args__ = (Index("idx_admin_session_expires", "expires_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    admin_id: Mapped[str] = mapped_column(
        ForeignKey("admin_users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ip: Mapped[Optional[str]] = mapped_column(String(64))
    user_agent: Mapped[Optional[str]] = mapped_column(String(256))


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    __table_args__ = (Index("idx_admin_audit_created", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    admin_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(32))
    target_id: Mapped[Optional[str]] = mapped_column(String(128))
    detail: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    ip: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ReleaseJob(Base):
    __tablename__ = "release_jobs"
    __table_args__ = (Index("idx_release_job_created", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    admin_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    release_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="building", nullable=False)
    log: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ContentRelease(Base):
    __tablename__ = "content_releases"
    __table_args__ = (Index("idx_content_release_subject_status", "subject_id", "status"),)

    subject_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    release_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="imported", nullable=False)
    counts_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    checksums_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    source: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ContentActiveRelease(Base):
    __tablename__ = "content_active_release"

    subject_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    release_id: Mapped[str] = mapped_column(String(64), nullable=False)
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    activated_by: Mapped[Optional[str]] = mapped_column(String(36))


class AdminContentRecord(Base):
    """App-side content override that takes precedence over a Release.

    The immutable Release remains the base snapshot. Effective content is
    materialized from Release + these records, so a later Release rebuild does
    not discard admin edits. ``origin`` is one of admin_created / admin_edited /
    admin_deleted.
    """

    __tablename__ = "admin_content_records"
    __table_args__ = (
        UniqueConstraint(
            "subject_id", "entity_type", "entity_id", name="uq_admin_content_record"
        ),
        Index("idx_admin_content_type", "subject_id", "entity_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    subject_id: Mapped[str] = mapped_column(String(64), default="psychology", nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    origin: Mapped[str] = mapped_column(String(16), nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    base_release_id: Mapped[Optional[str]] = mapped_column(String(64))
    created_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class AdminContentRevision(Base):
    __tablename__ = "admin_content_revisions"

    subject_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class KnowledgeGraphCustomConcept(Base):
    __tablename__ = "knowledge_graph_custom_concepts"
    __table_args__ = (Index("idx_kg_custom_unit", "subject_id", "unit_id"),)

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(64), default="psychology", nullable=False)
    unit_id: Mapped[str] = mapped_column(String(16), nullable=False)
    topic_code: Mapped[Optional[str]] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    definition: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="admin", nullable=False)
    review_status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class KnowledgeGraphTopicDraft(Base):
    __tablename__ = "knowledge_graph_topic_drafts"
    __table_args__ = (
        UniqueConstraint("subject_id", "unit_id", "topic_code", name="uq_kg_topic_draft"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    subject_id: Mapped[str] = mapped_column(String(64), default="psychology", nullable=False)
    unit_id: Mapped[str] = mapped_column(String(16), nullable=False)
    topic_code: Mapped[str] = mapped_column(String(16), nullable=False)
    tree: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class QuestionReport(Base):
    __tablename__ = "question_reports"
    __table_args__ = (Index("idx_report_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    question_id: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_id: Mapped[Optional[str]] = mapped_column(String(36))
    practice_session_id: Mapped[Optional[str]] = mapped_column(String(36))
    selected_label: Mapped[Optional[str]] = mapped_column(String(4))
    content_release_id: Mapped[Optional[str]] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class QuestionStar(Base):
    """Admin-assigned 1-5 star rating for a question.

    Kept in the app database rather than the content overlay: star ratings are
    admin metadata, and writing them should not rebuild effective content.
    ``question_id`` is stable across Releases.
    """

    __tablename__ = "question_stars"

    subject_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default="psychology"
    )
    question_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ActivationCodeBatch(Base):
    __tablename__ = "activation_code_batches"
    __table_args__ = (Index("idx_activation_batch_created", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scope_type: Mapped[str] = mapped_column(String(16), nullable=False)  # all / subject
    subject_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    duration_days: Mapped[Optional[int]] = mapped_column(Integer)
    expires_on: Mapped[Optional[date]] = mapped_column(Date)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    voided_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL")
    )


class ActivationCode(Base):
    __tablename__ = "activation_codes"
    __table_args__ = (
        Index("idx_activation_code_batch", "batch_id"),
        Index("idx_activation_code_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(
        ForeignKey("activation_code_batches.id", ondelete="CASCADE"), nullable=False
    )
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    code_hint: Mapped[str] = mapped_column(String(16), nullable=False)
    code_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    max_uses: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ActivationCodeRedemption(Base):
    __tablename__ = "activation_code_redemptions"
    __table_args__ = (Index("idx_redemption_user", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code_id: Mapped[str] = mapped_column(
        ForeignKey("activation_codes.id", ondelete="CASCADE"), nullable=False
    )
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    before_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    after_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class UserEntitlement(Base):
    __tablename__ = "user_entitlements"
    __table_args__ = (
        UniqueConstraint("user_id", "subject_id", name="uq_entitlement_user_subject"),
        Index("idx_entitlement_expires", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(16), default="code", nullable=False)
    last_code_id: Mapped[Optional[str]] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ClassroomHomework(Base):
    """Reusable teacher-authored homework, made of MCQ question ids."""

    __tablename__ = "classroom_homeworks"
    __table_args__ = (
        Index("idx_homework_subject_status", "subject_id", "status", "updated_at"),
        Index("idx_homework_unit_topic", "unit_id", "topic_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text)
    unit_id: Mapped[Optional[str]] = mapped_column(String(16))
    unit_title: Mapped[Optional[str]] = mapped_column(String(120))
    topic_id: Mapped[Optional[str]] = mapped_column(String(96))
    topic_code: Mapped[Optional[str]] = mapped_column(String(32))
    topic_title: Mapped[Optional[str]] = mapped_column(String(200))
    question_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    content_release_id: Mapped[Optional[str]] = mapped_column(String(64))
    created_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ClassroomHomeworkQuestion(Base):
    __tablename__ = "classroom_homework_questions"
    __table_args__ = (
        Index("idx_homework_question_q", "question_id"),
        Index("idx_homework_question_order", "homework_id", "sort_order"),
    )

    homework_id: Mapped[str] = mapped_column(
        ForeignKey("classroom_homeworks.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str] = mapped_column(String(8), default="MCQ", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class StudyPlan(Base):
    __tablename__ = "study_plans"
    __table_args__ = (Index("idx_study_plan_subject_status", "subject_id", "status", "updated_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(32))
    color: Mapped[str] = mapped_column(String(16), default="primary", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class StudyPlanItem(Base):
    __tablename__ = "study_plan_items"
    __table_args__ = (
        Index("idx_study_plan_item_order", "plan_id", "position"),
        Index("idx_study_plan_item_homework", "homework_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    plan_id: Mapped[str] = mapped_column(
        ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False
    )
    homework_id: Mapped[str] = mapped_column(
        ForeignKey("classroom_homeworks.id", ondelete="RESTRICT"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class StudyPlanAssignment(Base):
    __tablename__ = "study_plan_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "plan_id", "active_slot", name="uq_assignment_active"),
        Index("idx_study_assignment_user", "user_id", "status", "start_date"),
        Index("idx_study_assignment_plan", "plan_id", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    plan_id: Mapped[str] = mapped_column(
        ForeignKey("study_plans.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    assigned_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    plan_title: Mapped[str] = mapped_column(String(200), nullable=False)
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    schedule_mode: Mapped[str] = mapped_column(String(16), default="daily", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    # "1" while active, NULL after completion/cancellation. The unique
    # constraint above then allows historical rows while preventing duplicate
    # active assignments of the same plan to the same student.
    active_slot: Mapped[Optional[str]] = mapped_column(String(8))
    total_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    answered_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_task_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_release_id: Mapped[Optional[str]] = mapped_column(String(64))
    note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL")
    )


class StudyPlanTask(Base):
    """Denormalized per-day task row; the student calendar reads only this table."""

    __tablename__ = "study_plan_tasks"
    __table_args__ = (
        UniqueConstraint("assignment_id", "plan_item_id", name="uq_study_task_item"),
        Index("idx_study_task_user_date", "user_id", "study_date", "status"),
        Index("idx_study_task_user_status_date", "user_id", "status", "study_date"),
        Index("idx_study_task_assignment_day", "assignment_id", "status", "day_index"),
        Index("idx_study_task_assignment_date", "assignment_id", "study_date"),
        Index("idx_study_task_plan_status", "plan_id", "status"),
        Index("idx_study_task_homework_status", "homework_id", "status"),
        Index("idx_study_task_session", "practice_session_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    assignment_id: Mapped[str] = mapped_column(
        ForeignKey("study_plan_assignments.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[str] = mapped_column(
        ForeignKey("study_plans.id", ondelete="RESTRICT"), nullable=False
    )
    plan_item_id: Mapped[Optional[str]] = mapped_column(String(36))
    homework_id: Mapped[str] = mapped_column(
        ForeignKey("classroom_homeworks.id", ondelete="RESTRICT"), nullable=False
    )
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    study_date: Mapped[date] = mapped_column(Date, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_title: Mapped[str] = mapped_column(String(200), nullable=False)
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_color: Mapped[str] = mapped_column(String(16), nullable=False)
    item_title: Mapped[str] = mapped_column(String(200), nullable=False)
    homework_version: Mapped[int] = mapped_column(Integer, nullable=False)
    homework_title: Mapped[str] = mapped_column(String(200), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    unit_id: Mapped[Optional[str]] = mapped_column(String(16))
    unit_title: Mapped[Optional[str]] = mapped_column(String(120))
    topic_id: Mapped[Optional[str]] = mapped_column(String(96))
    topic_title: Mapped[Optional[str]] = mapped_column(String(200))
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unavailable_question_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    answered_question_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    practice_session_id: Mapped[Optional[str]] = mapped_column(String(36))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class QaThread(Base):
    """A student's question about a question inside a study-calendar homework."""

    __tablename__ = "qa_threads"
    __table_args__ = (
        Index("idx_qa_thread_question", "subject_id", "question_id", "created_at"),
        Index("idx_qa_thread_student", "student_id", "last_reply_at"),
        Index("idx_qa_thread_last_reply", "last_reply_at"),
        Index("idx_qa_thread_admin_read", "admin_last_read_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    question_id: Mapped[str] = mapped_column(String(64), nullable=False)
    homework_id: Mapped[Optional[str]] = mapped_column(String(36))
    plan_title: Mapped[Optional[str]] = mapped_column(String(200))
    task_title: Mapped[Optional[str]] = mapped_column(String(200))
    homework_title: Mapped[Optional[str]] = mapped_column(String(200))
    question_stem: Mapped[Optional[str]] = mapped_column(Text)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    last_reply_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_student_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_teacher_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    student_last_read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    admin_last_read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )


class QaReply(Base):
    __tablename__ = "qa_replies"
    __table_args__ = (Index("idx_qa_reply_thread", "thread_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    thread_id: Mapped[str] = mapped_column(
        ForeignKey("qa_threads.id", ondelete="CASCADE"), nullable=False
    )
    author_type: Mapped[str] = mapped_column(String(16), nullable=False)
    student_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    admin_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
