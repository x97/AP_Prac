# Barron's Review Questions — 图片素材

- `fig-*.png`：单元练习页面实际使用的题图/表格裁切，来自原书页面，一张图可被同一题组多道题引用。
- `page*.png`：整页 PDF 渲染源图，仅用于裁切和复核，不再被 `ap_exam.db.assets` 引用。

重新生成题图并入库：

```bash
python3 _tools/import_barron_review_questions.py
python3 _tools/build_unit_practice.py
```
