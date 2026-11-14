# services/data-pipeline

> 规划位置；当前数据管道脚本仍在项目根目录 `_tools/`，prompts 仍在 `prompts/`。
> `AP_exam/` 已拆分并移除：报告/JSON 在 `data/content/<subject>/{extraction,reports}/`，文档在 `docs/content/`。
> **不要现在迁移脚本。** 先保持现有路径可运行，再逐步迁入 `services/data-pipeline/tools/`。

## 当前实际布局

- 科目源库：`data/content/<subject>/<subject>_exam.db` / `<subject>_knowledge.db`
- 解析中间产物：`data/content/<subject>/extraction/`
- 报告：`data/content/<subject>/reports/`
- 内容文档：`docs/content/`
- 数据生产脚本：`_tools/`
- 提示语：`prompts/`

API/Web/小程序不读这些中间产物，只读 content release。

单元练习合并的成员映射不在代码里，而在 `config/practice_groups/<subject_id>.json`；规范见 `prompts/06_unit_practice_merge.md`。

## 推荐节奏

```text
Phase A：内容 v1（当前位置，不迁移）
  继续补试卷/教材/单元题
  单元练习成员映射写入 config/practice_groups/<subject_id>.json
  冻结 schema
  记录已知缺口
  产出 content release v1

Phase B：API MVP（不迁移）
  API 只读 release / 当前内容库
  做 papers / questions / concepts 接口

Phase C：Web + 小程序 MVP（不迁移）
  接 API，验证做题/知识点/进度

Phase D：仓库迁移（最后做）
  _tools/        → services/data-pipeline/tools/
  prompts/       → 保留顶层
  内容产物       → 已在 data/content/<subject>/{extraction,reports}/
  内容文档       → 已在 docs/content/
  更新所有路径常量 + 回归测试
```

## “第一版数据”不等于 100% 录完

v1 可以带已知缺口：

- 已录入的试卷/教材必须通过 QA
- 未录入的 source 用 manifest 标记 `planned`
- v2/v3 继续增量发布
- 不要把“所有内容都录完”作为 API/Web 开工的前置条件

## 迁移前检查

- [ ] content release v1 已生成并验证
- [ ] API 已能只读 release
- [ ] Web/小程序 MVP 已跑通
- [ ] 没有正在运行的数据导入任务
- [ ] 所有路径常量集中到配置（不再散落硬编码）
- [ ] 迁移脚本支持 dry-run + 回滚
