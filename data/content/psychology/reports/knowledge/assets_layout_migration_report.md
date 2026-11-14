# 静态资源目录迁移报告

> 日期：2026-10-28  
> 结果：已完成；幂等复跑 0 变更。

## 结果

| 项目 | 数量 |
|---|---:|
| 首次迁移文件 | 599 |
| 首次 DB 路径变更 | 445 |
| 清理空目录 | 22 |
| 缺失路径 | 0 |
| 幂等复跑变更 | 0 |
| 当前 `assets/psychology` 文件 | 600（含 README） |
| DB `assets` 引用 | 355 |

## 目标结构

```text
assets/
  psychology/
    papers/       # 真题、官方 FRQ、CB 题库 PDF；含答案 key
      2015/ ... 2025/
      official_frq/2023..2025/
      cb/
    images/       # 题目图、选项图、Barron/CB 裁图
      2018/ ... 2025/
      barron2027/
      barron2027_review/
      cb2026/
    books/        # 教材 PDF
```

当前分类：

| 目录 | 文件数 |
|---|---:|
| `assets/psychology/papers` | 36 |
| `assets/psychology/images` | 561 |
| `assets/psychology/books` | 2 |
| 合计 | 600（含 README） |

## 同步的 DB 字段

- `ap_exam.db.assets.path`
- `ap_exam.db.paper_sources.path`
- `ap_exam.db.content_sources.file_path`
- `ap_exam.db.papers.source_pdf`
- `ap_exam.db.questions.source_file`
- `ap_knowledge.db.books.source_path`

全部路径均验证存在，缺失 0。

## 规则

- 新科目使用 `assets/<subject_id>/`。
- 试卷 PDF 放 `papers/<year>/`；教材 PDF 放 `books/`；题目图片放 `images/<来源>/`。
- 移动文件后必须同步上述 DB 字段并重建页面。
- 迁移脚本：`_tools/migrate_assets_layout.py`（默认 dry-run，`--apply` 执行）。
