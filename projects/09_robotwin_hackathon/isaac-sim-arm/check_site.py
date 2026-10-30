"""校验 index.html 里所有本地资源引用是否真实存在，并检查标签配平。"""
import os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(BASE, "index.html"), encoding="utf-8").read()

refs = []
for m in re.finditer(r'(?:src|href)="([^"#][^"]*)"', html):
    u = m.group(1)
    if u.startswith(("http://", "https://", "mailto:", "data:")):
        continue
    refs.append(u.split("?")[0])

missing, present = [], []
for u in sorted(set(refs)):
    p = os.path.join(BASE, u.replace("/", os.sep))
    (present if os.path.isfile(p) else missing).append(u)

print(f"资源引用 {len(set(refs))} 个：存在 {len(present)}，缺失 {len(missing)}")
for u in present:
    p = os.path.join(BASE, u.replace("/", os.sep))
    print(f"  OK   {u:<46} {os.path.getsize(p)/1024:8.1f} KB")
for u in missing:
    print(f"  MISS {u}")

# 标签配平
for tag in ("section", "div", "figure", "dl", "video"):
    o = len(re.findall(rf"<{tag}[\s>]", html))
    c = len(re.findall(rf"</{tag}>", html))
    flag = "OK" if o == c else "MISMATCH"
    print(f"标签 <{tag}> 开{o} 闭{c}  {flag}")

# 未替换的占位符
ph = re.findall(r"\{\{[A-Z_]+\}\}", html)
print("残留占位符:", ph if ph else "无")
sys.exit(1 if missing else 0)
