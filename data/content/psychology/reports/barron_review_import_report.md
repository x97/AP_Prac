# Barron's AP Psychology 2027 章末 Review Questions 入库报告

- 导入时间：2026-10-27T00:37:29
- 来源：`assets/psychology/books/AP Psychology Premium, 2027 - Allyson J. Weseley & Robert McEntarffer.pdf`
- 结构：15 个章节，每章 1 份 `unit_practice` 试卷

| 项目 | 数量 |
|---|---:|
| 章节试卷 | 15 |
| 题目 | 160 |
| 有答案/解析 | 156 |
| 选项 | 640 |
| 题图（裁切） | 45 |
| 唯一题图 | 21 |

## 校验

- `foreign_key_check`：通过
- 答案与解析来自本书 Answer Explanations；正确选项 `options.explanation` 同步写入
- 原书未给解析的题：[(9, 14), (9, 15), (10, 4), (10, 5)]（这些题 `correct_answer` 也为 NULL）
- 题图按题目/题组从 PDF 页面裁切，只保留对应图表/表格，不再使用整页截图
- 同一图表/表格可被同组多道题引用；`assets.bbox` 保存相对来源页面的裁切范围
- 选项本身都有文本；图片只用于图表、表格或示意图
