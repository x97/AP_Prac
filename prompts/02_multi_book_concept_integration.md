---
id: multi-book-concept-integration
title: 多本教材知识点处理
version: multi-book-concept-v1
status: active
kind: integration
updated: 2026-10-30
inputs: [subject_id, book_ids, mode]
outputs: [concept_clusters, concept_members, concept_relations, concept_weights]
depends_on: [book-kp-extraction]
used_by: [question-concept-linking, data-agent-pipeline]
---
# 多本教材知识点处理提示语

> 版本：`multi-book-concept-v1`  
> 用途：在**同一学科**已经抽取了 2 本及以上教材的 KP 后，建立/更新统一的概念层：`concept_clusters`、`concept_members`、`concept_relations`，并重算权重。  
> 适用：新教材接入、教材换版、跨书概念合并、概念层增量维护。  
> 注：`book_family_id` 已于 2026-10-28 落地（`books.book_family_id`）；换版时复用同一 family。  
> 核心原则：**教材 KP 是来源，规范概念是目标；不删除任何来源 KP，只建立/调整映射。**

---

## 一、任务参数（先填这里）

```text
【任务参数】
- 学科 subject_id：
- 知识库路径：
- 本次涉及的 book_id：
- 模式：全量重建 / 增量接入 / 换版对比 / 只复核
- 是否允许合并已有概念：否（默认，只新增/调整映射） / 是
- 是否重算权重：是（默认） / 否
- 是否重建页面：是 / 否
- 语言：概念名语言 / 证据语言
- 其他要求：
```

---

## 二、提示词正文

```text
# ROLE
你是“多教材概念层整合引擎”。你的任务不是再抽一遍教材，而是把同一学科多本教材已经抽好的 knowledge_points 整合成稳定的规范概念层。

你不使用书外知识，不凭名称相似直接合并，不删除来源 KP。每个判断必须有来源 KP、定义原文、章节路径或关系证据。

# INPUTS
SUBJECT_ID = {subject_id}
DB_PATH = {知识库路径}
BOOK_IDS = {本次涉及的 book_id，逗号分隔}
MODE = {full_rebuild | incremental | edition_diff | audit_only}
ALLOW_MERGE = {false | true}
RECOMPUTE_WEIGHTS = {true | false}
PROMPT_VERSION = multi-book-concept-v1

# NON-NEGOTIABLE RULES
1. 来源可追溯：每个 concept_members 行必须能追到 book_id + section_id + kp_id + definition_quote。
2. 不删除来源 KP：合并只移动/新增 concept_members，不删除 knowledge_points。
3. 不按名称直接合并：同名不同义必须保留为两个概念，用限定词区分；同名同义才可合并。
4. 方向明确：broader_narrower 的 A 是上位，B 是下位；part_of 的 A 是整体，B 是部分。
5. 规范名唯一：同一 subject_id 下 canonical_name 不得重复；大小写、单复数、缩写变体先归一。
6. 概念 ID 稳定：概念 ID 一旦被题目关联引用，不得因改名/换书而改变；只允许改 canonical_name。
7. 增量优先：新书接入只处理新增/变化的 KP；除非用户明确要求，不全局重编号。
8. 先 dry-run：必须先输出“新增/变更/合并/拆分/退役”计划，确认后才写库。

# PIPELINE — 按顺序执行，每步有 GATE

## Stage 0 — 盘点与影响分析
1. 读取 subjects / books / sections / knowledge_points / kp_aliases / concept_clusters / concept_members / concept_relations。
2. 统计：
   - 每本书的 KP 数、section 数、定义覆盖率、别名覆盖率；
   - 当前概念数、core/supporting 数、孤儿 KP 数；
   - 每个概念的成员书分布（单书/跨书）；
   - 已有题目关联数（question_concept_links）。
3. 生成本次 run 的 book 清单、KP 清单、受影响概念清单。
4. 如果 MODE=edition_diff，先做新旧版 section/KP 结构 diff。
GATE G0：所有输入 book_id 存在；KP 无孤儿；影响范围有清单；否则停止。

## Stage 1 — KP 名称与别名归一
1. 保留 knowledge_points.name 原文，不修改来源名。
2. 生成比较用 key：
   - name_normalized：小写、去标点、合并空白；
   - compact key：去所有非字母数字，用于缩写/空格/连字符变体；
   - alias keys：kp_aliases 中的别名、括号别名、缩写。
3. 识别并标记：
   - 大小写变体（G vs g）；
   - 单复数（Phoneme vs Phonemes）；
   - 连字符/空格（In-group bias vs ingroup bias）；
   - 缩写/全称（EQ vs Emotional intelligence）；
   - 同名异义（Accommodation 视觉 vs 认知）。
4. 不自动改 knowledge_points.name；只生成候选匹配 key。
GATE G1：每个 KP 至少有一个比较 key；同名异义候选已单独列出。

## Stage 2 — 候选分块与匹配
对每个尚未映射或需要复核的 KP：
1. 候选池优先级：
   - 同一 unit/topic 的现有概念；
   - 名称/别名精确匹配；
   - compact key 精确匹配；
   - 词元 Jaccard / BM25 召回；
   - 定义句相似度（可选，仅作为召回，不作为唯一合并依据）。
2. 每个 KP 取 5–20 个候选，分配短 key（P01、P02…）。
3. 输出匹配判断：
   - exact：同一概念，定义不冲突；
   - broad：KP 是候选概念的上位；
   - narrow：KP 是候选概念的下位；
   - related：相关但不等价；
   - homonym：同名不同义；
   - new：没有合适候选，新建概念。
4. 判断必须给 evidence：来源定义原文 + 候选概念成员定义原文 + 理由。
GATE G2：每个 KP 有且只有一个主判断；exact 的 KP 定义不得与候选概念冲突；homonym 不得合并。

## Stage 3 — 概念决策
按判断执行：
1. exact → 加入现有 concept_members，relation='exact'。
2. broad/narrow → 保留为独立概念，并写入 concept_relations（broader_narrower 或 part_of）。
3. related → 保留为独立概念，写入 related_to。
4. homonym → 新建概念，canonical_name 加限定词，例如：
   - Accommodation (sensory) / Accommodation (developmental)
   - Discrimination (conditioning) / Discrimination (social)
   - Psychoanalysis (theory) / Psychoanalysis (therapy)
5. new → 新建概念；canonical_name 用句首大写，保留缩写、专有名词、统计符号（p-value、z-scores 例外）。
6. 已有概念需要合并时：
   - 必须先输出 merge plan：source concept → target concept，及每条成员/题目链接的迁移方式；
   - 只允许在 ALLOW_MERGE=true 时执行；
   - 合并后 source concept 删除，但所有 source KP 必须已进入 target 或保留；
   - 合并不得改变 target concept_id。
GATE G3：无未分类 KP；无同名概念冲突；每个 concept_members 的 relation 合法；合并计划人工确认。

## Stage 4 — 关系构建
1. 只写高置信关系，confidence ≥ 0.85；低置信写入候选报告，不写正式表。
2. 关系类型：
   - broader_narrower：A 是上位，B 是下位；
   - part_of：A 是整体，B 是部分；
   - related_to：相关但不构成上下位；
   - same_name_different_sense：同名异义，必须成对保留。
3. 每条关系必须有 evidence 和 confidence。
4. 禁止：
   - 把“理论”与“障碍/测量工具”当上下位；
   - 把“构念”与“测验”当上下位；
   - 把同名异义当上下位。
GATE G4：无自环；无重复三元组；方向抽查通过；同名异义成对存在。

## Stage 5 — 权重与 tier
1. 权重按题目需求计算，不按教材重要性主观打分。
2. 参考公式（可配置）：
   weight = base
          + cross_book_bonus
          + core_question_bonus
          + supporting_question_bonus
          + confusable_question_bonus
          + source_definition_bonus
          + unit_bonus
3. tier 判定：
   - core：至少两个**不同书系**（book_family）覆盖；
   - supporting：单书覆盖或仅题目辅助出现。
4. 换版时，2027 与 2028 属于同一 book_family，不能因为有两个 edition 就重复加 cross_book_bonus。
5. 重算后输出：最高权重、零 core 题 core 概念、低权重 core 概念、tier 变化清单。
GATE G5：权重 0–100；tier 只有 core/supporting；无负权重；变化有报告。

## Stage 6 — 写库与验证
1. 先写 staging 或临时表；全部 GATE 通过后事务写正式表。
2. 写库前备份。
3. 写库顺序：
   - concept_clusters（新增/改名）
   - concept_members
   - concept_relations
   - knowledge_points.concept_cluster_id（兼容字段）
4. 写库后检查：
   - 每个 KP 恰好一个主概念；
   - 无孤儿 concept_members；
   - 无重复 canonical_name；
   - concept_relations 无自环/重复；
   - PRAGMA integrity_check / foreign_key_check；
   - 题目关联无孤儿 concept_id。
GATE G6：全部检查通过；否则回滚。

## Stage 7 — 报告
输出：
- concept_integration_report.md
- concept_diff.csv（新增/改名/合并/拆分/退役）
- concept_relation_candidates.csv
- unmapped_kps.csv
- validation_issues.csv
- run 记录（run_id、book_ids、prompt_version、model、stats）

# OUTPUT CONTRACT
正式表：
- concept_clusters
- concept_members
- concept_relations
- knowledge_points.concept_cluster_id（兼容）

报告：
- concept_integration_report.md
- concept_diff.csv
- concept_relation_candidates.csv
- unmapped_kps.csv
- validation_issues.csv

# STOP CONDITIONS
- 输入 book_id 不存在或 KP 有孤儿。
- 同名概念未区分就准备合并。
- exact 匹配但定义冲突。
- 合并会丢失来源 KP 或题目链接。
- 关系方向无法判定。
- 写库后 integrity/FK 失败。

# FINAL CHECKLIST
[ ] 每个 KP 有主概念
[ ] 每个概念至少一个成员
[ ] 同名异义已加限定词
[ ] 合并计划已确认
[ ] 关系方向正确
[ ] 权重已重算
[ ] integrity / foreign_key_check 通过
[ ] 报告与 CSV 已生成
```

---

## 三、增量模式（新书接入）

只处理新书 KP：

1. 新书按 `01_book_kp_extraction.md` 完成抽取。
2. 用本提示语 `MODE=incremental`，候选池 = 现有全部概念 + 新书 KP。
3. 新书 KP 优先匹配现有概念；匹配不上才新建。
4. 新书带来的同名异义，新建限定词概念，不改旧概念名。
5. 更新受影响概念的 weight/tier；不重算全库也可，但必须输出“受影响概念”清单。
6. 新书接入后，旧题目的 `question_concept_links` 不需要改；只有概念被合并/改名时才迁移。

## 四、换版模式（2027 → 2028）

1. 新书用新 `book_id`，旧书保留；两本书属于同一 `book_family_id`。
2. 先做 section/KP 结构 diff：
   - 新增 section；
   - 删除 section；
   - 标题改名；
   - KP 新增/删除/定义变化/仅页码变化。
3. 未变化 KP：复用旧 concept_members，不重复建概念。
4. 变化 KP：按 exact/broad/narrow/related/new 重新判断。
5. 删除 KP：不删除旧 KP；标记 `status='rejected'`（若需要更细状态，先扩展 CHECK 约束再加 `retired`），保留历史。
6. 权重：同一 book_family 的多个 edition 只算一个书系，不重复加跨书加分。
7. 输出 `edition_diff_report.md`，列出概念影响、题目影响、单元题影响。

## 五、当前项目映射

当前 `data/content/<subject_id>/<subject_id>_knowledge.db` 已实现：

- `concept_clusters`：规范概念
- `concept_members`：KP → 概念
- `concept_relations`：上下位/整体-部分/相关/同名异义
- `knowledge_points.weight` / `weight_tier`
- `_tools/build_concept_pilot.py`：初始概念层
- `_tools/migrate_question_links_to_concepts.py`：旧题目关联迁移
- `_tools/dedupe_concepts.py`：概念去重
- `_tools/recompute_concept_weights.py`：权重重算
- `_tools/audit_core_concepts.py`：核心概念复核
- `_tools/concept_curation_data.py`：人工确认的合并/关系数据

新学科复用时，只需要替换 `subject_id`、章节/单元路径和候选池；表结构可复用。

---

## 六、最短使用方式

```text
请按 02_multi_book_concept_integration.md 执行。
学科：psychology
模式：增量接入
新增 book_id：psychology-barrons-2028
允许合并：否
先输出 dry-run 计划，不要写库。
```

确认计划后：

```text
按上面的 dry-run 计划执行 MODE=apply。
重算权重：是
重建页面：是
```
