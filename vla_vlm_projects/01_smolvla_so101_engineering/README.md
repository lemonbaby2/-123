# 工程 1：SmolVLA + LeRobot + SO-101 标定与动作安全链

## 目标

把一个真实的 VLA 项目拆成面试官能检查的工程链：

`Leader/Follower 舵机标定 → 双相机内参 → Eye-to-Hand/Hand-Eye 外参 → LeRobot 数据采集 → SmolVLA 微调 → action chunk → 安全门控 → 机器人控制器`。

SmolVLA 的官方实现位于 `huggingface/lerobot`。本目录不复制其权重，而提供工程 glue code、标定工具、dry-run 策略和可视化。

## 1. SO-101 舵机标定

官方 LeRobot 的典型命令：

```bash
# follower
lerobot-calibrate \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM0 \
  --robot.id=so101_follower_lab

# leader
lerobot-calibrate \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM1 \
  --teleop.id=so101_leader_lab
```

标定时先把关节放在各自行程中位附近，随后逐关节扫完整行程，让软件建立原始舵机读数到统一关节坐标的映射。不要把“电机零位标定”和“相机手眼标定”混为一谈：前者解决关节角一致性，后者解决相机坐标和机器人基座/末端坐标之间的 SE(3) 变换。

## 2. 相机内参

安装：

```bash
pip install numpy opencv-python
```

采集 15~30 张不同姿态棋盘格图像后：

```bash
python calibration/calibrate_camera_intrinsics.py \
  --images 'data/calib/cam0/*.png' \
  --cols 9 --rows 6 --square-size 0.024 \
  --output config/cam0_intrinsics.json
```

输出包括 `K`、畸变系数和重投影 RMS。工程验收不要只说“标定成功”，至少记录 RMS、图像分辨率、棋盘规格、有效图像数。

## 3. 手眼 / Eye-to-Hand 外参

本项目提供 `calibrate_hand_eye.py`，输入多组：

- `T_base_gripper`：机器人正运动学得到；
- `T_camera_target`：相机观察固定标定板，利用 solvePnP/AprilTag/Charuco 得到。

OpenCV `calibrateHandEye` 可解 Eye-in-Hand；Eye-to-Hand 需要按坐标定义进行逆变换/交换变量，面试时必须先画坐标系再写公式，不能死记函数参数。

## 4. SmolVLA 训练链

```bash
cd upstreams/lerobot
python -m pip install -e '.[smolvla,feetech]'

# 数据录制/推送步骤按 LeRobot 当前 CLI 为准；训练核心示意：
lerobot-train \
  --policy.type=smolvla \
  --dataset.repo_id=<HF_USER>/<YOUR_DATASET> \
  --policy.load_vlm_weights=true \
  --output_dir=outputs/smolvla_so101 \
  --steps=20000 \
  --batch_size=16
```

建议从单任务、50 个左右高质量 episode 起步，再做位置、光照、背景、抓取方向等分层覆盖。动作数据的时间戳、相机帧、关节状态必须同步，否则 VLA 训练会把“延迟”学进策略。

## 5. 动作安全门控

`src/pipeline.py` 演示：

- action chunk 长度检查；
- 每维动作上下界 clamp；
- 相邻动作最大步长限制；
- 置信度/视觉有效性门控；
- dry-run 输出。

真实项目还需要 joint limit、速度、加速度、jerk、力矩/电流、碰撞、急停、控制 watchdog。

## 6. 可视化

```bash
python src/visualize_action_chunk.py --output artifacts/action_chunk.svg
```

输出标准 SVG，可在浏览器、VSCode 或 GitHub 直接查看，用于解释 VLA 预测的动作 chunk 是否存在突跳。

## 7. 面试一句话

“我不把 VLA 当成一个从图像直接吐电机 PWM 的黑盒，而是把它放在严格标定和控制约束之间：相机/关节先统一坐标，VLA 只预测归一化动作，再经过反归一化、限幅、时序平滑、碰撞/急停状态机后交给底层控制器。”
