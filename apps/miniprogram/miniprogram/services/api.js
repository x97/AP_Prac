const { API_BASE_URL, PREVIEW_LIMIT } = require("../config");

const UNIT_LABEL = {
  "0": "Research Methods",
  "1": "Unit 1 · Biological Bases",
  "2": "Unit 2 · Cognition",
  "3": "Unit 3 · Development & Learning",
  "4": "Unit 4 · Social & Personality",
  "5": "Unit 5 · Mental & Physical Health",
  EM: "Research Methods",
};

const UNIT_OPTIONS = [
  { id: "methods", label: "研究方法" },
  { id: "1", label: "Unit 1" },
  { id: "2", label: "Unit 2" },
  { id: "3", label: "Unit 3" },
  { id: "4", label: "Unit 4" },
  { id: "5", label: "Unit 5" },
];

function unitMatches(apUnit, unitId) {
  if (unitId === "methods") return apUnit === "0" || apUnit === "EM";
  return String(apUnit || "") === String(unitId);
}

function absoluteAssetUrl(url) {
  if (!url) return "";
  if (/^https?:\/\//i.test(url)) return url;
  const base = API_BASE_URL.replace(/\/+$/, "");
  return `${base}${url.charAt(0) === "/" ? "" : "/"}${url}`;
}

function normalizeCard(card) {
  const unit = card.ap_unit || "";
  const unitLabel = UNIT_LABEL[unit] || "AP Psychology";
  return {
    ...card,
    origin: card.topic ? `${unitLabel} · ${card.topic}` : unitLabel,
    audio_url: absoluteAssetUrl(card.audio_url),
    definition: card.definition || "",
    quote: card.quote || "",
    showQuote: Boolean(card.definition && card.quote),
  };
}

function request(path, options) {
  const opts = options || {};
  const header = { "content-type": "application/json" };
  const token = opts.auth === false ? "" : getToken();
  if (token) header.Authorization = `Bearer ${token}`;
  Object.assign(header, opts.header || {});
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE_URL.replace(/\/+$/, "")}${path}`,
      method: opts.method || "GET",
      data: opts.data,
      header,
      timeout: opts.timeout || 15000,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
          return;
        }
        const body = res.data || {};
        const error = new Error(
          body.message ||
            (res.statusCode === 401 ? "请先登录" : `请求失败（${res.statusCode}）`),
        );
        error.statusCode = res.statusCode;
        error.code = body.code;
        error.authRequired = res.statusCode === 401;
        reject(error);
      },
      fail() {
        const error = new Error(
          "连接不到本机 API，请确认 FastAPI 已启动，并在开发者工具关闭合法域名校验。",
        );
        error.offline = true;
        reject(error);
      },
    });
  });
}

function getAppInstance() {
  try {
    return getApp();
  } catch (e) {
    return null;
  }
}

function getToken() {
  const app = getAppInstance();
  if (app && app.globalData && app.globalData.token) {
    return app.globalData.token;
  }
  try {
    return wx.getStorageSync("ap_token") || "";
  } catch (e) {
    return "";
  }
}

function setToken(token) {
  const app = getAppInstance();
  if (app && app.globalData) {
    app.globalData.token = token;
    app.globalData.loggedIn = true;
  }
  try {
    wx.setStorageSync("ap_token", token);
  } catch (e) {
    // Storage can be unavailable; globalData still carries the token.
  }
}

function clearSession() {
  const app = getAppInstance();
  if (app && app.globalData) {
    app.globalData.token = "";
    app.globalData.user = null;
    app.globalData.loggedIn = false;
  }
  try {
    wx.removeStorageSync("ap_token");
    wx.removeStorageSync("ap_user");
    wx.removeStorageSync("ap_logged_in");
  } catch (e) {
    // Storage can be unavailable.
  }
}

function hasToken() {
  return Boolean(getToken());
}

function updateStoredUser(user) {
  const app = getAppInstance();
  if (app && app.globalData) app.globalData.user = user || null;
  try {
    wx.setStorageSync("ap_user", user || null);
  } catch (e) {
    // Storage can be unavailable.
  }
}

function persistLogin(res) {
  if (!res || !res.token) {
    throw new Error("登录失败：服务端未返回 token");
  }
  setToken(res.token);
  updateStoredUser(res.user);
  try {
    wx.setStorageSync("ap_logged_in", 1);
  } catch (e) {
    // Storage can be unavailable.
  }
  return res;
}

function wechatLogin() {
  return new Promise((resolve, reject) => {
    wx.login({
      success(loginRes) {
        if (!loginRes.code) {
          reject(new Error("微信登录失败，请重试"));
          return;
        }
        request("/api/v1/auth/wechat/login", {
          method: "POST",
          data: { code: loginRes.code },
          auth: false,
        }).then(
          (res) => resolve(persistLogin(res)),
          reject,
        );
      },
      fail() {
        reject(new Error("微信登录失败，请重试"));
      },
    });
  });
}

function emailLogin(email, password) {
  return request("/api/v1/auth/email/login", {
    method: "POST",
    data: { email: email, password: password },
    auth: false,
  }).then(persistLogin);
}

function sendEmailCode(email, purpose) {
  return request("/api/v1/auth/email/code", {
    method: "POST",
    data: { email: email, purpose: purpose },
    auth: false,
  });
}

function emailRegister(email, code, password) {
  return request("/api/v1/auth/email/register", {
    method: "POST",
    data: { email: email, code: code, password: password },
    auth: false,
  }).then(persistLogin);
}

function resetPassword(email, code, password) {
  return request("/api/v1/auth/email/reset-password", {
    method: "POST",
    data: { email: email, code: code, password: password },
    auth: false,
  });
}

function getMe() {
  return request("/api/v1/auth/me").then((res) => {
    updateStoredUser(res.user);
    return res;
  });
}

function sendBindEmailCode(email) {
  return request("/api/v1/me/email/code", {
    method: "POST",
    data: { email: email },
  });
}

function bindEmail(email, code, password) {
  const data = { email: email, code: code };
  if (password) data.password = password;
  return request("/api/v1/me/email/bind", {
    method: "POST",
    data: data,
  }).then((res) => {
    updateStoredUser(res.user);
    return res;
  });
}

function bindWechat(code, password) {
  const data = { code: code };
  if (password) data.password = password;
  return request("/api/v1/auth/wechat/bind", {
    method: "POST",
    data: data,
    timeout: 4000,
  }).then((res) => {
    updateStoredUser(res.user);
    return res;
  });
}

function autoBindWechat(password) {
  // Best-effort link after email login. Never blocks or fails the login flow.
  return new Promise((resolve) => {
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      resolve(value);
    };
    const timer = setTimeout(() => finish(null), 2500);
    wx.login({
      success(loginRes) {
        if (!loginRes.code) {
          clearTimeout(timer);
          finish(null);
          return;
        }
        bindWechat(loginRes.code, password).then(
          (res) => {
            clearTimeout(timer);
            finish(res);
          },
          () => {
            clearTimeout(timer);
            finish(null);
          },
        );
      },
      fail() {
        clearTimeout(timer);
        finish(null);
      },
    });
  });
}

function logout() {
  return request("/api/v1/auth/logout", { method: "POST" })
    .catch(() => {})
    .then(() => clearSession());
}

function getPreview(limit, units) {
  const size = limit || PREVIEW_LIMIT;
  const parts = [`limit=${size}`];
  if (units && units.length) {
    parts.push(`units=${encodeURIComponent(units.join(","))}`);
  }
  return request(`/api/v1/flashcards/preview?${parts.join("&")}`).then((data) => ({
    cards: (data.cards || []).map(normalizeCard),
    stats: data.stats || { total: 0, due: 0, new: 0, reviewed: 0 },
    ahead: Boolean(data.ahead),
  }));
}

function getNext(units, minStars) {
  const parts = [];
  if (units && units.length) {
    parts.push(`units=${encodeURIComponent(units.join(","))}`);
  }
  if (minStars) parts.push(`min_stars=${minStars}`);
  const query = parts.length ? `?${parts.join("&")}` : "";
  return request(`/api/v1/flashcards/next${query}`).then((data) => ({
    ...data,
    card: data.card ? normalizeCard(data.card) : null,
  }));
}

function reviewCard(conceptId, rating) {
  return request(
    `/api/v1/flashcards/${encodeURIComponent(conceptId)}/review`,
    { method: "POST", data: { rating } },
  );
}

function getUnfamiliar(limit, offset) {
  const size = limit || 30;
  const start = offset || 0;
  return request(
    `/api/v1/flashcards/unfamiliar?limit=${size}&offset=${start}`,
  ).then((data) => ({
    ...data,
    cards: (data.cards || []).map(normalizeCard),
    total: Number(data.total || 0),
  }));
}

const DEMO_CARDS = [
  {
    concept_id: "demo-correlation",
    term: "Correlation",
    ipa: "ˌkɔrəˈleɪʃən",
    definition: "relationship between two variables, not causation",
    quote: "A correlation expresses a relationship between two variables without ascribing cause.",
    ap_unit: "0",
    topic: "Correlational Method",
    stars: 5,
    weight: 92.25,
  },
  {
    concept_id: "demo-standard-deviation",
    term: "Standard deviation",
    ipa: "ˈstændərd ˌdiviˈeɪʃən",
    definition: "measures how spread out scores are",
    quote: "Standard deviation is the square root of the variance.",
    ap_unit: "0",
    topic: "Descriptive Statistics",
    stars: 5,
    weight: 87.83,
  },
  {
    concept_id: "demo-operant",
    term: "Operant conditioning",
    ipa: "ˈɑpərənt kənˈdɪʃənɪŋ",
    definition: "learning based on consequences of behavior",
    quote: "Operant conditioning is learning based on the association of consequences with one’s behaviors.",
    ap_unit: "3",
    topic: "Operant Conditioning",
    stars: 5,
    weight: 86.62,
  },
  {
    concept_id: "demo-hippocampus",
    term: "Hippocampus",
    ipa: "ˌhɪpoʊˈkæmpəs",
    definition: "brain structure important for encoding new memories",
    quote: "The hippocampus is important in encoding new memories.",
    ap_unit: "2",
    topic: "Storing Memories",
    stars: 4,
    weight: 70.78,
  },
  {
    concept_id: "demo-fae",
    term: "Fundamental attribution error",
    ipa: "ˌfəndəˈmɛnəl ˌætrɪˈbjuʃən ˈɛrər",
    definition: "overestimating dispositional factors when explaining others",
    quote: "People tend to overestimate dispositional factors and underestimate situational variables.",
    ap_unit: "4",
    topic: "Attribution Theory",
    stars: 5,
    weight: 78.17,
  },
  {
    concept_id: "demo-confirmation",
    term: "Confirmation bias",
    ipa: "ˌkɑnfərˈmeɪʃən baɪəs",
    definition: "seeking only evidence that supports our beliefs",
    quote: "We tend to look for evidence that confirms our beliefs and ignore contradictory evidence.",
    ap_unit: "2",
    topic: "Problem-Solving",
    stars: 4,
    weight: 75.79,
  },
];

function getDemoDeck(units) {
  const selected = units && units.length ? units : [];
  const cards = selected.length
    ? DEMO_CARDS.filter((card) =>
        selected.some((unit) => unitMatches(card.ap_unit, unit)),
      )
    : DEMO_CARDS;
  return {
    cards: cards.map(normalizeCard),
    stats: {
      total: cards.length,
      due: 0,
      new: cards.length,
      reviewed: 0,
    },
    ahead: false,
  };
}

module.exports = {
  getPreview,
  getNext,
  reviewCard,
  getUnfamiliar,
  getDemoDeck,
  normalizeCard,
  absoluteAssetUrl,
  UNIT_OPTIONS,
  unitMatches,
  wechatLogin,
  emailLogin,
  sendEmailCode,
  emailRegister,
  resetPassword,
  getMe,
  sendBindEmailCode,
  bindEmail,
  bindWechat,
  autoBindWechat,
  logout,
  getToken,
  setToken,
  clearSession,
  hasToken,
};
