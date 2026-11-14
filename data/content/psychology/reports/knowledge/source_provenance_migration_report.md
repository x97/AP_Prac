# 来源追溯 / book_family 迁移报告

- 时间：2026-10-28T11:16:20+08:00
- `ap_knowledge.db` integrity：ok
- `ap_knowledge.db` foreign_key_check：OK
- `ap_exam.db` integrity：ok
- `ap_exam.db` foreign_key_check：OK
- books 更新：2
- content_sources 映射到 book：2
- paper_book_sources：18
- question_sources：391

## Books

| book_id | book_family_id | status | edition |
|---|---|---|---|
| `psychology-barrons-2027` | `psychology-barrons-ap-psychology` | `active` | `2027` |
| `psychology-myers-2024` | `psychology-myers-ap-psychology` | `active` | `4th` |

## 映射

| source_id | book_id |
|---|---|
| `psychology-barrons-2027` | `psychology-barrons-2027` |
| `psychology-myers-2024` | `psychology-myers-2024` |

## 说明

- `books.book_family_id` 用于教材换版：同一教材的 2027/2028 属于同一 family。
- `books.status` 当前全部为 `active`；旧版可改为 `archived`。
- `paper_book_sources` 记录试卷来自哪本教材；`question_sources` 记录题目来自哪本教材/页码。
- `content_sources.book_id` 是逻辑引用，跨库不建外键。
- 现有 `paper_sources` 仍然表示“试卷 → 源文件”，不要与 `paper_book_sources` 混淆。
