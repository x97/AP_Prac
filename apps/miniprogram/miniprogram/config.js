function resolveApiBaseUrl() {
  try {
    const info = wx.getAccountInfoSync();
    const version = info && info.miniProgram && info.miniProgram.envVersion;
    // 开发者工具里连本机 API；体验版/正式版连生产域名。
    if (version === "develop") {
      return "http://127.0.0.1:8000";
    }
  } catch (e) {
    // getAccountInfoSync may be unavailable outside the mini-program runtime.
  }
  return "https://api.psyprac.com";
}

module.exports = {
  BRAND_NAME: "PsyPrac",
  BRAND_DOMAIN: "psyprac.com",
  MINIAPP_DOMAIN: "miniapp.psyprac.com",
  // 生产：微信公众平台 → 开发管理 → 服务器域名，把
  // https://api.psyprac.com 加入 request 合法域名；音频/图片若通过
  // wx.downloadFile 加载，也加入 downloadFile 合法域名。
  // 本地开发：微信开发者工具里关闭「不校验合法域名」。
  API_BASE_URL: resolveApiBaseUrl(),
  PREVIEW_LIMIT: 50,
  // 登录：微信一键登录 POST /api/v1/auth/wechat/login。
  // 本地没有配置微信 appid 时，可用邮箱注册/登录（后端 EMAIL_PROVIDER=dev
  // 会返回 debug_code）。
  UNFAMILIAR_PAGE_SIZE: 30,
};
