# docs/content

内容生产相关的设计与方法文档。原 `AP_exam/` 目录已拆分并移除。

| 文档 | 用途 |
|---|---|
| `数据库设计文档.md` | 题库 / 知识库 schema、字段、表关系 |
| `试卷解析方法.md` | PDF 试卷解析、答案、解析、rubric、图片入库方法 |
| `新增试卷解析流程.md` | 新 PDF 的交互模板、目录、阶段、QA、写库与发布流程 |
| `ap_knowledge_schema.sql` | 知识库建表 SQL |

运行时数据与报告不在这里：

- 科目源库：`data/content/<subject>/`
- 解析中间产物：`data/content/<subject>/extraction/`
- 报告：`data/content/<subject>/reports/`
- Release：`data/releases/`
