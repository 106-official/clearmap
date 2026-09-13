/* ClearMap · store.js —— API 客户端 + 轻量状态 */
(function (win) {
  "use strict";

  const USER = "guest";
  const api = {
    user: USER,
    async _get(path) {
      const r = await fetch(path + "&user=" + this.user);
      return r.json();
    },
    async meta() { return this._get("/api/meta?"); },
    async pois() { return this._get("/api/pois?"); },
    async itinerary(budget) { return this._get(`/api/itinerary/${budget}?`); },
    async profile() { return this._get("/api/profile?"); },
    async me() { return this._get("/api/me?"); },
    async mbtiRecs() { return this._get("/api/mbti-recs?"); },

    async post(path, body) {
      const r = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      return r.json();
    },
    async saveProfile(profile) {
      return this.post("/api/profile?user=" + this.user, { profile });
    },
    async savePlan(plan) {
      return this.post("/api/plan?user=" + this.user, plan);
    },
    async toggleFavorite(poiId) {
      return this.post("/api/favorite/" + poiId + "?user=" + this.user, {});
    },
    async updateMe(patch) {
      return this.post("/api/me?user=" + this.user, patch);
    },
    async uploadAvatar(dataUrl) {
      return this.post("/api/avatar?user=" + this.user, { data: dataUrl });
    },
    async addCheckin(checkin) {
      return this.post("/api/checkin?user=" + this.user, checkin);
    },
    async addRoute(route) {
      return this.post("/api/route?user=" + this.user, route);
    },
    async routePlan(body) {
      return this.post("/api/route-plan?user=" + this.user, body);
    },
    async transit() { return this._get("/api/transit?"); },
    async del(path) {
      const r = await fetch(path + "&user=" + this.user, { method: "DELETE" });
      return r.json();
    },
    async deleteCheckin(id) { return this.del("/api/checkin/" + id + "?"); },
    async deleteRoute(id) { return this.del("/api/route/" + id + "?"); },
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
    me: { id: "guest", nickname: "", signature: "", avatar: "", mbti: null, mbti_name: "" },
    checkins: [],
    routes: [],
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