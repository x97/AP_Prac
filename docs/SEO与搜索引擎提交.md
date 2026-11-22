# SEO 与搜索引擎提交

面向 Google、Bing、百度，让用户搜索 **psyprac** / **PsyPrac** 时能找到
`https://www.psyprac.com/`。代码侧的 SEO 已完成，本文档记录部署与各平台提交步骤。

## 一、代码侧已完成

Web 应用（`apps/web`）：

- `src/app/robots.ts` → `/robots.txt`
  - 允许抓取首页；排除需要登录的应用页（`/dashboard`、`/practice`、`/exams` 等）和 `/api/`
  - 声明 `Host` 与 `Sitemap`
- `src/app/sitemap.ts` → `/sitemap.xml`
  - 首页（含 logo 图片 sitemap）
- `src/app/layout.tsx`
  - 品牌标题模板、中文 description、keywords
  - `robots: index, follow`、Googlebot 大图/长摘要
  - Open Graph / Twitter Card（logo 作为分享图）
  - JSON-LD：`WebSite` + `EducationalOrganization`（含 `alternateName: psyprac`，帮助品牌实体识别）
- `src/app/page.tsx`
  - 首页绝对标题、`canonical: https://www.psyprac.com/`
- `src/app/login/layout.tsx`
  - 登录页 `noindex, follow`（薄内容不进索引），canonical 指向 `/login`
- `public/a3a0ba739046ea2ca6bcb318cfa66ca4.txt`
  - IndexNow 密钥文件（Bing / Yandex / Seznam / Naver 用）
- `scripts/ping_indexnow.py`
  - 部署后向 IndexNow 提交 URL

> Google 不使用 IndexNow；Google 侧通过 Search Console 提交 sitemap。
> 百度也不使用 IndexNow；百度通过搜索资源平台提交 sitemap 或主动推送。

## 二、部署到生产

SEO 文件是构建产物，必须重新构建 `web` 镜像才会生效。

```bash
cd /path/to/AP_psych
git add apps/web/src/app/robots.ts apps/web/src/app/sitemap.ts \
  apps/web/src/app/layout.tsx apps/web/src/app/page.tsx \
  apps/web/src/app/login/layout.tsx \
  apps/web/public/a3a0ba739046ea2ca6bcb318cfa66ca4.txt \
  scripts/ping_indexnow.py scripts/push_baidu.py docs/SEO与搜索引擎提交.md
git commit -m "Add SEO metadata, robots.txt, sitemap, and IndexNow key"
SERVER=user@host ./infra/deploy/sync_code.sh
ssh user@host "cd /srv/ap-psych/infra/compose && docker compose up -d --build web"
```

部署后自检：

```bash
curl -fsS https://www.psyprac.com/robots.txt
curl -fsS https://www.psyprac.com/sitemap.xml
curl -fsS https://www.psyprac.com/a3a0ba739046ea2ca6bcb318cfa66ca4.txt
curl -fsS https://www.psyprac.com/ | grep -E 'canonical|application/ld\+json|og:title'
curl -fsS https://www.psyprac.com/login | grep 'noindex'
```

确认线上 `robots.txt` 不再返回 404（之前未配置，搜索引擎拿到的是一张 HTML 404 页）。

## 三、提交到搜索引擎

当前状态（2026-11-23）：

- [x] `robots.txt` / `sitemap.xml` / IndexNow 密钥文件已上线
- [x] IndexNow 已提交首页（HTTP 202）
- [ ] Google Search Console 验证并提交 sitemap
- [ ] Bing Webmaster Tools 验证（可选，IndexNow 已生效）
- [ ] 百度搜索资源平台验证并提交 sitemap

三个平台都需要账号。若还没有账号：Google 用 Google 账号登录
Search Console 即开通；Bing 用 Microsoft 账号；百度搜索资源平台用百度账号。
**服务器在阿里云深圳（中国大陆），百度要求域名完成 ICP 备案**；如果还没备案，
需要先走阿里云备案流程（2–4 周），否则百度收录会受限。备案号建议展示在页脚
（法规要求，也有助于百度识别站点）。

以下操作需要站点所有者登录各平台控制台。验证文件统一放进
`apps/web/public/`，重新构建 `web` 即会在域名根目录提供。

### 1. Google Search Console

1. 打开 <https://search.google.com/search-console>，添加「网址前缀」资源：
   `https://www.psyprac.com/`
2. 验证方式任选其一：
   - **HTML 文件**（最简单）：下载 `googleXXXXXXXX.html`，放到
     `apps/web/public/`，部署后回控制台点「验证」。
   - **DNS TXT**：在域名 DNS 添加 Google 提供的 TXT 记录（覆盖更广，推荐长期使用）。
3. 进入「抓取工具 → Sitemap」，提交 `sitemap.xml`
   （即 `https://www.psyprac.com/sitemap.xml`）。
4. 用「网址检查」输入首页，点「请求编入索引」。

Google 通常几天内收录新站；品牌词（psyprac）排名会随着外链和访问量提升。

### 2. Bing Webmaster Tools

1. 打开 <https://www.bing.com/webmasters>，添加 `https://www.psyprac.com/`。
2. 验证方式：
   - 支持直接从 Google Search Console 导入站点（最省事）。
   - 或下载 `BingSiteAuth.xml` 放入 `apps/web/public/` 后部署。
3. 提交 Sitemap：`https://www.psyprac.com/sitemap.xml`。
4. 启用 **IndexNow** 主动推送（见下一节），Bing 收录会快很多。

### 3. 百度搜索资源平台

前提：服务器在中国大陆（当前为阿里云深圳），域名需完成 **ICP 备案**；
未备案时百度收录会受限。备案号建议展示在页脚。

1. 打开 <https://ziyuan.baidu.com>，添加站点 `https://www.psyprac.com/`。
2. 验证方式：
   - 下载 `baidu_verify_codeva-XXXXXXXX.html`，放到 `apps/web/public/` 后部署；
   - 或在 `layout.tsx` 的 metadata 里加 `verification.other`（需改代码，文件方式更简单）。
3. 「资源提交 → 普通收录 → sitemap」提交
   `https://www.psyprac.com/sitemap.xml`。
4. 可选：在「普通收录 → API 提交」获取 token，做主动推送；新站建议同时提交 sitemap：

   ```bash
   BAIDU_PUSH_TOKEN=你的token python scripts/push_baidu.py
   ```

   返回 JSON（`success` 为成功条数）即提交成功。
5. 百度对新站收录较慢（通常 1–4 周），保持页面可访问、有外链即可。

### 4. IndexNow（Bing / Yandex 等）

部署并确认密钥文件可访问后执行：

```bash
python scripts/ping_indexnow.py
```

成功返回 `HTTP 200`。以后有新的公开页面时，把 URL 作为参数追加：

```bash
python scripts/ping_indexnow.py https://www.psyprac.com/ https://www.psyprac.com/about
```

> 密钥文件 `public/a3a0ba739046ea2ca6bcb318cfa66ca4.txt` 必须与脚本里的
> `KEY` 一致。若轮换密钥，三处一起改：文件名、文件内容、脚本常量。

## 四、注意事项

- **重复内容**：`miniapp.psyprac.com` 目前代理同一个 Web 应用。建议在生产
  Nginx 给该 host 加 `X-Robots-Tag: noindex, nofollow`（`manager.psyprac.com`
  已有），避免与 `www` 争排名。`infra/deploy/nginx.conf` 是服务器手工维护文件，
  同步脚本不会覆盖，需在服务器上自行修改并 `docker compose restart nginx`。
- **API 子域**：`api.psyprac.com` 的 `/docs` 等页面也可加 `X-Robots-Tag: noindex`。
- **语言与 SSR**：当前服务端默认输出英文 UI（客户端再按浏览器语言切换），
  页面 `<html lang="en">`。品牌词 psyprac 是中英混合查询，影响不大；如果后续要
  主攻中文搜索词（如「AP 心理学 练习」），需要把 SSR 默认语言改为中文，这属于
  产品决策，建议单独评估。
- **外链**：搜索引擎收录新站主要靠 sitemap + 外部链接。可以在小红书、微信公众号、
  Telegram 频道、学校社群等发布带 `https://www.psyprac.com` 的内容，加速品牌词收录。
- **维护**：新增公开页面时加入 `sitemap.ts`；首页内容有大改后重新跑一次
  IndexNow，并在 Search Console / 百度后台重新提交 sitemap（内容不变无需重复提交）。

## 五、验证收录

```text
Google:  site:www.psyprac.com
Bing:    site:www.psyprac.com
百度:    site:www.psyprac.com
品牌词:  psyprac（三个引擎各查一次）
```

收录生效时间：Google 几天到两周；Bing 借助 IndexNow 通常更快；百度 1–4 周。
提交后不需要每天重复操作，保持站点可访问即可。
