# -*- coding: utf-8 -*-
"""\u041a\u043e\u043d\u0442\u0440\u043e\u043b\u044c\u043d\u0430\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0447\u0438\u0441\u0442\u043e\u0442\u044b \u0432\u0441\u0435\u0433\u043e \u043f\u0440\u043e\u0435\u043a\u0442\u0430. \u0417\u0430\u043f\u0443\u0441\u043a: python3 src/check_clean.py"""
import json, os, re, sys, zipfile
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import censor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
TABOO = "".join(chr(c) for c in (0x0431, 0x0443, 0x043D, 0x043A, 0x0435, 0x0440))
SKIP_DIRS = {'.git', '__pycache__', '.venv', 'node_modules', 'uploads'}
ok_all = True

def bad(text):
    return [l for l in text.split('\n') if censor.dirty(l)]

# 1) \u043a\u043e\u043b\u043e\u0434\u0430
d = json.load(open('src/final_v5.json', encoding='utf-8'))
total = sum(len(v) for v in d.values())
dirty = [c for v in d.values() for c in v if censor.dirty(c)]
dups = {k: [c for c, n in Counter(v).items() if n > 1] for k, v in d.items()}
dups = {k: v for k, v in dups.items() if v}
print(f'[\u041a\u041e\u041b\u041e\u0414\u0410] \u043a\u0430\u0440\u0442: {total}  \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0439: {len(d)}')
print('   ' + 'OK  ' if not dirty else '   FAIL', f'\u043d\u0435\u0436\u0435\u043b\u0430\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u043a\u043e\u043d\u0442\u0435\u043d\u0442: {len(dirty)}')
print('   ' + 'OK  ' if not dups else '   FAIL', f'\u0434\u0443\u0431\u043b\u0438 \u0432\u043d\u0443\u0442\u0440\u0438 \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0439: {sum(len(v) for v in dups.values())}')
ok_all &= not dirty and not dups
for k, v in d.items():
    print(f'      {k:<36}{len(v):>5}')

# 2) \u0432\u0441\u0435 \u043e\u0441\u0442\u0430\u043b\u044c\u043d\u044b\u0435 \u0444\u0430\u0439\u043b\u044b \u043f\u0440\u043e\u0435\u043a\u0442\u0430
print('\n[\u0424\u0410\u0419\u041b\u042b]')
n_files = n_bad = n_taboo = 0
for root, dirs, files in os.walk('.'):
    dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
    for f in sorted(files):
        p = os.path.join(root, f)
        try:
            if f.endswith(('.xlsx', '.docx')):
                z = zipfile.ZipFile(p)
                t = ''.join(z.read(n).decode('utf8', 'ignore') for n in z.namelist() if n.endswith('.xml'))
                t = re.sub(r'<[^>]+>', ' ', t)
            elif f.endswith(('.md', '.txt', '.csv', '.json', '.py')):
                t = open(p, encoding='utf-8', errors='ignore').read()
            else:
                continue
        except Exception:
            continue
        n_files += 1
        b = bad(t); tb = t.lower().count(TABOO)
        if b or tb:
            n_bad += len(b); n_taboo += tb
            print(f'   FAIL {p}: \u043d\u0435\u0436\u0435\u043b\u0430\u0442\u0435\u043b\u044c\u043d\u043e\u0433\u043e \u043a\u043e\u043d\u0442\u0435\u043d\u0442\u0430 \u0441\u0442\u0440\u043e\u043a: {len(b)}, \u0441\u043b\u043e\u0432\u043e-\u0442\u0430\u0431\u0443: {tb}')
ok_all &= (n_bad == 0 and n_taboo == 0)
print(f'   \u043f\u0440\u043e\u0432\u0435\u0440\u0435\u043d\u043e \u0444\u0430\u0439\u043b\u043e\u0432: {n_files}  (\u043f\u0430\u043f\u043a\u0430 uploads/ \u2014 \u0438\u0441\u0445\u043e\u0434\u043d\u0438\u043a\u0438 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f \u2014 \u043d\u0435 \u043f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u0442\u0441\u044f)')
print('\n' + ('\u2705 \u0412\u0421\u0401 \u0427\u0418\u0421\u0422\u041e' if ok_all else '\u274c \u0415\u0421\u0422\u042c \u0417\u0410\u041c\u0415\u0427\u0410\u041d\u0418\u042f'))
sys.exit(0 if ok_all else 1)
