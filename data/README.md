# data

```text
content/    # 预留：本地内容库（当前 release 在 data/releases）
app/        # 本地用户库 app.db（gitignore）
releases/   # content release 产物（gitignore）
```

- `data/releases/<id>/` 由 `_tools/build_content_release.py` 生成，包含 `exam.db`、`knowledge.db`、`assets/`、`assets-manifest.json`、`release.json`、`exclusions.json`。
- API 默认读取最新 release；生产通过 `/srv/ap-psych/releases/current` 符号链接。
- `data/app/app.db` 只用于本地开发；生产用 Postgres。
