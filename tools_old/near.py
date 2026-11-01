import json,sys,re
def toks(s):
    s=s.lower(); s=re.sub(r'[^а-яёa-z0-9 ]',' ',s)
    return set(re.sub(r'\s+',' ',s).strip().split())
deck=json.load(open('src/final_v5.json'))
cat=sys.argv[1].lower()
items=[x for k,v in deck.items() if cat in k.lower() for x in v]
refs=[(toks(x),x) for x in items]
print(f'эталон: {cat} = {len(items)} карт')
for f in sys.argv[2:]:
    print(f'== {f}')
    n=0
    for line in open(f,encoding='utf-8'):
        line=line.strip()
        if not line: continue
        t=toks(line)
        best=max(refs,key=lambda r: len(t&r[0])/max(1,len(t|r[0])))
        j=len(t&best[0])/max(1,len(t|best[0]))
        if j>=0.55:
            print(f'   {j:.2f}  «{line}»  ~  «{best[1]}»'); n+=1
    print(f'   близких совпадений: {n}')
