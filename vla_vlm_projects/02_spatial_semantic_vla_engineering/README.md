# 工程 2：Qwen3-VL + Grounded-SAM2 + RGB-D + SpatialVLA/StarVLA 语义动作桥

## 目标

这个工程解决“语义模型知道是什么，但机器人不知道它在三维哪里；动作模型会动，但输入坐标不可信”的工程断层。

链路：

`RGB / Depth → 内参 + 深度对齐 → Qwen3-VL 任务语义 → Grounded-SAM2 目标框/掩码 → mask 内深度鲁棒统计 → 反投影到 Camera 3D → T_base_camera 外参 → Base 3D → grasp/approach waypoint → VLA adapter → 安全门控`。

其中：

- Qwen3-VL 负责高级语义、2D/3D grounding 辅助、任务拆解；
- Grounded-SAM2 负责开放词汇目标定位、像素级掩码和视频跟踪；
- RGB-D 提供 metric depth；
- SpatialVLA 适合研究 3D 空间增强动作；
- StarVLA 适合作为统一训练/动作头/多 benchmark 工程框架；
- SwiftVLA 作为 4D 动态前沿参考，但在源码完整度达到工程要求前不作为本项目默认依赖。

## 1. RGB-D / 相机标定

如果使用 RealSense 等 RGB-D 相机，优先读取厂商出厂内参和 depth-to-color extrinsic，并在现场验证。外接 USB 相机或更换镜头后仍建议用棋盘格/Charuco 标定 RGB 内参。

像素反投影：

```text
Xc = (u - cx) * Z / fx
Yc = (v - cy) * Z / fy
Zc = Z
```

随后：

```text
p_base = T_base_camera * p_camera
```

注意这里的 `T_base_camera` 方向。面试最常见错误是把 `T_camera_base` 直接左乘而不求逆。

## 2. 语义模型到几何模型

VLM 输出应该是“任务语义/候选类别/属性/约束”，而不是直接相信它给的毫米级坐标。像素级位置交给 grounding/segmentation，metric 位置交给标定后的深度和几何。

例如：

1. Qwen3-VL：`找到红色杯子，确认它不是夹具，给出目标描述`；
2. GroundingDINO：文本 `red cup` 得到 box；
3. SAM2：box → mask，并跨视频跟踪；
4. mask 内深度做中位数/分位数过滤，拒绝 0、NaN 和飞点；
5. 取掩码几何中心/可抓取区域，得到 Camera 3D；
6. 外参变换到 Base；
7. 生成 pre-grasp / grasp / retreat waypoint；
8. 再交给 SpatialVLA / SmolVLA / StarVLA action head 或传统 MoveIt2 控制。

## 3. 运行 dependency-free 演示

```bash
python src/pipeline.py
python src/visualize_semantic_scene.py --output artifacts/semantic_scene.svg
```

演示会把几个像素 + 深度反投影到三维并做外参平移，再输出可视化 SVG。

## 4. 真实依赖安装

```bash
bash scripts/setup_upstreams.sh
```

脚本会克隆 Qwen3-VL、Grounded-SAM-2、SAM2、SpatialVLA 和 StarVLA stable；大权重按上游文档手动选择下载，避免一键脚本直接吃满磁盘。

## 5. SpatialVLA 参考

官方 SpatialVLA 基于 PaLiGemma2，提出 Ego3D Position Encoding 和 Adaptive Action Grids。官方 README 给出 Hugging Face 直接推理和 LoRA fine-tune；工程上应把其动作输出解码所需的 `unnorm_key`、action statistics 与目标机器人数据配置锁定版本。

## 6. StarVLA 参考

StarVLA 更像 VLA 研发底座：VLM/world-model backbone、action head、训练 recipe、benchmark 解耦。工程接入新机器人时，优先统一 observation/action schema、数据集 adapter 和 evaluation，再换 backbone；不要一开始就改模型内部。

## 7. 面试一句话

“VLM 的语义精度和机器人的几何精度是两套问题。我让 VLM 负责‘是什么/要做什么’，让标定后的 RGB-D + 分割负责‘三维在哪里’，然后把结果转换到 base frame，再通过 VLA 或 MoveIt2 产生动作；任何一步置信度不足就进入重观测或人工接管，而不是让大模型瞎猜坐标。”
