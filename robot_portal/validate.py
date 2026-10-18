"""Check publication assets without claiming browser interaction testing."""
from pathlib import Path
from urllib.parse import urlsplit,unquote
from html.parser import HTMLParser
import argparse,json,requests,concurrent.futures
p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--public-url');a=p.parse_args()
root=a.directory.resolve();fail=[]
class Links(HTMLParser):
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in ('src','href') and value:
                u=urlsplit(value)
                if u.scheme or not u.path or u.path.startswith('/'):continue
                if not (root/unquote(u.path)).resolve().exists():fail.append(value)
parser=Links();parser.feed((root/'index.html').read_text(encoding='utf-8'))
data=json.loads((root/'tasks.json').read_text(encoding='utf-8'))
for t in data:
    parser.feed(t['html'])
    assert (root/t['cover']).is_file()
    if t['video']:assert (root/t['video']).is_file()
assert len(data)==7
assert not fail, fail
print('Local: 7 notes and all referenced local media/downloads exist')
if a.public_url:
    paths=['','tasks.json','app.js','lab.js','style.css','sim/index.html','sim/manifest.json','sim/isolation-sw.js']
    paths += [t['video'] for t in data if t['video']]
    paths += ['sim/assets/'+f.name for f in (root/'sim/assets').glob('*.wasm')]
    paths += ['sim/microduck/duck/policy/walk.onnx','sim/microduck/duck/scene.mjz']
    def check(path):
        r=requests.get(a.public_url.rstrip('/')+'/'+path,timeout=45,stream=True)
        row={'path':path,'status':r.status_code,'type':r.headers.get('Content-Type')};r.close();return row
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool: rows=list(pool.map(check,paths))
    print(json.dumps(rows,ensure_ascii=False,indent=2))
    assert all(r['status']==200 for r in rows)
