#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线 Web 控制台 (仅绑定 127.0.0.1, 不对外暴露)

提供: 提问框 -> agent.understand -> 渲染答案+依据+校验; 状态页。
依赖仅标准库, 断网可用。
"""
from __future__ import annotations
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .agent import Agent

PAGE = """
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>R1-VLA 离线自学习 Agent</title>
<style>
:root{--bg:#0f1420;--panel:#171d2b;--line:#26304a;--txt:#e6ebf5;--sub:#8a93a8;
--brand:#5b8cff;--ok:#34d399;--warn:#fbbf24;--err:#f87171}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);
font:14px/1.6 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
.wrap{max-width:920px;margin:0 auto;padding:22px}
h1{font-size:20px;margin:0 0 4px}.badge{font-size:12px;padding:2px 9px;border-radius:99px;
background:#1e2740;color:var(--brand);margin-left:8px}
.note{color:var(--sub);font-size:12px;margin-bottom:14px}
.box{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:14px}
textarea,input{width:100%;background:#0c111c;border:1px solid var(--line);color:var(--txt);
border-radius:8px;padding:10px;font:inherit;resize:vertical}
button{margin-top:8px;background:var(--brand);color:#fff;border:0;border-radius:8px;
padding:9px 16px;font-weight:600;cursor:pointer}
.ans{white-space:pre-wrap;margin-top:10px}
.src{font-size:12px;color:var(--sub);margin-top:8px}
.tag{display:inline-block;font-size:12px;padding:1px 8px;border-radius:6px;margin-right:6px}
.ok{background:#10331f;color:var(--ok)}.bad{background:#3a1d1d;color:var(--err)}
pre{white-space:pre-wrap;background:#0c111c;border:1px solid var(--line);border-radius:8px;padding:10px;overflow:auto}
</style></head>
<body><div class="wrap">
<h1>R1-VLA 离线自学习 Agent<span class="badge" id="mode">离线</span></h1>
<div class="note">断网可用 · 答案全部来自本地知识库 · 不调用任何外部服务</div>
<div class="box"><textarea id="q" rows="3" placeholder="输入问题, 例如: WALL-OSS-0.5 的参数量与许可证?"></textarea>
<button onclick="ask()">提问 (本地知识库)</button>
<div class="ans" id="ans"></div><div class="src" id="src"></div></div>
<div class="box"><b>自学习状态</b><pre id="st">loading…</pre></div>
</div>
<script>
async function ask(){
  const q=document.getElementById('q').value.trim(); if(!q)return;
  const r=await fetch('/api/ask?q='+encodeURIComponent(q)); const d=await r.json();
  const v=d.verified?'<span class="tag ok">已校验</span>':'<span class="tag bad">待复核</span>';
  document.getElementById('ans').innerHTML=v+' '+ (d.answer||'');
  document.getElementById('src').textContent='依据: '+(d.passages||[]).map(p=>p.title+'('+p.score+')').join(' | ')+
    ' ｜ 依据性='+d.groundedness+' ｜ '+(d.verify_reason||'');
}
async function st(){const r=await fetch('/api/status');document.getElementById('st').textContent=JSON.stringify(await r.json(),null,2);}
st(); setInterval(st,5000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    agent: Agent = None
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ct="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if u.path == "/api/ask":
            q = urllib.parse.parse_qs(u.query).get("q", [""])[0]
            res = self.agent.understand(q) if q else {"error": "empty"}
            return self._send(200, json.dumps(res, ensure_ascii=False))
        if u.path == "/api/status":
            from . import selflearn
            return self._send(200, json.dumps(selflearn.status(self.agent.kb), ensure_ascii=False))
        return self._send(404, json.dumps({"error": "not found"}, ensure_ascii=False))


def serve(agent: Agent, port: int = 18941, host: str = "127.0.0.1"):
    Handler.agent = agent
    return ThreadingHTTPServer((host, port), Handler)
