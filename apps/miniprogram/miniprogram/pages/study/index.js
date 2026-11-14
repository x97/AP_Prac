const api = require("../../services/api");

const app = getApp();

const EMPTY_QUEUE = {
  due: 0,
  new_today: 0,
  new_limit: 0,
  new_remaining: 0,
  new_limit_reached: false,
  reviewed_today: 0,
  total: 0,
  caught_up: false,
  next_due_at: null,
};

Page({
  data: {
    loading: true,
    error: "",
    offline: false,
    card: null,
    queue: { ...EMPTY_QUEUE },
    flipped: false,
    done: false,
    known: 0,
    again: 0,
    rating: "",
    pendingNext: false,
    audioPlaying: false,
    starSlots: [1, 2, 3, 4, 5],
  },

  onLoad() {
    this.units = app.globalData.studyUnits || [];
    this.demoCards = [];
    this.demoIndex = 0;
    if (app.globalData.studyOffline || !api.hasToken()) {
      this.startOffline();
      return;
    }
    this.fetchNext();
  },

  onHide() {
    this.stopAudio();
  },

  onUnload() {
    this.destroyAudio();
  },

  fetchNext(options) {
    const opts = options || {};
    const silent = Boolean(opts.silent);
    if (!silent) this.setData({ loading: true, error: "" });
    return api.getNext(this.units).then(
      (queue) => {
        const nextQueue = { ...EMPTY_QUEUE, ...queue };
        delete nextQueue.card;
        this.setData({
          loading: false,
          queue: nextQueue,
          error: "",
          pendingNext: false,
        });
        if (queue.card) {
          this.stopAudio();
          this.setData({
            card: queue.card,
            flipped: false,
            done: false,
            audioPlaying: false,
          });
        } else {
          this.finish();
        }
        return true;
      },
      (err) => {
        if (err && err.authRequired) {
          api.clearSession();
          wx.reLaunch({ url: "/pages/login/index" });
          return false;
        }
        const message = (err && err.message) || "加载卡片失败";
        if (!this.data.card && !silent && !this.data.done) {
          // First load failed: keep the old offline demo experience.
          this.startOffline();
          this.setData({ error: message });
          return false;
        }
        this.setData({
          loading: false,
          error: message,
          pendingNext: silent,
        });
        return false;
      },
    );
  },

  startOffline() {
    let cards = app.globalData.studyDeck || [];
    if (!cards.length) cards = api.getDemoDeck(this.units).cards;
    this.demoCards = (cards || []).map(api.normalizeCard);
    this.demoIndex = 0;
    this.setData({
      offline: true,
      loading: false,
      pendingNext: false,
      rating: "",
      queue: {
        ...EMPTY_QUEUE,
        total: this.demoCards.length,
        caught_up: true,
      },
    });
    this.showDemoCard(0);
  },

  showDemoCard(index) {
    const card = this.demoCards[index] || null;
    this.stopAudio();
    this.setData({
      card,
      flipped: false,
      done: !card,
      loading: false,
      pendingNext: false,
      rating: "",
      audioPlaying: false,
    });
  },

  flip() {
    if (!this.data.card) return;
    this.setData({ flipped: !this.data.flipped });
  },

  rate(event) {
    if (this.ratingLock || this.data.rating || !this.data.card) return;
    const rating =
      event.currentTarget.dataset.rating === "known" ? "known" : "again";
    if (this.data.offline) {
      this.ratingLock = true;
      setTimeout(() => {
        this.ratingLock = false;
      }, 240);
      this.bumpRating(rating);
      this.demoIndex += 1;
      this.showDemoCard(this.demoIndex);
      return;
    }
    this.setData({ rating, error: "", pendingNext: false });
    api.reviewCard(this.data.card.concept_id, rating).then(
      () => {
        this.bumpRating(rating);
        return this.fetchNext({ silent: true }).then(() => {
          this.setData({ rating: "" });
        });
      },
      (err) => {
        this.setData({ rating: "" });
        if (err && err.authRequired) {
          api.clearSession();
          wx.reLaunch({ url: "/pages/login/index" });
          return;
        }
        const message = (err && err.message) || "保存进度失败";
        this.setData({ error: message });
        wx.showToast({ title: message, icon: "none" });
      },
    );
  },

  bumpRating(rating) {
    const key = rating === "known" ? "known" : "again";
    this.setData({ [key]: this.data[key] + 1, flipped: false });
  },

  finish() {
    this.stopAudio();
    this.setData({
      done: true,
      card: null,
      flipped: false,
      loading: false,
      rating: "",
      pendingNext: false,
    });
  },

  retryNext() {
    if (this.data.rating) return;
    this.fetchNext({ silent: true });
  },

  restart() {
    this.ratingLock = false;
    this.setData({
      known: 0,
      again: 0,
      done: false,
      error: "",
      pendingNext: false,
      rating: "",
    });
    if (this.data.offline) {
      this.demoIndex = 0;
      this.showDemoCard(0);
      return;
    }
    this.fetchNext();
  },

  playAudio() {
    const card = this.data.card;
    if (!card) return;
    if (!card.audio_url) {
      wx.showToast({ title: "这张卡暂无发音", icon: "none" });
      return;
    }

    this.destroyAudio();
    const audio = wx.createInnerAudioContext();
    this.audio = audio;
    audio.obeyMuteSwitch = false;
    audio.src = card.audio_url;
    audio.onPlay(() => this.setData({ audioPlaying: true }));
    audio.onEnded(() => this.setData({ audioPlaying: false }));
    audio.onStop(() => this.setData({ audioPlaying: false }));
    audio.onError(() => {
      this.setData({ audioPlaying: false });
      wx.showToast({
        title: "音频加载失败，请确认本机 API 已启动",
        icon: "none",
      });
    });
    audio.play();
  },

  stopAudio() {
    if (!this.audio) return;
    this.audio.stop();
    this.setData({ audioPlaying: false });
  },

  destroyAudio() {
    if (!this.audio) return;
    this.audio.stop();
    this.audio.destroy();
    this.audio = null;
  },

  backToCards() {
    wx.navigateBack({
      delta: 1,
      fail: () => wx.switchTab({ url: "/pages/cards/index" }),
    });
  },
});
