# -*- coding: utf-8 -*-
"""B14 (часть 2): новый шаблон say() из гарда слепого убийства заводится в парсер/вьюер/покрытие.

Строка ядра: «🙈 слепое убийство: живых нет, цель не выбирается» → тип события blind_empty.
Без этого coverage_test.py справедливо ругается на нераспознанный шаблон (протокол: 64→65 шаблонов).

Запуск: python3 patch_b14_events.py
"""
import io, hashlib

EDITS = [
 # 1. bb_events.py — паттерн рядом со «слепым убийством»
 ('bb_events.py',
  """ (r'^\\s*🙈 слепое убийство: цель случайна → P(\\d+)', 'blind_kill', lambda m: dict(seat=int(m[1]))),
""",
  """ (r'^\\s*🙈 слепое убийство: цель случайна → P(\\d+)', 'blind_kill', lambda m: dict(seat=int(m[1]))),
 (r'^\\s*🙈 слепое убийство: живых нет', 'blind_empty', lambda m: dict()),   # B14: стол вымер во время хода
"""),
 # 2. bb_html.py — каталог рендера ленты
 ('bb_html.py',
  """ blind_kill:{i:'🙈',l:'слепое убийство',g:'условия',c:'dth',r:e=>'слепое убийство: цель случайна → '+one(e.seat)},
""",
  """ blind_kill:{i:'🙈',l:'слепое убийство',g:'условия',c:'dth',r:e=>'слепое убийство: цель случайна → '+one(e.seat)},
 blind_empty:{i:'🙈',l:'слепое убийство в пустоту',g:'условия',r:e=>'слепое убийство: живых нет, цель не выбирается'},
"""),
 # 3. coverage_test.py — ожидаемый тип
 ('coverage_test.py',
  """ '🙈 слепое убийство: цель случайна → P#': 'blind_kill',
""",
  """ '🙈 слепое убийство: цель случайна → P#': 'blind_kill',
 '🙈 слепое убийство: живых нет, цель не выбирается': 'blind_empty',
"""),
 # 4. coverage_test.py — образец строки (ветка редкая, в выборке партий не встречается)
 ('coverage_test.py',
  """SAMPLES = {
""",
  """SAMPLES = {
 '🙈 слепое убийство: живых нет, цель не выбирается': '  🙈 слепое убийство: живых нет, цель не выбирается',
"""),
]

bufs = {}
for path, old, new in EDITS:
    if path not in bufs:
        bufs[path] = io.open(path, encoding='utf-8').read()
    s = bufs[path]
    assert s.count(old) == 1, f'{path}: цель не найдена однозначно ({s.count(old)}): {old[:60]!r}'
    bufs[path] = s.replace(old, new)

for path, s in bufs.items():
    io.open(path, 'w', encoding='utf-8').write(s)
    print(f'{path}: {hashlib.sha256(s.encode()).hexdigest()[:12]}')
print('B14 (события) наложено')
