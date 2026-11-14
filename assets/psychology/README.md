# psychology 静态资源

> 所有心理学静态资源统一放在本目录。打开 `assets/` 先看到科目（`psychology/`），再进入该科目的资源类型。

```text
assets/psychology/
  papers/                 # 试卷、官方 FRQ、CB 题库 PDF；含答案 key（.txt/.doc）
    2015/ ... 2025/
    official_frq/2023..2025/
    cb/
  images/                 # 题目图、选项图、Barron/CB 裁图
    2018/ ... 2025/
    barron2027/
    barron2027_review/
    cb2026/
  books/                  # 教材 PDF
```

## 数据库对应关系

| 数据库字段 | 对应位置 |
|---|---|
| `ap_exam.db.assets.path` | `assets/psychology/images/...` |
| `ap_exam.db.paper_sources.path` | `assets/psychology/papers/...` 或 `books/...` |
| `ap_exam.db.content_sources.file_path` | `assets/psychology/papers/...` 或 `books/...` |
| `ap_exam.db.papers.source_pdf` | 旧字段，已同步到新路径 |
| `ap_exam.db.questions.source_file` | 题目来源 PDF |
| `ap_knowledge.db.books.source_path` | `assets/psychology/books/...` |

## 规则

- 新增科目时建立 `assets/<subject_id>/`，不要混入 `psychology/`。
- 试卷 PDF 放 `papers/<year>/`；教材 PDF 放 `books/`；题目图片放 `images/<来源>/`。
- 移动/重命名文件后，必须同步数据库路径并重建页面。
- 路径统一使用相对项目根目录的写法。
