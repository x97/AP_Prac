from __future__ import annotations

from datetime import timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.schemas import (
    FlashcardReviewRequest,
    UserFlashcardCreate,
    UserFlashcardPatch,
)
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.time import as_utc, shanghai_date, utcnow
from app.users.models import User, UserFlashcard

router = APIRouter(prefix="/flashcards/custom", tags=["flashcards"])

MAX_CUSTOM_CARDS = 200
# Keep the user-card schedule identical to the official concept cards.
BOX_DAYS = {1: 1, 2: 2, 3: 4, 4: 7, 5: 15}
AGAIN_MINUTES = 10
SAME_DAY_MINUTES = 30


def _manage_payload(card: UserFlashcard) -> dict[str, Any]:
    return {
        "id": card.id,
        "term": card.term,
        "short_meaning": card.short_meaning,
        "detail_meaning": card.detail_meaning or "",
        "box": card.box,
        "seen_count": card.seen_count,
        "known_count": card.known_count,
        "last_rating": card.last_rating,
        "last_reviewed_at": card.last_reviewed_at,
        "next_due_at": card.next_due_at,
        "created_at": card.created_at,
        "updated_at": card.updated_at,
    }


def _study_payload(card: UserFlashcard) -> dict[str, Any]:
    """Match the official card shape so the study UI can be reused."""
    return {
        "concept_id": card.id,
        "term": card.term,
        "ipa": None,
        "audio_url": None,
        "definition": card.short_meaning,
        "quote": card.detail_meaning or "",
        "topic": "My Cards",
        "ap_unit": None,
        "book_title": None,
        "section_heading": None,
        "weight": 0,
        "weight_tier": None,
        "stars": 0,
        "box": card.box,
        "seen_count": card.seen_count,
        "known_count": card.known_count,
        "last_rating": card.last_rating,
        "next_due_at": card.next_due_at,
    }


def _clean_text(value: str) -> str:
    return value.strip()


def _get_owned_card(db: Session, user: User, card_id: str) -> UserFlashcard:
    card = db.get(UserFlashcard, card_id)
    if not card or card.user_id != user.id:
        raise AppError(404, "CARD_NOT_FOUND", "记忆卡片不存在")
    return card


@router.get("")
def list_cards(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cards = list(
        db.scalars(
            select(UserFlashcard)
            .where(UserFlashcard.user_id == user.id)
            .order_by(UserFlashcard.updated_at.desc())
        )
    )
    return {
        "cards": [_manage_payload(card) for card in cards],
        "total": len(cards),
        "limit": MAX_CUSTOM_CARDS,
    }


@router.post("")
def create_card(
    body: UserFlashcardCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    term = _clean_text(body.term)
    short_meaning = _clean_text(body.short_meaning)
    detail_meaning = _clean_text(body.detail_meaning)
    if not term or not short_meaning:
        raise AppError(400, "CARD_FIELDS_REQUIRED", "卡片名称和简短意思不能为空")

    total = (
        db.scalar(
            select(func.count()).select_from(UserFlashcard).where(UserFlashcard.user_id == user.id)
        )
        or 0
    )
    if total >= MAX_CUSTOM_CARDS:
        raise AppError(
            409,
            "FLASHCARD_LIMIT",
            f"最多创建 {MAX_CUSTOM_CARDS} 张自定义记忆卡片",
        )

    now = utcnow()
    card = UserFlashcard(
        user_id=user.id,
        term=term,
        short_meaning=short_meaning,
        detail_meaning=detail_meaning,
        box=0,
        seen_count=0,
        known_count=0,
        created_at=now,
        updated_at=now,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return _manage_payload(card)


@router.get("/deck")
def get_deck(
    limit: int = Query(default=20, ge=1, le=50),
    scope: Literal["all", "today"] = Query(default="all"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cards = list(
        db.scalars(
            select(UserFlashcard)
            .where(UserFlashcard.user_id == user.id)
            .order_by(UserFlashcard.created_at.asc())
        )
    )
    now = utcnow()
    if scope == "today":
        today = shanghai_date(now)
        today_cards = [
            card
            for card in cards
            if card.last_reviewed_at
            and shanghai_date(card.last_reviewed_at) == today
        ]
        today_cards.sort(key=lambda card: as_utc(card.last_reviewed_at))
        chosen = today_cards[:limit]
        return {
            "cards": [_study_payload(card) for card in chosen],
            "stats": {
                "total": len(today_cards),
                "due": len(today_cards),
                "new": 0,
                "reviewed": sum(1 for card in cards if card.seen_count > 0),
            },
            "ahead": False,
            "scope": "today",
        }

    due: list[UserFlashcard] = []
    new: list[UserFlashcard] = []
    for card in cards:
        if card.next_due_at is None:
            new.append(card)
        elif as_utc(card.next_due_at) <= now:
            due.append(card)

    due.sort(key=lambda card: as_utc(card.next_due_at) if card.next_due_at else now)
    chosen = (due + new)[:limit]
    ahead = False
    if len(chosen) < limit:
        chosen_ids = {card.id for card in chosen}
        rest = [card for card in cards if card.id not in chosen_ids]
        rest.sort(key=lambda card: as_utc(card.next_due_at) if card.next_due_at else now)
        fill = rest[: limit - len(chosen)]
        chosen.extend(fill)
        ahead = bool(fill)

    reviewed = sum(1 for card in cards if card.seen_count > 0)
    return {
        "cards": [_study_payload(card) for card in chosen],
        "stats": {
            "total": len(cards),
            "due": len(due),
            "new": len(new),
            "reviewed": reviewed,
        },
        "ahead": ahead,
    }


@router.get("/next")
def next_card(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Continuous-study queue for a user's own cards (no daily new-card cap)."""
    cards = list(
        db.scalars(
            select(UserFlashcard)
            .where(UserFlashcard.user_id == user.id)
            .order_by(UserFlashcard.created_at.asc())
        )
    )
    now = utcnow()
    due: list[UserFlashcard] = []
    new: list[UserFlashcard] = []
    reviewed_today = 0
    today = shanghai_date(now)
    for card in cards:
        if card.last_reviewed_at and shanghai_date(card.last_reviewed_at) == today:
            reviewed_today += 1
        if card.next_due_at is None:
            new.append(card)
        elif as_utc(card.next_due_at) <= now:
            due.append(card)

    due.sort(key=lambda card: as_utc(card.next_due_at) if card.next_due_at else now)
    chosen = due[0] if due else (new[0] if new else None)
    future_due = sorted(
        as_utc(card.next_due_at)
        for card in cards
        if card.next_due_at and as_utc(card.next_due_at) > now
    )
    return {
        "card": _study_payload(chosen) if chosen else None,
        "reason": "due" if due else ("new" if new else None),
        "due": len(due),
        "new_today": 0,
        "new_limit": len(new),
        "new_remaining": len(new),
        "new_limit_reached": False,
        "reviewed_today": reviewed_today,
        "total": len(cards),
        "caught_up": chosen is None,
        "next_due_at": future_due[0].isoformat() if future_due else None,
    }


@router.patch("/{card_id}")
def update_card(
    card_id: str,
    body: UserFlashcardPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    card = _get_owned_card(db, user, card_id)
    updates = body.model_dump(exclude_unset=True)
    if "term" in updates and updates["term"] is not None:
        term = _clean_text(updates["term"])
        if not term:
            raise AppError(400, "CARD_FIELDS_REQUIRED", "卡片名称不能为空")
        card.term = term
    if "short_meaning" in updates and updates["short_meaning"] is not None:
        short_meaning = _clean_text(updates["short_meaning"])
        if not short_meaning:
            raise AppError(400, "CARD_FIELDS_REQUIRED", "简短意思不能为空")
        card.short_meaning = short_meaning
    if "detail_meaning" in updates and updates["detail_meaning"] is not None:
        card.detail_meaning = _clean_text(updates["detail_meaning"])
    card.updated_at = utcnow()
    db.commit()
    db.refresh(card)
    return _manage_payload(card)


@router.delete("/{card_id}")
def delete_card(
    card_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    card = _get_owned_card(db, user, card_id)
    db.delete(card)
    db.commit()
    return {"ok": True, "id": card_id}


@router.post("/{card_id}/review")
def review_card(
    card_id: str,
    body: FlashcardReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    card = _get_owned_card(db, user, card_id)
    now = utcnow()
    if body.rating == "known":
        if (card.box or 0) == 0 and (card.known_count or 0) == 0:
            # Same-day reinforcement for a brand-new custom card.
            card.next_due_at = now + timedelta(minutes=SAME_DAY_MINUTES)
        else:
            card.box = min(5, (card.box or 0) + 1)
            card.next_due_at = now + timedelta(days=BOX_DAYS[card.box])
        card.known_count += 1
    else:
        card.box = 0
        card.next_due_at = now + timedelta(minutes=AGAIN_MINUTES)

    card.seen_count += 1
    card.last_rating = body.rating
    card.last_reviewed_at = now
    card.updated_at = now
    db.commit()
    return {
        "concept_id": card.id,
        "rating": body.rating,
        "box": card.box,
        "seen_count": card.seen_count,
        "known_count": card.known_count,
        "last_reviewed_at": card.last_reviewed_at,
        "next_due_at": card.next_due_at,
    }
