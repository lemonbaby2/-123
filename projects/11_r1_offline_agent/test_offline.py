#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线合规自检: 验证 guard 拦截外联 + Web 接口本地可用。"""
import socket
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from core import KB, Agent, install_guard
from core.web import serve

print("== 1. 离线护栏: 应拦截非回环连接 ==")
install_guard(strict=True)
blocked = False
try:
    socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
except PermissionError as e:
    blocked = True
    print("   拦截成功:", e)
print("   结果:", "PASS" if blocked else "FAIL")

print("== 2. 知识库检索(纯本地, 断网) ==")
kb = KB(ROOT / "memory"); kb.load()
r = kb.search("WALL-OSS-0.5 许可证", topk=3)
print("   命中:", [(x["title"], x["score"]) for x in r])
assert r, "检索失败"
print("   结果: PASS")

print("== 3. 离线问答(无 Ollama 走兜底) ==")
ag = Agent(kb)
res = ag.understand("Jetson AGX Orin 32GB 的 CUDA 核数?")
print("   verified=%s grounded=%s used_llm=%s" % (res["verified"], res["groundedness"], res["used_llm"]))
assert res["verified"], "问答未通过校验"
print("   结果: PASS")

print("== 4. Web 本地接口 ==")
httpd = serve(ag, port=18949, host="127.0.0.1")
import threading
threading.Thread(target=httpd.serve_forever, daemon=True).start()
time.sleep(0.5)
with urllib.request.urlopen("http://127.0.0.1:18949/api/status", timeout=5) as rp:
    st = rp.read().decode()
print("   /api/status:", st[:120])
with urllib.request.urlopen("http://127.0.0.1:18949/api/ask?q=" + urllib.parse.quote("WALL-OSS-0.5 参数量"), timeout=10) as rp:
    ak = rp.read().decode()
print("   /api/ask 返回长度:", len(ak))
httpd.shutdown()
print("   结果: PASS")
print("\nALL OFFLINE CHECKS PASSED")
