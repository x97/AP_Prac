# Myers AP Psychology 4e 知识点抽取与对照

## 1. 抽取结果

| 项目 | 数值 |
|---|---:|
| 书 | Myers' Psychology for the AP Course, 4th ed. (BFW, 2024) |
| 出版社 Glossary 词条 | 666 |
| 去重 | 2（effect 重复 placebo effect；character strengths and virtues 合并到 24 strengths 词条） |
| 拆分的多义词 | 3（accommodation / discrimination / psychoanalysis） |
| 入库 glossary KP | **667** |
| 正文补充 KP | 11（scientific attitude 元素、Animism、Overlearning 等） |
| Myers KP 合计 | **678** |
| Module section | **82** |
| Unit section | 7（Unit 0–5 + Enrichment Modules） |
| 英文短释 | 678 条（667 glossary + 11 body），全部 3–10 词 |
| Module 归属 | 652 条按定义句正文命中；17 条按词频 |
| 别名 | 764 条（753 glossary + 11 body） |

Myers 的 KP 来源是出版社英文 Glossary/Glosario，定义逐字取自 glossary；
`definition_type='glossary'`。Module 归属优先用定义句在正文中的逐字命中，
找不到时用该词在本 Unit 内的词频最高 Module。

`EM.1 Influences on Drug Use` 和 `EM.3 Animal Thinking and Language` 没有英文
glossary 词条，因此对应 Module 为 0 KP；它们不是 AP Unit 0–5 的必考模块。

产物：

- `myers_glossary.json` / `myers_glossary.csv`：667 条 KP + 定义 + Unit/Module + 短释
- `myers_modules.json`：82 个 Module 的标题与 PDF 页范围
- `myers_extraction_report.md`：抽取统计与模块清单
- `myers_import_report.md`：入库统计
- `myers_vs_barrons.md`：与 Barron's 860 条 KP 的逐条对照

## 2. 与 Barron's 2027 的总量对照

| 指标 | Myers 4e glossary | Barron's 2027 |
|---|---:|---:|
| KP | 667 | 860 |
| 章节/模块 | 82 modules | 18 chapters（102 个二级块） |
| Unit 0 | 6 modules | 3 chapters（含 History of Psychology） |
| Unit 1 | 14 modules | 3 chapters |
| Unit 2 | 13 modules | 4 chapters |
| Unit 3 | 15 modules | 2 chapters |
| Unit 4 | 18 modules | 3 chapters |
| Unit 5 | 13 modules | 3 chapters |
| Enrichment | 3 modules | 0 |

逐条匹配（名称/别名 + 受控同义词；不做宽松模糊匹配）：

- 名字/别名精确匹配：**355**
- 受控同义匹配：**38**（24 条人工同义 + 14 条核心词元）
- 合计匹配：**393 / 667** Myers KP；**393 / 860** Barron KP
- Myers 有、Barron 没有对应 KP：**274**
  - 其中 **120** 条在 Barron 正文出现过（Barron 讲到了但没建 KP）
  - **154** 条按严格词形未在 Barron 正文出现（可能是新增术语或同义改写）
- Barron 有、Myers 没有对应 glossary KP：**468**
  - 其中 **273** 条在 Myers 正文出现过（Myers 讲到了但没进 glossary）
  - **195** 条按严格词形未在 Myers 正文出现（Barron 更细的考点或同义改写）

### 2.1 Myers 明显新增/术语化的方向

- 研究基础：critical thinking、falsifiable、peer reviewers、regression toward the mean、effect size、meta-analysis
- 发展：concrete/formal operational stage、basic trust、gender role、androgyny、asexual
- 记忆/思维：automatic/effortful/deep processing、semantic memory、source amnesia
- 临床/DSM-5-TR：DSM-5-TR、bipolar I/II、hoarding disorder、feeding and eating disorders、neurodevelopmental disorders、trauma-and-stressor-related disorders
- 积极心理学/健康：character strengths、flow、burnout、posttraumatic growth、aerobic exercise
- 生物：brainstem、cognitive neuroscience、NREM sleep、cochlear implant、Cattell-Horn-Carroll (CHC) theory

### 2.2 Barron 明显更细的方向

- **History of Psychology / Perspectives**：Barron 有独立 Chapter 1；Myers 没有独立历史章节，perspectives 分散在各 Unit。
- **Research Methods / Statistics**：Barron 的 KP 更细：Variables、Experimental hypothesis、Reliability、Sampling/Random/Stratified sampling、Double-blind/Single-blind study、Demand characteristics、Placebo method、Ex post facto、Likert scales、Directionality problem、Spurious correlation、z-scores、Percentiles、Line of best fit、Sampling error、APA ethics 细节。
- **Neuroanatomy / Consciousness**：terminal buttons、excitatory/inhibitory neurotransmitters、afferent nerves、phantom limb、nonconscious/preconscious/subconscious、SSRI、psychological/physical dependence、reverse tolerance、opiates、sleep onset、theta waves、night terrors、lucid dreams、activation-synthesis/information-processing dream theories、dichromatism、pitch theories、pain receptors、papillae、five tastes。
- **Psychometrics**：psychometricians、equivalent-form reliability、face/concurrent validity、speed/power/group/individual tests、multiple-intelligences  subtypes、EQ、deviation IQ、bias in testing、Head Start。
- **Clinical/treatment**：Barron 对障碍亚型、治疗流派和药物细节的 KP 更密。

## 3. 旧缺口概念在 Myers 中的情况

| 概念 | Myers glossary | Myers 正文 | Barron | 结论 |
|---|---|---|---|---|
| Variance | — | 0.6，p.201 | 正文提到，无 KP | 两本都没有独立 KP；Myers 在统计模块提到 |
| Regression to the mean | **有**（regression toward the mean） | 0.4，p.131 | 无 | Myers 补上 |
| Operational definition | **有** | 0.3，p.112 | 有 KP | 两本都有 |
| Animism | — | 3.4，p.1208 | 无 | Myers 正文有；已补 body KP |
| Erikson stages | —（无逐阶段词条） | 3.6b，Table 3.6-2，p.1317 | 只有 Psychosocial stage theory 伞概念 | 已补 Erikson psychosocial stage theory 伞概念；未逐阶段建 KP |
| Overlearning | — | 2.3，p.794 | 无 | Myers 正文有；已补 body KP |
| Vicarious conditioning | — | 3.9，p.1474 | 无 | Myers 正文有；已补 body KP |
| Source amnesia | **有** | 2.7，p.879 | 无 | Myers 补上 |
| Incentive theory | 有 `incentive` 词条 | 4.7a，p.1887（incentive theory） | 有 `Incentives` | 两本都有，Myers 用 incentive 词条 |
| Belongingness | — | 4.5b / 4.7a | 无 | Myers 正文有；已补 body KP |
| Tardive dyskinesia | — | 5.5d，p.2463 | 有 KP | Myers 正文有；已补 body KP；Barron 有 KP |
| Benzodiazepine | — | 未出现 | 有 | Myers 未覆盖（用 antianxiety drugs 泛称） |
| Sleep apnea | **有** | 1.5c，p.501 | 有 KP | 两本都有 |
| Halo effect | — | 4.2，p.1572 | 无 | Myers 正文有；已补 body KP |
| Self-perception | — | 仅 5.4d 厌食症定义中的措辞 | 无 | Myers 未把它作为社会心理学概念覆盖 |

> “正文有”只说明书中讨论了该概念，不等于它已成为可链接的 KP。要让这些概念进入题目解析，需要补 glossary/KP 或手工补建。

## 4. 单元/章节设计差异

1. **粒度**：Myers 82 个 Module，Barron 18 个 Chapter。Myers 把每个 AP Unit 拆成 13–18 个短 Module；Barron 用 2–4 个大 Chapter。
2. **Unit 0**：Myers 6 个 Module（科学态度、为何需要科学、方法、相关/实验、伦理、统计）；Barron 3 个 Chapter，其中 Chapter 1 是 History of Psychology。Myers 没有独立历史章节。
3. **Unit 1**：Myers 14 个 Module，把神经元、神经递质/药物、脑结构、睡眠、感觉分别拆开；Barron 3 个 Chapter。
4. **Unit 2**：Myers 13 个 Module，知觉、思维、记忆、智力分别细分；Barron 4 个 Chapter。
5. **Unit 3**：Myers 15 个 Module，单独设 Gender and Sexual Orientation（3 个 Module）和 Communication and Language（1 个 Module）；Barron 只有 Developmental Psychology + Learning 两章。
6. **Unit 4**：Myers 18 个 Module，把社会情境拆成 conformity、group、aggression、attraction、altruism，并细分人格理论、动机、情绪；Barron 3 个 Chapter。
7. **Unit 5**：Myers 13 个 Module，单独设 Positive Psychology（2 个 Module），障碍与治疗按 DSM 类别拆细；Barron 3 个 Chapter。
8. **Enrichment**：Myers 有 EM.1 Drug Use、EM.2 Psychology at Work、EM.3 Animal Thinking and Language；Barron 无对应章节。
9. **练习设计**：Myers 每个 Module 有 Learning Targets、AP Science Practice、Check Your Understanding、Module Review MCQs；Barron 以章末 Review Questions 为主，并配 3 套完整 Practice Tests。

## 5. 复跑命令

```bash
python3 _tools/extract_myers_kps.py
python3 _tools/generate_myers_plain.py
python3 _tools/import_myers_kps.py
python3 _tools/compare_myers_barrons.py
```

## 6. 题目状态

2026-10-28 已按要求**删除 Myers 的全部题目**：

- 删除 6 份 Unit 练习卷 + 1 份 Appendix A 模拟卷；
- 删除 814 道 MCQ、2 道 FRQ 及全部选项；
- 删除 Myers 题目的 `question_analysis` / `question_kp_links` / `question_concept_links` / `question_keywords`；
- 删除生成页 `quiz_myers_u*.html`、`quiz_myers_mock.html` 与题目报告/复核队列。

**Myers 的知识点仍保留**：`psychology-myers-2024` 的 678 条 KP、82 个 Module、别名和概念成员均未删除。

## 7. 概念层与权重

- 规范概念：1,105 条（402 core + 703 supporting）；全部 1,538 条 KP 已映射到概念。
- `question_concept_links`：7,371 条 / 2,837 题（仅保留 Barron 旧题目的概念关联）。
- `concept_relations`：209 条（上下位 132 / 整体-部分 55 / 相关 14 / 同名异义 8）。
- KP 权重：827 core / 711 supporting；0–100，已按移除 Myers 题目后的题目计数重算。
- 复核报告：`data/content/psychology/reports/knowledge/concept_audit_report.md`（393 core 基线、合并/改名/关系建议）与 `concept_audit_postcheck.md`（复核后状态）。
- 报告：`data/content/psychology/reports/knowledge/concept_weight_report.md`
- 概念清单：`data/content/psychology/reports/knowledge/concept_weights_final.csv`
- KP 权重清单：`data/content/psychology/reports/knowledge/kp_weights_final.csv`
