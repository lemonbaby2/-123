"""Real, reproducible benchmarks for the resume-repo audit.

All numbers written to benchmarks.json come from actual local execution on this
machine (RTX 4060 8GB + local Ollama + MuJoCo). Nothing is synthesized.
"""
import itertools
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRIAL = Path(r"<WORKDIR>/metatron_trial")
OUT = HERE / "benchmarks.json"

data = {
    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "machine": "Windows / RTX 4060 8GB / Ollama 127.0.0.1:11434",
    "sources": [
        "local Ollama /api/chat (real GPU inference)",
        "MuJoCo FrozenExecutionLayer from metatron_trial.py (real simulation)",
    ],
    "ollama": [],
    "metatron_grid": [],
}

# ---------- 1. real Ollama inference benchmark ----------
MODELS = ["qwen2.5-coder:7b", "qwen3.5:2b-q4_K_M", "qwen3.5:9b-q4_K_M"]
for model in MODELS:
    for rep in range(3):
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": "Reply with exactly two characters: OK"}],
            "stream": False,
            "think": False,
            "options": {"num_predict": 8, "temperature": 0},
        }).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat", data=payload,
            headers={"Content-Type": "application/json"})
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read().decode())
            wall = time.perf_counter() - t0
            eval_count = d.get("eval_count", 0)
            eval_dur = d.get("eval_duration", 0) / 1e9  # ns -> s
            tps = round(eval_count / eval_dur, 2) if eval_dur > 0 else 0
            data["ollama"].append({
                "model": model, "rep": rep + 1, "wall_s": round(wall, 2),
                "eval_tokens": eval_count, "eval_s": round(eval_dur, 2),
                "tok_per_s": tps,
                "load_s": round(d.get("load_duration", 0) / 1e9, 2),
                "content": (d.get("message", {}).get("content") or "")[:24],
                "ok": True,
            })
        except Exception as e:
            data["ollama"].append({
                "model": model, "rep": rep + 1, "ok": False,
                "error": f"{type(e).__name__}: {str(e)[:110]}",
            })
        print("ollama", model, rep + 1, data["ollama"][-1].get("tok_per_s",
              data["ollama"][-1].get("error")), flush=True)

# ---------- 2. real MuJoCo parameter grid ----------
sys.path.insert(0, str(TRIAL))
os.chdir(str(TRIAL))
try:
    import metatron_trial as M
    grid = list(itertools.product(
        [0.2, 0.4, 0.6, 0.8],       # stride
        [0.2, 0.5, 0.9, 1.2],       # lift near hurdle
        [0.3, 0.5, 0.8],            # vx
    ))
    for stride, lift, vx in grid:
        code = (
            "def skill(state, t, dt):\n"
            f"    lift = {lift} if state[\"dist_to_hurdle\"] < 0.6 else 0.2\n"
            "    return {\"vx\": %s, \"stride\": %s, \"lift\": lift, "
            "\"phase_bias\": 0.0, \"torso_pitch\": 0.0}\n" % (vx, stride)
        )
        m = M.evaluate(M.compile_skill(code), "hurdle", episodes=1, seconds=5.0)
        data["metatron_grid"].append({
            "stride": stride, "lift": lift, "vx": vx,
            "score": m["score"], "distance": m["distance"],
            "fall_rate": m["fall_rate"], "clear_rate": m["clear_rate"],
        })
    print("grid done", len(data["metatron_grid"]), flush=True)
except Exception as e:
    data["metatron_grid_error"] = f"{type(e).__name__}: {e}"
    print("grid ERR", data["metatron_grid_error"], flush=True)

OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("saved", OUT, flush=True)
