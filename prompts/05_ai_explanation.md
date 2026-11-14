---
id: ai-explanation
title: AI 答案解析生成
version: ai-explanation-v2
status: active
kind: generation
updated: 2026-10-30
inputs: [paper_id, question_scope]
outputs: [options.ai_explanation]
depends_on: [pdf-question-ingestion]
used_by: [data-agent-pipeline]
---
# AI 答案解析生成提示语

> 用途：下次让 Claude 为缺少解析的选择题批量生成 AI 解析，写入 `data/content/<subject_id>/<subject_id>_exam.db` 的 `options.ai_explanation`，并重建刷题页。
>
> 用法：复制下面「提示词正文」整段，填好「任务参数」后发给我。默认先盘点、先试跑，确认无误后再全量生成。

---

## 任务参数（先填这里）

```text
【任务参数】
- 任务模式：先盘点（默认） / 直接生成
- 学科 subject_id：psychology / statistics / ...
- 目标数据库：/Users/aa/Documents/AP_psych/data/content/<subject_id>/<subject_id>_exam.db
- 范围：单套卷 paper_id / 全部试卷 / 只补没有原书解析的题
- 语言：英文（默认） / 中文 / 中英双语
- 解析粒度：只写正确选项（默认，与 explanation 一致）
- 选项是图片的题：跳过（默认） / 包含（需额外提供选项图片内容）
- 带图题（题干或材料含图表）：生成并在报告中标记 / 跳过
- 模型：当前环境默认模型 / 指定模型
- 是否重建刷题页：是 / 否
- 其他要求：
```

---

## 提示词正文

你是本项目的 AI 解析工程师。目标：为**缺少解析的选择题**生成答案解析，写入 `data/content/<subject_id>/<subject_id>_exam.db` 的 `options.ai_explanation`，保证可追溯、可复核、可重建。

### 0. 先读规则，不要凭记忆写库

开工前先读取并遵守：

1. `/Users/aa/Documents/AP_psych/docs/content/数据库设计文档.md` 的 `options` 表说明（§3.6）
2. `04_pdf_question_ingestion.md` 第 4 节「答案与解析」
3. `data/content/<subject_id>/<subject_id>_exam.db` 的实际 schema（以数据库为准，不以文档猜测）
4. `_tools/generate_ai_explanations.py --help`
5. 如果任务涉及单元练习，再读 `prompts/06_unit_practice_merge.md`

硬性边界：

- **只写 `options.ai_explanation`，绝不写、绝不覆盖 `options.explanation`。**
- `options.explanation` 是原书/官方解析；`options.ai_explanation` 是 AI 生成解析。两者必须分开。
- **只给正确选项写 AI 解析**；错误选项保持 `NULL`。本项目的 AI 解析是题目级解析，不是逐项错误分析。
- 不得修改 `questions.correct_answer`。答案缺失、答案不是 A–E、答案与选项行对不上的题，跳过并写进报告，不要猜答案。
- 不得编造题目里没有的研究、统计数字、人物、图表细节。标准 AP 心理学教材定义和概念可以使用。
- 选项本身是图片的题，默认跳过：文字里没有选项内容，模型无法可靠判断。除非用户明确提供图片内容或允许读图；允许读图时，可逐题查看 `assets/.../opt_*.png` 后手工写入 `ai_explanation`，并在汇报中注明「读图补写」。
- 题干/材料带图表的题可以生成，但必须在报告中标记「含图题，建议人工复核」；当前流程只把文字送给模型，图表本身没有送进去。
- 不删除、不覆盖本任务范围之外的试卷和题目。
- 写库前必须备份数据库。

### 1. 先盘点，不要直接开始生成

先运行只读查询，输出一张覆盖表：

| 试卷 | MCQ | 有原书解析 | 已有 AI 解析 | 待生成 | 选项图片题 | 含图题 |
|---|---:|---:|---:|---:|---:|---:|

至少核对：

- 哪些试卷还有待生成题目；
- 是否已有 `ai_explanation`（默认跳过，`--force` 才会重生成）；
- 选项图片题的数量和题号；
- 含图题的数量和题号；
- 数据集是否完整（`PRAGMA integrity_check`、`PRAGMA foreign_key_check`）；
- API 端点、模型、API key 是否可用（只检查变量名，不打印密钥）。

如果「待生成」为 0，直接输出当前覆盖报告并结束，不要调用模型。

### 2. 先小样试跑，再全量

先跑 3–5 题，检查：

- 解析是否基于题干和正确答案；
- 是否出现答案矛盾、编造的研究/数据；
- 长度是否在 2–4 句、约 40–90 个英文单词；
- 是否误写进 `options.explanation`；
- 页面是否正确显示「AI 生成解析 · 仅供参考」。

小样确认后再全量。推荐命令：

```bash
# 单套卷（默认 psychology；其他科目显式传 --subject）
python3 _tools/generate_ai_explanations.py --subject psychology --paper <paper_id> --limit 5
python3 _tools/generate_ai_explanations.py --subject psychology --paper <paper_id>

# 全部试卷中，只补没有原书解析、也还没有 AI 解析的题
python3 _tools/generate_ai_explanations.py --subject psychology --all --skip-book-explained

# 只重做某一套卷的 AI 解析
python3 _tools/generate_ai_explanations.py --subject psychology --paper <paper_id> --force

# 先看提示词，不调用 API
python3 _tools/generate_ai_explanations.py --subject psychology --paper <paper_id> --dry-run --limit 3
```

脚本行为：

- 用 `--subject <subject_id>` 读取 `config/subjects/<subject_id>.json`，默认写 `data/content/<subject_id>/<subject_id>_exam.db`；
- 默认跳过已有 `ai_explanation` 的题，可断点续跑；
- 默认跳过选项图片题；`--include-option-images` 可强制包含（不推荐）；
- 默认生成含图题；`--skip-figures` 可跳过；
- 批量请求失败时自动回退单题请求；
- 写库前先导出 `data/content/<subject_id>/extraction/ai_explanations_<paper>.json`；
- 写库前自动备份 `<subject_id>_exam.db.bak-<时间>-ai-explanation`；
- 覆盖报告写到 `data/content/<subject_id>/reports/ai_explanation_report.md`。

### 3. 生成规则

对每道题，输入：题号、题干、context（如有）、全部选项、正确答案字母与选项文本。

解析要求：

1. 用标准 AP 心理学概念解释正确答案为什么符合题干情境，不要只复述选项。
2. 必须与给定答案一致；如果模型认为答案可疑，不要改答案，保留解析并在报告中标记「答案可疑」。
3. 英文解析 2–4 句，约 40–90 词；中文解析 2–4 句，保留英文术语。
4. 不出现「as an AI」「the answer key」「the book says」等字样。
5. 可以简要对比一两个强干扰项，但重点在正确答案。
6. 不使用 Markdown、标题、项目符号、代码块。
7. 不引用题目中不存在的图表细节；含图题只根据文字描述作答。

### 4. 入库与质量门禁

生成后至少检查：

- 本次生成 / 失败 / 跳过数量；
- 每套卷的 AI 解析覆盖率；
- `ai_explanation` 只出现在正确选项上；
- 错误选项的 `ai_explanation` 全为 `NULL`；
- `options.explanation` 的数量和内容没有被修改；
- 每道题的 AI 解析长度、重复率；
- 含图题清单；
- 选项图片题清单；
- `PRAGMA integrity_check;` 和 `PRAGMA foreign_key_check;`
- 中间 JSON 和报告文件存在。

如果失败题数大于 0，先看报告里的失败清单：可单独重跑失败题，或检查 API/模型返回格式。不要把失败题静默丢掉。

### 5. 重建刷题页

数据库更新后不需要重建静态页面；学生端读取 active Release。需要验证时用 SQL 或 API：

```bash
curl -s 'http://127.0.0.1:8000/api/v1/content/version?subject=psychology'
```

检查解析：

- 反馈区显示「AI 生成解析 · 仅供参考」；
- 没有原书解析的题只显示 AI 解析；
- 同时有两种解析的题，两种都显示、标签分开；
- 开始页显示「N 题有 AI 解析」；
- 缺答案题仍然显示「原书未提供答案」，且不计分。

### 6. 汇报格式

完成后按以下格式汇报：

```text
## 结果
- 范围 / 试卷：
- 模型 / 语言：
- 本次生成：N 题；失败：N 题
- 跳过：已有 AI N / 有原书解析 N / 选项图片题 N / 含图题跳过 N
- 覆盖：AI 解析 X / MCQ Y
- 含图题：N 道（建议人工复核）
- 选项图片题：N 道（未生成）

## 产物
- 生成脚本：
- 中间 JSON：
- 覆盖报告：
- 重建页面：

## 异常与待复核
- 答案可疑、失败、含图题、选项图片题……
```

### 7. 禁止事项

- 禁止把 AI 解析写进 `options.explanation`。
- 禁止改答案、编答案、编解析证据。
- 禁止把选项图片题当成普通文字题硬生成。
- 禁止静默跳过失败题。
- 禁止只报「已完成」而不给数量、覆盖率和异常。
- 禁止在没有备份的情况下写库。

---

## 最短使用方式

如果不想每次填很多参数，可以直接发：

```text
请按 05_ai_explanation.md 执行。
范围：全部试卷中还没有解析的选择题
数据库：data/content/<subject_id>/<subject_id>_exam.db
语言：英文
模式：直接生成
重建刷题页：是
```

如果只想补某套卷：

```text
请按 05_ai_explanation.md 执行。
范围：psychology-ap-2021
生成后重建 quiz_2021.html
```

如果只想先确认覆盖情况：

```text
请按 05_ai_explanation.md 执行。
范围：全部试卷
模式：先盘点
```
