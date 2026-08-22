# SOP 部署说明

公开源码基线位于 [`lemonbaby2/work`](https://github.com/lemonbaby2/work/tree/lzpsop20260821)，固定提交为 `2395071fa51cc68a84897c7e13a2c0bdf9677db9`。

本目录的 Dockerfile 提供基础网页、SQLite 标注、审计与配置浏览能力。构建上下文需要包含该提交中的 `server.py`、`web/` 和 `config/`。模型、数据集与运行数据库通过只读或持久化卷挂载，不写入公开镜像。

```bash
docker compose up -d --build
curl -f http://127.0.0.1:8096/api/health
```

摄像头、预标注与训练路径会在调用时导入 OpenCV、Ultralytics 和相关依赖。基础镜像没有预装这些大型依赖；生产镜像必须根据 GPU/CUDA、驱动和模型许可单独锁定。

