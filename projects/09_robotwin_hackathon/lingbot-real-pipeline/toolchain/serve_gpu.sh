#!/bin/bash
# LingBot-VLA 2.0 GPU 推理服务器一键启动
#
# 用法:
#   bash serve_gpu.sh                                   # 默认路径/端口，官方加载方式
#   bash serve_gpu.sh --model_path DIR --port 8006
#   bash serve_gpu.sh --low-mem true                    # 主机内存 <56GB 时必须开
#   bash serve_gpu.sh --length 25                       # 显存紧张时缩短动作块
#   bash serve_gpu.sh --moe-layout eager                # Blackwell 上 fused kernel 跑不了时用
#
# 前置: 已装 torch(CUDA) + 依赖，且已跑过 deploy/apply_patches.py
set -uo pipefail

MODEL_PATH="${MODEL_PATH:-/data/lingbot_models/robotwin_ckpt/hf_ckpt/lingbot-vla-v2-6b-robotwin}"
PORT="${PORT:-8006}"
BF16="${BF16:-true}"
LENGTH="${LENGTH:-50}"
LOW_MEM="${LINGBOT_LOW_MEM:-0}"
MOE_LAYOUT="${LINGBOT_MOE_LAYOUT:-fused}"
REPO="${REPO:-$(cd "$(dirname "$0")/.." && pwd)}"

while [ $# -gt 0 ]; do
  case "$1" in
    --model_path) MODEL_PATH="$2"; shift 2;;
    --port)       PORT="$2"; shift 2;;
    --bf16)       BF16="$2"; shift 2;;
    --length)     LENGTH="$2"; shift 2;;
    --low-mem)    LOW_MEM="$2"; shift 2;;
    --moe-layout) MOE_LAYOUT="$2"; shift 2;;
    -h|--help) sed -n '2,12p' "$0"; exit 0;;
    *) echo "unknown arg: $1"; exit 1;;
  esac
done

export LINGBOT_LOW_MEM="$LOW_MEM"
export LINGBOT_MOE_LAYOUT="$MOE_LAYOUT"

echo "=== LingBot-VLA 2.0 推理服务器 ==="
echo "repo      : $REPO"
echo "model_path: $MODEL_PATH"
echo "port      : $PORT   bf16: $BF16   chunk_len: $LENGTH"
echo "low_mem   : $LOW_MEM   moe_layout: $MOE_LAYOUT"

# --- 模型目录检查 ---
[ -f "$MODEL_PATH/model.safetensors.index.json" ] || { echo "ERR: 模型目录缺少 index.json"; exit 1; }
N_SHARD=$(ls "$MODEL_PATH"/model-*.safetensors 2>/dev/null | wc -l)
[ "$N_SHARD" -ge 1 ] || { echo "ERR: 模型目录无 safetensors"; exit 1; }
echo "shards    : $N_SHARD"

# --- cli yaml 检查（官方按三级上找；补丁已加二级回退）---
CLI_YAML="$(dirname "$(dirname "$(dirname "$MODEL_PATH")")")/lingbotvla_cli.yaml"
CLI_YAML_ALT="$(dirname "$(dirname "$MODEL_PATH")")/lingbotvla_cli.yaml"
if [ -f "$CLI_YAML" ]; then
  echo "cli yaml  : $CLI_YAML (三级，官方位置)"
elif [ -f "$CLI_YAML_ALT" ]; then
  echo "cli yaml  : $CLI_YAML_ALT (二级，依赖 apply_patches 的回退补丁)"
else
  echo "ERR: lingbotvla_cli.yaml 未找到。已查找:"
  echo "     $CLI_YAML"
  echo "     $CLI_YAML_ALT"
  echo "     修复: cp <你的yaml> $CLI_YAML"
  exit 1
fi

# --- 硬件预算检查 ---
python - <<'PY'
import os, sys
try:
    import torch, psutil
except ImportError as e:
    print(f"ERR: 缺依赖 {e}")
    sys.exit(1)

N_PARAM = 6.38e9
GB = 1e9
print(f"torch     : {torch.__version__}  cuda_avail={torch.cuda.is_available()}")
if not torch.cuda.is_available():
    print("ERR: CUDA 不可用。装 GPU 版 torch:")
    print("     pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128")
    sys.exit(1)

for i in range(torch.cuda.device_count()):
    p = torch.cuda.get_device_properties(i)
    print(f"  GPU{i}: {p.name}  {p.total_memory/GB:.1f}GB  sm_{p.major}{p.minor}")

free = torch.cuda.mem_get_info()[0] / GB
need_vram = N_PARAM * 2 / GB + 1.5
print(f"  free VRAM : {free:.1f}GB   需要约 {need_vram:.1f}GB (bf16 + 开销)")
if free < need_vram:
    print(f"  WARN: 显存不足，空闲 {free:.1f}GB < 需要 {need_vram:.1f}GB → 会 OOM")

low_mem = os.environ.get("LINGBOT_LOW_MEM", "0") == "1"
vm = psutil.virtual_memory()
need_ram = 13.5 if low_mem else 52.0
print(f"  RAM total : {vm.total/GB:.1f}GB   available: {vm.available/GB:.1f}GB")
print(f"  加载峰值需要约 {need_ram:.0f}GB（low_mem={'on' if low_mem else 'off'}）")
if vm.total / GB < need_ram:
    hint = "→ 加 --low-mem true 可降到 ~14GB" if not low_mem else "→ 低内存模式仍需 ~14GB"
    print(f"  WARN: 主机内存可能不足 {hint}")

p = torch.cuda.get_device_properties(0)
if p.major >= 12:
    try:
        arch = torch.cuda.get_arch_list()
    except Exception:
        arch = []
    tag = f"sm_{p.major}{p.minor}"
    if arch and not any(tag in a for a in arch):
        print(f"  WARN: torch 未编译 {tag} kernel → 必须换 cu128+ wheel")
    print(f"  NOTE: Blackwell {tag}：flash-attn 支持不成熟，自动走 sdpa/eager；")
    print(f"        若 fused MoE 的 triton kernel 报错，改用 --moe-layout eager")
PY

cd "$REPO" || exit 1

echo "--- 启动 server（Ctrl+C 停止）---"
exec python -u deploy/lingbot_vla_v2_policy.py \
  --model_path "$MODEL_PATH" \
  --port "$PORT" \
  --use_length "$LENGTH" \
  --chunk_ret true \
  --use_bf16 "$BF16" \
  --use_fp32 false \
  --use_compile false
