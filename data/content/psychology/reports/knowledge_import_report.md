# 知识点库导入报告（ap_knowledge.db）

- 导入日期：2026-10-26
- 书籍：`psychology-barrons-2027`
- 数据源：`data/content/psychology/reports/kp/知识点抽取_102节.json` + `data/content/psychology/reports/knowledge/unit*_plain_en.json`
- 提示语版本：`migration-102-v1`
- 导入方式：复用现有 860 条已校验知识点，英文通俗解释由 6 个单元分别改写为 ≤10 词

## 数量

| 项目 | 数量 |
|---|---:|
| 目录知识点块（level 2） | 102 |
| 树节点总数（6 units + 18 chapters + 102 sections + 184 subheadings） | 310 |
| 知识点 | 860 |
| 研究者关联 | 194 |
| 同概念/近重复/同形异义关系 | 36 |
| `section_texts` 页级文本 | 326 |
| 精确重复定义组 | 0 |

## 校验结果

| 检查 | 结果 |
|---|---|
| `PRAGMA foreign_key_check` | 通过 |
| `PRAGMA integrity_check` | `ok` |
| 目录块无知识点 | 0 |
| 子标题未覆盖 | 0 |
| 原文定义逐字匹配（忽略空白） | 860/860 |
| `plain_en` 2–9 个英文单词（严格小于 10） | 860/860 |
| `quote_hash` 为空 | 0 |
| `plain_en` 为空 | 0 |
| `section_id` 为空 | 0 |
| `source_page` 超出 section 页范围 | 0 |
| 精确重复 `quote_hash` 组 | 0 |

## 状态分布

| 字段 | 分布 |
|---|---|
| `status` | `approved` 859；`needs_review` 1 |
| `definition_type` | `explicit` 784；`implicit` 76 |
| `kp_relations.relation_type` | `same_concept` 27；`homonym` 7；`near_duplicate` 2 |

`needs_review` 的 1 条是 `figure-ground relationship`：教材原文用问句解释（“What part of a visual image is the figure...?”），定义类型标为 `implicit`，置信度 0.65，保留待人工复核。

## 说明

- 这次是**迁移**，不是重新抽取：原文定义、研究者、102 节结构沿用此前已校验的结果。
- 通俗解释统一改为英文，并全部控制在 10 个单词以内；原中文解释仍保留在 `data/content/psychology/reports/kp/知识点抽取_102节.json` / `.md` 中，便于对照。
- `section_texts` 为页级原文；跨页/连字符导致的空白差异在引用校验时按“忽略全部空白”处理。
- 旧版 `textbook.db`、旧 KP 流水线与旧报告已归档到 `_archive/`。
