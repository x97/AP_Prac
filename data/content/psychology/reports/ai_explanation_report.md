# AI 答案解析覆盖报告

- 生成时间：2026-11-02T05:55:57+00:00
- 模型：`deepseek-flash[1m]`
- 语言：`en`
- 当前 AI 覆盖：198 / 200 道 MCQ（99.0%）；缺任何解析 2 道
- 本次运行生成：192 题；失败：0 题；跳过已有 AI 6 题、原书解析 0 题

> AI 解析由模型根据题干、选项和**已核对的正确答案**生成，不是官方或原书解析，不能替代 `options.explanation`。刷题页会把两者分开显示，并标注“AI 生成解析”。
> “其中含图题”表示题目/选项带图表素材；当前生成只发送文字，图表本身没有送给模型，这部分解析建议人工复核。

| 试卷 | MCQ | 原书解析 | AI 解析 | 其中含图题 | 缺任何解析 |
|---|---:|---:|---:|---:|---:|
| `psychology-ap-2016` | 100 | 0 | 100 | 5 | 0 |
| `psychology-ap-2017` | 100 | 0 | 98 | 5 | 2 |
| **合计** | **200** | **0** | **198** | **10** | **2** |

## 未生成：选项本身是图片

以下题目的选项是图片，文字里没有选项内容，未调用模型，建议人工补：

- `psychology-ap-2017-mcq-043`
- `psychology-ap-2017-mcq-092`

## 复跑命令

```bash
# 单套卷 / 全部未生成 AI 解析的题
python3 _tools/generate_ai_explanations.py --subject <subject_id> --paper <paper_id>
python3 _tools/generate_ai_explanations.py --subject <subject_id> --all --skip-book-explained
```

---

> 后续人工复核：`psychology-ap-2017-mcq-067` 的含图解析已按图修正（均值 70）。最终统计与产物见 `data/content/psychology/reports/question_analysis/psychology-ap-2016-2017_ai_concepts_final.md`。
