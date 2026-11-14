# 题目解析关联报告

- 生成时间：2026-10-27T13:37:10+00:00
- 试卷：`psychology-barrons-2027-ch6-review`
- 模型：`deepseek-flash[1m]`
- Prompt：`question-kp-link-v1`
- 题目：6；失败：0

> 核心知识点按“正确选项倒推”生成；干扰项只进入 confusable。
> 含图题/知识库未收录的题会在备注中标记，不强行绑定不相干知识点。

| 题号 | 状态 | 核心知识点 | 辅助 | 易混淆 | 关键字 | 备注 |
|---:|---|---|---|---|---|---|
| 1 | linked | Amplitude、Pitch | Loudness | Cochlea（B） | amplitude、frequency（未收录）、sound waves（未收录）、pitch、cochlea、auditory cortex（未收录） | Core distinction is amplitude as wave height versus frequency as rate of wave passage; pitch and loudness are related but not the tested distinction. |
| 2 | linked | Vestibular sense | Semicircular canals | — | vestibular sense、Writing our name（未收录） | Vestibular sense (balance/orientation) is the core; semicircular canals support it. Kinesthesis and serial position effect are the nearest same-domain distractors. |
| 3 | linked | Smell (or Olfaction) | — | — | chemical senses（未收录）、energy senses（未收录）、chemical stimulus sense（未收录） | The item tests the defining feature of chemical senses (contact with receptors) versus energy senses. Wrong options B-D are comparative claims not tied to a specific candidate concept, so no confusables are listed. |
| 4 | linked | Nerve deafness | Transduction | — | earplugs（未收录）、hearing（未收录）、Hair cells（未收录）、Ossicles（未收录）、Pinna（未收录）、Tympanic membrane（未收录） | The item tests knowledge that loud noise damages cochlear hair cells, linking to nerve deafness. Transduction is a supporting concept because hair cells are the receptors where transduction occurs. |
| 5 | linked | Positive correlation | Scatterplot | — | scatter plot（未收录）、better hearing tended to have better vision（未收录）、make up for it with better hearing（未收录）、lead to similar deficits（未收录） | The item tests recognizing a positive correlation from a scatterplot; option D reflects a positive correlation, while B suggests a negative correlation and C implies causation. |
| 6 | linked | Somatosensory cortex | — | — | somatosensory receptors（未收录）、touch（未收录）、neurons | The item tests the density/distribution of touch receptors across skin areas. No candidate knowledge point directly names touch receptors or receptor density; C04 (somatosensory cortex) is the closest related concept but concerns cortical processing rather than skin receptor distribution, so confidence is moderate. Option A's 'neurons' maps loosely to C13 but is not a same-domain confusable for receptor density. |

## 覆盖

- linked：6
- needs_review：0
- no_match：0

## 校验记录

- Q1（psychology-barrons-2027-ch6-review-001）：keyword 'frequency': not a known alias of 'Pitch'; stored without a KP
- Q2（psychology-barrons-2027-ch6-review-002）：confusable 'Kinesthetic sense (kinesthesis)' is not named in option 'B' and is not in the core subheading; dropped
- Q2（psychology-barrons-2027-ch6-review-002）：confusable 'serial position effect' is not named in option 'C' and is not in the core subheading; dropped
- Q2（psychology-barrons-2027-ch6-review-002）：keyword 'Walking a straight line with our eyes closed': whole/long option text; dropped
- Q2（psychology-barrons-2027-ch6-review-002）：keyword 'Integrating what we see and hear': whole/long option text; dropped
- Q2（psychology-barrons-2027-ch6-review-002）：keyword 'Writing our name': not a known alias of 'Kinesthetic sense (kinesthesis)'; stored without a KP
- Q2（psychology-barrons-2027-ch6-review-002）：keyword 'Repeating a list of digits': whole/long option text; dropped
- Q3（psychology-barrons-2027-ch6-review-003）：supporting 'Vision' is not in the correct option or the core subheading; dropped
- Q3（psychology-barrons-2027-ch6-review-003）：keyword 'chemical senses': not a known alias of 'Smell (or Olfaction)'; stored without a KP
- Q3（psychology-barrons-2027-ch6-review-003）：keyword 'energy senses': not a known alias of 'Vision'; stored without a KP
- Q3（psychology-barrons-2027-ch6-review-003）：keyword 'chemical stimulus sense': not a known alias of 'Smell (or Olfaction)'; stored without a KP
- Q4（psychology-barrons-2027-ch6-review-004）：confusable 'Conduction deafness' is not named in option 'B' and is not in the core subheading; dropped
- Q4（psychology-barrons-2027-ch6-review-004）：keyword 'Hair cells': not a known alias of 'Nerve deafness'; stored without a KP
- Q4（psychology-barrons-2027-ch6-review-004）：keyword 'Ossicles': not a known alias of 'Conduction deafness'; stored without a KP
- Q5（psychology-barrons-2027-ch6-review-005）：confusable 'Negative correlation' is not named in option 'B' and is not in the core subheading; dropped
- Q5（psychology-barrons-2027-ch6-review-005）：confusable 'Correlation' is not named in option 'C' and is not in the core subheading; dropped
- Q5（psychology-barrons-2027-ch6-review-005）：keyword 'scatter plot': not a known alias of 'Scatterplot'; stored without a KP
- Q5（psychology-barrons-2027-ch6-review-005）：keyword 'better hearing tended to have better vision': not a known alias of 'Positive correlation'; stored without a KP
- Q5（psychology-barrons-2027-ch6-review-005）：keyword 'make up for it with better hearing': not a known alias of 'Negative correlation'; stored without a KP
- Q5（psychology-barrons-2027-ch6-review-005）：keyword 'lead to similar deficits': not a known alias of 'Correlation'; stored without a KP
- Q6（psychology-barrons-2027-ch6-review-006）：keyword 'somatosensory receptors': not a known alias of 'Somatosensory cortex'; stored without a KP

## 复跑命令

```bash
python3 _tools/link_question_kps.py --paper psychology-barrons-2027-ch6-review --force
```
