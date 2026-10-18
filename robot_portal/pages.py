"""Manage only the requested repository's Pages deployment; never print credentials."""
import argparse, json, subprocess, requests
p=argparse.ArgumentParser();p.add_argument('action',choices=['enable','status']);a=p.parse_args()
r=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,check=True)
creds=dict(line.split('=',1) for line in r.stdout.splitlines() if '=' in line)
s=requests.Session();s.auth=(creds['username'],creds['password']);s.headers['Accept']='application/vnd.github+json'
url='https://api.github.com/repos/lemonbaby2/-123/pages'
if a.action=='enable':
    current=s.get(url,timeout=30)
    if current.status_code==404:
        result=s.post(url,json={'source':{'branch':'gh-pages','path':'/'},'build_type':'legacy'},timeout=30)
        print('create',result.status_code)
        if result.status_code not in (201,409): raise RuntimeError(result.text)
    elif current.status_code==200:
        source=current.json().get('source',{})
        if source.get('branch')!='gh-pages': raise RuntimeError('Existing Pages uses another branch; preserve deployment')
    else: raise RuntimeError(current.text)
result=s.get(url,timeout=30)
print(json.dumps({k:result.json().get(k) for k in ['html_url','status','source','build_type','message']},ensure_ascii=False))
build=s.get(url+'/builds/latest',timeout=30)
print('build',json.dumps({k:build.json().get(k) for k in ['status','error','commit','message']},ensure_ascii=False))
