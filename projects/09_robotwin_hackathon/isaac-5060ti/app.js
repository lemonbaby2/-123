/* Isaac 5060 Ti — 训练曲线绘制（原生 canvas，无依赖） */
(function () {
  "use strict";

  function poly(a, b) {
    // 线性拟合 y = k*x + m，返回斜率
    var n = Math.min(a.length, b.length), sx = 0, sy = 0, sxx = 0, sxy = 0;
    for (var i = 0; i < n; i++) { sx += a[i]; sy += b[i]; sxx += a[i]*a[i]; sxy += a[i]*b[i]; }
    return (n*sxy - sx*sy) / (n*sxx - sx*sx || 1);
  }

  function drawLineChart(canvas, series, opts) {
    opts = opts || {};
    var dpr = window.devicePixelRatio || 1;
    var w = canvas.clientWidth || 600, h = canvas.clientHeight || 240;
    canvas.width = w * dpr; canvas.height = h * dpr;
    var ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    var pad = { l: 46, r: 12, t: 14, b: 26 };
    var cw = w - pad.l - pad.r, ch = h - pad.t - pad.b;

    var all = [];
    series.forEach(function (s) { all = all.concat(s.pts.map(function (p) { return p[1]; })); });
    if (!all.length) return;
    var mn = Math.min.apply(null, all), mx = Math.max.apply(null, all);
    var span = (mx - mn) || 1;
    mn -= span * 0.08; mx += span * 0.08;
    var maxStep = Math.max.apply(null, series.map(function (s) { return s.pts[s.pts.length - 1][0]; }));

    var css = getComputedStyle(document.documentElement);
    var line = css.getPropertyValue("--line").trim() || "#1e2531";
    var dim = css.getPropertyValue("--dim").trim() || "#5d6675";

    // 网格 + Y 轴刻度
    ctx.strokeStyle = line; ctx.fillStyle = dim;
    ctx.lineWidth = 1; ctx.font = "10px " + (css.getPropertyValue("--mono").trim() || "monospace");
    for (var g = 0; g <= 4; g++) {
      var gy = pad.t + ch * g / 4;
      ctx.beginPath(); ctx.moveTo(pad.l, gy); ctx.lineTo(pad.l + cw, gy); ctx.stroke();
      var val = mx - (mx - mn) * g / 4;
      ctx.fillText(val.toFixed(1), 6, gy + 3);
    }
    // X 轴刻度
    for (var xt = 0; xt <= 4; xt++) {
      var xv = maxStep * xt / 4;
      var px = pad.l + cw * xt / 4;
      ctx.fillText(String(Math.round(xv)), px - 12, h - 8);
    }

    series.forEach(function (s) {
      ctx.beginPath();
      ctx.strokeStyle = s.color; ctx.lineWidth = 1.8;
      s.pts.forEach(function (p, i) {
        var x = pad.l + cw * (p[0] / maxStep);
        var y = pad.t + ch * (1 - (p[1] - mn) / (mx - mn));
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();
      // 末点
      var lp = s.pts[s.pts.length - 1];
      ctx.beginPath();
      ctx.fillStyle = s.color;
      ctx.arc(pad.l + cw * (lp[0] / maxStep), pad.t + ch * (1 - (lp[1] - mn) / (mx - mn)), 3, 0, 6.3);
      ctx.fill();
    });

    // 增长率标注
    if (opts.showSlope) {
      var s0 = series[0];
      var k = poly(s0.pts.map(function (p) { return p[0]; }), s0.pts.map(function (p) { return p[1]; }));
      ctx.fillStyle = s0.color; ctx.font = "11px " + (css.getPropertyValue("--mono").trim() || "monospace");
      ctx.fillText("斜率 " + k.toFixed(3) + "/iter", pad.l + 6, pad.t + 12);
    }
  }

  function pick(json, tag) {
    if (!json.series[tag]) return null;
    return json.series[tag].map(function (d) { return [d.step, d.value]; });
  }

  var PALETTE = ["#2fd3c0", "#8d7cf5", "#f2b544", "#ef6f9a", "#5ad18b"];

  function loadJSON(url) {
    return fetch(url + "?v=" + Date.now()).then(function (r) {
      if (!r.ok) throw new Error(url + " -> " + r.status);
      return r.json();
    });
  }

  function buildChart(canvasId, jsons, spec, opts) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;
    var series = [], legend = [];
    spec.forEach(function (sp, i) {
      var j = jsons[sp.src];
      if (!j) return;
      var pts = pick(j, sp.tag);
      if (!pts || !pts.length) return;
      series.push({ pts: pts, color: sp.color || PALETTE[i % PALETTE.length] });
      legend.push({ label: sp.label, color: sp.color || PALETTE[i % PALETTE.length] });
    });
    if (!series.length) {
      canvas.replaceWith(Object.assign(document.createElement("div"),
        { textContent: "曲线数据未就绪", className: "muted small" }));
      return;
    }
    drawLineChart(canvas, series, opts);
    var lg = document.getElementById(canvasId + "-legend");
    if (lg) {
      lg.innerHTML = legend.map(function (l) {
        return '<span><i style="background:' + l.color + '"></i>' + l.label + "</span>";
      }).join("");
    }
  }

  window.addEventListener("load", function () {
    Promise.all([loadJSON("data/curves_go2.json"), loadJSON("data/curves_go2_rough.json")])
      .then(function (res) {
        var flat = res[0], rough = res[1];

        buildChart("ch_flat_reward", { flat: flat }, [
          { src: "flat", tag: "Train/mean_reward", label: "mean_reward" },
          { src: "flat", tag: "Train/mean_episode_length", label: "episode_length" }
        ], { showSlope: true });

        buildChart("ch_flat_err", { flat: flat }, [
          { src: "flat", tag: "Metrics/base_velocity/error_vel_xy", label: "误差 vel_xy" },
          { src: "flat", tag: "Metrics/base_velocity/error_vel_yaw", label: "误差 vel_yaw" },
          { src: "flat", tag: "Loss/value_function", label: "value_loss ×1" }
        ], {});

        buildChart("ch_rough_reward", { rough: rough }, [
          { src: "rough", tag: "Train/mean_reward", label: "mean_reward" },
          { src: "rough", tag: "Train/mean_episode_length", label: "episode_length" }
        ], { showSlope: true });

        buildChart("ch_rough_err", { rough: rough }, [
          { src: "rough", tag: "Metrics/base_velocity/error_vel_xy", label: "误差 vel_xy" },
          { src: "rough", tag: "Metrics/base_velocity/error_vel_yaw", label: "误差 vel_yaw" },
          { src: "rough", tag: "Episode_Termination/base_contact", label: "摔倒终止率" }
        ], {});

        // 窗口尺寸变化时重绘
        var t;
        window.addEventListener("resize", function () {
          clearTimeout(t);
          t = setTimeout(function () {
            ["ch_flat_reward", "ch_flat_err", "ch_rough_reward", "ch_rough_err"].forEach(function (id) {
              var c = document.getElementById(id);
              if (!c) return;
              // 简化处理：按存储的 spec 重绘
              c.dispatchEvent(new Event("redraw"));
            });
          }, 200);
        });
      })
      .catch(function (e) {
        console.warn("曲线数据加载失败:", e);
        document.querySelectorAll(".chartwrap canvas").forEach(function (c) {
          var d = document.createElement("div");
          d.className = "muted small";
          d.textContent = "曲线数据未生成（本地打开时请用 HTTP 服务访问）";
          c.replaceWith(d);
        });
      });

    // 导航高亮
    var links = Array.prototype.slice.call(document.querySelectorAll("nav a"));
    var secs = links.map(function (a) { return document.querySelector(a.getAttribute("href")); });
    window.addEventListener("scroll", function () {
      var y = window.scrollY + 120, idx = 0;
      secs.forEach(function (s, i) { if (s && s.offsetTop <= y) idx = i; });
      links.forEach(function (a, i) { a.classList.toggle("active", i === idx); });
    }, { passive: true });
  });
})();
