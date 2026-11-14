-- AP Psychology knowledge database schema (v4.0)
-- Database: ap_knowledge.db
-- Design doc: AP_exam/数据库设计文档.md (Part B)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS subjects (
    subject_id  TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    name_zh     TEXT,
    discipline  TEXT,
    exam_code   TEXT,
    description TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subject_aliases (
    subject_id       TEXT NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    alias            TEXT NOT NULL,
    alias_normalized TEXT NOT NULL,
    source           TEXT,
    PRIMARY KEY (subject_id, alias_normalized)
);

CREATE TABLE IF NOT EXISTS books (
    book_id                 TEXT PRIMARY KEY,
    subject_id              TEXT NOT NULL REFERENCES subjects(subject_id),
    title                   TEXT NOT NULL,
    subtitle                TEXT,
    authors                 TEXT,
    publisher               TEXT,
    edition                 TEXT,
    year                    INTEGER,
    isbn                    TEXT,
    language                TEXT,
    book_type               TEXT NOT NULL,
    target_exam             TEXT,
    target_year             INTEGER,
    source_path             TEXT NOT NULL,
    total_pages             INTEGER,
    pdf_printed_offset      INTEGER,
    ocr_used                INTEGER NOT NULL DEFAULT 0,
    classification_status   TEXT NOT NULL,
    classification_evidence TEXT,
    created_at              TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sections (
    section_id            TEXT PRIMARY KEY,
    book_id               TEXT NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
    parent_id             TEXT REFERENCES sections(section_id),
    level                 INTEGER NOT NULL,
    heading               TEXT NOT NULL,
    heading_normalized    TEXT NOT NULL,
    ordinal               INTEGER NOT NULL,
    path                  TEXT NOT NULL,
    pdf_page_start        INTEGER,
    pdf_page_end          INTEGER,
    printed_page_start    INTEGER,
    printed_page_end      INTEGER,
    is_leaf               INTEGER NOT NULL DEFAULT 0,
    excluded              INTEGER NOT NULL DEFAULT 0,
    excluded_reason       TEXT,
    text_hash             TEXT,
    structure_confidence  REAL,
    UNIQUE (book_id, path)
);

CREATE TABLE IF NOT EXISTS section_texts (
    section_id TEXT NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    page_no    INTEGER NOT NULL,
    text       TEXT NOT NULL,
    text_hash  TEXT,
    PRIMARY KEY (section_id, page_no)
);

CREATE TABLE IF NOT EXISTS concept_clusters (
    cluster_id      TEXT PRIMARY KEY,
    subject_id      TEXT NOT NULL REFERENCES subjects(subject_id),
    canonical_name  TEXT NOT NULL,
    canonical_kp_id TEXT,
    description     TEXT,
    UNIQUE (subject_id, canonical_name)
);

CREATE TABLE IF NOT EXISTS knowledge_points (
    kp_id               TEXT PRIMARY KEY,
    book_id             TEXT NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
    section_id          TEXT NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    subheading          TEXT,
    name                TEXT NOT NULL,
    name_normalized     TEXT NOT NULL,
    definition_quote    TEXT,
    definition_type     TEXT NOT NULL,
    definition_language TEXT,
    source_page         INTEGER,
    source_char_start   INTEGER,
    source_char_end     INTEGER,
    quote_hash          TEXT,
    plain_en            TEXT,
    plain_word_count    INTEGER,
    confidence          REAL,
    status              TEXT NOT NULL,
    duplicate_of        TEXT REFERENCES knowledge_points(kp_id),
    concept_cluster_id  TEXT REFERENCES concept_clusters(cluster_id),
    covers_concepts     TEXT,
    prompt_version      TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    updated_at          TEXT,
    UNIQUE (book_id, section_id, name_normalized, quote_hash),
    CHECK (definition_type IN ('explicit','implicit','glossary','table','none')),
    CHECK (status IN ('approved','needs_review','rejected')),
    CHECK (plain_word_count IS NULL OR (plain_word_count BETWEEN 1 AND 10))
);

CREATE TABLE IF NOT EXISTS section_researchers (
    section_id      TEXT NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    researcher_name TEXT NOT NULL,
    year            INTEGER,
    experiment      TEXT,
    evidence_quote  TEXT,
    relation        TEXT NOT NULL DEFAULT 'section_context',
    PRIMARY KEY (section_id, researcher_name, experiment),
    CHECK (relation IN ('section_context','direct'))
);

CREATE TABLE IF NOT EXISTS kp_researchers (
    kp_id           TEXT NOT NULL REFERENCES knowledge_points(kp_id) ON DELETE CASCADE,
    researcher_name TEXT NOT NULL,
    year            INTEGER,
    experiment      TEXT,
    evidence_quote  TEXT,
    relation        TEXT NOT NULL DEFAULT 'direct',
    PRIMARY KEY (kp_id, researcher_name, experiment),
    CHECK (relation IN ('direct','section_context'))
);

CREATE TABLE IF NOT EXISTS kp_experiments (
    kp_id           TEXT NOT NULL REFERENCES knowledge_points(kp_id) ON DELETE CASCADE,
    experiment_name TEXT NOT NULL,
    researcher_name TEXT,
    year            INTEGER,
    evidence_quote  TEXT,
    PRIMARY KEY (kp_id, experiment_name)
);

CREATE TABLE IF NOT EXISTS kp_aliases (
    kp_id            TEXT NOT NULL REFERENCES knowledge_points(kp_id) ON DELETE CASCADE,
    alias            TEXT NOT NULL,
    alias_normalized TEXT NOT NULL,
    source           TEXT,
    PRIMARY KEY (kp_id, alias_normalized)
);

CREATE TABLE IF NOT EXISTS kp_relations (
    kp_id_a       TEXT NOT NULL REFERENCES knowledge_points(kp_id) ON DELETE CASCADE,
    kp_id_b       TEXT NOT NULL REFERENCES knowledge_points(kp_id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    evidence      TEXT,
    confidence    REAL,
    PRIMARY KEY (kp_id_a, kp_id_b, relation_type),
    CHECK (relation_type IN ('same_concept','near_duplicate','homonym','prerequisite'))
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id         TEXT PRIMARY KEY,
    book_id        TEXT NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
    prompt_version TEXT NOT NULL,
    model          TEXT,
    status         TEXT NOT NULL,
    gates_json     TEXT,
    stats_json     TEXT,
    started_at     TEXT NOT NULL,
    finished_at    TEXT,
    CHECK (status IN ('running','success','partial','failed'))
);

CREATE TABLE IF NOT EXISTS validation_issues (
    issue_id   TEXT PRIMARY KEY,
    run_id     TEXT NOT NULL REFERENCES ingestion_runs(run_id) ON DELETE CASCADE,
    book_id    TEXT NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
    section_id TEXT REFERENCES sections(section_id),
    kp_id      TEXT REFERENCES knowledge_points(kp_id),
    severity   TEXT NOT NULL,
    code       TEXT NOT NULL,
    message    TEXT NOT NULL,
    resolved   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    CHECK (severity IN ('info','warning','error','blocker'))
);

CREATE INDEX IF NOT EXISTS idx_books_subject ON books(subject_id);
CREATE INDEX IF NOT EXISTS idx_books_status ON books(classification_status);
CREATE INDEX IF NOT EXISTS idx_sections_book ON sections(book_id);
CREATE INDEX IF NOT EXISTS idx_sections_parent ON sections(parent_id);
CREATE INDEX IF NOT EXISTS idx_kp_book_section ON knowledge_points(book_id, section_id);
CREATE INDEX IF NOT EXISTS idx_kp_name ON knowledge_points(name_normalized);
CREATE INDEX IF NOT EXISTS idx_kp_quote_hash ON knowledge_points(quote_hash);
CREATE INDEX IF NOT EXISTS idx_kp_cluster ON knowledge_points(concept_cluster_id);
CREATE INDEX IF NOT EXISTS idx_kp_status ON knowledge_points(status);
CREATE INDEX IF NOT EXISTS idx_kp_researchers_kp ON kp_researchers(kp_id);
CREATE INDEX IF NOT EXISTS idx_kp_experiments_kp ON kp_experiments(kp_id);
CREATE INDEX IF NOT EXISTS idx_kp_aliases_norm ON kp_aliases(alias_normalized);
CREATE INDEX IF NOT EXISTS idx_kp_relations_a ON kp_relations(kp_id_a);
CREATE INDEX IF NOT EXISTS idx_kp_relations_b ON kp_relations(kp_id_b);
CREATE INDEX IF NOT EXISTS idx_issues_run ON validation_issues(run_id);
CREATE INDEX IF NOT EXISTS idx_issues_severity ON validation_issues(severity);

-- Seed: subject taxonomy (mirrors ap_exam.db.subjects)
INSERT INTO subjects (subject_id, name, name_zh, discipline, exam_code, description, created_at)
VALUES ('psychology', 'AP Psychology', 'AP 心理学', 'Psychology', 'AP',
        'AP Psychology (College Board)', '2026-10-26');

INSERT INTO subject_aliases (subject_id, alias, alias_normalized, source) VALUES
  ('psychology', 'Psychology', 'psychology', 'manual'),
  ('psychology', 'AP Psychology', 'ap psychology', 'manual'),
  ('psychology', 'AP Psych', 'ap psych', 'manual'),
  ('psychology', '心理学', '心理学', 'manual'),
  ('psychology', 'AP 心理学', 'ap 心理学', 'manual');

-- Seed: analyzed book classification
INSERT INTO books (
    book_id, subject_id, title, authors, publisher, edition, year, isbn,
    language, book_type, target_exam, target_year, source_path,
    total_pages, pdf_printed_offset, ocr_used,
    classification_status, classification_evidence, created_at
) VALUES (
    'psychology-barrons-2027', 'psychology',
    'AP Psychology Premium, 2027',
    'Allyson J. Weseley; Robert McEntarffer',
    'Barron''s Educational Series (Kaplan)',
    '2027', 2026, '979-8-3497-0153-5',
    'en', 'review_book', 'AP Psychology', 2027,
    'AP Psychology Premium, 2027 - Allyson J. Weseley & Robert McEntarffer.pdf',
    628, NULL, 0, 'confirmed',
    '{"signals":["title:AP Psychology Premium 2027","authors:Weseley/McEntarffer","publisher:Barron''s","toc:Unit 0-5","target_exam:AP Psychology","language:en"],"subject_match":"psychology","confidence":0.99}',
    '2026-10-26'
);
