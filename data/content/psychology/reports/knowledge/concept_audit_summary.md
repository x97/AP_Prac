# 393 个 core 概念复核 · 最终摘要

## 1. 复核口径

- `weight_tier=core` 表示 Barron 与 Myers 两本书都有对应 KP，是**课程覆盖标记**，不是考试频率。
- `weight` 由 core / supporting / confusable 题量、跨书、Myers 词表、单元和定义共同决定，反映考试需求。
- 因此，零 core 题的 core 概念不自动降级；报告标为 `curriculum_only`，考试优先级交给 weight。

## 2. 最终结果

| 项目 | 基线 | 复核后 |
|---|---:|---:|
| 规范概念 | 1,125 | **1,105** |
| core 概念 | 393 | **402** |
| supporting 概念 | 732 | **703** |
| 概念关系 | 0 | **209** |
| 权重 ≥70 的 core | 119 | **127** |
| 零 core 题的 core | 63 | **64** |
| KP 权重 | 801 core / 737 supporting | **827 core / 711 supporting** |

概念关系：上下位 132、整体-部分 55、相关 14、同名异义 8。

## 3. 关键发现

### 3.1 九个“伪 supporting”概念

复核发现 9 个概念原本被拆成 Barron/Myers 两条，合并后恢复跨书身份，因此从 supporting 变为 core：

`In-group bias`、`General intelligence (g)`、`Emotional intelligence`、`Antipsychotic drugs`、`Neuroplasticity`、`Double-blind procedure`、`Percentile rank`、`Phoneme`、`Random sampling`。

这是 core 从 393 变为 402 的唯一原因。

### 3.2 合并了 20 组重复

包括：

- `Modeling (Unit 5)` → `Modeling`
- `Hypothalamus (Unit 4)` → `Hypothalamus`
- `Token economy (Unit 3)` → `Token economy`
- `Unconditional positive regard (Unit 4)` → `Unconditional positive regard`
- `In-group bias` + `ingroup bias`
- `G` + `General intelligence ( g )` → `General intelligence (g)`
- `EQ` + `Emotional intelligence`
- `Antipsychotic medications` + `Antipsychotic drugs`
- `Brain plasticity` + `Neuroplasticity`
- `Double-blind study` + `Double-blind procedure`
- `Monozygotic (identical) twins` + `Identical twins (monozygotic twins)`
- `Percentiles` + `Percentile rank`
- `Phonemes` + `Phoneme`
- `Random sample` + `Random sampling`

完整清单见 `concept_audit_actions.md`。

### 3.3 同名异义保留为两个概念

共 8 组，已加限定词并写入 `same_name_different_sense`：

- Accommodation (sensory) / Accommodation (developmental)
- Discrimination (conditioning) / Discrimination (social)
- Psychoanalysis (theory) / Psychoanalysis (therapy)
- Autonomy (Erikson) / Autonomy (self-determination)
- Proximity (visual) / Proximity (attraction)
- Similarity (visual) / Similarity (attraction)
- Opponent-process theory (color vision) / Opponent-process theory (motivation)
- GRIT (conflict resolution) / Grit (perseverance)

### 3.4 高权重概念

前 10 名：

| 概念 | 权重 | core 题 |
|---|---:|---:|
| Correlation | 92.25 | 40 |
| Independent variable | 90.31 | 38 |
| Mean | 87.85 | 27 |
| Standard deviation | 87.83 | 34 |
| Dependent variable | 86.74 | 26 |
| Operant conditioning | 86.62 | 27 |
| Random assignment | 85.71 | 31 |
| Informed consent | 84.28 | 24 |
| Operational definition | 81.62 | 26 |
| Classical conditioning | 80.04 | 13 |

高权重概念整体可靠。`Correlation`、`Validity`、`Learning`、`Motivation` 等 umbrella 保留为父概念，不降级；其下位关系写入 `concept_relations`。

### 3.5 命名修正

- 所有概念名统一为句首大写；保留统计符号 `p-value`、`z-scores` 的小写写法。
- 特殊修正：`Amygdala and hippocampus` → `Amygdala`、`Blind sight` → `Blindsight`、`Smell (or Olfaction)` → `Smell (Olfaction)`、`Operational definitions` → `Operational definition`、`Intrinsic motivations` → `Intrinsic motivation` 等。
- 复核后：首字母小写 core = 0，归一化同名重复 = 0，含 `(Unit X)` 的概念 = 0。

## 4. 验证

- `ap_knowledge.db`：`integrity_check=ok`，`foreign_key_check=OK`。
- 概念：1,105（402 core + 703 supporting）；全部 1,538 条 KP 仍映射，无孤儿。
- 题目关联：`question_concept_links` 7,371 条 / 2,837 题。
- 关系：209 条；`concept_relations` 表已建索引。
- 页面：23 个刷题页重建，2,323 张核心概念卡均有来源和权重；JS 语法检查通过。
- 知识库查看器已重建。

## 5. 产物

- 基线报告：`data/content/psychology/reports/knowledge/concept_audit_report.md`
- 基线 CSV：`data/content/psychology/reports/knowledge/concept_audit_baseline.csv`
- 最终 CSV：`data/content/psychology/reports/knowledge/concept_audit_final.csv`
- 关系清单：`data/content/psychology/reports/knowledge/concept_relation_candidates.csv`
- 执行记录：`data/content/psychology/reports/knowledge/concept_audit_actions.md`
- 复核后检查：`data/content/psychology/reports/knowledge/concept_audit_postcheck.md`
- 权重重算：`data/content/psychology/reports/knowledge/concept_weight_report.md`

## 6. 未做的事

- 没有因为“零 core 题”把 core 概念降级；core 仍表示跨书覆盖。
- 没有删除任何概念成员或题目关联；合并只移动成员/链接到主概念。
- 没有把 `Risk`、`Schizophrenia`、`Positive correlation` 等高需求 supporting 概念强行升为 core；它们通过关系表挂到上位概念，考试优先级仍由 weight 表达。
