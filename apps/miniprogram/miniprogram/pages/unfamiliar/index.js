const api = require("../../services/api");
const { UNFAMILIAR_PAGE_SIZE } = require("../../config");

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (part) => (part < 10 ? `0${part}` : String(part));
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate(),
  )} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

Page({
  data: {
    items: [],
    total: 0,
    loading: true,
    loadingMore: false,
    hasMore: false,
    error: "",
    offline: false,
    starSlots: [1, 2, 3, 4, 5],
  },

  onLoad() {
    this.reload();
  },

  onPullDownRefresh() {
    this.reload().then(() => wx.stopPullDownRefresh());
  },

  onReachBottom() {
    if (
      this.data.offline ||
      !this.data.hasMore ||
      this.data.loading ||
      this.data.loadingMore
    ) {
      return;
    }
    this.setData({ loadingMore: true, error: "" });
    const offset = this.data.items.length;
    this.fetchPage(offset).then(
      (data) => {
        const seen = new Set(this.data.items.map((item) => item.concept_id));
        const fresh = data.items.filter((item) => !seen.has(item.concept_id));
        this.setData({
          items: this.data.items.concat(fresh),
          total: data.total,
          hasMore: data.hasMore,
          loadingMore: false,
        });
      },
      (err) => {
        if (this.handleAuthError(err)) return;
        const message = (err && err.message) || "加载更多失败";
        this.setData({ loadingMore: false, error: message });
        wx.showToast({ title: message, icon: "none" });
      },
    );
  },

  reload() {
    if (!api.hasToken()) {
      this.setData({
        offline: true,
        loading: false,
        loadingMore: false,
        items: [],
        total: 0,
        hasMore: false,
        error: "",
      });
      return Promise.resolve();
    }
    const requestId = (this.requestId || 0) + 1;
    this.requestId = requestId;
    this.setData({ offline: false, loading: true, error: "" });
    return this.fetchPage(0).then(
      (data) => {
        if (this.requestId !== requestId) return;
        this.setData({
          items: data.items,
          total: data.total,
          hasMore: data.hasMore,
          loading: false,
          loadingMore: false,
        });
      },
      (err) => {
        if (this.requestId !== requestId) return;
        if (this.handleAuthError(err)) return;
        this.setData({
          loading: false,
          loadingMore: false,
          error: (err && err.message) || "加载失败",
        });
      },
    );
  },

  fetchPage(offset) {
    return api.getUnfamiliar(UNFAMILIAR_PAGE_SIZE, offset).then((data) => ({
      items: (data.cards || []).map((card) => ({
        ...card,
        lastReviewedLabel: formatDate(card.last_reviewed_at),
      })),
      total: Number(data.total || 0),
      hasMore: Boolean(data.has_more),
    }));
  },

  handleAuthError(err) {
    if (err && err.authRequired) {
      api.clearSession();
      wx.reLaunch({ url: "/pages/login/index" });
      return true;
    }
    return false;
  },

  retry() {
    this.reload();
  },
});
