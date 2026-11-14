const api = require("../../services/api");

Page({
  data: {
    unfamiliarLabel: "—",
    syncLabel: "—",
    emailLabel: "未绑定",
  },

  onShow() {
    if (typeof this.getTabBar === "function" && this.getTabBar()) {
      this.getTabBar().setData({ selected: 1 });
    }
    if (!getApp().globalData.loggedIn) {
      wx.reLaunch({ url: "/pages/login/index" });
      return;
    }
    this.setData({ syncLabel: api.hasToken() ? "已开启" : "本地预览" });
    this.loadProfile();
    this.loadUnfamiliarCount();
  },

  loadProfile() {
    if (!api.hasToken()) return;
    const stored = getApp().globalData.user;
    if (stored) this.applyUser(stored);
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
    });
  },

  onBindEmail() {
    wx.navigateTo({ url: "/pages/bind-email/index" });
  },

  loadUnfamiliarCount() {
    if (!api.hasToken()) {
      this.setData({ unfamiliarLabel: "—" });
      return;
    }
    this.setData({ unfamiliarLabel: "…" });
    api.getUnfamiliar(1, 0).then(
      (data) => {
        const total = Number(data.total || 0);
        this.setData({ unfamiliarLabel: `${total} 条` });
      },
      (err) => {
        if (err && err.authRequired) {
          api.clearSession();
          wx.reLaunch({ url: "/pages/login/index" });
          return;
        }
        this.setData({ unfamiliarLabel: "—" });
      },
    );
  },

  onUnfamiliar() {
    wx.navigateTo({ url: "/pages/unfamiliar/index" });
  },

  onAbout() {
    wx.showModal({
      title: "PsyPrac",
      content: "AP Psychology 记忆卡片 · psyprac.com",
      showCancel: false,
      confirmText: "知道了",
    });
  },

  onLogout() {
    api.logout().then(() => {
      wx.reLaunch({ url: "/pages/login/index" });
    });
  },
});
