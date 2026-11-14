# Barron's AP Statistics Premium 2027 — 数据接入

来源：`assets/statistics/books/AP Statistics Premium, 2027 - Martin Sternstein.pdf`（890 页，有文本层）。

## 结果

| 层 | 数量 | 位置 |
|---|---:|---|
| Units | 5 + Reference | `statistics_knowledge.db.sections` |
| 正文小节 | 44（2 个图片参考页 excluded） | `statistics_knowledge.db.sections` |
| 知识点 | 267（全部 approved） | `statistics_knowledge.db.knowledge_points` |
| 知识点别名 | 57 | `statistics_knowledge.db.kp_aliases` |
| 教材练习卷 | 34 Quiz + 1 Diagnostic + 4 Practice Test = 39 | `statistics_exam.db.papers` |
| 题目 | 613（MCQ 447 / FRQ 166） | `statistics_exam.db.questions` |
| 选项 | 1,788 | `statistics_exam.db.options` |
| 题图/公式图 | 439 引用 / 371 唯一文件 | `assets/statistics/images/stats2027/` |

## 关键 ID

- `subject_id`: `statistics`
- `book_id`: `statistics-barrons-2027`
- `book_family_id`: `statistics-barrons-ap-statistics`
- `source_id`: `statistics-barrons-2027`
- 试卷：`statistics-barrons-2027-quiz-01` … `quiz-34`、`-diagnostic`、`-pt1` … `-pt4`
- 题目：`<paper_id>-001` … 按卷内顺序编号

## 数据约定

- 知识点定义全部来自教材原文；`definition_quote` 空白规范化后逐字匹配，`quote_hash` 可复核。
- 一句原文定义两个概念时拆成两条 KP（如 Parameter/Statistic、Frequency/Relative frequency），用 `covers_concepts` 记录共享关系。
- `plain_en` 全部为 1–10 个英文单词。
- Quiz 1–30 为 MCQ + FRQ；Quiz 31–34 只有 FRQ。
- 教材练习卷 `paper_type='unit_practice'`；诊断卷与 4 套 Practice Test 为 `mock_exam`。
- 答案/解析来自本书 Answer Explanations；正确选项同步写入 `options.explanation`。
- 选项本身是公式图片时，`options.content='[see image]'` 并挂 `assets(kind='option')`；题图只裁图表区域，不使用整页截图。
- `frq_rubrics` 未伪造：原书没有正式评分点表的部分只保存 `questions.answer_text` 模型解答。

## 已知缺失（原书）

- `statistics-barrons-2027-quiz-23` Q5：原书缺少 A–D 选项内容，标记 `[source missing choices]`。
- `statistics-barrons-2027-quiz-26` FRQ 3：原书未提供解答。
- 8 道 MCQ 的解析在原书中仅为公式/图片，无文字 `answer_text`；答案本身完整。

## 复核

```bash
# 知识点：数量、状态、词数
sqlite3 data/content/statistics/statistics_knowledge.db "
SELECT COUNT(*), SUM(status='approved') FROM knowledge_points
WHERE book_id='statistics-barrons-2027';"

# 题库：试卷与题目统计
sqlite3 data/content/statistics/statistics_exam.db "
SELECT paper_type, COUNT(*), SUM(question_count)
FROM papers WHERE subject_id='statistics' GROUP BY paper_type;"

# 完整性
sqlite3 data/content/statistics/statistics_knowledge.db "PRAGMA integrity_check; PRAGMA foreign_key_check;"
sqlite3 data/content/statistics/statistics_exam.db "PRAGMA integrity_check; PRAGMA foreign_key_check;"
```

详细报告见 `reports/`：

- `extraction_report.md`
- `dedupe_report.md`
- `question_qa_report.md`
- `knowledge_import_report.md`
- `question_import_report.md`
- `stats_pipeline_report.md`
- `validation_issues.csv`

## 脚本

- `_tools/stats_extract_sections.py` — 目录/小节切分与文本导出
- `_tools/stats_parse_questions.py` — Quiz/Diagnostic/Practice Test 解析
- `_tools/stats_validate_kps.py` — 知识点逐字校验/ID/去重统计
- `_tools/stats_import_knowledge.py` — 写入 `statistics_knowledge.db`
- `_tools/stats_import_questions.py` — 写入 `statistics_exam.db` 并裁切题图
- `_tools/stats_write_reports.py` — 生成 QA 报告
