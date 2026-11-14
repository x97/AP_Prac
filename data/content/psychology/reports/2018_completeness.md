# 2018 AP Psychology 真题完整性

日期：2026-11-01

## 结论

2018 卷现在适合作为公开免费真题使用。MCQ 部分完整；FRQ 2 已补齐到 7/7，其中 Points 4–7 是根据题目和 AP Psychology 评分惯例人工重建，不是 College Board 原文。

## 数量

| 项目 | 现状 |
|---|---:|
| MCQ | 100 |
| MCQ 有答案 | 100 / 100（官方答案） |
| MCQ 有 AI 解析 | 100 / 100 |
| MCQ 有原书/官方解析 | 0（官方真题本身不提供逐题解析） |
| MCQ 有核心概念关联 | 100 / 100（Q77 已补） |
| FRQ | 2 |
| FRQ 1 rubric | 7 / 7 分完整 |
| FRQ 2 rubric | 7 / 7（Points 1–3 源文件；Points 4–7 人工重建） |
| 题图/表格素材 | 25 条引用 / 19 个唯一文件 |

## FRQ 2 评分点

| 评分点 | 来源 |
|---|---|
| 1. Self-fulfilling prophecy | 源 PDF |
| 2. Big Five trait of neuroticism | 源 PDF |
| 3. Superordinate goals | 源 PDF |
| 4. Metacognition | 人工重建 |
| 5. Token economy | 人工重建 |
| 6. Part C: mean score | 人工重建 |
| 7. Part C: distribution | 人工重建 |

源 PDF 的评分标准在 “Superordinate Goals” 之后截断。Points 4–7 是根据题目、图表和 AP Psychology 评分惯例重建的，已写入 `rubric_parts.notes` 和 General Scoring Notes 的 provenance 说明，**不是 College Board 原文**。

考试配置仍标记：

```text
frq_rubric_complete = false
expected_frq_points = 7
```

`frq_rubric_complete=false` 仅作为内部 provenance 标记，不在学生端显示提示。

## 其他说明

- 2018 MCQ 的 100 条解析全部是 `options.ai_explanation`，没有写入 `options.explanation`，页面会标注 AI 生成。
- Q77（酒精的常见心理效应）原本缺少概念关联，现已关联到 `Depressants`。
- 2018 作为免费真题后，2024 不再默认免费；2025 仍需要激活码。
- 免费配置：`config/entitlements/psychology.json`
  - `psychology-ap-2018`
  - `psychology-cb-2026-mock-1`（CB Mock，保留免费）

## 产物

- 当前 Release：`content-20261101-07`
- 2018 试卷：`psychology-ap-2018`
