# AP Psychology Admin

独立 Next.js 管理后台，默认端口 `3001`。

## 启动

先启动 API：

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

再启动 Admin：

```bash
cd apps/admin
npm install
npm run dev
# http://localhost:3001/login
```

生产构建：

```bash
npm run build
npm run start
```

## 创建管理员

管理员账号和学生手机号账号完全分离。

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/python -m app.cli create-admin
```

会提示输入 username、email、password。也可以使用参数：

```bash
PYTHONPATH=. ../../.venv/bin/python -m app.cli create-admin \
  --username admin \
  --email admin@example.com \
  --role super_admin
```

其他命令：

```bash
python -m app.cli list-admins
python -m app.cli reset-password --username admin
python -m app.cli disable-admin --username admin
```

## 内容发布

- Phase 1 Admin 默认只读；内容写接口由 `ADMIN_CONTENT_WRITE_ENABLED=false` 关闭。
- 内容源是 `data/content/<subject>/<subject>_exam.db` / `<subject>_knowledge.db`。
- 学生端只读取合并后的 `data/releases/active`。
- “发布”页可构建新的合并 release，并切换 `data/releases/active`（同步 `current` 兼容别名）。
- API 下一次请求检测到 active 变化后重新加载 `ContentStore`。

生产环境将 API 的 `CONTENT_DIR` 指向 `data/releases/active`。

## 激活码

`super_admin` 可在“激活码”页面：

- 选择科目或全部启用科目；
- 选择 1 年 / 6 个月 / 3 个月 / 1 个月或指定到期日；
- 批量生成 1–500 个激活码；
- 自动下载 TXT，也可在批次历史中重新下载；
- 查看未使用/已使用/已作废明细；
- 作废单个未使用码或整批未使用码。

学生端在“我的 → 课程权限”或锁定 Unit/试卷卡片处兑换。详见 `docs/激活码与课程权限.md`。
