# CVAT Webhook 与 Annotation-only 后端开发说明

状态：开发分支已实现并通过隔离测试，尚未部署到 8096。

## 1. 隔离边界

开发工作树：

```text
/home/xjai/Desktop/sop xjai/sop-backend-dev-20260822
```

开发服务只监听 `127.0.0.1:8110`，使用独立 `SOP_RUNTIME_DIR`，关闭摄像头自动启动。8096、8099、8101 至 8105 和 CVAT 不需要停止或重启。

## 2. 已实现链路

```text
CVAT update:job / update:task
  -> POST /api/cvat/webhook
  -> HMAC-SHA256 验签
  -> Task ID 和 video_id 绑定
  -> 去重并进入受限并发队列
  -> GET /api/tasks/{task_id}/annotations
  -> GET /api/labels?task_id={task_id}
  -> 内容 SHA256 和不可变版本目录
  -> frame_manifest.json
  -> SQLite cvat_annotation_versions
```

只有 `job.stage=acceptance` 且 `job.state=completed` 才把版本标为 `accepted` 和 `training_eligible=true`。普通标注完成仍是 `pending_review`，不会自动训练。

## 3. 接口

| 方法 | 路径 | 权限 | 用途 |
| --- | --- | --- | --- |
| POST | `/api/cvat/webhook` | HMAC 签名 | CVAT 事件入口，返回 202 |
| POST | `/api/cvat/annotations/pull` | 管理者/开发者 | 手工排队拉取 annotation-only |
| GET | `/api/cvat/annotation-versions?task_id=...` | 已登录 | 查看内容版本、SHA256 和 Manifest |
| GET | `/api/cvat/sync/jobs` | 已登录 | 查看 queued/waiting/running/completed/failed |

Webhook 支持 `X-Signature-256: sha256=<hex>`，也兼容 `X-CVAT-Signature`。未配置 `SOP_CVAT_WEBHOOK_SECRET` 时返回 503，签名错误返回 401，无关事件验签后返回 202/ignored。

## 4. 文件布局

```text
$SOP_RUNTIME_DIR/
  cvat_annotation_versions/
    task-<id>/
      CVAT-<id>-v<version>-<sha16>/
        annotations.json
        frame_manifest.json
  cvat_sync_jobs/
    <job-id>/status.json
  sop_annotations.sqlite3
```

相同 Task、CVAT version 和内容哈希重复回调时不复制数据。已 accepted 的同内容版本不会被后续 pending 事件降级。

## 5. 配置和发布

参考 `config/cvat_closed_loop.example.env`。真实 Token 和 Webhook Secret 只能放在权限受控的环境文件，不进入 Git。

发布步骤：

1. 备份 8096 SQLite、WAL、配置和当前 Git 提交。
2. 在预发布端口使用生产 CVAT 的只读测试 Task 验证拉取、标签、Track 和大任务。
3. 在 CVAT 创建 Webhook，目标指向受控内网 SOP 地址，并配置相同 Secret。
4. 验证重复事件、错误签名、CVAT 断线、超大响应、并发和恢复。
5. 通过后安排维护窗口切换 8096；当前开发分支不会自动替换线上服务。

## 6. 测试结果

- 4 个单元测试覆盖 HMAC、嵌套 Task ID、最终验收状态、版本幂等、Frame Manifest、Task/video 绑定、模拟 API 拉取和同步任务去重。
- 8110 接口验证：health 200、未登录 401、登录 200、版本/任务查询 200、错误签名 401、正确无关事件 202。
- 缺少开发 CVAT Token 时异步任务进入 failed 并返回明确原因，没有虚构成功。
- 测试 runtime 使用临时目录，不写 8096 或开发实例数据库。
