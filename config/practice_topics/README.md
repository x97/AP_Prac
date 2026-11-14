# config/practice_topics

`psychology.json` 是“Unit → Topic → 题目”的人工配置 source of truth。

- 5 个 Unit，35 个 CED topic（Unit 1 6 / Unit 2 8 / Unit 3 9 / Unit 4 7 / Unit 5 5）。
- 每个 Unit 额外一个“研究方法”topic（`kind=methods`），承接 `ap_unit=0/EM` 的方法/统计概念。
- `build_practice_topics.py` 会为无匹配题生成 `kind=other` 的“综合/其他”topic，只有非空时才出现在 API。
- `match_topics` 对 `concept_clusters.topic` 做 exact / startswith 匹配；`match_keywords` 对 canonical name 做包含匹配。
- 优先级：core > supporting > confusable；同优先级下 topic 匹配分 > confidence > concept weight。
- 修改后跑：

```bash
python3 _tools/build_exam_configs.py --subject psychology \
  --exam-db data/content/psychology/psychology_exam.db
python3 _tools/build_practice_topics.py --subject psychology \
  --exam-db data/content/psychology/psychology_exam.db \
  --knowledge-db data/content/psychology/psychology_knowledge.db
python3 _tools/build_merged_release.py --release-id content-YYYYMMDD-01
```

不要直接改合并 Release；按科目修改 `data/content/<subject>/<subject>_exam.db`，再构建新的合并 Release。
