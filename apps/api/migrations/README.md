# migrations

P0 的 App DB 用 `AUTO_CREATE_TABLES=true` + SQLAlchemy `create_all` 建表，方便本地和生产首启。

后续改 schema 前必须补 Alembic：

```bash
cd apps/api
../../.venv/bin/alembic init migrations   # 只在还没有时执行一次
# 配置 env.py 读取 app.core.db.Base 和 DATABASE_URL
../../.venv/bin/alembic revision --autogenerate -m "add ..."
../../.venv/bin/alembic upgrade head
```

生产把 `AUTO_CREATE_TABLES` 设为 `false`，用迁移代替自动建表。
