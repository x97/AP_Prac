---
id: book-kp-extraction
title: 全书一次性知识点抽取
version: whole-book-kp-v1
status: active
kind: extraction
updated: 2026-10-30
inputs: [book_path, book_id, subject_id]
outputs: [sections, section_texts, knowledge_points, kp_aliases, kp_relations]
depends_on: []
used_by: [multi-book-concept-integration, data-agent-pipeline]
---
# 全书一次性知识点抽取提示语

> 版本：`whole-book-kp-v1`  
> 适用：任意学科、任意书型（教材 / 复习书 / 专著 / 词典 / 练习册）  
> 目标数据库：`data/content/<subject_id>/<subject_id>_knowledge.db`（设计见 `docs/content/数据库设计文档.md` Part B）  
> 核心约束：不合并小节、定义必须逐字原文、通俗解释 ≤10 个英文单词、最后强制去重。  
> 多本教材抽取完成后，另执行 `02_multi_book_concept_integration.md` 建/更新概念层（concept_clusters / concept_members / concept_relations）。

---

## 一、使用方法

1. 复制下面的提示语，替换开头的 `{...}` 占位符。
2. 把提示语作为**一个独立任务**交给执行模型；不要和“生成题目”“写总结”等任务混在一起。
3. 执行模型必须先完成 `Stage 0` 的书籍体检与学科归类，再进入抽取。
4. 只有全部 GATE 通过，才允许写 `data/content/<subject_id>/<subject_id>_knowledge.db` 的正式表；否则只写 staging 并输出失败报告。
5. 本次书籍的学科归类已预先确认为 `psychology`，书名为 `AP Psychology Premium, 2027`，`book_id` 为 `psychology-barrons-2027`；如果换成新书，保留 `SUBJECT_ID=auto` 让模型重新判定。

---

## 二、提示语（复制以下整段）

```text
# ROLE
你是一个“全书知识点抽取引擎”。你的任务是从指定书籍中一次性抽取全书知识点，完成校验与去重，并写入 `data/content/<subject_id>/<subject_id>_knowledge.db`。
你不使用书外知识，不补全、不猜测、不翻译原文定义，不合并小节。
你允许在内部按章节分批读取，但必须维护全书统一的 section/KP registry；最终去重与写库必须基于全书，不得把不同章节交给不同模型后直接拼接。

# INPUTS
BOOK_PATH = {书籍文件路径}
BOOK_ID = {书籍ID；留空则由你生成，格式 <subject_id>-<publisher-slug>-<edition>}
DB_PATH = {数据库路径，默认 /Users/aa/Documents/AP_psych/data/content/<subject_id>/<subject_id>_knowledge.db}
SCHEMA_SQL = {schema路径，默认 /Users/aa/Documents/AP_psych/docs/content/ap_knowledge_schema.sql}
SUBJECT_ID = auto                 # auto 或指定 subject_id；指定时跳过自动匹配但仍校验
BLOCK_LEVEL = toc_section         # toc_section | leaf_heading
PLAIN_LANGUAGE = en               # 通俗解释统一英文
PLAIN_MAX_WORDS = 10              # 硬性上限
EXCLUDE_SECTIONS = exercises,answer_keys,index,front_matter,ads,acknowledgements,table_of_contents
PROMPT_VERSION = whole-book-kp-v1

# NON-NEGOTIABLE RULES
1. 可追溯：每条 KP 必须有 book_id + section_id + source_page + definition_quote + quote_hash。
2. 原文优先：definition_quote 必须是该书该节中连续、逐字、可复现的原文；禁止改写、拼接、翻译、概括。
3. 不合并：目录中有几个知识点小节，就生成几个 section block；正文子标题作为 block 内条目，不得丢弃。
4. 不臆造：书中没有的定义、研究者、实验，写 NULL 或 "not_mentioned"；禁止用常识补全。
5. 通俗解释：plain_en 必须为 1–10 个英文单词，不得含中文，不得引入新事实。
6. 去重是最后一道强制门禁：未通过去重检查，不得写正式表。
7. 全书一次性：所有 section 的抽取、去重、写库必须在同一个 run 内完成；不得中途把未去重的章节结果直接写正式表。

# PIPELINE — 按顺序执行，每步有 GATE

## Stage 0 — 书籍体检与学科归类
1. 读取书籍元数据：标题、副标题、作者、出版社、ISBN、版次、年份、语言、总页数。
2. 判断文本层；无文本层则 OCR，记录 ocr_used、ocr_engine、ocr_confidence。
3. 定位目录页、正文起始页、索引、习题、答案、术语表；确定 PDF 页与印刷页映射，无法确定则 printed_page=NULL。
4. 识别版式：单栏/多栏、页眉页脚、脚注、表格、图注。
5. 学科归类：
   - 读取 `<subject_id>_knowledge.db` 的 subjects / subject_aliases。
   - 用元数据、目录结构、考试名称、术语密度四类信号匹配。
   - 至少 2 个独立信号一致，才可 classification_status='auto'；1 个信号或冲突 → 'needs_review'；无匹配 → 新建 subject_id 并标 'needs_review'。
   - 写 books 行（或 staging_books），classification_evidence 存 JSON 证据。
   - 当前示例（仅当输入是 AP Psychology 2027 时）：book_id='psychology-barrons-2027'，subject_id='psychology'，book_type='review_book'，target_exam='AP Psychology'，target_year=2027。
   - 若输入 SUBJECT_ID 不是 auto，直接使用该 subject_id；若它与书籍内容明显冲突，标 needs_review 并停止。
6. 写 run 记录：run_id、prompt_version、model、started_at、status='running'。
GATE G0：书籍可读；学科分类为 auto/confirmed；否则停止，只输出报告。

## Stage 1 — 全书结构地图
1. 解析目录，并在正文中按字号/编号/层级校验每个标题。
2. 生成 sections 列表：section_id、parent_id、level、heading（逐字原文）、heading_normalized、ordinal、path、pdf_page_start/end、is_leaf、excluded、excluded_reason。
3. 目录标题与正文标题逐条对账；缺失、重复、合并、拆分都写入结构报告。
4. 同名标题用 parent_path + ordinal 区分，不得只靠标题做唯一键。
5. 按 EXCLUDE_SECTIONS 排除习题、答案、索引、前言、广告等，并写明原因；目录页只作为结构来源，不作为知识点块。
6. 确定 BLOCK_LEVEL：
   - toc_section：目录小节 = section block；正文子标题 = 块内 subheading。
   - leaf_heading：最低一级标题 = section block。
GATE G1：目录/正文标题对账完成，差异有报告；否则停止。

## Stage 2 — 全书正文提取与切分
1. 逐页提取正文，保持阅读顺序；多栏书验证栏间顺序。
2. 表格、图注、脚注单独存放，不混入正文定义。
3. 每个 section 从当前标题切到下一个同级/更高级标题，禁止跨节；记录 page_start/page_end、text_hash、section_texts。
4. 每个 section 的首句、末句做边界抽检。
GATE G2：无空 section、无跨节、无阅读顺序错乱；否则回退重切或停止。

## Stage 3 — 全书知识点抽取
对每个 section 抽取 knowledge_points：
- name：书中印刷的概念名，保留大小写、缩写、连字符。
- name_normalized：小写、去标点、合并空白。
- subheading：必须是该 section 的 subheading 原文，或 NULL。
- definition_quote：该概念在本书中的逐字定义句/定义从句。
- definition_type：explicit | implicit | glossary | table | none。
- definition_language：原文语言。
- source_page：定义所在 PDF 页。
- researchers：仅限本节明确提到、且与该概念直接相关的人名；没有则 []。
- experiments：仅限本节明确提到的实验名/研究名；没有则 []。
- confidence：0–1。
- status：approved | needs_review。

规则：
- 每个 subheading 至少 1 条知识点；没有定义的子标题也要保留一条 needs_review 记录。
- 一个概念一条记录，不要把多个概念塞进一个 name。
- 定义优先级：正文显式定义 > 术语表/定义表 > 正文隐含解释 > none。
- 若 definition_type='none'，definition_quote=NULL，status='needs_review'；禁止用常识补写。
- 习题、答案、页眉页脚、图注、表头不作为知识点；术语定义表除外。
- 研究者/实验必须附 evidence_quote；只出现在本节但没有绑定到具体概念的，放入 section_researchers。
GATE G3：subheading 覆盖率 100%；无无出处定义；否则停止。

## Stage 4 — 原文定义校验
1. 规范化空白后，definition_quote 必须是 section 文本的连续子串。
2. 校验 quote 中包含该概念名，或明确的代词/指代；否则标记 weak_definition。
3. 单条 quote 超过 500 字符时，截取最小完整定义句；不得截断到语义不完整。
4. 计算 quote_hash = sha256(normalize(definition_quote))；记录 source_char_start/end（能取到则记录）。
GATE G4：逐字匹配率 100%；否则逐条修正，无法修正则 needs_review，不得 approved。

## Stage 5 — 通俗解释（1–10 个英文单词）
1. plain_en：简单英文，1–10 个英文单词，硬性上限。
2. 不得含中文；不得复制定义原文；不得引入书中没有的新事实。
3. 计数规则：按空白分词；连字符词算 1 个；缩写、数字各算 1 个；标点不计。
4. 好例子：
   - "learned fear of a specific object"（6）
   - "the tendency to recall first items better"（7）
5. 坏例子：
   - "a cognitive bias in which people tend to..."（超过 10，且是定义改写）
6. 若 10 个词内说不清，优先简化核心机制，不要加从句；仍说不清则 needs_review。
GATE G5：全部 plain_word_count 在 1–10；否则重写或 needs_review。

## Stage 6 — 全书去重（强制最后一步）
去重范围：同一本书内强制；跨书只做聚类，不删除。
1. 精确重复：normalized quote 完全相同。
   - 同一概念 → 保留最早一条，其余 duplicate_of 指向保留条目。
   - 一句话同时定义两个概念 → 拆成两条各自的概念定义；无法拆分时合并为一条并用 covers_concepts 记录两个概念。
   - 同名不同义 → 保留两条，标 homonym，不得按名称删除。
2. 近似重复：同一概念且 quote 相似度 ≥ 0.90 → 标 near_duplicate，人工复核；不得自动删除。
3. 同名不同定义：保留，标 same_name_different_definition；教材跨章复现通常属于此类。
4. 跨书重复：不删除；用 concept_cluster_id 关联，保留各书出处。
5. 输出去重报告：精确重复组数（前/后）、拆分共享定义数、同名概念对及分类、近重复对及相似度。
GATE G6：去重后 exact_duplicate_count = 0；否则停止，不得写正式表。

## Stage 7 — staging 写库与正式表提升
1. 先写 staging_sections / staging_knowledge_points（或带 run_id 的 staging 表）；全部 GATE 通过后再事务性插入正式表。
2. 使用确定性 ID：
   - section_id = sha1(book_id + path)[:16]
   - kp_id = sha1(book_id + section_id + name_normalized + quote_hash)[:16]
3. 幂等：同一 book_id 重跑时，按 (book_id, section_id, name_normalized, quote_hash) 判重；未变则跳过，变化则写新版本。
4. 写库前备份；正式表提升用 BEGIN IMMEDIATE; ... COMMIT;，失败 ROLLBACK。
5. 写库后执行 PRAGMA foreign_key_check、PRAGMA integrity_check、唯一约束检查。
GATE G7：事务成功、外键/唯一约束通过；否则回滚。

## Stage 8 — 全书 QA 报告
输出：
- 结构覆盖：sections 总数、排除数、未匹配标题数。
- 知识点覆盖：有 KP 的 section 比例、subheading 覆盖率。
- 引用校验：quote 逐字匹配率、weak_definition 数。
- 通俗解释：≤10 words 通过率、最长词数。
- 去重：exact/near/homonym 数量。
- 随机抽检：至少 20 条或 5%（取较大者）。
- validation_issues.csv、extraction_report.md。
只有全部 GATE 通过，run.status 才能写 success；否则 partial 或 failed。

# OUTPUT CONTRACT
- 正式表：sections、section_texts、knowledge_points、kp_researchers、kp_experiments、kp_aliases、kp_relations、section_researchers。
- 运行表：ingestion_runs、validation_issues。
- 文件：extraction_report.md、validation_issues.csv、dedupe_report.md。
- JSON：book.json、sections.json、knowledge_points.json（可选，便于复核）。

# STOP CONDITIONS
出现以下任一情况，立即停止并报告，不得写正式表：
- 无文本层且 OCR 置信度过低，或无法确定阅读顺序。
- 学科分类为 needs_review 且未人工确认。
- 目录/正文标题结构无法对账。
- section 文本为空、错位、跨节。
- subheading 覆盖率 < 100%。
- definition_quote 逐字匹配失败且无法修正。
- plain_en 超过 10 个英文单词或含中文。
- 去重后仍有 exact_duplicate。
- 外键/唯一约束/事务检查失败。

# FINAL CHECKLIST
[ ] 学科归类有证据，classification_status 为 auto/confirmed
[ ] 目录/正文标题逐条对账
[ ] 每个 section 有 page_start/page_end
[ ] 每个 subheading 至少 1 条 KP
[ ] 每条 definition_quote 逐字匹配
[ ] 每条 plain_en ≤ 10 个英文单词
[ ] 每条 KP 有 book_id/section_id/source_page/quote_hash
[ ] 去重后 exact_duplicate = 0
[ ] staging → 正式表事务成功
[ ] extraction_report.md、validation_issues.csv、dedupe_report.md 已生成
```

---

## 三、本次书籍的归类结果

| 字段 | 值 | 依据 |
|---|---|---|
| subject_id | `psychology` | 与 `<subject_id>_exam.db.subjects` 一致 |
| name | `AP Psychology` | 书名、目录、考试说明 |
| name_zh | `AP 心理学` | 现有学科中文名 |
| discipline | `Psychology` | 学科大类 |
| exam_code | `AP` | 书名、目录、版权页 |
| book_id | `psychology-barrons-2027` | 学科 + 出版社 + 版次 |
| title | `AP Psychology Premium, 2027` | 封面 |
| authors | `Allyson J. Weseley; Robert McEntarffer` | 封面/版权页 |
| publisher | `Barron's Educational Series (Kaplan)` | 版权页 |
| edition / year | `2027` / `2026` | 书名 / 版权页 |
| isbn | `979-8-3497-0153-5` | 版权页 |
| language | `en` | 正文 |
| book_type | `review_book` | 复习书 + 练习题 + 模拟卷 |
| target_exam | `AP Psychology` | 目录含 AP Psychology Course and Exam Description |
| target_year | `2027` | 书名与封面 |
| classification_status | `confirmed` | 多信号一致 |

已写入 `<subject_id>_knowledge.db` 的 `subjects`、`subject_aliases`、`books` 表。

---

## 四、与多阶段版的关系

- 本文件是**全书一次性抽取版**：一个 run 内完成体检、结构、抽取、校验、去重、写库、QA。
- 如果书特别大（例如 1000 页以上），允许内部按章节分批读取，但必须维护全书统一 registry；最终去重与写库仍是一个 run。
- 多阶段版（先结构地图、再分章抽取、最后去重）适合人工逐步复核；本文件适合自动化流水线。
- 无论哪个版本，**最后一步都是去重**，且必须通过 `exact_duplicate_count = 0` 才能写正式表。

---

## 五、数据库与校验脚本

- Schema：`docs/content/ap_knowledge_schema.sql`
- 设计文档：`docs/content/数据库设计文档.md`（Part B / 附录 C）
- 数据库：`data/content/<subject_id>/<subject_id>_knowledge.db`
- 本次 860 条迁移脚本：`_tools/import_102_to_knowledge_db.py`
- 本次英文解释映射：`data/content/psychology/reports/knowledge/unit*_plain_en.json`
- 本次导入报告：`data/content/psychology/reports/knowledge_import_report.md`
- 知识点由 API/Admin 从 active Release 读取，不再生成静态查看器。
- 参考校验脚本（需按 `<subject_id>_knowledge.db` schema 改造）：`_tools/validate_extraction.py`、`_tools/dedupe_extraction.py`
