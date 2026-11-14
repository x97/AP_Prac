# 提示语统一管理

> 这是本项目所有提示语的唯一入口。  
> 根目录不再保留多份散落的提示语文件；新增/修改提示语先改 `prompts/`，再更新 `registry.yaml` 和 `CHANGELOG.md`。
> 新 PDF 的完整操作流程见 `docs/content/新增试卷解析流程.md`；本目录的 04/03/05 是执行规范。

---

## 1. 目录结构

```text
prompts/
  README.md                  # 本文件：索引、规范、使用方式
  registry.yaml              # 机器可读注册表（ID/版本/状态/输入输出/依赖）
  CHANGELOG.md               # 提示语变更记录
  _template.md               # 新提示语模板
  00_data_agent_pipeline.md  # 数据 Agent 总规范 + 路由提示语
  01_book_kp_extraction.md   # 单本教材 → 知识点
  02_multi_book_concept_integration.md  # 多本教材 → 概念层
  03_question_concept_linking.md        # 题目 → 概念
  04_pdf_question_ingestion.md          # PDF 试卷 → 题库
  05_ai_explanation.md                  # 选择题 → AI 解析
  06_unit_practice_merge.md             # 单元练习虚拟合并
  legacy/
    01_question_kp_linking.md           # 旧版题目 → KP（deprecated）
```

---

## 2. 提示语清单

| ID | 文件 | 版本 | 状态 | 用途 | 主要输出 |
|---|---|---|---|---|---|
| `data-agent-pipeline` | `00_data_agent_pipeline.md` | `data-agent-v1` | active | 统一状态机、5 个 playbook、路由提示语 | 计划、QA、运行记录 |
| `book-kp-extraction` | `01_book_kp_extraction.md` | `whole-book-kp-v1` | active | 单本教材全书抽取 | `sections` / `knowledge_points` / `kp_aliases` |
| `multi-book-concept-integration` | `02_multi_book_concept_integration.md` | `multi-book-concept-v1` | active | 多本教材概念层整合 | `concept_clusters` / `concept_members` / `concept_relations` |
| `question-concept-linking` | `03_question_concept_linking.md` | `question-concept-link-v2` | active | 题目 → 规范概念 | `question_analysis` / `question_concept_links` / `question_keywords` |
| `pdf-question-ingestion` | `04_pdf_question_ingestion.md` | `pdf-question-ingestion-v1` | active | PDF 试卷 → 题库 | `papers` / `questions` / `options` / `assets` / rubrics |
| `ai-explanation` | `05_ai_explanation.md` | `ai-explanation-v2` | active | 生成/补 AI 解析 | `options.ai_explanation` |
| `unit-practice-merge` | `06_unit_practice_merge.md` | `unit-practice-merge-v2` | active | 官方题库 + 教材章节虚拟合并 | `practice_groups` / `paper_question_map` / reports |
| `question-kp-linking-legacy` | `legacy/01_question_kp_linking.md` | `question-kp-link-v1` | deprecated | 旧版题目 → KP | `question_kp_links` |

完整字段见 `registry.yaml`。

---

## 2.5 多科目内容源路径（2026-10-30 起）

新任务必须按科目写入独立源库，根目录 `ap_exam.db` / `ap_knowledge.db` 已移除。

```text
data/content/<subject_id>/
  <subject_id>_exam.db
  <subject_id>_knowledge.db
  assets/
```

示例：

```text
data/content/psychology/psychology_exam.db
data/content/psychology/psychology_knowledge.db
data/content/statistics/statistics_exam.db
data/content/statistics/statistics_knowledge.db
```

科目配置：

```text
config/subjects/<subject_id>.json
```

规则：

- 每个科目只写自己的源库。
- 题目、概念、知识点、书籍的 ID 必须带科目前缀或保证全局唯一。
- 根目录 `ap_exam.db` / `ap_knowledge.db` 兼容链接已移除；新任务只使用科目源库。
- 发布时由 `build_merged_release.py` 合并所有 `enabled` 科目为一个 Release。
- 详细设计见 `docs/多科目内容源与合并发布.md`。

---

## 3. 使用方式

1. 从本目录选择提示语；不要从旧根目录路径找。
2. 复制提示语正文，填好「任务参数」。
3. 默认先 `dry-run` / 盘点，确认后再写库。
4. 执行完把 `prompt_version`、模型、run 统计写进 `pipeline_runs` / `ingestion_runs`。
5. 如果改了提示语，必须同时更新：
   - 文件内 YAML frontmatter 的 `version` / `updated`
   - `registry.yaml`
   - `CHANGELOG.md`
   - 引用该提示语的其他文档

---

### 推荐执行顺序

```text
单本教材接入：
  04 PDF 题目入库（如需）
  → 01 全书知识点抽取
  → 02 多本教材概念整合
  → 03 题目 → 概念关联
  → 05 AI 解析补全

新学科：
  01 × N 本教材
  → 02 概念层
  → 04 × N 套试卷
  → 03 题目 → 概念
  → 05 AI 解析
  → 06 单元练习虚拟合并
```

`00_data_agent_pipeline.md` 是总调度规范；具体任务按上面的顺序选提示语。

## 4. 命名与版本规则

### 文件命名

```text
NN_<stable_slug>.md
```

- `NN`：两位序号，表示推荐执行顺序；新增提示语用下一个空号。
- `slug`：稳定 ASCII 名称，不随标题改名。
- 文件名一旦发布，不重命名；需要新版本时新建文件或保留文件名、升 `version`。
- 中文标题写在文件第一行 `#` 和 frontmatter `title` 里。

### 版本

- 格式：`<prompt-family>-v<major>`，例如 `question-concept-link-v2`。
- 只有**输出契约/写库目标/质量门禁**变化才升 major。
- 文案、示例、补充说明不升 major，更新 `updated` 即可。
- 旧版本不删除；在 `registry.yaml` 标 `deprecated`，在 `CHANGELOG.md` 写替代关系。

### 状态

| 状态 | 含义 |
|---|---|
| `draft` | 草稿，不用于生产 |
| `active` | 当前推荐使用 |
| `deprecated` | 仍可查，但新任务不用 |
| `archived` | 只保留历史，不再维护 |

---

## 5. 元数据契约

每个提示语文件顶部必须有 YAML frontmatter：

```yaml
---
id: question-concept-linking
title: 题目知识点生成（概念层）
version: question-concept-link-v2
status: active
kind: linking
updated: 2026-10-28
inputs: [paper_id, concept_db, scope]
outputs: [question_analysis, question_concept_links, question_keywords]
depends_on: [multi-book-concept-integration, pdf-question-ingestion]
used_by: [data-agent-pipeline]
---
```

字段说明：

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 稳定 ID，与文件名分离 |
| `title` | 是 | 中文标题 |
| `version` | 是 | 提示语版本 |
| `status` | 是 | draft/active/deprecated/archived |
| `kind` | 是 | extraction/integration/linking/ingestion/generation/orchestration |
| `updated` | 是 | 最后修改日期 |
| `inputs` | 是 | 任务参数/输入表 |
| `outputs` | 是 | 写库目标/产物 |
| `depends_on` | 否 | 前置提示语 ID |
| `used_by` | 否 | 下游提示语 ID |
| `superseded_by` | 否 | deprecated 时必填 |

---

## 6. 新增提示语流程

1. 复制 `_template.md`。
2. 分配下一个 `NN` 和稳定 `id`。
3. 写清楚：输入、输出、GATE、停止条件、报告格式。
4. 在 `registry.yaml` 增加条目。
5. 在 `CHANGELOG.md` 增加记录。
6. 更新本 README 的清单。
7. 如果取代旧提示语：旧文件标 `deprecated` + `superseded_by`，不要直接删。
8. 跑一次提示语自检（见第 8 节）。

---

## 7. 提示语自检清单

- [ ] 顶部 YAML frontmatter 完整，`registry.yaml` 有对应条目。
- [ ] 明确输入参数和默认值。
- [ ] 明确输出表/字段/文件。
- [ ] 明确 GATE 和停止条件。
- [ ] 明确“先 dry-run，后写库”。
- [ ] 不硬编码单一学科；学科差异放在参数/配置里。
- [ ] 写库目标与当前 schema 一致（例如题目关联优先 `question_concept_links`）。
- [ ] 有报告格式和失败处理。
- [ ] 版本/日期/依赖关系已更新。
- [ ] 没有引用已移动的旧根目录路径。

---

## 8. 提示语校验

每次改动提示语后运行：

```bash
python3 _tools/validate_prompts.py
```

它会检查：

- `registry.yaml` 与文件 frontmatter 的 `id` / `version` / `status` / `kind` 是否一致；
- 依赖/被依赖/替代关系是否存在；
- 每个提示语文件是否已注册；
- 根目录是否残留旧提示语文件；
- active 提示语是否还引用旧根目录路径。

## 9. 旧路径迁移对照

| 旧路径 | 新路径 | 状态 |
|---|---|---|
| `全书一次性知识点抽取提示语.md` | `prompts/01_book_kp_extraction.md` | active |
| `多本教材知识点处理提示语.md` | `prompts/02_multi_book_concept_integration.md` | active |
| `题目知识点生成提示语.md` | `prompts/03_question_concept_linking.md` | active |
| `PDF题目解析入库提示语.md` | `prompts/04_pdf_question_ingestion.md` | active |
| `AI解析生成提示语.md` | `prompts/05_ai_explanation.md` | active |
| `数据Agent处理规范.md` | `prompts/00_data_agent_pipeline.md` | active |
| `题目解析关联提示语.md` | `prompts/legacy/01_question_kp_linking.md` | deprecated |

根目录不再保留这些文件的副本。旧链接如仍存在，按上表替换。

---

## 10. 相关文档

- 数据模型：`docs/content/数据库设计文档.md`
- 试卷解析方法：`../docs/content/试卷解析方法.md`
- 当前实现脚本：`_tools/`
- 概念层复核：`data/content/psychology/reports/knowledge/concept_audit_summary.md`

---

## 11. 一句话规则

**提示语只从 `prompts/` 取；改提示语必须同步 registry + changelog + 引用；旧版本只废弃，不删除。**
