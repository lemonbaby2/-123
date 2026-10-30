"""以完全分离的进程启动 serve.py（不随 agent 会话退出）。
用法: python launch.py [--port 18355]
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
port = "18355"
if "--port" in sys.argv:
    port = sys.argv[sys.argv.index("--port") + 1]

out = open(os.path.join(ROOT, "logs", "serve.out.log"), "ab")
err = open(os.path.join(ROOT, "logs", "serve.err.log"), "ab")

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000

p = subprocess.Popen(
    [sys.executable, os.path.join(ROOT, "serve.py"), "--host", "0.0.0.0", "--port", port],
    cwd=ROOT, stdout=out, stderr=err, stdin=subprocess.DEVNULL,
    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
    close_fds=True,
)
print(f"已分离启动 PID={p.pid} port={port}")
time.sleep(2.5)
print(f"进程状态: {'运行中' if p.poll() is None else '已退出 code=' + str(p.poll())}")
