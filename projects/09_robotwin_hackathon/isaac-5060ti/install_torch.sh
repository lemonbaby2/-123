#!/bin/bash
# 安装 torch 2.7.0+cu128 到 WSL Ubuntu-22.04 的系统 Python 3.10。
# 大件（torch / 14 个 nvidia 依赖）已用 curl 预下载到 ~/wheels，这里离线安装；
# 只有 triton 和纯 Python 依赖走阿里云 PyPI（小文件，风险低）。
set -e
W=/home/lizp/wheels
PYPI="https://mirrors.aliyun.com/pypi/simple/"

echo "=== [1/3] 先装 triton + 纯 Python 依赖（阿里云 PyPI，带超时与重试） ==="
sudo pip3 install --no-cache-dir --timeout 60 --retries 10 -i "$PYPI" \
  "triton==3.3.0" "filelock" "typing-extensions>=4.10.0" "sympy>=1.13.3" \
  "networkx" "jinja2" "fsspec" 2>&1 | tail -6

echo
echo "=== [2/3] 离线安装 torch + torchvision + 14 个 nvidia 运行时 ==="
sudo pip3 install --no-index --find-links "$W" \
  "$W/torch-2.7.0+cu128-cp310-cp310-manylinux_2_28_x86_64.whl" \
  "$W/torchvision-0.22.0+cu128-cp310-cp310-manylinux_2_28_x86_64.whl" 2>&1 | tail -12

echo
echo "=== [3/3] 验证 ==="
python3 - << 'PYEOF'
import torch, torchvision
print("torch      :", torch.__version__)
print("torchvision:", torchvision.__version__)
print("cuda avail :", torch.cuda.is_available())
print("device cnt :", torch.cuda.device_count())
if torch.cuda.is_available():
    print("device 0   :", torch.cuda.get_device_name(0))
    print("capability :", torch.cuda.get_device_capability(0))
    x = torch.randn(1024, 1024, device="cuda")
    y = (x @ x).sum().item()
    print("matmul ok  :", y == y and abs(y) > 0)
    # 简单前向+反向，验证 cudnn/cublas 链路
    import torch.nn as nn
    m = nn.Sequential(nn.Linear(256, 256), nn.ReLU(), nn.Linear(256, 10)).cuda()
    out = m(torch.randn(64, 256, device="cuda")).sum()
    out.backward()
    print("cudnn/bwd  : OK")
PYEOF
echo "=== 完成 ==="
