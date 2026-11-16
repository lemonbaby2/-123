#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""支持 HTTP Range 的静态服务器：让 5 分钟 MP4 可以拖动进度条。"""
import os, re, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.abspath(os.environ.get('PORTAL_ROOT', os.path.dirname(os.path.abspath(__file__))))

class RangeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'public, max-age=60')
        super().end_headers()

    def do_GET(self):
        path = self.translate_path(self.path)
        if os.path.isfile(path) and 'Range' in self.headers:
            m = re.match(r'bytes=(\d*)-(\d*)', self.headers['Range'])
            if m:
                size = os.path.getsize(path)
                start = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2) or 0))
                end = int(m.group(2)) if m.group(2) else size - 1
                end = min(end, size - 1)
                if start <= end:
                    with open(path, 'rb') as f:
                        f.seek(start)
                        data = f.read(end - start + 1)
                    self.send_response(206)
                    self.send_header('Content-Type', self.guess_type(path))
                    self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
        super().do_GET()

    def log_message(self, fmt, *args):
        pass  # 安静运行

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8140
    srv = ThreadingHTTPServer(('0.0.0.0', port), RangeHandler)
    print(f'serving {ROOT} on 0.0.0.0:{port}', flush=True)
    srv.serve_forever()
