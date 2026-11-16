#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W13 课程资源完整包：讲义 + Excel + 5 分钟视频 + 门户页 + 远程连接文件。"""
import os, shutil, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(ROOT, 'pack', 'W13_Gazebo与ROS2桥接课程资源包_20261116')
ZIP = os.path.join(ROOT, 'pack', 'W13_Gazebo与ROS2桥接课程资源包_20261116.zip')

if os.path.isdir(PACK):
    shutil.rmtree(PACK)
for d in ['01_课件讲义', '02_全量命令手册', '03_五分钟演示片', '04_门户网页', '05_远程连接DGX']:
    os.makedirs(os.path.join(PACK, d), exist_ok=True)

copies = [
    (os.path.join(ROOT, 'out', 'Gazebo世界模型与ROS2桥接_课件讲义_20261116.docx'), '01_课件讲义'),
    (os.path.join(ROOT, 'out', 'Gazebo世界模型与ROS2桥接_课件讲义_20261116.pdf'), '01_课件讲义'),
    (os.path.join(ROOT, 'out', 'ROS2与Ubuntu全量命令与验证代码手册_20261116.xlsx'), '02_全量命令手册'),
    (os.path.join(ROOT, 'media', 'w13_demo.mp4'), '03_五分钟演示片'),
    (os.path.join(ROOT, 'portal', 'index.html'), '04_门户网页'),
    (os.path.join(ROOT, 'remote_pc', '远程PC连接DGX_操作说明.md'), '05_远程连接DGX'),
    (os.path.join(ROOT, 'remote_pc', '<LOCAL_CONNECT_SCRIPT>'), '05_远程连接DGX'),
    (os.path.join(ROOT, 'remote_pc', '<PRIVATE_KEY>'), '05_远程连接DGX'),
    (os.path.join(ROOT, 'remote_pc', '<PRIVATE_KEY>.pub'), '05_远程连接DGX'),
    (os.path.join(ROOT, 'remote_pc', 'ssh_config_片段.txt'), '05_远程连接DGX'),
]
for src, folder in copies:
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(PACK, folder, os.path.basename(src)))
    else:
        print('MISSING:', src)

readme = '''# W13 课程资源包（2026-11-16）

## 里面有什么

| 目录 | 内容 |
|---|---|
| 01_课件讲义 | 明日课 Word 讲义 + PDF：Gazebo 世界 / 模型 / ROS2 桥接，含 3 组师生互问互答与 2 张实拍图 |
| 02_全量命令手册 | Excel 12 表：22.04 / 24.04 / 26.04 验证矩阵、ROS2 与 Ubuntu 全量命令、故障库、学习网站 |
| 03_五分钟演示片 | 300 秒真实录屏：Gazebo → RViz → 网页看板 → Gazebo，H.264 1920x1080 |
| 04_门户网页 | 单页离线可开：视频播放器 + 命令搜索 + 网站收藏 + 完整启动命令 |
| 05_远程连接DGX | 私钥 + 一键 bat + 操作说明（**私钥保密，只发给对方 PC 本人**） |

## 三个地址（DGX 上已启动）

- 课程资源门户：`http://<LAB_HOST>:8140/`（tailnet：`http://<TAILNET_HOST>:8140/`）
- 课堂实时看板：`http://<LAB_HOST>:8130/`
- SSH：`ssh <USER>@<TAILNET_HOST>`（密码 nvidia），或 `ssh -i <PRIVATE_KEY> <USER>@<TAILNET_HOST>`

## 完整启动

```bash
export ROS_DOMAIN_ID=42 GZ_PARTITION=w12course
cd ~/ros2_ws_w12 && MODE=pid AUTO_BROWSER=1 bash 01_启动课堂.sh
bash src/week12_odometry/scripts/check_w12.sh    # PASS=24 FAIL=0
bash src/week12_odometry/scripts/drive_demo.sh all
bash 02_停止全部.sh                               # 下课清场
```

## 证据等级

A=2026-11-16 DGX 实跑；B=Ubuntu 22.04/Humble 课程环境按官方接口编写；C=Ubuntu 26.04 无本机样本，标注待核，不冒充实测。
'''
with open(os.path.join(PACK, '00_交付说明.md'), 'w', encoding='utf-8') as f:
    f.write(readme)

n = 0
with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for dp, dns, fns in os.walk(PACK):
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            z.write(p, os.path.relpath(p, os.path.dirname(PACK)).replace('\\', '/'))
            n += 1
with zipfile.ZipFile(ZIP) as z:
    bad = z.testzip()
print('files:', n, 'MB:', round(os.path.getsize(ZIP) / 1048576, 2), 'integrity:', 'OK' if bad is None else bad)
print('zip:', ZIP)
