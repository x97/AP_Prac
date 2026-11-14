# 提示语变更记录

> 所有提示语的版本变化、迁移、废弃都记录在这里。  
> 格式：日期、提示语 ID、版本、变更类型、说明、影响文件。

## 2026-10-30

### ai-explanation-v2

- 变更类型：修改
- 变更内容：`generate_ai_explanations.py` 增加 `--subject`；命令、导出目录、报告目录改为按科目源库。
- 影响表/字段：`options.ai_explanation`
- 影响脚本/页面：`_tools/generate_ai_explanations.py`
- 兼容性：默认 `--subject psychology`；旧路径仍可通过 `--db` / `--out-json` / `--report` 覆盖。

### unit-practice-merge-v2

- 变更类型：修改
- 变更内容：明确 `config/practice_groups/<subject_id>.json` 必须指向 `data/content/<subject_id>/` 源库；legacy 模式按 `--subject-id` 读取科目配置。
- 影响表/字段：`practice_groups` / `practice_group_papers` / `paper_question_map`
- 影响脚本/页面：`_tools/merge_unit_practice.py`
- 兼容性：`--db` / `--knowledge-db` 仍可显式覆盖。

### 多科目内容源迁移

- 内容源改为按科目目录：

```text
data/content/<subject_id>/<subject_id>_exam.db
data/content/<subject_id>/<subject_id>_knowledge.db
```

- psychology 迁移为 `data/content/psychology/psychology_exam.db` / `psychology_knowledge.db`。
- statistics 从旧合并库拆出，暂不启用。
- 根 `ap_exam.db` / `ap_knowledge.db` 改为 psychology 兼容符号链接。
- 新增 `config/subjects/<subject_id>.json`。
- `04_pdf_question_ingestion.md`、`05_ai_explanation.md`、`01_book_kp_extraction.md`、`06_unit_practice_merge.md` 的写库路径改为 `<subject_id>_exam.db` / `<subject_id>_knowledge.db`。
- 新增 `_tools/build_merged_release.py`：按 enabled 科目合并为一个 `exam.db` + `knowledge.db`。
- 新增 `_tools/split_subject_sources.py`：从旧合并源库拆分科目。
- 新增 `docs/多科目内容源与合并发布.md`。
- 新增 statistics 三份空配置占位：`config/exam_formats/statistics.json`、`config/practice_topics/statistics.json`、`config/content_exclusions/statistics.json`；statistics 仍 `enabled=false`。
- `_tools/generate_ai_explanations.py` 新增 `--subject`，默认写 `data/content/<subject>/<subject>_exam.db`，中间产物和报告写到该科目的 `extraction/` / `reports/`。
- `_tools/merge_unit_practice.py` 的 legacy 模式按 `--subject-id` 读取 `config/subjects/<subject_id>.json` 的源库路径。
- statistics 导入/报告脚本改为写 `data/content/statistics/statistics_exam.db` / `statistics_knowledge.db`，不再写根库。
- Release 激活改为单一全局 `data/releases/active` 符号链接；`release.json` 的 `subjects` 决定同时切换的科目。
- `validate_content_release.py` 的总 counts 改为按实际库计算；多科目 Release 会提示“当前只校验 psychology 内容不变量”。
- 移除根 `ap_exam.db` / `ap_knowledge.db` 兼容符号链接；所有脚本改为直接使用科目源库。
- `AP_exam/` 目录移除：
  - 报告/JSON → `data/content/<subject>/{extraction,reports}/`
  - 数据库设计、试卷解析方法、schema → `docs/content/`
- Admin 内容读取改为 active Release；写接口（默认关闭）写本地科目源库。
- 移除旧静态演示页 `pages/`、根 `index.html`，以及 `build_quiz.py` / `build_unit_practice.py` / `build_knowledge_viewer.py` 和对应模板；项目统一使用 `apps/web` + `apps/api` 前后端分离。
- 新增 `docs/content/新增试卷解析流程.md`：新 PDF 的交互模板、目录、解析/QA/写库/概念关联/AI 解析/Release 激活流程。

---

## 2026-10-28

### 统一管理迁移

- 新增 `prompts/` 目录，所有提示语集中管理。
- 新增 `prompts/README.md`、`registry.yaml`、`_template.md`、`CHANGELOG.md`。
- 迁移文件：

| 旧路径 | 新路径 | 状态 |
|---|---|---|
| `全书一次性知识点抽取提示语.md` | `prompts/01_book_kp_extraction.md` | active |
| `多本教材知识点处理提示语.md` | `prompts/02_multi_book_concept_integration.md` | active |
| `题目知识点生成提示语.md` | `prompts/03_question_concept_linking.md` | active |
| `PDF题目解析入库提示语.md` | `prompts/04_pdf_question_ingestion.md` | active |
| `AI解析生成提示语.md` | `prompts/05_ai_explanation.md` | active |
| `数据Agent处理规范.md` | `prompts/00_data_agent_pipeline.md` | active |
| `题目解析关联提示语.md` | `prompts/legacy/01_question_kp_linking.md` | deprecated |

### 数据层实现（2026-10-28）

- 新增 `_tools/migrate_source_provenance.py`：`books.book_family_id` / `status`、`content_sources.book_id`、`paper_book_sources`、`question_sources`。
- 新增 `_tools/link_question_concepts.py`：通用 concept-first linker，写 `question_concept_links`；`question_keywords` 新增 `concept_id`。
- `recompute_concept_weights.py` 改为按 `book_family_id` 去重，避免换版重复加跨书权重。
- Q8 试点：`Animism` 从 needs_review 变为 linked；报告见 `data/content/psychology/reports/question_analysis/psychology-barrons-2027-ch11-review_concepts.md`。

### 根目录整理（2026-10-28）

- 25 个 HTML 页面迁入 `pages/`；新增根入口 `index.html`。
- 77 个 DB 备份迁入 `backups/`。
- `build_quiz.py` / `build_unit_practice.py` / `build_knowledge_viewer.py` 默认输出改为 `pages/`。
- 页面互链保持相对路径；单元练习 hub 与知识点库同目录。

### 静态资源目录（2026-10-28）

- 599 个文件迁入 `assets/psychology/{papers,images,books}`。
- 同步 `assets.path`、`paper_sources.path`、`content_sources.file_path`、`papers.source_pdf`、`questions.source_file`、`books.source_path` 共 445 条。
- 新增 `assets/psychology/README.md`；迁移脚本 `_tools/migrate_assets_layout.py`。
- 23 个刷题页重建；所有 DB 路径验证存在。

### unit-practice-merge-v1（2026-10-28）

- 新增 `prompts/06_unit_practice_merge.md`：任何学科的单元练习虚拟合并统一规范。
- 新增 `config/practice_groups/<subject_id>.json` 配置模式；心理学配置为 `config/practice_groups/psychology.json`。
- `_tools/merge_unit_practice.py` 支持 `--config`、`--dry-run`、单 group 重建；校验 primary 数量、跨 group 重复成员、bundle 冲突。
- 增加概念层 Unit 校验：supplement 的 `concept_clusters.ap_unit` 主导 Unit 必须与目标 Unit 一致，不一致默认阻止写库。
- 增加跨 Unit 重复 fingerprint 检测：默认 `warn`，只在报告提示，不自动删除。
- 修正心理学 Unit 映射：Ch6 Sensation → Unit 1；Ch7–10 → Unit 2；Ch15 Motivation/Emotion → Unit 4；Ch16–18 → Unit 5。
- 重建后各 Unit bundle 题目数：345 / 387 / 384 / 409 / 352，合计 1,877。

### 单元练习统一 bundle（2026-10-28）

- 5 个 Unit 各建一个 `practice_bundle` 虚拟卷。
- `practice_groups.bundle_paper_id` 指向 bundle。
- `paper_question_map` 1,877 条；CB 为主，Barron 作为 supplement 追加。
- 学生端只展示单元练习，不显示题库选择。

### 版本 diff / 单元练习合并（2026-10-28）

- 新增 `_tools/edition_diff.py`：只读对比同一 `book_family` 的旧版/新版 section、KP、概念影响；输出 `section_diff.csv`、`kp_diff.csv`、`concept_impact.csv`、`edition_diff_report.md`。
- 新增 `_tools/merge_unit_practice.py`：group 模式建 `practice_groups` / `practice_group_papers`；bundle 模式建 `practice_bundle` 虚拟卷与 `paper_question_map`；`question_fingerprint` 去重。
- 已建 5 个 Unit 练习组（20 个成员）；当前未建 bundle 卷。

### `question-concept-link-v2`

- `题目知识点生成提示语.md` 重写为概念层 v2。
- 写库目标从 `question_kp_links` 改为 `question_concept_links`。
- 候选池从来源 KP 改为 `concept_clusters`。
- 保留 `question_kp_links` 仅作 legacy 兼容。
- 旧版 `题目解析关联提示语.md` 标记为 deprecated，替代者 `question-concept-linking`。

### `multi-book-concept-v1`

- 新增多本教材概念层整合提示语。
- 覆盖 exact / broad / narrow / related / homonym / new 六类判断。
- 增加增量接入和教材换版模式。
- 明确 `book_family_id` 是换版建议字段。

### `data-agent-v1`

- 新增数据 Agent 总规范：统一状态机、5 个 playbook、schema 缺口、实施顺序。
- 增加元提示语（meta-prompt）路由模板。

---

## 变更模板

```text
## YYYY-MM-DD

### <prompt-id> <version>

- 变更类型：新增 / 修改 / 废弃 / 迁移
- 变更内容：
- 影响表/字段：
- 影响脚本/页面：
- 兼容性：
- 替代/被替代关系：
```
