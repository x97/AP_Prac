Component({
  data: {
    selected: 0,
    list: [
      { pagePath: "/pages/cards/index", text: "卡片" },
      { pagePath: "/pages/me/index", text: "我的" },
    ],
  },

  methods: {
    switchTab(event) {
      const { path, index } = event.currentTarget.dataset;
      if (Number(index) === this.data.selected) return;
      wx.switchTab({ url: path });
    },
  },
});
