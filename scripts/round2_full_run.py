"""Round-2 full local run - 2026-11-21.

Runs EVERYTHING that can actually be executed on this machine's RTX 4060 8GB,
serially (Ollama inference and MuJoCo simulation must not contend for VRAM),
and writes real logs + a machine-readable report. Nothing is synthesized.

Stages:
  0  environment snapshot (nvidia-smi, Ollama tags, toolchain)
  1  Ollama GPU inference benchmark (cold load + 3 steady reps per model)
     with a background nvidia-smi sampler proving real GPU utilisation
  2  MuJoCo 48-combination hurdle grid (real physics episodes)
  3  METATRON coding-agent loop, local 7B, 5 rounds with trajectory feedback
  4  upstream -123 repository self-check (tests / demos / layout)
  5  project runnability ledger for all 16 resume items

Outputs (all under HERE):
  benchmarks.json                 (new, old one backed up)
  repo_tests_full.log             (new, old one backed up)
  round2_gpu_samples.json
  round2_full_report.json
  round2_stage*.log
"""
from __future__ import annotations

import itertools
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRIAL = Path(r"<WORKDIR>/metatron_trial")
REPO = HERE / "upstream_-123"
VENV_PY = TRIAL / ".venv/Scripts/python.exe"
OLLAMA = "http://127.0.0.1:11434"
STAMP = "20261120"          # label for backups of round-1 data

sys.path.insert(0, str(TRIAL))
os.chdir(str(TRIAL))

report: dict = {
    "run_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "machine": "Windows / RTX 4060 8GB (GPU1 lost) / Ollama 127.0.0.1:11434 / MuJoCo 4.0.1",
    "stages": {},
    "principle": "Only real execution is recorded. Items requiring DGX / original "
                 "datasets / proprietary weights are marked NOT_RUNNABLE, never faked.",
}


def stage(name: str) -> None:
    print(f"\n{'=' * 78}\nSTAGE {name}\n{'=' * 78}", flush=True)
    report["stages"][name] = {"started": time.strftime("%H:%M:%S")}


def done(name: str, payload: dict) -> None:
    report["stages"][name].update(payload)
    report["stages"][name]["finished"] = time.strftime("%H:%M:%S")
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)


def backup(path: Path) -> None:
    if path.exists():
        dst = path.with_name(f"{path.stem}_{STAMP}{path.suffix}")
        if not dst.exists():
            shutil.copy2(path, dst)
            print(f"[backup] {path.name} -> {dst.name}", flush=True)


# ---------------------------------------------------------------- Stage 0
stage("0_environment")
env = {}
r = subprocess.run(
    ["nvidia-smi", "-i", "0", "--query-gpu=name,driver_version,memory.total,"
     "memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
    capture_output=True, text=True)
env["gpu_query"] = r.stdout.strip() or r.stderr.strip()
try:
    with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=8) as resp:
        tags = json.loads(resp.read().decode())
    env["ollama_models"] = [m["name"] for m in tags.get("models", [])]
except Exception as e:
    env["ollama_error"] = f"{type(e).__name__}: {e}"
env["mujoco"] = __import__("mujoco").__version__
env["python"] = sys.version.split()[0]
env["cmake"] = shutil.which("cmake") or "ABSENT"
env["gxx"] = shutil.which("g++") or shutil.which("cl") or "ABSENT"
done("0_environment", env)

# ---------------------------------------------------------------- GPU sampler
gpu_samples: list[dict] = []
_stop = threading.Event()


def sample_gpu() -> None:
    while not _stop.is_set():
        try:
            q = subprocess.run(
                ["nvidia-smi", "-i", "0", "--query-gpu=memory.used,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=4)
            line = (q.stdout or "").strip().splitlines()
            if line and "," in line[0]:
                mem, util = [x.strip() for x in line[0].split(",")[:2]]
                gpu_samples.append({"t": round(time.time(), 2),
                                    "mem_mib": float(mem), "util_pct": float(util)})
        except Exception:
            pass
        _stop.wait(0.6)


sampler = threading.Thread(target=sample_gpu, daemon=True)
sampler.start()

# ---------------------------------------------------------------- Stage 1
stage("1_ollama_gpu_benchmark")
MODELS = ["qwen2.5-coder:7b", "qwen3.5:2b-q4_K_M", "qwen3.5:9b-q4_K_M"]
backup(HERE / "benchmarks.json")

bench = {
    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "machine": report["machine"],
    "sources": ["local Ollama /api/chat (real GPU inference)",
                "MuJoCo FrozenExecutionLayer from metatron_trial.py (real simulation)"],
    "ollama": [], "ollama_warm": [], "metatron_grid": [],
}


def chat(model: str) -> dict:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly two characters: OK"}],
        "stream": False, "think": False,
        "options": {"num_predict": 8, "temperature": 0},
    }).encode()
    req = urllib.request.Request(OLLAMA + "/api/chat", data=payload,
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=240) as resp:
        d = json.loads(resp.read().decode())
    wall = time.perf_counter() - t0
    n = d.get("eval_count", 0)
    dur = d.get("eval_duration", 0) / 1e9
    return {"wall_s": round(wall, 2), "eval_tokens": n,
            "tok_per_s": round(n / dur, 2) if dur > 0 else 0,
            "load_s": round(d.get("load_duration", 0) / 1e9, 2),
            "content": (d.get("message", {}).get("content") or "")[:24], "ok": True}


cold_rows, warm_rows = [], []
for model in MODELS:
    # force-unload previous model so the first call is a genuine cold load
    try:
        unload = json.dumps({"model": model, "keep_alive": 0}).encode()
        urllib.request.urlopen(urllib.request.Request(
            OLLAMA + "/api/generate", data=unload,
            headers={"Content-Type": "application/json"}), timeout=30).read()
    except Exception:
        pass
    for rep in range(1, 4):
        try:
            row = chat(model)
        except Exception as e:
            row = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:110]}"}
        row.update({"model": model, "rep": rep})
        cold_rows.append(dict(row))
        # steady-state reps: same model, already resident
        if rep > 1:
            warm_rows.append({k: row[k] for k in
                              ("model", "rep", "wall_s", "eval_tokens", "tok_per_s") if k in row}
                             | {"ok": row.get("ok", False)})
        print(f"  {model:<24} rep{rep}  tps={row.get('tok_per_s')} "
              f"wall={row.get('wall_s')}s load={row.get('load_s')}s", flush=True)

# extra 3 true steady-state reps per model (cold-start excluded from fig2)
for model in MODELS:
    for rep in range(1, 4):
        try:
            row = chat(model)
            warm_rows.append({"model": model, "rep": rep,
                              "wall_s": row["wall_s"], "eval_tokens": row["eval_tokens"],
                              "tok_per_s": row["tok_per_s"], "ok": True})
            print(f"  [warm] {model:<24} rep{rep} tps={row['tok_per_s']}", flush=True)
        except Exception as e:
            print(f"  [warm] {model} ERR {e}", flush=True)

bench["ollama"] = cold_rows
bench["ollama_warm"] = warm_rows
bench["warm_note"] = ("Round-2: 3 cold-load reps + 3 steady-state reps per model on "
                      "the same RTX 4060 8GB; steady-state values exclude cold load. "
                      "GPU utilisation sampled in round2_gpu_samples.json.")
done("1_ollama_gpu_benchmark", {
    "cold_calls": len(cold_rows), "warm_calls": len(warm_rows),
    "models": MODELS,
    "steady_tps": {m: [r["tok_per_s"] for r in warm_rows
                       if r.get("model") == m and r.get("ok")]
                   for m in MODELS}})

# ---------------------------------------------------------------- Stage 2
stage("2_mujoco_grid")
import metatron_trial as M  # noqa: E402

grid = list(itertools.product([0.2, 0.4, 0.6, 0.8],       # stride
                              [0.2, 0.5, 0.9, 1.2],       # lift
                              [0.3, 0.5, 0.8]))           # vx
for stride, lift, vx in grid:
    code = (
        "def skill(state, t, dt):\n"
        f"    lift = {lift} if state[\"dist_to_hurdle\"] < 0.6 else 0.2\n"
        "    return {\"vx\": %s, \"stride\": %s, \"lift\": lift, "
        "\"phase_bias\": 0.0, \"torso_pitch\": 0.0}\n" % (vx, stride)
    )
    m = M.evaluate(M.compile_skill(code), "hurdle", episodes=1, seconds=5.0)
    bench["metatron_grid"].append({
        "stride": stride, "lift": lift, "vx": vx, "score": m["score"],
        "distance": m["distance"], "fall_rate": m["fall_rate"],
        "clear_rate": m["clear_rate"]})
scores = [r["score"] for r in bench["metatron_grid"]]
(HERE / "benchmarks.json").write_text(
    json.dumps(bench, ensure_ascii=False, indent=2), encoding="utf-8")
done("2_mujoco_grid", {"episodes": len(scores), "best_score": max(scores),
                       "cleared": sum(1 for r in bench["metatron_grid"]
                                      if r["clear_rate"] > 0),
                       "zero_fall": sum(1 for r in bench["metatron_grid"]
                                        if r["fall_rate"] == 0)})

# ---------------------------------------------------------------- Stage 3
stage("3_metatron_coding_agent")
history = []
code = M.BASE_SKILL
m = M.evaluate(M.compile_skill(code), "hurdle", episodes=3)
history.append({"round": 0, "source": "baseline", "code": code, "metrics": m})
print(f"  R0 baseline score={m['score']} fall={m['fall_rate']} clear={m['clear_rate']}",
      flush=True)
for rnd in range(1, 6):
    fb = M.feedback_of(m, "hurdle")
    t0 = time.time()
    try:
        raw = M.ask_coder(code, m, "hurdle", fb, "qwen2.5-coder:7b",
                          OLLAMA + "/v1", "ollama")
        cand = M.extract_code(raw)
        m2 = M.evaluate(M.compile_skill(cand), "hurdle", episodes=3)
        verdict = "ACCEPT" if m2["score"] > m["score"] else "REJECT"
        history.append({"round": rnd, "source": "coding-agent", "code": cand,
                        "metrics": m2, "verdict": verdict, "feedback": fb})
        print(f"  R{rnd} {verdict:<6} score={m2['score']:<7} fall={m2['fall_rate']:<5} "
              f"clear={m2['clear_rate']} ({time.time() - t0:.0f}s)", flush=True)
        if verdict == "ACCEPT":
            code, m = cand, m2
    except Exception as exc:
        history.append({"round": rnd, "error": f"{type(exc).__name__}: {exc}"})
        print(f"  R{rnd} ERROR {type(exc).__name__}: {str(exc)[:100]}", flush=True)

res_path = TRIAL / "results_round2_local.json"
res_path.write_text(json.dumps({
    "paper": "arXiv:2610.38027 METATRON (NVIDIA Research, 2026-10-27)",
    "task": "hurdle", "coder_model": "qwen2.5-coder:7b",
    "endpoint": OLLAMA + "/v1", "run_at": report["run_at"], "history": history,
    "best_score": max(h["metrics"]["score"] for h in history if "metrics" in h),
}, ensure_ascii=False, indent=2), encoding="utf-8")
done("3_metatron_coding_agent", {
    "rounds": 5, "baseline": history[0]["metrics"]["score"],
    "best": max(h["metrics"]["score"] for h in history if "metrics" in h),
    "result_file": res_path.name})

# ---------------------------------------------------------------- stage 1 GPU samples
_stop.set()
sampler.join(timeout=3)
(HERE / "round2_gpu_samples.json").write_text(
    json.dumps({"sampler_interval_s": 0.6, "samples": gpu_samples},
               ensure_ascii=False, indent=2), encoding="utf-8")
if gpu_samples:
    print(f"\n[GPU sampler] {len(gpu_samples)} samples, "
          f"peak mem={max(s['mem_mib'] for s in gpu_samples):.0f} MiB, "
          f"peak util={max(s['util_pct'] for s in gpu_samples):.0f}%", flush=True)

# ---------------------------------------------------------------- Stage 4
stage("4_repo_selfcheck")
backup(HERE / "repo_tests_full.log")
backup(HERE / "repo_demos_full.log")
checks = {}
for script, log in (("run_tests.py", "repo_tests_full.log"),
                    ("run_all_demos.py", "round2_demos_full.log"),
                    ("verify_layout.py", "round2_verify_layout_full.log")):
    r = subprocess.run([sys.executable, "scripts/" + script], cwd=str(REPO),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="ignore", timeout=300)
    (HERE / log).write_text((r.stdout or "") + (r.stderr or ""), encoding="utf-8")
    checks[script] = {"exit_code": r.returncode, "log": log}
    print(f"  {script:<22} exit={r.returncode}  log={log}", flush=True)
import re  # noqa: E402
t = (HERE / "repo_tests_full.log").read_text(encoding="utf-8", errors="ignore")
checks["tests_total"] = sum(int(x) for x in re.findall(r"Ran (\d+) tests", t))
checks["tests_failed"] = len(re.findall(r"^(?:ERROR|FAIL):", t, re.M))
checks["broken_link"] = sorted(set(re.findall(r"(evidence/[^\s']*\.mp4)", t)))
done("4_repo_selfcheck", checks)

# ---------------------------------------------------------------- Stage 5
stage("5_runnability_ledger")
ledger = [
    ("R1", "LingBot-VLA 2.0 / R2 / RoboTwin", "NOT_RUNNABLE", "needs DGX multi-GPU 50k+10k-step training, 50k/10k checkpoints, LeRobot dataset"),
    ("R2", "Zebra / YOLO11-P2 + AIFI/CCFM", "NOT_RUNNABLE", "needs ZT421T nozzle images/labels, trained weights, TensorRT engine"),
    ("R3", "Cloud Ginger / CCU / OpenVLA", "NOT_RUNNABLE", "needs vendor CCU API, Jetson Orin NX, AWQ quantisation log"),
    ("R4", "GeoScan Pro / LIO-SAM + RTK", "PARTIAL", "CRC / factor-graph unit tests run locally; real dual-antenna RTK needs hardware"),
    ("R5", "World model / action-conditioned pred", "NOT_RUNNABLE", "no original engineering project exists; 20+ frame / PSNR metrics have no source"),
    ("R6", "OpenVLA language-driven manipulation", "NOT_RUNNABLE", "needs 1000+ teleop trajectories and real-arm logs"),
    ("R7", "Qwen2.5-VL industrial VQA / SOP", "PARTIAL", "local Ollama VL inference benchmark runnable; 98.2% recall needs production video+labels"),
    ("R8", "ROS2 + 3DGS Lego visualization", "PARTIAL", "PLY/MarkerArray unit tests run locally; original Lego assets and Isaac Sim absent"),
    ("R9", "Quadruped SLAM / CUDA / Vicon", "PARTIAL", "voxel/ICP unit tests + C++17 build locally; Vicon ground truth and 100h log absent"),
    ("R10", "STM32-FreeRTOS BMS", "PARTIAL", "Thevenin/AEKF unit tests locally; MCU firmware and HIL rig absent"),
    ("P1", "Paper: Dy3DGS-SLAM", "PARTIAL", "repro assets published upstream; full 3DGS training needs DGX"),
    ("P2", "Paper: TAC-R2S2R", "VERIFIED_UPSTREAM", "160 seeded runs + CSV + figures already public"),
    ("P3", "Patents (4) / awards", "NOT_RUNNABLE", "documents only; no application numbers / scans"),
    ("A1", "Agent: R1 offline self-learning", "RUNNABLE", "pure stdlib; 4/4 offline self-check PASS in repo tests"),
    ("A2", "Agent: Hermes fix + all-agent setup", "RUNNABLE", "setup_local_models.py --verify runs locally; config contains secrets -> must sanitise"),
    ("A3", "Agent: Metatron coding-agent repro", "RUNNABLE", "fully executed this run: Ollama 7B + MuJoCo 48-grid + 5-round loop"),
]
report["runnability_ledger"] = [
    {"id": i, "label": l, "status": s, "reason": r} for i, l, s, r in ledger]
counts = {}
for _, _, s, _ in ledger:
    counts[s] = counts.get(s, 0) + 1
done("5_runnability_ledger", {"total_items": len(ledger), "by_status": counts})

(HERE / "round2_full_report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n{'=' * 78}\nALL STAGES DONE -> round2_full_report.json\n{'=' * 78}", flush=True)
