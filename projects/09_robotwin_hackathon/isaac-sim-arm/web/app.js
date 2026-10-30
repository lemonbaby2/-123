/* Isaac Sim 4.5 · Franka 机械臂复现 — 训练曲线绘制（原生 canvas，零依赖） */
(function () {
  "use strict";

  function drawLineChart(canvas, series, opts) {
    opts = opts || {};
    var dpr = window.devicePixelRatio || 1;
    var w = canvas.clientWidth || 600, h = canvas.clientHeight || 240;
    canvas.width = w * dpr; canvas.height = h * dpr;
    var ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    var pad = { l: 52, r: 14, t: 14, b: 26 };
    var cw = w - pad.l - pad.r, ch = h - pad.t - pad.b;

    var all = [];
    series.forEach(function (s) { all = all.concat(s.pts.map(function (p) { return p[1]; })); });
    if (!all.length) return;
    var mn = Math.min.apply(null, all), mx = Math.max.apply(null, all);
    var span = (mx - mn) || 1;
    mn -= span * 0.08; mx += span * 0.08;
    var maxStep = Math.max.apply(null, series.map(function (s) { return s.pts[s.pts.length - 1][0]; })) || 1;

    var css = getComputedStyle(document.documentElement);
    var line = css.getPropertyValue("--line").trim() || "#1e2531";
    var dim = css.getPropertyValue("--dim").trim() || "#5d6675";
    var mono = css.getPropertyValue("--mono").trim() || "monospace";

    ctx.strokeStyle = line; ctx.fillStyle = dim;
    ctx.lineWidth = 1; ctx.font = "10px " + mono;
    for (var g = 0; g <= 4; g++) {
      var gy = pad.t + ch * g / 4;
      ctx.beginPath(); ctx.moveTo(pad.l, gy); ctx.lineTo(pad.l + cw, gy); ctx.stroke();
      var val = mx - (mx - mn) * g / 4;
      var lbl = Math.abs(val) >= 100 ? val.toFixed(0) : (Math.abs(val) >= 10 ? val.toFixed(1) : val.toFixed(2));
      ctx.fillText(lbl, 6, gy + 3);
    }
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
      var lp = s.pts[s.pts.length - 1];
      ctx.beginPath();
      ctx.fillStyle = s.color;
      ctx.arc(pad.l + cw * (lp[0] / maxStep), pad.t + ch * (1 - (lp[1] - mn) / (mx - mn)), 3, 0, 6.3);
      ctx.fill();
    });

    ctx.fillStyle = dim;
    ctx.font = "10px " + mono;
    ctx.fillText("x: iteration", pad.l + cw - 62, pad.t + 4);
  }

  function pick(json, tag) {
    if (!json || !json.series || !json.series[tag]) return null;
    return json.series[tag].map(function (d) { return [d.step, d.value]; });
  }

  var PALETTE = ["#2fd3c0", "#8d7cf5", "#f2b544", "#ef6f9a", "#5ad18b"];
  var specs = [];   // 供 resize 重绘

  function loadJSON(url) {
    return fetch(url + "?v=" + Date.now()).then(function (r) {
      if (!r.ok) throw new Error(url + " -> " + r.status);
      return r.json();
    });
  }

  function buildChart(canvasId, jsons, spec) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;
    var series = [], legend = [];
    spec.forEach(function (sp, i) {
      var j = jsons[sp.src];
      var pts = pick(j, sp.tag);
      if (!pts || !pts.length) return;
      var color = sp.color || PALETTE[i % PALETTE.length];
      series.push({ pts: pts, color: color });
      legend.push({ label: sp.label, color: color });
    });
    if (!series.length) {
      canvas.parentNode.insertAdjacentHTML("beforeend",
        '<div class="muted small" style="padding:8px 0">曲线数据未就绪：' + spec.map(function (s) { return s.tag; }).join(", ") + "</div>");
      return;
    }
    specs.push({ canvasId: canvasId, series: series });
    drawLineChart(canvas, series, {});
    var lg = document.getElementById(canvasId + "-legend");
    if (lg) {
      lg.innerHTML = legend.map(function (l) {
        return '<span><i style="background:' + l.color + '"></i>' + l.label + "</span>";
      }).join("");
    }
  }

  window.addEventListener("load", function () {
    loadJSON("data/curves_franka_lift.json").then(function (j) {
      var J = { m: j };

      buildChart("ch_reward", J, [
        { src: "m", tag: "Train/mean_reward", label: "mean_reward" },
        { src: "m", tag: "Train/mean_episode_length", label: "episode_length", color: "#8d7cf5" }
      ]);

      buildChart("ch_task", J, [
        { src: "m", tag: "Episode_Reward/lifting_object", label: "lifting_object" },
        { src: "m", tag: "Episode_Reward/object_goal_tracking", label: "object_goal_tracking", color: "#8d7cf5" },
        { src: "m", tag: "Episode_Reward/reaching_object", label: "reaching_object", color: "#f2b544" }
      ]);

      buildChart("ch_error", J, [
        { src: "m", tag: "Metrics/object_pose/position_error", label: "位置误差 (m)" },
        { src: "m", tag: "Loss/value_function", label: "value_loss", color: "#ef6f9a" }
      ]);

      buildChart("ch_loss", J, [
        { src: "m", tag: "Loss/surrogate", label: "surrogate" },
        { src: "m", tag: "Policy/mean_noise_std", label: "noise_std", color: "#8d7cf5" },
        { src: "m", tag: "Loss/entropy", label: "entropy", color: "#5ad18b" }
      ]);

      var t;
      window.addEventListener("resize", function () {
        clearTimeout(t);
        t = setTimeout(function () {
          specs.forEach(function (s) {
            var c = document.getElementById(s.canvasId);
            if (c) drawLineChart(c, s.series, {});
          });
        }, 200);
      });
    }).catch(function (e) {
      console.warn("曲线数据加载失败:", e);
      document.querySelectorAll(".chartwrap canvas").forEach(function (c) {
        var d = document.createElement("div");
        d.className = "muted small";
        d.textContent = "曲线数据未生成（请用 HTTP 服务打开本页，file:// 下 fetch 会被拦截）";
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

    // 照片墙灯箱
    var lb = document.getElementById("lightbox");
    if (lb) {
      var lbImg = lb.querySelector("img");
      var lbCap = lb.querySelector("span");
      document.querySelectorAll("#gallery .gitem img").forEach(function (img) {
        img.addEventListener("click", function () {
          var fig = img.closest("figure");
          var cap = fig ? fig.querySelector("figcaption") : null;
          lbImg.src = img.currentSrc || img.src;
          lbImg.alt = img.alt || "";
          lbCap.textContent = cap ? cap.textContent.replace(/\s+/g, " ").trim() : "";
          lb.classList.add("on");
        });
      });
      lb.addEventListener("click", function () {
        lb.classList.remove("on");
        lbImg.removeAttribute("src");
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") { lb.classList.remove("on"); lbImg.removeAttribute("src"); }
      });
    }
  });
})();
