# 题目解析关联报告

- 生成时间：2026-10-27T13:35:39+00:00
- 试卷：`psychology-barrons-2027-ch10-review`
- 模型：`deepseek-flash[1m]`
- Prompt：`question-kp-link-v1`
- 题目：3；失败：0

> 核心知识点按“正确选项倒推”生成；干扰项只进入 confusable。
> 含图题/知识库未收录的题会在备注中标记，不强行绑定不相干知识点。

| 题号 | 状态 | 核心知识点 | 辅助 | 易混淆 | 关键字 | 备注 |
|---:|---|---|---|---|---|---|
| 1 | linked | aptitude tests | achievement tests | standardized test（A）、intelligence（C） | aptitude test（未收录）、standardized test、intelligence test（未收录）、achievement test（未收录）、good pilot（未收录） | The stem describes measuring potential ability for a future role, which is the defining feature of an aptitude test. |
| 2 | linked | content validity | validity | test-retest reliability（A）、split-half reliability（D）、Validity（B） | content validity、test-retest reliability、construct validity（未收录）、split-half reliability | The stem describes representativeness of the full year's material, which maps to content validity. Reliability and construct validity options are same-domain near-misses. |
| 3 | linked | validity | Validity | test-retest reliability（C）、predictive validity（D） | construct validity（未收录）、split half reliability、test-retest reliability、predictive validity、randomly assign（未收录） | The stem describes concern about whether two test versions are equally difficult, which relates to validity; the correct option is construct validity. |

## 覆盖

- linked：3
- needs_review：0
- no_match：0

## 校验记录

- Q1（psychology-barrons-2027-ch10-review-001）：confusable 'achievement tests' is not named in option 'D' and is not in the core subheading; dropped
- Q1（psychology-barrons-2027-ch10-review-001）：keyword 'aptitude test': not a known alias of 'aptitude tests'; stored without a KP
- Q1（psychology-barrons-2027-ch10-review-001）：keyword 'intelligence test': not a known alias of 'intelligence'; stored without a KP
- Q1（psychology-barrons-2027-ch10-review-001）：keyword 'achievement test': not a known alias of 'achievement tests'; stored without a KP
- Q2（psychology-barrons-2027-ch10-review-002）：keyword 'construct validity': not a known alias of 'Validity'; stored without a KP
- Q3（psychology-barrons-2027-ch10-review-003）：confusable 'split-half reliability' is not named in option 'B' and is not in the core subheading; dropped
- Q3（psychology-barrons-2027-ch10-review-003）：keyword 'construct validity': not a known alias of 'validity'; stored without a KP

## 复跑命令

```bash
python3 _tools/link_question_kps.py --paper psychology-barrons-2027-ch10-review --force
```
