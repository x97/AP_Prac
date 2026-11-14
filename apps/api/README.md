# apps/api

FastAPI + SQLAlchemy + SQLite（本地 App DB）/ Postgres（生产）。

## 本地运行

```bash
# 仓库根目录
python3 -m venv .venv
.venv/bin/pip install -r apps/api/requirements.txt

cd apps/api
PYTHONPATH=. ../../.venv/bin/uvicorn app.main:app --reload --port 8000
```

默认读取 `data/releases/` 下最新的 release；App DB 在 `data/app/app.db`。
登录使用邮箱 + 密码（`EMAIL_PROVIDER=dev` 时开发验证码为 `246810`），微信小程序走 `/auth/wechat/login` 一键登录。
已有数据库先运行：`python scripts/migrate_auth_email.py`。

## 目录

```text
app/core/       config / db / security / errors
app/content/    release 只读访问（exam.db + knowledge.db）
app/users/      App DB models
app/api/v1/     auth / content / practice / attempts / me
app/services/   practice_engine / exam_engine / progress / email / account_merge
app/jobs/       sweep_expired
tests/          pytest
```

## 测试

```bash
cd apps/api
../../.venv/bin/python -m pytest -q
../../.venv/bin/python -m ruff check app tests
```
