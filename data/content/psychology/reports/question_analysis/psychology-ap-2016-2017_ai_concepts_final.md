# 2016 / 2017 AP Psychology MCQ — AI 解析与概念关联最终报告

- 生成时间：2026-11-02
- 范围：`psychology-ap-2016`、`psychology-ap-2017`
- 模型：`deepseek-flash[1m]`
- Prompt：`05_ai_explanation.md`（ai-explanation-v2）、`03_question_concept_linking.md`（question-concept-link-v2）
- 当前 active Release：`content-20261102-04`

## 1. AI 解析

| 试卷 | MCQ | AI 解析 | 缺 AI 解析 | 含图题 | 选项图片题 |
|---|---:|---:|---:|---:|---:|
| `psychology-ap-2016` | 100 | 100 | 0 | 5 | 0 |
| `psychology-ap-2017` | 100 | 98 | 2 | 5 | 2 |

- 只写入正确选项的 `options.ai_explanation`；错误选项全部为 `NULL`。
- `options.explanation` 未修改；两套 2016/2017 题原本没有原书解析。
- 解析长度 191–548 字符，平均约 393 字符；无重复、无“as an AI / answer key”等元话语。
- 选项图片题按提示词默认跳过：`psychology-ap-2017-mcq-043`、`psychology-ap-2017-mcq-092`。
- 10 道含图题的解析已逐题复核；其中 `psychology-ap-2017-mcq-067` 初始解析误写均值 60，已按图改为均值 70，并重写为对应的正态分布计算。

## 2. 概念关联

| 试卷 | MCQ | 有 core 的题 | core 行数 | supporting | confusable |
|---|---:|---:|---:|---:|---:|
| `psychology-ap-2016` | 100 | 99 | 104 | 55 | 141 |
| `psychology-ap-2017` | 100 | 97 | 105 | 48 | 153 |
| **合计** | **200** | **196** | **209** | **103** | **294** |

- 13 道题有 2 个 core，其余 183 道有 1 个 core；没有题目超过 2 个 core。
- 所有 core 均有 evidence；所有 confusable 都指向错误选项，没有指向正确答案。
- `question_concept_links` 与 legacy `question_kp_links` 各 606 行，保持镜像。

### 没有 core 的题目

- `psychology-ap-2017-mcq-043`、`psychology-ap-2017-mcq-092`：选项是图片，按 prompt 03 默认跳过。
- `psychology-ap-2016-mcq-047`：正确答案是 Self-reference effect，但概念库没有该概念；`Self` 过于宽泛，标记 `needs_review`，未硬套。
- `psychology-ap-2017-mcq-080`：正确答案是 Compliance，但概念库没有 Compliance；`Conformity` 不等价，标记 `needs_review`，未硬套。

### 仍需人工复核

- `psychology-ap-2016-mcq-040`：core 为 Transference；Countertransference 不在候选概念中，confusable 缺失，状态 `needs_review`。
- `psychology-ap-2016-mcq-047`、`psychology-ap-2017-mcq-080`：需要补概念后重链。
- `psychology-ap-2017-mcq-043`、`psychology-ap-2017-mcq-092`：需要读图补 AI 解析和概念关联。

## 3. 人工修订

- `psychology-ap-2016-mcq-024`：core 从 REM sleep behavior disorder 改为 REM sleep，增加 Dreams supporting。
- `psychology-ap-2016-mcq-047`：移除过宽的 Self core，标记 needs_review。
- `psychology-ap-2016-mcq-079`：core 从 Stress/Endocrine system 改为 Psychoneuroimmunology，Stress/Endocrine 保留为 supporting。
- `psychology-ap-2017-mcq-060`：core 从 Somatic therapies 改为 Biological psychology，增加 Antidepressant drugs supporting。
- `psychology-ap-2017-mcq-080`：移除错误的 Conformity core，标记 needs_review。
- `psychology-ap-2017-mcq-088`：core 从 Learning 改为 Fluid intelligence。
- `psychology-ap-2017-mcq-067`：修正含图题 AI 解析中的均值。

## 4. 产物

- AI 解析最终 JSON：`data/content/psychology/extraction/ai_explanations_psychology-ap-2016-2017-final.json`
- 概念关联最终 JSON：`data/content/psychology/extraction/question_concept_links_psychology-ap-2016-2017-final.json`
- AI 解析工具报告：`data/content/psychology/reports/ai_explanation_report.md`
- 概念关联工具报告：`data/content/psychology/reports/question_analysis/psychology-ap-2016_concepts.md`、`psychology-ap-2017_concepts.md`

## 5. 备份

- AI 解析写库前：`data/content/psychology/psychology_exam.db.bak-20261102-135557-ai-explanation`
- 概念关联写库前：`data/content/psychology/psychology_knowledge.db.bak-20261102-140058-question-concept-link`
- 人工修订前：`data/content/psychology/psychology_knowledge.db.bak-20261102-141500-before-2016-2017-curation`
- Release 激活前应用库：`data/app/app.db.bak-20261102-141800-before-release-content-20261102-04-sqlite`

## 6. 校验

- `psychology_exam.db`：`integrity_check=ok`，`foreign_key_check=[]`
- `psychology_knowledge.db`：`integrity_check=ok`，`foreign_key_check=[]`
- Release `content-20261102-04`：校验通过，已激活。
