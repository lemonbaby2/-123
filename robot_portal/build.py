"""Build the public, self-contained robotics study portal."""
from pathlib import Path
import argparse, json, shutil, re, html
import markdown

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument('--output', type=Path, required=True)
ap.add_argument('--sim-build', type=Path, required=True)
args = ap.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
tasks = [
 ('microduck-1','MicroDuck','01','篮球上的闭环控制','物理仿真录像','datawhale_microduck/task1/Task1_学习笔记.md','datawhale_microduck/task1/basketball_gpu_contact_sheet.jpg','datawhale_microduck/task1/basketball_gpu_local.mp4'),
 ('microduck-2','MicroDuck','02','推一把，观察恢复','浏览器物理仿真','datawhale_microduck/task2/Task2_学习笔记.md','datawhale_microduck/task2/recordings/mjswan_microduck_contact_sheet.jpg','datawhale_microduck/task2/recordings/mjswan_microduck_manual_drag_demo.mp4'),
 ('hello-1','Hello-Robot','01','从底盘到七自由度机械臂','离线算法验证','hello_robot_tasks/task1/README.md','hello_robot_tasks/artifacts/task1_control_result.png',''),
 ('hello-2','Hello-Robot','02','让机器人看见空间','合成雷达建图','hello_robot_tasks/task2/README.md','hello_robot_tasks/artifacts/task2_mapping_result.png',''),
 ('hello-3','Hello-Robot','03','寻找一条可执行的路径','离线规划验证','hello_robot_tasks/task3/README.md','hello_robot_tasks/artifacts/task3_planning_result.png','hello_robot_tasks/artifacts/task3_trajectory_playback.mp4'),
 ('hello-4','Hello-Robot','04','从语言意图到动作数据','数据管线验证','hello_robot_tasks/task4/README.md','hello_robot_tasks/artifacts/task4_pipeline_dry_run.gif',''),
 ('hello-5','Hello-Robot','05','前沿模型与工程复盘','学习总结','hello_robot_tasks/task5/README.md','hello_robot_tasks/artifacts/task3_planning_result.png',''),
]
# Copy public learning artifacts only. Never include environments, auth files or logs.
for folder in ['datawhale_microduck','hello_robot_tasks']:
    for p in (ROOT/folder).rglob('*'):
        if not p.is_file() or '__pycache__' in p.parts or p.suffix in ['.log','.pt','.onnx','.pyc']: continue
        target = out/p.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,target)
pages=[]
for ident,course,num,title,status,note,cover,video in tasks:
    text=(ROOT/note).read_text(encoding='utf-8')
    rendered=markdown.markdown(text,extensions=['tables','fenced_code'])
    # Resolve relative media/downloads against each original note directory.
    def link(m):
        attr,value=m.group(1),m.group(2)
        if value.startswith(('https:','http:','#','mailto:')): return m.group(0)
        path=(Path(note).parent/value).as_posix()
        if value.endswith('.md'):
            path='https://github.com/lemonbaby2/-123/blob/hello-robot-tasks/'+path
        return f'{attr}="{html.escape(path,quote=True)}"'
    rendered=re.sub(r'(src|href)="([^"]+)"',link,rendered)
    pages.append(dict(id=ident,course=course,num=num,title=title,status=status,html=rendered,cover=cover,video=video,search=text))
(out/'tasks.json').write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
for name in ['index.html','style.css','app.js','lab.js']:
    shutil.copy2(ROOT/'robot_portal'/name,out/name)
css=(out/'style.css').read_text(encoding='utf-8')
# Use installed system fonts when offline; all required runtime assets are local.
css=re.sub(r"@import url\([^;]+;",'',css)
(out/'style.css').write_text(css,encoding='utf-8')
sim=out/'sim'
shutil.copytree(args.sim_build,sim,dirs_exist_ok=True)
# Upstream Vite output targets /. Adapt asset and manifest paths for GitHub Pages.
prefix='/'+ '-123' +'/sim/'
for p in [sim/'index.html',*list((sim/'assets').glob('*.js')),*list((sim/'assets').glob('*.css'))]:
    text=p.read_text(encoding='utf-8')
    text=text.replace('/assets/',prefix+'assets/').replace('TZ(`/`)','TZ(`'+prefix+'`)')
    if p.name=='index.html':
        text=text.replace('<head>','<head><script src="isolation.js"></script>')
    p.write_text(text,encoding='utf-8')
for name in ['isolation.js','isolation-sw.js']:
    shutil.copy2(ROOT/'robot_portal'/name,sim/name)
(out/'.nojekyll').touch()
assert all((out/t['cover']).exists() and (not t['video'] or (out/t['video']).exists()) for t in pages)
print(json.dumps({'tasks':len(pages),'files':sum(p.is_file() for p in out.rglob('*')),'output':str(out)},ensure_ascii=False))
