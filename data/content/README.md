# data/content

每个科目的内容源与生产产物都放在这里。

```text
data/content/<subject_id>/
  <subject_id>_exam.db        # 题库：试卷 / 题目 / 选项 / rubric
  <subject_id>_knowledge.db   # 知识点 / 概念 / 关系
  extraction/                 # 解析、OCR、AI 中间产物（可重建）
  reports/                    # 覆盖报告、QA、概念审计
  assets/                     # 可选：该科目自己的图片等资源
```

规则：

- `<subject_id>_exam.db` / `<subject_id>_knowledge.db` 是权威源库，直接编辑这两个文件。
- `extraction/`、`reports/` 不进入 Release，只用于复核和重建。
- 科目注册在 `config/subjects/<subject_id>.json`。
- 发布时运行 `_tools/build_merged_release.py`，产物在 `data/releases/`。
- 新 PDF 的完整操作见 `docs/content/新增试卷解析流程.md`。
- 根目录不再保留 `ap_exam.db` / `ap_knowledge.db` 兼容链接。
- 静态刷题页已移除；学生端使用 `apps/web`，只读 active Release。

当前科目：

```text
psychology/    # 已启用
statistics/    # enabled=false，概念层未完成
```

目录内的历史报告可能引用旧的 `AP_exam/` 路径；以本 README 和 `config/subjects/*.json` 为准。
