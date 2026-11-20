"""Round-2 figures: re-render the 6 audited figures from THIS run's real data,
then add 2 new figures that only this run could produce.

  fig1..fig6  <- make_figures.py (reads benchmarks.json / repo_tests_full.log /
                 results_*.json / coverage.json / BENCH_20261115.md)
  fig7        <- round2_gpu_samples.json : real nvidia-smi sampling during Ollama
  fig8        <- round2_full_report.json : 16-item local runnability ledger

No value in any figure is invented.
"""
from __future__ import annotations

import json
import runpy
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)

# 1) re-render the six existing figures against this run's fresh data
runpy.run_path(str(HERE / "make_figures.py"), run_name="__main__")

prov_path = HERE / "FIGURE_PROVENANCE.json"
prov = json.loads(prov_path.read_text(encoding="utf-8"))

# Correct stale hard-coded provenance strings left over from the round-1 script.
# The underlying data is real; only the descriptive text was out of date.
_n_results = len(list((HERE.parent / "metatron_trial").glob("results_*.json")))
_bench = json.loads((HERE / "benchmarks.json").read_text(encoding="utf-8"))
_n_warm = len(_bench.get("ollama_warm", []))
prov["fig2_ollama_gpu.png"] = (
    f"benchmarks.json ollama_warm ({_n_warm} real steady-state calls across 3 models; "
    "cold-load reps in benchmarks.json ollama excluded from the bar chart)")
prov["fig3_metatron_convergence.png"] = (
    f"metatron_trial/results_*.json ({_n_results} real experiment logs, "
    "including round2_local which did NOT converge)")

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.edgecolor": "#424242", "axes.labelcolor": "#212121",
    "xtick.color": "#424242", "ytick.color": "#424242",
    "text.color": "#212121", "font.size": 10, "axes.titleweight": "bold",
})

# ---------------- Fig 7: real GPU utilisation during local inference ----------------
gp = HERE / "round2_gpu_samples.json"
if gp.exists():
    samples = json.loads(gp.read_text(encoding="utf-8"))["samples"]
    if samples:
        t0 = samples[0]["t"]
        t = np.array([s["t"] - t0 for s in samples])
        mem = np.array([s["mem_mib"] for s in samples])
        util = np.array([s["util_pct"] for s in samples])
        fig, ax = plt.subplots(figsize=(10.4, 4.2))
        ax.plot(t, mem, color="#5C6BC0", linewidth=1.6, label="VRAM used (MiB)")
        ax.set_xlabel("wall time (s) during round-2 full run")
        ax.set_ylabel("VRAM used (MiB)", color="#3949AB")
        ax.tick_params(axis="y", labelcolor="#3949AB")
        ax.set_ylim(0, 8188 * 1.08)
        ax.axhline(8188, color="#9E9E9E", linestyle="--", linewidth=1,
                   label="RTX 4060 capacity 8188 MiB")
        ax2 = ax.twinx()
        ax2.plot(t, util, color="#EF6C00", linewidth=1.2, alpha=.85,
                 label="GPU utilisation (%)")
        ax2.set_ylabel("GPU utilisation (%)", color="#E65100")
        ax2.tick_params(axis="y", labelcolor="#E65100")
        ax2.set_ylim(0, max(100, util.max() * 1.2))
        ax.set_title("Real nvidia-smi sampling - RTX 4060 8GB during Ollama inference\n"
                     f"n={len(samples)} samples | peak VRAM {mem.max():.0f} MiB | "
                     f"peak util {util.max():.0f}% | mean util {util.mean():.1f}%",
                     fontsize=11)
        ax.grid(alpha=.3)
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)
        fig.tight_layout()
        fig.savefig(FIG / "fig7_gpu_trace.png", dpi=160)
        plt.close(fig)
        prov["fig7_gpu_trace.png"] = (
            "round2_gpu_samples.json (real nvidia-smi -i 0 sampling every 0.6s "
            "during Ollama /api/chat inference)")
        print("fig7_gpu_trace.png written", flush=True)
    else:
        print("WARN: empty GPU sample list", flush=True)

# ---------------- Fig 8: what can actually run on this machine ----------------
rp = HERE / "round2_full_report.json"
if rp.exists():
    ledger = json.loads(rp.read_text(encoding="utf-8"))["runnability_ledger"]
    palette = {
        "RUNNABLE": "#66BB6A", "VERIFIED_UPSTREAM": "#2E7D32",
        "PARTIAL": "#FFD54F", "NOT_RUNNABLE": "#EF9A9A",
    }
    fig, ax = plt.subplots(figsize=(9.6, 7.2))
    ys = np.arange(len(ledger))
    ax.barh(ys, [1] * len(ledger), color=[palette.get(r["status"], "#BDBDBD")
                                          for r in ledger], edgecolor="#757575", height=.72)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{r['id']}  {r['label'][:38]}" for r in ledger], fontsize=8)
    ax.invert_yaxis()
    ax.set_xticks([])
    for y, r in zip(ys, ledger):
        ax.text(.5, y, r["status"], ha="center", va="center", fontsize=7.6,
                fontweight="bold", color="#263238")
    counts: dict[str, int] = {}
    for r in ledger:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    subtitle = "  ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    ax.set_title("Resume items vs. what this machine can actually execute\n"
                 f"{subtitle}\n"
                 "DGX unreachable / no torch / 8GB VRAM / original datasets absent",
                 fontsize=10.5)
    ax.set_xlim(0, 1)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "fig8_runnability_ledger.png", dpi=160)
    plt.close(fig)
    prov["fig8_runnability_ledger.png"] = (
        "round2_full_report.json runnability_ledger (16 resume items, "
        "status assigned from real environment probes)")
    print("fig8_runnability_ledger.png written", flush=True)

prov_path.write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nfinal figures:", flush=True)
for p in sorted(FIG.glob("*.png")):
    print(f"  {p.name:<38} {p.stat().st_size:>8} bytes", flush=True)
print("provenance entries:", len(prov), flush=True)
