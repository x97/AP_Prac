export type Admin = {
  id: string;
  username: string;
  email: string;
  role: string;
  status: string;
  can_edit_content: boolean;
  created_at: string;
  last_login_at: string | null;
};

export type Dashboard = {
  admin: Admin;
  release: {
    release_id: string;
    counts: Record<string, number>;
    created_at: string | null;
  };
  stats: {
    students: number;
    active_students_7d: number;
    practice_sessions: number;
    attempts: number;
    wrong_active: number;
    open_reports: number;
  };
  recent_attempts: Array<{
    id: string;
    paper_id: string;
    paper_title: string;
    mode: string;
    status: string;
    mcq_score: number | null;
    mcq_total: number | null;
    created_at: string;
  }>;
  recent_practice: Array<{
    id: string;
    source: string;
    status: string;
    group_title: string | null;
    topic_title: string | null;
    created_at: string;
  }>;
};

export type StudentListItem = {
  id: string;
  email: string | null;
  email_masked: string | null;
  phone_masked: string | null;
  nickname: string | null;
  status: string;
  created_at: string;
  last_login_at: string | null;
  last_active_at: string | null;
  answered: number;
  correct: number;
  accuracy: number | null;
  practice_count: number;
  attempt_count: number;
};

export type StudentList = {
  students: StudentListItem[];
  total: number;
  limit: number;
  offset: number;
};

export type StudentDetail = {
  student: {
    id: string;
    email: string | null;
    email_masked: string | null;
    phone_masked: string | null;
    nickname: string | null;
    status: string;
    created_at: string;
    last_login_at: string | null;
  };
  dashboard: {
    overview: {
      answered: number;
      correct: number;
      accuracy: number | null;
      streak_days: number;
      total_questions: number;
    };
    units: Array<{
      group_id: string;
      unit_id: string;
      title: string;
      title_en: string;
      question_count: number;
      total: number;
      answered: number;
      correct: number;
      accuracy: number | null;
    }>;
    activity: Array<{ day: string; answered: number; correct: number }>;
    continue: unknown;
  };
  sessions: Array<{
    id: string;
    source: string;
    status: string;
    score: number | null;
    group_title: string | null;
    topic_title: string | null;
    created_at: string;
    submitted_at: string | null;
    total_questions: number;
    answered: number;
    correct: number;
  }>;
  attempts: Array<{
    id: string;
    paper_id: string;
    paper_title: string;
    paper_year: number | null;
    mode: string;
    status: string;
    mcq_score: number | null;
    mcq_total: number | null;
    frq_score: number | null;
    frq_total: number | null;
    created_at: string;
    submitted_at: string | null;
  }>;
  wrong_summary: {
    learning: number;
    reviewing: number;
    mastered: number;
  };
};

export type PaperConfig = {
  format_code: string | null;
  mcq_count: number | null;
  mcq_minutes: number | null;
  frq_count: number | null;
  frq_minutes: number | null;
  frq_forms: string[];
  is_complete: number | null;
  frq_rubric_complete: number | null;
  expected_frq_points: number | null;
  notes: string | null;
};

export type Paper = {
  paper_id: string;
  admin_origin?: string | null;
  admin_updated_at?: string | null;
  year: number;
  title: string | null;
  chinese_title: string | null;
  subject_id: string;
  paper_type: string;
  source_pdf: string | null;
  question_count: number | null;
  actual_questions: number;
  mcq_count: number;
  frq_count: number;
  config: PaperConfig;
};

export type QuestionSummary = {
  question_id: string;
  paper_id?: string;
  subject_id?: string;
  admin_origin?: string | null;
  admin_updated_at?: string | null;
  source_paper_id?: string | null;
  section: string;
  number: number;
  form: string | null;
  stem: string;
  answer_source: string | null;
  answer_confidence: string | null;
  option_count: number;
  correct_count: number;
};

export type PaperDetail = Omit<Paper, "actual_questions" | "mcq_count" | "frq_count"> & {
  config: PaperConfig;
  questions: QuestionSummary[];
  practice?: {
    group_id: string;
    unit_id: string;
    mapped: number;
    usable: number;
    excluded: number;
  } | null;
};

export type QuestionOption = {
  question_id: string;
  label: string;
  admin_origin?: string | null;
  admin_updated_at?: string | null;
  content: string;
  sort_order: number;
  is_correct: number;
  explanation: string | null;
  ai_explanation: string | null;
};

export type QuestionAsset = {
  asset_id: string;
  question_id: string;
  option_label: string | null;
  kind: string;
  path: string;
  page: number | null;
  bbox: string | null;
};

export type QuestionConceptLink = {
  link_id: number;
  question_id: string;
  concept_id: string;
  canonical_name: string | null;
  relation_type: "core" | "supporting" | "confusable";
  option_label: string | null;
  confidence: number | null;
  evidence: string | null;
  rationale: string | null;
  topic: string | null;
  ap_unit: string | null;
  weight: number | null;
  weight_tier?: string | null;
  admin_origin?: string | null;
  admin_updated_at?: string | null;
};

export type QuestionDetail = {
  question_id: string;
  paper_id: string;
  subject_id?: string;
  section: string;
  number: number;
  form: string | null;
  stem: string;
  context: string | null;
  correct_answer: string | null;
  answer_text: string | null;
  answer_source: string | null;
  answer_confidence: string | null;
  options: QuestionOption[];
  assets: QuestionAsset[];
  concepts: QuestionConceptLink[];
  admin_origin?: string | null;
  admin_updated_at?: string | null;
};

export type Concept = {
  cluster_id: string;
  subject_id?: string;
  admin_origin?: string | null;
  admin_updated_at?: string | null;
  canonical_name: string;
  description: string | null;
  ap_unit: string | null;
  topic: string | null;
  status: string;
  weight: number;
  weight_tier: string | null;
  member_count: number;
  canonical_kp_id: string | null;
};

export type ConceptDetail = Concept & {
  members: Array<{
    kp_id: string;
    name: string;
    plain_en: string | null;
    definition_quote: string | null;
    book_id: string;
    section_id: string;
    subheading: string | null;
    confidence: number | null;
  }>;
};

export type KnowledgePoint = {
  kp_id: string;
  subject_id?: string;
  admin_origin?: string | null;
  admin_updated_at?: string | null;
  book_id: string;
  section_id: string;
  subheading: string | null;
  name: string;
  plain_en: string | null;
  definition_quote: string | null;
  status: string;
  confidence: number | null;
  weight: number;
  weight_tier: string | null;
  concept_cluster_id: string | null;
};

export type Release = {
  release_id: string;
  subjects: string[];
  merged: boolean;
  created_at: string | null;
  counts: Record<string, number>;
  counts_by_subject: Record<string, Record<string, number>>;
  active: boolean;
};

export type ReleaseJob = {
  id: string;
  release_id: string;
  status: string;
  log: string | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
};

export type AuditLog = {
  id: string;
  admin_id: string | null;
  admin_username: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  detail: unknown;
  ip: string | null;
  created_at: string;
};

export type ActivationCodeBatch = {
  id: string;
  scope_type: "all" | "subject";
  subject_ids: string[];
  duration_days: number | null;
  expires_on: string | null;
  count: number;
  used: number;
  voided: number;
  available: number;
  status: string;
  note: string | null;
  created_at: string;
  voided_at: string | null;
};

export type ActivationCode = {
  id: string;
  batch_id: string;
  hint: string;
  status: string;
  used_count: number;
  max_uses: number;
  created_at: string;
  last_used_at: string | null;
  voided_at: string | null;
};


export type KnowledgeGraphNodeType = "branch" | "concept" | "supplement";

export type KnowledgeGraphSupplement = {
  id: string;
  name: string;
  definition: string;
  source: string;
  review_status: string;
};

export type KnowledgeGraphEditorNode = {
  id: string;
  label: string;
  type: KnowledgeGraphNodeType;
  concept_id?: string | null;
  concept_name?: string | null;
  definition?: string | null;
  tier?: string | null;
  supplement?: KnowledgeGraphSupplement | null;
  children: KnowledgeGraphEditorNode[];
};

export type KnowledgeGraphTopicOption = {
  topic_code: string;
  topic_id: string | null;
  title_en: string;
  title_zh: string;
  kind: string;
  has_mindmap: boolean;
  has_draft: boolean;
  revision: number;
  node_count: number;
};

export type KnowledgeGraphUnitOption = {
  unit_id: string;
  group_id: string;
  title: string;
  title_en: string;
  topics: KnowledgeGraphTopicOption[];
};

export type KnowledgeGraphUnitsResponse = {
  units: KnowledgeGraphUnitOption[];
  can_edit: boolean;
};

export type KnowledgeGraphTopicPayload = {
  unit_id: string;
  group_id: string;
  topic_code: string;
  title_en: string;
  title_zh: string;
  source: "release" | "draft";
  revision: number;
  node_count: number;
  tree: KnowledgeGraphEditorNode;
  duplicate_concept_ids: string[];
  duplicate_labels: string[];
  unresolved_concept_ids: string[];
  can_edit: boolean;
};

export type KnowledgeGraphSaveResult = {
  ok: boolean;
  revision: number;
  node_count: number;
  duplicate_concept_ids: string[];
  duplicate_labels: string[];
};

export type KnowledgeGraphSearchResult = {
  kind: "concept" | "supplement";
  concept_id: string;
  name: string;
  definition: string;
  tier?: string | null;
  topic_code?: string | null;
  source: string;
  review_status?: string | null;
};

export type KnowledgeGraphSearchResponse = {
  results: KnowledgeGraphSearchResult[];
  total: number;
};

export type KnowledgeGraphCustomConcept = {
  concept_id: string;
  name: string;
  definition: string;
  source: string;
  review_status: string;
  unit_id: string;
  topic_code: string | null;
};


export type AdminSubject = {
  subject_id: string;
  name: string;
  name_zh: string;
  enabled: boolean;
};
