---
id: pdf-question-ingestion
title: PDF 题目解析入库
version: pdf-question-ingestion-v1
status: active
kind: ingestion
updated: 2026-10-30
inputs: [pdf_path, subject_id, paper_meta]
outputs: [papers, questions, options, assets, frq_rubrics, rubric_parts]
depends_on: []
used_by: [question-concept-linking, ai-explanation, data-agent-pipeline]
---
# PDF 题目解析入库提示语

> 用途：下次把一份试卷 / 题库 PDF（或扫描图）交给 Claude，让它按统一流程解析题目、答案、解析、评分标准和题图，写入 `data/content/<subject_id>/<subject_id>_exam.db`，并生成可复核报告与刷题页。
>
> 用法：复制下面「提示词正文」整段，填好「任务参数」后发给我。默认先做只读盘点；只有明确写“直接入库”才写数据库。  
> 本文只定义通用提示语；AP Psychology 的具体数据源、脚本、字段映射见 `../docs/content/试卷解析方法.md`。
>
> AI 解析生成提示语：`05_ai_explanation.md`（只生成/补 `options.ai_explanation`，不重新导入试卷）。

---

## 任务参数（先填这里）

```text
【任务参数】
- 任务模式：先盘点（默认） / 直接入库
- PDF 或图片路径：
- 学科 subject_id：psychology / statistics / ...
- 目标数据库：/Users/aa/Documents/AP_psych/data/content/<subject_id>/<subject_id>_exam.db
- 来源 ID（source_id）：
- 来源名称（中文/英文）：
- 学科 / 考试 / 年份：
- 试卷类型：真题 real_exam / 模拟题 mock_exam / 单元练习 unit_practice
- 页码范围或章节：
- 是否包含 FRQ / 评分标准：
- 是否生成刷题页面：
- 其他要求：
```

---

## 提示词正文

你是本项目的试卷数据工程师。目标：把指定 PDF / 图片中的**题目、选项、答案、解析、评分标准和必要题图**解析为结构化数据，写入 `data/content/<subject_id>/<subject_id>_exam.db`，并保证可追溯、可复核、可重建。

### 0. 先读项目规则，不要凭记忆写库

开工前先读取并遵守：

1. `/Users/aa/Documents/AP_psych/docs/content/数据库设计文档.md`
2. `/Users/aa/Documents/AP_psych/docs/content/试卷解析方法.md`
3. `data/content/<subject_id>/<subject_id>_exam.db` 的实际 schema（以数据库为准，不以文档猜测）
4. 如果任务是单元练习，再读 `config/practice_groups/<subject_id>.json` 和 `prompts/06_unit_practice_merge.md`

硬性边界：

- 只处理**题库数据**。不要把知识点、教材、课程、标签、集合等表重新加回 `*_exam.db`；知识点写入 `data/content/<subject_id>/<subject_id>_knowledge.db`。
- `paper_type` 只允许三种：`real_exam`、`mock_exam`、`unit_practice`。教材课后题、章末 Review Questions 一律归为 `unit_practice`。
- 不擅自改表结构；需要加字段时先说明原因并等我确认。
- 不删除、不覆盖本轮范围之外的试卷和题目。所有写入必须限定在本次 `paper_id` 范围内。
- 不伪造答案、解析、页码、题图或评分标准。源文件没有的，保持 `NULL` 并写进报告。

### 1. 先盘点 PDF，不要直接开始写数据库

先输出一份“结构地图”，至少包括：

- PDF 总页数、是否有文本层、是否扫描件、单栏/双栏/混合栏。
- 目录、单元、章节、试卷、题目区、答案区、解析区、评分标准区的**PDF 页码范围**。
- 每套卷的题型与数量：MCQ、FRQ、AAQ、EBQ 等。
- 答案和解析在哪里：答案表、绿色高亮、Answer Explanations、评分标准、单独答案 PDF。
- 图表/表格/示意图清单：大致页码、对应题号或题组。
- 可能的风险：跨页题、跨页选项、双栏错序、答案缺失、扫描模糊、表格串行、题目共用材料等。

区分：

- **PDF 页码**：从 1 开始的 `PDFPage` 索引，用于 `assets.page`、复核和裁图。
- **印刷页码**：书页上印的页码，只用于展示或追溯，不要拿它当 PDF 索引。

默认先盘点，不写库。只有任务参数写了“直接入库”，或我明确说“开始入库”，才进入写库阶段。

### 2. 文本和版面提取

- 优先使用带坐标的文本行，不要只用 `page.string`。`page.string` 可能把选项标签和正文合并，导致选项错位。
- 用 PDFKit / `PDFSelection.selectionsByLine()` 或等效方式提取：`page`、`line_no`、`x`、`y`、`w`、`h`、`text`。
- 双栏页面按栏重建阅读顺序；跨栏图表要单独处理。
- 扫描件先 OCR；OCR 结果必须保留原始页码和坐标，低置信度内容标记出来。
- 不要把整页文本直接按空格切分后硬猜题目边界；题号、选项标签、答案标签、页眉页脚都要有明确规则。

### 3. 解析题目

每道题至少保存：

- `question_id`
- `paper_id`
- `section`：`MCQ` / `FRQ`
- 原始题号 `number`；必要时保存 `form` 和展示用编号
- `stem`：只放题目本身，不要把上一题/下一题的题干粘进来
- `context`：共用材料、实验描述、图表引导语、题组说明
- `page_start` / `page_end`：题目实际跨页范围
- 正确选项 `correct_answer`
- 答案说明 `answer_text`
- 答案来源 `answer_source` 与置信度
- 选项：A–E 的 `label`、`content`、`sort_order`、`is_correct`、正确选项的 `explanation`

解析规则：

1. 只解析题目区。目录、页眉页脚、章节标题、Answer Explanations 的题号、评分标准行不能当作新题；答案区必须与题目区分开。
2. 题号必须按原卷顺序；发现跳号、重号、跨页续题时先记录，不要强行合并。
3. 共用材料只放在 `context`，不要在每个 `stem` 里重复。
4. 如果下一步会用题图展示表格/图表，`context` 只保留引导句，例如“The data appear in the table below.”；不要把 PDF 解析出来的表格单元格文字继续塞进 context。
5. 如果表格必须以文本形式保存，必须按行列重建；禁止把表格单元格拼成一串不可读文本。
6. 选项必须拆成独立 A/B/C/D/E；不能把下一题的引导语吸进上一题选项。
7. 跨页选项、跨页题干要正确延长 `page_end`。
8. 题目共用一段材料时，每道题都要能独立读出；`context` 相同是允许的。
9. 题目文本以 PDF 原文为准；明显 OCR 错字要修正并记录，不要改题意。
10. 题目 ID 统一使用稳定格式，例如 `paper_id-001`；不要用随机 ID。

### 4. 答案与解析

答案必须来自源文件；即使模型自己知道正确答案，也不能用模型知识补答案。

答案来源按优先级：

1. 官方答案表 / 官方评分标准 → `answer_source='official'`
2. 官方绿色高亮或官方标注 → `answer_source='official_highlight'`
3. 教材/第三方书的 Answer Explanations → `answer_source='book_answer'`
4. 只有答案字母、没有解释 → 保留答案，解析为空
5. 原文件没有答案 → `correct_answer=NULL`、`answer_text=NULL`，在报告中列出

解析规则：

- `options.explanation` **只给正确选项**写解析；错误选项没有逐项解析时保持 `NULL`，不要编造。
- 如果原书解析是“题目级”的一段话，放入 `questions.answer_text`，并同步到正确选项的 `options.explanation`。
- 如果原书解析同时讨论多个选项，也不要拆成假的逐项解析；保留原文，并在报告中说明。
- 如果正确选项有绿色高亮/颜色标记，颜色检测结果要与答案表交叉验证；两套答案不一致时保留异常，不要静默选一个。
- 同一题出现两个“Correct.”或多个疑似正确答案时，不要静默选一个；保留异常，写入报告，等复核。
- 原书缺失答案的题必须保留，不能为了“完整性”编答案；刷题页应显示“原书未提供答案”，且不计入正确率。
- 如果用户明确要求 AI 生成解析，必须写入单独的 `options.ai_explanation` 字段，不能写进 `options.explanation`，也不能伪装成 `book_answer` / `official`；页面要标注“AI 生成解析”。
- AI 解析只写正确选项，基于题干、context、选项和**已核对答案**生成；不得改动答案，不得编造题目里没有的研究、数据或事实。标准 AP 心理学教材定义可以使用。
- 批量生成用 `_tools/generate_ai_explanations.py`（默认英文、批量请求、断点续跑、失败回退）。先生成到 `data/content/<subject_id>/extraction/ai_explanations_<paper>.json`，再写库；报告写到 `data/content/<subject_id>/reports/ai_explanation_report.md`。
- 刷题页把 `options.explanation`（原书解析）和 `options.ai_explanation`（AI 生成解析）分开显示，AI 解析带明确标签，不覆盖、不合并。

### 5. 题图、表格和截图（重点）

默认原则：**题图只放题目真正需要的图表、表格、示意图，不放整页截图。**

#### 5.1 什么时候需要图

题目或共用材料出现以下情况时才配图：

- 明确说“diagram / graph / chart / table / figure / scatter plot below”
- 题目要求读柱状图、折线图、散点图、数据表、示意图
- 选项本身是图片
- 没有图就无法作答

不要因为题干/材料里出现 `data`、`results`、`values` 这种泛词就自动配整页图；这类词经常是误报。

#### 5.2 正确做法

1. 先把图表按题组建立清单：`chapter/paper → question numbers → source page → figure type`。
2. 对文本层 PDF：题目文字从 PDF 提取并渲染；图片只裁**图表/表格区域**。
3. 对扫描件：如果文字确实无法可靠提取，可以裁“题目区域”，但不要默认整页；仍要在报告里说明原因。
4. 图表可能在题目的**上一页**（题组材料页）或下一页；不要只用 `page_start..page_end` 找图。
5. 裁图时使用页面 2 倍渲染 + 文本行锚点 + 内容自动裁边；保留完整标题、坐标轴、单位、图例、表头、行标签。
6. 同一张图被多道题共用时，可以给多道题挂同一张裁切图，但不要复制成不同图片内容。
7. `assets` 记录：
   - `kind='figure'`：示意图、折线图、柱状图、散点图
   - `kind='table'`：表格
   - `kind='option'`：选项图
   - `option_label`：选项图才填 A–E，题目级图保持 `NULL`
   - `page`：来源 PDF 页码
   - `bbox`：相对整页的比例坐标 `[x0,y0,x1,y1]`
   - `path`：相对项目根目录的裁切图路径
8. 选项本身是图片时：每张选项图单独存为 `kind='option'`、`option_label` 填对应字母；`options.content` 放“见图 A”这类占位文本，不要把整页截图当选项图。
9. 扫描件/无文本层时：优先裁“题目自身的区域”（题干 + 选项，通常不含相邻题）；确实只能整页时，`kind='page'`，并在报告里写明原因。不要把整页截图当默认方案。
10. 保存裁图后必须逐张目检，或拼成 contact sheet 统一目检：
   - 有没有把相邻题、页眉页脚、上一题选项裁进去？
   - 有没有把表头、坐标轴标签、单位裁掉？
   - 题目文字是否已经在页面上单独显示，图片是否只保留图表？
11. 如果找不到对应图，或图在源文件中缺失：不要拿一张整页图凑数；标记为缺图并写进报告。

#### 5.3 错误示例（禁止）

- 把 page87.png、page88.png 整页挂到 Q3/Q4；实际 Q3/Q4 没有图。
- 题目说“table below”，却挂了题目下一页的整页截图。
- 图表在上一页 p310，却只按 `page_start=311` 找图，导致图根本没入库。
- 表格文字已经从 PDF 解析进 `context`，又展示同一张表，造成重复。
- 把整页截图当默认兜底，导致页面里出现相邻题和答案区。

### 6. FRQ 和评分标准

- `section='FRQ'`；题干、子问、材料分开保存。
- `frq_rubrics` 保存总分、评分格式、题目说明。
- `rubric_parts` 保存每个评分点：part、points、criteria、判定规则、正例/反例。
- 不要把 Sample Student Answer 当成题干；不要把评分标准粘进 `stem`。
- AAQ / EBQ、Set 1 / Set 2 等用 `form` 或展示编号区分，保持套内编号可还原。
- 评分标准缺失时保留空值并报告，不要自己补评分点。

### 7. 入库规则

- 一套 Practice Test / 一个 Unit / 一个 Chapter 的练习 = 一份 `papers` 记录；不要把多套模拟卷、多个章节合并成一份卷，也不要擅自拆开一套完整试卷。
- 写库前备份：`cp data/content/<subject_id>/<subject_id>_exam.db <same>.bak-<日期>-<原因>`。
- 开启 `PRAGMA foreign_keys = ON;`
- 使用事务；先删除本 `paper_id` 的旧 questions/options/assets/rubrics/paper_sources，再插入；不要误删其他试卷。
- 先导出中间 JSON（如 `data/content/<subject_id>/extraction/<source>_questions.json`），再入库；这样可复核、可重建。
- 重新导入会删除并重建该卷的 `options`；如果该卷之前生成过 `ai_explanation`，入库后需要重跑 `_tools/generate_ai_explanations.py`。
- `papers.question_count`、来源表、`content_sources`、`paper_sources` 要同步更新；`source_id` 先落到 `content_sources`，每份卷在 `paper_sources` 记录来源 PDF、角色和备注。
- 选项、题目、素材的 ID 必须稳定、唯一。
- 同一道题不要重复插入；重复运行必须幂等。
- 入库后执行：
  - `PRAGMA foreign_key_check;`
  - `PRAGMA integrity_check;`
  - 重复 `question_id` / `asset_id` 检查
  - 选项数量检查（每道 MCQ 的选项标签连续，A–D 或 A–E 按原题，不可缺项）
  - 答案覆盖、解析覆盖、缺答案清单
  - 素材路径是否存在
  - 是否有整页图被当成题图（除非报告明确说明）
  - 是否有 `page` 类型素材混入本应裁切的题图

### 8. 质量门禁

至少输出并核对：

- 试卷数、题目数、选项数、素材数、评分标准数
- 每套卷的 MCQ / FRQ 数量
- 有答案题数、有解析题数、缺答案题号
- 每道 MCQ 的选项数分布
- 唯一题图数 vs 题图引用数
- 跨页题清单
- 共用材料/题组清单
- 图片裁切清单
- 异常清单：答案冲突、题干缺失、选项缺失、图片缺失、OCR 低置信度

抽样人工复核：

- 每套卷至少看第一题、最后一题、一题跨页题、一题图片题、一题缺答案题
- 对照 PDF 原页检查题干、选项、答案、解析、页码
- 至少打开一张生成的刷题页，检查图片裁切、点击放大、判分反馈、返回链接

### 9. 页面与前端

新项目是前后端分离，数据写入科目源库并构建 Release 后，由 API/Web 直接读取；不再生成静态刷题页。

- 用 SQL 校验题目、选项、答案、图片引用；
- 需要预览时启动 API/Web，不要写回 HTML 文件；
- 数据改了但 Release 没重建，学生端就仍是旧数据；在报告里写清是否已重建/激活 Release。

### 10. 最终汇报格式

完成后按以下格式汇报：

```text
## 结果
- 来源 / 年份 / 试卷类型：
- 新增或更新试卷：
- 题目：MCQ N / FRQ N
- 选项：
- 有答案 / 有解析 / 缺答案：
- 题图引用 / 唯一裁切图：
- 数据库检查：foreign_key_check / integrity_check

## 产物
- 解析 JSON：
- 导入脚本：
- 入库报告：
- 生成的页面：

## 异常与待复核
- ...
```

### 11. 禁止事项

- 禁止编造答案、解析、页码、题图、评分点。
- 禁止把不同科目的题目写入同一个源库；每科只写自己的 `data/content/<subject_id>/<subject_id>_exam.db`。
- 禁止把 statistics 等科目的数据写进 psychology 的源库；根目录已不再提供 `ap_exam.db` 兼容链接。
- 禁止用整页截图作为默认题图。
- 禁止把相邻题、页眉页脚、答案区裁进题图。
- 禁止把表格单元格文字同时塞进 context 和题图。
- 禁止把知识点表重新加回 `<subject_id>_exam.db`。
- 禁止修改本轮范围之外的试卷。
- 禁止在没有备份的情况下做破坏性写入。
- 禁止只报“已完成”而不给数量、异常和验证结果。

---

## 最短使用方式

如果不想每次填很多参数，可以直接发：

```text
请按 04_pdf_question_ingestion.md 执行。
PDF：<路径>
数据库：data/content/<subject_id>/<subject_id>_exam.db
模式：直接入库
生成刷题页：是
```

如果源文件复杂、跨页题多、图表多，建议先用默认“先盘点”模式，让我输出结构地图和图表清单，再开始入库。
