# SOP 部署说明

`source/` 包含经过脱敏的 SOP 核心源码快照，包括 HTTP 服务、Web 界面和示例配置；其来源基线固定为 [`lemonbaby2/work@2395071`](https://github.com/lemonbaby2/work/tree/2395071fa51cc68a84897c7e13a2c0bdf9677db9)。Dockerfile 直接从该快照构建，不依赖另一个仓库在构建时保持可用。

公开快照提供基础网页、SQLite 标注、审计与配置浏览能力。模型、数据集、运行数据库及实际摄像头配置通过只读或持久化卷挂载，不写入公开镜像或仓库。

```bash
docker compose up -d --build
curl -f http://127.0.0.1:8096/api/health
```

摄像头、预标注与训练路径会在调用时导入 OpenCV、Ultralytics 和相关依赖。基础镜像没有预装这些大型依赖；生产镜像必须根据 GPU/CUDA、驱动和模型许可单独锁定。

`source/requirements.txt` 是生产功能依赖清单，不由基础 Dockerfile 自动安装。这样可以避免在仅需查看、标注和审计功能时下载 GPU/视觉推理依赖。
