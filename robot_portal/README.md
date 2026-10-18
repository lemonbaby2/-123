# 具身学习实验室

公网网站：https://lemonbaby2.github.io/-123/

源代码位于 `hello-robot-tasks` 分支的 `robot_portal/`；部署产物位于 `gh-pages`。页面为静态 HTML/CSS/JS，笔记在构建时转换为 HTML，视频和仿真文件均由 Pages 托管，不依赖个人电脑在线。

## 构建

```powershell
python -m pip install markdown
python robot_portal/build.py --output E:/robot-public-site --sim-build /path/to/mjswan/dist/microduck
```

`--output` 指定专用产物目录。已有部署 checkout 可在构建后 `git add .`、commit、push 到 `gh-pages`。`pages.py status` 使用现有 Git credential helper 检查部署状态，不输出或写入凭据。

仿真来自 mjswan 0.11.9 构建，路径适配到 `/-123/sim/`；局限在该目录下的 Service Worker 增加跨域隔离响应头以支持 WASM 共享内存。首次打开可能自动刷新一次。浏览器无法运行时可查看托管录像。相关模型许可随仿真构建保留。

## 实验改进

- Hello-Robot 路径与轨迹增加真实碰撞/时间断言，报告记录碰撞检测范围。
- 合成数据不再标记物理任务成功。
- 增加由计算结果逐帧生成的 G2 轨迹 MP4/GIF。
- 网站提供七篇完整笔记、搜索、专题筛选、录像切换/下载、MicroDuck 在线物理仿真与 G2 轮式运动学交互。

完整 Isaac Sim、YOLO、VLA 与前沿模型部署仍未完成；公开页面明确显示相应实验范围。
