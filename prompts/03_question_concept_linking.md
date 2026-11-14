---
id: question-concept-linking
title: 题目知识点生成（概念层）
version: question-concept-link-v2
status: active
kind: linking
updated: 2026-10-30
inputs: [paper_id, concept_db, scope]
outputs: [question_analysis, question_concept_links, question_keywords]
depends_on: [multi-book-concept-integration, pdf-question-ingestion]
used_by: [data-agent-pipeline]
---
# 题目知识点生成提示语（概念层 v2）

> 版本：`question-concept-link-v2`  
> 用途：给一套新科目题库或一批新题生成“题目解析”：核心概念、辅助概念、干扰项易混淆概念、题目中实际出现的关键字。  
> 重要变化：**题目关联的第一目标层是规范概念 `concept_clusters`，不是来源 KP**。来源 KP 只作为概念的定义/出处成员。  
> 用法：复制「提示词正文」，填好「任务参数」后发给执行模型。默认先盘点、先试跑，确认后再全量。

---

## 任务参数（先填这里）

```text
【任务参数】
- 科目 / 考试：
- 题目库路径：
- 知识点库路径：
- 范围：单套卷 paper_id / 某章 / 某单元 / 全部
- 概念层状态：已建立 / 需要先从教材建立
- 语言：题目语言 / 解析语言
- 核心概念粒度：1 个（默认）/ 最多 2 个
- 选项是图片的题：跳过（默认） / 人工读图后补
- 含图题：正常关联并在报告标记 / 跳过
- 是否重建页面：是 / 否
- 其他要求：
```

---

## 提示词正文

```text
# ROLE
你是本项目的题目分析员。目标：为每道选择题建立“关键字 + 规范概念”关联，写入题目解析库，供刷题页展示。

你不直接按来源 KP 名称扫词，也不把“题干里出现的词”当成被考查概念。你的第一目标层是 concept_clusters（规范概念）；knowledge_points 只是概念的来源和定义证据。

# 0. 先读实际 schema，不要套用别的科目
开工前先检查：
- 题目库：questions / options / correct_answer / explanation / ai_explanation 在哪些表；
- 知识库：subjects / books / sections / knowledge_points / concept_clusters / concept_members / concept_relations；
- 关联表：question_analysis / question_concept_links / question_keywords 是否存在；
- 兼容表：question_kp_links 是否还在使用；
- 别名表：kp_aliases 的 match_mode 是否支持大小写敏感缩写；
- 题目所属 unit/chapter 如何从 paper_id、section 或 context 推断。

如果字段名不同，先写适配层/脚本，不要直接改原库结构。

# 1. 核心定义（必须遵守）
- 关键字：题目文本里实际出现的术语或概念短语。出现 ≠ 被考查。
- 核心概念：学生要选对正确答案必须理解的那个规范概念。从正确答案倒推，不是从题干/干扰项扫词。
- 一道题通常 1 个核心概念，最多 2 个；辅助概念最多 1 个。
- 干扰项里的术语只进 confusable（带选项字母），绝不能进 core。
- 知识库没有的概念，标 needs_review / no_match，不要硬套相近概念。
- 同名异义概念必须靠 concept_id 或限定词区分；不得只按名称选。

自检规则：
> “如果学生没学过这个术语，他还能做对这道题吗？”
> 不能 → 核心概念；能但会被骗 → confusable。

# 2. 先盘点，不要直接写库
盘点至少输出：
- 每套卷/章节的 MCQ 数量、有答案数量、有解析数量；
- 概念层总量、core/supporting 分布、别名覆盖；
- 该卷/章节可用概念池数量；
- 同名/重复概念（same_concept / homonym）清单；
- 选项图片题、含图题清单；
- 哪些题还没有分析、哪些题需要复核。

然后先选 10–20 题试跑，人工检查核心概念和 confusable，再全量。

# 3. 候选检索（概念级）
不要把所有概念一次性塞给模型，也不要用“题干扫词”直接决定概念。

推荐流程：
1. 范围池：该题所属 unit/chapter 的全部 concept_clusters；
2. 别名精确匹配：概念名、来源 KP 名、kp_aliases、括号别名、缩写；
3. BM25/全文检索：用题干 + context + 正确选项 + 原书解析检索候选；
4. 取 40–90 个候选，分配短 key（C01、C02…），模型只能选 key。

候选必须带：
- concept_id、canonical_name、weight、weight_tier；
- 1–3 条来源定义（book_id、book 名称、section、definition_quote）；
- 同名概念的限定词/章节，避免混用。

别名要求：
- 括号别名：Evolutionary (or Darwinian) Perspective → Evolutionary Perspective / Darwinian Perspective；
- 缩写：Applied behavior analysis (ABA) → ABA，并标为大小写敏感；
- 避免 DID 匹配普通单词 did、CNS 匹配普通词；
- 同名不同义靠 concept_id + 限定词 + 章节区分；
- 同一概念的重复来源 KP 已在 concept_members 中合并，候选只出现一次。

# 4. 让模型选择，不要让模型自由发挥
对每道题，模型必须返回严格 JSON：

{
  "status": "linked",
  "core": [
    {"concept": "C01", "confidence": 0.95, "evidence": "题干/正确选项原文"}
  ],
  "supporting": [
    {"concept": "C02", "confidence": 0.8, "evidence": ""}
  ],
  "confusables": [
    {"concept": "C03", "option_label": "B", "reason": "为什么这个干扰项容易混淆"}
  ],
  "keywords": [
    {
      "surface": "exact text from the question",
      "concept": "C01",
      "role": "core",
      "location": "stem",
      "option_label": null
    }
  ],
  "notes": ""
}

规则：
- core 1–2 个；status=linked 时必须有 core；
- core.evidence 必须是题干/context/正确选项的原文；
- confusable 必须是同章节/同小节的近义干扰项，不能只是“错误选项里出现了一个概念”；没有就近义项就返回空数组；
- confusable.option_label 必须是错误选项；
- keyword.surface 必须真的出现在指定位置；
- keyword 应是术语/概念短语，不是整句选项；
- 无法映射的 keyword 可以 concept=null，表示术语存在但概念库未收录；
- 找不到合适候选就 status=no_match / needs_review，不要硬套。

# 5. 自动校验
写库前至少检查：
- core 数量 1–2；core 不能只匹配干扰项；
- core evidence 能在题干/context/正确选项中定位；
- confusable 必须在对应错误选项里出现，且与 core 同章节/同小节；不能和 core 重复；
- supporting 必须在正确选项或 core 的同一小节；
- keyword surface 必须在指定位置；
- keyword 映射的 concept 必须存在，且 surface 是该概念的已知别名/成员名；
- 同名概念没有混用：core/confusable 的 concept_id 与限定词一致；
- 选项图片题跳过；含图题在报告中标记；
- 通用词（theory / concepts / need / learning / personality 等）不要轻易当 core；
- 写库前备份；写库后跑 PRAGMA integrity_check / foreign_key_check。

# 6. 写库建议
关联表不要放在题目库；放知识点库或独立关联库。

第一目标层：
- question_concept_links：question_id、concept_id、relation_type（core/supporting/confusable）、option_label、confidence、evidence、rationale、created_at；
- 唯一键：(question_id, concept_id, relation_type, IFNULL(option_label,''))。

分析状态：
- question_analysis：question_id、paper_id、status、model、prompt_version、notes、updated_at。

关键字：
- question_keywords：当前 schema 用 `kp_id`；概念层优先时，建议新增 `concept_id`，或写该概念的 `canonical_kp_id`。字段至少包含 surface、role、location、option_label。

兼容层：
- question_kp_links：仅当旧页面/旧脚本仍依赖时写入；新逻辑以 question_concept_links 为准。
- 写 KP 兼容层时，优先用 concept_clusters.canonical_kp_id；没有则取概念成员中该书的首选 KP。

question_id 是逻辑引用，不建跨库外键；concept_id 保留知识点库外键。

# 7. 页面展示
页面只展示三层：
1. 核心概念（1–2 张卡）
2. 辅助概念
3. 易混淆概念（折叠；答错且选中某个干扰项时自动展开）

交互：
- 答对：默认折叠，只显示“本题解析 · 核心概念名”；
- 答错：自动展开；
- 关键字 chip 可点击，弹出规范概念、权重、来源教材定义；
- 题干/context/正确选项里的已映射关键字可加虚线点击；
- 不要显示“相关术语”“干扰项术语”这类额外区块；未收录术语只在“核心概念未收录”提示里出现；
- 选项本身是图片的题不要硬生成。

# 8. 质量门禁
至少输出：
- linked / needs_review / no_match 数量；
- 每题 core 是否 1–2 个；
- 核心概念覆盖率；
- confusable 数量分布；
- 待补概念清单；
- 同名/重复概念误用清单；
- 含图题 / 选项图片题清单；
- 数据库 integrity / foreign_key_check。

# 9. 汇报格式
## 结果
- 科目 / 范围：
- 模型 / Prompt：
- 题目：N；linked N / needs_review N / no_match N
- 核心概念覆盖：X/N
- 待补概念：
- 含图题 / 选项图片题：

## 产物
- 关联 JSON：
- 报告：
- 重建页面：

## 异常与待复核
- ...
```

---

## 三、本项目可直接用的命令

当前 AP Psychology 的实现：

```bash
# 1. 首次建关联表 / 补别名
python3 _tools/migrate_question_analysis.py
python3 _tools/build_kp_aliases.py

# 2. 概念层 linker（推荐）
python3 _tools/link_question_concepts.py --paper <paper_id> --dry-run --limit 3
python3 _tools/link_question_concepts.py --paper <paper_id> --force

# 3. 只跑某几题 / 指定范围
python3 _tools/link_question_concepts.py --paper <paper_id> \
  --question-id <question_id> --scope "Chapter 11" --scope-kind chapter

# 4. 旧逻辑：按 KP 关联（legacy；只写 question_kp_links）
python3 _tools/link_question_kps.py --paper <paper_id> --force

# 5. 概念层权重重算
python3 _tools/recompute_concept_weights.py
```

`link_question_concepts.py` 的行为：

- 候选池：`concept_clusters`（含所有成员名/别名/来源定义），不是来源 KP；
- 模型输出：`core/supporting/confusables` 选 `C01...` 概念 key；
- 写库：`question_concept_links` 为主，`question_kp_links` 用 `canonical_kp_id` 镜像；
- `question_keywords` 新增 `concept_id`，同时保留 `kp_id` 兼容旧页面；
- 默认跳过已有 core 概念关联的题；`--force` 才重链；
- `--exam-db` / `--know-db` 可指向新学科/临时库；
- `--scope` / `--scope-kind` 可手动指定 unit/chapter 池；
- `--no-kp-links` 可关闭 `question_kp_links` 旧表镜像。

新学科要替换的是：

- `data/content/<subject_id>/<subject_id>_exam.db` / `<subject_id>_knowledge.db` 的表名和字段；
- `--scope` / `--scope-kind` 的 unit/chapter 规则；
- `_tools/link_question_concepts.py` 的 `load_concepts`（如果新学科概念表结构不同）；
- 页面模板。

---

## 四、最短使用方式

```text
请按 03_question_concept_linking.md 执行。
科目：<科目>
题目库：<路径>
知识点库：<路径>
范围：先抽 20 题试点
模式：先盘点 + 试跑
概念层：已建立
```

试点确认后：

```text
请按 03_question_concept_linking.md 执行。
范围：全部选择题
模式：直接生成
写库：question_concept_links 优先，question_kp_links 仅兼容
重建页面：是
```
