# VLA / VLM / 语义模型 / 动作模型工程化面试笔记（2026-08-18）

> 目标：这份笔记不是“背模型名字”，而是让你面对机器人算法、具身智能、VLA、VLM、SLAM/3D视觉、机器人系统工程岗位时，能把模型、标定、数据、控制、安全、部署串成一个工程闭环。本文同时总结仓库原有 8 个项目和新增 2 个 VLA/VLM 项目，重点准备面试追问。

## 0. 先建立总框架：VLM、VLA、语义模型、动作模型到底分别解决什么

VLM（Vision-Language Model）的本质是把视觉观测和语言放进统一表示空间，完成识别、描述、OCR、问答、grounding、视频理解、任务推理等。它通常回答“看到了什么、目标是什么、应该做哪一类事情”。机器人里常把 VLM 放在高层语义和任务规划层，但 VLM 并不天然保证毫米级几何准确，也不天然知道某个相机像素对应机器人 base frame 的三维坐标。

VLA（Vision-Language-Action）在 VLM 的视觉语言表示之上引入机器人状态和动作输出。输入可能包括多相机 RGB、深度、proprioception、关节状态、末端状态、语言指令；输出可能是离散 action token、连续 action chunk、flow matching 生成的连续轨迹、末端位姿增量或关节动作。VLA 解决的是“从观测和指令到动作策略”的学习问题。

语义模型在工程里不一定只有 VLM。开放词汇检测 GroundingDINO、分割 SAM2、3D 语义场、CLIP embedding、目标跟踪都属于语义感知的重要组件。动作模型也不一定必须是 VLA；ACT、Diffusion Policy、传统 IK/MoveIt2、MPC、轨迹优化、行为树都可能承担动作生成或动作执行。

一个成熟机器人系统应该分层：感知层先解决同步和标定，语义层解决“是什么”，几何层解决“在哪里”，策略层解决“做什么动作”，控制层解决“电机怎样稳定执行”，安全层负责“什么时候绝对不能执行”。面试时如果能主动讲出这一分层，通常比只背某个 VLA 结构更像工程候选人。

## 1. 为什么标定是 VLA 工程里必须讲清楚的核心

很多候选人把 VLA 理解成“摄像头接大模型，大模型直接控制机械臂”。真实工程中，这种描述是不合格的。只要涉及跨相机、跨机器人、三维抓取或动作数据复用，就绕不开标定。

第一类是机器人关节/舵机标定。例如 SO-101 leader/follower 的原始编码器读数、零位、方向和有效范围必须映射到一致的关节表示。LeRobot 的校准流程要求机械臂先到关节范围中部附近，再逐关节扫完整范围，用于建立统一位置映射。它解决的是“两个机械臂在相同物理姿态时，数值是否一致”。

第二类是相机内参标定。针孔模型的 K 矩阵包含 fx、fy、cx、cy，畸变系数描述镜头径向和切向畸变。只要要做像素到射线、PnP、3D 反投影、手眼标定，就必须知道内参。验收要记录图像尺寸、棋盘/Charuco 尺寸、有效视角数量、重投影误差 RMS，而不是只保存一个 YAML。

第三类是相机和机器人之间的外参。Eye-in-Hand 表示相机安装在末端，常求 T_gripper_camera；Eye-to-Hand 表示相机固定在环境中，常求 T_base_camera。两者变量关系不同。工程上先画坐标系，再写齐次变换链。例如物体点 p_camera 转到机器人基座：p_base = T_base_camera p_camera。如果手里拿到的是 T_camera_base，则必须求逆。

第四类是多相机/深度对齐。RGB 和 depth 传感器通常有各自内参和相对外参。深度未对齐到彩色图时，不能直接拿 RGB 像素索引 depth。RealSense 等设备可以提供 factory calibration，但现场仍应做点云与标定板验证，尤其换了镜头、机械安装件或设备受过撞击时。

第五类是时间标定/同步。VLA 数据里“图像 t、关节状态 t、动作 t+Δ”是否一致直接决定模型学到的是正确控制还是延迟补偿。USB 相机、ROS topic、机械臂状态和控制命令都可能有不同时间基准。至少要记录 timestamp、采样率、掉帧率、端到端延迟和同步策略。

## 2. SpatialVLA：为什么它适合做 3D 空间动作研究

SpatialVLA 的核心不是“简单加一个深度图”，而是把空间表示和动作表示都重新设计。论文提出 Ego3D Position Encoding，把三维信息注入 VLA 的视觉输入；同时用 Adaptive Action Grids 对空间机器人动作做自适应离散化，试图让不同机器人之间复用空间动作知识。官方模型以 PaLiGemma2 为 VLM backbone，并在大规模真实机器人数据上预训练。

工程上要注意三点。第一，SpatialVLA 官方 4B 模型对显存仍有明显要求，官方快速推理说明约需要 8.5GB GPU memory；因此 8GB 显存笔记本不应直接承诺“无脑跑满”，需要考虑更小模型、量化、offload 或换服务器。第二，真实机器人 fine-tune 时必须正确设置数据集 observation/action schema、action statistics 和 unnorm key，否则模型能出 tensor，但动作物理含义错误。第三，Adaptive Action Grid 的优势需要建立在动作坐标定义一致的基础上，标定和 action normalization 仍然不能省略。

面试可回答：SpatialVLA 与普通 2D VLA 的差别，不是它“看得更清楚”，而是它显式增强了三维空间编码，并重新考虑动作空间离散化，使跨机器人空间动作迁移更自然。若在精密插入任务中落地，我会额外使用 RGB-D/双目几何、手眼标定和末端力控闭环，因为纯视觉策略不应该承担最后毫米级接触稳定性。

## 3. SmolVLA：为什么更适合做你的第一套真机 VLA

SmolVLA 的价值在于把 VLA 的门槛降到一个真实开发者能够试验的范围。官方实现直接进入 LeRobot 生态，能复用机器人驱动、数据集、teleoperation、训练 CLI 和 evaluation。模型是约 450M 级别的紧凑 VLA，输入多视角图像、机器人状态和语言，输出连续动作 chunk，并使用 flow matching 类型的动作生成机制。

工程上 SmolVLA 最大优势不是“参数小”本身，而是生态完整：SO-100/SO-101 等低成本机械臂、摄像头、数据采集、Hugging Face 数据集、策略训练、checkpoint 都在同一套框架。你可以真正回答“我如何从 0 采集 50 个 episode、如何做标定、如何训练、如何回放、如何评估成功率”。这比只在 benchmark 上跑一个大模型更像机器人产品开发。

但要避免夸张。450M 并不意味着任何普通笔记本都能舒服完成训练。训练显存、batch、图像尺寸、混合精度、数据规模、是否冻结 VLM 都会影响成本。比较稳妥的说法是：它显著降低了 VLA 训练和推理的资源门槛，并支持消费级硬件部署方向；正式训练仍建议根据 GPU 实际显存做 batch 和精度规划。

## 4. SwiftVLA：为什么先进，但暂时不把它作为主工程

SwiftVLA 聚焦轻量 VLA 的时空动态能力。论文引入预训练 4D visual geometry transformer 和 temporal cache，从连续图像抽取 4D 特征；通过 Fusion Tokens 融合 2D 与 4D 表示，并使用 future prediction objective。其 mask-and-reconstruct 设计让模型训练时学习 4D 信息，同时目标是在推理阶段尽量降低额外 4D 分支开销。

它特别适合解释动态抓取、传送带、移动物体等问题：静态单帧 VLA 很容易把“物体现在在哪里”当成全部信息，但实际控制需要知道速度、运动趋势和机械臂到达时间。StreamVGGT 一类流式 4D 几何模型提供了在线时序几何记忆的思路。

然而工程选型不仅看论文。到本次整理日期，官方 SwiftVLA GitHub 主分支公开内容仍主要是论文入口 README，没有形成像 LeRobot/SpatialVLA/StarVLA 那样完整的可直接训练/部署源码树。因此面试里可以把 SwiftVLA 放在“前沿技术储备/拟复现”而不是“我已完整落地”的栏目。这个区分能体现你重视证据边界。

## 5. StarVLA：为什么它更像 VLA 研发操作系统

StarVLA 的优势是模块化。它把 backbone、action head、dataloader、trainer、config、evaluation 拆开，支持 VLM backbone、world model backbone 以及不同 action decoding 范式。这样研究者不用每换一个 action head 就重写全套训练框架。

工程上可以把它理解成“VLA 研发平台”，而不是某一个固定权重。它适合做：统一多 benchmark、统一机器人数据格式、比较 FAST/OFT/flow matching/GR00T 风格动作头、做 cross-embodiment co-training、做多模态 co-training、接真实机器人。它还提供 stable 和 dev 分支，面试里要强调生产复现优先锁 stable branch/commit，而不是永远追默认开发分支。

StarVLA 的 co-training 价值在于：纯机器人动作数据昂贵，但互联网图文/多模态数据丰富。把 VLM 语义能力和机器人动作学习放进统一训练 recipe，可以研究如何在保持视觉语言能力的同时学习动作，而不是 fine-tune 后出现严重语义遗忘。但实际共训要处理采样比例、loss 权重、冻结策略、不同数据 domain、动作缺失样本如何 masking 等问题。

## 6. Qwen3-VL：为什么适合作为工程语义前端

Qwen3-VL 提供从 2B 到更大规模的不同模型尺寸，具备图像、视频、空间理解、2D grounding、3D grounding 等能力。对机器人来说，一个非常有用的思路是：让 Qwen3-VL 做“任务语义+候选目标+关系判断”，让几何模型做“精确位置”。例如“拿左边红色杯子而不是蓝色夹具”，VLM 可以理解属性和关系；随后 GroundingDINO/SAM2 把文字目标变成稳定 mask；深度相机和标定负责 metric 3D。

为什么不直接让 VLM 输出 XYZ？因为大模型的 grounding 坐标可能受 resize、tokenization、训练坐标规范、视角和深度歧义影响。对精密抓取，最稳健的方法仍是显式几何：mask + depth + intrinsics + extrinsics。VLM 是语义专家，不是自动替代所有几何算法。

## 7. Grounded-SAM2：为什么是“语义到像素”的重要桥梁

Grounded-SAM2 把开放词汇 grounding 和 SAM2 分割/视频跟踪组合起来。GroundingDINO 或 Florence/DINO-X 给出文本条件目标，SAM2 把 box/point prompt 扩展到像素级 mask，并可在视频序列中跟踪目标。

机器人抓取里 mask 比 bbox 更有价值，因为可以在 mask 内统计深度，避免背景桌面深度污染；可以估计物体轮廓和主方向；可以对动态目标做连续跟踪。工程时要过滤 mask 边缘、0 depth、飞点，并对深度做中位数/分位数统计。bbox 中心的单点深度很容易恰好落在空洞或反光区域。

## 8. “语义 → 3D → 动作”完整数学链

假设从语义模型获得目标 mask M，并从对齐后的深度图 D 获得目标像素 (u,v) 及深度 Z。相机内参 K = [[fx,0,cx],[0,fy,cy],[0,0,1]]。反投影：X=(u-cx)Z/fx，Y=(v-cy)Z/fy，Z=Z。得到 p_c。

若 Eye-to-Hand 标定得到 T_b_c，则 p_b = T_b_c p_c。对于抓取，不应只生成一个点，还要估计 approach direction、gripper orientation、pre-grasp offset、collision clearance。若目标表面法向可由局部点云 PCA 得到，可以构造末端姿态 R_b_e；再交给 IK/MoveIt2 或 VLA action head。

如果使用 VLA 直接输出末端增量 Δx,Δy,Δz,Δroll,Δpitch,Δyaw,gripper，仍要知道这些动作是 base frame、tool frame 还是归一化 robot frame。所有动作都必须做 unnormalize，再限幅。任何 action statistics 和训练时不同都会造成灾难性尺度错误。

## 9. Action Chunk、ACT、Diffusion、Flow Matching、Autoregressive Token 有什么差别

单步动作策略每一帧只预测一个动作，闭环强但容易高频抖动且推理成本高。Action Chunk 一次预测未来 H 步，能利用局部时序结构，提高控制流畅度和推理吞吐，但 horizon 太长会降低闭环响应。

ACT 用 Transformer 预测 action chunk，适合 imitation learning。Diffusion Policy 把动作轨迹视作扩散生成问题，能表达多模态动作分布。Flow Matching 与扩散类似也是连续生成思想，但通过学习向量场实现从噪声分布到动作分布的变换，很多新 VLA 采用这一类 action expert。Autoregressive action token 则把动作离散化成 token，直接复用语言模型解码范式，但量化误差和 token 序列长度是关键问题。

面试回答不要说哪个绝对最好。接触丰富、动作多模态任务可能更喜欢生成式连续策略；高频实时控制要关注推理步数和 chunk；跨机器人统一动作需要关注 action representation 和 normalization。

## 10. VLA 为什么仍然需要传统机器人学

VLA 不会让 SE(3)、坐标变换、运动学、控制理论失效。相反，大模型越强，系统工程越需要传统模块给它边界。至少要掌握：DH/URDF、FK/IK、Jacobian、奇异位形、四元数、轴角、李群 SE(3)、轨迹插值、PID/阻抗/导纳、碰撞检测、MoveIt2、TF2、时间同步。

举例：VLA 预测“向前 5cm 抓取”。如果“前”是在 camera frame 还是 tool frame 不清楚，动作就可能错误。如果末端接近奇异位形，IK 可能跳解。如果抓取插入阶段没有力控，视觉误差 2mm 也可能卡死。优秀回答应该说：VLA 负责策略先验，传统几何和控制负责可执行性与稳定性。

## 11. 数据工程：VLA 成败往往不在模型，而在数据

一个真实数据 episode 至少包含：多相机帧、机器人状态、动作、语言任务、timestamp、episode success/failure、设备和 calibration version。最好还记录软件 commit、机器人序列号、相机序列号、operator、异常码。

数据划分不要随机把同一条连续轨迹相邻帧分到 train/test，这会造成泄漏。更好的划分单位是 episode、场景、物体实例、日期或机器人。泛化评估可分：seen object/seen position、seen object/unseen position、unseen object、lighting shift、camera perturbation、background shift。

失败数据是否使用取决于训练范式。纯行为克隆如果把“失败动作”当正确动作会污染标签；但失败轨迹可以用于 value/reward、failure detection、DAgger/纠错、对比学习。关键是明确 label semantics。

## 12. 真实机器人评测应该记录什么

只报 success rate 不够。至少记录任务数、每任务 episode 数、随机化范围、重试规则、平均耗时、P95 推理延迟、控制频率、人工接管次数、碰撞/急停次数、失败类型。

失败类型可分：语义选错目标、grounding 错、深度无效、外参漂移、抓取点错误、IK 失败、碰撞规划失败、action chunk 抖动、夹爪力不足、时延过大、模型幻觉。只有把失败分类，才能知道是该换模型还是修标定。

## 13. 工程部署：Jetson、桌面 GPU、DGX Spark 怎么分工

边缘设备适合传感器接入、图像预处理、轻量检测/分割、状态机、低延迟控制和安全；大模型训练更适合服务器。SmolVLA 这种轻量模型可以尝试边缘推理，但需要实测显存、TensorRT/torch.compile 可用性和延迟。4B/7B VLM/VLA 更适合工作站或服务器推理，然后通过 ROS2/网络下发高层动作，但网络断开必须有本地安全降级。

部署前做三套 profile：模型纯推理延迟、传感器到动作端到端延迟、长时间热稳定。GPU 峰值速度不等于 2 小时稳定控制速度。记录功耗模式、GPU/CPU 温度、频率、显存、P50/P95/P99。

## 14. ROS2 集成架构

推荐把系统拆成多个节点：camera driver、depth align、semantic grounding、3D localization、policy inference、safety gate、robot controller、logger。用 TF2 管理 frame tree，避免每个节点手写外参。QoS 按数据类型设计：图像可能 best effort，控制和状态要可靠且有 watchdog。

策略节点不要直接发布电机 PWM，而发布结构化动作目标，例如 PoseStamped、JointTrajectory 或自定义 action chunk。safety node 检查 workspace、速度、关节限位和心跳，再交给 controller。

## 15. 两个主项目如何在面试中讲

项目 A（SmolVLA+SO101）按六步讲：我先完成 leader/follower 舵机 ID、波特率和位置标定；然后做前视/腕部相机内参；如果需要三维抓取，再做 hand-eye；用 LeRobot 采集多位置、多背景 episode；fine-tune SmolVLA；推理输出 action chunk 后做反归一化、限幅、最大步长、急停，再发给 follower。最后用成功率和失败分类评估。

项目 B（Qwen3-VL+Grounded-SAM2+RGB-D+Spatial/StarVLA）按七步讲：语言指令由 VLM 解析；开放词汇 grounding 找目标；SAM2 得 mask 并追踪；mask+depth 得相机三维；T_base_camera 变换到机器人 base；生成 grasp candidate；VLA/MoveIt2 执行；任何 confidence/geometry/safety gate 不通过则重观测。

## 16. 原仓库 8 个项目与新增 2 个项目如何形成统一故事

01 四足 SLAM：体现 LiDAR/IMU/ICP/回环/定位和 C++/Python 基础。它回答“机器人在哪里”。

02 Ginger 服务机器人：体现 rosbridge、状态机、故障恢复和导航门控。它回答“机器人系统如何在通信异常时降级”。

03 GeoScan Pro：体现串口协议、CRC、传感器质量、相对/绝对约束融合。它回答“传感器数据如何可靠进入优化系统”。

04 工业视觉：体现检测指标、量化、异常评分和边缘推理。它回答“视觉模型如何从 accuracy 变成可部署系统”。

05 ROS2 + 3DGS：体现 3D 表示、ROS2 消息和可视化。它回答“地图/场景如何被系统消费和展示”。

06 BMS：体现状态估计、嵌入式实时任务和安全门控。它回答“为什么 AI 系统也必须有硬实时和安全边界”。

07 GaussPatrol：体现任务规划、动态重规划、定位/检测/地图指标。它回答“感知、规划、评测如何闭环”。

08 3DGS 扫描仪软硬件：体现硬件资料、PCB/BMS/SLAM 主控、测试矩阵。它回答“你不是只会训练模型，还考虑供电、接口、打板和工程验证”。

09 SmolVLA SO-101：补上具身动作学习和真实机器人数据闭环。

10 Spatial Semantic VLA：补上 VLM 语义、开放词汇分割、RGB-D 三维、手眼标定和动作桥接。

这样十个项目可以统一成一句话：我覆盖了机器人从传感器硬件、时空标定、定位建图、语义感知、任务规划到 VLA 动作和安全执行的完整链路。

## 17. 高频面试题与参考回答

### Q1：VLM 和 VLA 的根本区别？
VLM 的输出通常是语言、分类、grounding 或语义表示；VLA 在此基础上把机器人状态和动作建模纳入训练，最终输出机器人可执行动作或动作序列。VLA 不是简单在 VLM 后面接一个 MLP，关键还包括 action representation、跨 embodiment 数据、时序建模和控制闭环。

### Q2：为什么不能让 Qwen3-VL 直接输出抓取 XYZ？
因为语义模型的坐标输出不等价于经过相机内参、深度和外参校准后的 metric 坐标。工程上我让 VLM 选目标，分割模型给 mask，深度+K 做反投影，再通过 T_base_camera 变换，毫米级动作还要由几何/力控闭环保证。

### Q3：SmolVLA 为什么轻？
它采用紧凑 VLM 和 action expert，模型规模明显低于多 B 参数 VLA，并在 LeRobot 中面向高效 fine-tune/部署。回答时不要把“轻量”说成完全没有 GPU 需求；训练仍取决于 batch、图像和是否冻结 backbone。

### Q4：SpatialVLA 的 Ego3D Position Encoding 解决什么？
传统视觉 token 主要来自二维图像，三维空间关系需要模型隐式推理。Ego3D 将三维位置先验注入输入表示，使模型更直接学习相机自视角下的空间关系。

### Q5：Adaptive Action Grid 为什么有意义？
不同机器人动作范围和分布不同。固定离散 action bin 可能浪费分辨率。自适应网格根据动作空间重新离散化，有利于在不同 embodiment 上迁移动作知识，同时针对新机器人重新调整网格。

### Q6：SwiftVLA 的 4D 是什么？
不是简单 3D+时间标签，而是利用连续视频构建带时序记忆的几何特征，目标是理解物体/机器人随时间变化的空间结构。动态抓取时需要预测“未来相遇”而不是只看当前帧。

### Q7：为什么 StarVLA 对研发有价值？
它把 backbone、action head、训练 recipe、benchmark 和数据接口解耦，方便在同一训练/评测框架下比较不同 VLA 范式，降低每换模型就重写整套工程的成本。

### Q8：Eye-in-Hand 与 Eye-to-Hand 的区别？
Eye-in-Hand 相机跟随末端运动，常求 gripper-camera 固定变换；Eye-to-Hand 相机固定在环境中，常求 base-camera。两种标定方程中的变量方向不同，使用 OpenCV API 前必须把机器人 SDK 给的位姿方向统一。

### Q9：怎样验证手眼标定？
不能只看算法返回矩阵。准备 held-out 标定板姿态，把相机观测的目标点变换到 base frame，与机器人触碰/已知点比较，统计三维 RMSE/最大误差；同时检查多个工作空间位置，避免只在标定区域中心准确。

### Q10：动作归一化错了会怎样？
模型训练可能在 [-1,1] 或数据集统计空间中预测。如果部署时用错 mean/std、min/max、关节顺序或单位，0.1 可能代表 0.1m、0.1rad 或归一化尺度，后果非常严重，所以 action stats 必须随 checkpoint 版本化。

### Q11：VLA 的 action chunk 太长有什么问题？
闭环变弱，场景变化后仍执行旧计划；太短则推理频率和延迟压力大。可采用 receding horizon，只执行 chunk 前 N 步再重规划，或 real-time chunking/overlap 融合。

### Q12：动态物体为什么更难？
观测、推理、网络和执行都有延迟。若只基于当前位置规划，机械臂到达时物体已经移动。需要时序状态、速度估计、预测未来位置和低延迟闭环。

### Q13：为什么 VLA 需要多相机？
单视角存在遮挡和深度歧义。前视相机提供全局任务上下文，腕部相机提供接触前局部细节。多相机需要同步和外参管理，并注意训练/部署相机名称、顺序和分辨率一致。

### Q14：如何处理模型 hallucination？
高层 VLM 输出只能作为提议。通过 grounding score、分割一致性、depth validity、workspace、物体类别白名单/禁区、控制安全状态机验证。关键动作可要求二次观测或传统检测器交叉确认。

### Q15：什么时候不用 VLA？
任务高度结构化、物体固定、轨迹可解析、精度和节拍要求极高时，传统视觉+规则+MoveIt/PLC 可能更可靠、更易认证。VLA 适合任务多样、语义变化大、示教成本可接受的场景。

### Q16：怎样把 VLA 接 MES/工业系统？
VLA 不直接负责 MES。上层任务服务拿工单/SOP，转换成机器人 task goal；VLA 负责局部操作策略；每一步记录工单 ID、模型版本、输入帧哈希、动作、结果、异常码，再回写追溯系统。

### Q17：LoRA fine-tune 适合什么时候？
数据较少、显存有限、希望保留 backbone 能力时。真实机器人小数据适合先 LoRA；如果动作分布/视觉 domain 与预训练差异极大，再考虑更深层解冻。要通过 ablation 比较冻结范围和泛化，而不是默认 LoRA 一定最好。

### Q18：OpenVLA-OFT 与普通 OpenVLA 思路差异怎么讲？
面试可从高效 fine-tune 和连续动作解码改进角度讲，重点不是背 benchmark 数字，而是说明 OFT 类方法试图提升 action decoding/训练效率，使开源 VLA 更容易适配新机器人。

### Q19：π0 / flow matching 为什么火？
机器人连续动作天然适合连续生成建模。flow matching 可以用条件向量场从噪声生成动作轨迹，能表达多模态动作方案，并与强 VLM backbone 结合。

### Q20：GR00T 的工程启发是什么？
大型通用机器人模型需要把高层语义与低层快速动作分层，并依赖大规模跨 embodiment 数据、仿真/合成数据、Isaac 生态和部署工具。面试里更应讲系统分层而不是只背参数量。

## 18. Coding 面试准备

你需要能现场写出四类代码。第一类是几何：四元数/旋转矩阵、齐次变换、点云坐标变换、像素反投影。第二类是数据：读取 episode、按 timestamp 对齐、滑动窗口构造 action chunk。第三类是安全：clamp、rate limit、watchdog、异常值过滤。第四类是评测：success rate、precision/recall、ATE/RPE、延迟分位数。

典型 coding 题：给 K、像素 u,v 和 depth，写出 camera XYZ；给 T_base_camera，把点转到 base；给 50 步 action chunk，限制每步最大 delta；给 timestamp 序列检测掉帧；给一组 mask depth 过滤 0/NaN/离群值并取中位数。

## 19. Linux / VSCode / Git 工程能力

面试官可能问如何拉仓库、管理分支、固定 commit、建环境。建议回答：每个大模型上游独立 conda/venv，不把 LeRobot、SpatialVLA、StarVLA、Grounded-SAM2 全塞进一个环境；使用 `git rev-parse HEAD` 保存版本；requirements/lockfile 与 CUDA/Torch 版本一起记录；VSCode 使用 workspace 管理多个仓库。

克隆自己的仓库：`git clone https://github.com/lemonbaby2/-123.git`。进入以连字符开头目录可用 `cd -- -123`。为了可读性也可以 clone 时重命名：`git clone https://github.com/lemonbaby2/-123.git lizipeng-embodied-ai-portfolio`。

## 20. 你应该主动承认的真实性边界

不要说“我已经在真机上验证 SwiftVLA”如果你只是读论文。不要把合成 demo 的成功率说成真实机器人指标。不要把论文 benchmark 结果说成自己的。不要说“VLM 已经达到毫米级”而没有标定/测量证据。工程面试里，明确区分“仓库实测、历史项目报告、论文结果、设计目标”会显著提升可信度。

## 21. 推荐的 14 天学习/复现顺序

第 1-2 天：LeRobot 安装、SO-101 文档、理解 robot/teleop/dataset/policy 四个对象。第 3 天：相机内参标定和重投影误差。第 4 天：SE(3)、hand-eye、TF2。第 5-6 天：录制一个 pick-place 数据集，检查时间戳、关节范围和相机帧。第 7 天：SmolVLA fine-tune 和离线 replay。

第 8 天：Qwen3-VL 2B/4B 做图像 grounding/任务描述。第 9 天：Grounded-SAM2 做文本目标 mask。第 10 天：RGB-D mask 反投影到 3D。第 11 天：T_base_camera 外参验证。第 12 天：读 SpatialVLA Ego3D/Adaptive Action Grid。第 13 天：读 StarVLA 模块化框架和自定义机器人接入。第 14 天：把两条 pipeline 用 ROS2 topic/服务串起来并做一次故障注入演示。

## 22. 最终面试项目陈述模板

“我的具身智能项目不是单独跑一个 VLA checkpoint。我先把硬件、相机、机器人关节和坐标系标定好，保证数据是可解释的；语义侧用 VLM/开放词汇分割确定目标和任务约束；几何侧用深度、内参和外参得到机器人 base frame 的三维目标；动作侧根据算力和任务选择 SmolVLA、SpatialVLA 或 StarVLA 框架里的 action head；最后所有动作通过限位、速度、碰撞、watchdog 和急停状态机。我会对每一层记录版本和失败类型，这样模型升级时能知道收益来自哪里。”

这段话之后，面试官如果追模型，你可以讲 SmolVLA/SpatialVLA/SwiftVLA/StarVLA；如果追视觉，你讲 Qwen3-VL/Grounded-SAM2/RGB-D；如果追机器人学，你讲 SE(3)/hand-eye/IK/MoveIt2；如果追系统，你讲 ROS2/QoS/watchdog/日志；如果追工程真实性，你讲 dry-run、CI、版本锁定和真实数据边界。

## 23. 参考上游（建议固定 commit 后再复现）

- Hugging Face LeRobot / SmolVLA: https://github.com/huggingface/lerobot
- SpatialVLA: https://github.com/SpatialVLA/SpatialVLA
- SwiftVLA: https://github.com/GigaAI-research/SwiftVLA
- StarVLA: https://github.com/starVLA/starVLA
- Qwen3-VL: https://github.com/QwenLM/Qwen3-VL
- Grounded-SAM-2: https://github.com/IDEA-Research/Grounded-SAM-2
- SAM2: https://github.com/facebookresearch/sam2
- StreamVGGT: https://github.com/wzzheng/StreamVGGT
- OpenVLA: https://github.com/openvla/openvla
- OpenVLA-OFT: https://github.com/moojink/openvla-oft
- openpi: https://github.com/Physical-Intelligence/openpi
- NVIDIA Isaac GR00T: https://github.com/NVIDIA/Isaac-GR00T
- SpatialVLA paper: https://arxiv.org/abs/2501.15830
- SmolVLA paper: https://arxiv.org/abs/2506.01844
- SwiftVLA paper: https://arxiv.org/abs/2512.00903
- StarVLA technical report: https://arxiv.org/abs/2604.05014
- Qwen3-VL report: https://arxiv.org/abs/2511.21631

## 24. 最后记忆的十条红线

1. VLM 语义坐标不等于标定后的机器人 metric 坐标。
2. VLA action 必须知道单位、frame、joint order、normalization。
3. Hand-eye 先画坐标系，再套公式。
4. 多相机必须做时间同步和外参管理。
5. action chunk 不能无条件整段执行，要 receding horizon / safety gate。
6. 大模型不能绕过碰撞检测、急停和 watchdog。
7. 真实机器人小数据先看数据质量，不要只加训练步数。
8. 论文结果、仓库 demo、真机实测必须分开表述。
9. 上游仓库要固定 branch/commit，尤其 StarVLA stable/dev 要区分。
10. SwiftVLA 当前可作为前沿储备，工程主线优先使用源码/文档完整的 LeRobot、SpatialVLA、StarVLA。


## 25. 针对十个作品集项目的逐项目追问

### 25.1 四足 SLAM
面试官会从体素滤波追到为什么 downsample 会影响 ICP；从 ICP 追到 point-to-point 与 point-to-plane；从 IMU 积分追到 bias 和预积分；从回环门控追到 false positive；再追到为什么只靠 scan matching 会漂移。回答时把前端里程计、后端图优化、回环和地图管理分开。若对方问如何与 VLA 结合，可以说 SLAM/定位提供世界坐标和机器人自身状态，VLA 负责操作/语义决策，两者可以通过统一 scene graph 或 TF frame 连接，但不要让 VLA 替代安全定位。

### 25.2 Ginger 服务机器人
重点是状态机、链路故障、导航门控。面试官可能问为什么不用一个大模型决定所有恢复动作。正确方向是：大模型可以提出恢复策略，但低层恢复必须是确定性状态机，例如连接断开、定位失效、电量低、急停都必须进入明确状态。LLM/VLM 不能覆盖硬故障逻辑。

### 25.3 GeoScan Pro
重点是串口协议、CRC、传感器质量和小型因子图。可能追问 CRC 能检测什么、不能检测什么；协方差如何影响因子权重；RTK absolute factor 与 odometry relative factor 如何共同约束漂移。与 VLA 的联系是：动作策略同样需要可靠 telemetry，数据链路质量差时应拒绝动作而不是继续推理。

### 25.4 工业视觉
重点是 precision/recall、阈值、INT8、时序异常。可能追问量化为什么会影响小目标、calibration dataset 如何选、TensorRT engine 和 PyTorch 结果怎样对齐。这个项目能支撑你回答“如何把 Qwen/Grounded-SAM/VLA 从研究代码变成边缘部署”。

### 25.5 ROS2 + 3DGS
重点是 frame_id、timestamp、MarkerArray、点云/高斯可视化和 ROS2 package。与 VLM/VLA 的结合点是：3DGS/场景表示可作为高层语义地图，VLM 可以查询对象关系，VLA 可以使用局部视觉控制；但实时控制不应依赖高延迟离线渲染链。

### 25.6 BMS
重点是 EKF、Thevenin 模型、均衡、实时调度和安全门控。它能证明你理解“AI 之外还有安全系统”。机器人里电池 brown-out、温度过高、SOC 低都会影响 GPU 频率和机械臂动作，策略层必须读系统健康状态。

### 25.7 GaussPatrol
重点是任务规划、动态重规划、ATE/RPE、AP、地图完整度。面试官可能要求解释为什么指标要分层：定位误差、感知 AP 和任务成功率不能混成一个数。VLA 评测也一样，先看 perception/geometry，再看 action success。

### 25.8 3DGS 扫描仪软硬件
重点是电源预算、接口、PCB、主控和资料边界。具身项目非常吃硬件：USB 带宽、电源、相机触发、散热、GPU 功耗都可能让“算法正常”但系统失败。你可以主动讲 Jetson 上 TensorRT 构建和内存问题，说明部署能力。

### 25.9 SmolVLA SO-101
面试官会追：为什么要 leader/follower；示教怎么录；多少 episode；动作是什么；模型输出是否闭环；为什么 action chunk；失败如何重采。你需要明确：示教质量优先于盲目增加数据，任务变体要分层覆盖；部署时只执行 chunk 的一部分并重新观测更安全。

### 25.10 Spatial Semantic VLA
面试官会追：VLM 与 GroundingDINO 重复吗；为什么还要 SAM；depth 如何处理；如何从 camera 到 base；抓取姿态怎么来。回答：VLM负责语义关系，Grounding负责文本到 bbox，SAM负责精确 mask/跟踪，depth+K负责 metric 3D，hand-eye 负责 frame transform，抓取姿态来自几何/抓取网络/VLA，最后 safety gate。

## 26. 再补 30 个短问短答

1. **为什么用中位深度而不是平均？** 中位数对 mask 内少量飞点和背景污染更鲁棒。
2. **深度相机遇到反光物体怎么办？** 多视角、结构光/双目备选、点云邻域、时序滤波，必要时回退到视觉伺服或力控。
3. **如何检测 calibration 漂移？** 定期观察固定 AprilTag/Charuco，统计重投影和 base-frame 点误差，超过阈值重新标定。
4. **四元数为什么要归一化？** 数值误差会破坏单位旋转约束，插值/变换前需规范化。
5. **欧拉角有什么问题？** 奇异性和角度不连续；优化和插值更常用四元数/李代数。
6. **视觉伺服与 VLA 怎么结合？** VLA 给目标/粗轨迹，最后阶段用 IBVS/PBVS 或力控闭环修正。
7. **为什么需要 wrist camera？** 近距离遮挡、末端误差、抓取接触前视觉更可靠。
8. **数据中语言指令要统一吗？** 既要模板一致避免标签噪声，也要适量 paraphrase 提升语言泛化。
9. **如何防止模型只记背景？** domain randomization、多背景、多光照、物体位置分层和 held-out 场景测试。
10. **为什么 episode success label 重要？** 方便离线评测、失败挖掘、RL/偏好训练和数据清洗。
11. **VLA 输出频率低怎么办？** action chunk、异步推理、策略服务器、局部控制器插值、实时 chunking。
12. **网络推理放服务器安全吗？** 可以，但控制安全必须本地；网络 timeout 立刻停止或进入安全姿态。
13. **如何评估端到端延迟？** 在采集帧、模型入队、模型出队、控制发送、执行反馈各打 monotonic timestamp。
14. **为什么要 P95/P99？** 控制系统怕尾延迟，平均值掩盖偶发 500ms 卡顿。
15. **训练数据 FPS 越高越好吗？** 不是，过高产生强冗余；关键是覆盖动作动态和与控制频率匹配。
16. **动作是 joint space 还是 Cartesian space？** 取决于数据和机器人。Cartesian 跨机器人更直观，但最终仍需 IK；joint space 控制直接但跨 embodiment 更难。
17. **gripper 开合如何编码？** 连续宽度、二值开关或归一化标量；训练和部署必须一致。
18. **为什么机器人动作常加 state 输入？** 纯图像难准确知道关节/末端当前状态，proprioception 提升可控性。
19. **如何避免关节顺序错？** schema 明确 joint_names，运行时按名字映射，不依赖数组默认顺序。
20. **ROS2 TF 为什么重要？** 集中维护时变/静态坐标关系，降低 frame 方向错误。
21. **VLA 与行为树冲突吗？** 不冲突。行为树可管理高层任务和异常，VLA 作为某个 manipulation skill。
22. **VLA 与 MoveIt2 谁负责什么？** VLA可给目标/局部动作，MoveIt2负责几何规划和碰撞约束；也可按任务选择端到端策略。
23. **为什么精密插入需要力传感器？** 最后接触阶段视觉被遮挡且毫米误差敏感，力/阻抗能提供接触反馈。
24. **如何处理遮挡？** 多视角、主动视角调整、SAM2时序记忆、重观测策略。
25. **如何做 active perception？** 当目标置信度低或几何不确定性高时，策略先移动相机/机械臂获取更好视角，而不是强行抓取。
26. **什么是 cross-embodiment？** 在不同机器人形态/动作空间之间学习可迁移的表示和策略。
27. **为什么 action tokenizer 有风险？** 离散化会产生量化误差，且不同机器人范围差异导致 token 语义不一致。
28. **什么叫 world model for action？** 学习环境状态转移/未来视觉或 latent，再用预测辅助动作决策。
29. **Real2Sim 的价值？** 用真实观测重建仿真环境，扩充训练和安全测试，但存在材质、动力学和接触 gap。
30. **你最先优化什么？** 先做失败归因；如果 40% 失败来自外参漂移，换更大的 VLA 没意义。

## 27. 现场白板题：手眼标定如何解释

先定义四个 frame：B=base，G=gripper，C=camera，T=target。Eye-in-Hand 中 C 固连 G，标定板 T 固定在环境。机器人移动到 i,j 两姿态时，可从 FK 得 T_B_Gi、T_B_Gj，从 PnP 得 T_Ci_T、T_Cj_T。构造相对运动 A = inv(T_B_Gj) T_B_Gi，B = T_Cj_T inv(T_Ci_T)，求 AX=XB，X 对应固定的 gripper-camera 变换（具体方向取决于定义）。

工程里最重要不是背 AX=XB，而是检查：所有 pose 是否同单位；rotation 是否正交；translation 是否 m/mm 混用；机器人和相机 timestamp 是否同步；采样姿态是否有足够旋转激励。只平移、不旋转的姿态集会让某些参数不可观。

## 28. 现场白板题：从 mask 得 3D 抓取点

步骤一：用 mask 过滤 depth。步骤二：去除 0、NaN、超量程。步骤三：可以在 mask 中心区域或距离变换最大点附近取深度，减少边缘混合像素。步骤四：K^-1 [u,v,1]^T * Z 反投影。步骤五：用 T_base_camera 转换。步骤六：邻域点云 PCA 求表面法向或主轴。步骤七：构造 pre-grasp，在法向反方向留安全距离。步骤八：检查工作空间和碰撞。最后才调用控制器。

## 29. 现场系统设计题：传送带动态抓取

相机固定观察传送带，先标定 conveyor frame。检测器/分割器持续跟踪物体，基于 timestamp 估计二维/三维速度；StreamVGGT/SwiftVLA 类时序几何可作为高级方案，但传统 Kalman filter 仍是可靠 baseline。预测机械臂可达时间 t_arrival 时物体位置 p(t_arrival)。VLA 可以决定 grasp strategy，但控制层需要轨迹时间参数化和速度同步。若预测不确定度超过阈值，直接放弃该目标抓下一个，而不是追到机械限位。

## 30. 现场系统设计题：工业螺钉 SOP + VLM/VLA

VLM 可用于识别工位语义、理解自然语言 SOP 或异常说明；传统视觉/检测器负责螺钉、工具、工件的高精度检测；状态机负责步骤顺序；电批提供扭矩/角度闭环；VLA 只在需要灵活抓取/搬运/工具操作时介入。这样比“所有步骤都交给一个 VLA”更符合工业可靠性。

如果需要跨产线迁移，先迁移相机/机械臂标定模板、ROI/工位 frame、设备接口，再收集少量新 domain 数据做 VLM/VLA adapter。MES 追溯记录模型版本、任务 ID、图像证据、扭矩结果和异常路径。
