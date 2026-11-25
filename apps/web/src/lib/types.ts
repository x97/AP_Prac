export type User = {
  id: string;
  email: string | null;
  email_masked: string | null;
  email_verified: boolean;
  has_password: boolean;
  phone_masked: string | null;
  nickname: string | null;
  grade: string | null;
  region: string | null;
  target_score: number | null;
  studied_psychology: boolean | null;
  study_mode: string | null;
  exam_time: string | null;
  profile_completed: boolean;
  role: string;
};

export type PracticeGroup = {
  group_id: string;
  unit_id: string;
  title: string;
  title_en: string;
  status: string;
  bundle_paper_id: string | null;
  topic_count: number;
  question_count: number;
  total: number;
  answered: number;
  correct: number;
  accuracy: number | null;
  locked?: boolean;
};

export type SubjectEntitlement = {
  subject_id: string;
  name: string;
  name_zh: string;
  enabled: boolean;
  active: boolean;
  expires_at: string | null;
  source: string | null;
  free_unit_ids: string[];
  free_paper_ids: string[];
};

export type Topic = {
  topic_id: string;
  group_id: string;
  unit_id: string;
  code: string;
  title_zh: string;
  title_en: string;
  kind: string;
  sort_order: number;
  question_count: number;
  total: number;
  locked?: boolean;
  answered: number;
  correct: number;
  accuracy: number | null;
  concepts?: Concept[];
  current_session?: PracticeSessionSummary | null;
};

export type PracticeSessionSummary = {
  id: string;
  status: string;
  answered: number;
  total: number;
  correct: number;
  next_index: number;
  score: number | null;
  updated_at: string;
  submitted_at: string | null;
};

export type Concept = {
  concept_id: string;
  relation_type?: string;
  option_label?: string | null;
  canonical_name: string;
  topic?: string;
  ap_unit?: string;
  weight?: number;
  plain_en?: string;
  definition_quote?: string;
  section_heading?: string;
  book_title?: string;
  confidence?: number;
};

export type Asset = {
  asset_id: string;
  kind: string;
  option_label: string | null;
  url: string;
  page: number | null;
  bbox: string | null;
  description?: string | null;
};

export type Option = {
  label: string;
  content: string;
  sort_order: number;
  asset_urls: string[];
  is_correct?: boolean;
  explanation?: string;
  ai_explanation?: string;
};

export type Question = {
  question_id: string;
  paper_id: string;
  section: string;
  number: number;
  form: string | null;
  display_number: number;
  stem: string;
  context: string;
  options: Option[];
  assets: Asset[];
  answer_source?: string | null;
  answer_confidence?: string | null;
  selected_label?: string | null;
  is_correct?: boolean | null;
  flagged?: boolean;
  answered_at?: string | null;
  feedback?: Feedback;
  explanation?: string;
  explanation_source?: string | null;
  correct_label?: string | null;
  concepts?: Concept[];
  answer_text?: string | null;
};

export type Feedback = Question & {
  explanation?: string;
  explanation_source?: string | null;
  concepts?: Concept[];
  correct_label?: string | null;
  answer_text?: string | null;
};

export type SessionPayload = {
  session: {
    id: string;
    source: string;
    group_id: string | null;
    topic_id: string | null;
    status: string;
    score: number | null;
    total: number | null;
    answered: number;
    total_questions: number;
    next_index: number;
    started_at: string;
    submitted_at: string | null;
  };
  questions: Question[];
  topic_concepts: Concept[];
  progress: {
    answered: number;
    correct: number;
    total: number;
    accuracy: number | null;
  };
  homework?: StudyHomeworkBlock;
};

export type SessionTopicContext = {
  topic: Pick<
    Topic,
    "topic_id" | "group_id" | "unit_id" | "code" | "title_zh" | "title_en"
  > | null;
  concepts: Concept[];
  inferred?: boolean;
};

export type Paper = {
  paper_id: string;
  year: number;
  title: string | null;
  chinese_title: string | null;
  paper_type: string;
  question_count: number;
  format_code: string | null;
  mcq_count: number | null;
  mcq_minutes: number | null;
  frq_count: number | null;
  frq_minutes: number | null;
  frq_forms: string[];
  section_order: string[];
  is_complete: number;
  frq_rubric_complete: number;
  expected_frq_points: number;
  notes: string;
  modes: string[];
  frq_warning: string | null;
  active_attempts?: ActiveAttempt[];
  locked?: boolean;
};

export type ActiveAttempt = {
  id: string;
  mode: string;
  frq_form: string | null;
  status: string;
  current_section: string;
  section_status: string | null;
  answered: number;
  total: number;
  mcq_score: number | null;
  mcq_total: number | null;
  frq_score: number | null;
  frq_total: number | null;
  updated_at: string;
};

export type QuestionSourceInfo = {
  paper_id?: string;
  paper_title?: string | null;
  paper_title_en?: string | null;
  paper_type?: string | null;
  paper_year?: number | null;
  section?: string;
  display_number?: number;
  stem?: string;
  unit_id?: string | null;
  topic_id?: string | null;
  topic_code?: string | null;
  topic_title_zh?: string | null;
  topic_title_en?: string | null;
  group_id?: string | null;
  group_title?: string | null;
  group_title_en?: string | null;
};

export type WrongQuestion = {
  question_id: string;
  wrong_count: number;
  correct_streak: number;
  mastery: string;
  last_wrong_at: string | null;
  mastered_at: string | null;
  unit_id: string | null;
  topic_id: string | null;
} & QuestionSourceInfo;

export type Bookmark = QuestionSourceInfo & {
  question_id: string;
  created_at: string;
};

export type Note = {
  id: string;
  target_type: string;
  target_id: string;
  content: string;
  created_at: string;
  updated_at: string;
  question?: QuestionSourceInfo & {
    question_id: string;
    stem: string;
    display_number: number;
    paper_id: string;
    section: string;
  };
};

export type Dashboard = {
  user: User;
  overview: {
    answered: number;
    correct: number;
    accuracy: number | null;
    streak_days: number;
    total_questions: number;
  };
  activity: Array<{
    day: string;
    answered: number;
    correct: number;
  }>;
  activity_summary: {
    days: number;
    active_days: number;
    total_answered: number;
  };
  units: PracticeGroup[];
  continue: {
    type: string;
    id: string;
    source?: string;
    group_id?: string | null;
    topic_id?: string | null;
    paper_id?: string;
    mode?: string;
    status: string;
    score?: number | null;
    total?: number | null;
    answered?: number;
    total_questions?: number;
    mcq_score?: number | null;
    mcq_total?: number | null;
    frq_score?: number | null;
    frq_total?: number | null;
    group_title?: string | null;
    group_title_en?: string | null;
    topic_title_zh?: string | null;
    topic_title_en?: string | null;
    topic_code?: string | null;
    paper_title?: string | null;
    paper_title_en?: string | null;
    paper_year?: number | null;
    paper_type?: string | null;
    updated_at: string;
  } | null;
  recent: Array<{
    type: string;
    id: string;
    source?: string;
    group_id?: string | null;
    topic_id?: string | null;
    paper_id?: string;
    mode?: string;
    status: string;
    score?: number | null;
    total?: number | null;
    answered?: number;
    total_questions?: number;
    mcq_score?: number | null;
    mcq_total?: number | null;
    frq_score?: number | null;
    frq_total?: number | null;
    group_title?: string | null;
    group_title_en?: string | null;
    topic_title_zh?: string | null;
    topic_title_en?: string | null;
    topic_code?: string | null;
    paper_title?: string | null;
    paper_title_en?: string | null;
    paper_year?: number | null;
    paper_type?: string | null;
    created_at: string;
  }>;
};

export type AttemptAnswer = {
  question_id: string;
  selected_label: string | null;
  flagged: boolean;
  frq_text: string | null;
  late: boolean;
  server_saved_at: string;
};

export type AttemptState = {
  attempt: {
    id: string;
    paper_id: string;
    mode: string;
    frq_form: string | null;
    status: string;
    current_section: string | null;
    mcq_score: number | null;
    mcq_total: number | null;
    frq_score: number | null;
    frq_total: number | null;
  };
  section: {
    name: string;
    status: string;
    started_at: string | null;
    expires_at: string | null;
    submitted_at: string | null;
    finalized_reason: string | null;
    score: number | null;
    total: number | null;
    paused?: boolean;
  };
  can_start: boolean;
  paused?: boolean;
  server_time: string;
  remaining_ms: number | null;
  questions: Question[];
  answers: AttemptAnswer[];
};

export type RubricPart = {
  part_id: string;
  label: string;
  title: string | null;
  max_points: number;
  criteria?: string;
  criteria_json?: Array<{ points: number; criterion: string }> | null;
  decision_rules?: string | null;
  examples_positive_json?: string[] | null;
  examples_negative_json?: string[] | null;
  sort_order: number;
};

export type FrqGuidelines = {
  question_id: string;
  answer_text: string | null;
  rubric: {
    rubric_id: string;
    total_points: number;
    general_considerations: string | null;
    format: string;
  } | null;
  parts: RubricPart[];
};

export type FrqReviewItem = Question & {
  frq_text: string;
  guidelines: FrqGuidelines;
  scores: Array<{ part_id: string; points: number; max_points: number }>;
};

export type AttemptReview = {
  attempt: {
    id: string;
    paper_id: string;
    mode: string;
    status: string;
    frq_form: string | null;
    mcq_score: number | null;
    mcq_total: number | null;
    frq_score: number | null;
    frq_total: number | null;
  };
  mcq_items: Question[];
  frq_items: FrqReviewItem[];
  score: number | null;
  total: number | null;
};

export type PracticeHistoryItem = {
  id: string;
  source: string;
  group_id: string | null;
  topic_id: string | null;
  status: string;
  score: number | null;
  total: number | null;
  total_questions: number;
  answered: number;
  correct: number;
  accuracy: number | null;
  group_title: string | null;
  group_title_en: string | null;
  topic_title_zh: string | null;
  topic_title_en: string | null;
  topic_code: string | null;
  started_at: string;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AttemptHistoryItem = {
  id: string;
  paper_id: string;
  mode: string;
  frq_form: string | null;
  status: string;
  current_section: string | null;
  mcq_score: number | null;
  mcq_total: number | null;
  frq_score: number | null;
  frq_total: number | null;
  paper_title: string | null;
  paper_title_en: string | null;
  paper_year: number | null;
  paper_type: string | null;
  started_at: string;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Flashcard = {
  concept_id: string;
  term: string;
  ipa?: string | null;
  audio_url?: string | null;
  definition: string;
  quote: string;
  topic: string | null;
  ap_unit: string | null;
  book_title: string | null;
  section_heading: string | null;
  weight: number;
  weight_tier: string | null;
  stars: number;
  box: number;
  seen_count: number;
  known_count: number;
  last_rating: string | null;
  next_due_at: string | null;
};

export type FlashcardDeck = {
  cards: Flashcard[];
  stats: {
    total: number;
    due: number;
    new: number;
    reviewed: number;
  };
  ahead: boolean;
  scope?: "all" | "today";
};

export type FlashcardNext = {
  card: Flashcard | null;
  reason: "due" | "new" | null;
  due: number;
  new_today: number;
  new_limit: number;
  new_remaining: number;
  new_limit_reached: boolean;
  reviewed_today: number;
  total: number;
  caught_up: boolean;
  next_due_at: string | null;
};

export type UserFlashcard = {
  id: string;
  term: string;
  short_meaning: string;
  detail_meaning: string;
  box: number;
  seen_count: number;
  known_count: number;
  last_rating: string | null;
  last_reviewed_at: string | null;
  next_due_at: string | null;
  created_at: string;
  updated_at: string;
};

export type UserFlashcardList = {
  cards: UserFlashcard[];
  total: number;
  limit: number;
};

export type WrongQuestionDetail = WrongQuestion & {
  question: Feedback;
};

export type WrongSummary = {
  all: number;
  active: number;
  learning: number;
  reviewing: number;
  mastered: number;
};

export type KnowledgeGraphCounts = {
  core: number;
  supporting: number;
  confusable: number;
  total: number;
};

export type KnowledgeGraphSample = {
  question_id: string;
  role?: string;
  paper: string;
  number: number | null;
  stem?: string;
};

export type KnowledgeGraphRelation = {
  id: string;
  name: string;
  type: string;
  label: string;
  direction: "in" | "out";
  evidence: string;
  confidence: number;
};

export type KnowledgeGraphContrast = {
  id: string;
  name: string;
  weight: number;
  questions: KnowledgeGraphSample[];
};

export type KnowledgeGraphConcept = {
  concept_id: string;
  name: string;
  tier: string;
  weight: number;
  questions: KnowledgeGraphCounts;
  definition: string;
  quote: string;
  chapter?: string;
  section: string;
  book: string;
  relations: KnowledgeGraphRelation[];
  contrast: KnowledgeGraphContrast[];
  samples: KnowledgeGraphSample[];
  topic_code?: string;
  supplement?: boolean;
  supplement_source?: string;
  review_status?: string;
};

export type KnowledgeGraphEdge = {
  source: string;
  target: string;
  type: string;
  kind: "relation" | "contrast" | "cooccurrence";
  label?: string;
  evidence?: string;
  confidence?: number;
  weight?: number;
  source_type?: string;
};

export type KnowledgeGraphMindNode = {
  label: string;
  concept_id?: string;
  concept_name?: string;
  children?: KnowledgeGraphMindNode[];
};

export type KnowledgeGraphMindMap = {
  label: string;
  node_count: number;
  matched_count: number;
  children: KnowledgeGraphMindNode[];
};

export type KnowledgeGraphTopic = {
  topic_id: string;
  code: string;
  title_zh: string;
  title_en: string;
  kind: string;
  sort_order: number;
  concept_count: number;
  question_count: number;
  concepts: KnowledgeGraphConcept[];
  edges: KnowledgeGraphEdge[];
  mindmap?: KnowledgeGraphMindMap;
};

export type KnowledgeGraphBridge = {
  source: string;
  target: string;
  semantic: number;
  contrast: number;
  co: number;
};

export type KnowledgeGraphUnit = {
  unit_id: string;
  group_id: string;
  title: string;
  title_en: string;
  topic_count: number;
  question_count: number;
  locked: boolean;
  concept_count?: number;
  topics?: KnowledgeGraphTopic[];
  mindmap_concepts?: Record<string, KnowledgeGraphConcept>;
  bridges?: KnowledgeGraphBridge[];
  graph_version?: number;
};

export type KnowledgeGraphResponse = {
  release_id: string;
  subject_id: string;
  units: KnowledgeGraphUnit[];
};

// ---------------------------------------------------------------------------
// Study calendar
// ---------------------------------------------------------------------------
export type StudyCalendarTask = {
  task_id: string;
  title: string;
  plan_title: string;
  color: string;
  unit_title: string | null;
  topic_title: string | null;
  question_count: number;
  answered_question_count: number;
  status: "completed" | "pending" | "overdue" | "locked";
  locked: boolean;
  early: boolean;
  overdue: boolean;
  completed_late: boolean;
};

export type StudyCalendarDay = {
  date: string;
  tasks: StudyCalendarTask[];
  summary: {
    total: number;
    completed: number;
    pending: number;
    overdue: number;
    locked: number;
  };
};

export type StudyCalendarPlan = {
  assignment_id: string;
  plan_id: string;
  title: string;
  color: string;
  status: string;
  start_date: string;
  end_date: string;
  total_items: number;
  completed_items: number;
  total_questions: number;
  answered_questions: number;
  current_task: {
    task_id: string;
    title: string;
    study_date: string;
    day_index: number;
  } | null;
};

export type StudyCalendarResponse = {
  month: string;
  today: string;
  has_ever_plan: boolean;
  has_active_plan: boolean;
  active_assignment_count: number;
  plans: StudyCalendarPlan[];
  days: StudyCalendarDay[];
  backlog: StudyBacklogTask[];
  overdue_days: number;
  earliest_overdue_date: string | null;
};

export type StudyDayTask = {
  task_id: string;
  title: string;
  homework_id: string;
  homework_title: string;
  note: string;
  unit_id: string | null;
  unit_title: string | null;
  topic_id: string | null;
  topic_title: string | null;
  question_count: number;
  unavailable_question_count: number;
  answered_question_count: number;
  correct_count: number;
  status: "completed" | "pending" | "overdue" | "locked";
  locked: boolean;
  locked_reason: string | null;
  early: boolean;
  overdue: boolean;
  completed_late: boolean;
  session_id: string | null;
  session_status: string | null;
};

export type StudyBacklogTask = StudyDayTask & {
  study_date: string;
  plan_title: string;
  plan_color: string;
};

export type StudyDayAssignment = {
  assignment_id: string;
  plan_id: string;
  plan_title: string;
  color: string;
  status: string;
  start_date: string;
  end_date: string;
  tasks: StudyDayTask[];
  summary: {
    total: number;
    completed: number;
    pending: number;
    overdue: number;
    locked: number;
  };
};

export type StudyDayResponse = {
  date: string;
  today: string;
  is_today: boolean;
  assignments: StudyDayAssignment[];
};

export type StudyHomeworkBlock = {
  task_id: string;
  assignment_id: string;
  plan_title: string;
  plan_color: string;
  task_title: string;
  study_date: string;
  task_completed: boolean;
  next_task: { id: string; title: string; study_date: string } | null;
};

// ---------------------------------------------------------------------------
// Homework Q&A
// ---------------------------------------------------------------------------
export type QaReply = {
  id: string;
  author_type: "student" | "teacher";
  is_teacher: boolean;
  author_name: string;
  content: string;
  created_at: string;
};

export type QaThread = {
  id: string;
  question_id: string;
  content: string;
  created_at: string;
  is_mine: boolean;
  student: { nickname: string };
  teacher_replied: boolean;
  unread: boolean;
  replies: QaReply[];
};

export type QaQuestionThreads = {
  task_id: string;
  question_id: string;
  threads: QaThread[];
  unread: boolean;
};

export type QaMyThread = {
  id: string;
  question_id: string;
  question_stem: string;
  content: string;
  plan_title: string | null;
  task_title: string | null;
  homework_title: string | null;
  created_at: string;
  last_reply_at: string;
  last_message: string;
  reply_count: number;
  teacher_replied: boolean;
  unread: boolean;
};

export type QaMyThreadList = {
  threads: QaMyThread[];
  total: number;
  limit: number;
  offset: number;
};

export type QaThreadDetail = QaThread & {
  question_stem: string;
  plan_title: string | null;
  task_title: string | null;
  homework_title: string | null;
  last_reply_at: string;
};
