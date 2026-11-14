# 概念层 linker 试点报告

> 日期：2026-10-28  
> 脚本：`_tools/link_question_concepts.py`  
> Prompt：`question-concept-link-v2`  
> 范围：`psychology-barrons-2027-ch11-review` 的 Q8（单题试点）

## 试点题

- question_id：`psychology-barrons-2027-ch11-review-008`
- 原状态：`needs_review`
- 原概念链接：无
- 原备注：Animism 未被知识库收录，无法关联

## 试点结果

| 项目 | 结果 |
|---|---|
| 状态 | `linked` |
| 核心概念 | `Animism`（confidence 0.95；weight 30.0 → 34.74） |
| 易混淆概念 | `Egocentric`（选项 B） |
| 关键字 | Animism、Egocentrism、Reversibility（未收录） |
| 候选数 | 80 |
| 模型 | `deepseek-flash[1m]` |
| tokens | 6,005 input / 395 output |
| 写库 | `question_concept_links` 2 条；`question_kp_links` 镜像 2 条；`question_keywords` 3 条 |
| 验证 | `integrity_check=ok`，`foreign_key_check=OK` |

## 说明

- 概念候选池包含 1,105 个规范概念；本题 scope=`Chapter 11`。
- 核心概念 `Animism` 来自 Myers 正文 KP（supporting；试点后 weight 34.74（因新增 1 道 core 题）），此前未进入 Barron KP 候选池。
- `Egocentric` 作为干扰项进入 `confusable`，没有进入 core。
- 旧页面仍能读取 `question_kp_links`；新页面优先读取 `question_concept_links`。
- 本次只跑了 Q8 一题；其余题仍保留原有概念链接，没有全量重链。

## 产物

- JSON：`data/content/psychology/extraction/question_concept_links_psychology-barrons-2027-ch11-review.json`
- 报告：`data/content/psychology/reports/question_analysis/psychology-barrons-2027-ch11-review_concepts.md`
- 页面：`quiz_barron_ch11.html`（已按 Q8 新结果重建）
