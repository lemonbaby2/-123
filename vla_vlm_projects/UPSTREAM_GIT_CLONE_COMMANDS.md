# VLA / VLM 上游 GitHub 克隆清单（Ubuntu / VSCode）

以下命令建议在 `~/Desktop/VLA_VLM_Engineering_2026/upstreams` 下运行。

```bash
mkdir -p ~/Desktop/VLA_VLM_Engineering_2026/upstreams
cd ~/Desktop/VLA_VLM_Engineering_2026/upstreams

# 1) 你的作品集
git clone https://github.com/lemonbaby2/-123.git lizipeng-embodied-ai-portfolio

# 2) SmolVLA 官方实现所在仓库：Hugging Face LeRobot
git clone --depth 1 https://github.com/huggingface/lerobot.git

# 3) SpatialVLA 官方仓库
git clone --depth 1 https://github.com/SpatialVLA/SpatialVLA.git
# LeRobot 适配分支（单独目录）
git clone --depth 1 -b lerobot https://github.com/SpatialVLA/SpatialVLA.git SpatialVLA-lerobot

# 4) SwiftVLA 官方仓库（截至 2026-08-18 公开主分支仍主要是论文入口/README，作为前沿跟踪）
git clone --depth 1 https://github.com/GigaAI-research/SwiftVLA.git

# 5) StarVLA：稳定分支不要直接跟默认 dev 分支
git clone --depth 1 -b starVLA https://github.com/starVLA/starVLA.git StarVLA-stable
# 如需跟进最新功能，再单独克隆开发分支
git clone --depth 1 -b starVLA_dev https://github.com/starVLA/starVLA.git StarVLA-dev

# 6) Qwen3-VL：语义/空间理解 VLM
git clone --depth 1 https://github.com/QwenLM/Qwen3-VL.git

# 7) Grounded-SAM-2：开放词汇检测 + SAM2 分割/跟踪
git clone --depth 1 https://github.com/IDEA-Research/Grounded-SAM-2.git

# 8) Meta SAM2
git clone --depth 1 https://github.com/facebookresearch/sam2.git

# 9) StreamVGGT：SwiftVLA 相关的流式 4D 几何参考
git clone --depth 1 https://github.com/wzzheng/StreamVGGT.git

# 10) OpenVLA 与 OpenVLA-OFT：经典 VLA / 高效微调参考
git clone --depth 1 https://github.com/openvla/openvla.git
git clone --depth 1 https://github.com/moojink/openvla-oft.git

# 11) Physical Intelligence openpi：pi0/pi0.5 系列开放实现参考
git clone --depth 1 https://github.com/Physical-Intelligence/openpi.git

# 12) NVIDIA GR00T（如果仓库 URL 后续变更，以 NVIDIA 官方页面为准）
git clone --depth 1 https://github.com/NVIDIA/Isaac-GR00T.git
```

VSCode 打开：

```bash
code ~/Desktop/VLA_VLM_Engineering_2026
```

如果系统没有 `code` 命令，在 VSCode 中执行 “Shell Command: Install 'code' command in PATH”，或直接用文件菜单打开目录。
