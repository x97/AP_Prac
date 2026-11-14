# 题目解析关联报告

- 生成时间：2026-10-27T13:53:46+00:00
- 试卷：`psychology-ap-2022`
- 模型：`deepseek-flash[1m]`
- Prompt：`question-kp-link-v1`
- 题目：3；失败：0

> 核心知识点按“正确选项倒推”生成；干扰项只进入 confusable。
> 含图题/知识库未收录的题会在备注中标记，不强行绑定不相干知识点。

| 题号 | 状态 | 核心知识点 | 辅助 | 易混淆 | 关键字 | 备注 |
|---:|---|---|---|---|---|---|
| 7 | linked | Systematic desensitization | specific phobia | Cognitive therapy（D）、Aversive therapy（E）、Drug therapy or psychopharmacology（C） | behavioral principles（未收录）、anxiety disorder（未收录）、systematic desensitization、specific phobia、cognitive therapy、aversion therapy（未收录）、lithium | The item tests recognition that systematic desensitization is a behavioral treatment applied to an anxiety disorder (specific phobia). |
| 56 | linked | availability heuristic | heuristic | functional fixedness（A）、divergent thinking（D） | availability heuristic、cognitive process（未收录）、Functional fixedness、fundamental attribution error、Divergent thinking、hindsight bias | Max's reaction is driven by the easily recalled shark image from the movie, illustrating the availability heuristic. |
| 78 | linked | Operant conditioning | Token economy | Observational learning（B） | schizophrenia、plastic coins（未收录）、desirable behaviors（未收录）、rewards（未收录）、Operant conditioning、Counterconditioning、Observational learning、Cognitive restructuring、Learned helplessness | The scenario describes a token economy, which is an application of operant conditioning; C10/C16 support the answer but the tested principle is operant conditioning. |

## 覆盖

- linked：3
- needs_review：0
- no_match：0

## 校验记录

- Q7（psychology-2022-mcq-007）：keyword 'anxiety disorder': not a known alias of 'Anxiety disorders'; stored without a KP
- Q7（psychology-2022-mcq-007）：keyword 'aversion therapy': not a known alias of 'Aversive therapy'; stored without a KP
- Q56（psychology-2022-mcq-056）：confusable 'Hindsight bias' is in option 'E' but not in the core's narrow domain; dropped
- Q78（psychology-2022-mcq-078）：confusable 'Counterconditioning' is in option 'A' but not in the core's narrow domain; dropped
- Q78（psychology-2022-mcq-078）：confusable 'Cognitive restructuring' is in option 'C' but not in the core's narrow domain; dropped
- Q78（psychology-2022-mcq-078）：confusable 'learned helplessness' is in option 'D' but not in the core's narrow domain; dropped
- Q78（psychology-2022-mcq-078）：keyword 'plastic coins': not a known alias of 'Token economy'; stored without a KP
- Q78（psychology-2022-mcq-078）：keyword 'desirable behaviors': not a known alias of 'Operant conditioning'; stored without a KP
- Q78（psychology-2022-mcq-078）：keyword 'rewards': not a known alias of 'Reinforcer'; stored without a KP

## 复跑命令

```bash
python3 _tools/link_question_kps.py --paper psychology-ap-2022 --force
```
