/* ClearMap · app.js —— 引导启动 + 视图切换 + 事件编排 */
(function () {
  "use strict";

  const { api, AXES, state, toast, render, map } = window.ClearMap;

  let pendingCheckinPoi = "";

  /* 当前城市（地图底图 / POI / 行程均随之切换） */
  let ACTIVE_CITY = "changsha";
  function cityActive() { return ACTIVE_CITY; }
  function setActiveCity(c) { ACTIVE_CITY = c; }

  function escHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // ---- 纸飞机：规划前往景点的最省时路线（默认从「我的位置」出发）----
  let lastPlanPoi = null;
  function planToPoi(poiId) {
    const poi = state.pois.find((p) => p.id === poiId);
    const routeEl = document.getElementById("sideRoutePanel");
    if (!poi || !routeEl) return;
    if (!navigator.geolocation) {
      routeEl.innerHTML = '<div class="rp-empty">当前环境不支持定位，无法规划起点。</div>';
      return;
    }
    routeEl.innerHTML = '<div class="rp-empty">正在获取您的位置，规划前往「' + escHtml(poi.name) + '」的路线…</div>';
    lastPlanPoi = poiId;
    navigator.geolocation.getCurrentPosition((pos) => {
      const from = { lat: pos.coords.latitude, lon: pos.coords.longitude, name: "我的位置" };
      api.routePlan({ from: from, to: { poi_id: poiId } }).then((r) => {
        if (r.ok) {
          render.renderRoutePlan(routeEl, r, from.name, poi.name);
          map.drawPlan(r.legs);
          toast("已为您规划前往「" + poi.name + "」的路线");
        } else {
          routeEl.innerHTML = '<div class="rp-empty">' + escHtml(r.error || "规划失败") + "</div>";
        }
      });
    }, () => {
      routeEl.innerHTML = '<div class="rp-empty">无法获取位置，路线规划已取消。</div>';
    }, { timeout: 8000, maximumAge: 30000 });
  }

  // ---- 视图切换 ----
  const VIEWS = ["home", "map", "plan", "discover", "me"];
  function showView(name) {
    document.body.dataset.view = name;
    const TAB_VIEWS = ["map", "plan", "discover", "me"];
    VIEWS.forEach((v) => {
      const sec = document.getElementById("view-" + v);
      if (sec) sec.hidden = v !== name;
    });
    // 随笔是子页（不属底部栏），单独收放
    const ev = document.getElementById("view-essay");
    if (ev) ev.hidden = name !== "essay";
    document.querySelectorAll(".tab-link").forEach((b) => {
      const nav = b.getAttribute("data-nav");
      b.classList.toggle("is-active", nav === name && TAB_VIEWS.indexOf(name) !== -1);
    });
    // 切到地图时，若面板刚可见则校正尺寸并复位视野（修复 SVG 底图不显示）
    if (name === "map") map.refreshSize();
    if (name === "plan") {
      renderCheckinSelect(); loadArchive();
      const f = document.getElementById("checkinForm");
      if (f) f.hidden = !pendingCheckinPoi;   // 从景点「在此打卡」进入时自动展开打卡表单
    }
    if (name === "discover") { loadFeed(); }
    if (name === "me") { renderCheckinSelect(); loadMyEssays(); }
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
      pendingCheckinPoi = ck.getAttribute("data-checkin-poi");   // 自动确定打卡景点（preview-1.04）
      closePoiPop();                                             // 收起全屏详情页去行程打卡
      showView("plan");
      toast("已选景点，上传照片即可打卡");
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

  function refreshAffinities() {
    api.pois(cityActive()).then((r) => {
      // ok 但返回空数组也可能（云端未部署 POI 数据）：同样回退到随包内置，保证地图上有景点
      if (r.ok && Array.isArray(r.pois) && r.pois.length) {
        state.pois = r.pois;
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
    const list = (state.pois || []).map(function (p) {
      // 离线/内置 POI 无 affinity：按 scores 平均估算，保证地图上有“红=高契合 / 绿=常规”分层
      if (p.affinity == null) {
        const s = p.scores || {};
        let sum = 0, n = 0;
        for (const k in s) { if (s[k] != null) { sum += Number(s[k]); n++; } }
        p.affinity = n ? sum / n : 1;
      }
      return p;
    });
    state.pois = list;
    renderMap();
    renderSideNow();
    renderCheckinSelect();
  }

  function loadProfile() {
    api.profile().then((r) => {
      if (r.ok) {
        state.profile = r.profile;
        state.favorites = r.favorites || [];
        refreshAffinities();
      }
    });
  }

  // ---- 个人中心 ----
  function setMeTitle(name) {
    const el = document.getElementById("meTitle");
    if (!el) return;
    el.innerHTML = escHtml((name && name.trim()) || "我") + "的<span class=\"lead-em\">旅行志</span>";
  }
  function loadMe() {
    api.me().then((r) => {
      if (!r.ok) return;
      state.me = r.me;
      state.checkins = r.checkins || [];
      state.routes = r.routes || [];
      state.favorites = r.favorites || [];
      state.essays = r.essays || [];
      render.renderProfile(state.me);
      setMeTitle(state.me.nickname);
      render.renderAlbum(document.getElementById("albumGrid"), state.checkins, state.routes);
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
      render.renderAlbum(document.getElementById("albumGrid"), state.checkins, state.routes);
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
    // preview-1.04：打卡地点由地图「在此打卡」自动确定，不再提供景点下拉选择
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
      } else {
        toast(r.error || "MBTI 保存失败");
      }
    }).catch((e) => { console.error("saveMbti fail:", e); toast("MBTI 保存失败：请检查网络"); });
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
        } else {
          toast(r.error || "头像保存失败");
        }
      }).catch((e) => { console.error("avatar fail:", e); toast("头像上传失败：请检查网络"); });
    };
    fr.readAsDataURL(file);
  }

  function saveMe() {
    const nickname = document.getElementById("nicknameInput").value.trim();
    const signature = document.getElementById("signatureInput").value.trim();
    if (!nickname && !signature) { toast("昵称与签名都为空，无需保存"); return; }
    api.updateMe({ nickname, signature }).then((r) => {
      if (r.ok) {
        state.me = r.me;
        render.renderProfile(state.me);
        setMeTitle(state.me.nickname);
        toast("资料已保存");
      } else {
        toast(r.error || "资料保存失败");
      }
    }).catch((e) => { console.error("saveMe fail:", e); toast("资料保存失败：请检查网络"); });
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
          const cf = document.getElementById("checkinForm");
          if (cf) cf.hidden = true;
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
    // 景点由地图「在此打卡」自动确定，无需手动选择（preview-1.04）
    const poiId = pendingCheckinPoi;
    const poi = state.pois.find((p) => p.id === poiId);
    if (!poi) { toast("请先在地图点开景点选择「在此打卡」"); return; }
    const caption = document.getElementById("checkinCaption").value.trim();
    submitCheckin(img, poi.lat, poi.lon, poiId, caption);
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
    const hud = document.getElementById("recHud");
    if (hud) hud.hidden = false;
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
    const hud = document.getElementById("recHud");
    if (hud) hud.hidden = true;
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
    }).catch((e) => { console.error("essay fail:", e); toast("发布失败：请检查网络"); });
    void text;
  }

  function todayText() {
    const d = new Date();
    return (d.getMonth() + 1) + "月" + d.getDate() + "日";
  }

  // ---- 登录 / 注册 ----
  // 强制登录标志：从首页进入地图时若未登录，弹手机验证码登录且不可跳过
  let authForced = false;
  let afterAuthView = null;
  function openAuthModal(forced) {
    authForced = !!forced;
    document.getElementById("authError").hidden = true;
    document.getElementById("authDev").hidden = true;
    document.getElementById("authModal").hidden = false;
    const cancel = document.getElementById("authCancel");
    if (cancel) cancel.style.display = forced ? "none" : "";
    const phone = document.getElementById("authPhone");
    if (phone) phone.focus();
  }
  function closeAuthModal() {
    if (authForced) return;   // 强制登录：未登录前不准跳过
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
    }).catch((e) => {
      setAuthErr("网络异常，无法连接服务器");
      console.error("sendCode fail:", e);
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
      authForced = false;   // 登录成功后可正常关闭弹窗
      closeAuthModal();
      toast("登录成功" + (r.session.nickname ? "，你好，" + r.session.nickname : ""));
      loadProfile();
      loadMe();
      if (afterAuthView) { const v = afterAuthView; afterAuthView = null; showView(v); }
    });
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

    // ---- 进入地图：未登录则强制手机验证码登录（不准跳过）----
    function onEnterHome() {
      if (api.token) { showView("map"); return; }
      afterAuthView = "map";
      openAuthModal(true);   // forced：隐藏取消按钮、禁止点背景关闭
    }
    const homeEnter = document.getElementById("homeEnter");
    if (homeEnter) homeEnter.addEventListener("click", onEnterHome);
    const brandHome = document.getElementById("brandHome");
    if (brandHome) brandHome.addEventListener("click", () => showView("home"));

    // 登录 / 注册
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
    document.getElementById("albumGrid").addEventListener("click", onMeClick);
    document.getElementById("feedList").addEventListener("click", onMeClick);
    document.getElementById("myEssaysList").addEventListener("click", onMeClick);
    // 「加一张打卡」：展开/收起打卡小表单
    const checkinToggleBtn = document.getElementById("checkinToggle");
    if (checkinToggleBtn) checkinToggleBtn.addEventListener("click", () => {
      const f = document.getElementById("checkinForm");
      if (f) f.hidden = !f.hidden;
    });

    // 随笔：从「个人」进入发布页 / 从发布页返回
    document.getElementById("essayGoBtn").addEventListener("click", () => showView("essay"));
    document.getElementById("essayBack").addEventListener("click", () => showView("me"));

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
    document.getElementById("recordStart").addEventListener("click", () => {
      toast("开始记录足迹，去地图沿 GPS 走走吧");
      showView("map");
      startRecord();
    });
    document.getElementById("recordStop").addEventListener("click", stopRecord);
    // MBTI 专属推荐卡（个人中心）：点击卡片去地图看对应景点（preview-1.02 该卡已移除，留空避免启动报错）
    const mbtiRecsBox = document.getElementById("mbtiRecsMe");
    if (mbtiRecsBox) mbtiRecsBox.addEventListener("click", (e) => {
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

    // 定位到我的位置（requirement #4：访问设备位置方便实时定位）
    const locateBtn = document.getElementById("mapLocate");
    if (locateBtn) locateBtn.addEventListener("click", locator);
    function locator() {
      if (!navigator.geolocation) { toast("当前设备不支持定位"); return; }
      toast("正在定位您的设备位置…");
      navigator.geolocation.getCurrentPosition((pos) => {
        map.locate(pos.coords.latitude, pos.coords.longitude);
        toast("已定位到您的当前位置");
      }, () => {
        toast("无法获取位置，请在系统设置中允许定位权限");
      }, { timeout: 8000, maximumAge: 30000 });
    }

    // 拉取数据
    showView("home");          // 打开 App 先落在首页，登录态由「进入地图」时判定
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
