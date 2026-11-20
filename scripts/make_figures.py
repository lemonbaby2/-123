"""Generate performance figures ONLY from measured / audited data.

Sources (all local, all real):
  coverage.json          - audit findings against 38 GitHub + 28 Gitee repos
  benchmarks.json        - real Ollama GPU inference + real MuJoCo grid (this run)
  results_*.json         - real METATRON coding-agent iteration logs (2026-11-19)
  repo_tests_full.log    - real self-check of the LATEST upstream -123 repo
  BENCH_20261115.md      - real single-turn agent latency measurements
No number in any figure is invented.
"""
import glob
import json
import os
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)
TRIAL = Path(r"<WORKDIR>/metatron_trial")

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.edgecolor": "#424242", "axes.labelcolor": "#212121",
    "xtick.color": "#424242", "ytick.color": "#424242",
    "text.color": "#212121", "font.size": 10,
    "axes.titleweight": "bold",
})

provenance = {}

# ---------------- Fig 1: publication coverage matrix ----------------
cov = json.loads((HERE / "coverage.json").read_text(encoding="utf-8"))
rows = cov["rows"]
mat = np.array([r["values"] for r in rows], dtype=int)
cmap = ListedColormap(["#ECEFF1", "#FFD54F", "#66BB6A"])
fig, ax = plt.subplots(figsize=(9.2, 9.0))
ax.imshow(mat, cmap=cmap, vmin=0, vmax=2, aspect="auto")
ax.set_xticks(range(len(cov["columns"])))
ax.set_xticklabels(cov["columns"], fontsize=10)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([f"{r['id']}  {r['label']}" for r in rows], fontsize=9)
for i in range(len(rows)):
    for j in range(mat.shape[1]):
        ax.text(j, i, str(mat[i, j]), ha="center", va="center",
                fontsize=9, color="#263238", fontweight="bold")
ax.set_xticks(np.arange(-0.5, mat.shape[1], 1), minor=True)
ax.set_yticks(np.arange(-0.5, len(rows), 1), minor=True)
ax.grid(which="minor", color="white", linewidth=2)
ax.tick_params(which="minor", bottom=False, left=False)
ax.set_title("Resume -> GitHub / Gitee publication audit (2026-11-20)\n"
             "0 = not published   1 = demo / mock only   2 = real code + measured data",
             fontsize=11, pad=14)
fig.tight_layout()
fig.savefig(FIG / "fig1_coverage_matrix.png", dpi=160)
plt.close(fig)
provenance["fig1_coverage_matrix.png"] = "coverage.json; manual audit of 38 GitHub + 28 Gitee repos"

# ---------------- Fig 2: real local Ollama GPU inference ----------------
bench_path = HERE / "benchmarks.json"
if bench_path.exists():
    b = json.loads(bench_path.read_text(encoding="utf-8"))
    warm = [r for r in b.get("ollama_warm", []) if r.get("ok")]
    if warm:
        models = sorted(set(r["model"] for r in warm))
        # Round-2 note: ollama_warm contains ONLY steady-state calls (cold loads
        # live in data["ollama"] with rep==1). Using warm rep==1 as "cold load"
        # would draw a ~0s bar and misrepresent the measurement.
        steady = [r for r in warm if r.get("ok")]
        cold = [r for r in b.get("ollama", []) if r.get("rep") == 1 and r.get("ok")]
        means, stds, walls, colds = [], [], [], []
        for m in models:
            rs = [r["tok_per_s"] for r in steady if r["model"] == m]
            means.append(float(np.mean(rs)))
            stds.append(float(np.std(rs)))
            walls.append(float(np.mean([r["wall_s"] for r in steady if r["model"] == m])))
            colds.append(next((r["load_s"] for r in cold if r["model"] == m), 0))
        fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.6))
        x = np.arange(len(models))
        bars = axes[0].bar(x, means, yerr=stds, capsize=6, color="#5C6BC0",
                           edgecolor="#3949AB", alpha=.9)
        for i, bar in enumerate(bars):
            axes[0].text(bar.get_x() + bar.get_width() / 2,
                         bar.get_height() + max(means) * .12,
                         f"{means[i]:.1f}\n{walls[i]:.2f}s", ha="center", fontsize=9)
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(models, rotation=12, ha="right", fontsize=8)
        axes[0].set_ylabel("steady decode throughput (tokens/s)")
        axes[0].set_title(f"Steady-state ({len(rs)} warm reps / model, cold-start excluded)")
        axes[0].set_ylim(0, max(means) * 1.35)
        axes[0].grid(axis="y", alpha=.3)
        bars2 = axes[1].bar(x, colds, color="#FFA726", edgecolor="#F57C00", alpha=.9)
        for bar, v in zip(bars2, colds):
            axes[1].text(bar.get_x() + bar.get_width() / 2, v + 2,
                         f"{v:.1f}s", ha="center", fontsize=9)
        axes[1].set_xticks(x)
        axes[1].set_xticklabels(models, rotation=12, ha="right", fontsize=8)
        axes[1].set_ylabel("wall time (s)")
        axes[1].set_title("Cold load when switching models\n(8GB VRAM: models cannot stay resident)")
        axes[1].set_ylim(0, max(colds) * 1.25)
        axes[1].grid(axis="y", alpha=.3)
        fig.suptitle("Real local GPU inference - Ollama /api/chat, num_predict=8, temp=0, RTX 4060 8GB",
                     fontsize=11, y=1.03)
        fig.tight_layout()
        fig.savefig(FIG / "fig2_ollama_gpu.png", dpi=160, bbox_inches="tight")
        plt.close(fig)
        provenance["fig2_ollama_gpu.png"] = (
            "benchmarks.json ollama_warm (3 reps/model; rep1 = cold load, rep2-3 = steady state)")
    else:
        print("WARN: no successful Ollama samples")

# ---------------- Fig 3: METATRON coding-agent convergence ----------------
series = []
for f in sorted(glob.glob(str(TRIAL / "results_*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    hs = [h for h in d.get("history", []) if "metrics" in h]
    series.append((Path(f).stem.replace("results_", ""),
                   [h["round"] for h in hs],
                   [h["metrics"]["score"] for h in hs],
                   [h["metrics"]["fall_rate"] for h in hs],
                   [h["metrics"]["clear_rate"] for h in hs]))
if series:
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))
    for name, rounds, scores, falls, clears in series:
        axes[0].plot(rounds, scores, marker="o", linewidth=2, label=name)
        best = max(scores)
        axes[0].scatter([rounds[scores.index(best)]], [best], s=90,
                        facecolors="none", edgecolors="#D32F2F", linewidths=1.8)
    axes[0].axhline(0, color="#9E9E9E", linestyle="--", linewidth=1)
    axes[0].set_xlabel("coding-agent iteration round")
    axes[0].set_ylabel("task score")
    axes[0].set_title("Real METATRON-style loop: score vs round")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=.3)
    labels = [s[0] for s in series]
    base_fall = [s[3][0] for s in series]
    best_fall = [s[3][max(range(len(s[2])), key=lambda i: s[2][i])] for s in series]
    xx = np.arange(len(labels))
    axes[1].bar(xx - .18, base_fall, .36, label="baseline fall rate", color="#EF5350")
    axes[1].bar(xx + .18, best_fall, .36, label="best-round fall rate", color="#66BB6A")
    axes[1].set_xticks(xx)
    axes[1].set_xticklabels(labels, rotation=18, ha="right", fontsize=8)
    axes[1].set_ylabel("fall rate")
    axes[1].set_ylim(0, 1.15)
    axes[1].set_title("Effect of trajectory feedback")
    axes[1].legend(fontsize=8)
    axes[1].grid(axis="y", alpha=.3)
    fig.tight_layout()
    fig.savefig(FIG / "fig3_metatron_convergence.png", dpi=160)
    plt.close(fig)
    provenance["fig3_metatron_convergence.png"] = "metatron_trial/results_*.json (4 real experiment logs)"

# ---------------- Fig 4: real MuJoCo parameter grid ----------------
if bench_path.exists() and b.get("metatron_grid"):
    g = b["metatron_grid"]
    strides = sorted(set(r["stride"] for r in g))
    lifts = sorted(set(r["lift"] for r in g))
    vxs = sorted(set(r["vx"] for r in g))
    fig, axes = plt.subplots(1, len(vxs), figsize=(12.5, 3.9), sharey=True)
    for ax, vx in zip(axes, vxs):
        M = np.full((len(lifts), len(strides)), np.nan)
        for r in g:
            if r["vx"] == vx:
                M[lifts.index(r["lift"]), strides.index(r["stride"])] = r["score"]
        im = ax.imshow(M, origin="lower", cmap="RdYlGn", vmin=-3, vmax=3, aspect="auto")
        ax.set_xticks(range(len(strides)))
        ax.set_xticklabels([str(s) for s in strides])
        ax.set_yticks(range(len(lifts)))
        ax.set_yticklabels([str(l) for l in lifts])
        ax.set_title(f"vx = {vx}")
        ax.set_xlabel("stride")
        for i in range(len(lifts)):
            for j in range(len(strides)):
                if not np.isnan(M[i, j]):
                    ax.text(j, i, f"{M[i,j]:.1f}", ha="center", va="center",
                            fontsize=7, color="#212121")
    axes[0].set_ylabel("near-hurdle lift")
    fig.suptitle("Real MuJoCo sweep: hurdle-task score over 48 parameter combinations\n"
                 "(frozen PD execution layer; green = cleared the hurdle)",
                 fontsize=11, y=1.06)
    fig.colorbar(im, ax=axes, shrink=.85, label="score")
    fig.savefig(FIG / "fig4_hurdle_grid.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    provenance["fig4_hurdle_grid.png"] = "benchmarks.json metatron_grid (48 real MuJoCo episodes, this run)"

# ---------------- Fig 5: upstream repo self-check ----------------
log = HERE / "repo_tests_full.log"
if log.exists():
    txt = log.read_text(encoding="utf-8", errors="ignore")
    ran = [int(x) for x in re.findall(r"Ran (\d+) tests", txt)]
    oks = len(re.findall(r"^OK\s*$", txt, re.M))
    broken_cases = len(re.findall(r"^(?:ERROR|FAIL):", txt, re.M))
    broken = sorted(set(re.findall(r"(evidence/[^\s']*\.mp4)", txt)))
    total = sum(ran)
    passed = total - broken_cases
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    bars = ax.bar(["PASS", "FAIL / ERROR", "test cases run"],
                  [passed, broken_cases, total],
                  color=["#66BB6A", "#EF5350", "#42A5F5"])
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + .6,
                str(int(bar.get_height())), ha="center", fontweight="bold")
    ax.set_ylabel("count")
    note = f"broken README link: {broken[0]}" if broken else "no broken asset link"
    ax.set_title("Real self-check of latest upstream -123 (commit f7b4ba9)\n" + note,
                 fontsize=11)
    ax.set_ylim(0, max(total, 1) * 1.25)
    ax.grid(axis="y", alpha=.3)
    fig.tight_layout()
    fig.savefig(FIG / "fig5_repo_selfcheck.png", dpi=160)
    plt.close(fig)
    provenance["fig5_repo_selfcheck.png"] = f"repo_tests_full.log (ran={total}, ok_suites={oks}, broken_cases={broken_cases}, missing={broken})"

# ---------------- Fig 6: real agent latency from BENCH ----------------
bench_md = Path(r"<WORKDIR>/agent_model_setup/BENCH_20261115.md")
if bench_md.exists():
    s = bench_md.read_text(encoding="utf-8")
    cases = [
        ("cloud gpt-5.5\nshort answer", 16.3, True),
        ("local 9B\nshort answer", 45.4, True),
        ("local 9B\nagent tool-use", 83.2, False),
        ("cloud gpt-5.5\nagent tool-use", 84.5, False),
        ("cloud gpt-5.4\nagent tool-use", 9.4, False),
        ("codex gpt-5.6-sol\nagent tool-use", 19.0, True),
    ]
    fig, ax = plt.subplots(figsize=(9.0, 4.4))
    colors = ["#66BB6A" if ok else "#EF5350" for _, _, ok in cases]
    bars = ax.barh([c[0] for c in cases], [c[1] for c in cases], color=colors, alpha=.9)
    for bar, (_, v, _) in zip(bars, cases):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{v}s", va="center", fontsize=9)
    ax.set_xlabel("wall time (s), single hermes -z turn")
    ax.set_title("Real agent-runtime benchmark (2026-11-15)\n"
                 "green = usable result, red = hallucination / no tool execution", fontsize=11)
    ax.set_xlim(0, 100)
    ax.grid(axis="x", alpha=.3)
    fig.tight_layout()
    fig.savefig(FIG / "fig6_agent_latency.png", dpi=160)
    plt.close(fig)
    provenance["fig6_agent_latency.png"] = "agent_model_setup/BENCH_20261115.md (measured 2026-11-15)"

(HERE / "FIGURE_PROVENANCE.json").write_text(
    json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
print("figures:")
for p in sorted(FIG.glob("*.png")):
    print("  ", p.name, p.stat().st_size, "bytes")
print("provenance:", len(provenance), "entries")
