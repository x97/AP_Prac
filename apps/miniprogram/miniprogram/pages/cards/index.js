const api = require("../../services/api");

const app = getApp();

function formatNumber(value) {
  return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

Page({
  data: {
    loading: true,
    error: "",
    usingDemo: false,
    localOnly: false,
    cards: [],
    stats: {
      total: 0,
      new: 0,
    },
    totalLabel: "—",
    unitOptions: api.UNIT_OPTIONS.map((unit) => ({ ...unit, selected: true })),
    allSelected: true,
    scopeLabel: "全部单元",
    scopeOpen: false,
  },

  onLoad() {
    if (!app.globalData.loggedIn) {
      wx.reLaunch({ url: "/pages/login/index" });
      return;
    }
    this.loadPreview();
  },

  onShow() {
    if (typeof this.getTabBar === "function" && this.getTabBar()) {
      this.getTabBar().setData({ selected: 0 });
    }
    if (!app.globalData.loggedIn) {
      wx.reLaunch({ url: "/pages/login/index" });
    }
  },

  onPullDownRefresh() {
    this.loadPreview().then(() => wx.stopPullDownRefresh());
  },

  selectedUnits() {
    return this.data.unitOptions.filter((unit) => unit.selected).map((unit) => unit.id);
  },

  toggleScope() {
    this.setData({ scopeOpen: !this.data.scopeOpen });
  },

  closeScope() {
    this.setData({ scopeOpen: false });
  },

  applyScope(unitOptions, reload) {
    const selected = unitOptions.filter((unit) => unit.selected);
    const selectedCount = selected.length;
    const allSelected = selectedCount === unitOptions.length;
    const scopeLabel = allSelected
      ? "全部单元"
      : selectedCount === 1
        ? selected[0].label
        : `${selectedCount} 个单元`;
    this.setData({ unitOptions, allSelected, scopeLabel });
    if (reload) this.loadPreview(selected.map((unit) => unit.id));
  },

  toggleUnit(event) {
    const id = event.currentTarget.dataset.id;
    const unitOptions = this.data.unitOptions.map((unit) =>
      unit.id === id ? { ...unit, selected: !unit.selected } : unit,
    );
    if (!unitOptions.some((unit) => unit.selected)) {
      wx.showToast({ title: "至少选择一个单元", icon: "none" });
      return;
    }
    this.applyScope(unitOptions, true);
  },

  selectAllUnits() {
    const unitOptions = this.data.unitOptions.map((unit) => ({ ...unit, selected: true }));
    this.applyScope(unitOptions, true);
    this.closeScope();
  },

  loadPreview(pickedUnits) {
    const units = pickedUnits || this.selectedUnits();
    const requestId = (this.requestId || 0) + 1;
    this.requestId = requestId;
    this.setData({
      loading: true,
      error: "",
      localOnly: !api.hasToken(),
    });
    return api
      .getPreview(undefined, units)
      .then((deck) => {
        if (this.requestId !== requestId) return;
        if (!deck.cards.length) throw new Error("所选单元暂时没有可预览的卡片");
        this.applyDeck(deck, false);
      })
      .catch((err) => {
        if (this.requestId !== requestId) return;
        this.applyDeck(api.getDemoDeck(units), true);
        this.setData({
          error:
            err && err.message
              ? err.message
              : "连接不到本机 API，当前显示示例卡片。",
        });
      })
      .then(() => {
        if (this.requestId === requestId) this.setData({ loading: false });
      });
  },

  applyDeck(deck, usingDemo) {
    const stats = deck.stats || {};
    const total = Number(stats.total || 0);
    app.globalData.studyDeck = deck.cards || [];
    app.globalData.studyOffline = !api.hasToken();
    this.setData({
      cards: deck.cards || [],
      stats: {
        total,
        new: Number(stats.new || 0),
      },
      totalLabel: total ? formatNumber(total) : "—",
      usingDemo,
      localOnly: !api.hasToken(),
    });
  },

  startStudy() {
    if (!this.data.cards.length) {
      wx.showToast({ title: "卡片还在加载", icon: "none" });
      return;
    }
    app.globalData.studyDeck = this.data.cards;
    app.globalData.studyUnits = this.selectedUnits();
    app.globalData.studyOffline = !api.hasToken();
    wx.navigateTo({ url: "/pages/study/index" });
  },
});
