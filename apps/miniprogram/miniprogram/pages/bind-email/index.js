const app = getApp();
const api = require("../../services/api");

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

Page({
  data: {
    email: "",
    password: "",
    code: "",
    emailLabel: "未绑定",
    hasEmail: false,
    sendingCode: false,
    countdown: 0,
    submitting: false,
    error: "",
    notice: "",
    devCode: "",
  },

  onShow() {
    this.refreshUser();
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

  refreshUser() {
    const stored = app.globalData.user;
    if (stored) this.applyUser(stored);
    if (!api.hasToken()) return;
    api.getMe().then(
      (res) => this.applyUser((res && res.user) || null),
      (err) => {
        if (err && err.authRequired) {
          api.clearSession();
          wx.reLaunch({ url: "/pages/login/index" });
        }
      },
    );
  },

  applyUser(user) {
    if (!user) return;
    this.setData({
      emailLabel: user.email_masked || "未绑定",
      hasEmail: Boolean(user.email),
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

  sendCode() {
    if (this.data.sendingCode || this.data.countdown > 0) return;
    const email = this.data.email.trim();
    if (!EMAIL_RE.test(email)) {
      this.setData({ error: "请输入有效的邮箱地址" });
      return;
    }
    this.setData({ sendingCode: true, error: "", notice: "" });
    api.sendBindEmailCode(email).then(
      (res) => {
        this.setData({
          sendingCode: false,
          notice: "验证码已发送，请查收邮箱",
          devCode: (res && res.debug_code) || "",
        });
        this.startCountdown();
      },
      (err) => {
        this.setData({
          sendingCode: false,
          error: (err && err.message) || "验证码发送失败",
        });
      },
    );
  },

  submit() {
    if (this.data.submitting) return;
    const email = this.data.email.trim();
    const password = this.data.password;
    const code = this.data.code;
    if (!EMAIL_RE.test(email)) {
      this.setData({ error: "请输入有效的邮箱地址" });
      return;
    }
    if (code.length < 4) {
      this.setData({ error: "请输入验证码" });
      return;
    }
    if (password && password.length < 8) {
      this.setData({ error: "密码至少需要 8 位" });
      return;
    }

    this.setData({ submitting: true, error: "", notice: "" });
    api.bindEmail(email, code, password).then(
      (res) => {
        this.setData({
          submitting: false,
          hasEmail: true,
          emailLabel: (res.user && res.user.email_masked) || "已绑定",
          email: "",
          password: "",
          code: "",
          devCode: "",
          notice: res.merged ? "已合并到该邮箱账号" : "邮箱绑定成功",
        });
        wx.showToast({
          title: res.merged ? "学习数据已合并" : "邮箱绑定成功",
          icon: "success",
        });
        setTimeout(() => wx.navigateBack(), 900);
      },
      (err) => {
        this.setData({
          submitting: false,
          error: (err && err.message) || "绑定失败，请重试",
        });
      },
    );
  },
});
