from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class EmailCodeRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    purpose: Literal["register", "reset"]


class EmailRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=4, max_length=8)
    password: str = Field(min_length=8, max_length=128)


class EmailLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class EmailResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=4, max_length=8)
    password: str = Field(min_length=8, max_length=128)


class EmailBindCodeRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class EmailBindRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=4, max_length=8)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class WechatLoginRequest(BaseModel):
    code: str = Field(min_length=4, max_length=256)


class WechatBindRequest(BaseModel):
    code: str = Field(min_length=4, max_length=256)
    password: Optional[str] = Field(default=None, max_length=128)


class PracticeSessionCreate(BaseModel):
    source: Literal["topic", "unit", "wrong", "bookmark"]
    group_id: Optional[str] = None
    topic_id: Optional[str] = None
    count: int = Field(default=20, ge=1, le=100)
    restart: bool = False


class PracticeAnswerRequest(BaseModel):
    question_id: str
    selected_label: str = Field(min_length=1, max_length=4)


class PracticeFlagRequest(BaseModel):
    question_id: str
    flagged: bool


class PracticeFlushRequest(BaseModel):
    answers: list[PracticeAnswerRequest] = Field(default_factory=list, max_length=100)


class FlashcardReviewRequest(BaseModel):
    rating: Literal["known", "again"]


class UserProfilePatch(BaseModel):
    nickname: Optional[str] = Field(default=None, max_length=64)
    grade: Optional[str] = Field(default=None, max_length=32)
    region: Optional[str] = Field(default=None, max_length=64)
    target_score: Optional[int] = Field(default=None, ge=1, le=5)
    studied_psychology: Optional[bool] = None
    study_mode: Optional[Literal["school", "tutoring", "self", "not_yet"]] = None
    exam_time: Optional[Literal["2027", "2028", "undecided"]] = None
    complete_profile: bool = False


class AdminStudentPatch(BaseModel):
    teacher_note: Optional[str] = Field(default=None, max_length=5000)


class PaperPatch(BaseModel):
    year: Optional[int] = Field(default=None, ge=1990, le=2100)
    title: Optional[str] = Field(default=None, max_length=500)
    chinese_title: Optional[str] = Field(default=None, max_length=500)
    paper_type: Optional[str] = Field(default=None, max_length=32)


class QuestionOptionPatch(BaseModel):
    label: str = Field(min_length=1, max_length=4)
    content: str = Field(default="", max_length=5000)
    is_correct: bool = False
    explanation: Optional[str] = Field(default=None, max_length=10000)
    ai_explanation: Optional[str] = Field(default=None, max_length=10000)


class QuestionPatch(BaseModel):
    stem: Optional[str] = Field(default=None, max_length=20000)
    context: Optional[str] = Field(default=None, max_length=20000)
    answer_text: Optional[str] = Field(default=None, max_length=100000)
    answer_source: Optional[str] = Field(default=None, max_length=64)
    answer_confidence: Optional[str] = Field(default=None, max_length=64)
    options: Optional[list[QuestionOptionPatch]] = Field(default=None, max_length=5)


class QuestionStarsPatch(BaseModel):
    # ``null`` clears the rating.
    stars: Optional[int] = Field(default=None, ge=1, le=5)


class ConceptPatch(BaseModel):
    canonical_name: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = Field(default=None, max_length=10000)
    ap_unit: Optional[str] = Field(default=None, max_length=16)
    topic: Optional[str] = Field(default=None, max_length=200)
    status: Optional[str] = Field(default=None, max_length=32)
    weight: Optional[float] = Field(default=None, ge=0, le=1000)


class KnowledgePointPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=300)
    plain_en: Optional[str] = Field(default=None, max_length=10000)
    definition_quote: Optional[str] = Field(default=None, max_length=20000)
    subheading: Optional[str] = Field(default=None, max_length=500)
    status: Optional[str] = Field(default=None, max_length=32)
    weight: Optional[float] = Field(default=None, ge=0, le=1000)


class AdminQuestionCreate(BaseModel):
    subject_id: str = Field(default="psychology", min_length=1, max_length=64)
    paper_id: str = Field(min_length=1, max_length=64)
    section: Literal["MCQ"] = "MCQ"
    number: Optional[int] = Field(default=None, ge=1)
    stem: str = Field(min_length=1, max_length=20000)
    context: str = Field(default="", max_length=20000)
    answer_text: str = Field(default="", max_length=100000)
    answer_source: Optional[str] = Field(default=None, max_length=64)
    answer_confidence: Optional[str] = Field(default=None, max_length=64)
    options: list[QuestionOptionPatch] = Field(min_length=2, max_length=5)


class AdminConceptCreate(BaseModel):
    subject_id: str = Field(default="psychology", min_length=1, max_length=64)
    canonical_name: str = Field(min_length=1, max_length=300)
    definition: str = Field(min_length=1, max_length=10000)
    ap_unit: Optional[str] = Field(default=None, max_length=16)
    topic: Optional[str] = Field(default=None, max_length=200)


class AdminQuestionConceptLinkCreate(BaseModel):
    concept_id: str = Field(min_length=1, max_length=128)
    relation_type: Literal["core", "supporting", "confusable"] = "core"
    option_label: Optional[str] = Field(default=None, max_length=4)


class KnowledgeGraphTopicSave(BaseModel):
    unit_id: str = Field(min_length=1, max_length=16)
    topic_code: str = Field(min_length=1, max_length=16)
    tree: dict[str, Any]
    expected_revision: Optional[int] = Field(default=None, ge=0)


class KnowledgeGraphCustomConceptCreate(BaseModel):
    unit_id: str = Field(min_length=1, max_length=16)
    topic_code: Optional[str] = Field(default=None, max_length=16)
    name: str = Field(min_length=1, max_length=300)
    definition: str = Field(min_length=1, max_length=8000)


class AdminLoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class UserFlashcardCreate(BaseModel):
    term: str = Field(min_length=1, max_length=200)
    short_meaning: str = Field(min_length=1, max_length=500)
    detail_meaning: str = Field(default="", max_length=5000)


class UserFlashcardPatch(BaseModel):
    term: Optional[str] = Field(default=None, min_length=1, max_length=200)
    short_meaning: Optional[str] = Field(default=None, min_length=1, max_length=500)
    detail_meaning: Optional[str] = Field(default=None, max_length=5000)


class NoteUpsertRequest(BaseModel):
    target_type: Literal["question", "concept", "kp"] = "question"
    target_id: str
    content: str = Field(min_length=0, max_length=20000)


class NotePatchRequest(BaseModel):
    content: str = Field(min_length=0, max_length=20000)


class QuestionReportRequest(BaseModel):
    question_id: str
    reason: Literal["wrong_answer", "typo", "bad_explanation", "image_missing", "other"]
    detail: Optional[str] = Field(default=None, max_length=2000)
    attempt_id: Optional[str] = None
    practice_session_id: Optional[str] = None
    selected_label: Optional[str] = None


class ActivationCodeBatchCreate(BaseModel):
    scope_type: Literal["all", "subject"] = "subject"
    subject_id: Optional[str] = None
    duration_days: Optional[int] = Field(default=None, ge=1, le=3650)
    expires_on: Optional[date] = None
    count: int = Field(default=10, ge=1, le=500)
    note: Optional[str] = Field(default=None, max_length=1000)


class ActivationCodeRedeem(BaseModel):
    code: str = Field(min_length=1, max_length=64)


class AttemptCreate(BaseModel):
    paper_id: str
    mode: Literal["mcq", "frq", "full"]
    frq_form: Optional[str] = None
    restart: bool = False


class AttemptAnswerItem(BaseModel):
    question_id: str
    selected_label: Optional[str] = Field(default=None, max_length=4)
    frq_text: Optional[str] = Field(default=None, max_length=50000)
    flagged: Optional[bool] = None
    time_spent_ms: Optional[int] = Field(default=None, ge=0)


class AttemptAnswersRequest(BaseModel):
    answers: list[AttemptAnswerItem] = Field(default_factory=list, max_length=100)


class FrqScoreItem(BaseModel):
    question_id: str
    part_id: str
    points: int = Field(ge=0, le=20)


class FrqScoresRequest(BaseModel):
    scores: list[FrqScoreItem] = Field(default_factory=list, max_length=200)


class HomeworkCreate(BaseModel):
    subject_id: Optional[str] = None
    title: str = Field(min_length=1, max_length=200)
    note: Optional[str] = Field(default=None, max_length=5000)
    unit_id: Optional[str] = Field(default=None, max_length=16)
    topic_id: Optional[str] = Field(default=None, max_length=96)
    question_ids: list[str] = Field(min_length=1, max_length=300)


class HomeworkUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    note: Optional[str] = Field(default=None, max_length=5000)
    unit_id: Optional[str] = Field(default=None, max_length=16)
    topic_id: Optional[str] = Field(default=None, max_length=96)
    question_ids: Optional[list[str]] = Field(default=None, max_length=300)


class HomeworkQuestionsReplace(BaseModel):
    question_ids: list[str] = Field(min_length=1, max_length=300)


class StudyPlanCreate(BaseModel):
    subject_id: Optional[str] = None
    title: str = Field(min_length=1, max_length=200)
    note: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=32)
    color: str = Field(default="primary", max_length=16)


class StudyPlanUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    note: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=32)
    color: Optional[str] = Field(default=None, max_length=16)
    status: Optional[Literal["active", "archived"]] = None


class StudyPlanItemInput(BaseModel):
    homework_id: str = Field(min_length=1, max_length=36)
    title: Optional[str] = Field(default=None, max_length=200)


class StudyPlanItemsReplace(BaseModel):
    items: list[StudyPlanItemInput] = Field(max_length=500)


class StudyPlanAssignPreview(BaseModel):
    start_date: date
    end_date: date


class StudyPlanAssign(BaseModel):
    student_ids: list[str] = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    note: Optional[str] = Field(default=None, max_length=5000)


class StudyAssignmentCancel(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)
