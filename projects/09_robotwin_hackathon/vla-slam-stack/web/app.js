import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';

const $ = (id) => document.getElementById(id);
const fmt = (n, d = 3) => (n === null || n === undefined ? '—' : Number(n).toFixed(d));

async function loadJSON(path) {
  const res = await fetch(path, { cache: 'no-store' });
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}`);
  return res.json();
}

/* ============================ training ============================ */

const CARD = {
  act: { bar: 'actBar', step: 'actStep', loss: 'actLoss', total: 20000, color: '#2fd3c0' },
  smolvla: { bar: 'vlaBar', step: 'vlaStep', loss: 'vlaLoss', total: 20000, color: '#8d7cf5' },
};

function drawChart(runs) {
  const cv = $('lossChart');
  const dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth;
  const h = 260;
  cv.width = w * dpr;
  cv.height = h * dpr;
  cv.style.height = h + 'px';
  const ctx = cv.getContext('2d');
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);

  const pad = { l: 56, r: 14, t: 34, b: 28 };
  const pw = w - pad.l - pad.r;
  const ph = h - pad.t - pad.b;

  const all = runs.flatMap((r) => r.points);
  if (!all.length) {
    ctx.fillStyle = '#5d6675';
    ctx.font = '13px monospace';
    ctx.fillText('暂无训练数据', pad.l, pad.t + 20);
    return;
  }
  const maxStep = Math.max(...all.map((p) => p.step), 2000);
  const losses = all.map((p) => p.loss).filter((v) => v > 0);
  let lo = Math.min(...losses);
  let hi = Math.max(...losses);
  // log axis: the two policies use different loss definitions (flow matching vs L1 chunking)
  lo = Math.max(1e-4, lo * 0.7);
  hi = hi * 1.35;

  const X = (s) => pad.l + (s / maxStep) * pw;
  const L = Math.log10(hi) - Math.log10(lo);
  const Y = (v) => pad.t + ph - ((Math.log10(Math.max(v, lo)) - Math.log10(lo)) / L) * ph;

  // grid + y labels, evenly spaced in log space
  ctx.font = '11px monospace';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  for (let i = 0; i <= 4; i++) {
    const t = i / 4;
    const v = lo * Math.pow(hi / lo, t);
    const y = pad.t + ph - t * ph;
    ctx.strokeStyle = '#1e2531';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad.l, y);
    ctx.lineTo(w - pad.r, y);
    ctx.stroke();
    ctx.fillStyle = '#5d6675';
    ctx.fillText(v < 0.01 ? v.toExponential(0) : v < 0.1 ? v.toFixed(3) : v.toFixed(2), pad.l - 9, y);
  }
  // x labels
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  for (let i = 0; i <= 4; i++) {
    const s = (maxStep * i) / 4;
    ctx.fillStyle = '#5d6675';
    ctx.fillText((s / 1000).toFixed(0) + 'k', X(s), pad.t + ph + 9);
  }
  ctx.fillStyle = '#5d6675';
  ctx.textAlign = 'left';
  ctx.fillText('loss · log', 4, 13);
  ctx.textAlign = 'right';
  ctx.fillText('step', w - pad.r, 13);

  // series
  for (const r of runs) {
    if (!r.points.length) continue;
    const c = CARD[r.id] ? CARD[r.id].color : '#f2b544';
    ctx.strokeStyle = c;
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    r.points.forEach((p, i) => {
      const x = X(p.step);
      const y = Y(p.loss);
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    });
    ctx.stroke();
    // last point marker
    const last = r.points[r.points.length - 1];
    ctx.fillStyle = c;
    ctx.beginPath();
    ctx.arc(X(last.step), Y(last.loss), 2.6, 0, Math.PI * 2);
    ctx.fill();
  }
}

function renderTraining(data) {
  for (const run of data.runs) {
    const c = CARD[run.id];
    if (!c) continue;
    const pct = Math.min(100, (run.last_step / c.total) * 100);
    $(c.bar).style.width = pct.toFixed(1) + '%';
    $(c.step).textContent = run.last_step
      ? `${run.last_step.toLocaleString()} / ${c.total.toLocaleString()} 步`
      : '模型加载中…';
    $(c.loss).textContent = run.last_loss === null ? 'loss —' : `loss ${fmt(run.last_loss, 3)}`;
  }
  drawChart(data.runs);
  const hasVla = data.runs.some((r) => r.id === 'smolvla' && r.points.length);
  $('chartNote').textContent = hasVla
    ? '对数纵轴 · 两者 loss 定义不同（ACT 为动作块 L1，SmolVLA 为流匹配），只看各自收敛趋势，不可横向比较'
    : 'SmolVLA 正在加载 5 亿参数视觉语言主干，其曲线稍后出现';
}

/* ============================ simulation ============================ */

function renderRuns(sim) {
  const tb = $('runsTable');
  tb.innerHTML = sim.runs
    .map(
      (r) => `<tr>
      <td>${r.seed}</td><td>${r.frames}</td><td>${r.points.toLocaleString()}</td>
      <td>${fmt(r.ate_rmse_m, 2)} m</td><td>${fmt(r.rpe_translation_rmse_m, 4)} m</td>
      <td>${fmt(r.map_mean_nn_m, 3)} m</td>
      <td>${(r.observed_surface_coverage_10cm * 100).toFixed(1)}%</td>
      <td>${fmt(r.icp_mean_ms, 1)} ms</td></tr>`
    )
    .join('');
}

/* ============================ semantics ============================ */

function renderSemantics(sem) {
  const ul = $('semList');
  const preds = sem.predictions || [];
  const rows = [];
  rows.push(
    `<li><span>模型</span><b>${(sem.model || '').split('/').pop()}</b></li>` +
      `<li><span>推理设备</span><b>${sem.device}</b></li>` +
      `<li><span>输入分辨率</span><b>${(sem.input_resolution || []).join('×')}</b></li>`
  );
  const stable = (sem.runs || []).filter((r) => r.run > 1);
  if (stable.length) {
    const avg = stable.reduce((a, r) => a + r.seconds, 0) / stable.length;
    rows.push(`<li><span>单轮 3 图耗时</span><b>${avg.toFixed(2)} s</b></li>`);
  }
  for (const p of preds.slice(0, 2)) {
    const top = (p.top_labels || [])[0];
    if (top) {
      rows.push(
        `<li><span>帧 ${String(p.frame).padStart(3, '0')} 主导标签</span><b>${top.label} ${(top.pixel_fraction * 100).toFixed(0)}%</b></li>`
      );
    }
  }
  ul.innerHTML = rows.join('');
}

/* ============================ point cloud ============================ */

async function buf(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}`);
  return res.arrayBuffer();
}

function heightColors(pos, n) {
  let zmin = Infinity;
  let zmax = -Infinity;
  for (let i = 0; i < n; i++) {
    const z = pos[i * 3 + 2];
    if (z < zmin) zmin = z;
    if (z > zmax) zmax = z;
  }
  const arr = new Float32Array(n * 3);
  const c0 = new THREE.Color('#1b4a8a');
  const c1 = new THREE.Color('#2fd3c0');
  const c2 = new THREE.Color('#f2b544');
  const tmp = new THREE.Color();
  for (let i = 0; i < n; i++) {
    const t = (pos[i * 3 + 2] - zmin) / Math.max(1e-6, zmax - zmin);
    if (t < 0.5) tmp.copy(c0).lerp(c1, t * 2);
    else tmp.copy(c1).lerp(c2, (t - 0.5) * 2);
    arr[i * 3] = tmp.r;
    arr[i * 3 + 1] = tmp.g;
    arr[i * 3 + 2] = tmp.b;
  }
  return arr;
}

function monoColors(n, hex = '#7fe8dc') {
  const c = new THREE.Color(hex);
  const arr = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    arr[i * 3] = c.r;
    arr[i * 3 + 1] = c.g;
    arr[i * 3 + 2] = c.b;
  }
  return arr;
}

async function initCloud(sim) {
  const vp = $('viewport');
  // .dat rather than .bin: some extension/adblock lists answer bare *.bin GETs with 204.
  const posBuf = await buf('data/map-positions.dat?v=1');
  const colBuf = await buf('data/map-colors.dat?v=1');
  const frameBuf = await buf('data/map-frame.dat?v=1');

  const n = posBuf.byteLength / 12;
  const rawPos = new Float32Array(posBuf);
  const rawCol = new Uint8Array(colBuf);
  const rawFrame = new Uint16Array(frameBuf);

  // stable sort by acquisition frame so the build animation reveals points in scan order
  const order = Array.from({ length: n }, (_, i) => i).sort((a, b) => rawFrame[a] - rawFrame[b]);
  const pos = new Float32Array(n * 3);
  const matCol = new Float32Array(n * 3);
  const frames = new Uint16Array(n);
  for (let i = 0; i < n; i++) {
    const s = order[i];
    pos[i * 3] = rawPos[s * 3];
    pos[i * 3 + 1] = rawPos[s * 3 + 1];
    pos[i * 3 + 2] = rawPos[s * 3 + 2];
    matCol[i * 3] = rawCol[s * 3] / 255;
    matCol[i * 3 + 1] = rawCol[s * 3 + 1] / 255;
    matCol[i * 3 + 2] = rawCol[s * 3 + 2] / 255;
    frames[i] = rawFrame[s];
  }

  const hgtCol = heightColors(pos, n);
  const moCol = monoColors(n);

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x07090d, 0.018);

  const camera = new THREE.PerspectiveCamera(46, vp.clientWidth / vp.clientHeight, 0.1, 400);
  camera.up.set(0, 0, 1);
  camera.position.set(19, 19, 16);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(vp.clientWidth, vp.clientHeight);
  renderer.setClearColor(0x07090d, 1);
  vp.appendChild(renderer.domElement);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.07;
  controls.target.set(0, 0, 0.9);
  controls.maxDistance = 90;
  controls.minDistance = 2;

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(matCol, 3));
  geo.setDrawRange(0, n);

  const mat = new THREE.PointsMaterial({
    size: 0.035,
    vertexColors: true,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0.95,
    depthWrite: true,
  });
  const points = new THREE.Points(geo, mat);
  scene.add(points);

  const grid = new THREE.GridHelper(20, 20, 0x1d2530, 0x141a22);
  grid.rotation.x = Math.PI / 2;
  scene.add(grid);

  // trajectory
  const trajGroup = new THREE.Group();
  const mkLine = (arr, color, width) => {
    const pts = arr.map((p) => new THREE.Vector3(p[0], p[1], p[2]));
    const g = new THREE.BufferGeometry().setFromPoints(pts);
    const m = new THREE.LineBasicMaterial({ color, linewidth: width, transparent: true, opacity: 0.95 });
    return new THREE.Line(g, m);
  };
  if (sim && sim.trajectory_gt) trajGroup.add(mkLine(sim.trajectory_gt, 0xf2b544, 2));
  if (sim && sim.trajectory_est && sim.trajectory_est[0])
    trajGroup.add(mkLine(sim.trajectory_est[0], 0x2fd3c0, 2));
  scene.add(trajGroup);

  // counts per frame for HUD
  const maxFrame = frames[n - 1];
  const cum = new Uint32Array(maxFrame + 2);
  for (let i = 0; i < n; i++) cum[frames[i] + 1]++;
  for (let i = 1; i < cum.length; i++) cum[i] += cum[i - 1];

  $('ptCount').textContent = n.toLocaleString() + ' POINTS';
  $('frameTag').textContent = `FRAME ${String(maxFrame).padStart(3, '0')} / ${String(maxFrame).padStart(3, '0')}`;

  // controls wiring
  $('colorMode').addEventListener('change', (e) => {
    const v = e.target.value;
    const arr = v === 'height' ? hgtCol : v === 'mono' ? moCol : matCol;
    geo.setAttribute('color', new THREE.BufferAttribute(arr, 3));
    geo.attributes.color.needsUpdate = true;
  });
  $('pointSize').addEventListener('input', (e) => {
    const s = parseFloat(e.target.value);
    mat.size = s;
    $('sizeOut').textContent = s.toFixed(3);
  });
  $('showTraj').addEventListener('change', (e) => (trajGroup.visible = e.target.checked));
  $('showGrid').addEventListener('change', (e) => (grid.visible = e.target.checked));

  let raf = null;
  $('buildBtn').addEventListener('click', () => {
    if (raf) cancelAnimationFrame(raf);
    const t0 = performance.now();
    const dur = 6500;
    const step = (t) => {
      const k = Math.min(1, (t - t0) / dur);
      const f = Math.floor(k * maxFrame);
      const count = cum[f + 1];
      geo.setDrawRange(0, count);
      $('frameTag').textContent = `FRAME ${String(f).padStart(3, '0')} / ${String(maxFrame).padStart(3, '0')}`;
      if (k < 1) raf = requestAnimationFrame(step);
      else raf = null;
    };
    geo.setDrawRange(0, 0);
    raf = requestAnimationFrame(step);
  });

  const resize = () => {
    const w = vp.clientWidth;
    const h = vp.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  };
  window.addEventListener('resize', resize);

  const loop = () => {
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(loop);
  };
  loop();

  $('loading')?.remove();
}

/* ============================ boot ============================ */

function navSpy() {
  const links = [...document.querySelectorAll('nav a')];
  const secs = links
    .map((a) => ({ a, el: document.querySelector(a.getAttribute('href')) }))
    .filter((x) => x.el);
  const onScroll = () => {
    const y = window.scrollY + 120;
    let current = secs[0];
    for (const s of secs) if (s.el.offsetTop <= y) current = s;
    links.forEach((l) => l.classList.toggle('active', l === current.a));
  };
  document.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

(async function boot() {
  navSpy();

  let sim = null;
  try {
    sim = await loadJSON('data/simulation.json');
    renderRuns(sim);
    const p = sim.runs[0].points;
    $('heroPoints').textContent = p.toLocaleString();
  } catch (e) {
    console.warn('simulation.json', e);
  }

  try {
    renderSemantics(await loadJSON('data/semantics.json'));
  } catch (e) {
    console.warn('semantics.json', e);
  }

  try {
    renderTraining(await loadJSON('data/training.json'));
  } catch (e) {
    console.warn('training.json', e);
  }

  try {
    await initCloud(sim);
  } catch (e) {
    console.warn('point cloud', e);
    const l = $('loading');
    if (l) l.textContent = '点云加载失败：' + e.message;
  }
})();
