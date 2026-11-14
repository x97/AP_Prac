# apps/web

Next.js 16 App Router + TypeScript + Tailwind。

## 本地运行

```bash
cd apps/web
npm install
npm run dev
```

`next.config.js` 把 `/api/*` 和 `/assets/*` rewrite 到 FastAPI（localhost:8000）。
开发验证码提示由 `.env.local` 的 `NEXT_PUBLIC_DEV_OTP_CODE` 控制，不要带到生产。

## 页面

```text
/login              手机验证码登录
/                   首页 / 进度
/practice           Unit 列表
/practice/[id]      Topic 列表
/practice/session/[id]  练习答题
/exams              真题 / 模拟列表
/exams/[id]         考前说明 + 模式选择
/.../attempt/[id]   考试 runner（MCQ / FRQ / 全卷）
/.../review         MCQ 复盘 + FRQ rubric 自评
/wrong /bookmarks /notes /me
```

## 校验

```bash
npm run typecheck
npm run build
```
