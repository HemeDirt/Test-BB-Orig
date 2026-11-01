# -*- coding: utf-8 -*-
"""B15c (№7): st['max_hand'] учитывает стартовую руку (7 карт) — до этого пик считался только
по успешным приёмам через take() и занижался на старте. Статистика не трогает лог/ГСЧ — baseline цел.

Запуск: python3 patch_b15c_maxhand.py
"""
import io, hashlib, ast

EDITS = [
 ('bb_full.py',
  """              limit_burns=0, max_hand=0)
""",
  """              limit_burns=0, max_hand=0)
    if P: st['max_hand'] = max(sum(len(l) for l in p['hand'].values()) for p in P)   # B15c: старт тоже входит в пик
"""),
]

bufs = {}
for path, old, new in EDITS:
    s = io.open(path, encoding='utf-8').read()
    assert s.count(old) == 1, f'{path}: цель не найдена однозначно ({s.count(old)})'
    bufs[path] = s.replace(old, new)

for path, s in bufs.items():
    ast.parse(s)
for path, s in bufs.items():
    io.open(path, 'w', encoding='utf-8').write(s)
    print(f'{path}: {hashlib.sha256(s.encode()).hexdigest()[:12]}')
print('B15c наложено')
