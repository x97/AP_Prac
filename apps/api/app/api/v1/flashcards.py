from __future__ import annotations

import random
from datetime import timedelta
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.schemas import FlashcardReviewRequest
from app.content.store import ContentStore
from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import get_current_user, get_store
from app.core.errors import AppError
from app.core.time import as_utc, shanghai_date, utcnow
from app.users.models import FlashcardReview, User

router = APIRouter(prefix="/flashcards", tags=["flashcards"])

# Leitner-style spacing. A card starts at box 0; "known" promotes it.
BOX_DAYS = {1: 1, 2: 2, 3: 4, 4: 7, 5: 15}
AGAIN_MINUTES = 10
SAME_DAY_MINUTES = 30
STAR_MIN_WEIGHT = {0: 0.0, 1: 0.0, 2: 30.0, 3: 45.0, 4: 60.0, 5: 75.0}


def _stars(weight: float) -> int:
    if weight >= 75:
        return 5
    if weight >= 60:
        return 4
    if weight >= 45:
        return 3
    if weight >= 30:
        return 2
    return 1


def _parse_units(units: Optional[str]) -> list[str]:
    return [part.strip() for part in (units or "").split(",") if part.strip()]


def _pool_for(
    store: ContentStore,
    *,
    unit_id: Optional[str] = None,
    units: Optional[str] = None,
    min_stars: int = 0,
) -> list[dict[str, Any]]:
    """Resolve the concept pool for one unit or a comma-separated unit list.

    ``units`` wins when present so the mini-program can keep its multi-unit
    selector; web callers keep using the single ``unit_id`` path unchanged.
    """
    min_weight = STAR_MIN_WEIGHT.get(min_stars, 0.0)
    picked = _parse_units(units)
    if picked:
        merged: dict[str, dict[str, Any]] = {}
        for unit in picked:
            for item in store.flashcard_pool(unit, min_weight):
                merged.setdefault(str(item["cluster_id"]), item)
        return sorted(
            merged.values(),
            key=lambda item: (
                -float(item.get("weight") or 0),
                str(item["cluster_id"]),
            ),
        )
    filter_unit = None if unit_id in (None, "", "all") else unit_id
    return store.flashcard_pool(filter_unit, min_weight)


def _card_payload(detail: dict[str, Any], review: Optional[FlashcardReview]) -> dict[str, Any]:
    weight = float(detail.get("weight") or 0)
    return {
        "concept_id": detail["cluster_id"],
        "term": detail.get("canonical_name") or "",
        "ipa": detail.get("ipa"),
        "audio_url": detail.get("audio_url"),
        "definition": detail.get("plain_en") or "",
        "quote": detail.get("definition_quote") or "",
        "topic": detail.get("topic"),
        "ap_unit": detail.get("ap_unit"),
        "book_title": detail.get("book_title"),
        "section_heading": detail.get("section_heading"),
        "weight": weight,
        "weight_tier": detail.get("weight_tier"),
        "stars": _stars(weight),
        "box": review.box if review else 0,
        "seen_count": review.seen_count if review else 0,
        "known_count": review.known_count if review else 0,
        "last_rating": review.last_rating if review else None,
        "next_due_at": review.next_due_at if review else None,
    }


@router.get("/preview")
def preview_cards(
    limit: int = Query(default=20, ge=1, le=50),
    units: Optional[str] = Query(default=None),
    store: ContentStore = Depends(get_store),
):
    """Public sample deck for the landing page.

    It deliberately returns no review state and accepts no rating writes.
    ``units`` is an optional comma-separated list (``methods,1,2``) so the
    mini-program can scope the sample deck to the Units a student picked.
    """
    pool = _pool_for(store, units=units)
    if not pool:
        return {
            "cards": [],
            "stats": {"total": 0, "due": 0, "new": 0, "reviewed": 0},
            "ahead": False,
        }

    # The landing page samples from high-weight concepts; a Unit-scoped deck
    # used by the mini-program may draw from the full filtered pool so long
    # study sessions can keep loading fresh cards.
    candidates = pool if units else pool[: min(len(pool), 200)]
    chosen_cards = random.sample(candidates, min(limit, len(candidates)))
    chosen = [item["cluster_id"] for item in chosen_cards]
    details = {item["cluster_id"]: item for item in store.get_flashcard_concepts(chosen)}
    cards = [
        _card_payload(details[concept_id], None)
        for concept_id in chosen
        if concept_id in details
    ]
    return {
        "cards": cards,
        "stats": {
            "total": len(pool),
            "due": 0,
            "new": len(cards),
            "reviewed": 0,
        },
        "ahead": False,
    }


@router.get("")
def list_cards(
    unit_id: Optional[str] = None,
    min_stars: int = Query(default=0, ge=0, le=5),
    limit: int = Query(default=20, ge=1, le=50),
    scope: Literal["all", "today"] = Query(default="all"),
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    filter_unit = None if unit_id in (None, "", "all") else unit_id
    pool = store.flashcard_pool(filter_unit, STAR_MIN_WEIGHT.get(min_stars, 0.0))
    all_ids = [item["cluster_id"] for item in pool]
    if not all_ids:
        return {
            "cards": [],
            "stats": {"total": 0, "due": 0, "new": 0, "reviewed": 0},
            "ahead": False,
        }

    known_ids = set(all_ids)
    reviews = {
        row.concept_id: row
        for row in db.scalars(select(FlashcardReview).where(FlashcardReview.user_id == user.id))
        if row.concept_id in known_ids
    }
    now = utcnow()
    if scope == "today":
        today = shanghai_date(now)
        today_ids = [
            concept_id
            for concept_id in all_ids
            if reviews.get(concept_id)
            and reviews[concept_id].last_reviewed_at
            and shanghai_date(reviews[concept_id].last_reviewed_at) == today
        ]
        today_ids.sort(
            key=lambda concept_id: as_utc(reviews[concept_id].last_reviewed_at)
        )
        chosen = today_ids[:limit]
        details = {
            item["cluster_id"]: item
            for item in store.get_flashcard_concepts(chosen)
        }
        cards = [
            _card_payload(details[concept_id], reviews.get(concept_id))
            for concept_id in chosen
            if concept_id in details
        ]
        return {
            "cards": cards,
            "stats": {
                "total": len(today_ids),
                "due": len(today_ids),
                "new": 0,
                "reviewed": len(reviews),
            },
            "ahead": False,
            "scope": "today",
        }

    due: list[str] = []
    new: list[str] = []
    # The pool is already ordered by concept weight, so high-importance cards
    # show up first inside both the due and new queues.
    for concept_id in all_ids:
        review = reviews.get(concept_id)
        if review is None:
            new.append(concept_id)
        elif review.next_due_at is None or as_utc(review.next_due_at) <= now:
            due.append(concept_id)

    chosen = (due + new)[:limit]
    ahead = False
    if len(chosen) < limit:
        rest = [concept_id for concept_id in all_ids if concept_id not in chosen]
        rest.sort(
            key=lambda concept_id: (
                as_utc(reviews[concept_id].next_due_at)
                if reviews.get(concept_id) and reviews[concept_id].next_due_at
                else now
            )
        )
        fill = rest[: limit - len(chosen)]
        chosen.extend(fill)
        ahead = bool(fill)

    details = {item["cluster_id"]: item for item in store.get_flashcard_concepts(chosen)}
    cards = [
        _card_payload(details[concept_id], reviews.get(concept_id))
        for concept_id in chosen
        if concept_id in details
    ]
    return {
        "cards": cards,
        "stats": {
            "total": len(all_ids),
            "due": len(due),
            "new": len(new),
            "reviewed": len(reviews),
        },
        "ahead": ahead,
    }


@router.get("/next")
def next_card(
    unit_id: Optional[str] = None,
    units: Optional[str] = Query(default=None),
    min_stars: int = Query(default=0, ge=0, le=5),
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    """Continuous-study queue: one due/new card at a time.

    New cards are capped per Shanghai calendar day. Due cards always take
    priority, so a card that comes due later in the same session naturally
    returns to the queue.
    """
    pool = _pool_for(store, unit_id=unit_id, units=units, min_stars=min_stars)
    all_ids = [item["cluster_id"] for item in pool]
    if not all_ids:
        return {
            "card": None,
            "reason": None,
            "due": 0,
            "new_today": 0,
            "new_limit": int(get_settings().flashcard_new_per_day),
            "new_remaining": 0,
            "new_limit_reached": False,
            "reviewed_today": 0,
            "total": 0,
            "caught_up": True,
            "next_due_at": None,
        }

    known_ids = set(all_ids)
    reviews_all = {
        row.concept_id: row
        for row in db.scalars(
            select(FlashcardReview).where(FlashcardReview.user_id == user.id)
        )
    }
    reviews = {
        concept_id: review
        for concept_id, review in reviews_all.items()
        if concept_id in known_ids
    }
    now = utcnow()
    today = shanghai_date(now)
    new_today = sum(
        1
        for review in reviews_all.values()
        if review.created_at and shanghai_date(review.created_at) == today
    )
    reviewed_today = sum(
        1
        for review in reviews.values()
        if review.last_reviewed_at
        and shanghai_date(review.last_reviewed_at) == today
    )
    new_limit = max(1, int(get_settings().flashcard_new_per_day))
    new_remaining = max(0, new_limit - new_today)

    due: list[str] = []
    new: list[str] = []
    for concept_id in all_ids:
        review = reviews.get(concept_id)
        if review is None:
            new.append(concept_id)
        elif review.next_due_at is None or as_utc(review.next_due_at) <= now:
            due.append(concept_id)

    due.sort(
        key=lambda concept_id: (
            as_utc(reviews[concept_id].next_due_at)
            if reviews[concept_id].next_due_at
            else now
        )
    )

    chosen: Optional[str] = None
    reason: Optional[str] = None
    if due:
        chosen = due[0]
        reason = "due"
    elif new and new_remaining > 0:
        chosen = new[0]
        reason = "new"

    card = None
    if chosen is not None:
        details = {
            item["cluster_id"]: item
            for item in store.get_flashcard_concepts([chosen])
        }
        if chosen in details:
            card = _card_payload(details[chosen], reviews.get(chosen))

    future_due = sorted(
        as_utc(review.next_due_at)
        for review in reviews.values()
        if review.next_due_at and as_utc(review.next_due_at) > now
    )
    return {
        "card": card,
        "reason": reason,
        "due": len(due),
        "new_today": new_today,
        "new_limit": new_limit,
        "new_remaining": new_remaining,
        "new_limit_reached": bool(new) and new_remaining == 0,
        "reviewed_today": reviewed_today,
        "total": len(all_ids),
        "caught_up": card is None,
        "next_due_at": future_due[0].isoformat() if future_due else None,
    }


@router.get("/unfamiliar")
def unfamiliar_cards(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    """Cards whose latest rating is ``again`` — still unfamiliar right now.

    This is a current-state list, not a history: rating a card ``known``
    updates ``last_rating`` and removes it from the result. Reviews that
    point at concepts no longer present in the active content release are
    ignored so the count matches what the study queue can serve.
    """
    pool_ids = {str(item["cluster_id"]) for item in store.flashcard_pool()}
    rows = [
        row
        for row in db.scalars(
            select(FlashcardReview).where(
                FlashcardReview.user_id == user.id,
                FlashcardReview.last_rating == "again",
            )
        )
        if str(row.concept_id) in pool_ids
    ]
    rows.sort(
        key=lambda row: (
            -as_utc(row.last_reviewed_at or row.updated_at).timestamp(),
            str(row.concept_id),
        )
    )
    total = len(rows)
    page = rows[offset : offset + limit]
    details = {
        item["cluster_id"]: item
        for item in store.get_flashcard_concepts([row.concept_id for row in page])
    }
    cards: list[dict[str, Any]] = []
    for row in page:
        detail = details.get(row.concept_id)
        if detail is None:
            continue
        payload = _card_payload(detail, row)
        payload["last_reviewed_at"] = (
            as_utc(row.last_reviewed_at).isoformat(timespec="milliseconds")
            if row.last_reviewed_at
            else None
        )
        cards.append(payload)
    return {
        "cards": cards,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(cards) < total,
    }


@router.post("/{concept_id}/review")
def review_card(
    concept_id: str,
    body: FlashcardReviewRequest,
    db: Session = Depends(get_db),
    store: ContentStore = Depends(get_store),
    user: User = Depends(get_current_user),
):
    detail = store.get_flashcard_concepts([concept_id])
    if not detail:
        raise AppError(404, "CARD_NOT_FOUND", "卡片不存在")
    now = utcnow()
    review = db.get(FlashcardReview, (user.id, concept_id))
    if not review:
        review = FlashcardReview(
            user_id=user.id,
            concept_id=concept_id,
            box=0,
            seen_count=0,
            known_count=0,
            created_at=now,
        )
        db.add(review)

    if body.rating == "known":
        if (review.box or 0) == 0 and (review.known_count or 0) == 0:
            # First success for a brand-new card: bring it back later today
            # before promoting it to the 1-day box.
            review.next_due_at = now + timedelta(minutes=SAME_DAY_MINUTES)
        else:
            review.box = min(5, (review.box or 0) + 1)
            review.next_due_at = now + timedelta(days=BOX_DAYS[review.box])
        review.known_count += 1
    else:
        # A lapse goes back to the new-card box. The next "known" then starts
        # again at 1 day instead of jumping straight to 2 days.
        review.box = 0
        review.next_due_at = now + timedelta(minutes=AGAIN_MINUTES)

    review.seen_count += 1
    review.last_rating = body.rating
    review.last_reviewed_at = now
    review.updated_at = now
    db.commit()
    return {
        "concept_id": concept_id,
        "rating": body.rating,
        "box": review.box,
        "seen_count": review.seen_count,
        "known_count": review.known_count,
        "last_reviewed_at": review.last_reviewed_at,
        "next_due_at": review.next_due_at,
    }
