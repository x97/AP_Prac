# Unit 1 知识点关系审计

日期：2026-11-01

## 结论

要改，但优先改“边的语义”，不是先改图形。当前 Unit 1 的显式关系主要来自教材层级（part_of / broader_narrower），只能表达“谁属于谁”；它不足以支撑错题推荐、FRQ 关联提示和复习排序。考试层面真正有价值的关系，需要单独建层并保留来源。

## 当前数据（Unit 1，225 个概念 / 27 个教材章节）

| 关系层 | 数量 | 来源 | 是否跨章节 | 说明 |
|---|---:|---|---:|---|
| 教材显式关系 | 35 | `concept_relations` | 5 | 26 条 part_of、8 条 broader_narrower、1 条 related_to |
| 真题易混 | 82（权重 ≥ 2） | 同一题中的 core 概念 vs confusable 干扰概念 | 7 | 共 240 个候选对；按出现次数合并 |
| 同题共现 | 154 | 同一题中的 core + supporting 概念 | 18 | 只做“常一起考”，不等于语义关系 |
| 前置依赖 | 0 | — | — | 当前没有可靠来源，不自动生成 |
| 同框架 | 0 条边 | 章节软分区 | — | 用 27 个章节区域表达，而不是两两连边 |
| 跨单元应用 | 0 | — | — | 当前 Unit 1 原型未建跨单元层 |

高频易混示例：

- 副交感神经系统 ↔ 交感神经系统（同一题 18 次）
- 视杆细胞 ↔ 视锥细胞（8 次）
- 对立过程理论 ↔ 三色论（8 次）
- 睡眠呼吸暂停 ↔ 嗜睡症（7 次）
- 小脑 ↔ 下丘脑（7 次）
- EEG ↔ PET（6 次）

## 问题

1. **层级边不是学习关系**：26 条 part_of 只说明组成，不能告诉学生“先学什么、哪里容易混、什么会一起考”。
2. **跨章节连接太少**：35 条教材关系里只有 5 条跨章节；82 条易混边里只有 7 条跨章节。图在视觉上仍偏“章节内网”。
3. **同题共现不能冒充语义关系**：共现只能说明考试场景一起出现，不能说明因果、前置或同框架，必须单独存储。
4. **FRQ 还没有概念链接**：当前 `question_concept_links` 覆盖 MCQ；FRQ 没有 concept link，因此无法生成 FRQ 共现边。
5. **缺少来源与状态**：如果以后让模型生成候选边，必须有 `source_type`、`source_ref`、`confidence`、`review_status`，不能直接进正式图。

## 建议的数据模型

```text
concept_edges
  edge_id
  subject_id
  source_concept_id
  target_concept_id
  relation_type          -- is_a / part_of / prerequisite / contrast /
                         -- same_framework / cross_unit_application / related_to
  direction              -- directed / symmetric
  source_type            -- textbook_relation / exam_confusable /
                         -- manual_review / llm_candidate
  source_ref             -- book_id + section_id / question_id / review_note
  evidence
  confidence
  review_status          -- approved / candidate / rejected
```

```text
concept_cooccurrence     -- 不与 semantic edge 混表
  subject_id
  source_concept_id
  target_concept_id
  scope                  -- same_mcq_core_support / same_mcq_core_confusable /
                         -- same_frq / same_unit_exam
  weight
  question_ids_json
  source_release_id
```

规则：

- `contrast` 是对称边；`prerequisite` 是有向边；`part_of` / `is_a` 是有向边。
- 同框架优先用章节/理论框架节点表达，不要把所有同章节概念两两连边。
- 共现边只用于推荐和排序，不进入“概念定义关系”计数。
- 模型只生成 `candidate`，人工审核后才能变成 `approved`；每条边保留原文或题目证据。

## 下一步

1. **保留** 35 条教材关系 + 82 条真题易混边，作为 Unit 1 的第一版可用关系层；原型已经用不同线型区分，并在右侧显示易混题号。
2. **人工补前置依赖**：先从教材的流程/阶段段落整理 20–40 条，如“神经元结构 → 动作电位”“感觉 → 知觉”；不要从层级自动推断成前置。
3. **同框架**：继续用 27 个章节软分区；如果以后要显示“理论框架”节点，再单独建 framework 节点，不增加章节内全连接。
4. **跨单元**：Unit 1 稳定后，用真题共现 + 明确因果句建跨单元层；先做 Unit 1 ↔ Unit 2/3 的高频连接。
5. **FRQ**：先给 2024/2025 FRQ 补 concept link，才能做 FRQ 共现和评分提示。

当前原型仍是静态预览；以上关系尚未写入正式 `concept_edges` 表。

## 展示层（2026-11-01 原型）

默认不再是 225 点全量图，而是三层：

1. **结构层**：8 个 CED Topic 节点，每个只露出 3 个核心概念（共 24 个点）、7 条跨 Topic 桥。
2. **Topic 层**：点击 Topic 打开该 Topic 的完整概念图（例如 The Brain 20 个概念）。
3. **概念层**：点击概念后只高亮一跳邻居，其余节点淡出；可“显示全图”恢复。

“全部 225”保留为可选高级视图，不默认展开；它使用 27 个教材章节软分区和 117 条语义/易混边。
