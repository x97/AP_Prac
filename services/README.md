# services

> 离线服务。当前数据管道仍在项目根目录，尚未迁移。

| 目录 | 用途 |
|---|---|
| `data-pipeline/` | 教材抽取、题目解析、概念整合、权重、内容发布 |

迁移原则：

- **先把第一版内容数据做完并发布，再迁目录。**
- 数据没录完不影响 API/Web/小程序开工；它们读 release，不读 `data/content/` 里的中间产物。
- 迁移放到最后，见 `data-pipeline/README.md` 的 Phase A–D。
