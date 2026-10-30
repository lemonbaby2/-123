#!/bin/bash
# 预下载 torch 2.7.0+cu128 的 14 个 NVIDIA 运行时依赖 wheel。
# 走阿里云 pytorch-wheels 镜像，用 curl 断点续传 —— 比 pip 在弱网下稳定得多。
BASE="https://mirrors.aliyun.com/pytorch-wheels/cu128"
OUT=/home/lizp/wheels
mkdir -p "$OUT"

FILES="
nvidia_cublas_cu12-12.8.3.14-py3-none-manylinux_2_27_x86_64.whl
nvidia_cuda_cupti_cu12-12.8.57-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
nvidia_cuda_nvrtc_cu12-12.8.61-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl
nvidia_cuda_runtime_cu12-12.8.57-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
nvidia_cudnn_cu12-9.7.1.26-py3-none-manylinux_2_27_x86_64.whl
nvidia_cufft_cu12-11.3.3.41-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
nvidia_cufile_cu12-1.13.0.11-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
nvidia_curand_cu12-10.3.9.55-py3-none-manylinux_2_27_x86_64.whl
nvidia_cusolver_cu12-11.7.2.55-py3-none-manylinux_2_27_x86_64.whl
nvidia_cusparse_cu12-12.5.7.53-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
nvidia_cusparselt_cu12-0.6.3-py3-none-manylinux2014_x86_64.whl
nvidia_nccl_cu12-2.26.2-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
nvidia_nvjitlink_cu12-12.8.61-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl
nvidia_nvtx_cu12-12.8.55-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
"

printf "%s\n" $FILES | xargs -P 4 -I{} sh -c \
  "curl -sSL --retry 8 --retry-delay 2 --retry-all-errors --max-time 900 -C - -o $OUT/{} $BASE/{}"

echo "=== 下载完成，共 $(ls $OUT/*.whl 2>/dev/null | grep -c nvidia) 个 nvidia wheel ==="
ls -lh "$OUT"/*.whl | grep nvidia
