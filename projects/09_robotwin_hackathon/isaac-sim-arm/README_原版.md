# Isaac Sim 4.5 × Franka 机械臂 RGB-D 分拣复现

> 目标仓库：**Kishan-Gadhavi01/IsaacSim_Robotics_Portfolio** @ `48540c0`
> 复现环境：Isaac Sim **4.5.0.0** + Isaac Lab **2.1.1**，Windows 11 + RTX 4060 8 GB / RTX 5060 Ti 16 GB
> 复现日期：2026-10-26

一句话结论：上游代码写于 Isaac Sim 4.2/4.3（`omni.isaac.*` 旧命名空间），
在本机 4.5 上**原样运行会直接段错误（EXIT=139）**。本包记录了把它完整跑起来、跑对、
并额外跑完一整套 Isaac Lab 机械臂强化学习（PPO / Franka 抓取）的全过程、全部代码与全部产物。

---

## 1. 交付清单

| 类别 | 内容 |
|---|---|
| **复现代码** | `run_rgb_cube_sorter_45.py`（33 KB，自包含，含 4.5 适配 + 双路录像 + 渲染校验） |
| **自定义 experience** | `isaac/isaaclab.arm.sorter.headless.kit`（解决 osqp 段错误的关键件） |
| **后端服务** | `serve.py`（Range 206 / 416、MIME 映射、`/api/info`、`/api/highlights`、`/api/curves`） |
| **前端** | `index.html` + `style.css` + `app.js`（零依赖、原生 canvas 图表、照片灯箱） |
| **媒体生产流水线** | `map_highlights.py`、`make_highlight.sh`、`make_detect.sh`、`make_photos.sh`、`postprocess.sh` |
| **校验工具** | `check_site.py`（资源存在性 + 标签配平 + 占位符残留） |
| **成片** | `videos/sorter_highlight.mp4`（1 分 40 秒精华片）、`videos/sorter_detect.mp4`（14 s 感知讲解）、两路原速完整录屏 |
| **照片** | `photos/` 18 张（8 次抓放 × 搬运中/已入仓 + 开局 + 终局） |
| **数据** | `data/curves_franka_lift.json`（24 条 RL 标量 × 401 点）、`data/highlights.json`（时间轴） |
| **日志** | `logs/run_rgb_cube_sorter.log`（48,938 行）、`logs/train_franka_lift.log`（42,193 行）及两份 summary.json |
| **上游参考** | `repo_isaacsim_robotics_portfolio/`（不含 `media/`，上游演示 GIF/MP4 共 41 MB 未打包） |

---

## 2. 目录结构

```
isaac-arm-sorter-2026-10/
├── run_rgb_cube_sorter_45.py      ★ 主复现脚本（唯一需要跑的脚本）
├── serve.py                       后端：静态服务 + Range + 轻量 API
├── launch.py                      以分离进程启动 serve.py
├── index.html / style.css / app.js  前端站点
├── isaac/
│   └── isaaclab.arm.sorter.headless.kit   ★ 自定义 experience（复制到 IsaacLab/apps/）
├── data/
│   ├── curves_franka_lift.json    RL 训练曲线（TensorBoard EventAccumulator 导出）
│   └── highlights.json            8 次成功放置的步数/时间码
├── videos/                        4 个 mp4（精华片 / 感知讲解 / 宽视角 / 俯视面板）
├── photos/                        18 张 jpg
├── frames/                        海报与关键帧
├── logs/                          原始日志 + summary
├── repo_isaacsim_robotics_portfolio/  上游源码副本（PickPlaceController / Sensor / rmpflow）
├── map_highlights.py              日志 → 时间轴校准
├── make_highlight.sh              精华片剪辑
├── make_detect.sh                 感知流水线拼版
├── make_photos.sh                 逐帧抽照片
├── postprocess.sh                 mpeg4→h264 转码 + 海报/关键帧抽取
└── check_site.py                  站点自检
```

---

## 3. 前置条件

| 项 | 要求 |
|---|---|
| GPU | 支持 RTX 的 NVIDIA 卡，≥ 8 GB 显存（本机 RTX 4060 8 GB 可跑） |
| Isaac Sim | 4.5.0.0，路径示例 `D:\nvidia\Isaac` |
| Isaac Lab | 2.1.1，venv 示例 `D:\nvidia\Isaac\envs\isaaclab-2.1.1`（Python 3.10.11） |
| 磁盘 | ≥ 15 GB（Isaac 本体 + 缓存） |
| 依赖 | `opencv-python`、`numpy`（Isaac Lab venv 内已带） |

---

## 4. 算法设计

### 4.1 场景生成

- Franka Panda + 桌面 + 3 个颜色分拣箱 + 12 个 4 cm 动态立方体（红/绿/蓝各 4）。
- 分拣箱基座位：红 `[0.15,-0.5,0.05]`、绿 `[0.35,-0.5,0.05]`、蓝 `[0.55,-0.5,0.05]`。
- 方块撒布区：`x ∈ [0.40, 0.70]`、`y ∈ [0.15, 0.45]`。
- **拒绝采样**保证互不重叠：新点与所有已有点的 xy 距离必须 `≥ MIN_SEPARATION = 0.08 m`。

### 4.2 视觉感知

```
俯视相机 (0.5, 0, 2.5)，绕 X 转 90°，640×480
        │  RGB ─────────────┐
        │  depth via distance_to_image_plane
        ▼                   ▼
   HSV 转换            depth → 世界坐标
        │
        ├─ 红: H∈[0,10]∪[170,180], S≥120, V≥70
        ├─ 绿: H∈[40,85],  S≥100, V≥100
        └─ 蓝: H∈[90,130], S≥50,  V≥50
        │
        ▼  ROI 裁剪（排除分拣箱区域）
   ROI_X = (100, 600)，ROI_Y = (30, 450)
        │
        ▼  cv2.findContours(RETR_TREE, CHAIN_APPROX_SIMPLE)
   轮廓 → 外接矩形 → 中心点 + 世界坐标（深度反投影）
```

### 4.3 遮挡判定（本仓库的算法核心）

对每个候选方块 `c1`，遍历其它同层方块 `c2`，分别判定两种夹持姿态的净空：

```python
req_clear_body    = GRIPPER_BODY_WIDTH + SAFETY_MARGIN   # 0.045 + 0.005 = 0.050 m
req_clear_fingers = GRIPPER_OPEN_WIDTH + SAFETY_MARGIN   # 0.100 + 0.005 = 0.105 m

same_layer = |c1.z - c2.z| < CUBE_HEIGHT * 0.75          # 0.03 m

lateral   = |c1.x - c2.x|      # 侧向距离
longitud  = |c1.y - c2.y|      # 纵向距离

# Y 向夹持（夹爪沿 y 张开）：侧向要容下夹爪体，纵向要容下张开宽度
standard_blocked = same_layer and lateral < req_clear_body    and longitud < req_clear_fingers
# X 向夹持（旋转 90°）：两个判据互换
rotated_blocked  = same_layer and lateral < req_clear_fingers and longitud < req_clear_body
```

决策：

| 情况 | 结论 | 标注 |
|---|---|---|
| `not standard_blocked` | 可抓，`angle_offset = 0` | 绿框 + 绿竖线 `Y-grip` |
| 仅 `standard_blocked` | 可抓，`angle_offset = π/2` | 绿框 + 紫横线 `X-grip` |
| 两者都 blocked | 跳过 | 红框 `CLUTTER` + 橙框 `BLOCKER` |

**为什么必须两个方向**：夹爪张开 100 mm 但夹爪体只有 45 mm 宽，
同一块方块「竖着夹」被挡时，往往「横着夹」还有空间——一刀切地判"被挡"会白扔掉近一半方块。

### 4.4 抓取控制

`isaacsim.robot.manipulators.examples.franka.controllers.PickPlaceController`
（继承 `manipulators_controllers.PickPlaceController` + `RMPFlowController`）的 10 相位状态机：

```python
events_dt = [0.008, 0.005, 1, 0.1, 0.05, 0.05, 0.0025, 1, 0.008, 0.08]
#             ①      ②    ③   ④    ⑤     ⑥     ⑦      ⑧    ⑨      ⑩
```

| 相位 | 含义 | 本次改写 |
|---|---|---|
| ① | 移向方块上方 | `0.008 → 0.008` |
| ② | 下探到抓取高度 | **`0.005 → 0.0015`（关键修复，见 §7）** |
| ③–⑥ | 闭合 / 抬升 / 移向箱上方 | 保持 |
| ⑦ | 下放到箱内 | `0.0025` |
| ⑧ | 松开 | `1` |
| ⑨⑩ | 回撤退 | 保持 |

> 每相位步数 = `1 / dt`。例如相位② `dt=0.0015` → 667 步。
> RMPFlow 在 0.0015 相位里约 0.00045 m/步，667 步 ≈ 0.30 m 下探行程，正好覆盖初始高度。

### 4.5 码垛

```python
class BinManager:
    offsets = [[0,0], [0,0.06], [0,-0.06], [0.06,0], [0.06,0.06], [0.06,-0.06]]

    def get_place_target(self, color, base_pos):
        count = self.counts[color]
        idx    = count % 6                       # 每层 6 格
        z_stack = (count // 6) * 0.04            # 第三维按层高叠加
        return base + [offsets[idx][0], offsets[idx][1], z_stack + 0.05]
```

即每个箱先铺 6 格（3×2 偏移），满了往上叠一层。

---

## 5. 三处代码改动

| # | 问题 | 原代码 | 改后 |
|---|---|---|---|
| 1 | headless 无窗口 | `simulation_app = SimulationApp({"headless": False})` | `SimulationApp({"headless": True}, experience=自定义 kit 路径)` |
| 2 | import 路径失效（4.5 改名） | `from omni.isaac.franka.controllers import PickPlaceController` | `from isaacsim.robot.manipulators.examples.franka.controllers import PickPlaceController` |
| 3 | `cv2.imshow` 在 headless 下崩 | `cv2.imshow(...)` / `cv2.waitKey(1)` | 双路 `cv2.VideoWriter`（宽视角 1280×720 + 俯视面板 640×1440） |

额外两处工程性修复（不属于原仓库逻辑错误，但不修就没法拿到可信录像）：

| # | 问题 | 修复 |
|---|---|---|
| 4 | **CJK 路径**下 `cv2.imwrite` 返回 `False`、`VideoWriter` 只产出 258 字节空壳（OpenCV 在 Windows 用 ANSI `fopen`） | 先写 `%TEMP%/isaac_arm_stage`（纯 ASCII），收尾用 `shutil.move` 搬回中文目录 |
| 5 | 相机朝向/焦距不对：`Camera.set_world_pose` 默认 `camera_axes="world"`（+X 前 +Z 上），而 USD 相机是 −Z 前 +Y 上 | 传 `camera_axes="usd"`；并按目标视场反算焦距 `focal = aperture / (2·tan(hfov/2))` |

---

## 6. 自定义 experience kit

`isaac/isaaclab.arm.sorter.headless.kit` 是本包最关键的一个文件。两个作用：

### 6.1 绕开 osqp 段错误

默认 `isaacsim.exp.full.kit` 启动时会加载 `isaacsim.robot.wheeled_robots`，
其 `controllers/holonomic_controller.py` 会 import `osqp`，在 Python 3.10.11 + 本机环境下
`osqp._osqp.cp310-win_amd64.pyd` 直接让进程 **EXIT=139**（在任何 `print` 之前就死，所以看不到报错）。

> 单独 `import osqp` 是正常的（0.6.7.post3）。所以不是包坏了，是加载时序问题。

解法：基于 `isaaclab.python.headless.rendering` 自建 kit，**只显式列出真正需要的扩展，不引入 wheeled_robots**。

### 6.2 让渲染真的写回 USD（否则录像是静止图）

`isaaclab.python.headless.rendering` 为了 RL 吞吐量，默认把物理→USD 的写回关掉了：

```toml
[settings.physics]
updateToUsd = true
updateVelocitiesToUsd = true
updateForceSensorsToUsd = true
updateParticlesToUsd = true
fabricUpdateTransformations = true
fabricUpdateVelocities = true
```

不开这几项，仿真状态在推进（末端执行器 z 从 0.30 → 0.09、方块进箱），
但 RTX/Hydra 每帧读到的永远是初始位姿——**录出来是一张静止画面，而且没有任何报错**。

---

## 7. 踩坑铁律（全部实测查证）

### 铁律 1 · 默认 experience 启动脚部错误（EXIT=139）
- **现象**：`SimulationApp({"headless": True})` 不传 experience，进程在启动阶段直接段错误，无任何 Python traceback。
- **根因**：默认 `isaacsim.exp.full.kit` → 加载 `wheeled_robots` → import `osqp` 的 `.pyd` → 崩。
- **判定**：用一个 5 步最小脚本二分定位；单独 `import osqp` 正常，证明是启动时序。
- **修复**：自建 kit，剔除 `isaacsim.robot.wheeled_robots`。

### 铁律 2 · 物理不写回 USD → 录像是一张静止图
- **现象**：仿真正常推进，但两路录像每帧差异 `MAE=1.5`、变化像素仅 7.7%（纯编码噪声）。
- **根因**：`headless.rendering` 默认 `physics.updateToUsd=false`、`fabricUpdateTransformations=false`。
- **修复**：kit 里打开写回开关；同时在脚本里内置**渲染活性校验**——每 300 步打印与首帧的 MAE 与变化像素比例，避免这个坑静默复发。

### 铁律 3 · 状态机相位时长不足 → 夹爪在空中闭合
- **现象**：`Object Dropped Mid-Air!` 反复出现。
- **判定**：加 `[PICK] step=.. event=.. ee=.. grip=.. tgt=.. cubeW=.. dxy=..` 逐 30 步诊断，
  看到末端停在 `z≈0.096`（目标 0.03）就开始闭合，夹爪宽度归 `0.0000`。
- **根因**：`events_dt[1]=0.005` 只给相位② 200 步，RMPFlow 下探约 0.0012 m/步，从 `h1=0.3` 需要 ≈255 步，**行程不够**。
- **修复**：`events_dt[1]` 先改 `0.0025`（400 步）→ 末端到 0.089、夹爪 0.0406（抓住了）；
  修好渲染写回后深度读数变准（方块顶面 0.07 → 0.04），再收紧到 `0.0015`（667 步）。

### 铁律 4 · OpenCV 在中文路径下静默失败
- **现象**：`cv2.imwrite` 返回 `False`；`VideoWriter` 打开成功但只产出 258 字节文件。
- **判定**：同一段代码 `CN path -> False False`、`ASCII path -> True True`。
- **根因**：OpenCV 在 Windows 内部用 ANSI `fopen`，不认 UTF-8 路径。
- **修复**：全程写 `%TEMP%/isaac_arm_stage` 中转，再 `shutil.move` 回中文目录。

### 铁律 5 · 相机四元数要按「相机→世界」构造，不能用 SetLookAt
- **现象**：宽视角相机全黑（`wide_mean=0.0`）；换成 `SetLookAt` 后画面滚了约 45°、地平线竖直。
- **根因**：① `Gf.Matrix4d().SetLookAt()` 给的是 world→camera 的视图旋转，是逆；
  ② `Camera.set_world_pose` 默认 `camera_axes="world"`（+X 前 +Z 上），USD 相机是 −Z 前 +Y 上，内部还会乘一个 `W_U_TRANSFORM`。
- **修复**：显式按 camera→world 构造 `R = [r, u, -f]`（并数值验证 `R·(0,0,-1) == f`），且传 `camera_axes="usd"`。
- **附带**：Isaac `Camera` 默认焦距约 4.2 mm、水平光阑约 2.11 mm（hFOV≈29°），不是 USD 常见的 50 mm；
  直接 `set_focal_length(17)` 会得到 7.1° 长焦。要按目标视场反算，本包用 52° → 焦距 2.1 mm。

---

## 8. 运行方法

### 8.1 一次性准备

```bat
:: 把自定义 kit 放到 IsaacLab apps 目录
copy isaac\isaaclab.arm.sorter.headless.kit  D:\nvidia\Isaac\IsaacLab\apps\
```

### 8.2 冒烟测试（不真分拣，约 1 分钟）

```bat
set CUDA_VISIBLE_DEVICES=0
set OMNI_CONFIG_PATH=D:\nvidia\Isaac\config
D:\nvidia\Isaac\envs\isaaclab-2.1.1\Scripts\python.exe ^
  run_rgb_cube_sorter_45.py --smoke
```

### 8.3 完整分拣（本包结果出处）

```bat
set CUDA_VISIBLE_DEVICES=0
set OMNI_CONFIG_PATH=D:\nvidia\Isaac\config
D:\nvidia\Isaac\envs\isaaclab-2.1.1\Scripts\python.exe ^
  run_rgb_cube_sorter_45.py --max-sorted 9 --max-steps 20000 --timeout-s 2700
```

常用参数：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--max-sorted` | 9 | 期望分拣件数上限 |
| `--max-steps` | 9000 | 仿真步上限 |
| `--timeout-s` | 3600 | 墙钟超时 |
| `--phase0-dt` / `--phase1-dt` | 0.008 / 0.0015 | 相位①②时长（见 §4.4） |
| `--pick-fail-z` / `--pick-fail-open` | 0.03 / 0.06 | 抓取失败判据阈值 |
| `--no-wide` | 关 | 不录宽视角（省一半渲染开销） |
| `--smoke` | 关 | 只验证渲染链路，不分拣 |

### 8.4 起站点

```bat
python launch.py --port 18355
:: 或前台
python serve.py --host 0.0.0.0 --port 18355
```

浏览器打开 `http://127.0.0.1:18355/index.html`；局域网用 `http://<本机IP>:18355/index.html`。

---

## 9. 前端架构

纯静态、零依赖、无构建步骤。

```
index.html   6 个 section：00 总览 / 01 仓库选型 / 02 环境打通 /
             03 完整分拣（含 03.1 照片墙）/ 04 机械臂 RL / 05 踩坑铁律
style.css    CSS 变量主题（深色），响应式断点 1000 / 1100 / 1380 px
app.js       ① 原生 canvas 折线图  ② 训练曲线按需 fetch  ③ 照片墙灯箱  ④ 滚动导航高亮
```

关键实现点：

- **图表**：不引 Chart.js，自己用 `ctx` 画坐标轴/折线/dpr 缩放；
  把 `series` 规格存进 `specs[]`，`resize` 时按新尺寸重绘（否则窗口变化后画布被拉伸模糊）。
- **数据加载**：`fetch('data/curves_franka_lift.json?v=' + Date.now())` 加时间戳绕缓存；
  `file://` 下 fetch 被拦时降级为一行提示，不白屏。
- **灯箱**：事件委托到 `#gallery .gitem img`，`Esc` 或点击背景关闭。
- **降级**：所有 `<video>` 带 `poster`，`controls muted playsinline`，首屏不自动下载视频。

---

## 10. 后端服务（`serve.py`）

`python -m http.server` 不够用的三个原因，逐条对应三个实现：

| 缺口 | 后果 | 本服务的处理 |
|---|---|---|
| 不支持 HTTP Range | 浏览器拖视频进度条失败、Safari 无法播放 | 实现 **206 Partial Content** + `Content-Range`，越界回 **416** + `bytes */size` |
| 缺 MIME 映射 | `.mp4` 可能返回 `application/octet-stream` | 显式 `MIME` 表（html/css/js/json/mp4/jpg/png/woff2/zip…） |
| 无结构化数据接口 | 页面只能读死数据 | `GET /api/info`（运行摘要 + 局域网地址）、`/api/highlights`、`/api/curves` |

其他工程细节：
- `ThreadingHTTPServer` + `daemon_threads`，多客户端并发不互相阻塞。
- 大文件 256 KB 分块流式写，`BrokenPipeError` 静默吞掉（用户拖进度条会主动断连）。
- `launch.py` 用 `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW` 分离启动，
  关掉终端后服务继续跑。

已实测通过的响应：

```
bytes=0-1023        → 206  Content-Range: bytes 0-1023/3540654
bytes=1000000-1000999 → 206  Content-Range: bytes 1000000-1000999/3540654
bytes=99999999-     → 416  Content-Range: bytes */3540654
```

---

## 11. 媒体生产流水线

### 11.1 时间轴校准（`map_highlights.py`）

录像 30 fps、每 2 步写 1 帧 → **60 步/秒**。脚本扫 48,938 行日志，
把每条 `SUCCESS: Sorted <color>` 回溯到最近一条 `[PICK] step=N`，再折成时间码：

| # | 颜色 | 累计 | step | 时间 |
|---|---|---|---|---|
| 1 | green | 1 | 1380 | 23.0 s |
| 2 | red | 1 | 2790 | 46.5 s |
| 3 | blue | 1 | 4170 | 69.5 s |
| 4 | red | 2 | 5580 | 93.0 s |
| 5 | blue | 2 | 6990 | 116.5 s |
| 6 | red | 3 | 8400 | 140.0 s |
| 7 | blue | 3 | 9810 | 163.5 s |
| 8 | green | 2 | 11220 | 187.0 s |

抓放周期 **≈23.4 s**，非常稳定。

### 11.2 精华片（`make_highlight.sh`）

三段切分 → 交叉淡化 → 烧录标题，**三阶段执行**（一次性在同一 filter_complex 里同时解 3 路 333 s 源会 OOM）：

| 段 | 原始时间 | 耗时 | 内容 |
|---|---|---|---|
| A | 2.0 → 23.5 | 21.5 s | 首件（绿）完整流程 |
| B | 90.0 → 165.5 | 75.5 s | 连续 4 件：红 / 蓝 / 红 / 蓝 |
| C | 329.0 → 333.3 | 4.3 s | 终局 8 件入仓定格 |

- A→B 用 `xfade transition=fade`
- B→C 用 **`transition=fadeblack`**——跨了 165 s → 329 s 的时间跳切，
  交叉淡化会让机械臂出现"叠影"，容易被误读成渲染 bug
- 成品：**1280×720 / 30 fps / 99.73 s / 2992 帧 / 3.4 MB**，无变速无补帧

### 11.3 感知讲解片（`make_detect.sh`）

俯视面板是 `np.vstack([vis_rgb, vis_depth, vis_mask])` = 3 行 × 640×480 = 640×1440。
裁 3 行 → 各自 `scale=480:360,pad=640:360` 居中留黑边 → 2×2 `xstack` 成 1280×720，
第 4 格是判读图例。成品 14 s / 0.55 MB。

> 中途踩过一次坑：一开始按 4 行 × 360 切分，把深度图当成"红色掩膜"标注出去了。
> 回头读源码 `np.vstack([vis_rgb, vis_depth, vis_mask])` 才发现只有 3 行、每行 480。

### 11.4 照片（`make_photos.sh`）

每个成功点抽 2 张：`成功前 3.5 s`（搬运中，工件在夹爪里飞向目标仓）+ `成功后 0.3 s`（已入仓）。
另加开局全景与终局全景，共 18 张。

### 11.5 转码（`postprocess.sh`）

OpenCV 的 `mp4v` 编码浏览器不能内联播放 → 统一转 `libx264 / yuv420p / +faststart`。
俯视面板是每步 1 帧（60 Hz）写入却按 30 fps 编码，会变成半速 → 用 `-r 60` 声明输入帧率修正。

---

## 12. 实测结果

### 12.1 RGB-D 分拣

| 指标 | 值 |
|---|---|
| 分拣成功 | **8** 件 |
| 颜色分布 | 红 3 / 绿 2 / 蓝 3 |
| 仿真步数 | 20,000 步 / 333.3 s 仿真时间 |
| 墙钟耗时 | 821 s（≈24.2 fps，含两路 60 Hz 渲染） |
| 抓取尝试 | 11 次（含失败重试） |
| 生成方块 | 12 个 |

**为什么只做了 8 个（重要）**：收尾阶段日志里 `blocked by neighbor` 出现 388 次（最后 400 行内）。
剩余方块的同层邻域净空**同时**不满足 Y-grip 与 X-grip 两套判据，被判定为 `CLUTTER` 主动跳过，
`SEARCH` 一直找不到安全下爪点，最终在 20,000 步上限退出。
**这是脚本的遮挡判定在起作用，不是抓取失败。**

### 12.2 Isaac Lab 机械臂强化学习

`Isaac-Lift-Cube-Franka-v0` / RSL-RL PPO / 2048 envs / RTX 5060 Ti：

| 指标 | 值 |
|---|---|
| 迭代 | **1500 / 1500**，25 min 07 s，EXIT=0 |
| 总经验步数 | 73,728,000（≈51,848 steps/s） |
| mean_reward | 0.7064 → **135.9303** |
| episode_length | 18.65 → 250.0（已饱和） |
| position_error | 0.2215 → 0.1006 |
| lifting_object | 0.1175 → 13.1134 |
| object_goal_tracking | 0.0198 → 12.3817 |
| value_function | 0.0226 → 0.4988 |
| mean_noise_std | 1.0023 → 0.3901 |
| object_dropping | **全程 0.0000** |

`value_loss` 先升后降、最终 0.4988，属于回报量级变大后的正常现象，不是发散。

---

## 13. 已知限制

1. **未做 sim-to-real**：全部结果来自仿真，无真实机械臂验证。
2. **遮挡判定只看同层**：`same_layer` 用 `dz < 0.75×边长` 判定，叠放场景（上层压下层）不会判为遮挡。
3. **抓取失败无重试策略**：失败后由外层循环重新 `SEARCH`，没有局部重试或换向重试。
4. **相机外参硬编码**：俯视相机位置/朝向写死，改变了场景布局要重标 ROI。
5. **上游 `media/` 未打包**：41 MB 的上游演示 GIF/MP4 与本复现无关，已剔除；见上游仓库链接。
6. **日志较大**：`logs/` 原始日志约 7 MB（未裁剪，供逐帧核对）。

---

## 14. 许可与出处

- 上游代码：`Kishan-Gadhavi01/IsaacSim_Robotics_Portfolio`（见其 `README.md` 与许可声明）。
- 本包新增内容（4.5 适配脚本、自定义 kit、前端站点、后端服务、媒体流水线、文档）为复现过程产物。
- Isaac Sim / Isaac Lab 为 NVIDIA 专有软件，需自行获取授权；本包不含其二进制。
