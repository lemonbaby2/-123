# 复现说明 · 双卡 VLA 训练 + Go2 激光建图

本次运行的全部脚本。环境：Windows 11 + WSL2 Ubuntu 22.04，conda 环境 `lerobot`
（Python 3.10 / torch 2.10.0+cu128 / lerobot 0.4.4），另有一个
`geoslam-go2-lab/.venv`（Python 3.12 / mujoco 3.17.0）跑 MuJoCo 仿真。

## 1. 双卡训练（LeRobot）

| 脚本 | 作用 |
|---|---|
| `vla_run_train.sh` | GPU1：SmolVLA + LoRA（rank 16），基座 `lerobot/smolvla_base` |
| `vla_run_train_act.sh` | GPU0：ACT 从零训练 |
| `vla_train_lora.py` | 入口补丁：peft 的 `BaseTuner.get_model_config` 假定 config 有 `.get()`，而 lerobot 的 `PreTrainedConfig` 是 draccus dataclass，会抛 `AttributeError`。补丁让它在拿到非 dict 时返回 `{}`。 |

关键参数（踩过的坑都在这里）：

- `--policy.load_vlm_weights=true` 必须显式给。CLI 构造的 `SmolVLAConfig` 会覆盖基座
  `config.json` 里的同名项，漏掉就等于随机初始化 VLM 主干，LoRA 训练无意义。
- 不要用 `--policy.use_peft=true`。该分支要求 `pretrained_path` 指向**适配器目录**，
  会报 `Can't find 'adapter_config.json'`。正确做法是保持 `use_peft=false` 并改用顶层
  `--peft.method_type=LORA --peft.r=16`。
- `HF_HUB_DISABLE_XET=1` 必需。HF 镜像不代理 `cas-bridge.xethub.hf.co`，不禁用 Xet 会
  在下载 SmolVLM2-500M 权重时 DNS 失败并无限重试。
- 依赖：`transformers==4.57.3`、`huggingface-hub==0.35.3`、`peft==0.17.1`、`num2words`。
  transformers 5.x 会把 hub 顶到 2.x，与 lerobot 0.4.4 的 `hub<0.36.0` 冲突。

启动方式（tmux 常驻，关闭终端不影响）：

```bash
tmux new-session -d -s train1 'bash /root/vla_run_train.sh > /root/vla_outputs/train.log 2>&1'
tmux new-session -d -s train2 'bash /root/vla_run_train_act.sh > /root/vla_outputs/train_act.log 2>&1'
```

## 2. 策略评测与录像

| 脚本 | 作用 |
|---|---|
| `vla_eval.sh` | 非 LoRA 策略（ACT），10 回合并行 |
| `vla_eval_lora.sh` | LoRA 策略，需配合 `vla_eval_patched.py`（同样的 peft 补丁） |
| `vla_eval_patched.py` | 补丁版 `lerobot-eval` 入口 |

```bash
bash /root/vla_eval.sh /root/vla_outputs/act_pusht/checkpoints/last/pretrained_model 0 /root/vla_outputs/eval_act
bash /root/vla_eval_lora.sh /root/vla_outputs/smolvla_pusht_lora/checkpoints/004000/pretrained_model 1 /root/vla_outputs/eval_smolvla4k 5
```

`gym_pusht` 的 `PushtEnv` 默认 `render_mode="rgb_array"`，评测流程会自动把每回合写成
`<output_dir>/videos/pusht_0/eval_episode_*.mp4`（384×384 / 300 帧 / 30 s）。

## 3. Go2 激光建图与语义

| 脚本 | 作用 |
|---|---|
| `go2_simulate.py` | MuJoCo Go2，16×240 射线扫描，体素降采样 + 截断 ICP，输出 `map.ply`、`simulation.json`、RGB 帧 |
| `go2_infer_semantics.py` | SegFormer-B0 (ADE20K) 在仿真 RGB 上推理，输出语义叠加图与 `semantics.json` |
| `render_videos.py` | 自写透视投影 + 画家算法渲染器，把 19.7 万点渲成 MP4（比 matplotlib 快一个量级） |

```bash
cd geoslam-go2-lab
.venv/Scripts/python.exe scripts/simulate.py
.venv/Scripts/python.exe scripts/render_videos.py      # 在 WSL lerobot 环境跑（需要 cv2 + ffmpeg）
```

注意：`geoslam-go2-lab/.venv` 是用 `--system-site-packages` 建在 Anaconda 上的，
Windows 侧 `transformers 5.x` 会 eager import 损坏的 `torchaudio`。语义推理因此改在
WSL 的 `lerobot` 环境里跑（`CUDA_VISIBLE_DEVICES='' python scripts/infer_semantics.py`），
只走 CPU，3 张图 0.33 秒。

## 4. 数据导出

```bash
python export_training.py     # 解析训练日志 → data/training.json（步数 / loss / 梯度范数）
```

正则要允许 `ep:2K` 这种带 K 的字段，否则 1000 回合后会静默失配、曲线停在早期步数。

## 5. 站点

`../index.html` + `style.css` + `app.js` 是纯静态站点，无外部 CDN 依赖
（three.js r169 本地放在 `vendor/`）。点云二进制文件名用 `.dat` 而不是 `.bin`：
部分浏览器扩展/拦截列表会对裸 `.bin` GET 返回 `204 No Content`，前端会读到 0 字节。
