/* ClearMap · app.js —— 引导启动 + 视图切换 + 事件编排 */
(function () {
  "use strict";

  const { api, AXES, state, toast, render, map } = window.ClearMap;

  let currentItinerary = null;
  let currentBudget = "full";
  let pendingCheckinPoi = "";
  let startPoint = null;   // {lat, lon, name}

  /* 当前城市（地图底图 / POI / 行程均随之切换） */
  let ACTIVE_CITY = "changsha";
  function cityActive() { return ACTIVE_CITY; }
  function setActiveCity(c) { ACTIVE_CITY = c; }

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
  const VIEWS = ["home", "map", "plan", "discover", "me"];
  function showView(name) {
    document.body.dataset.view = name;
    VIEWS.forEach((v) => {
      const sec = document.getElementById("view-" + v);
      if (sec) sec.hidden = v !== name;
    });
    document.querySelectorAll(".tab-link").forEach((b) => {
      b.classList.toggle("is-active", b.getAttribute("data-nav") === name);
    });
    if (name === "plan") { renderCheckinSelect(); loadArchive(); }
    if (name === "discover") { loadFeed(); }
    if (name === "me") { renderCheckinSelect(); refreshServerState(); loadMyEssays(); }
    if (name === "home") { refreshAuthUi(); }
  }

  // ---- 首页：登录状态展示 ----
  function refreshHomeAuth() {
    const el = document.getElementById("homeAccount");
    const init = document.getElementById("homeInit");
    if (!el) return;
    const t = api.token;
    if (t) {
      api.authMe().then((r) => {
        if (r.ok && r.me && r.me.signed_in) {
          el.textContent = "已登录 · " + maskedPhone(r.me.phone || "");
          el.classList.add("is-in");
          el.title = "已登录，点此进入个人中心";
        } else {
          el.textContent = "游客 · 点击登录";
          el.classList.remove("is-in");
        }
      });
    } else {
      el.textContent = "游客 · 点击登录";
      el.classList.remove("is-in");
    }
    if (init) init.hidden = true;
  }

  // ---- 个人中心：服务器 / 后端连接设置 ----
  function refreshServerState() {
    const inp = document.getElementById("serverBase");
    if (inp) inp.value = api.serverBase();
    testServer();
  }
  let serverChecking = false;
  function testServer() {
    const st = document.getElementById("serverState");
    if (!st) return;
    if (serverChecking) return;
    serverChecking = true;
    st.textContent = "检测中…";
    st.classList.remove("is-err", "is-ok");
    api.health().then((r) => {
      serverChecking = false;
      const ok = r && r.ok === true;
      st.textContent = ok ? "已连接" : "未连接(检查笔记本/路由器)";
      st.classList.toggle("is-ok", !!ok);
      st.classList.toggle("is-err", !ok);
      if (!ok) toast("后端未连通，地图仍可离线使用");
    }).catch(() => {
      serverChecking = false;
      st.textContent = "未连接(检查笔记本/路由器)";
      st.classList.add("is-err");
    });
  }

  // ---- 地图 ----
  function selectPoi(id) {
    state.selected = id;
    const poi = state.pois.find((p) => p.id === id);
    renderMap();
    openPoiPop(poi);
  }

  // 选点详情底部弹层：点击红绿点时在这里弹出景点介绍
  function openPoiPop(poi) {
    const pop = document.getElementById("poiPop");
    const body = document.getElementById("poiPopBody");
    if (!pop || !body) return;
    if (!poi) { pop.hidden = true; return; }
    render.renderSide(body, poi);
    pop.hidden = false;
  }
  function closePoiPop() {
    const pop = document.getElementById("poiPop");
    if (pop) pop.hidden = true;
  }

  function renderMap() {
    map.renderMap(document.getElementById("mapPanel"), state.pois, state.selected, selectPoi);
  }

  // ---- 事件委托：选点弹层（收藏 + 打卡 + 规划）----
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
      showView("plan");
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
    if (document.getElementById("poiPop").hidden) return;
    const poi = state.pois.find((p) => p.id === state.selected);
    openPoiPop(poi);
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
    api.pois(cityActive()).then((r) => {
      if (r.ok) {
        state.pois = r.pois || [];
        applyPois();
      } else {
        applyBundledPois();
      }
    }).catch(applyBundledPois);
  }

  /* 离线兜底：APK 尚无后端时，从随包内置的 pois-<city>.json 读取景点 */
  function applyBundledPois() {
    const file = "pois-" + cityActive() + ".json";
    fetch(file, { cache: "no-store" })
      .then((res) => res.json())
      .then((j) => {
        state.pois = Array.isArray(j) ? j : (j.pois || []);
        applyPois();
      })
      .catch(function () { /* 无声降级：无数据则保持空态 */ });
  }

  function applyPois() {
    renderMap();
    renderSideNow();
    renderCheckinSelect();
  }

  // ---- 行程 ----
  function generateItinerary() {
    api.itinerary(currentBudget, cityActive()).then((r) => {
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
      state.essays = r.essays || [];
      render.renderProfile(state.me);
      render.renderCheckins(document.getElementById("checkinList"), state.checkins);
      render.renderRoutes(document.getElementById("routeList"), state.routes);
      renderMyEssays();
      renderCheckinSelect();
      loadMbtiRecs();
      map.drawCheckins(state.checkins);
    });
  }

  // 读取个人随笔锁存（避免每次切视图重复拉接口）
  let essaysLoaded = false;
  function loadMyEssays() {
    if (essaysLoaded && state.essays.length) { renderMyEssays(); return; }
    api.me().then((r) => {
      if (!r.ok) return;
      state.essays = r.essays || [];
      essaysLoaded = true;
      renderMyEssays();
      loadArchive();
    });
  }
  function renderMyEssays() {
    render.renderMyEssays(document.getElementById("myEssaysList"), state.essays || []);
  }

  // 行程档案：打卡景点 + 足迹路线（切到「行程」视图时刷新）
  let archiveLoaded = false;
  function loadArchive() {
    if (archiveLoaded) return;
    api.me().then((r) => {
      if (!r.ok) return;
      state.checkins = r.checkins || [];
      state.routes = r.routes || [];
      archiveLoaded = true;
      render.renderCheckins(document.getElementById("checkinList"), state.checkins);
      render.renderRoutes(document.getElementById("routeList"), state.routes);
      map.drawCheckins(state.checkins);
    });
  }

  // 发现流：别人的旅游随笔
  function loadFeed() {
    api.feed(60).then((r) => {
      if (r.ok) {
        state.feed = r.essays || [];
        render.renderFeed(document.getElementById("feedList"), state.feed, state.me.id);
      }
    });
  }

  function renderCheckinSelect() {
    render.renderCheckinSelect(document.getElementById("checkinPoi"), state.pois, pendingCheckinPoi);
  }

  function loadMbtiRecs() {
    api.mbtiRecs(cityActive()).then((r) => {
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
    const delE = e.target.closest("[data-del-essay]");
    if (delE) {
      const id = delE.getAttribute("data-del-essay");
      api.deleteEssay(id).then((r) => {
        if (r.ok) {
          toast("随笔已删除");
          state.essays = state.essays.filter((x) => x.id !== id);
          state.feed = state.feed.filter((x) => x.id !== id);
          renderMyEssays();
          const fl = document.getElementById("feedList");
          if (fl) render.renderFeed(fl, state.feed, state.me.id);
        }
      });
    }
  }

  // ---- 随笔发布（文字 + 可选相册配图，最多 6 张）----
  const ESSAY_IMG_MAX = 6;
  const ESSAY_IMG_MAX_BYTES = 4 * 1024 * 1024;
  let essayImgs = [];   // 待发布的图片 dataURL
  function addEssayImgs(files) {
    const box = document.getElementById("essayImgs");
    for (const f of files) {
      if (essayImgs.length >= ESSAY_IMG_MAX) { toast("最多上传 " + ESSAY_IMG_MAX + " 张图"); break; }
      if (!f.type || f.type.indexOf("image/") !== 0) { toast("只能选图片"); continue; }
      if (f.size > ESSAY_IMG_MAX_BYTES) { toast("单张图片需小于 4MB"); continue; }
      const fr = new FileReader();
      fr.onload = () => {
        essayImgs.push(fr.result);
        renderEssayImgs();
      };
      fr.readAsDataURL(f);
      void box;
    }
  }
  function renderEssayImgs() {
    const box = document.getElementById("essayImgs");
    box.innerHTML = essayImgs.map((src, i) =>
      '<span class="es-preview"><img src="' + src + '" alt="待发配图">' +
      '<button class="es-preview-del" data-es-del="' + i + '" aria-label="移除该图">×</button></span>').join("");
    box.scrollLeft = box.scrollWidth;
  }
  function publishEssay() {
    const text = document.getElementById("essayText").value.trim();
    if (!text) { toast("随笔内容不能为空"); return; }
    if (!api.token) { toast("请先登录后再发布随笔"); showView("me"); openAuthModal(); return; }
    api.publishEssay({ text, imgs: essayImgs }).then((r) => {
      if (r.ok) {
        toast("已发布，快去「发现」围观");
        document.getElementById("essayText").value = "";
        essayImgs = [];
        renderEssayImgs();
        essaysLoaded = false;
        state.feed = [];
        loadMyEssays();
      } else {
        toast(r.error || "发布失败");
      }
    });
    void text;
  }

  function todayText() {
    const d = new Date();
    return (d.getMonth() + 1) + "月" + d.getDate() + "日";
  }

  // ---- 登录 / 注册 ----
  const authBtn = () => document.getElementById("authBtn");
  function maskedPhone(phone) {
    const d = String(phone || "").replace(/\D/g, "");
    if (d.length >= 8) return d.slice(0, 3) + "****" + d.slice(-4);
    return phone || "";
  }
  function refreshAuthUi() {
    refreshHomeAuth();
    const t = api.token;
    const el = authBtn();
    if (!el) return;
    if (t) {
      api.authMe().then((r) => {
        if (r.ok && r.me && r.me.signed_in) {
          state.me.phone = r.me.phone || state.me.phone;
          el.textContent = maskedPhone(r.me.phone || state.me.phone) || (state.me.nickname || "我的账号");
          el.classList.add("is-in");
          el.title = "已登录 · 点击退出";
        } else {
          el.textContent = "登录";
          el.classList.remove("is-in");
        }
      });
    } else {
      el.textContent = "登录";
      el.classList.remove("is-in");
    }
  }
  function openAuthModal() {
    document.getElementById("authError").hidden = true;
    document.getElementById("authDev").hidden = true;
    document.getElementById("authModal").hidden = false;
    const phone = document.getElementById("authPhone");
    if (phone) phone.focus();
  }
  function closeAuthModal() {
    document.getElementById("authModal").hidden = true;
  }
  function setAuthErr(msg) {
    const er = document.getElementById("authError");
    if (msg) { er.textContent = msg; er.hidden = false; }
    else { er.hidden = true; }
  }
  let codeTimer = null;
  function startCodeCountdown(sec) {
    const btn = document.getElementById("authSend");
    if (codeTimer) clearInterval(codeTimer);
    let left = sec;
    btn.disabled = true;
    btn.textContent = left + "s";
    codeTimer = setInterval(() => {
      left -= 1;
      if (left <= 0) { clearInterval(codeTimer); codeTimer = null; btn.disabled = false; btn.textContent = "获取验证码"; return; }
      btn.textContent = left + "s";
    }, 1000);
  }
  function sendCode() {
    const phone = document.getElementById("authPhone").value.trim();
    if (!phone) { toast("请先输入手机号"); return; }
    setAuthErr(null);
    api.sms(phone).then((r) => {
      if (r.ok) {
        toast(r.msg || "验证码已发送");
        if (r.dev_code) {
          const dv = document.getElementById("authDev");
          dv.textContent = "调试模式验证码：" + r.dev_code;
          dv.hidden = false;
          document.getElementById("authCode").value = r.dev_code;
        }
        startCodeCountdown(60);
      } else {
        setAuthErr(r.error || r.msg || "发送失败");
      }
    });
  }
  function submitAuth() {
    const phone = document.getElementById("authPhone").value.trim();
    const code = document.getElementById("authCode").value.trim();
    if (!phone || !code) { toast("请填写手机号和验证码"); return; }
    setAuthErr(null);
    api.login(phone, code).then((r) => {
      if (!r.ok) { setAuthErr(r.error || "登录失败"); return; }
      api.token = r.session.token;
      localStorage.setItem("clearmap_token", r.session.token);
      state.me.phone = r.session.phone || phone;
      closeAuthModal();
      toast("登录成功" + (r.session.nickname ? "，你好，" + r.session.nickname : ""));
      refreshAuthUi();
      loadProfile();
      loadMe();
    });
  }
  function doLogout() {
    const t = api.token;
    api.logout().then(() => {
      api.token = "";
      localStorage.removeItem("clearmap_token");
      state.me.phone = "";
      toast("已退出登录，数据回到本地游客账号");
      refreshAuthUi();
      loadProfile();
      loadMe();
    }).catch(() => {
      api.token = "";
      localStorage.removeItem("clearmap_token");
      state.me.phone = "";
    });
  }
  function onAuthBtnClick() {
    if (api.token) doLogout();
    else openAuthModal();
  }

  // ---- 启动 ----
  function boot() {
    // 导航
    document.querySelectorAll("[data-nav]").forEach((el) => {
      el.addEventListener("click", (e) => {
        const nav = el.getAttribute("data-nav");
        if (nav && VIEWS.indexOf(nav) !== -1) { e.preventDefault(); showView(nav); }
      });
    });

    // 首页：进入地图 / 登录状态 / 回首页 logo
    const homeEnter = document.getElementById("homeEnter");
    if (homeEnter) homeEnter.addEventListener("click", () => showView("map"));
    const homeAccount = document.getElementById("homeAccount");
    if (homeAccount) homeAccount.addEventListener("click", () => {
      if (api.token) showView("me");
      else openAuthModal();
    });
    const brandHome = document.getElementById("brandHome");
    if (brandHome) brandHome.addEventListener("click", () => showView("home"));

    // 服务器 / 后端连接设置
    document.getElementById("serverSave").addEventListener("click", () => {
      const inp = document.getElementById("serverBase");
      api.setServerBase(inp.value);
      toast("地址已保存，正在重连…");
      loadProfile();
      loadMe();
      refreshAffinities();
      setTimeout(() => location.reload(), 600);
    });
    document.getElementById("serverReset").addEventListener("click", () => {
      api.setServerBase("");
      toast("已恢复同源地址，正在重连…");
      setTimeout(() => location.reload(), 600);
    });
    document.getElementById("serverBase").addEventListener("keydown", (e) => {
      if (e.key === "Enter") document.getElementById("serverSave").click();
    });

    // 登录 / 注册
    authBtn().addEventListener("click", onAuthBtnClick);
    document.getElementById("authSend").addEventListener("click", sendCode);
    document.getElementById("authSubmit").addEventListener("click", submitAuth);
    document.getElementById("authCancel").addEventListener("click", closeAuthModal);
    document.getElementById("authModal").addEventListener("click", (e) => {
      if (e.target === e.currentTarget) closeAuthModal();
    });
    document.getElementById("authCode").addEventListener("keydown", (e) => {
      if (e.key === "Enter") submitAuth();
    });
    document.getElementById("authPhone").addEventListener("keydown", (e) => {
      if (e.key === "Enter") sendCode();
    });

    // 选点弹层委托（收藏 / 打卡 / 规划）+ 关闭
    document.getElementById("poiPop").addEventListener("click", onSideClick);
    document.getElementById("poiPopClose").addEventListener("click", closePoiPop);
    document.getElementById("poiPop").addEventListener("click", (e) => {
      if (e.target === e.currentTarget) closePoiPop();
    });
    document.getElementById("mbtiStrip").addEventListener("click", (e) => {
      const card = e.target.closest("[data-mbti-poi]");
      if (card) {
        showView("map");
        selectPoi(card.getAttribute("data-mbti-poi"));
      }
    });

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
    // 行程打卡 / 路线 / 随笔的事件委托
    document.getElementById("checkinForm").addEventListener("submit", onCheckinSubmit);
    document.getElementById("checkinList").addEventListener("click", onMeClick);
    document.getElementById("routeList").addEventListener("click", onMeClick);
    document.getElementById("feedList").addEventListener("click", onMeClick);
    document.getElementById("myEssaysList").addEventListener("click", onMeClick);

    // 行程页「去地图记录足迹」
    document.getElementById("goRecord").addEventListener("click", () => showView("map"));

    // 随笔发布（文字 + 可选相册配图，走系统相册选择器）
    const essayFile = document.getElementById("essayFile");
    document.getElementById("essayAddImg").addEventListener("click", () => essayFile.click());
    essayFile.addEventListener("change", () => {
      addEssayImgs(essayFile.files);
      essayFile.value = "";
    });
    document.getElementById("essayPublish").addEventListener("click", publishEssay);
    document.getElementById("essayImgs").addEventListener("click", (e) => {
      const del = e.target.closest("[data-es-del]");
      if (del) { essayImgs.splice(Number(del.getAttribute("data-es-del")), 1); renderEssayImgs(); }
    });

    // 路线
    document.getElementById("recordStart").addEventListener("click", startRecord);
    document.getElementById("recordStop").addEventListener("click", stopRecord);
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

    // 切换城市底图
    const citySel = document.getElementById("mapCity");
    if (citySel) {
      citySel.value = map.getCity();
      citySel.addEventListener("change", () => {
        const c = citySel.value;
        setActiveCity(c);
        map.setCity(c);
        state.selected = null;
        closePoiPop();
        refreshAffinities();          // 各城市都加载对应 POI（接口 / 离线包）
        const cap = {
          changsha: "从河心洲与千年书院，到夜色不熄的街巷 —— 点一粒光，看它的模样。",
          shanghai: "外滩灯火与弄堂晨光之间 —— 摩登与市井，都在这城漫游。",
          beijing:  "皇城根下的胡同与高楼 —— 千年古都，任你穿行。",
        };
        const capEl = document.getElementById("mapCaption");
        if (capEl && cap[c]) capEl.textContent = cap[c];
        const kickEl = document.getElementById("cityKicker");
        const kicker = {
          changsha: "长沙 · 湘江边的山水之城",
          shanghai: "上海 · 黄浦江畔的摩登之城",
          beijing:  "北京 · 皇城根下的千年古都",
        };
        if (kickEl && kicker[c]) kickEl.textContent = kicker[c];
      });
    }

    // 拉取数据
    showView("home");          // 打开 App 先落在首页，登录状态随之检测
    refreshAuthUi();
    loadProfile();
    loadMe();
    refreshAffinities();   // 无后端也初始化地图（走离线包），避免地图空白
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(window);
