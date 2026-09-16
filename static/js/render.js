/* ClearMap · render.js —— 各类视图 DOM 的轻量渲染 */
(function () {
  "use strict";

  const { AXES, state, MBTI_NAMES } = window.ClearMap;

  function favBtn(id, fav) {
    const isFav = Array.isArray(state.favorites) && state.favorites.indexOf(id) !== -1;
    return '<button class="btn-fav' + (isFav ? " is-saved" : "") + '" data-fav="' + id + '">' +
      (isFav ? "已收藏" : "收藏") + "</button>";
  }

  function styleChips(poi) {
    return (poi.style || []).map((s) => '<span class="style-chip">' + escapeHTML(s) + "</span>").join("");
  }

  // 纸飞机图标（景点名旁的“前往规划”按钮）
  function planeBtn(id) {
    return '<button class="poi-plane" data-route-poi="' + escapeHTML(id) +
      '" title="规划前往此景点" aria-label="规划前往此景点">' +
      '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">' +
      '<path d="M2 11l19-7-5.5 17-4.6-6.4L8 16.6 6.6 9.3 2 11z"/></svg></button>';
  }

  // —— 侧栏：单个 POI 详情（图集 / 开放信息 / 门票 / 纸飞机线路）——
  function renderSide(panel, poi) {
    if (!poi) {
      panel.innerHTML = '<div class="side-placeholder">从地图上点一粒光，\n看它的名字与来历。</div>';
      return;
    }
    const imgs = poi.images || [];
    const first = imgs.length ? imgs[0].src : "";
    const dots = imgs.map((_, i) => '<i class="gal-dot' + (i === 0 ? " is-on" : "") + '" data-i="' + i + '"></i>').join("");
    const styles = styleChips(poi);
    const hours = poi.hours || {};
    const mbtiLine = (poi.mbti_affinity != null)
      ? '<span>MBTI 契合 <b>' + Number(poi.mbti_affinity).toFixed(1) + " / 5</b></span>" : "";
    panel.innerHTML =
      '<p class="side-district">' + escapeHTML(poi.district) + (poi.type ? " · " + (AXES[poi.type] || poi.type) : "") + "</p>" +
      '<div class="side-name-row"><h3 class="side-name">' + escapeHTML(poi.name) + "</h3>" + planeBtn(poi.id) + "</div>" +
      (styles ? '<div class="side-styles">' + styles + "</div>" : "") +
      (first ? '<div class="side-gallery"><img class="gal-img" src="' + escapeHTML(first) +
        '" alt="' + escapeHTML(poi.name) + '" loading="lazy">' +
        (imgs.length > 1 ? '<button class="gal-btn gal-prev" aria-label="上一张">‹</button>' +
          '<button class="gal-btn gal-next" aria-label="下一张">›</button>' +
          '<div class="gal-dots">' + dots + "</div>" : "") + "</div>" : "") +
      '<p class="side-desc">' + escapeHTML(poi.desc || "") + "</p>" +
      '<div class="side-tags">' + (poi.tags || []).map((t) => '<span class="tag">' + escapeHTML(t) + "</span>").join("") + "</div>" +
      '<div class="side-meta"><span>停留 <b>' + poi.duration_min + " 分钟</b></span>" +
      '<span>契合度 <b>' + Number(poi.affinity).toFixed(1) + " / 5</b></span>" +
      mbtiLine +
      '<span>门票 <b>' + escapeHTML(poi.ticket || "免费") + "</b></span>" +
      (hours.open ? '<span>开放 <b>' + escapeHTML(hours.open) + " — " + escapeHTML(hours.close) + "</b></span>" : "") +
      (hours.note ? '<span class="side-hours-note">' + escapeHTML(hours.note) + "</span>" : "") + "</div>" +
      '<div class="side-actions">' + favBtn(poi.id, false) +
      '<button class="btn-ghost btn-sm" data-checkin-poi="' + escapeHTML(poi.id) + '">在此打卡</button></div>' +
      '<div class="side-route" id="sideRoutePanel"></div>';
    bindGallery(panel, imgs);
  }

  // 图集翻页绑定（每次 renderSide 重建内部状态）
  function bindGallery(panel, imgs) {
    if (!imgs || imgs.length < 2) return;
    let idx = 0;
    const img = panel.querySelector(".gal-img");
    const dots = panel.querySelectorAll(".gal-dot");
    function show(i) {
      idx = (i + imgs.length) % imgs.length;
      img.src = imgs[idx].src;
      dots.forEach((d, k) => d.classList.toggle("is-on", k === idx));
    }
    const prev = panel.querySelector(".gal-prev"), next = panel.querySelector(".gal-next");
    if (prev) prev.addEventListener("click", () => show(idx - 1));
    if (next) next.addEventListener("click", () => show(idx + 1));
  }

  // —— 偏好七轴滑块 ——
  function renderPrefs(panel, profile, onInput) {
    panel.innerHTML = Object.keys(AXES).map((key) => {
      const v = profile[key] == null ? 3 : profile[key];
      return (
        '<div class="pref-row">' +
        '<div><div class="pref-name">' + AXES[key] + "</div>" +
        '<div class="pref-meta">' + prefHint(key) + "</div></div>" +
        '<div class="pref-control"><input type="range" min="0" max="5" step="1" value="' + v +
        '" data-axis="' + key + '" aria-label="' + AXES[key] + '">' +
        '<span class="pref-value" data-v="' + key + '">' + v + "</span></div>" +
        "</div>"
      );
    }).join("");

    panel.querySelectorAll('input[type="range"]').forEach((inp) => {
      inp.addEventListener("input", () => {
        const key = inp.getAttribute("data-axis");
        const v = Number(inp.value);
        state.profile[key] = v;
        const label = panel.querySelector('[data-v="' + key + '"]');
        if (label) label.textContent = v;
        if (onInput) onInput(key, v);
      });
    });
  }

  // —— 行程 ——
  function renderItinerary(panel, itinerary) {
    if (!itinerary || !itinerary.items || itinerary.items.length === 0) {
      panel.innerHTML = '<div class="plan-empty">这一档预算里没装下想去的地方，换一档试试。</div>';
      return;
    }
    const rows = itinerary.items.map((it, i) => {
      return (
        '<div class="route-stop">' +
        '<span class="route-num">' + String(i + 1).padStart(2, "0") + "</span>" +
        "<div><p class=\"route-name\">" + escapeHTML(it.poi.name) + "</p>" +
        '<div class="route-foot"><span class="route-rank"><b>契合度 ' + Number(it.affinity).toFixed(1) + "</b></span>" +
        " &nbsp;·&nbsp; " + escapeHTML(it.poi.district) +
        " · " + it.poi.duration_min + " 分钟</div></div>" +
        '<span class="route-affinity">' + Number(it.affinity).toFixed(1) + "</span>" +
        "</div>"
      );
    }).join("");
    const total = itinerary.budget_minutes;
    panel.innerHTML =
      '<div class="route-legend">按顺序 · 全程约 ' + total + " 分钟</div>" + rows;
  }

  function renderSaved(listEl, plans) {
    if (!plans || plans.length === 0) {
      listEl.innerHTML = '<div class="saved-none">还没有收藏行程。</div>';
      return;
    }
    const lines = plans.slice().reverse().map((pl) => {
      const n = (pl.items || []).length;
      const names = (pl.items || []).slice(0, 3)
        .map((it) => (it.name || it.id)).join(" → ");
      return '<div class="saved-item"><div><b>' + escapeHTML(pl.title || "我的行程") +
        "</b><div class=\"saved-meta\">" + n + " 站 · " + escapeHTML(names) + "</div></div>" +
        '<div class="saved-meta">' + budgetText(pl.budget) + "</div></div>";
    }).join("");
    listEl.innerHTML = lines;
  }

  // 头像 URL 归一化：云端返回的相对路径加上 API_BASE，绝对路径/本地 data 原样保留
  function avatarUrl(u) {
    if (!u) return "";
    if (/^https?:\/\/|^data:/i.test(u)) return u;
    let base = "";
    try { base = window.ClearMap.api.serverBase() || window.CLEARMAP_API_BASE || ""; } catch (e) { /* 忽略 */ }
    base = String(base).replace(/\/+$/, "");
    return base + (u.charAt(0) === "/" ? u : "/" + u);
  }

  // —— 个人中心：资料 ——
  function renderProfile(me) {
    const avatar = document.getElementById("avatarImg");
    const ph = document.getElementById("avatarPh");
    if (me.avatar) {
      const src = avatarUrl(me.avatar);
      avatar.src = src;
      avatar.hidden = false;
      ph.hidden = true;
      avatar.onerror = () => {             // 图片加载失败时回退到默认剪影，避免损坏框
        if (avatar) { avatar.hidden = true; ph.hidden = false; }
      };
    } else {
      avatar.hidden = true;
      ph.hidden = false;
    }
    document.getElementById("nicknameInput").value = me.nickname || "";
    document.getElementById("signatureInput").value = me.signature || "";
    const badge = document.getElementById("mbtiBadge");
    if (me.mbti) {
      badge.textContent = me.mbti;
      badge.title = "MBTI " + me.mbti + " · " + (me.mbti_name || MBTI_NAMES[me.mbti] || "");
      badge.classList.add("is-set");
    } else {
      badge.textContent = "MBTI";
      badge.title = "选择你的 MBTI 性格";
      badge.classList.remove("is-set");
    }
  }

  // —— 个人中心：MBTI 四维选择器 ——
  const MBTI_DIMS = window.ClearMap.MBTI_DIMS;
  function renderMbtiPicker(container) {
    const picked = {};
    container.innerHTML = MBTI_DIMS.map((dim, di) =>
      '<div class="mbti-dim"><div class="mbti-dim-name">' + dim.key + "</div>" +
      dim.opts.map((o, oi) =>
        '<button type="button" class="mbti-opt" data-dim="' + di + '" data-opt="' + o + '">' +
        dim.label[o] + "</button>").join("") + "</div>").join("");
    const dims = container.querySelectorAll(".mbti-dim");
    container.querySelectorAll(".mbti-opt").forEach((btn) => {
      btn.addEventListener("click", () => {
        const di = btn.getAttribute("data-dim");
        dims[di].querySelectorAll(".mbti-opt").forEach((b) => b.classList.remove("is-on"));
        btn.classList.add("is-on");
        picked[di] = btn.getAttribute("data-opt");
        const code = MBTI_DIMS.map((_, k) => picked[k] || "").join("");
        updateMbtiPreview(code);
      });
    });
    function updateMbtiPreview(code) {
      const preview = document.getElementById("mbtiPreview");
      const save = document.getElementById("mbtiSave");
      if (code.length === 4) {
        const name = MBTI_NAMES[code] || "";
        preview.innerHTML = "<b>" + code + " · " + name + "</b><br>已认证后，地图会按你的性格推荐契合景点。";
        save.disabled = false;
      } else {
        preview.textContent = "已选 " + code.length + " 维，再选 " + (4 - code.length) + " 维完成认证。";
        save.disabled = true;
      }
    }
  }

  // —— 个人中心：打卡列表 ——
  function renderCheckins(listEl, checkins) {
    if (!checkins || checkins.length === 0) {
      listEl.innerHTML = '<div class="me-none">还没有打卡 —— 上传第一张旅行照片吧。</div>';
      return;
    }
    const lines = checkins.slice().reverse().map((c) => {
      const img = c.img ? '<img class="ck-img" src="' + escapeHTML(c.img) + '" alt="打卡照片" loading="lazy">' : "";
      const when = timeText(c.created);
      const poi = c.poi_name ? '<span class="ck-poi">@' + escapeHTML(c.poi_name) + "</span>" : "";
      return '<div class="ck-item">' + img +
        '<div class="ck-body"><div class="ck-cap">' + escapeHTML(c.caption || "无题") + poi + "</div>" +
        '<div class="ck-meta">' + when + "</div></div>" +
        '<button class="icon-del" data-del-checkin="' + escapeHTML(c.id) + '" aria-label="删除打卡">✕</button></div>';
    }).join("");
    listEl.innerHTML = lines;
  }

  // —— 个人中心：路线列表 ——
  function renderRoutes(listEl, routes) {
    if (!routes || routes.length === 0) {
      listEl.innerHTML = '<div class="me-none">还没有路线 —— 去地图页点亮一条吧。</div>';
      return;
    }
    const lines = routes.slice().reverse().map((r) => {
      const km = (r.distance_m / 1000).toFixed(1);
      return '<div class="route-item"><div class="route-item-head"><b>' + escapeHTML(r.title || "我的足迹") + "</b>" +
        '<span class="route-item-meta">' + timeText(r.start) + " · " + r.duration_min + " 分钟 · " + km + " km · " +
        (r.points || []).length + " 点</span></div>" +
        '<div class="route-item-acts">' +
        '<button class="btn-ghost btn-sm" data-view-route="' + escapeHTML(r.id) + '">查看轨迹</button>' +
        '<button class="icon-del" data-del-route="' + escapeHTML(r.id) + '" aria-label="删除路线">✕</button>' +
        "</div></div>";
    }).join("");
    listEl.innerHTML = lines;
  }

  // —— 行程：相册/邮戳卡片（打卡照片卡 与 足迹路线卡 交叉排列）——preview-1.02
  function renderAlbum(listEl, checkins, routes) {
    if ((!checkins || !checkins.length) && (!routes || !routes.length)) {
      listEl.innerHTML = '<div class="me-none">还没有记录 —— 点左上角「开始记录行程」或「加一张打卡」吧。</div>';
      return;
    }
    const ck = (checkins || []).slice().reverse().map(function (c) {
      const img = c.img
        ? '<img class="stamp-photo" src="' + escapeHTML(c.img) + '" alt="打卡照片" loading="lazy">'
        : '<div class="stamp-photo stamp-photo--none">📷</div>';
      const poi = c.poi_name ? '<span class="stamp-poi">@' + escapeHTML(c.poi_name) + "</span>" : "";
      return '<figure class="stamp-card">' + img +
        '<figcaption class="stamp-caption">' + escapeHTML(c.caption || "无题") + "</figcaption>" +
        '<div class="stamp-meta">' + poi + " " + timeText(c.created) + "</div>" +
        '<button class="icon-del" data-del-checkin="' + escapeHTML(c.id) + '" aria-label="删除打卡">✕</button></figure>';
    });
    const rt = (routes || []).slice().reverse().map(function (r) {
      const km = (r.distance_m / 1000).toFixed(1);
      return '<div class="stamp-route">' +
        '<div class="stamp-route-title">' + escapeHTML(r.title || "我的足迹") + "</div>" +
        '<div class="stamp-route-meta">' + timeText(r.start) + " · " + r.duration_min + " 分钟 · " +
        km + " km · " + (r.points || []).length + " 点</div>" +
        '<div class="stamp-route-acts">' +
        '<button class="btn-ghost btn-sm" data-view-route="' + escapeHTML(r.id) + '">查看轨迹</button>' +
        '<button class="icon-del" data-del-route="' + escapeHTML(r.id) + '" aria-label="删除路线">✕</button>' +
        "</div></div>";
    });
    // 交叉排列：照片卡与路线卡交错，拼成一张“相册墙”
    const cells = [];
    let i = 0, j = 0;
    while (i < ck.length || j < rt.length) {
      if (i < ck.length) cells.push(ck[i++]);
      if (j < rt.length) cells.push(rt[j++]);
    }
    listEl.innerHTML = cells.join("");
  }

  // —— 地图页：MBTI 推荐条 ——
  function renderMbtiRecs(strip, recs) {
    if (!recs || !recs.mbti) {
      strip.hidden = true;
      strip.innerHTML = "";
      return;
    }
    const cards = (recs.recommended || []).map((r) =>
      '<button class="mbti-card" data-mbti-poi="' + escapeHTML(r.poi.id) + '">' +
      '<div class="mbti-card-name">' + escapeHTML(r.poi.name) + "</div>" +
      '<div class="mbti-card-meta">' + escapeHTML(r.poi.district) + " · " +
      (r.poi.style || []).map((s) => escapeHTML(s)).join(" / ") + "</div>" +
      '<div class="mbti-card-aff">契合 <b>' + Number(r.mbti_affinity).toFixed(1) + " / 5</b></div>" +
      "</button>").join("");
    strip.hidden = false;
    strip.innerHTML =
      '<div class="mbti-strip-head">' + escapeHTML(recs.mbti) + " · " + escapeHTML(recs.name) +
      ' <span>为你推荐</span></div><div class="mbti-cards">' + cards + "</div>";
  }

  // —— 打卡表单（景点下拉）——
  function renderCheckinSelect(sel, pois, selectedId) {
    if (!sel) return;
    const opts = ['<option value="">自由打卡（不关联景点）</option>'].concat(
      pois.map((p) => '<option value="' + escapeHTML(p.id) + '"' + (p.id === selectedId ? " selected" : "") + ">" +
        escapeHTML(p.name) + " · " + escapeHTML(p.district) + "</option>")
    );
    sel.innerHTML = opts.join("");
  }

  // 段模式中文与颜色
  const MODE_META = {
    walk: { t: "步行", c: "#9a9383" },
    subway: { t: "地铁", c: "#cf4436" },
    bus: { t: "公交", c: "#c99a2e" },
  };

  // —— 侧栏：换乘路线结果 ——
  function renderRoutePlan(panel, result, startName, endName) {
    if (!panel) return;
    if (!result || !result.legs) {
      panel.innerHTML = "";
      return;
    }
    if (!result.ok || !result.legs.length) {
      panel.innerHTML = '<div class="rp-empty">暂无可达路线。</div>';
      return;
    }
    const rows = result.legs.map((L) => {
      const m = MODE_META[L.mode] || MODE_META.walk;
      const nm = L.mode === "subway" ? "地铁" : (L.mode === "bus" ? "公交" : "");
      const line = L.line ? '<span class="rp-line">' + escapeHTML(L.line) + "</span>" : "";
      return '<div class="rp-leg">' +
        '<span class="rp-mode" style="color:' + m.c + '">' + m.t + "</span>" +
        line +
        '<span class="rp-time">' + L.time_min + " 分</span></div>";
    }).join("");
    const fromTxt = startName || "起点";
    const toTxt = endName || "终点";
    panel.innerHTML =
      '<div class="rp-head"><span>路线</span><b>' + fromTxt + " → " + toTxt + "</b>" +
      '<span class="rp-total">约 ' + result.total_min + " 分" +
      (result.transfers ? " · 换乘 " + result.transfers + " 次" : "") + "</span></div>" + rows;
  }

  // —— 个人中心：MBTI 专属推荐卡 ——
  function renderMbtiRecsMe(container, recs) {
    if (!container) return;
    if (!recs || !recs.mbti) {
      container.innerHTML =
        '<div class="mbti-me-empty"><p>还没有性格画像。</p>' +
        '<p class="mbti-me-hint">去上方“个人资料”选一个 MBTI，这里会浮现为你的风景。</p></div>';
      return;
    }
    const cards = (recs.recommended || []).slice(0, 6).map((r) =>
      '<button class="mbti-me-card" data-mbti-poi="' + escapeHTML(r.poi.id) + '">' +
      '<div class="mbti-me-name">' + escapeHTML(r.poi.name) + "</div>" +
      '<div class="mbti-me-meta">' + escapeHTML(r.poi.district) + " · " +
      (r.poi.style || []).map((s) => escapeHTML(s)).join(" / ") + "</div>" +
      '<div class="mbti-me-aff">契合 <b>' + Number(r.mbti_affinity).toFixed(1) + " / 5</b></div>" +
      "</button>").join("");
    container.innerHTML =
      '<div class="mbti-me-cap">' + escapeHTML(recs.mbti) + " · " + escapeHTML(recs.name) +
      " 为你推荐</div><div class=\"mbti-me-cards\">" + cards + "</div>";
  }

  // —— 随笔（我的随笔 / 发现流）preview-1.22 ——
  function renderMyEssays(listEl, essays) {
    if (!essays || essays.length === 0) {
      listEl.innerHTML = '<div class="me-none">还没有随笔 —— 写一段旅途心情吧。</div>';
      return;
    }
    const cards = essays.slice().reverse().map((e) => {
      const imgs = (e.imgs || []).map((src) =>
        '<img class="es-photo" src="' + escapeHTML(avatarUrl(src)) + '" alt="随笔配图" loading="lazy">').join("");
      return '<div class="essay-card">' +
        '<div class="essay-text">' + escapeHTML(e.text) + "</div>" +
        (imgs ? '<div class="essay-photos">' + imgs + "</div>" : "") +
        '<div class="essay-foot"><span>' + timeText(e.created) + "</span>" +
        '<button class="icon-del" data-del-essay="' + escapeHTML(e.id) + '" aria-label="删除随笔">✕</button></div>' +
        "</div>";
    }).join("");
    listEl.innerHTML = cards;
  }

  function renderFeed(listEl, items, myId) {
    if (!items || items.length === 0) {
      listEl.innerHTML = '<div class="me-none">还没有旅志 —— 来「个人」页发布第一篇随笔吧。</div>';
      return;
    }
    const cards = items.map((e) => {
      const mine = e.author_id === myId;
      const av = e.avatar
        ? '<img class="feed-av" src="' + escapeHTML(avatarUrl(e.avatar)) + '" alt="">'
        : '<span class="feed-av feed-av--ph">' + escapeHTML((e.author || "旅").slice(0, 1)) + "</span>";
      const imgs = (e.imgs || []).map((src) =>
        '<img class="es-photo" src="' + escapeHTML(avatarUrl(src)) + '" alt="随笔配图" loading="lazy">').join("");
      return '<article class="feed-card">' +
        '<div class="feed-head">' + av +
        '<div class="feed-author"><b>' + escapeHTML(e.author) + "</b>" +
        '<span class="feed-time">' + timeText(e.created) + "</span></div>" +
        (mine ? '<button class="icon-del" data-del-essay="' + escapeHTML(e.id) + '" aria-label="删除我的随笔">✕</button>' : "") +
        "</div>" +
        '<div class="essay-text">' + escapeHTML(e.text) + "</div>" +
        (imgs ? '<div class="essay-photos">' + imgs + "</div>" : "") +
        "</article>";
    }).join("");
    listEl.innerHTML = cards;
  }

  // —— 工具 ——
  function budgetText(k) {
    return { quick: "半日", full: "全天", relax: "慢游" }[k] || "";
  }
  function prefHint(k) {
    return {
      nature: "山水 · 江畔", culture: "古迹 · 书院", food: "小吃 · 湘菜",
      shopping: "潮牌 · 商圈", nightlife: "夜色 · 街巷", family: "亲子 · 放空", photo: "出片 · 打卡",
    }[k] || "";
  }
  function timeText(ts) {
    if (!ts) return "";
    const d = new Date(ts * 1000);
    return (d.getMonth() + 1) + "月" + d.getDate() + "日 " +
      String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
  }
  function escapeHTML(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  window.ClearMap.render = {
    renderSide, renderPrefs, renderItinerary, renderSaved,
    renderProfile, renderMbtiPicker, renderCheckins, renderRoutes, renderAlbum,
    renderMbtiRecs, renderCheckinSelect, renderRoutePlan, renderMbtiRecsMe,
    renderMyEssays, renderFeed,
  };
})(window);
