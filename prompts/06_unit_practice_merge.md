---
id: unit-practice-merge
title: 单元练习虚拟合并
version: unit-practice-merge-v2
status: active
kind: integration
updated: 2026-10-30
inputs: [subject_id, exam_db, knowledge_db, practice_group_config]
outputs: [practice_groups, practice_group_papers, paper_question_map, question_fingerprint, reports]
depends_on: [pdf-question-ingestion, question-concept-linking]
used_by: [data-agent-pipeline]
---

# 单元练习虚拟合并

> 版本：`unit-practice-merge-v2`  
> 用途：把“官方题库单元练习 + 教材章末练习”虚拟合并成一个学生可见的 Unit 练习。  
> 适用：任何学科、任何教材；心理学是第一个落地学科。  
> 核心约束：官方题库必须是 `primary`；教材章节只能是 `supplement`；不复制题目；学生端不显示题库选择。

---

## 一、任务参数

```text
【任务参数】
- 学科 subject_id：
- 题库 exam_db：data/content/<subject_id>/<subject_id>_exam.db
- 知识库 knowledge_db：data/content/<subject_id>/<subject_id>_knowledge.db
- 合并配置：config/practice_groups/<subject_id>.json
- 模式：盘点 / dry-run / apply
- 是否重建页面：是 / 否
- 其他要求：
```

---

## 二、不可违反的规则

1. **官方题库优先**
   - CB / 官方题库卷 = `primary`。
   - 教材章末练习、教辅章节练习 = `supplement`。
   - 不允许把 supplement 静默升为 primary。

2. **一个 Unit 一个 group**
   - `practice_groups.group_id` 建议 `<subject_id>-unit<N>-practice`。
   - 一个 group 只有一个虚拟 `practice_bundle`。
   - 不同 Unit 不共用同一份练习卷。

3. **不复制题目**
   - 题目、选项、答案、解析仍保留在原 `paper`。
   - bundle 通过 `paper_question_map` 引用原题。
   - 禁止把题目复制成新 `question_id`。

4. **固定排序**
   - 顺序固定为 `primary → supplement → old_edition`。
   - 同一角色内按配置文件顺序。
   - 不按章节数量平均分配，不按难度随机重排。

5. **去重规则**
   - `question_fingerprint = sha1(normalize(stem) + normalize(options))`。
   - 同一 fingerprint 只保留第一条进入 bundle。
   - 因为 primary 在前，重复题自动保留官方题库版本。
   - 原题不删除；只影响 bundle 映射。

6. **Unit 归属以课程标准为准**
   - 教材章节数 ≠ Unit 数，不能按数量平均分。
   - 以官方 CED / 课程大纲的 Unit–Topic 映射为准。
   - 概念层 `concept_clusters.ap_unit` 只作为辅助校验信号，不是最终权威。
   - 例如 AP Psychology 2024 CED：
     - Sensation = Unit 1（1.6）
     - Perception = Unit 2（2.1）
     - Motivation / Emotion = Unit 4
     - 不能把 Sensation 和 Perception 合并成同一章塞进 Unit 2。

7. **没有官方题库的 Unit**
   - `practice_groups.status` 标为 `needs_review`。
   - 仍可建 group/bundle 供预览，但学生端只能展示 `active`。
   - 不允许静默把教材练习升为 `primary`。

8. **学生端只看到 Unit**
   - 不显示“CB / Barron / 教材版本”选择。
   - 来源只保留在数据层和后台报告。
   - 旧双来源页面只作为过渡，不作为新架构。

9. **跨 Unit 重复题只报告，不自动删除**
   - 同一 `question_fingerprint` 出现在多个 Unit 时，默认 `warn`。
   - 归属需要人工判断；不要在未确认时自动从某个 Unit 删除。
   - 如需严格阻断，配置 `validation.on_cross_group_duplicate='error'`。

10. **写库前必须 dry-run**
   - 先跑配置校验 + Unit 映射校验。
   - 有 `error` 不写库。
   - 写库前自动备份；写库后跑 `integrity_check` / `foreign_key_check`。

---

## 三、统一配置

一个学科一个文件：

```text
config/practice_groups/<subject_id>.json
```

最小结构：

```json
{
  "schema_version": 1,
  "subject_id": "psychology",
  "curriculum": "AP Psychology CED 2024-25",
  "exam_db": "data/content/<subject_id>/<subject_id>_exam.db",
  "knowledge_db": "data/content/<subject_id>/<subject_id>_knowledge.db",
  "report_dir": "data/content/psychology/reports/knowledge",
  "validation": {
    "enabled": true,
    "check_primary": false,
    "min_core_links": 3,
    "min_dominant_share": 0.5,
    "on_mismatch": "error",
    "on_cross_group_duplicate": "warn"
  },
  "groups": [
    {
      "group_id": "psychology-unit1-practice",
      "unit_id": "1",
      "curriculum_topics": "1.1-1.6",
      "title": "心理学 Unit 1 单元练习",
      "bundle_paper_id": "psychology-unit1-practice-bundle",
      "bundle_title": "心理学 Unit 1 单元练习",
      "note": "CED Unit 1: Biological Bases + Sleep + Sensation",
      "members": [
        {"paper_id": "psychology-cb-2026-u1", "role": "primary"},
        {"paper_id": "psychology-barrons-2027-ch4-review", "role": "supplement"}
      ]
    }
  ]
}
```

字段规则：

| 字段 | 必填 | 说明 |
|---|---|---|
| `subject_id` | 是 | 学科 ID；所有 paper 必须属于该学科 |
| `curriculum` | 否 | 课程大纲版本，写入报告 |
| `exam_db` | 否 | 默认 `data/content/<subject_id>/<subject_id>_exam.db` |
| `knowledge_db` | 否 | 默认 `data/content/<subject_id>/<subject_id>_knowledge.db`；用于 Unit 映射校验 |
| `groups[].unit_id` | 是 | 目标 Unit；与 `concept_clusters.ap_unit` 比较 |
| `groups[].curriculum_topics` | 否 | 该 Unit 的官方 Topic 范围 |
| `groups[].bundle_paper_id` | 建议 | 虚拟卷 ID；不填则只建 group |
| `members[].role` | 是 | `primary` / `supplement` / `old_edition` |
| `validation.on_cross_group_duplicate` | 否 | `warn` / `error` / `ignore`；默认 `warn` |

---

## 四、Pipeline

### Stage 0 — 盘点

检查：

```text
papers：paper_id / paper_type / subject_id / question_count
每个 Unit 是否有官方题库 primary
每个教材章节属于哪个 Unit
题目数、答案数、解析数
是否已有旧 group / bundle / paper_question_map
```

GATE G0：

- 所有成员 `paper_type='unit_practice'`，或显式 `--allow-any-paper`。
- 准备上线的 group 恰好一个 primary；0 个 primary 只能标 `needs_review`，不能静默升级 supplement。
- 一个 paper 只属于一个 Unit；跨 Unit 必须拆卷或显式配置共享。
- `bundle_paper_id` 不与普通 paper 冲突。

### Stage 1 — 写配置

按官方课程标准的 Unit–Topic 映射填写 `config/practice_groups/<subject_id>.json`。

GATE G1：

- 每个 Unit 都有 `unit_id`、`title`、`members`。
- 准备上线的 Unit 有且只有一个 primary；没有 primary 的 Unit 标 `needs_review`。
- primary 在前；supplement 按教材章节顺序。
- 配置中的 Unit 归属有人工依据（CED /  syllabus / 教材目录）。
- 不按“章节数量平均”分配。

### Stage 2 — dry-run

```bash
python3 _tools/merge_unit_practice.py \
  --config config/practice_groups/<subject_id>.json \
  --dry-run
```

脚本会做：

- 配置结构校验；
- paper 存在性 / 学科 / 类型校验；
- primary 数量校验；
- 跨 group 重复成员校验；
- `question_fingerprint` 去重预览；
- supplement 的 `concept_clusters.ap_unit` 主导 Unit 校验；
- 输出每个 group 的成员、题目数、唯一题数、重复组、错误/警告。

GATE G2：

- `errors=0`。
- 如果有 Unit 映射 `WARN`，必须人工确认后才能 apply。
- 如果知识库没有概念层，`validation.enabled=false`，但必须人工核对 Unit 归属。

### Stage 3 — apply

```bash
python3 _tools/merge_unit_practice.py \
  --config config/practice_groups/<subject_id>.json
```

只重建一个 group：

```bash
python3 _tools/merge_unit_practice.py \
  --config config/practice_groups/<subject_id>.json \
  --group-id <group_id>
```

写库路径：

- `config/practice_groups/<subject_id>.json` 的 `exam_db` / `knowledge_db` 必须指向
  `data/content/<subject_id>/<subject_id>_exam.db` / `<subject_id>_knowledge.db`；
- 不用 `--config` 的 legacy 单 group 模式会按 `--subject-id`（默认 psychology）读取
  `config/subjects/<subject_id>.json`，默认写该科目的源库；
- `--db` / `--knowledge-db` 可显式覆盖，仅用于临时检查或迁移。

写库内容：

```text
practice_groups
practice_group_papers
paper_question_map
questions.question_fingerprint
papers（仅 bundle 虚拟卷）
```

GATE G3：

- 写库前已备份。
- 事务提交失败必须回滚。
- bundle 的 `question_count` = 唯一题数。
- 不新增重复 `question_id`。

### Stage 4 — QA

```sql
-- group / bundle 计数
SELECT g.group_id, g.unit_id, g.status, g.bundle_paper_id,
       p.question_count
FROM practice_groups g
JOIN papers p ON p.paper_id = g.bundle_paper_id
ORDER BY CAST(g.unit_id AS INTEGER);

-- 成员顺序
SELECT gp.group_id, gp.sort_order, gp.role, gp.paper_id,
       p.question_count
FROM practice_group_papers gp
JOIN papers p ON p.paper_id = gp.paper_id
ORDER BY gp.group_id, gp.sort_order;

-- bundle 来源块
SELECT source_paper_id, COUNT(*) n,
       MIN(sort_order) first_order, MAX(sort_order) last_order
FROM paper_question_map
WHERE paper_id = '<bundle_paper_id>'
GROUP BY source_paper_id
ORDER BY first_order;

-- 重复 fingerprint
SELECT question_fingerprint, COUNT(*) n
FROM questions
WHERE question_fingerprint IS NOT NULL
GROUP BY question_fingerprint
HAVING n > 1;

-- 跨 Unit 重复（同一 fingerprint 出现在多个 bundle）
SELECT q.question_fingerprint, COUNT(DISTINCT m.paper_id) bundle_count
FROM paper_question_map m
JOIN questions q ON q.question_id = m.question_id
GROUP BY q.question_fingerprint
HAVING bundle_count > 1;
```

GATE G4：

- `integrity_check = ok`
- `foreign_key_check` 无输出
- 每个 active group 只有一个 primary；`needs_review` group 没有 primary
- 每个 bundle 的映射数 = `papers.question_count`
- primary 题在前，supplement 按配置顺序追加
- 跨 Unit 重复 fingerprint 已列入报告；`on_cross_group_duplicate='error'` 时已阻断
- 没有题目被复制

### Stage 5 — 报告

脚本自动写：

```text
data/content/psychology/reports/knowledge/practice_merge_<group_id>.md
data/content/psychology/reports/knowledge/practice_merge_summary.md
```

报告必须包含：

- 配置路径、课程标准范围
- 每个成员的 role / 题目数 / 进入 bundle 的唯一题
- Unit 校验表（目标 Unit / 主导 Unit / 占比 / 结果）
- 重复 fingerprint
- group 状态（`active` / `needs_review`）
- 数据表计数

---

## 五、新增学科的最短路径

```text
1. 确认官方题库卷和教材章节卷都已入库，paper_type='unit_practice'
2. 按官方课程标准列出 Unit → 章节映射
3. 复制 config/practice_groups/psychology.json 为 <subject_id>.json
4. 改 subject_id / 数据库路径 / group / bundle / members
5. 跑 --dry-run，修到 errors=0
6. 正式 apply
7. 跑 QA SQL
8. 学生端只读 active group 的 bundle_paper_id
```

如果新学科还没有概念层：

```text
validation.enabled = false
```

但必须人工核对课程标准的 Unit 归属；等概念层建好后再打开校验。

---

## 六、输出契约

```json
{
  "subject_id": "psychology",
  "groups": [
    {
      "group_id": "psychology-unit1-practice",
      "unit_id": "1",
      "status": "active",
      "bundle_paper_id": "psychology-unit1-practice-bundle",
      "question_count": 345,
      "members": 4,
      "duplicate_groups": 0
    }
  ],
  "validation": {
    "errors": 0,
    "warnings": 0
  }
}
```

---

## 七、停止条件

遇到以下情况立即停止，不写库：

- 一个 group 有 0 个或 2 个以上 primary。
- 同一个 paper 被分到多个 Unit。
- supplement 的主导 `ap_unit` 与目标 Unit 不一致，且 `on_mismatch='error'`。
- 跨 Unit 重复 fingerprint 且 `on_cross_group_duplicate='error'`。
- `bundle_paper_id` 与普通 paper 冲突。
- 成员卷不是 `unit_practice` 且没有显式 override。
- 写库前备份失败。
- 写库后 `integrity_check` 或 `foreign_key_check` 失败。

---

## 八、最终检查清单

- [ ] 配置在 `config/practice_groups/<subject_id>.json`
- [ ] 每个 active Unit 恰好一个 primary；没有 primary 的标 `needs_review`
- [ ] primary 题在前，supplement 按配置顺序
- [ ] 没有复制题目
- [ ] bundle 只通过 `paper_question_map` 引用
- [ ] Unit 映射与官方课程标准一致
- [ ] 没有官方题库的 Unit 标 `needs_review`
- [ ] `--dry-run` 通过
- [ ] 已备份
- [ ] `integrity_check` / `foreign_key_check` 通过
- [ ] 报告已生成
- [ ] 学生端只展示 active group，不显示题库选择

---

## 九、本项目实现映射

- 脚本：`_tools/merge_unit_practice.py`
- 配置：`config/practice_groups/<subject_id>.json`
- 配置说明：`config/practice_groups/README.md`
- 表：`practice_groups` / `practice_group_papers` / `paper_question_map`
- 字段：`questions.question_fingerprint`
- 报告：`data/content/psychology/reports/knowledge/practice_merge_<group_id>.md` / `practice_merge_summary.md`
- 总调度：`prompts/00_data_agent_pipeline.md` Playbook C

---

## 十、最短使用方式

```text
请按 prompts/06_unit_practice_merge.md 执行。
学科：<subject_id>
配置：config/practice_groups/<subject_id>.json
模式：先 dry-run，确认后再 apply
```
