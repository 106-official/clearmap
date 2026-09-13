/* ClearMap · app.js —— 引导启动 + 视图切换 + 事件编排 */
(function () {
  "use strict";

  const { api, AXES, state, toast, render, map } = window.ClearMap;

  let currentItinerary = null;
  let currentBudget = "full";
  let pendingCheckinPoi = "";
  let startPoint = null;   // {lat, lon, name}

  function escHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // ---- 起点选择 ----
  function setStartPoint(pt, name) {
    startPoint = { lat: pt.lat, lon: pt.lon, name: name || "起点" };
    const el = document.getElementById("startName");
    if (el) el.textContent = startPoint.name;
    toast("起点已设为 " + (name || "地图所示位置"));
    pickingStart = false;
    map.setClickMap(null);
    map.drawPlan(null); // 清除旧的规划线，方便重新规划
  }
  let pickingStart = false;
  function enterPickStart() {
    pickingStart = true;
    map.setClickMap((lat, lon) => setStartPoint({ lat, lon }, "我点选的位置"));
    toast("已进入选起点模式：点击地图空白处设为起点");
  }
  function useGpsStart() {
    if (!navigator.geolocation) { toast("当前环境不支持定位"); return; }
    navigator.geolocation.getCurrentPosition(
      (pos) => setStartPoint({ lat: pos.coords.latitude, lon: pos.coords.longitude }, "我的位置"),
      () => toast("无法获取位置，请改用「选起点」在地图上点选"),
      { timeout: 8000, maximumAge: 30000 }
    );
  }

  // ---- 纸飞机：规划前往景点的最省时路线 ----
  let lastPlanPoi = null;
  function planToPoi(poiId) {
    const poi = state.pois.find((p) => p.id === poiId);
    const routeEl = document.getElementById("sideRoutePanel");
    if (!poi || !routeEl) return;
    if (!startPoint) {
      routeEl.innerHTML = '<div class="rp-empty">请先在地图页「选起点」（或点 ◎ 用我的位置），再规划路线。</div>';
      return;
    }
    lastPlanPoi = poiId;
    api.routePlan({
      from: { lat: startPoint.lat, lon: startPoint.lon, name: startPoint.name },
      to: { poi_id: poiId },
    }).then((r) => {
      if (r.ok) {
        render.renderRoutePlan(routeEl, r, startPoint.name, poi.name);
        map.drawPlan(r.legs);
        toast("已为您规划前往「" + poi.name + "」的路线");
      } else {
        routeEl.innerHTML = '<div class="rp-empty">' + escHtml(r.error || "规划失败") + "</div>";
      }
    });
  }

  // ---- 视图切换 ----
  const VIEWS = ["map", "prefs", "plan", "me"];
  function showView(name) {
    document.body.dataset.view = name;
    VIEWS.forEach((v) => {
      const sec = document.getElementById("view-" + v);
      if (sec) sec.hidden = v !== name;
    });
    document.querySelectorAll(".nav-link").forEach((b) => {
      b.classList.toggle("is-active", b.getAttribute("data-nav") === name);
    });
    if (name === "me") renderCheckinSelect();
  }

  // ---- 地图 ----
  function selectPoi(id) {
    state.selected = id;
    const poi = state.pois.find((p) => p.id === id);
    render.renderSide(document.getElementById("sidePanel"), poi);
    renderMap();
  }

  function renderMap() {
    map.renderMap(document.getElementById("mapPanel"), state.pois, state.selected, selectPoi);
  }

  // ---- 事件委托：侧栏（收藏 + 打卡入口）----
  function onSideClick(e) {
    const fav = e.target.closest("[data-fav]");
    if (fav) {
      const id = fav.getAttribute("data-fav");
      api.toggleFavorite(id).then((r) => {
        if (r.ok) {
          state.favorites = r.favorites;
          toast(r.action === "added" ? "已收藏" : "已取消收藏");
          renderSideNow();
        }
      });
      return;
    }
    const ck = e.target.closest("[data-checkin-poi]");
    if (ck) {
      pendingCheckinPoi = ck.getAttribute("data-checkin-poi");
      showView("me");
      renderCheckinSelect();
      toast("选好景点后，上传照片即可打卡");
      return;
    }
    // 纸飞机：规划前往景点的最省时路线
    const rp = e.target.closest("[data-route-poi]");
    if (rp) {
      planToPoi(rp.getAttribute("data-route-poi"));
    }
  }

  function renderSideNow() {
    const poi = state.pois.find((p) => p.id === state.selected);
    render.renderSide(document.getElementById("sidePanel"), poi);
  }

  function renderSaved(plans) {
    render.renderSaved(document.getElementById("savedPlans"), plans);
  }

  // ---- 偏好 ----
  function renderPrefs() {
    render.renderPrefs(document.getElementById("prefsPanel"), state.profile, function (key, v) {
      state.profile[key] = v;
      saveProfileSoon();
      refreshAffinities();
    });
  }

  let prefTimer;
  function saveProfileSoon() {
    clearTimeout(prefTimer);
    prefTimer = setTimeout(() => {
      api.saveProfile(state.profile).then((r) => {
        if (r.ok) toast("偏好已存进本地");
      });
    }, 400);
  }

  function refreshAffinities() {
    api.pois().then((r) => {
      if (r.ok) {
        state.pois = r.pois;
        renderMap();
        renderSideNow();
        renderCheckinSelect();
      }
    });
  }

  // ---- 行程 ----
  function generateItinerary() {
    api.itinerary(currentBudget).then((r) => {
      if (r.ok) {
        currentItinerary = r;
        render.renderItinerary(document.getElementById("planPanel"), r);
        document.getElementById("savePlanBtn").disabled = !r.items.length;
      }
    });
  }

  function savePlan() {
    if (!currentItinerary || !currentItinerary.items.length) return;
    const items = currentItinerary.items.map((it) => ({
      id: it.poi.id, name: it.poi.name, district: it.poi.district,
    }));
    api.savePlan({ title: "我的行程 · " + todayText(), budget: currentBudget, items }).then((r) => {
      if (r.ok) {
        toast("行程已存进本地");
        loadProfile();
      }
    });
  }

  function loadProfile() {
    api.profile().then((r) => {
      if (r.ok) {
        state.profile = r.profile;
        state.favorites = r.favorites || [];
        renderPrefs();
        renderSaved(r.plans || []);
        refreshAffinities();
      }
    });
  }

  // ---- 个人中心 ----
  function loadMe() {
    api.me().then((r) => {
      if (!r.ok) return;
      state.me = r.me;
      state.checkins = r.checkins || [];
      state.routes = r.routes || [];
      state.favorites = r.favorites || [];
      render.renderProfile(state.me);
      render.renderCheckins(document.getElementById("checkinList"), state.checkins);
      render.renderRoutes(document.getElementById("routeList"), state.routes);
      renderCheckinSelect();
      loadMbtiRecs();
      map.drawCheckins(state.checkins);
    });
  }

  function renderCheckinSelect() {
    render.renderCheckinSelect(document.getElementById("checkinPoi"), state.pois, pendingCheckinPoi);
  }

  function loadMbtiRecs() {
    api.mbtiRecs().then((r) => {
      if (r.ok) {
        state.mbtiRecs = r;
        render.renderMbtiRecs(document.getElementById("mbtiStrip"), r);
        render.renderMbtiRecsMe(document.getElementById("mbtiRecsMe"), r);
      }
    });
  }

  // ---- MBTI 弹窗 ----
  function openMbtiModal() {
    document.getElementById("mbtiModal").hidden = false;
    render.renderMbtiPicker(document.getElementById("mbtiPicker"));
  }
  function closeMbtiModal() {
    document.getElementById("mbtiModal").hidden = true;
  }
  function currentMbtiCode() {
    let code = "";
    document.querySelectorAll("#mbtiPicker .mbti-dim").forEach((d) => {
      const on = d.querySelector(".mbti-opt.is-on");
      if (on) code += on.getAttribute("data-opt");
    });
    return code.length === 4 ? code : "";
  }
  function saveMbti() {
    const code = currentMbtiCode();
    if (!code) return;
    api.updateMe({ mbti: code }).then((r) => {
      if (r.ok) {
        closeMbtiModal();
        toast("已认证 " + code + "，地图为你换了一批风景");
        loadMe();
        refreshAffinities();
      }
    });
  }

  // ---- 头像 / 资料 ----
  function uploadAvatar(file) {
    if (!file) return;
    if (file.size > 4 * 1024 * 1024) { toast("图片需小于 4MB"); return; }
    const fr = new FileReader();
    fr.onload = () => {
      api.uploadAvatar(fr.result).then((r) => {
        if (r.ok) {
          state.me.avatar = r.avatar;
          render.renderProfile(state.me);
          toast("头像已更新");
        }
      });
    };
    fr.readAsDataURL(file);
  }

  function saveMe() {
    api.updateMe({
      nickname: document.getElementById("nicknameInput").value.trim(),
      signature: document.getElementById("signatureInput").value.trim(),
    }).then((r) => {
      if (r.ok) {
        state.me = r.me;
        render.renderProfile(state.me);
        toast("资料已保存");
      }
    });
  }

  // ---- 打卡 ----
  function submitCheckin(img, lat, lon, poiId, caption) {
    const fr = new FileReader();
    fr.onload = () => {
      api.addCheckin({ img: fr.result, lat, lon, poi_id: poiId, caption }).then((r) => {
        if (r.ok) {
          toast("打卡已记录");
          document.getElementById("checkinFile").value = "";
          document.getElementById("checkinCaption").value = "";
          document.getElementById("checkinImgPrev").hidden = true;
          document.getElementById("checkinImgPh").hidden = false;
          pendingCheckinPoi = "";
          loadMe();
        } else {
          toast(r.error || "打卡失败");
        }
      });
    };
    fr.readAsDataURL(img);
  }

  function onCheckinSubmit(e) {
    e.preventDefault();
    const img = document.getElementById("checkinFile").files[0];
    if (!img) { toast("请先添加一张照片"); return; }
    if (img.size > 4 * 1024 * 1024) { toast("图片需小于 4MB"); return; }
    const poiId = document.getElementById("checkinPoi").value;
    const caption = document.getElementById("checkinCaption").value.trim();
    const poi = state.pois.find((p) => p.id === poiId);
    if (poi) {
      submitCheckin(img, poi.lat, poi.lon, poiId, caption);
    } else if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => submitCheckin(img, pos.coords.latitude, pos.coords.longitude, "", caption),
        () => toast("无法获取位置，请关联一个景点后打卡"),
        { timeout: 8000, maximumAge: 30000 }
      );
    } else {
      toast("无法获取位置，请关联一个景点后打卡");
    }
  }

  // ---- 路线记录（实时 GPS，失败降级点选）----
  let recording = false;
  let clickMode = false;
  let routePoints = [];
  let routeWatch = null;
  let routeStartSec = 0;

  function setRouteStatus(msg) {
    const el = document.getElementById("routeStatus");
    if (el) el.textContent = msg;
  }

  function addRoutePoint(pt) {
    routePoints.push(pt);
    map.drawRoute(routePoints);
    setRouteStatus("已记录 " + routePoints.length + " 个采样点" + (clickMode ? "（点选模式）" : ""));
  }

  function enableClickMode() {
    clickMode = true;
    if (routeWatch != null) { navigator.geolocation.clearWatch(routeWatch); routeWatch = null; }
    map.setClickMap((lat, lon) => { if (recording && clickMode) addRoutePoint([lat, lon]); });
    setRouteStatus("GPS 不可用，已切换点选模式：点击地图落点");
  }

  function startRecord() {
    recording = true;
    clickMode = false;
    routePoints = [];
    routeStartSec = Math.floor(Date.now() / 1000);
    map.clearRoute();
    document.getElementById("recordStart").disabled = true;
    document.getElementById("recordStop").disabled = false;
    setRouteStatus("正在记录…（GPS 定位中）");
    if (navigator.geolocation) {
      routeWatch = navigator.geolocation.watchPosition(
        (pos) => { if (recording) addRoutePoint([pos.coords.latitude, pos.coords.longitude]); },
        () => { if (recording) enableClickMode(); },
        { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 }
      );
    } else {
      enableClickMode();
    }
  }

  function stopRecord() {
    if (routeWatch != null) { navigator.geolocation.clearWatch(routeWatch); routeWatch = null; }
    recording = false;
    clickMode = false;
    map.setClickMap(null);
    document.getElementById("recordStart").disabled = false;
    document.getElementById("recordStop").disabled = true;
    if (routePoints.length < 2) {
      map.clearRoute();
      setRouteStatus("采样点太少，未保存。可再试一次。");
      return;
    }
    const title = "我的足迹 · " + todayText();
    api.addRoute({
      title,
      start: routeStartSec,
      end: Math.floor(Date.now() / 1000),
      points: routePoints,
    }).then((r) => {
      if (r.ok) {
        toast("路线已保存");
        map.clearRoute();
        setRouteStatus("路线已保存，去「我的」页查看。");
        loadMe();
      } else {
        setRouteStatus(r.error || "保存失败");
      }
    });
  }

  // ---- 个人中心事件委托（打卡/路线列表）----
  function onMeClick(e) {
    const delCk = e.target.closest("[data-del-checkin]");
    if (delCk) {
      api.deleteCheckin(delCk.getAttribute("data-del-checkin")).then((r) => {
        if (r.ok) { toast("打卡已删除"); loadMe(); }
      });
      return;
    }
    const delR = e.target.closest("[data-del-route]");
    if (delR) {
      api.deleteRoute(delR.getAttribute("data-del-route")).then((r) => {
        if (r.ok) { toast("路线已删除"); loadMe(); }
      });
      return;
    }
    const viewR = e.target.closest("[data-view-route]");
    if (viewR) {
      const r = state.routes.find((x) => x.id === viewR.getAttribute("data-view-route"));
      if (r) {
        showView("map");
        map.drawRoute(r.points);
        toast("已在地图画出了「" + (r.title || "我的足迹") + "」");
      }
    }
  }

  function todayText() {
    const d = new Date();
    return (d.getMonth() + 1) + "月" + d.getDate() + "日";
  }

  // ---- 启动 ----
  function boot() {
    // 导航
    document.querySelectorAll(".nav-link, [data-nav]").forEach((el) => {
      el.addEventListener("click", (e) => {
        const nav = el.getAttribute("data-nav");
        if (nav && VIEWS.indexOf(nav) !== -1) { e.preventDefault(); showView(nav); }
      });
    });
    document.getElementById("profileBtn").addEventListener("click", () => showView("me"));

    // 地图侧栏委托（收藏 / 打卡）
    document.getElementById("sidePanel").addEventListener("click", onSideClick);
    document.getElementById("mbtiStrip").addEventListener("click", (e) => {
      const card = e.target.closest("[data-mbti-poi]");
      if (card) {
        showView("map");
        selectPoi(card.getAttribute("data-mbti-poi"));
      }
    });

    // 行程预算
    document.querySelectorAll(".chip[data-budget]").forEach((chip) => {
      chip.addEventListener("click", () => {
        document.querySelectorAll(".chip[data-budget]").forEach((c) => c.classList.remove("is-active"));
        chip.classList.add("is-active");
        currentBudget = chip.getAttribute("data-budget");
      });
    });
    document.getElementById("generateBtn").addEventListener("click", generateItinerary);
    document.getElementById("savePlanBtn").addEventListener("click", savePlan);

    // 个人中心：资料
    const avatarBox = document.getElementById("avatarBox");
    const avatarFile = document.getElementById("avatarFile");
    avatarBox.addEventListener("click", () => avatarFile.click());
    avatarFile.addEventListener("change", () => uploadAvatar(avatarFile.files[0]));
    document.getElementById("saveMeBtn").addEventListener("click", saveMe);

    // MBTI
    document.getElementById("mbtiBadge").addEventListener("click", openMbtiModal);
    document.getElementById("mbtiCancel").addEventListener("click", closeMbtiModal);
    document.getElementById("mbtiModal").addEventListener("click", (e) => {
      if (e.target === e.currentTarget) closeMbtiModal();
    });
    document.getElementById("mbtiSave").addEventListener("click", saveMbti);

    // 打卡
    const checkinFile = document.getElementById("checkinFile");
    checkinFile.addEventListener("change", () => {
      const f = checkinFile.files[0];
      const prev = document.getElementById("checkinImgPrev");
      const ph = document.getElementById("checkinImgPh");
      if (!f) return;
      const fr = new FileReader();
      fr.onload = () => {
        prev.src = fr.result;
        prev.hidden = false;
        ph.hidden = true;
      };
      fr.readAsDataURL(f);
    });
    document.getElementById("checkinForm").addEventListener("submit", onCheckinSubmit);
    document.getElementById("checkinList").addEventListener("click", onMeClick);

    // 路线
    document.getElementById("recordStart").addEventListener("click", startRecord);
    document.getElementById("recordStop").addEventListener("click", stopRecord);
    document.getElementById("routeList").addEventListener("click", onMeClick);
    // 起点选择 / 规划
    document.getElementById("setStart").addEventListener("click", enterPickStart);
    document.getElementById("useGpsStart").addEventListener("click", useGpsStart);
    // MBTI 专属推荐卡（个人中心）：点击卡片去地图看对应景点
    document.getElementById("mbtiRecsMe").addEventListener("click", (e) => {
      const card = e.target.closest("[data-mbti-poi]");
      if (card) {
        showView("map");
        selectPoi(card.getAttribute("data-mbti-poi"));
      }
    });

    // 拉取数据
    loadProfile();
    loadMe();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(window);
