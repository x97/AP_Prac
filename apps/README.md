# apps

| 目录 | 技术 | 职责 |
|---|---|---|
| `api/` | FastAPI | 数据库访问层；学生内容只读 release + 用户库读写 + Admin API |
| `web/` | Next.js + TypeScript | 学生 Web 前端 |
| `admin/` | Next.js + TypeScript | 独立管理后台；内容编辑、学生进度、Release 发布 |
| `miniprogram/` | 原生微信小程序 | 小程序前端 |

边界：

- `web/`、`admin/` 和 `miniprogram/` 只能通过 API 访问数据。
- 学生端读取 `data/releases/current` 的不可变 release。
- Admin 编辑 `ap_exam.db` / `ap_knowledge.db` 内容源，通过发布流程生成新 release。
- 共享类型目前分别维护；后续可抽到 `packages/api-contracts/`。
