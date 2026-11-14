# 单元练习合并报告

- 生成时间：2026-10-28T12:24:00+08:00
- group_id：`psychology-unit2-practice`
- 标题：心理学 Unit 2 单元练习
- subject_id：`psychology`
- unit_id：`2`
- 课程标准范围：`2.1-2.5`
- 配置文件：`config/practice_groups/psychology.json`
- 状态：`active`
- 成员试卷：5
- 题目总数：387
- 唯一 fingerprint：387
- 重复 fingerprint 组：0
- bundle：`psychology-unit2-practice-bundle`
- bundle 题目映射：387

## 成员

| 顺序 | paper_id | role | 题目数 | 进入 bundle 的唯一题 |
|---:|---|---|---:|---:|
| 0 | `psychology-cb-2026-u2` | primary | 349 | 349 |
| 1 | `psychology-barrons-2027-ch7-review` | supplement | 9 | 9 |
| 2 | `psychology-barrons-2027-ch8-review` | supplement | 9 | 9 |
| 3 | `psychology-barrons-2027-ch9-review` | supplement | 15 | 15 |
| 4 | `psychology-barrons-2027-ch10-review` | supplement | 5 | 5 |

## Unit 校验

| paper_id | 目标 Unit | 主导 Unit | 核心链接占比 | 结果 |
|---|---:|---:|---:|---|
| `psychology-barrons-2027-ch7-review` | 2 | 2 | 100% | OK |
| `psychology-barrons-2027-ch8-review` | 2 | 2 | 100% | OK |
| `psychology-barrons-2027-ch9-review` | 2 | 2 | 100% | OK |
| `psychology-barrons-2027-ch10-review` | 2 | — | — | insufficient core links (2 < 3); skipped |

## 校验问题

- **WARNING**: cross-unit duplicate fingerprint a12ed6e82682: psychology-unit4-practice:psychology-cb26-u4-0100

## 重复题

- 无

## 跨 Unit 重复题

| fingerprint | 涉及 group | question_id |
|---|---|---|
| `a12ed6e82682` | `psychology-unit2-practice`, `psychology-unit4-practice` | `psychology-cb26-u2-0340`, `psychology-cb26-u4-0100` |

## 说明

- group 模式只建组，不复制题目；原 paper / 题目 / 解析保持不动。
- bundle 模式创建 `practice_bundle` 虚拟卷，`paper_question_map` 引用原题，不复制 `questions` / `options`。
- 重复 fingerprint 只保留第一条进入 bundle；原题仍保留在各自 paper 中。
- 跨 Unit 重复 fingerprint 只报告，不自动删除；归属需要人工确认。
- 排序固定为 `primary → supplement → old_edition`；同一角色内按配置顺序。
