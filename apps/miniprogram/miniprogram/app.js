App({
  globalData: {
    token: "",
    user: null,
    loggedIn: false,
    studyDeck: [],
    studyUnits: [],
    studyOffline: false,
  },

  onLaunch() {
    const token = wx.getStorageSync("ap_token");
    if (token) this.globalData.token = token;
    const user = wx.getStorageSync("ap_user");
    if (user) this.globalData.user = user;
    // 离线示例模式也会写 ap_logged_in，但没有 token；两者任一存在都算已登录。
    this.globalData.loggedIn =
      Boolean(token) || Boolean(wx.getStorageSync("ap_logged_in"));
  },
});
