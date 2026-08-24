const stages = [
  { id: "overview", view: "overview", title: "运营总览", description: "查看产线运行、模型、标注和闭环任务的总体状态。", tip: "先确认服务和产线状态，再进入数据接入。" },
  { id: "acquire", view: "monitor", title: "数据接入", description: "接入相机、生产录像、本机视频或公开数据集。", tip: "选择数据来源并确认视频清晰度、机位和工位编号。" },
  { id: "clean", view: "monitor", title: "清洗质检", description: "抽帧、去重并剔除模糊、遮挡和无效画面。", tip: "清洗与数据接入共用成熟页面，完成后进入 AI 预标注。" },
  { id: "prelabel", view: "decision", title: "AI 预标注", description: "调用三种工业检测算法生成候选框与证据。", tip: "先选产线和算法，再提交预标注；候选结果仍需人工复核。" },
  { id: "cvat", view: "annotation", title: "CVAT 人工标注", description: "在 SOP 与官方 CVAT 之间同步任务、标签和版本。", tip: "先在本页创建或绑定 CVAT Task，再点左下角进入官方 CVAT 精标。" },
  { id: "freeze", view: "quality", title: "数据集冻结", description: "审核标注质量，划分训练/验证/测试集并生成版本。", tip: "冻结后不直接修改版本；有问题应退回复核并生成新版本。" },
  { id: "train", view: "training", title: "模型训练", description: "选择数据版本、三算法方案、GPU 与训练参数。", tip: "先用小轮次冒烟测试，确认流程正常后再启动正式训练。" },
  { id: "validate", view: "training", title: "推理验证", description: "对比精度、召回率、速度、小目标与误检表现。", tip: "不只看总精度，还要确认关键螺钉和漏装类别的召回率。" },
  { id: "realtime", view: "mes", title: "实时 SOP", description: "对现场视频进行步骤判断、越序识别和告警。", tip: "检测画面保持可见，右侧 SOP 看板用于解释当前步骤与异常。" },
  { id: "mes", view: "mes", title: "MES 闭环", description: "回传工单、步骤、结果、证据图与异常状态。", tip: "先使用测试工单验证幂等、重试和字段映射，再切换生产地址。" }
];

const state = { user: null, stageIndex: 0, cvatUrl: "" };
const qs = new URLSearchParams(location.search);
const cvatFromQuery = qs.get("cvat");
if (cvatFromQuery) localStorage.setItem("sop.unified.cvatUrl", cvatFromQuery.replace(/\/$/, ""));
state.cvatUrl = localStorage.getItem("sop.unified.cvatUrl") || "http://10.70.102.210:8081";

async function api(url, options = {}) {
  const response = await fetch(url, { credentials: "same-origin", ...options });
  let data = {};
  try { data = await response.json(); } catch (_) { data = { message: `HTTP ${response.status}` }; }
  if (!response.ok) throw new Error(data.message || `请求失败（${response.status}）`);
  return data;
}

function toast(message) {
  const element = document.getElementById("toast");
  element.textContent = message;
  element.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => element.classList.remove("show"), 2300);
}

function showLogin(message = "请使用现有岗位账号登录。", bad = false) {
  state.user = null;
  document.body.className = "unauthenticated";
  const element = document.getElementById("loginMessage");
  element.textContent = message;
  element.classList.toggle("bad", bad);
  document.getElementById("legacyFrame").removeAttribute("src");
}

function applyUser(user) {
  state.user = user;
  document.body.className = "authenticated";
  document.getElementById("displayName").textContent = user.display_name || user.username;
  document.getElementById("roleName").textContent = user.role_label || user.role;
  const allowed = new Set(user.views || []);
  document.querySelectorAll(".flow-item").forEach(button => {
    button.classList.toggle("locked", !allowed.has(button.dataset.view));
    button.setAttribute("aria-disabled", String(!allowed.has(button.dataset.view)));
  });
  const requested = stages.findIndex(item => item.id === qs.get("stage"));
  selectStage(requested >= 0 && allowed.has(stages[requested].view) ? requested : 0, true);
  refreshHealth();
}

function legacyUrl(stage) {
  return `${location.origin}/#${encodeURIComponent(stage.view)}`;
}

function selectStage(index, force = false) {
  const next = stages[index];
  if (!next) return;
  if (!force && state.user && !(state.user.views || []).includes(next.view)) {
    toast("当前岗位无此功能权限，请联系管理者。");
    return;
  }
  state.stageIndex = index;
  document.querySelectorAll(".flow-item").forEach(button => button.classList.toggle("active", button.dataset.step === next.id));
  document.getElementById("flowProgress").textContent = `${index + 1} / ${stages.length}`;
  document.getElementById("stageCode").textContent = `STAGE ${String(index + 1).padStart(2, "0")}`;
  document.getElementById("stageTitle").textContent = next.title;
  document.getElementById("stageDescription").textContent = next.description;
  document.getElementById("stageTip").textContent = next.tip;
  document.getElementById("nextButton").textContent = index === stages.length - 1 ? "返回总览" : "下一步";
  const frame = document.getElementById("legacyFrame");
  const target = legacyUrl(next);
  if (force || frame.src !== target) frame.src = target;
  history.replaceState(null, "", `${location.pathname}${location.search}#${next.id}`);
}

async function refreshHealth() {
  const sop = document.getElementById("sopHealth");
  const cvat = document.getElementById("cvatHealth");
  try {
    await api("/api/health");
    sop.className = "health-pill good";
    sop.innerHTML = "<i></i>SOP 中心服务正常";
  } catch (error) {
    sop.className = "health-pill bad";
    sop.innerHTML = "<i></i>SOP 服务异常";
  }
  try {
    const result = await api("/api/cvat/status");
    const ready = Boolean(result.available || result.ok || result.token_configured);
    cvat.className = `health-pill ${ready ? "good" : "bad"}`;
    cvat.innerHTML = `<i></i>${ready ? "CVAT 已连接" : "CVAT 待连接"}`;
  } catch (error) {
    cvat.className = "health-pill bad";
    cvat.innerHTML = "<i></i>CVAT 状态异常";
  }
}

async function openCvat(route = "/tasks") {
  try {
    if (window.pywebview?.api?.open_cvat) {
      const result = await window.pywebview.api.open_cvat(route);
      if (result?.ok === false) throw new Error(result.message || "无法打开 CVAT");
      return;
    }
  } catch (error) { toast(error.message); return; }
  window.open(`${state.cvatUrl}${route}`, "_blank", "noopener");
}

document.getElementById("loginForm").addEventListener("submit", async event => {
  event.preventDefault();
  const button = document.getElementById("loginButton");
  const message = document.getElementById("loginMessage");
  button.disabled = true;
  button.textContent = "正在验证…";
  message.classList.remove("bad");
  try {
    const result = await api("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: document.getElementById("username").value.trim(), password: document.getElementById("password").value })
    });
    document.getElementById("password").value = "";
    applyUser(result.user);
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("bad");
  } finally {
    button.disabled = false;
    button.textContent = "进入工作台";
  }
});

document.getElementById("logoutButton").addEventListener("click", async () => {
  await api("/api/auth/logout", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).catch(() => null);
  showLogin("已安全退出。请重新登录。", false);
});
document.getElementById("workflowNav").addEventListener("click", event => {
  const button = event.target.closest(".flow-item");
  if (button) selectStage(stages.findIndex(item => item.id === button.dataset.step));
});
document.getElementById("nextButton").addEventListener("click", () => {
  let candidate = (state.stageIndex + 1) % stages.length;
  for (let count = 0; count < stages.length; count += 1) {
    if ((state.user.views || []).includes(stages[candidate].view)) return selectStage(candidate);
    candidate = (candidate + 1) % stages.length;
  }
});
document.getElementById("refreshButton").addEventListener("click", () => {
  const frame = document.getElementById("legacyFrame");
  frame.contentWindow?.location.reload();
  refreshHealth();
});
document.getElementById("openLegacyButton").addEventListener("click", () => window.open(legacyUrl(stages[state.stageIndex]), "_blank", "noopener"));
document.getElementById("openCvatButton").addEventListener("click", () => openCvat("/tasks"));

(async function initialize() {
  try {
    const status = await api("/api/auth/status");
    if (status.authenticated && status.user) applyUser(status.user);
    else showLogin("中心服务已连接，请使用岗位账号登录。", false);
  } catch (error) {
    showLogin(`中心服务连接失败：${error.message}`, true);
  }
})();
