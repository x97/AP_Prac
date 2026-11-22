from __future__ import annotations

from app.core.security import mask_email, mask_phone
from app.users.models import User


def user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "email_masked": mask_email(user.email),
        "email_verified": bool(user.email_verified_at),
        "has_password": bool(user.password_hash),
        "phone_masked": mask_phone(user.phone),
        "nickname": user.nickname,
        "grade": user.grade,
        "region": user.region,
        "target_score": user.target_score,
        "studied_psychology": user.studied_psychology,
        "study_mode": user.study_mode,
        "exam_time": user.exam_time,
        "profile_completed": user.profile_completed_at is not None,
        "role": user.role,
    }
