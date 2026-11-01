# -*- coding: utf-8 -*-
"""B15b (№7): уточнение семантики hand_limit — потолок ≥ len(CATS) = 7 (стартовая рука = 7 карт,
по одной в категорию; лимит 7 = режим «нулевого накопления»). Найден фаззом: при лимите 5 стартовая
рука уже выше потолка, инвариант «рука ≤ лимита» недостижим без сожжения стартовых карт (не канон).

Правки:
  1. bb_full.py — комментарий ручки + гард ValueError на hand_limit < len(CATS);
  2. fuzz_test.py — случайные значения лимита из {None, 7, 9, 12} (было {None, 5, 7, 10});
  3. patch_b15_handlimit.py — докстримент (≥5 → ≥7), чтобы история не врала.

Запуск: python3 patch_b15b_handfix.py
"""
import io, hashlib, ast

EDITS = [
 ('bb_full.py',
  """             hand_limit=None)  # №7/B15: потолок закрытых карт в руке (None/0 = без лимита, канон); избыток сгорает; ≥5
""",
  """             hand_limit=None)  # №7/B15: потолок закрытых карт в руке (None/0 = без лимита, канон); избыток сгорает; ≥7=len(CATS)
"""),
 ('bb_full.py',
  """    C.update(cfg or {})
    dice = C['dice']
""",
  """    C.update(cfg or {})
    if C['hand_limit'] and C['hand_limit'] < len(CATS):   # B15b: стартовая рука = по карте в категорию, потолок ниже бессмысленен
        raise ValueError(f"hand_limit={C['hand_limit']} < {len(CATS)} категорий: стартовая рука уже выше потолка")
    dice = C['dice']
"""),
 ('fuzz_test.py',
  """               hand_limit=rng.choice([None, None, 5, 7, 10]))   # B15/№7
""",
  """               hand_limit=rng.choice([None, None, 7, 9, 12]))   # B15/№7 (≥7=len(CATS), B15b)
"""),
 ('patch_b15_handlimit.py',
  """  * hand_limit=None/0 = лимита нет (канон 268 партий не меняется); осмысленные значения ≥5 (стартовая рука = 5).
""",
  """  * hand_limit=None/0 = лимита нет (канон 268 партий не меняется); осмысленные значения ≥7 = len(CATS)
    (стартовая рука = 7 карт, по одной в категорию; лимит 7 = «нулевое накопление») — см. patch_b15b_handfix.py.
"""),
]

bufs = {}
for path, old, new in EDITS:
    if path not in bufs:
        bufs[path] = io.open(path, encoding='utf-8').read()
    s = bufs[path]
    assert s.count(old) == 1, f'{path}: цель не найдена однозначно ({s.count(old)}): {old[:70]!r}'
    bufs[path] = s.replace(old, new)

for path, s in bufs.items():
    if path.endswith('.py'):
        ast.parse(s)

for path, s in bufs.items():
    io.open(path, 'w', encoding='utf-8').write(s)
    print(f'{path}: {hashlib.sha256(s.encode()).hexdigest()[:12]}')
print('B15b (hand_limit ≥ 7) наложено:', len(EDITS), 'правок')
