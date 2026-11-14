---
id: data-agent-pipeline
title: 数据 Agent 处理规范
version: data-agent-v1
status: active
kind: orchestration
updated: 2026-10-30
inputs: [task_type, subject_id, scope]
outputs: [pipeline_runs, pipeline_steps, reports]
depends_on: [book-kp-extraction, multi-book-concept-integration, question-concept-linking, pdf-question-ingestion, ai-explanation, unit-practice-merge]
used_by: []
---
# 数据 Agent 处理规范

> 版本：`data-agent-v1`  
> 目标：把“新试卷 / 新学科 / 多教材 / 单元练习合并 / 教材换版”统一成一套可重复、可审计、可回滚的数据处理流程。  
> 范围：只讨论数据层；不讨论前端交互和教学设计。  
> 现状：每个科目使用独立源库 `data/content/<subject_id>/<subject_id>_exam.db` + `<subject_id>_knowledge.db`；本文把它们抽象成多学科、多教材、多版本的通用 Agent 流程。

---

## 0. 一句话原则

**所有任务都走同一条状态机：盘点 → 计划/diff → staging → 质量门禁 → 事务写库 → 验证 → 报告。任何一步没有通过 GATE，不进入下一步；任何写库之前必须先 dry-run。**

---

## 1. 设计原则

1. **来源层与概念层分离**
   - 来源层：`books` / `sections` / `knowledge_points`，保留每本书的原文和出处。
   - 概念层：`concept_clusters` / `concept_members` / `concept_relations`，跨书统一。
   - 题目层只关联概念层；来源 KP 只作为概念的定义/出处成员。

2. **不覆盖，追加版本**
   - 新教材 = 新 `book_id`，不覆盖旧教材。
   - 新试卷 = 新 `paper_id`，不覆盖旧试卷。
   - 教材换版 = 新 `book_id` + 同一 `book_family_id`，旧版保留。
   - 概念改名不换 `concept_id`；题目关联不受改名影响。

3. **确定性 ID**
   - `subject_id`：稳定 slug，如 `psychology`。
   - `book_family_id`：`<subject>-<publisher>-<title-slug>`。
   - `book_id`：`<book_family_id>-<edition/year>`。
   - `section_id`：`sha1(book_id + path)[:16]`。
   - `kp_id`：`sha1(book_id + section_id + name_normalized + quote_hash)[:16]`。
   - `concept_id`：按学科内规范名 + 义项限定词生成，**跨版本稳定**。
   - `paper_id`：`<subject>-<source>-<year>-<form>`。
   - `question_id`：`<paper_id>-<section>-<number>`。

4. **staging 优先**
   - 解析结果先写 staging / 临时表 / JSON，全部 GATE 通过后再事务写正式表。
   - 失败只回滚 staging，不污染正式库。

5. **来源可追溯**
   - 每个 KP 有 `book_id + section_id + source_page + definition_quote + quote_hash`。
   - 每个题目有 `paper_id + source_id + source_page/file`。
   - 每个题目概念关联有 `evidence` 和 `confidence`。

6. **幂等**
   - 同一输入重跑不产生重复行。
   - 以自然键判重：KP 用 `(book_id, section_id, name_normalized, quote_hash)`；题目用 `(paper_id, section, number)`；题目概念关联用 `(question_id, concept_id, relation_type, option_label)`。
   - 变化时写新版本或更新指定字段，不做“先删后建”的全局重建。

7. **先审计后合并**
   - 同名不等于同概念。
   - 同名同义才合并；同名异义保留两条并加限定词。
   - 合并必须先输出 merge plan，确认后才执行。

---

## 2. 数据分层

| 层 | 表 | 作用 |
|---|---|---|
| 学科 | `subjects` / `subject_aliases` / `subject_config`（建议新增） | 学科、考试、语言、单元体系、权重参数 |
| 教材来源 | `books` / `book_families`（建议新增）/ `sections` / `section_texts` | 教材版本、章节树、原文 |
| 知识点 | `knowledge_points` / `kp_aliases` / `kp_relations` / `kp_researchers` / `kp_experiments` | 每本书自己的 KP 和出处 |
| 概念 | `concept_clusters` / `concept_members` / `concept_relations` | 跨书统一概念、上下位、同名异义 |
| 题库 | `papers` / `questions` / `options` / `assets` / `frq_rubrics` / `rubric_parts` | 试卷、题目、选项、图片、评分标准 |
| 题目关联 | `question_analysis` / `question_concept_links` / `question_keywords` / `question_kp_links`（legacy） | 题目 ↔ 概念、关键字、状态 |
| 运行 | `pipeline_runs` / `pipeline_steps`（建议新增） / `ingestion_runs` / `validation_issues` | 每次运行的状态、统计、错误 |
| 静态资源 | `assets/<subject_id>/{papers,images,books}` | 试卷/题目图/教材 PDF；DB 存相对路径 |

---

## 3. 统一运行模型

每次任务写一条 `pipeline_run`，每个阶段写一条 `pipeline_step`。建议 DDL：

```sql
CREATE TABLE pipeline_runs (
  run_id          TEXT PRIMARY KEY,
  subject_id      TEXT NOT NULL,
  task_type       TEXT NOT NULL,   -- book_ingest / concept_integrate / paper_ingest /
                                   -- question_link / practice_merge / edition_upgrade
  scope_json      TEXT,            -- book_ids / paper_ids / unit_ids
  input_hash      TEXT,
  prompt_version  TEXT,
  model           TEXT,
  status          TEXT NOT NULL,   -- planned / running / qa_passed / applied / failed / rolled_back
  started_at      TEXT,
  finished_at     TEXT,
  stats_json      TEXT,
  report_path     TEXT
);

CREATE TABLE pipeline_steps (
  run_id          TEXT NOT NULL REFERENCES pipeline_runs(run_id),
  step_no         INTEGER NOT NULL,
  name            TEXT NOT NULL,
  gate            TEXT,            -- G0..G6
  status          TEXT NOT NULL,   -- pending / running / passed / failed / skipped
  stats_json      TEXT,
  started_at      TEXT,
  finished_at     TEXT,
  PRIMARY KEY (run_id, step_no)
);
```

当前 `ingestion_runs` 只覆盖教材抽取；建议保留它，新增 `pipeline_runs` 作为所有任务的统一入口，或把 `ingestion_runs` 扩展成通用表。

---

## 4. Agent 状态机

```text
ROUTE
  → INVENTORY（盘点现有数据、影响范围）
  → PLAN / DIFF（dry-run：新增/变更/合并/删除计划）
  → STAGE（写 staging / JSON）
  → QA（G0–G5 门禁）
  → APPLY（事务写正式表）
  → VERIFY（integrity / FK / 计数 / 页面）
  → REPORT（报告 + run 记录）
```

Agent 角色可以是一个模型/脚本，按任务切换 6 个模式：

1. **Router**：判断任务类型，选择 playbook。
2. **Extractor**：PDF/题库 → staging。
3. **Normalizer**：ID、名称、别名、章节、unit。
4. **Matcher**：KP ↔ 概念、题目 ↔ 概念。
5. **Auditor**：跑 GATE、生成 diff/QA 报告。
6. **Publisher**：事务写库、重建页面、写 run 记录。

硬规则：

- 没有 `PLAN` 不进入 `STAGE`。
- 没有 `QA passed` 不进入 `APPLY`。
- 没有 `VERIFY` 不算完成。
- 任何写库前备份；任何失败可回滚。

---

## 5. Playbook A：新增一套试卷

### A0. 注册来源

```sql
INSERT INTO content_sources
(source_id, kind, title, chinese_title, edition, target_year, file_path, imported_at, subject_id)
VALUES (...);
```

- `source_id` 命名：`<subject>-<publisher>-<year>` 或 `<subject>-<exam-board>-<year>`。
- `kind`：`real_exam` / `mock_exam` / `unit_practice`。
- 保留原始文件路径和 hash（建议新增 `file_hash`）。

### A1. 注册试卷

```sql
INSERT INTO papers
(paper_id, year, title, chinese_title, subject_id, source_pdf, question_count, paper_type, source_id)
VALUES (...);
```

- `paper_id` 必须稳定：`<subject>-<source>-<year>-<form>`。
- 同一套卷的不同 section（MCQ/FRQ）放在同一 `paper_id` 下，用 `questions.section` 区分。
- 同一年的不同 Form 用 `form` 字段区分。

### A2. 解析 → staging

1. PDF 体检：文本层、页数、印刷页偏移、栏数、页眉页脚。
2. 结构识别：MCQ / FRQ / answer key / scoring guidelines / figures。
3. 逐题解析：题干、context、选项 A–E、正确答案、解析、图片、题组。
4. FRQ：prompt、rubric、parts、分值。
5. 写入 staging 表或 JSON：
   - `staging_papers`
   - `staging_questions`
   - `staging_options`
   - `staging_assets`
   - `staging_rubrics`

### A3. 答案与解析

优先级：

1. 官方 answer key；
2. 题目正文中明确给出的答案；
3. 官方 explanation；
4. AI 推断答案（必须标 `answer_source='ai_inferred'` + `answer_confidence`）；
5. AI 生成解析（写 `options.ai_explanation`，不覆盖 `options.explanation`）。

**不得**用 AI 推断覆盖官方答案；不得把 AI 解析写成原书解析。

### A4. 题目 → 概念关联

1. 建立候选池：
   - 该卷所属 unit/chapter 的概念；
   - 别名/缩写/词形匹配；
   - BM25/全文检索；
   - 取 40–90 个候选，分配 C01…。
2. 模型输出 core / supporting / confusable / keywords（见 `03_question_concept_linking.md`）。
3. 校验：
   - core 1–2；
   - core evidence 在题干/context/正确选项；
   - confusable 必须带错误选项字母；
   - keyword surface 必须在原文；
   - 同名概念未混用。
4. 写 `question_analysis` + `question_concept_links`；`question_kp_links` 仅兼容。

### A5. 权重

```bash
python3 _tools/recompute_concept_weights.py
```

内容由 API 读取 active Release；不再生成静态刷题页。

### A6. QA 门禁

- 题目数 = PDF 识别数；选项数 = 题目数 × 选项数；
- 有答案率、有解析率、概念覆盖率；
- 无重复 `question_id`；
- 无孤儿 `concept_id`；
- 图片路径存在；
- `integrity_check` / `foreign_key_check`。

### A7. 产物

- `paper_import_report.md`
- `question_analysis_<paper_id>.md`
- `question_concept_links` 统计
- `pipeline_runs` 记录

---

## 6. Playbook B：新增一门学科

### B0. 学科注册

```sql
INSERT INTO subjects (subject_id, name, name_zh, discipline, exam_code, description, created_at)
VALUES (...);
INSERT INTO subject_aliases (...);
```

建议新增 `subject_config`：

```sql
CREATE TABLE subject_config (
  subject_id        TEXT PRIMARY KEY REFERENCES subjects(subject_id),
  unit_taxonomy     TEXT,   -- JSON：Unit 0–5 / chapter / module
  answer_labels     TEXT,   -- JSON：A–E / 其他
  language          TEXT,
  weight_profile    TEXT,   -- JSON：权重公式参数
  page_template     TEXT,
  stoplist          TEXT    -- JSON：通用词/停用词
);
```

### B1. 多本教材解析

对每本教材执行 `01_book_kp_extraction.md`：

- 新 `book_family_id`；
- 新 `book_id`；
- `books` 行；
- `sections` / `section_texts`；
- `knowledge_points` / `kp_aliases`；
- 去重报告 / QA 报告。

### B2. 概念层整合

执行 `02_multi_book_concept_integration.md`：

- 建 `concept_clusters`；
- 建 `concept_members`；
- 建 `concept_relations`；
- 初始权重可先按跨书覆盖 + 题目数（题目为空时权重普遍低，这是正常的）。

### B3. 题库录入

按 Playbook A 逐套试卷解析。

### B4. 题目 → 概念关联

按 Playbook A4 执行。新学科必须重新校准：

- 候选池的 unit/chapter 规则；
- 通用词 stoplist；
- 同名异义清单；
- 题目语言/解析语言；
- 核心概念粒度。

### B5. 权重校准

- 初始权重只用于排序，不宣称“考试重要性”。
- 等题目量达到阈值（建议 ≥300 道有答案 MCQ）后重算。
- 权重公式参数放在 `subject_config.weight_profile`，不要硬编码心理学阈值。

### B6. 页面

- 新学科使用独立模板或模板变量；
- 不要复用心理学页面文案/单元名；
- 页面只读概念层。

### B7. 隔离规则

- 不在不同学科之间共享 `concept_id`。
- 如果未来要共享统计/研究方法等跨学科概念，另建 `concept_domains` 层，不要让心理学概念直接挂到其他学科。
- 所有查询必须带 `subject_id` 过滤。

---

## 7. Playbook C：单元练习虚拟合并

“合并”有三种含义，先选层级：

### C1. 展示层合并（推荐）

保留两套独立 `paper`，新增 `practice_group`，页面按组聚合。

```sql
CREATE TABLE practice_groups (
  group_id    TEXT PRIMARY KEY,
  subject_id  TEXT NOT NULL,
  unit_id     TEXT,
  title       TEXT,
  edition     TEXT,
  status      TEXT
);

CREATE TABLE practice_group_papers (
  group_id    TEXT NOT NULL REFERENCES practice_groups(group_id),
  paper_id    TEXT NOT NULL REFERENCES papers(paper_id),
  sort_order  INTEGER,
  role        TEXT,   -- primary / supplement / old_edition
  PRIMARY KEY (group_id, paper_id)
);
```

优点：

- 不复制题目；
- 保留来源、答案、解析、版权出处；
- 两套练习可以分别统计正确率；
- 换版时只加新 paper，不改旧数据。

### C2. 虚拟合并卷（需要“一张卷”时）

保留题目行，新增多对多映射：

```sql
CREATE TABLE paper_question_map (
  paper_id    TEXT NOT NULL REFERENCES papers(paper_id),
  question_id TEXT NOT NULL REFERENCES questions(question_id),
  section     TEXT,
  number      INTEGER,
  sort_order  INTEGER,
  PRIMARY KEY (paper_id, question_id)
);
```

- 新建一个 `paper_type='practice_bundle'` 的虚拟卷；
- 通过 `paper_question_map` 引用两套原题；
- 不复制 `questions` / `options`；
- 统计时按 `question_fingerprint` 去重。

### C3. 物理合并（不推荐）

把两套题复制进一张新卷：

- 会产生重复 `question_id` / 重复题目；
- 破坏来源追溯；
- 只适合导出/离线打印，不适合作为主数据。

### C4. 合并流程

1. 盘点两套卷：paper_id、unit、题目数、答案率、解析率。
2. 计算重叠：`question_fingerprint = sha1(normalize(stem) + normalize(options))`。
3. 建 group / bundle。
4. 处理重叠：
   - 同一 fingerprint：bundle 只保留第一条进入映射，primary 优先；
   - 原题仍保留在各自 paper，不删除、不合并 `question_id`；
   - 不同题：全部保留。
5. 统计口径：
   - 去重题数；
   - 各来源进入 bundle 的唯一题数；
   - 正确率按 bundle 中的 question_id 计算。
6. QA：无重复 `question_id`；无孤儿；来源标签只在后台/报告，学生端不显示。
7. 产物：`practice_merge_<group_id>.md` + `practice_merge_summary.md`（重叠题、来源分布、Unit 校验）。

### C4.1 当前实现（配置驱动）

完整规则见 `prompts/06_unit_practice_merge.md`；一个学科一个配置：

```text
config/practice_groups/<subject_id>.json
```

```bash
# 先校验，不写库
python3 _tools/merge_unit_practice.py \
  --config config/practice_groups/psychology.json \
  --dry-run

# 正式重建全部 Unit
python3 _tools/merge_unit_practice.py \
  --config config/practice_groups/psychology.json
```

- 官方题库（CB）固定为 `primary`，教材章节固定为 `supplement`。
- 一个 group 恰好一个 primary；没有 primary 时 `status='needs_review'`，不静默升级 supplement。
- 脚本按 `primary → supplement → old_edition` 稳定排序；CB 题在前。
- 不复制题目；bundle 只通过 `paper_question_map` 引用原题。
- `question_fingerprint` 去重；第一条进入 bundle，原题保留。
- 配置中的 Unit 归属必须按官方课程标准，不按章节数量平均分配。
- 可选的概念层校验会用 supplement 的 `concept_clusters.ap_unit` 主导 Unit 与目标 Unit 比较；不一致默认阻止写库。
- 跨 Unit 重复 fingerprint 默认 `warn`，只在报告中提示，不自动删除。
- 当前心理学 5 个组、20 个成员、5 个 bundle；`paper_question_map` 1,877 条；摘要见 `data/content/psychology/reports/knowledge/practice_merge_summary.md`。

### C5. 两套“同单元不同版本”的练习

不要合并成一个卷；用同一个 `practice_group`，`edition` 区分，默认展示最新版，旧版保留：

```text
group: psychology-unit1-practice
  paper: psychology-cb-2026-u1      role=primary, edition=2026
  paper: psychology-cb-2028-u1      role=primary, edition=2028
  paper: psychology-barrons-2027-ch4 role=supplement, edition=2027
```

当前 bundle 模式要求一个 group 一个 primary；多版本请拆成不同 group/edition，或把旧版标 `old_edition`，不要让两个 primary 同时进入一个 bundle。

---

## 8. Playbook D：教材换版（2027 → 2028）

### D0. 原则

- **不覆盖旧版**；新 `book_id`，旧版保留。
- 同一教材的多个版本共用一个 `book_family_id`。
- 概念 ID 跨版本稳定；来源 KP 按版本新增。
- 单元题、题目、图片、评分标准都按版本追溯。

### D1. 注册新版本

```text
book_family_id = psychology-barrons-ap-psychology
book_id        = psychology-barrons-2028
edition        = 2028
```

`books` 增加（建议）：

```sql
ALTER TABLE books ADD COLUMN book_family_id TEXT;
ALTER TABLE books ADD COLUMN status TEXT DEFAULT 'active';  -- active / archived
```

### D2. 结构 diff

对 2027 与 2028 做：

1. section 树 diff：
   - 新增/删除/改名/移动/层级变化；
   - 用 `path + heading_normalized + ordinal` 对齐。
2. KP diff：
   - `quote_hash` 完全相同 → unchanged；
   - `name_normalized + section` 相同但 quote 变 → definition_changed；
   - 新增 → added；
   - 删除 → removed；
   - 同名不同义 → homonym。
3. 输出 `edition_diff_report.md`：
   - section 变化数；
   - KP 新增/删除/改定义数；
   - 受影响概念清单；
   - 受影响题目/单元题清单。

```bash
python3 _tools/edition_diff.py \
  --old-book psychology-barrons-2027 \
  --new-book psychology-barrons-2028 \
  --json
```

### D3. 概念层增量

执行 `02_multi_book_concept_integration.md` 的 `MODE=edition_diff`：

- unchanged：复用旧 concept_members；
- added：匹配现有概念或新建；
- definition_changed：重新判断 exact/broad/narrow/related；
- removed：不删除旧 KP；标记 `status='rejected'`（如需 `retired` 先扩展 CHECK 约束）；
- 新同名异义：新建限定词概念，不改旧概念名。

### D4. 权重

当前权重公式把“书的本数”当作跨书证据。换版后 2027 + 2028 会被误算成两本独立书。必须改成：

```text
cross_book = COUNT(DISTINCT book_family_id) >= 2
```

同一 `book_family_id` 的多个 edition 只算一个书系。  
`books.book_family_id` 已在 2026-10-28 实现；换版时直接复用同一 family。

### D5. 单元题与题目

- 新版单元题 = 新 `paper_id`，例如 `psychology-barrons-2028-ch11-review`。
- 旧版单元题保留，不覆盖。
- 教材版本追溯使用 `paper_book_sources`（不要与“试卷 → 源文件”的 `paper_sources` 混淆）：
  ```sql
  CREATE TABLE paper_book_sources (
    paper_id TEXT NOT NULL REFERENCES papers(paper_id),
    book_id  TEXT NOT NULL,  -- 逻辑引用 <subject_id>_knowledge.db.books
    role     TEXT NOT NULL DEFAULT 'main',
    note     TEXT,
    PRIMARY KEY (paper_id, book_id, role)
  );
  ```
- 题目来源使用 `question_sources`：
  ```sql
  CREATE TABLE question_sources (
    source_link_id INTEGER PRIMARY KEY,
    question_id TEXT NOT NULL REFERENCES questions(question_id),
    book_id     TEXT NOT NULL,
    section_id  TEXT,
    page_start  INTEGER,
    page_end    INTEGER,
    figure_ref  TEXT,
    role        TEXT NOT NULL DEFAULT 'question',
    note        TEXT
  );
  ```
- 如果新卷题目与旧卷完全相同：
  - 可以复用旧 `question_id`，用 `paper_question_map` 挂到新 paper；
  - 也可以建新 `question_id`，用 `question_fingerprint` 做统计去重。
  - 推荐：**新 paper 新 question_id**，保留来源；分析时按 fingerprint 去重。

### D6. 题目概念关联

- 概念 ID 稳定，所以旧题的 `question_concept_links` 不需要改。
- 只有以下情况需要重链：
  - 概念被合并/拆分；
  - 旧题核心概念在新版被删除或改定义；
  - 新题需要新建关联。
- 重链只影响受影响题目，不做全库重跑。

### D7. 页面

- 默认展示最新 edition；
- 提供 edition 选择器；
- 旧版页面保留，不删除；
- 单元练习 hub 按 `practice_group` 聚合，显示 edition 标签。

### D8. QA

- 新旧版 section/KP 对账；
- 概念新增/改名/合并/退役清单；
- 受影响题目清单；
- 权重变化清单；
- `integrity_check` / `foreign_key_check`；
- 页面无断链、图片存在。

---

## 9. Playbook E：多教材知识点整合

直接使用 `02_multi_book_concept_integration.md`。核心约束：

- 不删除来源 KP；
- 同名同义才合并；
- 同名异义加限定词；
- 关系方向明确；
- 权重按书系而不是按 edition 重复加分；
- 增量模式只处理新书/变化 KP。

---

## 10. 建议的 schema 扩展（按优先级）

> 2026-10-28 状态：P0 已实现；P1 已实现；P2/P3/P4 仍待做。

### P0：换版/多书必须补（已实现）

```sql
ALTER TABLE books ADD COLUMN book_family_id TEXT;
ALTER TABLE books ADD COLUMN status TEXT DEFAULT 'active';
ALTER TABLE content_sources ADD COLUMN book_id TEXT;  -- <subject_id>_exam.db
```

```sql
-- 注意：现有 paper_sources 是“试卷 → 源文件”；
-- 教材版本追溯使用 paper_book_sources，避免混淆。
CREATE TABLE paper_book_sources (
  paper_id TEXT NOT NULL REFERENCES papers(paper_id),
  book_id  TEXT NOT NULL,
  role     TEXT NOT NULL DEFAULT 'main',
  note     TEXT,
  PRIMARY KEY (paper_id, book_id, role)
);

CREATE TABLE question_sources (
  source_link_id INTEGER PRIMARY KEY,
  question_id TEXT NOT NULL REFERENCES questions(question_id),
  book_id     TEXT NOT NULL,
  section_id  TEXT,
  page_start  INTEGER,
  page_end    INTEGER,
  figure_ref  TEXT,
  role        TEXT NOT NULL DEFAULT 'question',
  note        TEXT
);
```

### P1：单元练习合并（已实现）

```sql
CREATE TABLE practice_groups (...);
CREATE TABLE practice_group_papers (...);
CREATE TABLE paper_question_map (...);
ALTER TABLE questions ADD COLUMN question_fingerprint TEXT;
```

### P2：运行与审计

```sql
CREATE TABLE pipeline_runs (...);
CREATE TABLE pipeline_steps (...);
```

### P3：题目去重

```sql
ALTER TABLE questions ADD COLUMN question_fingerprint TEXT;
CREATE INDEX idx_questions_fingerprint ON questions(question_fingerprint);
```

### P4：学科配置

```sql
CREATE TABLE subject_config (...);
```

---

## 11. 统一质量门禁

| Gate | 检查 | 失败动作 |
|---|---|---|
| G0 | 输入 ID 存在；无孤儿；影响范围有清单 | 停止 |
| G1 | 来源解析：题目数/选项数/答案数/图片数对账 | 回退解析 |
| G2 | staging：确定性 ID；无重复；定义逐字匹配 | 修正后重跑 |
| G3 | 概念映射：每个 KP 恰好一个主概念；同名异义未合并 | 停止 |
| G4 | 题目关联：core 1–2；evidence 可定位；confusable 有选项字母 | 该题 needs_review |
| G5 | 权重：0–100；tier 合法；book_family 不重复加分 | 重算/修正 |
| G6 | 写库：integrity / FK / 计数 / 页面 | 回滚 |

每道 GATE 都必须输出机器可读的 `stats_json` 和人工可读的 report。

---

## 12. 当前脚本映射

| 阶段 | 现有脚本 | 说明 |
|---|---|---|
| 教材抽取 | `extract_myers_kps.py` / `import_myers_kps.py` / `import_102_to_knowledge_db.py` | 单书抽取/导入 |
| 教材校验 | `validate_extraction.py` / `dedupe_extraction.py` | 逐字校验、去重 |
| 概念层 | `build_concept_pilot.py` / `dedupe_concepts.py` | 初始概念、去重 |
| 概念关系 | `audit_core_concepts.py` / `concept_curation_data.py` | 核心复核、关系数据 |
| 来源追溯 | `migrate_source_provenance.py` | `book_family_id`、`paper_book_sources`、`question_sources` |
| 版本 diff | `edition_diff.py` | 旧版/新版 section、KP、概念影响对比 |
| 单元练习合并 | `merge_unit_practice.py` | `--config`；`practice_groups` / `practice_group_papers` / bundle map；Unit 校验 |
| 题目迁移 | `migrate_question_links_to_concepts.py` | KP links → concept links |
| 概念权重重算 | `recompute_concept_weights.py` | 权重/tier |
| 试卷解析 | `parse_cb.py` / `import_cb_mock.py` / `parse_barron_*` / `import_barron_*` | 单卷解析 |
| 题目关联（legacy） | `link_question_kps.py` / `link_all_question_kps.py` | 只写 KP links；旧流程保留 |
| 概念关联（推荐） | `link_question_concepts.py` | **通用 concept-first linker**：写 `question_concept_links` |
| 概念关联（Myers 旧版） | `link_myers_concepts.py` / `link_myers_concepts_lexical.py` | Myers 专用；已被通用版取代 |

**当前状态**：通用 concept-first linker 已落地为 `_tools/link_question_concepts.py`。  
它复用 `link_question_kps.py` 的候选/校验框架，但候选池和写库目标换成 `concept_clusters` / `question_concept_links`；`question_kp_links` 仅镜像兼容。

---

## 13. 建议实施顺序

1. ✅ **补 schema**：`book_family_id`、`paper_book_sources`、`question_sources`（2026-10-28 已完成）。
2. ✅ **写通用 concept-first linker**：`link_question_concepts.py`（2026-10-28 已完成）。
3. ✅ **写 edition diff 工具**：`edition_diff.py`（2026-10-28 已完成）。
4. ✅ **写 practice merge 工具**：`merge_unit_practice.py`（2026-10-28 已完成；配置化 + Unit 校验；已建 5 个 Unit 组）。
5. **写 pipeline orchestrator**：一个 CLI/agent，按 task_type 调用上述步骤。
6. **最后再扩新学科**：先用一门新学科跑通 1 本书 + 1 套卷 + 20 题试点，再扩全量。

---

## 附录：数据 Agent 总提示语

```text
# ROLE
你是本项目的“数据流水线 Agent”。你不直接改库；你先盘点、出计划、跑门禁，确认后才写库。

# TASK ROUTER
先判断任务类型：
- new_paper：新增一套试卷
- new_subject：新增一门学科
- multi_book_concepts：多本教材概念整合
- practice_merge：单元练习虚拟合并
- edition_upgrade：教材换版
- question_link：题目 → 概念关联
- audit_only：只复核，不写库

# HARD RULES
1. 先读实际 schema，不套用别的学科字段。
2. 先 dry-run：输出新增/变更/合并/删除计划。
3. 没有 QA passed，不写正式表。
4. 写库前备份；写库后跑 integrity_check / foreign_key_check。
5. 不删除来源 KP；不覆盖旧版本；不按名称直接合并同名异义。
6. 所有任务写 pipeline_runs / pipeline_steps 记录。
7. 最终报告必须包含：范围、输入、统计、GATE 结果、产物、待复核。

# OUTPUT
- 计划（dry-run）
- staging/JSON
- QA 报告
- 写库结果
- 验证结果
- 变更报告
```
