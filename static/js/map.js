/* ClearMap · map.js —— 真实地理 SVG 地图（OSM 数据投影）+ 平移缩放 LOD
   数据源：/map/changsha.json（构建期由 scripts/build_map.py 从 OpenStreetMap 生成）
   坐标系：Web Mercator 世界坐标（整数），落盘数据为"世界坐标 - origin"的局部坐标；
           前端用同一公式从 POI lat/lon 投影，标记与道路自然对齐。 */
(function (win) {
  "use strict";

  // ---- 投影（与 build_map.py 的 WORLD / proj 完全一致）----
  var WORLD = 1 << 23;
  function proj(lon, lat) {
    var x = (lon + 180.0) / 360.0 * WORLD;
    var y;
    var rad = Math.min(85, Math.max(-85, lat)) * Math.PI / 180;
    y = (1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2 * WORLD;
    return [x, y];
  }

  // ---- 状态 ----
  var DATA = null;          // changsha.json 内容
  var ORIGIN = [0, 0];
  var CELL = 512;
  var dataPromise = null;

  var svg = null;           // <svg> 根
  var viewG = null;         // <g class="map-view"> 相机层
  var poiLayer = null;      // 点位层
  var labelLayer = null;    // 片区名/路名/点位名
  var bldLayer = null;      // 建筑层（随缩放填充）
  var routeLayer = null;    // 记录路线层
  var checkinLayer = null;  // 打卡标记层
  var planLayer = null;     // 换乘规划层（纸飞机）

  var view = { x: 0, y: 0, s: 1 };   // screen = local * s + (x,y)
  var W = 800, H = 600;              // 面板像素
  var fitS = 1;                      // 初始适配比例
  var fitBox = null;                 // 适配时的本地矩形 [x0,y0,x1,y1]

  var pois = [];            // 当前 POI 列表
  var selectedId = null;
  var onClick = null;
  var onClickMap = null;    // 点击空白处（无拖拽）回调 (lat, lon)

  var roadBB = {};          // tier -> [ [pathIdx, bbox] ] 惰性 bbox
  var roadCache = {};       // tier -> 解析后的道路数组（含 bbox）

  var MIN_S = 0.04, MAX_S = 90;
  var raf = null;
  var dirty = true;
  var initDone = false;

  // 视口本地矩形
  function visibleRect() {
    var x0 = -view.x / view.s, y0 = -view.y / view.s;
    var x1 = (W - view.x) / view.s, y1 = (H - view.y) / view.s;
    return [x0, y0, x1, y1];
  }

  function fits(rect, pad) {
    pad = pad || 0;
    var v = visibleRect();
    return rect[0] <= v[2] + pad && rect[2] >= v[0] - pad &&
           rect[1] <= v[3] + pad && rect[3] >= v[1] - pad;
  }

  // ---- 数据装载（多城市：/map/<city>.json，按城市缓存）----
  var activeCity = "changsha";
  var dataCache = {};
  var dataPromise = null;

  function loadData() {
    var c = activeCity;
    if (dataCache[c]) return Promise.resolve(dataCache[c]);
    if (dataPromise) return dataPromise;
    dataPromise = fetch("/map/" + c + ".json").then(function (r) {
      if (!r.ok) throw new Error("map data " + r.status);
      return r.json();
    }).then(function (d) {
      dataCache[c] = d;
      DATA = d;
      ORIGIN = d.meta.origin;
      CELL = d.meta.cell || 512;
      fitBox = localBBox();
      return d;
    });
    return dataPromise;
  }

  // 切换城市底图：重新装载 <city>.json 并复位视野
  function setCity(c) {
    activeCity = c;
    dataPromise = null;   // 强制重新装载新城市数据
    initDone = false;     // 走初始化适应
    if (svg) {
      loadData().then(function () {
        fitToBox();
        render();
      }).catch(function (err) { console.error("map load failed:", err); });
    }
  }

  // meta.bbox（w,s,e,n）四角投影 → 局部矩形
  function localBBox() {
    var b = DATA.meta.bbox;
    var corners = [proj(b[0], b[1]), proj(b[2], b[1]), proj(b[0], b[3]), proj(b[2], b[3])];
    var xs = corners.map(function (p) { return p[0] - ORIGIN[0]; });
    var ys = corners.map(function (p) { return p[1] - ORIGIN[1]; });
    return [Math.min.apply(null, xs), Math.min.apply(null, ys),
            Math.max.apply(null, xs), Math.max.apply(null, ys)];
  }

  function poiLocal(p) {
    var w = proj(p.lon, p.lat);
    return [w[0] - ORIGIN[0], w[1] - ORIGIN[1]];
  }

  // Web Mercator 反投影：世界坐标 -> [lat, lon]
  function unproj(x, y) {
    var lon = x / WORLD * 360 - 180;
    var n = Math.PI * (1 - 2 * y / WORLD);
    var lat = 180 / Math.PI * Math.atan(Math.sinh(n));
    return [lat, lon];
  }

  // 屏幕像素 -> [lat, lon]（供点选记录路线使用）
  function screenToLatLon(px, py) {
    var lx = (px - view.x) / view.s;
    var ly = (py - view.y) / view.s;
    return unproj(lx + ORIGIN[0], ly + ORIGIN[1]);
  }

  // ---- 路线 / 打卡图层 ----
  function drawRoute(points, color) {
    if (!routeLayer) return;
    if (!points || points.length < 2) { clearRoute(); return; }
    var d = "";
    for (var i = 0; i < points.length; i++) {
      var pt = points[i];
      var w = proj(pt[1], pt[0]);           // points 为 [lat, lon]
      var lx = w[0] - ORIGIN[0], ly = w[1] - ORIGIN[1];
      d += (i ? "L" : "M") + lx.toFixed(1) + " " + ly.toFixed(1);
    }
    var start = proj(points[0][1], points[0][0]);
    var end = proj(points[points.length - 1][1], points[points.length - 1][0]);
    var rpt = 7 / view.s;
    routeLayer.innerHTML =
      '<path class="route-line" d="' + d + '" vector-effect="non-scaling-stroke"></path>' +
      '<circle class="route-pt route-pt--start" cx="' + (start[0] - ORIGIN[0]).toFixed(1) +
        '" cy="' + (start[1] - ORIGIN[1]).toFixed(1) + '" r="' + rpt.toFixed(2) + '"></circle>' +
      '<circle class="route-pt route-pt--end" cx="' + (end[0] - ORIGIN[0]).toFixed(1) +
        '" cy="' + (end[1] - ORIGIN[1]).toFixed(1) + '" r="' + rpt.toFixed(2) + '"></circle>';
  }

  function clearRoute() {
    if (routeLayer) routeLayer.innerHTML = "";
  }

  function drawCheckins(checkins) {
    if (!checkinLayer) return;
    if (!checkins || !checkins.length) { clearCheckins(); return; }
    var html = "";
    checkins.forEach(function (c) {
      var w = proj(c.lon, c.lat);
      var lx = w[0] - ORIGIN[0], ly = w[1] - ORIGIN[1];
      var r = 10 / view.s;   // 恒定屏幕半径
      html += '<g class="ck-marker" transform="translate(' + lx.toFixed(1) + "," + ly.toFixed(1) + ')">' +
        '<circle class="ck-ring" r="' + r.toFixed(2) + '"></circle>' +
        '<circle class="ck-dot" r="' + (r * 0.5).toFixed(2) + '"></circle>' +
        '<title>' + esc(c.caption || c.poi_name || "打卡") + "</title></g>";
    });
    checkinLayer.innerHTML = html;
  }

  function clearCheckins() {
    if (checkinLayer) checkinLayer.innerHTML = "";
  }

  // 换乘规划层：每条 leg 画一绺配色线（地铁/公交/步行按 mode 区分颜色）
  function drawPlan(legs) {
    if (!planLayer) return;
    if (!legs || !legs.length) { clearPlan(); return; }
    var PLAN_COLORS = { subway: "#1f7a5c", bus: "#c26847", walk: "#9a9383" };
    var pts = legs[0].stops;
    for (var k = 1; k < legs.length; k++) {
      var rest = legs[k].stops;
      if (rest && rest.length) pts = pts.concat(rest.slice(1));
    }
    var d = "";
    for (var i = 0; i < pts.length; i++) {
      var w = proj(pts[i][1], pts[i][0]);
      d += (i ? "L" : "M") + (w[0] - ORIGIN[0]).toFixed(1) + " " + (w[1] - ORIGIN[1]).toFixed(1);
    }
    var layers = "";
    for (var li = 0; li < legs.length; li++) {
      var lg = legs[li];
      var c = PLAN_COLORS[lg.mode] || PLAN_COLORS.walk;
      var p = lg.stops || [];
      var seg = "";
      for (var j = 0; j < p.length; j++) {
        var wp = proj(p[j][1], p[j][0]);
        seg += (j ? "L" : "M") + (wp[0] - ORIGIN[0]).toFixed(1) + " " + (wp[1] - ORIGIN[1]).toFixed(1);
      }
      layers += '<path class="plan-seg plan-seg--' + li + '" d="' + seg +
        '" stroke="' + c + '" vector-effect="non-scaling-stroke"></path>';
    }
    var start = proj(pts[0][1], pts[0][0]);
    var end = proj(pts[pts.length - 1][1], pts[pts.length - 1][0]);
    var rpt = 8 / view.s;
    planLayer.innerHTML =
      '<path class="plan-line" d="' + d + '" vector-effect="non-scaling-stroke"></path>' +
      layers +
      '<circle class="plan-pt plan-pt--start" cx="' + (start[0] - ORIGIN[0]).toFixed(1) +
        '" cy="' + (start[1] - ORIGIN[1]).toFixed(1) + '" r="' + rpt.toFixed(2) + '"></circle>' +
      '<circle class="plan-pt plan-pt--end" cx="' + (end[0] - ORIGIN[0]).toFixed(1) +
        '" cy="' + (end[1] - ORIGIN[1]).toFixed(1) + '" r="' + rpt.toFixed(2) + '"></circle>';
  }

  function clearPlan() {
    if (planLayer) planLayer.innerHTML = "";
  }

  // ---- SVG 结构 ----
  function ensureSvg(container) {
    if (svg && svg.parentNode === container) return;
    // 只移除旧的 svg，保留同级的缩放控件与城市选择器等静态节点
    var prev = container.querySelector("svg");
    if (prev) prev.remove();
    svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "map--frame");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "长沙真实城市地图");

    var rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("width", "100%"); rect.setAttribute("height", "100%");
    rect.setAttribute("class", "map-paper");
    svg.appendChild(rect);

    viewG = document.createElementNS("http://www.w3.org/2000/svg", "g");
    viewG.setAttribute("class", "map-view");
    svg.appendChild(viewG);

    bldLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    bldLayer.setAttribute("class", "bld-layer");
    viewG.appendChild(bldLayer);

    var baseG = document.createElementNS("http://www.w3.org/2000/svg", "g");
    baseG.setAttribute("class", "base-layer");
    viewG.appendChild(baseG);

    var roadG = document.createElementNS("http://www.w3.org/2000/svg", "g");
    roadG.setAttribute("class", "road-layer");
    viewG.appendChild(roadG);

    poiLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    poiLayer.setAttribute("class", "marker-layer");
    viewG.appendChild(poiLayer);

    labelLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    labelLayer.setAttribute("class", "label-layer");
    viewG.appendChild(labelLayer);

    routeLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    routeLayer.setAttribute("class", "route-layer");
    viewG.appendChild(routeLayer);

    checkinLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    checkinLayer.setAttribute("class", "checkin-layer");
    viewG.appendChild(checkinLayer);

    planLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    planLayer.setAttribute("class", "plan-layer");
    viewG.appendChild(planLayer);

    container.appendChild(svg);
    resize();
    if (DATA) renderAll();
  }

  function resize() {
    var r = svg.getBoundingClientRect();
    W = Math.max(120, r.width); H = Math.max(120, r.height);
  }

  function setTransform() {
    viewG.setAttribute("transform", "translate(" + view.x + "," + view.y + ") scale(" + view.s + ")");
    if (viewG) viewG.style.setProperty("--unit", 1 / view.s);
  }

  // —— 相机与内容解耦：平移/缩放先即时应用 transform（GPU 合成，丝滑），
  //    仅当相机跨越阈值时才重建道路/标签/点位的 innerHTML，避免“每帧全量重建”导致的卡顿。
  var riS = 1, riX = 0, riY = 0;   // 上次全量渲染时的相机
  function needFullRender() {
    if (!DATA || !initDone) return true;               // 首帧/切城市强制
    if (Math.abs(view.s / riS - 1) > 0.07) return true;  // 缩放跨 LOD 档位
    if (Math.abs(view.x - riX) + Math.abs(view.y - riY) > 150) return true; // 平移出缓潜带
    return false;
  }
  function render() {
    setTransform();
    if (needFullRender()) renderAll();
  }
  function maybeRender() {
    if (raf) return;
    raf = requestAnimationFrame(function () {
      raf = null;
      render();
    });
  }
  function markDirty() { maybeRender(); }

  // ---- 相机 ----
  function fitToBox() {
    if (!fitBox) return;
    resize();
    var s = Math.min(W / (fitBox[2] - fitBox[0]), H / (fitBox[3] - fitBox[1]));
    fitS = s * 0.92;
    view.s = fitS;
    view.x = (W - (fitBox[0] + fitBox[2]) * fitS) / 2;
    view.y = (H - (fitBox[1] + fitBox[3]) * fitS) / 2;
    markDirty();
  }

  function resetView() { fitToBox(); }

  function zoomAt(px, py, factor) {
    var ns = Math.max(MIN_S, Math.min(MAX_S, view.s * factor));
    var k = ns / view.s;
    view.x = px - (px - view.x) * k;
    view.y = py - (py - view.y) * k;
    view.s = ns;
    setTransform();
    maybeRender();
  }

  function panBy(dx, dy) {
    view.x += dx; view.y += dy;
    setTransform();   // 即时应用相机，丝滑；内容重建由 maybeRender 按需触发
    maybeRender();
  }

  // ---- 道路 bbox 解析（惰性）----
  var numRe = /-?\d+(?:\.\d+)?/g;
  function parseRoads(tier) {
    if (roadCache[tier]) return roadCache[tier];
    var list = (DATA.roads[tier] || []).map(function (r) {
      var nums = r.path.match(numRe);
      var xs = [], ys = [];
      for (var i = 0; i + 1 < nums.length; i += 2) {
        xs.push(+nums[i]); ys.push(+nums[i + 1]);
      }
      var b = [Math.min.apply(null, xs), Math.min.apply(null, ys),
               Math.max.apply(null, xs), Math.max.apply(null, ys)];
      return { r: r, b: b };
    });
    roadCache[tier] = list;
    return list;
  }

  // ---- 渲染 ----
  function renderAll() {
    if (!svg || !viewG) return;
    riS = view.s; riX = view.x; riY = view.y;   // 记录本次全量渲染时的相机
    setTransform();
    renderBase();
    renderRoads();
    renderBuildings();
    renderLabels();
    renderMarkers();
  }

  function renderBase() {
    if (!DATA) return;
    var baseG = svg.querySelector(".base-layer");
    var html = "";
    (DATA.districts || []).forEach(function (d) {
      html += '<path class="map-district" d="' + esc(d.path) + '"></path>';
    });
    (DATA.water || []).forEach(function (w) {
      html += '<path class="map-water ' + (w.kind === "river" ? "is-river" : "") + '" d="' + esc(w.path) + '"></path>';
    });
    baseG.innerHTML = html;
  }

  function renderRoads() {
    if (!DATA) return;
    var upx = 1 / view.s;   // 每屏幕像素对应多少局部单位
    var layer = svg.querySelector(".road-layer");
    var html = "";

    // tier1/2 始终尝试显示，随 upx 增长才隐藏极细等级
    // 阈值放宽：让主干道/次干道在整城视野即可见，避免初始视图显得空旷
    var tiers = [
      { t: "tier1", max: 90, cls: "road-t1" },
      { t: "tier2", max: 55, cls: "road-t2" },
      { t: "tier3", max: 3.5, cls: "road-t3" },
      { t: "tier4", max: 1.2, cls: "road-t4" },
    ];
    tiers.forEach(function (cfg) {
      if (upx > cfg.max) return;
      var list = parseRoads(cfg.t);
      var v = visibleRect(), pad = 170 * upx;   // 潜带加宽，覆盖平滑平移的相机提前量
      list.forEach(function (item) {
        if (!fits(item.b, pad)) return;
        html += '<path class="' + cfg.cls + '" d="' + esc(item.r.path) + '"></path>';
      });
    });
    layer.innerHTML = html;
  }

  function renderBuildings() {
    if (!DATA) return;
    var upx = 1 / view.s;
    var layer = bldLayer;
    // 可读性阈值：建筑至少约 3 屏幕像素见方，minArea ≈ (3*upx)²（局部单位²）
    var minArea = Math.max(5, 9 * upx * upx);
    var show = upx <= 1.5;   // 缩放不足（全局视野）时不加载建筑
    var html = "";
    if (show) {
      var v = visibleRect(), pad = 300 * upx;
      var c0x = Math.floor((v[0] - pad) / CELL), c1x = Math.floor((v[2] + pad) / CELL);
      var c0y = Math.floor((v[1] - pad) / CELL), c1y = Math.floor((v[3] + pad) / CELL);
      var grid = DATA.buildings.grid;
      var parts = [];
      for (var gx = c0x; gx <= c1x; gx++) {
        for (var gy = c0y; gy <= c1y; gy++) {
          var cell = grid[gx + "_" + gy];
          if (!cell) continue;
          for (var i = 0; i < cell.length; i++) {
            var b = cell[i];
            if (b.area < minArea) continue;
            var p = b.pts;
            // 粗略包围盒剔除
            var bx0 = p[0], by0 = p[1], bx1 = p[0], by1 = p[1];
            for (var j = 2; j < p.length; j += 2) {
              if (p[j] < bx0) bx0 = p[j]; if (p[j] > bx1) bx1 = p[j];
              if (p[j + 1] < by0) by0 = p[j + 1]; if (p[j + 1] > by1) by1 = p[j + 1];
            }
            if (bx1 < v[0] - pad || bx0 > v[2] + pad || by1 < v[1] - pad || by0 > v[3] + pad) continue;
            var d = "M" + b.pts[0] + " " + b.pts[1];
            for (var k = 2; k < p.length; k += 2) d += "L" + p[k] + " " + p[k + 1];
            parts.push(d + "Z");
          }
        }
      }
      html = parts.join("");
      if (html) layer.innerHTML = '<path class="map-building" d="' + html + '"></path>';
    }
    if (!html) layer.innerHTML = "";
  }

  var districtCache = null;
  function districtMeta() {
    if (districtCache) return districtCache;
    districtCache = [];
    (DATA.districts || []).forEach(function (d) {
      var nums = d.path.match(numRe);
      var xs = [], ys = [];
      for (var i = 0; i + 1 < nums.length; i += 2) { xs.push(+nums[i]); ys.push(+nums[i + 1]); }
      if (!xs.length) return;
      districtCache.push({
        name: d.name,
        b: [Math.min.apply(null, xs), Math.min.apply(null, ys),
            Math.max.apply(null, xs), Math.max.apply(null, ys)]
      });
    });
    return districtCache;
  }

  function renderLabels() {
    if (!DATA) return;
    var upx = 1 / view.s;
    var html = "";
    // 片区名：取「区界 ∩ 地图范围」的中心，钳制到可见区域；视口外整区剔除
    if (upx < 30) {
      var bb = localBBox();
      var pad = 170 * upx;
      districtMeta().forEach(function (d) {
        if (!fits(d.b, pad)) return;
        var ix0 = Math.max(d.b[0], bb[0]), ix1 = Math.min(d.b[2], bb[2]);
        var iy0 = Math.max(d.b[1], bb[1]), iy1 = Math.min(d.b[3], bb[3]);
        var lx = ix1 > ix0 ? (ix0 + ix1) / 2 : (d.b[0] + d.b[2]) / 2;
        var ly = iy1 > iy0 ? (iy0 + iy1) / 2 : (d.b[1] + d.b[3]) / 2;
        html += '<text class="map-label" x="' + lx.toFixed(0) + '" y="' + ly.toFixed(0) + '">' + esc(d.name) + "</text>";
      });
    }
    // 路名（主干道放大时）：同名道路只标注一次，避免重复文字相互重叠
    if (upx <= 6) {
      var v = visibleRect(), pad = 160 * upx;
      var shownRoad = {};
      parseRoads("tier1").concat(parseRoads("tier2")).forEach(function (item) {
        var nm = item.r.name;
        if (!nm || shownRoad[nm]) return;
        if (item.r.path.length < 40) return;
        if (!fits(item.b, pad)) return;
        var mid = item.r.path.match(numRe);
        if (!mid || mid.length < 4) return;
        var cx = (+mid[0] + +mid[mid.length - 2]) / 2;
        var cy = (+mid[1] + +mid[mid.length - 1]) / 2;
        shownRoad[nm] = true;
        html += '<text class="map-roadname" x="' + cx.toFixed(0) + '" y="' + cy.toFixed(0) + '">' + esc(nm) + "</text>";
      });
    }
    labelLayer.innerHTML = html;
  }

  function renderMarkers() {
    if (!poiLayer) return;
    var upx = 1 / view.s;
    var redUpx = 300;   // 红色(高契合/重点) 在任何视野都显示
    var allUpx = 300;   // 绿色(常规) 也在整城视野显示，避免地图“空白”
    var html = "";
    if (upx <= redUpx) {
      var maxAff = 1;
      pois.forEach(function (p) { if (p.affinity > maxAff) maxAff = p.affinity; });
      // 红绿圆点 + 虚线包围（恒定屏幕尺寸）：红色=高契合推荐，绿色=常规
      var k = upx;  // 缩放系数，使圆点保持约 11px 恒定
      pois.forEach(function (p) {
        var hot = p.affinity / maxAff >= 0.8;
        // 分层：缩放不足时只显示高契合(红)点，绿色(常规)点放大后再出现
        if (!hot && upx > allUpx) return;
        var l = poiLocal(p);
        var sel = p.id === selectedId;
        var cls = "poi-marker" + (hot ? " is-hot" : "") + (sel ? " is-selected" : "");
        html +=
          '<g class="' + cls + '" data-id="' + esc(p.id) + '" transform="translate(' + l[0].toFixed(1) + "," + l[1].toFixed(1) + ')">' +
          '<g class="pk-marker" transform="scale(' + (k > 0 ? k.toFixed(4) : 0.01) + ')">' +
          '<circle class="pk-hit" cx="0" cy="0" r="20"></circle>' +
          '<circle class="pk-ring" cx="0" cy="0" r="9" fill="none"></circle>' +
          '<circle class="pk-dot" cx="0" cy="0" r="5.2"></circle>' +
          '</g>' +
          '<title>' + esc(p.name) + " · " + esc(p.district) + "</title></g>";
        // 点位名：恒定屏幕像素抬高
        if (upx <= 7 && upx >= 0.3) {
          var dy = -26 * upx;
          html += '<text class="poi-name" x="' + l[0].toFixed(1) + '" y="' + (l[1] + dy).toFixed(1) + '">' + esc(p.name) + "</text>";
        }
      });
    }
    poiLayer.innerHTML = html;
  }

  // ---- 拖拽 / 缩放 / 双指捏合 / 点选（绑定在容器上，仅一次）----
  var bound = false;
  function bindInteraction(container) {
    if (bound) return;
    bound = true;

    var pointers = {};   // pointerId -> {x,y}（client 坐标）
    var pinch = null;    // {d0, s0, pivot:{lx,ly}}
    var drag = null;     // 单指平移 {ox, oy}
    var movedTot = 0, tapX = 0, tapY = 0;

    function np() { var n = 0; for (var k in pointers) n++; return n; }
    function pointersArr() { var a = []; for (var k in pointers) a.push(k); return a; }

    function pickAt(cx, cy) {
      var hit = document.elementFromPoint(cx, cy);
      var marker = hit && hit.closest ? hit.closest(".poi-marker") : null;
      if (marker) {
        var mid = marker.getAttribute("data-id");
        if (mid && onClick) { onClick(mid); return; }
      }
      if (onClickMap) {
        var rect = container.getBoundingClientRect();
        var ll = screenToLatLon(cx - rect.left, cy - rect.top);
        onClickMap(ll[0], ll[1]);
      }
    }

    container.addEventListener("pointerdown", function (e) {
      if (e.pointerType === "mouse" && e.button !== 0) return;
      pointers[e.pointerId] = { x: e.clientX, y: e.clientY };
      var n = np();
      if (n === 1) {
        movedTot = 0; tapX = e.clientX; tapY = e.clientY;
        drag = { ox: e.clientX, oy: e.clientY };
      } else if (n === 2) {
        var ids = pointersArr();
        var a = pointers[ids[0]], b = pointers[ids[1]];
        var mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
        pinch = {
          d0: Math.max(1, Math.sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y))),
          s0: view.s,
          pivot: { lx: (mx - view.x) / view.s, ly: (my - view.y) / view.s },
        };
        drag = null;
      }
      if (container.setPointerCapture) container.setPointerCapture(e.pointerId);
    });

    container.addEventListener("pointermove", function (e) {
      if (!pointers[e.pointerId]) return;
      pointers[e.pointerId] = { x: e.clientX, y: e.clientY };
      var n = np();
      if (n >= 2 && pinch) {
        var ids = pointersArr();
        var a = pointers[ids[0]], b = pointers[ids[1]];
        var mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
        var d = Math.sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y));
        var ns = Math.max(MIN_S, Math.min(MAX_S, pinch.s0 * (d / pinch.d0)));
        view.s = ns;
        view.x = mx - pinch.pivot.lx * ns;
        view.y = my - pinch.pivot.ly * ns;
        movedTot = 1e9;             // 捏合不算点选
        setTransform(); maybeRender();
      } else if (n === 1 && drag) {
        var dx = e.clientX - drag.ox, dy = e.clientY - drag.oy;
        view.x += dx; view.y += dy;
        drag.ox = e.clientX; drag.oy = e.clientY;
        movedTot += Math.abs(dx) + Math.abs(dy);
        setTransform(); maybeRender();
      }
    });

    function endPointer(e) {
      delete pointers[e.pointerId];
      var n = np();
      if (n === 1) {
        // 捏合剩一指 → 退化为平移
        var id = pointersArr()[0];
        drag = { ox: pointers[id].x, oy: pointers[id].y };
        pinch = null;
      } else if (n === 0) {
        if (movedTot < 12) pickAt(tapX, tapY);   // 轻点：选景点 / 空白取坐标
        drag = null; pinch = null; movedTot = 0;
      }
    }
    container.addEventListener("pointerup", endPointer);
    container.addEventListener("pointercancel", endPointer);

    container.addEventListener("wheel", function (e) {
      e.preventDefault();
      var rect = container.getBoundingClientRect();
      var px = e.clientX - rect.left, py = e.clientY - rect.top;
      zoomAt(px, py, Math.exp(-e.deltaY * 0.0012));
    }, { passive: false });
  }

  var controlsBound = false;
  function bindControls(container) {
    if (controlsBound) return;
    controlsBound = true;
    var q = function (sel) { return container.querySelector(sel); };
    var ctrl = q(".map-controls");
    if (!ctrl) return;
    var btnIn = q('[data-zoom="in"]'), btnOut = q('[data-zoom="out"]'), btnR = q('[data-zoom="reset"]');
    if (btnIn) btnIn.addEventListener("click", function () {
      var r = container.getBoundingClientRect();
      zoomAt(r.width / 2, r.height / 2, 1.6);
    });
    if (btnOut) btnOut.addEventListener("click", function () {
      var r = container.getBoundingClientRect();
      zoomAt(r.width / 2, r.height / 2, 1 / 1.6);
    });
    if (btnR) btnR.addEventListener("click", resetView);
  }

  // ---- 公开入口（保留原契约）----
  function renderMap(container, poiList, selId, cb) {
    pois = poiList || [];
    selectedId = selId;
    onClick = cb;
    ensureSvg(container);
    bindInteraction(container);
    bindControls(container);
    if (!initDone) {
      initDone = true;
      loadData().then(function () {
        fitToBox();
      }).catch(function (err) {
        console.error("map data load failed:", err);
      });
    } else {
      markDirty();
    }
  }

  // 调试探针（正式版可移除）
  function dbg() {
    return { data: !!DATA, fitBox: !!fitBox, initDone: initDone, s: view.s,
             raf: raf, dirty: dirty, svg: !!svg, viewG: !!viewG,
             roads: svg ? svg.querySelectorAll(".road-layer path").length : -1 };
  }
  window.__mapDbg = dbg;

  function setClickMap(cb) { onClickMap = cb; }

  // 兼容旧导出（renderBase/renderMarkers 不再使用，保留占位）
  function renderBaseCompat() { return ""; }
  function renderMarkersCompat() { return ""; }
  var GEO = {};  // 旧导出占位

  function esc(v) {
    return String(v).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
  }

  win.ClearMap = win.ClearMap || {};
  win.ClearMap.map = {
    renderMap: renderMap,
    setCity: setCity,
    getCity: function () { return activeCity; },
    renderBase: renderBaseCompat,
    renderMarkers: renderMarkersCompat,
    GEO: GEO,
    resetView: resetView,
    zoomIn: function () { var r = svg && svg.getBoundingClientRect(); if (r) zoomAt(r.width / 2, r.height / 2, 1.6); },
    zoomOut: function () { var r = svg && svg.getBoundingClientRect(); if (r) zoomAt(r.width / 2, r.height / 2, 1 / 1.6); },
    drawRoute: drawRoute,
    clearRoute: clearRoute,
    drawCheckins: drawCheckins,
    clearCheckins: clearCheckins,
    drawPlan: drawPlan,
    clearPlan: clearPlan,
    setClickMap: setClickMap,
  };
})(window);