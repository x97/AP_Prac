# PsyPrac 微信小程序

原生微信小程序（WXML / WXSS / JavaScript），当前是**页面与交互体验版**。

## 现在能看什么

- 极简登录页：只有一个按钮；点击后用开发短信接口自动换取 Bearer Token（API 不可达时进入本地预览）
- 记忆卡片首页：右上角下拉选择背诵范围，默认全部单元；卡片展示概念总数，来自 `/flashcards/preview`
- 翻卡学习页：术语、IPA、单元名下一行右侧「星级重要度 + 蓝色喇叭」、认识了 / 还不熟；连续模式，每次评分写 `/flashcards/{concept_id}/review`
- 我的页面：账号状态、关于与版本，以及「知识当前仍不熟悉」入口
- 仍不熟悉列表：列出最近一次评分为「还不熟」、之后没有再点「认识了」的词条

当前数据模式：

- 开发期自动登录：固定测试手机号 + 后端 dev OTP（优先使用 `/auth/sms/send` 返回的 `debug_code`），换取 Bearer Token 并存入 `ap_token`
- 学习页使用登录后的 `GET /api/v1/flashcards/next`，与 Web 连续模式一致：到期优先、每日新卡上限、Leitner 间隔
- 「我的 → 知识当前仍不熟悉」读取 `flashcard_reviews.last_rating = 'again'`，只展示当前状态，不保留历史
- 卡片首页仍用公开预览接口做范围统计与教材展示，支持 `units=methods,1,2` 多选
- 每日新卡上限是账户级的（默认 60 张），多单元共享
- API 连不上时自动显示本地示例卡片，此时评分不落库
- 暂不请求微信手机号授权；`POST /api/v1/auth/wechat/login` 已预留，配置 AppID/Secret 后可替换开发登录

## 本机运行

1. 启动 API：

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

2. 微信开发者工具导入目录：

```text
apps/miniprogram
```

3. AppID 先使用 `touristappid`，或者替换 `project.config.json` 里的 `appid` 为你自己的小程序 AppID。

4. 开发者工具 → 详情 → 本地设置：

- 勾选「不校验合法域名、web-view、TLS 版本以及 HTTPS 证书」
- 确保 `project.config.json` 的 `setting.urlCheck` 为 `false`

5. 修改 `miniprogram/config.js` 里的 API 地址和开发登录账号。默认：

```js
API_BASE_URL: "http://127.0.0.1:8000";
DEV_PHONE: "13800138000";
DEV_OTP: "246810";
```

开发登录要求后端 `SMS_PROVIDER=dev`；如果设置了 `DEV_PHONE_ALLOWLIST`，该手机号必须在白名单里。dev OTP 默认限制为同一手机号 1 次/分钟、5 次/小时；登录成功后 token 会保存 30 天，通常只需登录一次。频繁退出/登录测试时可在 `apps/api/.env` 提高 `OTP_PHONE_PER_MINUTE` / `OTP_PHONE_PER_HOUR`。

真机调试时不能再用 `127.0.0.1`，需要改成电脑局域网 IP（手机和电脑同一 Wi-Fi），或在备案后改为 HTTPS 域名。

## 已知限制

- 登录按钮使用开发期固定测试手机号；所有开发设备共用同一账号，上线前应替换为微信登录。
- 开发登录依赖后端 dev OTP，后端切到真实短信后不能直接使用。
- 部分 Android 机型的系统字体可能缺少个别 IPA 字符；后续可加 Charis SIL/Doulos SIL 子集字体。
- 真机播放音频需要使用可访问的 HTTPS 地址；本机 `127.0.0.1` 只在开发者工具里预览。

## 页面结构

```text
miniprogram/
  pages/login/       极简登录（开发期自动换取 Token）
  pages/cards/       卡片首页 + Unit 范围选择
  pages/study/       连续翻卡学习（next + review）
  pages/me/          我的 + 不熟入口
  pages/unfamiliar/  知识当前仍不熟悉列表
  custom-tab-bar/    自定义底部导航（大号字体）
  services/api.js    鉴权、卡片、评分、不熟列表
  config.js          品牌、API 地址、开发登录配置
```

## 下一步

1. 域名备案 / 微信登录配置完成后，把 `loginDev()` 替换为 `POST /api/v1/auth/wechat/login`
2. 音频域名和 API 域名备案/白名单配置
3. 如需按单元筛选「仍不熟悉」列表，再给 `/flashcards/unfamiliar` 增加 `units` 参数
