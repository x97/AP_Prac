# AP 心理学官方主观题（2023–2025）

从 College Board AP Central 官方页面下载的 Free-Response Questions（主观题）与 Scoring Guidelines（评分标准）。

| 项目 | 内容 |
|---|---|
| 来源页面 | https://apcentral.collegeboard.org/courses/ap-psychology/exam/past-exam-questions |
| 下载日期 | 2026-10-24 |
| 文件数 | 12 个 PDF（3 年 × 2 套 × 题目+评分标准） |

---

## 文件清单

| 年份 | 套 | 题目文件 | 页数 | 评分标准 | 页数 | 主题 |
|---|---|---|---|---|---|---|
| 2023 | Set 1 | `2023/FRQ-Set-1.pdf` | 4 | `2023/Scoring-Guidelines-Set-1.pdf` | 9 | Steve 为四个孩子做早餐 |
| 2023 | Set 2 | `2023/FRQ-Set-2.pdf` | 4 | `2023/Scoring-Guidelines-Set-2.pdf` | 10 | Jordan 转学适应新学校 |
| 2024 | Set 1 | `2024/FRQ-Set-1.pdf` | 4 | `2024/Scoring-Guidelines-Set-1.pdf` | 8 | Gavin 参观科学博物馆 |
| 2024 | Set 2 | `2024/FRQ-Set-2.pdf` | 4 | `2024/Scoring-Guidelines-Set-2.pdf` | 8 | Claire 的篮球队进入决赛 |
| 2025 | Set 1 | `2025/FRQ-Set-1.pdf` | 12 | `2025/Scoring-Guidelines-Set-1.pdf` | 12 | AAQ：错误信息与记忆；EBQ：他人在场是否提升表现 |
| 2025 | Set 2 | `2025/FRQ-Set-2.pdf` | 10 | `2025/Scoring-Guidelines-Set-2.pdf` | 14 | AAQ：犬类研究；EBQ：助人行为 |

2025 年起官方 FRQ 采用 AAQ（Article Analysis Question）+ EBQ（Evidence-Based Question）格式，题目文件包含完整研究摘要与三份 Source，所以页数明显多于 2023/2024（每年 2 套，每套 2 题）。

---

## 与其他目录的关系

- **2025 的 4 个文件与 `assets/psychology/papers/2025/` 下已有文件完全相同**（MD5 一致）：
  - `25--FRQ-Set-1.pdf` = `2025/FRQ-Set-1.pdf`
  - `25--FRQ-Set-2.pdf` = `2025/FRQ-Set-2.pdf`
  - `ap25-sg-psychology-set-1/2.pdf` = `2025/Scoring-Guidelines-Set-1/2.pdf`
  这些已经在数据库 `psychology-ap-2025` 中解析入库。
- **2023 的官方两套与 `assets/psychology/papers/2023/` 的整卷不同**：整卷（100 道选择题 + 2 道主观题）里的主观题是 Bette（刨冰口味）与 Ember（开学第一天），属于国际卷；官方这里下载的是美国本土 Set 1（Steve 早餐）与 Set 2（Jordan 转学）。
- **2024 尚未入库**：目前数据库中没有 2024 年试卷。

---

## 使用说明

- 文件为 College Board 公开发布的 FRQ 与评分标准，版权归 College Board 所有，仅供个人备考与教学参考，请勿再分发或商用。
- 若要把 2023/2024 的官方两套也导入数据库，可按现有 `paper_type='real_exam'` 的格式建 paper（每套 2 道 FRQ + 评分标准），我可以继续处理。

## 重新下载

页面地址固定，文件 URL 规则为：

```
https://apcentral.collegeboard.org/media/pdf/ap{YY}-frq-psychology-set-{1|2}.pdf
https://apcentral.collegeboard.org/media/pdf/ap{YY}-sg-psychology-set-{1|2}.pdf
```

例如 2024 Set 1 题目：

```
https://apcentral.collegeboard.org/media/pdf/ap24-frq-psychology-set-1.pdf
```

注意 AP Central 只保留最近三年的已释出材料，更早年份会从页面撤下。
