from pathlib import Path
import re
p = Path(r'\\wsl.localhost\Ubuntu-22.04\home\lizp\microduck-task2\dist\microduck')
t = next((p/'assets').glob('index-*.js')).read_text(encoding='utf-8')
print(sorted(set(re.findall(r'''["'](/[^"'\s]{1,100})["']''',t))))
for word in ['TZ\\(', 'BASE_URL', 'new URL\\(', '`/assets/', 'basePath']:
    for m in list(re.finditer(word,t))[:5]:
        print(word, t[max(0,m.start()-140):m.end()+140])
