import subprocess
import sys
from pathlib import Path

CR = Path("/home/nvidia/microduck-course-run")
M = CR / "topic/02-可运行代码/MotrixLab"
MP = M / ".venv/bin/python"
RUNNER = CR / "topic/02-可运行代码/microduck-playground-stilts/scripts/motrix_runner.py"
OUT = CR / "topic/03-Notebook/outputs"

if not MP.is_file():
    sys.exit("MOTRIX_PYTHON missing: %s" % MP)

# 1) scratch FastSAC smoke (64 envs x 10 iterations, no resume checkpoint)
train_cmd = [
    str(MP), str(RUNNER), "train", str(M / "scripts/train.py"),
    "task=microduck-ball-balance/motrix.fastsac",
    "num_envs=64",
    "play=false", "render=false", "algo.asynchronous=false",
    "algo.device=cuda", "algo.agent.compile=false", "algo.agent.amp=false",
    "algo.agent.learning_starts=0", "algo.agent.buffer_size=8",
    "algo.agent.batch_size=64", "algo.agent.num_updates=1",
    "algo.trainer.num_learning_iterations=10",
]
print("TRAIN:", " ".join(train_cmd), flush=True)
r = subprocess.run(train_cmd, cwd=M)
if r.returncode != 0:
    sys.exit("TRAIN FAILED rc=%d" % r.returncode)

# 2) locate latest run dir
run_root = M / "runs/microduck-ball-balance/motrix/torch/fastsac"
runs = sorted((p for p in run_root.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime)
if not runs:
    sys.exit("no run dir under %s" % run_root)
run_dir = runs[-1]
print("RUN_DIR:", run_dir, flush=True)

# 3) export ONNX
export_cmd = [
    str(MP), str(RUNNER), "export", str(M / "scripts/export_onnx.py"),
    "run_dir=%s" % run_dir, "output=outputs/motrix_ball_balance_latest.onnx", "opset=11",
]
print("EXPORT:", " ".join(export_cmd), flush=True)
r = subprocess.run(export_cmd, cwd=M)
exported = M / "outputs/motrix_ball_balance_latest.onnx"
if r.returncode != 0 or not exported.is_file():
    sys.exit("EXPORT FAILED")

# 4) place into converted/ (stable inference path used by notebook cell 2)
dst = CR / "converted/motrix_ball_balance_restored.opset11.onnx"
dst.parent.mkdir(parents=True, exist_ok=True)
if dst.is_symlink() or dst.exists():
    dst.unlink()
dst.symlink_to(exported)
print("SYMLINK:", dst, "->", exported, flush=True)

# 5) copy to notebook OUTPUT_ROOT as well (FASTSAC_ONNX target)
OUT.mkdir(parents=True, exist_ok=True)
import shutil
shutil.copy2(exported, OUT / "motrix_ball_balance_latest.onnx")
print("BALL_PRETRAIN_DONE", flush=True)
