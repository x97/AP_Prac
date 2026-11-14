# infra

```text
compose/   # docker-compose.yml + .env.example
deploy/    # nginx.conf / nginx-https.conf.example / backup.sh / deploy_release.sh
docker/    # 预留
```

P0 部署形态：

- `api`：FastAPI 容器，读 `/srv/ap-psych/releases/active`（只读）+ Postgres。
- `worker`：`app.jobs.sweep_expired`，每分钟自动交卷。
- `web`：Next.js standalone。
- `nginx`：同源 `/api/`、`/assets/`（代理到 API 校验签名）、`/`。
- 内容 release 由 `_tools/build_merged_release.py` 生成，rsync 到服务器后切 `active` 符号链接（同步 `current` 兼容别名）。

详细步骤见 `docs/部署手册.md`。
