# 题目概念关联报告（概念层）

- 生成时间：2026-10-28T11:14:59+08:00
- 试卷：`psychology-barrons-2027-ch11-review`
- 模型：`deepseek-flash[1m]`
- Prompt：`question-concept-link-v2`
- 题目：1；失败：0

> 核心概念按“正确选项倒推”生成；干扰项只进入 confusable。
> 写库目标：`question_concept_links`；`question_kp_links` 仅作 legacy 兼容。

| 题号 | 状态 | 核心概念 | 辅助 | 易混淆 | 关键字 | 备注 |
|---:|---|---|---|---|---|---|
| 8 | linked | Animism（34.7） | — | Egocentric（B） | Animism、Egocentrism、Reversibility（未收录） | The item tests animism: attributing life/lifelike fixability to an inanimate object (the fish). Identification (option C) is not a close developmental near-miss in the candidate set, so it is omitted from confusables. |

## 覆盖

- linked：1
- needs_review：0
- no_match：0

## 校验记录

- Q8（psychology-barrons-2027-ch11-review-008）：confusable 'Conservation' is not named in option 'D' and is not in the core subheading; dropped
- Q8（psychology-barrons-2027-ch11-review-008）：keyword 'Reversibility': not a known alias of 'Conservation'; stored without a KP

## 复跑命令

```bash
python3 _tools/link_question_concepts.py --paper psychology-barrons-2027-ch11-review --force
```
