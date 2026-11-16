/* W12 课堂看板：纯原生 Canvas，无第三方库 */
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
