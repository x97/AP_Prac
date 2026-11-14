# packages

> 跨应用共享包。当前只规划目录，不写代码。

| 包 | 用途 |
|---|---|
| `api-contracts/` | OpenAPI 契约 + 生成的 TypeScript client |
| `quiz-core/` | 评分、答题状态、进度计算（Web / 小程序共享） |
| `design-tokens/` | 颜色、字号、间距等设计 token |

规则：

- `api-contracts` 是 Web/小程序/API 的共同契约。
- `quiz-core` 只放纯逻辑，不依赖 DOM 或小程序 API。
- 不要在 Web/小程序各写一套评分逻辑。
