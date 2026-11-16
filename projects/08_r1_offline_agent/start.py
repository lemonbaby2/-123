#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R1-VLA 离线自学习 Agent · 完整启动入口

用法:
  python start.py --offline --web                  # 断网启动本地控制台 (默认)
  python start.py --offline --loop --budget 60     # 内测窗口(秒, 演示用 60; 生产填 72000=20h)
  python start.py --offline --web --loop           # 控制台 + 后台自学习
  python start.py --ingest <目录或文件>            # 吸收一份新文档到知识库

设计目标: 无 WiFi / 无外网也能回答、试错、记忆、上线。
所有外部连接被 guard 拦截(仅放行 127.0.0.1 本地 Ollama)。
"""
from __future__ import annotations
import argparse
import datetime as dt
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core import KB, Agent, install_guard, selflearn
from core.web import serve

CORPUS = ROOT / "corpus"
TASKS = ROOT / "tasks" / "sample_tasks.jsonl"
MEM = ROOT / "memory"


def boot_kb():
    kb = KB(MEM)
    kb.load()
    if len(kb) == 0 and CORPUS.exists():
        n = kb.ingest_dir(CORPUS)
        kb.save()
        print("[boot] 知识库首次构建: 吸收 %d 篇文档" % n)
    else:
        print("[boot] 知识库载入: %d 篇文档" % len(kb))
    return kb


def run_loop(agent, budget, topk=5):
    tasks = selflearn.load_tasks(TASKS)
    if not tasks:
        print("[loop] 无任务库, 跳过")
        return
    print("[loop] 内测窗口 %ds 启动, 任务库 %d 条" % (budget, len(tasks)))
    win = selflearn.run(agent, tasks, budget_seconds=budget, topk=topk)
    print("[loop] 本窗口:", win)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="开启离线网络护栏(默认True)")
    ap.add_argument("--no-offline", dest="offline", action="store_false")
    ap.add_argument("--web", action="store_true", help="启动本地 Web 控制台")
    ap.add_argument("--loop", action="store_true", help="启动每日自学习内测")
    ap.add_argument("--budget", type=int, default=72000, help="内测窗口秒数(默认72000=20h)")
    ap.add_argument("--port", type=int, default=18941)
    ap.add_argument("--model", default="qwen2.5:7b")
    ap.add_argument("--ingest", help="吸收一份新文档/目录到知识库后退出")
    ap.add_argument("--reconcile", action="store_true", help="复核历史错误项后退出")
    ap.set_defaults(offline=True)
    a = ap.parse_args()

    if a.offline:
        install_guard(strict=True)
        print("[guard] 离线护栏已开启: 仅 127.0.0.1 可连")

    kb = boot_kb()
    agent = Agent(kb, model=a.model)

    if a.ingest:
        r = agent.act("ingest", {"path": a.ingest})
        print("[ingest]", r)
        return
    if a.reconcile:
        print("[reconcile]", selflearn.reconcile(agent))
        return

    print("[status]", selflearn.status(agent.kb))

    if a.loop and a.web:
        t = threading.Thread(target=run_loop, args=(agent, a.budget), daemon=True)
        t.start()

    if a.web:
        httpd = serve(agent, port=a.port, host="127.0.0.1")
        print("[web] 控制台: http://127.0.0.1:%d  (仅本机)" % a.port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[shutdown] 已停止")
    elif a.loop:
        # 单独 --loop: 前台跑完预算窗口后退出 (用于内测/演示)
        run_loop(agent, a.budget)
    else:
        # 默认: 跑一次问答演示后退出
        import json
        demo = selflearn.load_tasks(TASKS)[:3]
        for q in demo:
            print("\nQ:", q)
            print(json.dumps(agent.understand(q), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
