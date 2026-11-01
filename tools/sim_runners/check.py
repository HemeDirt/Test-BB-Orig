import json, sys, re, unicodedata
from collections import Counter
def norm(s):
    s=s.lower().strip()
    s=re.sub(r'[^а-яёa-z0-9 ]',' ',s)
    return re.sub(r'\s+',' ',s).strip()
deck=json.load(open('src/final_v5.json'))
existing=set()
for k,v in deck.items():
    for x in v: existing.add(norm(x))
files=sys.argv[1:]
for f in files:
    lines=[l.strip() for l in open(f,encoding='utf-8') if l.strip()]
    c=Counter(lines)
    dups=[k for k,n in c.items() if n>1]
    print(f'== {f}: строк={len(lines)} уникальных={len(set(lines))}')
    # шаблонные повторы по первым двум словам
    pref=Counter(' '.join(norm(l).split()[:2]) for l in lines)
    hot=[(p,n) for p,n in pref.most_common(8) if n>1]
    if hot: print('   повтор префиксов:', hot)
    # длина
    L=[len(l.split()) for l in lines]
    print(f'   слов: min={min(L)} max={max(L)} среднее={sum(L)/len(L):.1f}')
    long_ones=[l for l in lines if len(l.split())>10]
    if long_ones: print('   длиннее 10 слов:', len(long_ones))
    clash=[l for l in lines if norm(l) in existing]
    if clash: print('   ТОЧНЫЕ дубли с колодой v3:', clash)
    if dups: print('   дубли внутри файла:', dups)
