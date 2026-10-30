"""Parse LeRobot training logs into a small JSON for the web dashboard."""
import json
import pathlib
import re

LOGS = {
    "act": ("/root/vla_outputs/train_act.log", "ACT · PyTorch 从零训练", "RTX 4060 8GB"),
    "smolvla": ("/root/vla_outputs/train.log", "SmolVLA · LoRA 微调", "RTX 5060 Ti 16GB"),
}
OUT = pathlib.Path("/mnt/e/研究生学习/黑客松/outputs/vla-slam-stack-2026-10/data/training.json")

LINE = re.compile(
    r"step:(?P<step>\d+)K\s+smpl:(?P<smpl>\d+)K\s+ep:(?P<ep>\d+)K?\s+epch:(?P<epch>[\d.]+)\s+"
    r"loss:(?P<loss>[\d.]+)\s+grdn:(?P<grdn>[\d.]+)\s+lr:(?P<lr>[\deE.+-]+)"
)


def parse(path):
    series = []
    try:
        text = pathlib.Path(path).read_text(errors="ignore")
    except OSError:
        return series
    for m in LINE.finditer(text):
        series.append(
            {
                "step": int(m.group("step")) * 1000,
                "sample": int(m.group("smpl")) * 1000,
                "epoch": float(m.group("epch")),
                "loss": float(m.group("loss")),
                "grad_norm": float(m.group("grdn")),
                "lr": float(m.group("lr")),
            }
        )
    return series


def main():
    out = {"runs": []}
    for key, (path, label, gpu) in LOGS.items():
        series = parse(path)
        out["runs"].append(
            {
                "id": key,
                "label": label,
                "gpu": gpu,
                "points": series,
                "last_step": series[-1]["step"] if series else 0,
                "last_loss": series[-1]["loss"] if series else None,
                "min_loss": min(p["loss"] for p in series) if series else None,
            }
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    for r in out["runs"]:
        print(f"{r['id']}: {len(r['points'])} points, last_step={r['last_step']}, min_loss={r['min_loss']}")


if __name__ == "__main__":
    main()
