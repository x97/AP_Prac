# config/practice_groups

> 单元练习虚拟合并的配置目录。一个学科一个 JSON 文件，脚本只读配置，不把章节映射写死在代码里。

## 统一规则

1. **官方题库优先**：CB / 官方题库是 `primary`，教材章末练习是 `supplement`。
2. **一个 Unit 一个 group**：`group_id` 建议 `<subject>-unit<N>-practice`。
3. **一个 group 一个虚拟 bundle**：`bundle_paper_id` 指向 `paper_type='practice_bundle'` 的虚拟卷。
4. **不复制题目**：bundle 只通过 `paper_question_map` 引用原题。
5. **CB 题在前**：脚本按 `primary → supplement → old_edition` 稳定排序；同一角色内按配置顺序。
6. **没有官方题库**：`status` 自动标为 `needs_review`，不要把 supplement 升为 primary。
7. **章节归属按课程标准校验**：`validation` 用概念层的 `ap_unit` 检查 supplement 是否落在目标 Unit；不一致默认报错。
8. **学生端只看到 Unit 练习**，不显示题库/来源选择。
9. **跨 Unit 重复题只报告，不自动删除**：同一 fingerprint 出现在多个 Unit 时默认 `warn`；归属需要人工判断。

## 文件命名

```text
config/practice_groups/<subject_id>.json
```

## 配置结构

```json
{
  "schema_version": 1,
  "subject_id": "psychology",
  "curriculum": "AP Psychology CED 2024-25",
  "exam_db": "data/content/psychology/psychology_exam.db",
  "knowledge_db": "data/content/psychology/psychology_knowledge.db",
  "report_dir": "data/content/psychology/reports/knowledge",
  "validation": {
    "enabled": true,
    "check_primary": false,
    "min_core_links": 3,
    "min_dominant_share": 0.5,
    "on_mismatch": "error",
    "on_cross_group_duplicate": "warn"
  },
  "groups": [
    {
      "group_id": "psychology-unit1-practice",
      "unit_id": "1",
      "curriculum_topics": "1.1-1.6",
      "title": "心理学 Unit 1 单元练习",
      "bundle_paper_id": "psychology-unit1-practice-bundle",
      "bundle_title": "心理学 Unit 1 单元练习",
      "note": "CED Unit 1: Biological Bases + Sleep + Sensation",
      "members": [
        {"paper_id": "psychology-cb-2026-u1", "role": "primary"},
        {"paper_id": "psychology-barrons-2027-ch4-review", "role": "supplement"}
      ]
    }
  ]
}
```

## 运行

```bash
# 先校验，不写库
python3 _tools/merge_unit_practice.py \
  --config config/practice_groups/psychology.json \
  --dry-run

# 正式重建全部 Unit 的 group / bundle / 报告
python3 _tools/merge_unit_practice.py \
  --config config/practice_groups/psychology.json

# 只重建一个 group
python3 _tools/merge_unit_practice.py \
  --config config/practice_groups/psychology.json \
  --group-id psychology-unit1-practice
```

## 新增学科

1. 复制 `psychology.json` 为 `<subject_id>.json`。
2. 改 `subject_id`、数据库路径、Unit 列表、`paper_id`、`bundle_paper_id`。
3. 准备上线的 Unit 恰好一个 `primary`；没有官方题库的 Unit 标 `needs_review`。教材章节全部 `supplement`。
4. 跑 `--dry-run`，确认校验通过后再正式执行。
5. 如果该学科还没有概念层/`ap_unit`，把 `validation.enabled` 设为 `false`，但仍需人工核对课程标准。

## 校验字段

| 字段 | 默认 | 说明 |
|---|---|---|
| `enabled` | `true` | 是否启用章节归属校验 |
| `check_primary` | `false` | 是否也校验官方题库卷；官方卷可能含跨单元复习题，默认不校验 |
| `min_core_links` | `3` | supplement 至少有多少条 core 概念链接才判断 |
| `min_dominant_share` | `0.5` | 主导 Unit 的最低占比；低于此值只警告，不直接判错 |
| `on_mismatch` | `error` | 主导 Unit 与目标 Unit 不一致时：`error` 阻止写库，`warn` 只警告 |
| `on_cross_group_duplicate` | `warn` | 同一 fingerprint 出现在多个 Unit 时：`warn` / `error` / `ignore`；不自动删除重复题 |

## 当前心理学映射

| Unit | 课程标准 | CB primary | Barron supplement |
|---:|---|---|---|
| 1 | 1.1–1.6 Biological Bases + Sleep + Sensation | `psychology-cb-2026-u1` | Ch4, Ch5, Ch6 |
| 2 | 2.1–2.5 Cognition（含 Perception） | `psychology-cb-2026-u2` | Ch7, Ch8, Ch9, Ch10 |
| 3 | 3.1–3.9 Development and Learning | `psychology-cb-2026-u3` | Ch11, Ch12 |
| 4 | 4.1–4.8 Social + Personality + Motivation/Emotion | `psychology-cb-2026-u4` | Ch13, Ch14, Ch15 |
| 5 | 5.1–5.4 Mental and Physical Health | `psychology-cb-2026-u5` | Ch16, Ch17, Ch18 |

> 注意：Barron 是 18 章，CB 是 5 个 Unit；章节数不同是正常的。归属必须以课程标准为准，不能按章节数量平均分配。
