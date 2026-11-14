# 2026 AP Psychology PDF 解析报告

## 结构地图

- 源文件：`assets/psychology/papers/2026/2026 AP心理学.pdf`
- PDF 页数：49；有文本层；A4；双栏题目区 + 单栏直接题混合。
- Section I（MCQ）：PDF 第 1–29 页，共 75 题；每题 4 个选项 A–D；答案字母直接印在题号行。
- Section II（FRQ）：PDF 第 30–49 页，共 2 题；Q1 为 AAQ 六部分（A–F），Q2 为 EBQ 三部分（A–C）。
- Q1 的源材料在每个子问页面重复出现；Q2 的 Sources 1–3 不在本 PDF 中。
- 图表/表格题：Q9、Q18、Q31、Q46、Q53、Q60、Q61、Q62、Q66、Q72、Q73、Q74。

## 数量与完整性

| 项目 | 结果 |
|---|---:|
| MCQ | 75 |
| FRQ | 2 |
| MCQ 选项数分布 | {4: 75} |
| 答案分布 | {'A': 18, 'B': 18, 'C': 18, 'D': 21} |
| 有解析的选项 | 0 |
| 题图/表格引用 | 16 |
| 唯一裁切文件 | 12 |
| FRQ rubric | 0 |

## 入库状态

- `import_ready = false`
- `mcq_import_ready = true`
- `frq_import_ready = false`
- 阻塞项：Q2 Sources 1-3 are missing from the PDF.
- 阻塞项：FRQ scoring guidelines and rubric parts are missing from the PDF.

## 跨页题

- Q9：PDF p3–p4
- Q46：PDF p17–p18

## 图表/表格裁切

- Q9：figure, figure；`assets/psychology/images/ap2026/q09_figure_1_first_test.png`
- Q18：figure；`assets/psychology/images/ap2026/q18_attitude_before_after_mural.png`
- Q31：figure；`assets/psychology/images/ap2026/q31_hypnosis_anxiety_scatterplot.png`
- Q46：option A, option B, option C, option D；`assets/psychology/images/ap2026/q46_option_a.png`
- Q53：table；`assets/psychology/images/ap2026/q53_group_demographics_and_completion_time.png`
- Q60：table；`assets/psychology/images/ap2026/q60_62_withdrawal_symptom_table.png`
- Q61：table；`assets/psychology/images/ap2026/q60_62_withdrawal_symptom_table.png`
- Q62：table；`assets/psychology/images/ap2026/q60_62_withdrawal_symptom_table.png`
- Q66：figure；`assets/psychology/images/ap2026/q66_mental_health_curves.png`
- Q72：figure；`assets/psychology/images/ap2026/q72_74_offers_to_help_chart.png`
- Q73：figure；`assets/psychology/images/ap2026/q72_74_offers_to_help_chart.png`
- Q74：figure；`assets/psychology/images/ap2026/q72_74_offers_to_help_chart.png`

## FRQ

### Q1 (AAQ)

- 页码：p30–p47
- 子问：6 个
- 参考答案：已提取 sample response
- 评分标准：源 PDF 未提供，`frq_rubrics` 为空

### Q2 (EBQ)

- 页码：p48–p49
- 子问：3 个
- 参考答案：已提取 sample response
- 评分标准：源 PDF 未提供，`frq_rubrics` 为空
- **缺源材料：Sources 1–3 不在本 PDF 中，Q2 目前不能独立作答。**

## 异常与待复核

- The PDF prints answer letters (正确答案) but no MCQ explanations.
- The PDF prints sample FRQ responses but no scoring guidelines or rubric points.
- Q2's Sources 1-3 are not included in this PDF.
- The answer key is treated as source-provided, not independently verified as official.
- Q1 source tables 1-4 were reconstructed as text; values were visually checked.
- Q9, Q18, Q31, Q46, Q53, Q60-Q62, Q66, and Q72-Q74 have cropped figure/table assets.
- Figure descriptions are stored in `assets.description` and displayed below each image in the exam UI.
- Q46 options are image-only; option text is a placeholder pointing to the image.

## 产物

- JSON：`data/content/psychology/extraction/psychology-ap-2026.json`
- 裁图目录：`assets/psychology/images/ap2026`
- 解析脚本：`_tools/parse_ap_psych_2026.py`

## 入库记录（2026-11-01）

- MCQ 75 题已写入 `data/content/psychology/psychology_exam.db`，paper_id = `psychology-ap-2026`。
- Q9 的两张图已拆成两个 asset，各自带图案说明。
- 已构建并激活 Release `content-20261101-06`（37 papers / 2,951 questions）。
- FRQ 未入库；Q2 源材料仍缺失。
- MCQ AI 解析 75/75 已补全；核心概念关联 75/75。
- 当前合集：`data/content/psychology/reports/2026_ai_and_concepts_summary.md`。
