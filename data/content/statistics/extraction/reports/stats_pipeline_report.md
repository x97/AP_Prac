# 统计学教材接入 — 总报告

## 范围

- 教材：`AP Statistics Premium, 2027 - Martin Sternstein.pdf`（890 页）
- 任务：知识点抽取 + 教材练习题入库

## 结果

| 层 | 数量 |
|---|---:|
| 知识库 sections | 55 |
| 知识库 knowledge_points | 267（approved 267） |
| 题库 papers | 39 |
| 题库 questions | 613 |
| 题库 assets | 439 |

## 知识点

- 覆盖 Unit 1–5 的 44 个复习小节 + 5 个 Reference 小节（`Selecting an Appropriate Inference Procedure`、`Templates`、`Names of Procedures` 等）。
- 2 个纯图片参考页（`Graphical Displays`、`Guide to Inference`）标记 `excluded`，不生成 KP。
- 所有定义均来自本书原文；未使用书外知识补写。

## 练习题

- 34 份 Quiz（`unit_practice`）：Quiz 1–30 为 MCQ+FRQ，Quiz 31–34 为 FRQ。
- 1 份 Diagnostic Test + 4 份 Practice Test（`mock_exam`）。
- 答案与解析来自本书 Answer Explanations；正确选项同步写入 `options.explanation`。

## 待复核

- `statistics-barrons-2027-quiz-26` FRQ 3：原书未提供解答。
- `statistics-barrons-2027-quiz-23` Q5：原书缺少 A–D 选项内容。
- 8 道 MCQ：原书解析仅为公式/图片，无文字解析。

## 产物

- `data/content/statistics/extraction/reports/extraction_report.md`
- `data/content/statistics/extraction/reports/dedupe_report.md`
- `data/content/statistics/extraction/reports/question_qa_report.md`
- `data/content/statistics/extraction/reports/knowledge_import_report.md`
- `data/content/statistics/extraction/reports/question_import_report.md`
- `data/content/statistics/extraction/questions_all.json`
- `data/content/statistics/extraction/kp_all.json`
- `assets/statistics/images/stats2027/`
