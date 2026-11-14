# 题目解析关联报告

- 生成时间：2026-10-27T13:37:05+00:00
- 试卷：`psychology-barrons-2027-ch5-review`
- 模型：`deepseek-flash[1m]`
- Prompt：`question-kp-link-v1`
- 题目：7；失败：0

> 核心知识点按“正确选项倒推”生成；干扰项只进入 confusable。
> 含图题/知识库未收录的题会在备注中标记，不强行绑定不相干知识点。

| 题号 | 状态 | 核心知识点 | 辅助 | 易混淆 | 关键字 | 备注 |
|---:|---|---|---|---|---|---|
| 1 | linked | Narcolepsy | — | Sleep apnea（A）、Insomnia（B）、Somnambulism (sleepwalking)（D） | falls asleep at unusual times（未收录）、Narcolepsy、Sleep apnea、Insomnia、Somnambulism | The item tests recognition of narcolepsy from the hallmark of falling asleep at inappropriate times; the other options are other sleep disorders. |
| 2 | linked | REM sleep | — | — | REM sleep、REM deprivation（未收录）、EEG、cognitive purpose（未收录） | The item asks what function REM sleep serves; the correct answer (cognitive purpose) is supported by the memory/quiz manipulation. No candidate knowledge point directly encodes 'cognitive function of sleep,' so the core is anchored to REM sleep (C02) with the correct-option term left unlinked. |
| 3 | linked | Informed consent、No coercion | — | — | ethical concern（未收录）、consent（未收录）、his Introduction to Psychology class（未收录）、deception（未收录）、privacy（未收录）、long-lasting harm（未收录） | The core ethical issue is informed consent, heightened by the professor-student relationship (potential coercion). Deception is a related APA ethics principle but is not the primary concern here. |
| 4 | linked | Population | Representative sample | — | generalize（未收录）、sample（未收录） | The item tests understanding of population/generalizability: broadening age and school variety increases representativeness beyond the original college sample. |
| 5 | linked | Delta sleep | Sleep cycle | — | sleep（未收录）、stage（未收录）、REM（未收录）、non-REM 3（未收录） | Item tests identifying the sleep stage with least duration; non-REM 3 corresponds to delta/deep sleep. |
| 6 | linked | Sleep spindles | Sleep cycle | — | sleep spindles、stage of sleep（未收录）、REM（未收录）、non-REM 1（未收录）、non-REM 2（未收录）、non-REM 3（未收录） | Core is sleep spindles and their prevalence in NREM 2. NREM 1 is a same-domain distractor but has no dedicated candidate key; left as null. |
| 7 | linked | Electroencephalogram (EEG) | Ways of Studying the Brain | Positron emission tomography (PET) scan（A） | stage of sleep（未收录）、EEGs（未收录）、PET scans（未收录）、EMGs（未收录）、MRIs（未收录） | The item tests knowledge of which brain-recording technique is used to monitor sleep stages; EEG is the core. EMG is a real term but not in the candidate list, so kp is null. |

## 覆盖

- linked：7
- needs_review：0
- no_match：0

## 校验记录

- Q1（psychology-barrons-2027-ch5-review-001）：keyword 'falls asleep at unusual times': not a known alias of 'Narcolepsy'; stored without a KP
- Q2（psychology-barrons-2027-ch5-review-002）：supporting 'Electroencephalogram (EEG)' is not in the correct option or the core subheading; dropped
- Q2（psychology-barrons-2027-ch5-review-002）：keyword 'REM deprivation': not a known alias of 'REM sleep'; stored without a KP
- Q3（psychology-barrons-2027-ch5-review-003）：confusable 'Debriefing' is not named in option 'A' and is not in the core subheading; dropped
- Q3（psychology-barrons-2027-ch5-review-003）：keyword 'ethical concern': not a known alias of 'Informed consent'; stored without a KP
- Q3（psychology-barrons-2027-ch5-review-003）：keyword 'consent': not a known alias of 'Informed consent'; stored without a KP
- Q3（psychology-barrons-2027-ch5-review-003）：keyword 'his Introduction to Psychology class': not a known alias of 'No coercion'; stored without a KP
- Q3（psychology-barrons-2027-ch5-review-003）：keyword 'deception': not a known alias of 'Debriefing'; stored without a KP
- Q4（psychology-barrons-2027-ch5-review-004）：confusable 'Replication' is not named in option 'A' and is not in the core subheading; dropped
- Q4（psychology-barrons-2027-ch5-review-004）：confusable 'Longitudinal research' is not named in option 'B' and is not in the core subheading; dropped
- Q4（psychology-barrons-2027-ch5-review-004）：keyword 'generalize': not a known alias of 'Population'; stored without a KP
- Q4（psychology-barrons-2027-ch5-review-004）：keyword 'sample': not a known alias of 'Representative sample'; stored without a KP
- Q4（psychology-barrons-2027-ch5-review-004）：keyword 'students of different ages from a variety of schools': whole/long option text; dropped
- Q4（psychology-barrons-2027-ch5-review-004）：keyword 'test these students again later in the semester': whole/long option text; dropped
- Q4（psychology-barrons-2027-ch5-review-004）：keyword 'test students from a class he will teach the following semester': whole/long option text; dropped
- Q5（psychology-barrons-2027-ch5-review-005）：confusable 'REM sleep' is not named in option 'A' and is not in the core subheading; dropped
- Q5（psychology-barrons-2027-ch5-review-005）：keyword 'sleep': not a known alias of 'Sleep cycle'; stored without a KP
- Q5（psychology-barrons-2027-ch5-review-005）：keyword 'stage': not a known alias of 'Delta sleep'; stored without a KP
- Q5（psychology-barrons-2027-ch5-review-005）：keyword 'REM': not a known alias of 'REM sleep'; stored without a KP
- Q5（psychology-barrons-2027-ch5-review-005）：keyword 'non-REM 3': not a known alias of 'Delta sleep'; stored without a KP
- Q6（psychology-barrons-2027-ch5-review-006）：confusable 'REM sleep' is not named in option 'A' and is not in the core subheading; dropped
- Q6（psychology-barrons-2027-ch5-review-006）：confusable 'Delta sleep' is not named in option 'D' and is not in the core subheading; dropped
- Q6（psychology-barrons-2027-ch5-review-006）：keyword 'stage of sleep': not a known alias of 'Sleep cycle'; stored without a KP
- Q6（psychology-barrons-2027-ch5-review-006）：keyword 'REM': not a known alias of 'REM sleep'; stored without a KP
- Q6（psychology-barrons-2027-ch5-review-006）：keyword 'non-REM 2': not a known alias of 'Sleep spindles'; stored without a KP
- Q6（psychology-barrons-2027-ch5-review-006）：keyword 'non-REM 3': not a known alias of 'Delta sleep'; stored without a KP
- Q7（psychology-barrons-2027-ch5-review-007）：confusable 'Magnetic resonance imaging (MRI)' is not named in option 'D' and is not in the core subheading; dropped
- Q7（psychology-barrons-2027-ch5-review-007）：keyword 'EEGs': not a known alias of 'Electroencephalogram (EEG)'; stored without a KP
- Q7（psychology-barrons-2027-ch5-review-007）：keyword 'PET scans': not a known alias of 'Positron emission tomography (PET) scan'; stored without a KP
- Q7（psychology-barrons-2027-ch5-review-007）：keyword 'MRIs': not a known alias of 'Magnetic resonance imaging (MRI)'; stored without a KP

## 复跑命令

```bash
python3 _tools/link_question_kps.py --paper psychology-barrons-2027-ch5-review --force
```
