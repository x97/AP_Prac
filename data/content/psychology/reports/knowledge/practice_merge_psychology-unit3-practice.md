# 单元练习合并报告

- 生成时间：2026-10-28T12:24:00+08:00
- group_id：`psychology-unit3-practice`
- 标题：心理学 Unit 3 单元练习
- subject_id：`psychology`
- unit_id：`3`
- 课程标准范围：`3.1-3.9`
- 配置文件：`config/practice_groups/psychology.json`
- 状态：`active`
- 成员试卷：3
- 题目总数：384
- 唯一 fingerprint：384
- 重复 fingerprint 组：0
- bundle：`psychology-unit3-practice-bundle`
- bundle 题目映射：384

## 成员

| 顺序 | paper_id | role | 题目数 | 进入 bundle 的唯一题 |
|---:|---|---|---:|---:|
| 0 | `psychology-cb-2026-u3` | primary | 354 | 354 |
| 1 | `psychology-barrons-2027-ch11-review` | supplement | 16 | 16 |
| 2 | `psychology-barrons-2027-ch12-review` | supplement | 14 | 14 |

## Unit 校验

| paper_id | 目标 Unit | 主导 Unit | 核心链接占比 | 结果 |
|---|---:|---:|---:|---|
| `psychology-barrons-2027-ch11-review` | 3 | 3 | 87% | OK |
| `psychology-barrons-2027-ch12-review` | 3 | 3 | 100% | OK |

## 校验问题

- **WARNING**: cross-unit duplicate fingerprint c52676384ea0: psychology-unit4-practice:psychology-cb26-u4-0099
- **WARNING**: cross-unit duplicate fingerprint d18d750051c5: psychology-unit5-practice:psychology-cb26-u5-0087

## 重复题

- 无

## 跨 Unit 重复题

| fingerprint | 涉及 group | question_id |
|---|---|---|
| `c52676384ea0` | `psychology-unit3-practice`, `psychology-unit4-practice` | `psychology-cb26-u3-0248`, `psychology-cb26-u4-0099` |
| `d18d750051c5` | `psychology-unit3-practice`, `psychology-unit5-practice` | `psychology-cb26-u3-0249`, `psychology-cb26-u5-0087` |

## 说明

- group 模式只建组，不复制题目；原 paper / 题目 / 解析保持不动。
- bundle 模式创建 `practice_bundle` 虚拟卷，`paper_question_map` 引用原题，不复制 `questions` / `options`。
- 重复 fingerprint 只保留第一条进入 bundle；原题仍保留在各自 paper 中。
- 跨 Unit 重复 fingerprint 只报告，不自动删除；归属需要人工确认。
- 排序固定为 `primary → supplement → old_edition`；同一角色内按配置顺序。
