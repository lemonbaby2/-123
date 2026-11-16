# -*- coding: utf-8 -*-
"""生成 W12 网页看板：server.py + index.html + app.js + style.css。"""
import os

DASH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'ros2_ws_w12', 'dashboard')
FILES = {}

FILES['server.py'] = r'''#!/usr/bin/env python3
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
'''

FILES['index.html'] = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>第12周 · 里程计与 PID 课堂看板</title>
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header class="topbar">
  <div class="brand">
    <span class="dot" id="live"></span>
    <b>W12 课堂实时看板</b>
    <span class="sub">运动学 / 里程计 / PID / SLAM</span>
  </div>
  <div class="stats" id="stats">
    <span>数据 <b id="s_age">—</b></span>
    <span>odom <b id="s_odom">—</b> Hz</span>
    <span>scan <b id="s_scan">—</b> Hz</span>
    <span>map <b id="s_map">—</b> Hz</span>
    <span>误差 <b id="s_err">—</b> m</span>
  </div>
</header>

<main>
  <section class="control">
    <div class="ctl-title">驾驶台 <span class="hint">按住按钮持续发指令；松手 0.6 s 后看门狗自动停车</span></div>
    <div class="ctl-row">
      <div class="pad">
        <button data-l="0.35" data-a="0"      class="k up">↑ 前进</button><br>
        <button data-l="0"    data-a="0.8"    class="k left">↰ 左转</button>
        <button data-l="0"    data-a="0"      class="k stop">■ 停</button>
        <button data-l="0"    data-a="-0.8"   class="k right">↱ 右转</button><br>
        <button data-l="-0.25" data-a="0"     class="k down">↓ 后退</button>
        <button data-l="0.30" data-a="0.60"   class="k circle">⟳ 画圈</button>
      </div>
      <div class="readout">
        <div class="ro"><label>目标 v</label><b id="r_target">0.000</b><span>m/s</span></div>
        <div class="ro"><label>实测 v</label><b id="r_meas">0.000</b><span>m/s</span></div>
        <div class="ro"><label>误差 e</label><b id="r_err">0.000</b><span>m/s</span></div>
        <div class="ro"><label>P / I / D</label><b id="r_pid">0 / 0 / 0</b><span></span></div>
        <div class="ro"><label>输出 u</label><b id="r_out">0.000</b><span>m/s</span></div>
        <div class="ro"><label>位置</label><b id="r_pos">0.00, 0.00</b><span>m</span></div>
      </div>
      <div class="tips">
        <p><b>课堂提示</b></p>
        <p>蓝线＝轮式里程计，灰线＝Gazebo 真值。两条线分开就是漂移。</p>
        <p>PID 曲线里目标与实测不重合时，P/I/D 三项会把它补回来。</p>
        <p>右下角栅格是 slam_toolbox 实时建的图，画圈一圈后能看到回环对齐。</p>
        <p>键盘：<kbd>W</kbd><kbd>S</kbd><kbd>A</kbd><kbd>D</kbd> / <kbd>空格</kbd> 停车</p>
      </div>
    </div>
  </section>

  <section class="grid">
    <div class="card">
      <div class="card-h"><b>① 里程计 vs 真值轨迹</b><span id="c1n">odom 蓝 / truth 灰</span></div>
      <canvas id="c_trail"></canvas>
    </div>
    <div class="card">
      <div class="card-h"><b>② PID 速度闭环曲线</b><span id="c2n">目标 / 实测 / 输出</span></div>
      <canvas id="c_pid"></canvas>
    </div>
    <div class="card">
      <div class="card-h"><b>③ 2D 激光雷达极坐标</b><span id="c3n">/scan</span></div>
      <canvas id="c_scan"></canvas>
    </div>
    <div class="card">
      <div class="card-h"><b>④ SLAM 占用栅格地图</b><span id="c4n">/map</span></div>
      <canvas id="c_map"></canvas>
    </div>
  </section>

  <footer>
    <span>数据源 /tmp/w12_dashboard.json · telemetry_node.py</span>
    <span>控制链路 /api/cmd → /tmp/w12_cmd.json → velocity_arbiter.py → /diff_drive_controller/cmd_vel</span>
    <span>广州现代信息工程职业技术学院 · 第12周</span>
  </footer>
</main>
<script src="/app.js"></script>
</body>
</html>
'''

FILES['style.css'] = r'''*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0d1117; --panel:#151c26; --panel2:#1b2430; --line:#2a3646;
  --txt:#e6edf5; --dim:#8b9bb0; --blue:#3fa9ff; --gray:#8794a5;
  --green:#3ddc97; --amber:#ffc857; --red:#ff6b6b;
}
body{background:var(--bg);color:var(--txt);font:14px/1.5 "Noto Sans CJK SC","Microsoft YaHei",system-ui,sans-serif}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:10px 18px;
  background:linear-gradient(90deg,#111a26,#0d1117);border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:10px;font-size:17px}
.brand .sub{color:var(--dim);font-size:12px;font-weight:400}
.dot{width:10px;height:10px;border-radius:50%;background:#555;box-shadow:0 0 0 3px #ffffff10}
.dot.on{background:var(--green);box-shadow:0 0 10px var(--green)}
.dot.off{background:var(--red)}
.stats{display:flex;gap:18px;color:var(--dim);font-size:12px}
.stats b{color:var(--txt);font-variant-numeric:tabular-nums}
main{padding:12px 16px;max-width:1900px;margin:0 auto}
.control{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin-bottom:12px}
.ctl-title{font-weight:600;margin-bottom:8px;font-size:13px}
.ctl-title .hint{color:var(--dim);font-weight:400;font-size:12px;margin-left:10px}
.ctl-row{display:grid;grid-template-columns:330px 1fr 1.2fr;gap:16px;align-items:start}
.pad button{background:var(--panel2);color:var(--txt);border:1px solid var(--line);
  border-radius:6px;padding:7px 12px;margin:2px;min-width:74px;cursor:pointer;font-size:13px}
.pad button:hover{border-color:var(--blue);background:#20304a}
.pad button.active{background:#1d4e7a;border-color:var(--blue)}
.pad button.stop{color:var(--red)}
.readout{display:grid;grid-template-columns:repeat(3,1fr);gap:6px 12px}
.ro{background:var(--panel2);border:1px solid var(--line);border-radius:6px;padding:5px 9px}
.ro label{display:block;color:var(--dim);font-size:11px}
.ro b{font:600 17px/1.3 "DejaVu Sans Mono",monospace;color:var(--blue)}
.ro span{color:var(--dim);font-size:11px;margin-left:4px}
.tips{color:var(--dim);font-size:12px;border-left:2px solid var(--line);padding-left:12px}
.tips p{margin:3px 0}
.tips b{color:var(--amber)}
kbd{background:var(--panel2);border:1px solid var(--line);border-radius:3px;padding:0 4px;font-size:11px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.card-h{display:flex;justify-content:space-between;align-items:center;padding:7px 12px;
  border-bottom:1px solid var(--line);font-size:13px}
.card-h span{color:var(--dim);font-size:11px}
canvas{display:block;width:100%;height:290px;background:#0b1017}
footer{display:flex;justify-content:space-between;gap:20px;color:#61728a;font-size:11px;padding:12px 2px 4px;flex-wrap:wrap}
@media(max-width:1100px){.grid{grid-template-columns:1fr}.ctl-row{grid-template-columns:1fr}}
'''

FILES['app.js'] = r'''/* W12 课堂看板：纯原生 Canvas，无第三方库 */
'use strict';
const $ = id => document.getElementById(id);
const P = {blue:'#3fa9ff', gray:'#8794a5', green:'#3ddc97',
           amber:'#ffc857', red:'#ff6b6b', line:'#26344a', dim:'#8b9bb0'};

let D = null;
let holdTimer = null;
let activeBtn = null;

/* ---------- 画布工具：适配高分屏 ---------- */
function prep(cv){
  const r = cv.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(1, Math.round(r.width * dpr));
  const h = Math.max(1, Math.round(r.height * dpr));
  if (cv.width !== w || cv.height !== h){ cv.width = w; cv.height = h; }
  const g = cv.getContext('2d');
  g.setTransform(dpr,0,0,dpr,0,0);
  g.clearRect(0,0,r.width,r.height);
  return {g, w:r.width, h:r.height};
}
function grid(g,w,h,step){
  g.strokeStyle = P.line; g.lineWidth = 1;
  for(let x=0;x<w;x+=step){ g.beginPath();g.moveTo(x,0);g.lineTo(x,h);g.stroke(); }
  for(let y=0;y<h;y+=step){ g.beginPath();g.moveTo(0,y);g.lineTo(w,y);g.stroke(); }
}
function text(g,s,x,y,color,size){
  g.fillStyle = color||P.dim; g.font = (size||11)+'px "DejaVu Sans Mono",monospace';
  g.fillText(s,x,y);
}

/* ---------- ① 轨迹 ---------- */
function drawTrail(){
  const {g,w,h} = prep($('c_trail'));
  grid(g,w,h,40);
  const trails = [['truth_trail',P.gray,1.5,true],['trail',P.blue,2.2,false]];
  let xs=[],ys=[];
  trails.forEach(([k])=>{ (D&&D[k]||[]).forEach(p=>{xs.push(p[0]);ys.push(p[1]);}); });
  if(D&&D.odom){xs.push(D.odom.x);ys.push(D.odom.y);}
  let cx=0,cy=0,span=6;
  if(xs.length){ const x0=Math.min(...xs),x1=Math.max(...xs),
                 y0=Math.min(...ys),y1=Math.max(...ys);
                 cx=(x0+x1)/2; cy=(y0+y1)/2;
                 span=Math.max(4,Math.max(x1-x0,y1-y0)*1.35); }
  const sc = Math.min(w,h)/span;
  const X = x => w/2 + (x-cx)*sc, Y = y => h/2 - (y-cy)*sc;
  g.strokeStyle='#3a4a60'; g.beginPath();g.moveTo(w/2,0);g.lineTo(w/2,h);g.stroke();
  g.beginPath();g.moveTo(0,h/2);g.lineTo(w,h/2);g.stroke();
  trails.forEach(([k,color,lw,dash])=>{
    const arr = (D&&D[k])||[]; if(arr.length<2) return;
    g.strokeStyle=color; g.lineWidth=lw; g.setLineDash(dash?[5,4]:[]);
    g.beginPath(); arr.forEach((p,i)=> i?g.lineTo(X(p[0]),Y(p[1])):g.moveTo(X(p[0]),Y(p[1])));
    g.stroke(); g.setLineDash([]);
  });
  if(D&&D.odom){
    g.fillStyle=P.blue; g.beginPath();g.arc(X(D.odom.x),Y(D.odom.y),5,0,7);g.fill();
    g.strokeStyle=P.amber;g.lineWidth=2;
    g.beginPath();g.moveTo(X(D.odom.x),Y(D.odom.y));
    g.lineTo(X(D.odom.x)+Math.cos(D.odom.yaw)*16,
             Y(D.odom.y)-Math.sin(D.odom.yaw)*16);g.stroke();
  }
  if(D&&D.truth){ g.strokeStyle=P.gray;g.lineWidth=1.5;
    g.beginPath();g.arc(X(D.truth.x),Y(D.truth.y),6,0,7);g.stroke(); }
  text(g,`±${(span/2).toFixed(1)} m   odom ${(D&&D.trail||[]).length} 点`,10,16);
  text(g,(D&&D.error_m!=null)?`漂移 ${D.error_m.toFixed(3)} m`:'等待真值',10,h-10,P.amber,12);
  $('c1n').textContent='odom 蓝 / truth 灰';
}

/* ---------- ② PID 曲线 ---------- */
function drawPid(){
  const {g,w,h} = prep($('c_pid'));
  grid(g,w,h,40);
  const hist = (D&&D.pid_hist)||[];
  const keys = [['target',P.blue],['measured',P.green],['out',P.amber]];
  let lo=-0.1,hi=0.9;
  hist.forEach(r=>r.slice(1).forEach(v=>{lo=Math.min(lo,v);hi=Math.max(hi,v);}));
  if(hi-lo<0.4){hi=lo+0.4;}
  const pad=8, X=i=>pad+(i/Math.max(1,hist.length-1))*(w-2*pad),
        Y=v=>h-pad-((v-lo)/(hi-lo))*(h-2*pad);
  g.strokeStyle='#3a4a60';g.beginPath();g.moveTo(0,Y(0));g.lineTo(w,Y(0));g.stroke();
  keys.forEach(([k,color],ki)=>{
    if(hist.length<2)return;
    g.strokeStyle=color;g.lineWidth=1.8;g.beginPath();
    hist.forEach((r,i)=>{const v=r[ki+1];i?g.lineTo(X(i),Y(v)):g.moveTo(X(i),Y(v));});
    g.stroke();
  });
  text(g,`${hi.toFixed(2)} m/s`,10,14); text(g,`${lo.toFixed(2)} m/s`,10,h-8);
  let lx=10; keys.forEach(([k,c])=>{g.fillStyle=c;g.fillRect(lx,h-26,9,3);
    text(g,k,lx+13,h-22,c,11);lx+=88;});
  $('c2n').textContent = `最近 ${hist.length} 帧 · ${(D&&D.pid)?'e='+D.pid.err.toFixed(3):''}`;
}

/* ---------- ③ 激光极坐标 ---------- */
function drawScan(){
  const {g,w,h} = prep($('c_scan'));
  const cx=w/2, cy=h/2, R=Math.min(w,h)/2-16;
  g.strokeStyle=P.line;
  for(let i=1;i<=4;i++){g.beginPath();g.arc(cx,cy,R*i/4,0,7);g.stroke();}
  g.beginPath();g.moveTo(cx-R,cy);g.lineTo(cx+R,cy);g.stroke();
  g.beginPath();g.moveTo(cx,cy-R);g.lineTo(cx,cy+R);g.stroke();
  const rs=(D&&D.scan&&D.scan.ranges)||[], rmax=(D&&D.scan&&D.scan.range_max)||12;
  if(rs.length){
    g.fillStyle=P.green;
    rs.forEach((r,i)=>{
      const a=-Math.PI + (i/(rs.length-1))*2*Math.PI;
      const rr=Math.min(r,rmax)/rmax*R;
      g.fillRect(cx+Math.cos(a)*rr-1.2, cy+Math.sin(a)*rr-1.2, 2.4,2.4);
    });
  }
  g.fillStyle=P.amber;g.beginPath();g.arc(cx,cy,4,0,7);g.fill();
  text(g,`${rs.length} 点 / 360°   max ${rmax.toFixed(1)} m`,10,16);
  $('c3n').textContent = rs.length?`${rs.length} 点已桥接`:'等待 /scan';
}

/* ---------- ④ 占用栅格 ---------- */
function drawMap(){
  const {g,w,h} = prep($('c_map'));
  g.fillStyle='#0b1017';g.fillRect(0,0,w,h);
  const m=D&&D.map;
  if(!m){ text(g,'等待 /map —— 跑 drive_demo.sh c 让车绕一圈',12,h/2,P.dim,13); return; }
  const cw=Math.min((w-16)/m.w,(h-16)/m.h);
  const ox=(w-m.w*cw)/2, oy=(h-m.h*cw)/2;
  for(let j=0;j<m.h;j++){
    const row=m.cells[j]||'';
    for(let i=0;i<m.w;i++){
      const c=row[i]||' ';
      if(c==='#') g.fillStyle='#c9d6e6';
      else if(c==='.') g.fillStyle='#27394d';
      else continue;
      g.fillRect(ox+i*cw,oy+j*cw,Math.ceil(cw),Math.ceil(cw));
    }
  }
  // 机器人当前位置（按 origin 换算）
  if(D&&D.odom&&m.res){
    const px=ox+(D.odom.x-m.ox)/m.res, py=oy+(m.h-(D.odom.y-m.oy)/m.res);
    g.fillStyle=P.amber;g.beginPath();g.arc(px,py,4,0,7);g.fill();
  }
  text(g,`${m.w}×${m.h}  res=${m.res.toFixed(3)} m  origin=(${m.ox.toFixed(1)},${m.oy.toFixed(1)})`,10,16);
  $('c4n').textContent='灰=未知 深蓝=空闲 白=占用';
}

/* ---------- 状态栏 ---------- */
function drawStats(){
  const fresh = D && (Date.now()/1000 - D.ts) < 3;
  $('live').className = 'dot ' + (fresh?'on':'off');
  $('s_age').textContent = D? (Date.now()/1000-D.ts).toFixed(1)+'s' : '—';
  $('s_odom').textContent = D? (D.hz.odom??0) : '—';
  $('s_scan').textContent = D? (D.hz.scan??0) : '—';
  $('s_map').textContent  = D? (D.hz.map??0) : '—';
  $('s_err').textContent  = (D&&D.error_m!=null)? D.error_m.toFixed(3):'—';
  const p=(D&&D.pid)||{};
  $('r_target').textContent=(p.target??0).toFixed(3);
  $('r_meas').textContent  =(p.measured??0).toFixed(3);
  $('r_err').textContent   =(p.err??0).toFixed(3);
  $('r_pid').textContent   =`${(p.P??0).toFixed(2)} / ${(p.I??0).toFixed(2)} / ${(p.D??0).toFixed(2)}`;
  $('r_out').textContent   =(p.out??0).toFixed(3);
  $('r_pos').textContent   = D? `${D.odom.x.toFixed(2)}, ${D.odom.y.toFixed(2)}`:'0.00, 0.00';
}

function render(){ if(!D) return;
  try{ drawTrail();drawPid();drawScan();drawMap();drawStats(); }
  catch(e){ console.warn('render',e); }
}
async function poll(){
  try{
    const r = await fetch('/api/data',{cache:'no-store'});
    const j = await r.json();
    if(j&&j.ok) D=j;
  }catch(e){ D=null; }
  render();
}
setInterval(poll,500); poll();
window.addEventListener('resize',render);

/* ---------- 控制：按住持续发，松开立刻停 ---------- */
async function cmd(l,a){
  try{ await fetch(`/api/cmd?linear=${l}&angular=${a}`,{cache:'no-store'}); }catch(e){}
}
function release(){
  if(holdTimer){clearInterval(holdTimer);holdTimer=null;}
  if(activeBtn){activeBtn.classList.remove('active');activeBtn=null;}
  cmd(0,0);
}
function hold(btn){
  release();
  activeBtn=btn;btn.classList.add('active');
  const l=parseFloat(btn.dataset.l), a=parseFloat(btn.dataset.a);
  cmd(l,a);
  // 看门狗 0.6 s，必须 100 ms 持续发，否则车会自动停
  holdTimer=setInterval(()=>cmd(l,a),100);
}
document.querySelectorAll('.pad button').forEach(b=>{
  b.addEventListener('pointerdown',e=>{e.preventDefault();hold(b);});
  b.addEventListener('pointerup',release);
  b.addEventListener('pointerleave',()=>{if(activeBtn===b)release();});
  b.addEventListener('pointercancel',release);
});
const KEYMAP={w:['0.35','0'],s:['-0.25','0'],a:['0','0.8'],d:['0','-0.8']};
window.addEventListener('keydown',e=>{
  if(e.code==='Space'){e.preventDefault();release();return;}
  const k=e.key.toLowerCase();
  if(KEYMAP[k]){e.preventDefault();
    const fake=document.createElement('button');
    fake.dataset.l=KEYMAP[k][0];fake.dataset.a=KEYMAP[k][1];
    if(!holdTimer) hold(fake);}
});
window.addEventListener('keyup',e=>{if(KEYMAP[e.key.toLowerCase()]||e.code==='Space')release();});
window.addEventListener('blur',release);
'''

if __name__ == '__main__':
    os.makedirs(os.path.join(DASH, 'maps'), exist_ok=True)
    for name, text in FILES.items():
        with open(os.path.join(DASH, name), 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        print('  + dashboard/', name, len(text.splitlines()), 'lines')
    # 占位文件，保证 maps 目录进 zip
    with open(os.path.join(DASH, 'maps', 'README.txt'), 'w', encoding='utf-8') as f:
        f.write('运行 03_保存地图.sh 后，w12_map_*.pgm / *.yaml 与 latest.* 会出现在这里。\n')
    print('[part3] done')
