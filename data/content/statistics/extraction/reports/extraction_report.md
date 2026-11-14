# Barron's AP Statistics Premium 2027 知识点抽取报告

## 书籍

- `book_id`: `statistics-barrons-2027`
- 书名: AP Statistics Premium, 2027
- 作者: Martin Sternstein
- 出版社: Barron's Educational Series (Kaplan)
- ISBN: 979-8-3497-0157-3
- PDF 页数: 890；文本层：有；未使用 OCR

## 结构覆盖

- Units: 5
- Section rows: 49（含 Reference 5 节）
- 排除: `Graphical Displays`、`Guide to Inference`（纯图片公式页）
- 已排除习题 / 答案 / 模拟卷 / 50 Misconceptions 等非知识点章节

## 知识点覆盖

- Knowledge points: 267
- approved: 267
- needs_review: 0
- 有 KP 的正文 section: 47 / 47（2 个图片参考页 excluded）
- 分布: Unit 1=105, Unit 2=47, Unit 3=44, Unit 4=28, Unit 5=21, Reference=22

## 引用与通俗解释

- `definition_quote` 空白规范化后逐字匹配率: 100%
- `plain_en` 词数范围: 3–10；全部 ≤10 个英文单词
- 所有 KP 带 `book_id/section_id/source_page/quote_hash`

## 去重

- 同名同引文精确重复: 0 组
- 一句定义两个概念（拆分共享引文）: 12 组 / 24 条
- 同名不同定义: 1 组（均为跨节复现，已保留）
- 跨书重复: 不适用（当前只有一本统计学教材）

## GATE

| Gate | 结果 |
|---|---|
| G0 书籍可读 / 学科归类 | pass |
| G1 目录与正文标题对账 | pass |
| G2 section 切分 / 无跨节 | pass |
| G3 subheading 覆盖 | pass（无子标题，section 级覆盖 100%） |
| G4 引文逐字校验 | pass |
| G5 plain_en ≤10 words | pass |
| G6 全书去重 | pass（exact duplicate = 0） |
| G7 事务写库 / FK / integrity | pass |

## 产物

- `data/content/statistics/extraction/kp_all.json`
- `data/content/statistics/extraction/sections/*.txt`
- `data/content/statistics/extraction/kp/unit*.json`
- `data/content/statistics/extraction/reports/dedupe_report.md`
- `data/content/statistics/extraction/reports/validation_issues.csv`
- `data/content/statistics/extraction/reports/knowledge_import_report.md`
