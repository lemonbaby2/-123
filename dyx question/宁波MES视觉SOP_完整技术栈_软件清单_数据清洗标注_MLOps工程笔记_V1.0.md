# 宁波 MES + 视觉 SOP + DGX Spark 工业视觉项目技术栈与软件总笔记
## —— 从设备接入、数据采集/清洗/标注、模型训练、推理部署到 MES 追溯的完整工程技术栈

> 项目定位：厂内本地部署的 MES + 视觉 SOP 工位智能执行/监督系统  
> AI 平台：DGX Spark 128GB + 4TB  
> 工位侧：工业工控机 IPC / Station Agent  
> 视觉侧：USB UVC / GigE 工业相机 + 工业光源  
> 业务侧：MES / MEMS、扫码枪、打印机、USB485、烧录工具、PLC、电批、HMI  
> 核心原则：**AI 负责难视觉问题，确定性规则负责生产放行；DGX 管 AI，IPC 管现场设备，MES 管业务与追溯。**

---

# 目录

1. 项目总体技术架构  
2. 技术栈总览  
3. 操作系统与基础开发环境  
4. 编程语言与工程框架  
5. 工控机 IPC 技术栈  
6. DGX Spark AI 平台技术栈  
7. 相机与图像采集技术栈  
8. 工业视觉算法技术栈  
9. 传统机器视觉技术栈  
10. OCR / 二维码 / 条码技术栈  
11. Tracking / Pose / Action 技术栈  
12. 工业异常检测技术栈  
13. 数据采集体系  
14. 数据清洗体系【重点】  
15. 数据标注体系【重点】  
16. 标注类别与任务设计【重点】  
17. 数据集目录与命名规范【重点】  
18. Train / Val / Frozen Test 划分【重点】  
19. 预标注与主动学习【重点】  
20. 数据质量 QA【重点】  
21. 数据集版本管理  
22. 模型训练技术栈  
23. 模型评估体系  
24. TensorRT / ONNX / 推理部署  
25. Triton / AI 服务化  
26. Model Registry / MLOps  
27. MES 技术栈  
28. 工业设备 Adapter 技术栈  
29. PLC / 电批 / 串口协议  
30. HMI / Web 前端技术栈  
31. 数据库与对象存储  
32. 网络与 IP 技术栈  
33. 日志、监控、审计与告警  
34. Docker 与服务部署  
35. 测试与 FAT / SAT  
36. 跨产线迁移技术栈  
37. 推荐 GitHub / 开源项目  
38. 推荐代码目录结构  
39. 项目开发阶段路线  
40. 最终推荐软件安装清单  
41. 一句话总结

---

# 1. 项目总体技术架构

```text
                        ┌─────────────────────┐
                        │      MES / MEMS     │
                        │ 工单 / SN / 报工 / 追溯 │
                        └──────────┬──────────┘
                                   │
                           REST / HTTPS / MQ
                                   │
                        ┌──────────▼──────────┐
                        │   IPC Station Agent │
                        │ SOP FSM / Device IO │
                        └──────────┬──────────┘
                                   │
        ┌─────────────┬────────────┼────────────┬─────────────┐
        ▼             ▼            ▼            ▼             ▼
      Camera        Scanner      Printer      USB485        PLC/Tool
        │
        │ Frame / ROI
        ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                    DGX Spark AI Platform                     │
 │                                                              │
 │ Detection / Anomaly / Segmentation / Tracking / Pose / OCR  │
 │ Training / Validation / Annotation / Model Registry          │
 └─────────────────────────┬────────────────────────────────────┘
                           │
                    Detection / State
                           │
                     ┌─────▼─────┐
                     │  SOP FSM  │
                     └─────┬─────┘
                           │
                 PASS / NOK / REWORK
                           │
                     ┌─────▼─────┐
                     │    HMI    │
                     │ 工人提示/纠正 │
                     └─────┬─────┘
                           │
                         MES
```

---

# 2. 技术栈总览

| 层级 | 技术栈 | 推荐软件/框架 |
|---|---|---|
| 操作系统 | Linux / Windows | DGX OS / Ubuntu；IPC 可 Windows 11 IoT 或 Ubuntu |
| 编程语言 | Python / C++ / JS / SQL | Python 3.10+、C++17、TypeScript/JavaScript、SQL |
| AI训练 | PyTorch | PyTorch、TorchVision |
| 实时检测 | YOLO / RT-DETR / D-FINE | Ultralytics、RT-DETR、D-FINE |
| 异常检测 | PatchCore / EfficientAD | Anomalib |
| 分割 | SegFormer / Mask2Former | MMSegmentation |
| OCR | OCR / QR | PaddleOCR、OpenCV QR、ZXing |
| 跟踪 | OC-SORT | OC-SORT |
| 姿态 | RTMPose / FoundationPose | MMPose、FoundationPose |
| 视频动作 | VideoMAE / SlowFast | MMAction2 |
| 自动标注 | Grounding DINO + SAM2 | GroundingDINO、SAM2、Grounded-SAM-2 |
| 图像处理 | OpenCV | OpenCV |
| 视频流 | GStreamer / FFmpeg | GStreamer、FFmpeg |
| 推理优化 | ONNX / TensorRT | ONNX、TensorRT、ONNX Runtime |
| AI服务 | Triton / FastAPI | NVIDIA Triton、FastAPI |
| 标注 | CVAT / Label Studio | CVAT、Label Studio |
| 数据浏览 | FiftyOne | FiftyOne |
| 数据转换 | Datumaro | Datumaro |
| 数据版本 | DVC | DVC + Git |
| 模型版本 | MLflow | MLflow / 自研 Registry |
| 数据库 | PostgreSQL / SQLite | PostgreSQL、SQLite |
| 对象存储 | MinIO / NAS | MinIO、NAS |
| 消息队列 | NATS / RabbitMQ | NATS / RabbitMQ |
| 前端 | Web / HMI | Vue / React / Qt / Chromium Kiosk |
| MES接口 | REST / OPC UA / MQTT | FastAPI、open62541、paho-mqtt |
| PLC | Modbus / OPC UA / S7 | pymodbus、asyncua、snap7 |
| 串口 | RS232 / RS485 | pyserial |
| 监控 | Prometheus / Grafana | Prometheus、Grafana |
| 容器 | Docker | Docker、Docker Compose |
| 反向代理 | HTTPS | Nginx / Caddy |
| 测试 | pytest | pytest、Postman、Locust |
| CI/CD | Git | GitHub / GitLab CI |

---

# 3. 操作系统与基础开发环境

## 3.1 DGX Spark

建议：

```text
DGX OS / Ubuntu
```

主要运行：

```text
Docker
CUDA
TensorRT
PyTorch
Triton
CVAT
PostgreSQL
MinIO
FastAPI
MLflow
Prometheus
Grafana
```

DGX 不建议直接承担：

```text
USB打印机驱动
Windows烧录工具
COM口测试软件
现场PLC直接控制
```

这些留在 IPC。

---

# 4. 编程语言与工程框架

## Python

项目主语言。

负责：

```text
AI训练
推理
OpenCV
串口
MES API
FSM
Device Adapter
数据处理
数据清洗
标注辅助
自动化脚本
```

推荐库：

```text
numpy
pandas
opencv-python
torch
torchvision
onnx
onnxruntime
tensorrt
ultralytics
fastapi
uvicorn
pydantic
sqlalchemy
psycopg
pyserial
pymodbus
asyncua
requests
httpx
loguru
pytest
```

---

## C++

在以下场景使用：

```text
极低延迟
厂商SDK
GigE Camera SDK
PLC SDK
TensorRT Runtime
高性能Video Pipeline
```

推荐：

```text
C++17
OpenCV C++
TensorRT C++
GStreamer C++
Boost
CMake
```

---

## JavaScript / TypeScript

负责：

```text
HMI
MES Web
管理后台
模型管理界面
标注任务管理
设备状态
```

推荐：

```text
Vue 3
React
TypeScript
Vite
Axios
ECharts
WebSocket
```

---

# 5. 工控机 IPC 技术栈

IPC 是：

> 现场设备控制中心。

推荐运行模块：

```text
Station Agent
├── Device Registry
├── Camera Service
├── Scanner Adapter
├── Printer Adapter
├── USB485 Adapter
├── Burner Adapter
├── PLC Adapter
├── Tool Adapter
├── SOP FSM
├── AI Client
├── HMI
├── Local Queue
├── Logger
└── Watchdog
```

---

# 6. DGX Spark AI 平台技术栈

DGX Spark：

```text
AI Center
```

推荐容器：

```text
Nginx
FastAPI
Triton
Training Worker
Validation Worker
CVAT
MLflow
PostgreSQL
MinIO
Prometheus
Grafana
```

---

# 7. 相机与图像采集技术栈

## PoC

亚博 USB UVC 工业摄像头。

软件：

```text
OpenCV VideoCapture
V4L2
DirectShow
GStreamer
```

Linux：

```bash
v4l2-ctl --list-devices
v4l2-ctl --list-formats-ext -d /dev/video0
```

---

## 正式量产

推荐：

```text
GigE Vision
USB3 Vision
Global Shutter
```

常见厂商：

```text
海康机器人
大恒
Basler
Teledyne FLIR
IDS
```

软件：

```text
厂商SDK
GenICam
GigE Vision
Aravis
Harvesters
```

---

# 8. 工业视觉算法技术栈

检测：

```text
YOLO
RT-DETR
D-FINE
```

异常：

```text
PatchCore
EfficientAD
SuperADD
AnomalyVFM
```

分割：

```text
SegFormer
Mask2Former
```

跟踪：

```text
OC-SORT
SAM2 Tracking
TAPTR
```

Pose：

```text
RTMPose
FoundationPose
```

自动标注：

```text
Grounding DINO
SAM2
Grounded-SAM-2
```

---

# 9. 传统机器视觉技术栈

工业项目中非常重要。

软件：

```text
OpenCV
Halcon（商业）
VisionPro（商业）
```

算法：

```text
HSV
Lab
Threshold
Morphology
Connected Components
Contour
Template Matching
ORB
SIFT
Homography
PnP
AprilTag
ArUco
```

---

# 10. OCR / 二维码 / 条码

优先级：

```text
扫码枪
>
二维码解码
>
OCR
```

软件：

```text
ZXing
ZBar
OpenCV QRCodeDetector
PaddleOCR
```

---

# 11. Tracking / Pose / Action

Tracking：

```text
OC-SORT
ByteTrack
BoT-SORT
```

Pose：

```text
RTMPose
MMPose
FoundationPose
```

Action：

```text
MMAction2
VideoMAE
TSM
SlowFast
VideoSwin
```

---

# 12. 工业异常检测

推荐平台：

```text
Anomalib
```

模型：

```text
PatchCore
EfficientAD
Dinomaly
WinCLIP
SuperADD
AnomalyVFM
```

---

# 13. 数据采集体系【重点】

工业AI真正最重要的不是模型，而是：

> 数据体系。

---

## 13.1 数据来源

数据应该来自：

```text
真实生产相机
PoC相机
正常样件
NG样件
不同班次
不同工人
不同环境
不同光照
不同批次
不同产品
不同工位
```

---

## 13.2 必须覆盖的数据场景

正常：

```text
标准产品
标准位置
标准光照
标准工具
```

困难：

```text
手遮挡
工具遮挡
强反光
暗光
轻微模糊
运动模糊
产品偏移
标签倾斜
线缆遮挡
```

NG：

```text
漏装
错装
错序
LED异常
MAC不一致
端子未插
线缆未接
工具错误
```

---

# 14. 数据清洗体系【重点】

这是整个项目中最容易被忽略，但最影响模型质量的一部分。

推荐建立：

```text
Raw Data
 ↓
Integrity Check
 ↓
Blur Check
 ↓
Exposure Check
 ↓
Duplicate Removal
 ↓
Near Duplicate Removal
 ↓
Data Leakage Check
 ↓
Label Audit
 ↓
Balanced Dataset
```

---

## 14.1 图片完整性检查

检测：

```text
图片损坏
0字节
解码失败
尺寸异常
通道异常
```

软件：

```text
Python PIL
OpenCV
ImageMagick
```

---

## 14.2 模糊图片清洗

常用：

```text
Variance of Laplacian
```

示例思想：

```python
score = cv2.Laplacian(gray, cv2.CV_64F).var()
```

不要简单删除全部模糊图。

建议分：

```text
严重模糊 → 删除
中度运动模糊 → Hard Case
轻度模糊 → 保留
```

---

## 14.3 曝光质量

检查：

```text
过曝
欠曝
对比度过低
```

统计：

```text
Mean Brightness
Histogram
Clipped Pixel Ratio
```

---

## 14.4 重复图片去除

视频抽帧非常容易产生：

```text
Frame001
Frame002
Frame003
```

几乎一样。

这会造成：

```text
数据冗余
Train/Val泄漏
模型虚高
```

工具：

```text
imagehash
imagededup
FiftyOne
OpenCV perceptual hash
```

方法：

```text
pHash
dHash
SSIM
CLIP/DINO Feature Similarity
```

---

# 15. 数据标注体系【重点】

推荐主平台：

```text
CVAT
```

辅助：

```text
Label Studio
FiftyOne
Datumaro
```

---

## 15.1 为什么推荐 CVAT

支持：

```text
Detection
Segmentation
Polygon
Keypoint
Tracking
Video Annotation
Auto Annotation
Review
Consensus
```

非常适合：

```text
工业视频
Tool tracking
螺钉
线缆
手
PCB
产品
```

---

# 16. 标注任务设计【重点】

不要把：

```text
S01
S02
S03
```

训练成 YOLO class。

正确：

```yaml
0: product
1: screw
2: nut
3: screwdriver
4: tool_tip
5: hand
6: cable
7: connector
8: pcb
9: module
```

---

## 16.1 S01/S02在哪里保存

保存到：

```text
Recipe
```

例如：

```yaml
steps:
  S01:
    roi: [...]
    target: screw

  S02:
    roi: [...]
    target: connector
```

模型：

```text
识别“是什么”
```

Recipe：

```text
定义“在哪里”
```

FSM：

```text
定义“现在应该做什么”
```

---

# 17. 标注类型设计【重点】

## Detection

适合：

```text
screw
tool
hand
module
connector
```

格式：

```text
YOLO bbox
COCO bbox
```

---

## Segmentation

适合：

```text
喷涂
划痕
胶
线缆区域
缺陷区域
```

---

## Keypoint

适合：

```text
ToolTip
端子中心
开关点
手指点
```

---

## Tracking

视频中：

```text
tool_id=1
hand_id=2
```

---

## Temporal Annotation

SOP动作：

```text
start_time
end_time
action
step
result
```

例如：

```json
{
  "step": "S03",
  "action": "connect_usb485",
  "start": 32.5,
  "end": 38.2
}
```

---

# 18. 数据目录规范【重点】

推荐：

```text
datasets/
├── raw/
│   ├── line_01/
│   ├── line_02/
│   └── poc/
│
├── cleaned/
│
├── annotations/
│   ├── cvat/
│   ├── yolo/
│   └── coco/
│
├── splits/
│   ├── train.txt
│   ├── val.txt
│   └── frozen_test.txt
│
├── hard_cases/
│   ├── reflection/
│   ├── blur/
│   ├── occlusion/
│   ├── wrong_order/
│   └── unknown/
│
└── versions/
    ├── v1.0
    ├── v1.1
    └── v2.0
```

---

# 19. 文件命名规范【重点】

不要：

```text
1.jpg
2.jpg
3.jpg
```

推荐：

```text
ST01_PRODUCT313_SN000123_20260818_142312_S03_CAM_TOP_000123.jpg
```

包含：

```text
Station
Product
SN
Timestamp
Step
Camera
Frame
```

---

# 20. Metadata【重点】

每张图片建议有：

```json
{
  "station": "ST01",
  "product": "82300000313",
  "sn": "SN000123",
  "camera": "CAM_TOP",
  "timestamp": "2026-08-18T14:23:12.221",
  "step": "S03",
  "operator": "OP009",
  "recipe": "recipe_313_v4",
  "model": "parts_v3",
  "result": "NOK"
}
```

---

# 21. Train / Val / Frozen Test【重点】

绝对不要随机逐帧切分视频。

错误：

```text
同一段视频Frame001进Train
Frame002进Val
```

模型会虚高。

正确：

```text
按工单
按SN
按时间
按视频
按批次
按产线
```

隔离。

---

## 推荐比例

```text
Train 70%
Val 15%
Frozen Test 15%
```

具体按项目调整。

Frozen Test：

> 模型开发人员训练过程中不能反复用来调参数。

---

# 22. 数据泄漏检查【重点】

检查：

```text
同一个SN是否跨Train/Test
同一视频是否跨Train/Test
近重复图片是否跨Train/Test
同一产品序列是否跨Test
```

工具：

```text
FiftyOne
Python Hash
DINO Feature Similarity
```

---

# 23. 类别平衡【重点】

统计：

```text
class_count
bbox_count
image_count
small_object_count
NG_count
```

避免：

```text
hand 10000
screw 500
connector 80
```

---

# 24. Hard Negative【重点】

非常重要。

例如：

```text
螺丝附近金属反光
类似螺丝的圆孔
工具上的反光点
PCB焊点
标签字符
```

如果模型总误报：

> 不一定改模型，先增加 Hard Negative。

---

# 25. 预标注【重点】

推荐：

```text
旧模型
+
Grounding DINO
+
SAM2
```

流程：

```text
新视频
 ↓
抽帧
 ↓
旧模型预标注
 ↓
Grounding DINO补开放类别
 ↓
SAM2传播Mask
 ↓
CVAT人工修正
```

---

# 26. Active Learning【重点】

不是所有帧都人工标。

自动选择：

```text
低置信度
高Entropy
模型分歧
NOK
人工纠正
新产品
新光照
```

进入：

```text
Label Queue
```

---

# 27. FiftyOne【重点】

推荐作为：

> 数据集浏览和质量分析工具。

功能：

```text
搜索标签
查看误检
找重复
过滤低置信度
比较模型
Embedding Similarity
Hard Case Mining
```

---

# 28. Datumaro【重点】

负责：

```text
CVAT
YOLO
COCO
VOC
```

格式转换和数据校验。

推荐：

```text
CVAT → Datumaro → YOLO/COCO
```

---

# 29. DVC【重点】

负责：

```text
Dataset Version Control
```

不要把10GB数据直接Git。

推荐：

```text
Git
+
DVC
+
MinIO/NAS
```

Git管理：

```text
配置
代码
DVC pointer
```

MinIO保存：

```text
图片
视频
Dataset
Model
```

---

# 30. 数据版本命名

例如：

```text
dataset_fastener_v1.0
dataset_313_v1.0
dataset_313_v1.1_hardcase
dataset_multi_line_v2.0
```

---

# 31. 数据QA流程【重点】

建议：

```text
Annotator
 ↓
Reviewer
 ↓
QA Sampling
 ↓
Dataset Release
```

---

## QA检查

```text
漏框
错框
框太大
框太小
类别错
遮挡标错
重复框
跨边界
空Label
```

---

# 32. 自动标注质量检查

预标注：

```text
confidence > 0.8
```

也不能直接进入训练。

必须：

```text
人工确认
```

尤其：

```text
生产安全/质量相关类别
```

---

# 33. 标注规范文档

建议维护：

```text
annotation_guideline.md
```

必须定义：

```text
遮挡多少标？
只有一半目标标不标？
反光螺丝算screw吗？
ToolTip被挡住标不标？
手套算hand吗？
线缆接头标connector还是cable？
```

---

# 34. 模型训练技术栈

基础：

```text
PyTorch
TorchVision
CUDA
cuDNN
```

Detector：

```text
Ultralytics
RT-DETR
D-FINE
MMDetection
```

Anomaly：

```text
Anomalib
```

Segmentation：

```text
MMSegmentation
```

Pose：

```text
MMPose
```

Video：

```text
MMAction2
```

---

# 35. 数据增强

推荐：

```text
Brightness
Contrast
Gamma
Noise
Blur
Motion Blur
Perspective
Rotate
Crop
Occlusion
CopyPaste
Mosaic
MixUp
```

工业场景避免：

> 太激进的数据增强。

---

# 36. Albumentations

推荐：

```text
Albumentations
```

用于：

```text
Blur
Noise
Brightness
Contrast
Perspective
```

---

# 37. 模型评估

不要只看：

```text
mAP50
```

必须看：

```text
Precision
Recall
F1
mAP50
mAP50-95
Per-class Recall
False Positive / Hour
False Negative / 1000 pcs
Small Object Recall
Latency
FPS
GPU Memory
```

---

# 38. 工业真正重要的指标

例如：

```text
漏检率
误报率
每1000件误拦截
每小时报警次数
工位节拍
连续运行时间
```

---

# 39. Frozen Test

模型只有：

```text
Frozen Test通过
```

才能进入：

```text
Model Registry Approved
```

---

# 40. ONNX

训练：

```text
PyTorch
```

中间：

```text
ONNX
```

部署：

```text
TensorRT
```

工具：

```text
onnx
onnxruntime
onnxsim
onnxslim
Netron
```

Netron用于：

```text
查看模型结构
输入输出
节点
```

---

# 41. TensorRT

DGX / Jetson：

```text
TensorRT FP16
TensorRT INT8
```

优先：

```text
FP16
```

INT8：

> 有足够Calibration Dataset再做。

---

# 42. Triton Inference Server

推荐 DGX：

```text
NVIDIA Triton
```

支持：

```text
TensorRT
ONNX
PyTorch
Python Backend
```

---

# 43. AI API

推荐：

```text
FastAPI
+
gRPC
```

IPC发送：

```json
{
  "station": "ST01",
  "step": "S03",
  "image": "...",
  "model": "parts_v3"
}
```

返回：

```json
{
  "detections": [],
  "latency_ms": 23.4,
  "model_hash": "..."
}
```

---

# 44. Model Registry

推荐：

```text
MLflow
```

或者自研。

记录：

```text
model_name
model_version
dataset_version
git_commit
metrics
engine_hash
TensorRT
station_scope
product_scope
approved_by
```

---

# 45. MES 技术栈

MES / MEMS通过：

```text
REST API
HTTPS
WebSocket
MQ
OPC UA
```

常用：

```text
FastAPI
requests
httpx
pydantic
```

---

# 46. MES事件

```text
task_start
scan
step_start
vision_result
serial_result
tightening
step_complete
final_result
rework
complete
```

---

# 47. 工业设备 Adapter

统一接口：

```python
class DeviceAdapter:
    connect()
    health()
    read()
    write()
    reset()
```

---

# 48. 打印机

协议可能：

```text
ZPL
TSPL
ESC/POS
Windows Spooler
厂商SDK
```

---

# 49. 扫码枪

接口：

```text
USB HID
USB COM
TCP
RS232
```

---

# 50. USB485 / 串口

Python：

```text
pyserial
```

不要绑定：

```text
COM3
```

要绑定：

```text
VID
PID
USB Serial
Alias
```

---

# 51. PLC

协议：

```text
Modbus TCP
OPC UA
S7
EtherNet/IP
```

Python：

```text
pymodbus
asyncua
python-snap7
```

---

# 52. 智能电批

数据：

```text
PSet
Torque
Angle
OK/NOK
Tool ID
Tightening ID
```

常见：

```text
Open Protocol
OPC UA
TCP
厂商SDK
```

---

# 53. HMI

推荐：

```text
Web HMI
```

技术：

```text
Vue3
TypeScript
WebSocket
ECharts
```

---

# 54. 工人页面

显示：

```text
当前任务
SN
产品
SOP步骤
实时相机
当前ROI
PASS/NOK
错误原因
纠正方法
设备状态
```

---

# 55. PostgreSQL

存：

```text
Station
Product
Recipe
SN
WorkOrder
Event
User
Model
Deployment
Trace
```

---

# 56. MinIO / NAS

存：

```text
图片
视频
数据集
模型
TensorRT engine
日志归档
固件包
```

---

# 57. SQLite

IPC本地：

```text
Local Queue
```

当：

```text
MES断线
DGX断线
```

先缓存。

---

# 58. 网络

推荐：

```text
Device LAN
Factory LAN
AI LAN
MES LAN
```

IPC：

```text
双网卡
```

---

# 59. IP管理

能固定IP的：

```text
Camera
Printer
PLC
Tool Controller
DGX
Server
```

固定IP。

USB设备：

```text
VID/PID/SN
```

---

# 60. NTP

所有：

```text
IPC
DGX
MES
PLC
```

统一时间。

否则：

```text
Trace ID
视频
Torque
MES Event
```

时间对不上。

---

# 61. 日志

推荐：

```text
Python logging / Loguru
JSON Structured Logging
```

字段：

```text
timestamp
station
sn
step
module
device
level
message
trace_id
```

---

# 62. Prometheus

监控：

```text
DGX GPU
CPU
RAM
Disk
Inference latency
Station online
Camera FPS
MES queue
```

---

# 63. Grafana

看板：

```text
工位在线率
模型时延
NG率
报警
磁盘
GPU
```

---

# 64. Docker

DGX建议所有服务容器化：

```text
docker compose
```

---

# 65. Docker Compose

服务：

```yaml
services:
  api:
  inference:
  training:
  cvat:
  postgres:
  minio:
  mlflow:
  prometheus:
  grafana:
```

---

# 66. Nginx

统一：

```text
HTTPS
Reverse Proxy
TLS
```

---

# 67. 测试

Python：

```text
pytest
```

API：

```text
Postman
```

压力：

```text
Locust
```

---

# 68. FAT

工厂验收前：

```text
Camera
Scanner
Printer
Serial
PLC
DGX
MES Mock
FSM
```

全部模拟。

---

# 69. SAT

现场：

```text
真实产品
真实MES
真实相机
真实设备
真实网络
```

---

# 70. 跨产线迁移

技术层：

```text
Station Config
Recipe
Calibration
Model Registry
Adapter
```

---

# 71. 推荐 GitHub

## Detection

- https://github.com/ultralytics/ultralytics
- https://github.com/lyuwenyu/RT-DETR
- https://github.com/Peterande/D-FINE

## Anomaly

- https://github.com/open-edge-platform/anomalib
- https://github.com/amazon-science/patchcore-inspection

## Annotation

- https://github.com/cvat-ai/cvat
- https://github.com/HumanSignal/label-studio

## Dataset

- https://github.com/voxel51/fiftyone
- https://github.com/open-edge-platform/datumaro
- https://github.com/iterative/dvc

## Foundation

- https://github.com/IDEA-Research/GroundingDINO
- https://github.com/facebookresearch/sam2
- https://github.com/IDEA-Research/Grounded-SAM-2

## Segmentation

- https://github.com/open-mmlab/mmsegmentation

## Tracking

- https://github.com/noahcao/OC_SORT

## Pose

- https://github.com/open-mmlab/mmpose
- https://github.com/NVlabs/FoundationPose

## Video

- https://github.com/open-mmlab/mmaction2

## OCR

- https://github.com/PaddlePaddle/PaddleOCR

## MES / OPC UA

- https://github.com/open62541/open62541

---

# 72. 推荐代码目录

```text
sop-platform/

├── station/
│   ├── device_registry/
│   ├── camera/
│   ├── scanner/
│   ├── printer/
│   ├── serial/
│   ├── burner/
│   ├── plc/
│   ├── tool/
│   ├── fsm/
│   └── hmi/
│
├── ai/
│   ├── detection/
│   ├── anomaly/
│   ├── segmentation/
│   ├── tracking/
│   ├── pose/
│   ├── ocr/
│   └── inference/
│
├── data/
│   ├── collector/
│   ├── cleaner/
│   ├── annotation/
│   ├── converter/
│   └── qa/
│
├── training/
├── validation/
├── registry/
├── mes/
├── api/
├── recipes/
├── calibration/
├── configs/
├── tests/
└── deploy/
```

---

# 73. 数据流水线最终推荐

```text
Camera
 ↓
Raw Video
 ↓
Frame Extract
 ↓
Integrity Check
 ↓
Blur/Exposure Filter
 ↓
Duplicate Removal
 ↓
Hard Case Selection
 ↓
Pre-Label
 ↓
CVAT
 ↓
Review
 ↓
Datumaro
 ↓
FiftyOne QA
 ↓
DVC Version
 ↓
Train/Val/Frozen Test
 ↓
Training
 ↓
Validation
 ↓
TensorRT
 ↓
Model Registry
```

---

# 74. 最推荐的数据软件组合

如果只选一套：

```text
FFmpeg
+
OpenCV
+
CVAT
+
FiftyOne
+
Datumaro
+
DVC
+
MinIO
+
PostgreSQL
```

---

# 75. 数据部分优先级

P0：

```text
采集规范
命名
Metadata
CVAT
标注规范
Frozen Test
数据泄漏检查
Hard Negative
```

P1：

```text
FiftyOne
Datumaro
DVC
主动学习
自动预标注
```

P2：

```text
Grounding DINO
SAM2
Embedding去重
DINO Feature Mining
```

---

# 76. 项目第一阶段最小软件组合

IPC：

```text
Python
OpenCV
GStreamer
pyserial
FastAPI Client
SQLite
Vue HMI
```

DGX：

```text
Docker
PyTorch
TensorRT
Triton
FastAPI
CVAT
FiftyOne
PostgreSQL
MinIO
MLflow
Prometheus
Grafana
```

---

# 77. 最终结论

这个项目真正涉及的技术不是单纯：

```text
YOLO
```

而是：

```text
工业设备接入
+
工业网络
+
工业机器视觉
+
深度学习
+
数据工程
+
数据清洗
+
数据标注
+
MLOps
+
TensorRT
+
MES
+
FSM
+
HMI
+
数据库
+
对象存储
+
监控
+
测试
```

其中真正决定算法能不能长期稳定运行的是：

> **数据采集 → 数据清洗 → 标注规范 → 数据QA → Frozen Test → Hard Case回流 → Dataset Version。**

模型只是整个系统的一部分。

---

# 78. 一句话总结

> **宁波 MES + 视觉 SOP 项目应该建设成“设备平台 + 数据平台 + AI平台 + SOP规则平台 + MES业务平台”的组合系统，其中数据清洗、标注规范、数据版本和失败样本回流是决定跨产线泛化能力的核心基础设施。**
