---
id: question-kp-linking-legacy
title: 题目解析关联（KP 旧版）
version: question-kp-link-v1
status: deprecated
superseded_by: question-concept-linking
kind: linking
updated: 2026-10-28
inputs: [paper_id, kp_db]
outputs: [question_analysis, question_kp_links, question_keywords]
depends_on: [pdf-question-ingestion]
used_by: []
---
# 题目解析关联提示语（关键字 + 知识点）

> **2026-10-28 更新**：本文是 AP 心理学项目专用 runbook，保留为历史操作说明。  
> 新任务请优先使用 `../03_question_concept_linking.md`（概念层 v2）：题目关联的第一目标层是 `question_concept_links` / `concept_clusters`，不是来源 KP。  
> 当前 `link_question_kps.py` 仍只写 `question_kp_links`；新试卷需要 concept-first linker，详见 `../00_data_agent_pipeline.md` 第 12 节。

> 用途：为选择题生成“本题解析”数据：核心知识点、辅助知识点、干扰项易混淆概念、题目中实际出现的关键字。数据写入 `ap_knowledge.db` 的关联表，刷题页读取后展示。
>
> 用法：复制下面「提示词正文」整段，填好「任务参数」后发给我。默认先盘点、先试跑，确认后再全量。

---

## 任务参数（先填这里）

```text
【任务参数】
- 任务模式：先盘点（默认） / 直接关联
- 目标数据库：/Users/aa/Documents/AP_psych/ap_exam.db + ap_knowledge.db
- 范围：单套卷 paper_id / 某章 / 全部试卷
- 章节过滤：自动从 paper_id 推断（如 -ch11- → Chapter 11） / 手动指定
- 选项是图片的题：跳过（默认） / 人工读图后补
- 带图题：正常关联，并在报告中标记 / 跳过
- 是否重建刷题页：是 / 否
- 其他要求：
```

---

## 提示词正文

你是本项目的 AP 心理学题目分析员。目标：为每道选择题建立**关键字**和**知识点**关联，写入 `ap_knowledge.db`，供刷题页展示。

### 0. 先读规则，不要直接扫词

开工前先读取：

1. `/Users/aa/Documents/AP_psych/docs/content/数据库设计文档.md` §3.19
2. `/Users/aa/Documents/AP_psych/docs/content/试卷解析方法.md` 的 `options` 说明
3. `ap_exam.db` / `ap_knowledge.db` 的实际 schema
4. `_tools/link_question_kps.py --help`

**核心区分：**

- **关键字**：题目文本里出现的术语或概念短语。出现 ≠ 被考查。
- **核心知识点**：学生要选对正确答案必须理解的概念。**从正确答案倒推**，不是从题干/干扰项扫词。
- 一道题通常 1 个核心知识点，最多 2 个；辅助知识点最多 1 个。
- 干扰项里的术语只进 `confusable`（带选项字母），**绝不能进 core**。
- 知识库没有的概念，写 `needs_review` / `no_match`，不要硬套相近知识点。

自检规则：

> “如果学生没学过这个术语，他还能做对这道题吗？”  
> 不能 → 才是核心知识点；能但会被骗 → 放进 confusable。

### 1. 先盘点，不要直接写库

先运行：

```bash
python3 _tools/migrate_question_analysis.py   # 首次运行，建表 + 补 kp_aliases.match_mode
python3 _tools/build_kp_aliases.py            # 补别名；可重复运行，INSERT OR IGNORE
python3 _tools/link_question_kps.py --paper <paper_id> --dry-run --limit 3
```

盘点至少输出：

- 试卷/章节的 MCQ 数量；
- 知识库里该章的 KP 数量；
- 别名覆盖和大小写敏感缩写（DID / CNS / IRB 等）；
- 重复概念（same_concept）和同名不同义（homonym）清单；
- 选项图片题、含图题清单；
- 预计候选知识点数量。

### 2. 候选检索规则

脚本会为每道题生成候选集：

1. 该题所属章节的全部 KP（例如 Chapter 11 的 64 个 KP）；
2. 用题干、context、正确选项、原书解析检索到的其他章节 KP（按命中位置和词长打分）；
3. 每个候选分配短 key（`C01`、`C02`…），模型只能选 key，不能编 `kp_id`。

脚本会把候选的名称、`plain_en`、所属 subheading 一起给模型。同名知识点（如两个 `Accommodation`）靠 section 区分。

### 3. 模型选择规则

对每道题，模型必须返回：

```json
{
  "status": "linked",
  "core": [{"kp": "C01", "confidence": 0.95, "evidence": "题干/正确选项原文"}],
  "supporting": [{"kp": "C02", "confidence": 0.8, "evidence": ""}],
  "confusables": [{"kp": "C03", "option_label": "B", "reason": "为什么这个干扰项容易混淆"}],
  "keywords": [{
    "surface": "exact text from the question",
    "kp": "C01",
    "role": "core",
    "location": "stem",
    "option_label": null
  }],
  "notes": ""
}
```

规则：

- `core` 1–2 个；`status=linked` 时必须有 core；
- `core.evidence` 必须是题干/context/正确选项的原文；
- `confusable.option_label` 必须是错误选项；
- `keywords.surface` 必须真的出现在指定位置；
- `keywords.kp` 可以省略（null），表示题目里的真实术语但知识库未收录；
- 不把整个选项句子当 keyword；关键字应是术语/概念短语；
- 找不到合适候选就 `status=no_match` 或 `needs_review`。

### 4. 脚本自动校验

`link_question_kps.py` 会检查：

- core 数量 1–2；core 不能只匹配干扰项；
- core evidence 是否在题干/context/正确选项中；
- confusable 是否出现在对应错误选项，且不能和 core 重复；
- supporting 是否在正确选项或 core 的同一 subheading；
- keyword surface 是否在指定位置，且映射的 KP 必须是该术语的已知别名；
- 选项图片题跳过；含图题正常生成但报告标记；
- 关联表写入后跑 `PRAGMA integrity_check` / `foreign_key_check`。

### 5. 建议的试跑顺序

1. 先选一章 10–20 题（本项目先用 Barron Ch11 的 16 题）；
2. `--dry-run` 看候选是否包含正确 KP；
3. 真实跑一遍，逐题检查报告；
4. 修正别名/stoplist/校验规则；
5. 再扩到同章全部题目，最后扩到全库。

单套卷命令：

```bash
python3 _tools/link_question_kps.py --paper psychology-barrons-2027-ch11-review --force
python3 _tools/link_question_kps.py --paper psychology-barrons-2027-ch11-review --force
```

批量和断点续跑：

```bash
# 每套卷写完才 checkpoint；中断后重跑会跳过已完成/已分析的题
python3 _tools/link_all_question_kps.py --workers 4

# 只从数据库重建该卷的 JSON / 报告，不调用模型（修产物用）
python3 _tools/link_question_kps.py --paper <paper_id> --export-only \
  --report data/content/psychology/reports/question_analysis/<paper_id>.md
```

无章节试卷（真题、练习卷）用 BM25 候选；CB Unit 会自动用 `Unit N` 知识点池；Barron 章节用 `Chapter N` 池。

页面展示约束：

- 只展示 **核心概念 / 辅助概念 / 易混淆概念**；
- 概念卡显示规范概念、`weight` / `weight_tier`，以及 Barron / Myers 来源标签；
- 不显示“相关术语”“干扰项术语”这类额外区块；
- 知识库未收录的核心概念，只在“本题核心概念暂未收录”提示里显示；
- 关键字 chip 和题干/正确选项里的已映射关键字可点击弹出规范概念、权重和来源教材定义。

### 6. 质量门禁

至少检查：

- `linked` / `needs_review` / `no_match` 数量；
- 每题 core 是否 1–2 个；
- 是否有 core 只出现在干扰项；
- confusable 是否都有错误选项字母；
- keyword 是否都能在题目文本中找到；
- 有多少 `kp=null` 的关键字（待补概念）；
- 同名/重复 KP 是否被错误混用；
- 选项图片题、含图题清单；
- `ap_knowledge.db` 的 integrity / foreign_key_check。

当前已发现的待补概念：

- `Animism`（Ch11 Q8，知识库未收录）；
- `Preoperational`、`Formal operations`、`Sensorimotor`、`Concrete operational`（Piaget 阶段名未单独建 KP）；
- `Identity versus role confusion` 等 Erikson 具体阶段（目前只能挂到 `Psychosocial stage theory` 伞概念）。

全库当前 91 题 `needs_review`、4 题 `no_match`，其余缺口集中在统计/测量术语（Variance、Regression to the mean、operational definition）、学习与记忆现象（Overlearning、source amnesia、vicarious conditioning、instinctive drift）、动机理论（incentive theory、belongingness）、临床药物/障碍（tardive dyskinesia、benzodiazepine、sleep apnea）等。完整清单见 `data/content/psychology/reports/question_analysis/question_analysis_all_report.md`。

2026-10-27 已新增 Myers 4e 的 678 条 KP（667 条 glossary + 11 条正文补充，`psychology-myers-2024`），并建立规范概念层（`concept_clusters` / `question_concept_links`）；2026-10-28 复核合并后为 1,105 条概念、209 条 `concept_relations`（上下位/整体-部分/相关/同名异义）。上述缺口中：

- 已有 Myers glossary 词条：`regression toward the mean`、`source amnesia`、`sleep apnea`、`operational definition`；
- 已补成 Myers 正文 KP：Animism、Overlearning、vicarious conditioning、halo effect、belongingness、tardive dyskinesia、scientific attitude / curiosity / skepticism / humility、Erikson psychosocial stage theory；
- Myers 也未覆盖：Benzodiazepine（Myers 用 antianxiety drugs 泛称）；Self-perception 只出现在厌食症定义里，不是社会心理学概念。

重新跑题目关联时，候选池会同时包含 Barron 与 Myers 的知识点；新题目应优先写 `question_concept_links`，`question_kp_links` 仅作 UI 兼容。`knowledge_points` 有 `weight`（0–100）与 `weight_tier`（core / supporting）；候选排序可优先给 weight 高的 core 概念。Myers 的题目已于 2026-10-28 删除，仅保留 678 条 KP / 82 个 Module / 概念成员；不要再引用已删除的 Myers 题目。

这些先写进报告，不要用相近但错误的知识点硬补。

### 7. 汇报格式

```text
## 结果
- 范围 / 试卷：
- 模型 / Prompt：
- 题目：N；linked N / needs_review N / no_match N
- 核心知识点覆盖：X/N
- 含图题 / 选项图片题：
- 待补概念：

## 产物
- 关联 JSON：
- 报告：
- 重建页面：

## 异常与待复核
- 答案可疑、候选缺失、同名 KP、含图题……
```

---

## 最短使用方式

```text
请按 01_question_kp_linking.md 执行。
范围：psychology-barrons-2027-ch11-review
模式：先盘点
```

确认候选和规则后：

```text
请按 01_question_kp_linking.md 执行。
范围：psychology-barrons-2027-ch11-review
模式：直接关联
重建刷题页：是
```
