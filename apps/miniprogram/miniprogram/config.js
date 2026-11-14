module.exports = {
  BRAND_NAME: "PsyPrac",
  BRAND_DOMAIN: "psyprac.com",
  // 本机开发：微信开发者工具里关闭「不校验合法域名」。
  // 备案后上线改成 HTTPS API 域名，例如 https://psyprac.com
  API_BASE_URL: "http://127.0.0.1:8000",
  PREVIEW_LIMIT: 50,
  // 登录：微信一键登录 POST /api/v1/auth/wechat/login。
  // 本地没有配置微信 appid 时，可用邮箱注册/登录（后端 EMAIL_PROVIDER=dev
  // 会返回 debug_code）。
  UNFAMILIAR_PAGE_SIZE: 30,
};
