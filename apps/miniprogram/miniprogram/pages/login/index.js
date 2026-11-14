const app = getApp();
const api = require("../../services/api");

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const SUBMIT_LABELS = {
  email: "登录",
  register: "注册并登录",
  reset: "设置新密码",
};

Page({
  data: {
    mode: "email",
    email: "",
    password: "",
    code: "",
    loggingIn: false,
    sendingCode: false,
    countdown: 0,
    error: "",
    notice: "",
    devCode: "",
    offline: false,
    submitLabel: SUBMIT_LABELS.email,
  },

  onLoad() {
    if (app.globalData.loggedIn) {
      wx.switchTab({ url: "/pages/cards/index" });
    }
  },

  onUnload() {
    this.clearCountdown();
  },

  clearCountdown() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  },

  startCountdown() {
    this.clearCountdown();
    this.setData({ countdown: 60 });
    this.timer = setInterval(() => {
      const next = this.data.countdown - 1;
      if (next <= 0) {
        this.clearCountdown();
        this.setData({ countdown: 0 });
        return;
      }
      this.setData({ countdown: next });
    }, 1000);
  },

  switchMode(event) {
    const mode = event.currentTarget.dataset.mode;
    this.setData({
      mode: mode,
      password: "",
      code: "",
      devCode: "",
      error: "",
      notice: "",
      offline: false,
      submitLabel: SUBMIT_LABELS[mode] || "登录",
    });
  },

  onEmailInput(event) {
    this.setData({ email: event.detail.value, error: "" });
  },

  onPasswordInput(event) {
    this.setData({ password: event.detail.value, error: "" });
  },

  onCodeInput(event) {
    this.setData({
      code: event.detail.value.replace(/\D/g, ""),
      error: "",
    });
  },

  enterApp() {
    app.globalData.loggedIn = true;
    wx.switchTab({ url: "/pages/cards/index" });
  },

  fail(error) {
    const message = (error && error.message) || "操作失败，请重试";
    this.setData({
      loggingIn: false,
      sendingCode: false,
      error: message,
      offline: Boolean(error && error.offline),
    });
    if (error && error.offline) {
      wx.showToast({ title: message, icon: "none" });
    }
  },

  onWechatLogin() {
    if (this.data.loggingIn) return;
    this.setData({ loggingIn: true, error: "", notice: "", offline: false });
    api.wechatLogin().then(
      () => {
        this.setData({ loggingIn: false });
        this.enterApp();
      },
      (err) => this.fail(err),
    );
  },

  sendCode() {
    if (this.data.sendingCode || this.data.countdown > 0) return;
    const email = this.data.email.trim();
    if (!EMAIL_RE.test(email)) {
      this.setData({ error: "请输入有效的邮箱地址" });
      return;
    }
    const purpose = this.data.mode === "reset" ? "reset" : "register";
    this.setData({ sendingCode: true, error: "", notice: "" });
    api.sendEmailCode(email, purpose).then(
      (res) => {
        this.setData({
          sendingCode: false,
          notice: "验证码已发送，请查收邮箱",
          devCode: (res && res.debug_code) || "",
        });
        this.startCountdown();
      },
      (err) => this.fail(err),
    );
  },

  onSubmit() {
    if (this.data.loggingIn) return;
    const mode = this.data.mode;
    const email = this.data.email.trim();
    const password = this.data.password;
    const code = this.data.code;

    if (!EMAIL_RE.test(email)) {
      this.setData({ error: "请输入有效的邮箱地址" });
      return;
    }
    if (!password) {
      this.setData({ error: "请输入密码" });
      return;
    }
    if (mode !== "email" && code.length < 4) {
      this.setData({ error: "请输入验证码" });
      return;
    }

    this.setData({ loggingIn: true, error: "", notice: "", offline: false });
    let task;
    if (mode === "email") {
      task = api.emailLogin(email, password);
    } else if (mode === "register") {
      task = api.emailRegister(email, code, password);
    } else {
      task = api.resetPassword(email, code, password);
    }

    task.then(
      (res) => {
        if (mode === "reset") {
          this.setData({
            loggingIn: false,
            mode: "email",
            password: "",
            code: "",
            devCode: "",
            notice: "密码已重置，请用新密码登录",
            submitLabel: SUBMIT_LABELS.email,
          });
          return;
        }
        // Link this WeChat to the email account so the next one-click login
        // resolves here instead of creating a separate virtual account.
        api.autoBindWechat(password).then((bound) => {
          this.setData({ loggingIn: false });
          if (bound && bound.status === "bound") {
            wx.showToast({ title: "已关联当前微信", icon: "none" });
          } else if (bound && bound.status === "merged") {
            wx.showToast({ title: "已合并微信账号", icon: "none" });
          }
          this.enterApp();
        });
        return res;
      },
      (err) => this.fail(err),
    );
  },

  onOffline() {
    app.globalData.loggedIn = true;
    try {
      wx.setStorageSync("ap_logged_in", 1);
    } catch (e) {
      // Storage can be unavailable.
    }
    wx.switchTab({ url: "/pages/cards/index" });
  },
});
