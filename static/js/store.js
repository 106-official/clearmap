/* ClearMap · store.js —— API 客户端 + 轻量状态 */
(function (win) {
  "use strict";

  // 后端基址（可变）：优先取本地保存的地址（在“个人中心→服务器设置”中修改），
  // 其次回退到打包时 index.html 里的 CLEARMAP_API_BASE；都为空则同源（Web 内嵌资源）。
  let API_BASE = (() => {
    try {
      const s = localStorage.getItem("clearmap_api_base");
      if (s != null) return s;
    } catch (e) { /* ignore */ }
    return win.CLEARMAP_API_BASE || "";
  })();

  const api = {
    user: "guest",
    token: localStorage.getItem("clearmap_token") || "",
    /* 当前后端地址（末尾带 /，同源为 ""） */
    serverBase() { return API_BASE; },
    /* 修改后端地址并持久化到本地，返回规范化后的地址 */
    setServerBase(url) {
      const v = String(url || "").trim();
      const norm = (v === "" || v === "/") ? "" : (v.replace(/\/+$/, "") + "/");
      API_BASE = norm;
      try {
        if (norm === "") localStorage.removeItem("clearmap_api_base");
        else localStorage.setItem("clearmap_api_base", norm);
      } catch (e) { /* ignore */ }
      return norm;
    },
    /* 认证查询串：登录后带 token，否则退回 guest */
    qs() {
      return this.token
        ? "&token=" + encodeURIComponent(this.token)
        : "&user=" + this.user;
    },
    /* 带认证参数的基础 GET（path 形如 /api/xx?） */
    async _get(path) {
      const r = await fetch(API_BASE + path + this.qs());
      return r.json();
    },
    /* 认证 POST（auth=true 时把 token 追到 URL 上） */
    async post(path, body, auth) {
      const url = (auth === false ? path : path + this.qs());
      const r = await fetch(API_BASE + url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      return r.json();
    },
    async _del(path) {
      const r = await fetch(API_BASE + path + this.qs(), { method: "DELETE" });
      return r.json();
    },

    /* ---- 认证 ----
       这些接口不需要用户身份，auth=false（登录登出在 body 里带 token）。 */
    async sms(phone) { return this.post("/api/sms", { phone }, false); },
    async login(phone, code) { return this.post("/api/auth/login", { phone, code }, false); },
    async logout() {
      if (this.token) await this.post("/api/auth/logout", { token: this.token }, false);
    },
    async authMe() { return this._get("/api/auth/me?"); },

    /* ---- 其余资源（认证采用 token 或退回 guest）---- */
    async meta() { return this._get("/api/meta?"); },
    /* 健康检查（用于“服务器设置”测连接） */
    async health() { return this._get("/api/health?"); },
    async pois(city) {
      return this._get("/api/pois?" + (city ? "city=" + encodeURIComponent(city) + "&" : ""));
    },
    async itinerary(budget, city) {
      return this._get(`/api/itinerary/${budget}?` + (city ? "city=" + encodeURIComponent(city) + "&" : ""));
    },
    async profile() { return this._get("/api/profile?"); },
    async me() { return this._get("/api/me?"); },
    async mbtiRecs(city) {
      return this._get("/api/mbti-recs?" + (city ? "city=" + encodeURIComponent(city) + "&" : ""));
    },

    async saveProfile(profile) {
      return this.post("/api/profile?", { profile });
    },
    async savePlan(plan) {
      return this.post("/api/plan?", plan);
    },
    async toggleFavorite(poiId) {
      return this.post("/api/favorite/" + poiId + "?", {});
    },
    async updateMe(patch) {
      return this.post("/api/me?", patch);
    },
    async uploadAvatar(dataUrl) {
      return this.post("/api/avatar?", { data: dataUrl });
    },
    async addCheckin(checkin) {
      return this.post("/api/checkin?", checkin);
    },
    async addRoute(route) {
      return this.post("/api/route?", route);
    },
    async routePlan(body) {
      return this.post("/api/route-plan?", body);
    },
    async transit() { return this._get("/api/transit?"); },
    async deleteCheckin(id) { return this._del("/api/checkin/" + id + "?"); },
    async deleteRoute(id) { return this._del("/api/route/" + id + "?"); },

    /* ---- 旅游随笔 / 发现（preview-1.22）---- */
    async publishEssay(payload) { return this.post("/api/essay?", payload); },
    async feed(limit) {
      return this._get("/api/feed?" + (limit ? "limit=" + limit + "&" : ""));
    },
    async deleteEssay(id) { return this._del("/api/essay/" + id + "?"); },
  };

  // 类别元数据
  const AXES = {
    nature: "自然山水", culture: "历史人文", food: "美食风味",
    shopping: "逛街购物", nightlife: "夜生活", family: "亲子休闲", photo: "网红打卡",
  };

  // 全局状态
  const state = {
    pois: [],
    meta: null,
    profile: { nature: 3, culture: 3, food: 3, shopping: 3, nightlife: 3, family: 3, photo: 3 },
    favorites: [],
    selected: null,
    me: { id: "guest", nickname: "", signature: "", avatar: "", mbti: null, mbti_name: "", phone: "" },
    checkins: [],
    routes: [],
    essays: [],          // 我的随笔
    feed: [],            // 发现流
    mbtiRecs: { mbti: null, name: "", recommended: [] },
  };

  // MBTI 四维与 16 型描述（选择器 / 预览用）
  const MBTI_DIMS = [
    { key: "精力", opts: ["E", "I"], label: { E: "外向 E", I: "内向 I" } },
    { key: "认知", opts: ["N", "S"], label: { N: "直觉 N", S: "实感 S" } },
    { key: "决策", opts: ["T", "F"], label: { T: "思考 T", F: "情感 F" } },
    { key: "生活", opts: ["J", "P"], label: { J: "计划 J", P: "随性 P" } },
  ];
  const MBTI_NAMES = {
    INTJ: "建筑师", INTP: "逻辑学家", ENTJ: "指挥官", ENTP: "辩论家",
    INFJ: "提倡者", INFP: "调停者", ENFJ: "主人公", ENFP: "竞选者",
    ISTJ: "物流师", ISFJ: "守卫者", ESTJ: "总经理", ESFJ: "执政官",
    ISTP: "鉴赏家", ISFP: "探险家", ESTP: "企业家", ESFP: "表演者",
  };

  // 极简 toast
  let toastTimer;
  function toast(msg) {
    const t = document.getElementById("toast");
    t.textContent = msg;
    t.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("is-visible"), 2200);
  }

  win.ClearMap = { api, AXES, state, toast, MBTI_DIMS, MBTI_NAMES };
})(window);