# packages/api-contracts

> 规划目录；当前不写代码。

计划内容：

```text
openapi.yaml          # API 契约（source of truth）
generated/ts/         # 生成的 TypeScript client
README.md
```

流程：

1. FastAPI 生成/导出 OpenAPI。
2. 本目录提交 OpenAPI 快照。
3. CI 生成 TS client 到 `generated/ts/`。
4. Web / 小程序引用生成 client，不手写重复类型。
