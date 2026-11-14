# 单元练习合并摘要

> 日期：2026-10-28T12:24:00+08:00
> 配置：`config/practice_groups/psychology.json`
> 策略：官方题库 primary + 教材章节 supplement；虚拟 bundle；fingerprint 去重

| Group | Unit | 标题 | 成员卷 | 题目数 | 唯一题 | 重复组 | 状态 |
|---|---:|---|---:|---:|---:|---:|---|
| `psychology-unit1-practice` | 1 | 心理学 Unit 1 单元练习 | 4 | 345 | 345 | 0 | `active` |
| `psychology-unit2-practice` | 2 | 心理学 Unit 2 单元练习 | 5 | 387 | 387 | 0 | `active` |
| `psychology-unit3-practice` | 3 | 心理学 Unit 3 单元练习 | 3 | 384 | 384 | 0 | `active` |
| `psychology-unit4-practice` | 4 | 心理学 Unit 4 单元练习 | 4 | 409 | 409 | 0 | `active` |
| `psychology-unit5-practice` | 5 | 心理学 Unit 5 单元练习 | 4 | 352 | 352 | 0 | `active` |
| **合计** | — | — | **20** | **1877** | **1877** | **0** | — |

> `重复组` 是 group 内重复；跨 Unit 重复见下方“跨 Unit 重复题”。

## Bundle

| Group | Bundle paper | 题目 |
|---|---|---:|
| `psychology-unit1-practice` | `psychology-unit1-practice-bundle` | 345 |
| `psychology-unit2-practice` | `psychology-unit2-practice-bundle` | 387 |
| `psychology-unit3-practice` | `psychology-unit3-practice-bundle` | 384 |
| `psychology-unit4-practice` | `psychology-unit4-practice-bundle` | 409 |
| `psychology-unit5-practice` | `psychology-unit5-practice-bundle` | 352 |

## 成员结构

- Unit 1：`psychology-cb-2026-u1` (primary) → `psychology-barrons-2027-ch4-review` (supplement) → `psychology-barrons-2027-ch5-review` (supplement) → `psychology-barrons-2027-ch6-review` (supplement)
- Unit 2：`psychology-cb-2026-u2` (primary) → `psychology-barrons-2027-ch7-review` (supplement) → `psychology-barrons-2027-ch8-review` (supplement) → `psychology-barrons-2027-ch9-review` (supplement) → `psychology-barrons-2027-ch10-review` (supplement)
- Unit 3：`psychology-cb-2026-u3` (primary) → `psychology-barrons-2027-ch11-review` (supplement) → `psychology-barrons-2027-ch12-review` (supplement)
- Unit 4：`psychology-cb-2026-u4` (primary) → `psychology-barrons-2027-ch13-review` (supplement) → `psychology-barrons-2027-ch14-review` (supplement) → `psychology-barrons-2027-ch15-review` (supplement)
- Unit 5：`psychology-cb-2026-u5` (primary) → `psychology-barrons-2027-ch16-review` (supplement) → `psychology-barrons-2027-ch17-review` (supplement) → `psychology-barrons-2027-ch18-review` (supplement)

## 校验

- **WARNING** `psychology-unit1-practice`: cross-unit duplicate fingerprint 8d13de901ec0: psychology-unit4-practice:psychology-cb26-u4-0101
- **WARNING** `psychology-unit2-practice`: cross-unit duplicate fingerprint a12ed6e82682: psychology-unit4-practice:psychology-cb26-u4-0100
- **WARNING** `psychology-unit3-practice`: cross-unit duplicate fingerprint c52676384ea0: psychology-unit4-practice:psychology-cb26-u4-0099
- **WARNING** `psychology-unit3-practice`: cross-unit duplicate fingerprint d18d750051c5: psychology-unit5-practice:psychology-cb26-u5-0087
- **WARNING** `psychology-unit4-practice`: cross-unit duplicate fingerprint 8d13de901ec0: psychology-unit1-practice:psychology-cb26-u1-0311
- **WARNING** `psychology-unit4-practice`: cross-unit duplicate fingerprint a12ed6e82682: psychology-unit2-practice:psychology-cb26-u2-0340
- **WARNING** `psychology-unit4-practice`: cross-unit duplicate fingerprint c52676384ea0: psychology-unit3-practice:psychology-cb26-u3-0248
- **WARNING** `psychology-unit4-practice`: cross-unit duplicate fingerprint 6c24bccb8ae4: psychology-unit5-practice:psychology-cb26-u5-0074
- **WARNING** `psychology-unit5-practice`: cross-unit duplicate fingerprint d18d750051c5: psychology-unit3-practice:psychology-cb26-u3-0249
- **WARNING** `psychology-unit5-practice`: cross-unit duplicate fingerprint 6c24bccb8ae4: psychology-unit4-practice:psychology-cb26-u4-0090

## 跨 Unit 重复题

| fingerprint | 涉及 group | question_id |
|---|---|---|
| `6c24bccb8ae4` | `psychology-unit4-practice`, `psychology-unit5-practice` | `psychology-cb26-u4-0090`, `psychology-cb26-u5-0074` |
| `8d13de901ec0` | `psychology-unit1-practice`, `psychology-unit4-practice` | `psychology-cb26-u1-0311`, `psychology-cb26-u4-0101` |
| `a12ed6e82682` | `psychology-unit2-practice`, `psychology-unit4-practice` | `psychology-cb26-u2-0340`, `psychology-cb26-u4-0100` |
| `c52676384ea0` | `psychology-unit3-practice`, `psychology-unit4-practice` | `psychology-cb26-u3-0248`, `psychology-cb26-u4-0099` |
| `d18d750051c5` | `psychology-unit3-practice`, `psychology-unit5-practice` | `psychology-cb26-u3-0249`, `psychology-cb26-u5-0087` |

## 数据表

- `practice_groups`：5 条
- `practice_group_papers`：20 条
- `paper_question_map`：1877 条（5 个 bundle）
- `questions.question_fingerprint`：1877 条已填充

