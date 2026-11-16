#!/usr/bin/env python3
"""
server.py —— W12 课堂网页看板服务端（只用 Python 标准库）
========================================================
为什么不用 Flask / rosbridge：
  · 教室机器不一定能联网装包，标准库一定在；
  · 大屏要常驻，依赖越少越不容易被别的服务升级搞坏；
  · 「浏览器读本地 JSON」这件事，课堂上比 WebSocket 好讲得多。

路由：
  GET /                     → index.html
  GET /app.js  /style.css   → 静态资源
  GET /api/data             → 转发 /tmp/w12_dashboard.json（no-store）
  GET /api/cmd?linear=&angular=  → 原子写 /tmp/w12_cmd.json（网页开车）
  GET /api/stop             → 写零速等价于停止
  GET /maps/<file>          → 保存的 pgm / yaml

启动：
  python3 server.py --port 8130 --data /tmp/w12_dashboard.json
"""
import argparse
import json
import mimetypes
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = '/tmp/w12_dashboard.json'
CMD = '/tmp/w12_cmd.json'


def atomic_json(path, doc):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    os.replace(tmp, path)


class Handler(BaseHTTPRequestHandler):
    server_version = 'W12Dashboard/1.0'

    def log_message(self, fmt, *args):
        # 只记 API，静态资源不刷屏
        if args and str(args[0]).startswith('/api'):
            super().log_message(fmt, *args)

    def _send(self, code, body, ctype='application/json; charset=utf-8',
              extra=None):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store, must-revalidate')
        self.send_header('Access-Control-Allow-Origin', '*')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False, allow_nan=False))

    def _file(self, rel, ctype=None):
        p = os.path.normpath(os.path.join(HERE, rel))
        if not p.startswith(HERE) or not os.path.isfile(p):
            return self._json({'error': 'not found', 'path': rel}, 404)
        ctype = ctype or mimetypes.guess_type(p)[0] or 'application/octet-stream'
        with open(p, 'rb') as f:
            self._send(200, f.read(), ctype)

    def do_GET(self):
        u = urlparse(self.path)
        path, qs = u.path, parse_qs(u.query)

        if path in ('/', '/index.html'):
            return self._file('index.html', 'text/html; charset=utf-8')
        if path in ('/app.js', '/style.css'):
            return self._file(path.lstrip('/'),
                              'application/javascript; charset=utf-8'
                              if path.endswith('.js') else 'text/css; charset=utf-8')
        if path.startswith('/maps/'):
            return self._file(path.lstrip('/'))

        if path == '/api/data':
            try:
                with open(DATA, 'r', encoding='utf-8') as f:
                    return self._send(200, f.read())
            except OSError:
                return self._json({'ok': False, 'hint': 'telemetry_node 尚未产出数据'}, 200)

        if path in ('/api/cmd', '/api/stop'):
            if path == '/api/stop':
                linear = angular = 0.0
            else:
                try:
                    linear = max(-1.0, min(1.0, float(qs.get('linear', ['0'])[0])))
                    angular = max(-2.5, min(2.5, float(qs.get('angular', ['0'])[0])))
                except ValueError:
                    return self._json({'error': 'bad number'}, 400)
            atomic_json(CMD, {'linear': linear, 'angular': angular,
                              'ts': time.time(), 'src': 'dashboard'})
            return self._json({'ok': True, 'linear': linear, 'angular': angular})

        if path == '/api/ping':
            return self._json({'ok': True, 'ts': time.time()})

        return self._json({'error': 'not found'}, 404)


def main():
    global DATA, CMD
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8130)
    ap.add_argument('--data', default=DATA)
    ap.add_argument('--cmd', default=CMD)
    ap.add_argument('--bind', default='0.0.0.0')
    a = ap.parse_args()
    DATA, CMD = a.data, a.cmd
    os.makedirs(os.path.join(HERE, 'maps'), exist_ok=True)
    srv = ThreadingHTTPServer((a.bind, a.port), Handler)
    srv.daemon_threads = True
    print(f'W12 看板已启动： http://127.0.0.1:{a.port}/   data={DATA}', flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == '__main__':
    main()
