# AI 答案解析覆盖报告

- 生成时间：2026-10-27T11:31:53+00:00
- 模型：`deepseek-flash[1m]`
- 语言：`en`
- 当前 AI 覆盖：1492 / 2848 道 MCQ（52.4%）；缺任何解析 0 道
- 本次运行生成：0 题；失败：0 题；跳过已有 AI 1492 题、原书解析 1356 题

> AI 解析由模型根据题干、选项和**已核对的正确答案**生成，不是官方或原书解析，不能替代 `options.explanation`。刷题页会把两者分开显示，并标注“AI 生成解析”。
> “其中含图题”表示题目/选项带图表素材；当前生成只发送文字，图表本身没有送给模型，这部分解析建议人工复核。

| 试卷 | MCQ | 原书解析 | AI 解析 | 其中含图题 | 缺任何解析 |
|---|---:|---:|---:|---:|---:|
| `psychology-ap-2018` | 100 | 0 | 100 | 10 | 0 |
| `psychology-ap-2019` | 100 | 0 | 100 | 8 | 0 |
| `psychology-ap-2021` | 100 | 0 | 100 | 9 | 0 |
| `psychology-ap-2022` | 100 | 0 | 100 | 9 | 0 |
| `psychology-ap-2023` | 100 | 0 | 100 | 11 | 0 |
| `psychology-ap-2024` | 100 | 0 | 100 | 11 | 0 |
| `psychology-ap-2025` | 75 | 0 | 75 | 13 | 0 |
| `psychology-barrons-2027-ch10-review` | 3 | 3 | 0 | 0 | 0 |
| `psychology-barrons-2027-ch11-review` | 16 | 16 | 0 | 0 | 0 |
| `psychology-barrons-2027-ch12-review` | 14 | 14 | 0 | 0 | 0 |
| `psychology-barrons-2027-ch13-review` | 14 | 14 | 0 | 0 | 0 |
| `psychology-barrons-2027-ch14-review` | 8 | 8 | 0 | 0 | 0 |
| `psychology-barrons-2027-ch15-review` | 9 | 9 | 0 | 0 | 0 |
| `psychology-barrons-2027-ch16-review` | 11 | 11 | 0 | 0 | 0 |
| `psychology-barrons-2027-ch17-review` | 13 | 13 | 0 | 0 | 0 |
| `psychology-barrons-2027-ch18-review` | 7 | 7 | 0 | 0 | 0 |
| `psychology-barrons-2027-ch4-review` | 17 | 17 | 0 | 0 | 0 |
| `psychology-barrons-2027-ch5-review` | 7 | 7 | 0 | 0 | 0 |
| `psychology-barrons-2027-ch6-review` | 6 | 6 | 0 | 0 | 0 |
| `psychology-barrons-2027-ch7-review` | 9 | 9 | 0 | 0 | 0 |
| `psychology-barrons-2027-ch8-review` | 9 | 9 | 0 | 0 | 0 |
| `psychology-barrons-2027-ch9-review` | 13 | 13 | 0 | 0 | 0 |
| `psychology-barrons-2027-pt1` | 75 | 75 | 0 | 0 | 0 |
| `psychology-barrons-2027-pt2` | 75 | 75 | 0 | 0 | 0 |
| `psychology-barrons-2027-pt3` | 75 | 75 | 0 | 0 | 0 |
| `psychology-cb-2026-mock-1` | 75 | 75 | 0 | 0 | 0 |
| `psychology-cb-2026-u1` | 315 | 165 | 150 | 3 | 0 |
| `psychology-cb-2026-u2` | 349 | 191 | 158 | 14 | 0 |
| `psychology-cb-2026-u3` | 354 | 183 | 171 | 3 | 0 |
| `psychology-cb-2026-u4` | 378 | 194 | 184 | 10 | 0 |
| `psychology-cb-2026-u5` | 321 | 167 | 154 | 5 | 0 |
| **合计** | **2848** | **1356** | **1492** | **106** | **0** |

## 复跑命令

```bash
# 单套卷 / 全部未生成 AI 解析的题
python3 _tools/generate_ai_explanations.py --paper <paper_id>
python3 _tools/generate_ai_explanations.py --all --skip-book-explained

# 重新生成刷题页（单套卷）
```
