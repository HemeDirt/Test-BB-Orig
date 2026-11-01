# -*- coding: utf-8 -*-
"""B17 (вердикт пользователя по открытому вопросу №25-п.9): «мёртвый не играет за живого».

Вердикт дословно: «если игрок умер, он не имеет право как-либо играть за живого; он становится
мёртвым, а уже будучи мёртвым сам играет от себя, используя жетоны и карты».
Реализация: смерть (или лимбо) ПОСЕРЕДИНЕ собственного хода немедленно обрывает живой ход:
  * цикл РПДИ прерывается (оставшиеся заявки сгорают);
  * вторая личность (демон) не кидает инициативу и не действует;
  * обмен не объявляется и реактивные обменки не взводятся.
Призрак далее играет по канону: со СЛЕДУЮЩЕГО цикла ghost_phase даёт +1 жетон и тень (свои,
личные — B12), тени тратятся в свой момент. Экономика призраков не меняется.

Новая строка лога «⛔ P#: смерть посреди хода — оставшиеся РПД и обмен сгорают» = 68-й шаблон:
парсер (тип midturn_stop), вьюер, покрытие (+живой кейс), статистика st['midturn_stops'].
ВНИМАНИЕ: правка меняет канон партий, где смерть наступала посреди хода (268/600 в старом каноне);
baseline 777/plane/N8 мог измениться — после патча переснять хэш и регрессии в run_tests.sh.

Запуск: python3 patch_b17_deadstop.py
"""
import io, hashlib

EDITS = [
 # ============ bb_full.py ============
 ('bb_full.py',
  """              limit_burns=0, max_hand=0, draft_takes=0, draft_pool_peak=0, draft_left=0)
""",
  """              limit_burns=0, max_hand=0, draft_takes=0, draft_pool_peak=0, draft_left=0, midturn_stops=0)
"""),
 ('bb_full.py',
  """        if rpds: rpds_phase(p)
        while rpdi > 0:
""",
  """        if rpds: rpds_phase(p)
        while rpdi > 0 and p['alive'] and not p['limbo']:   # B17: смерть/лимбо обрывают живой ход
"""),
 ('bb_full.py',
  """            rpdi -= 1
        p['demon_act'] = False
        if p.get('demon'):
""",
  """            rpdi -= 1
        if rpdi > 0 and (not p['alive'] or p['limbo']):   # B17: ход оборван смертью — заявки и обмен сгорают
            st['midturn_stops'] += 1
            say(f'  ⛔ P{p["seat"]}: смерть посреди хода — оставшиеся РПД и обмен сгорают')
        p['demon_act'] = False
        if p.get('demon') and p['alive'] and not p['limbo']:   # B17: мёртвый носитель не кидает инициативу
"""),
 ('bb_full.py',
  """        ex = p['exch']
        if ex and not p['used_rpd']:
""",
  """        ex = p['exch']
        if ex and not p['used_rpd'] and p['alive'] and not p['limbo']:   # B17: мёртвый не объявляет обмен
"""),
 ('bb_full.py',
  """        elif ex in ('ОТРАТ', 'ПУСТО', 'СПАС') and p['pers']['arch'] != 'suicider':
""",
  """        elif ex in ('ОТРАТ', 'ПУСТО', 'СПАС') and p['alive'] and not p['limbo'] and p['pers']['arch'] != 'suicider':   # B17: и реактивные не взводит
"""),
 # ============ bb_events.py: 68-й шаблон ============
 ('bb_events.py',
  """  parse_log(lines)     → список событий ПОЛНОГО каталога (67 шаблонов say() ядра B16),
""",
  """  parse_log(lines)     → список событий ПОЛНОГО каталога (68 шаблонов say() ядра B17),
"""),
 ('bb_events.py',
  """ (r'^\\s*🃏 драфт: P(\\d+) берёт из пула \\[([^\\]]+)\\] «(.*)»', 'draft_take',
  lambda m: dict(seat=int(m[1]), cat=m[2], card=m[3])),   # B16/№9: РПДС «add» забрал карту из общего пула
""",
  """ (r'^\\s*🃏 драфт: P(\\d+) берёт из пула \\[([^\\]]+)\\] «(.*)»', 'draft_take',
  lambda m: dict(seat=int(m[1]), cat=m[2], card=m[3])),   # B16/№9: РПДС «add» забрал карту из общего пула
 (r'^\\s*⛔ P(\\d+): смерть посреди хода', 'midturn_stop',
  lambda m: dict(seat=int(m[1]))),   # B17: живой ход оборван смертью/лимбо
"""),
 # ============ bb_html.py: рендер события ============
 ('bb_html.py',
  """ draft_take:{i:'🃏',l:'драфт из пула',g:'карты',c:'card',r:e=>one(e.seat)+'забирает из пула <b>['+esc(e.cat)+']</b> «'+esc(e.card)+'» (РПДС-драфт)'},
""",
  """ draft_take:{i:'🃏',l:'драфт из пула',g:'карты',c:'card',r:e=>one(e.seat)+'забирает из пула <b>['+esc(e.cat)+']</b> «'+esc(e.card)+'» (РПДС-драфт)'},
 midturn_stop:{i:'⛔',l:'ход оборван смертью',g:'смерть',c:'dth',r:e=>one(e.seat)+'смерть посреди хода — оставшиеся РПД и обмен сгорают (B17)'},
"""),
 # ============ coverage_test.py: EXPECT + SAMPLES + живой кейс ============
 ('coverage_test.py',
  """ '🃏 драфт: P# берёт из пула [#] «#»': 'draft_take',
""",
  """ '🃏 драфт: P# берёт из пула [#] «#»': 'draft_take',
 '⛔ P#: смерть посреди хода — оставшиеся РПД и обмен сгорают': 'midturn_stop',
"""),
 ('coverage_test.py',
  """ '🃏 драфт: P# берёт из пула [#] «#»': '  🃏 драфт: P4 берёт из пула [разум] «Спокойствие»',
""",
  """ '🃏 драфт: P# берёт из пула [#] «#»': '  🃏 драфт: P4 берёт из пула [разум] «Спокойствие»',
 '⛔ P#: смерть посреди хода — оставшиеся РПД и обмен сгорают': '  ⛔ P2: смерть посреди хода — оставшиеся РПД и обмен сгорают',
"""),
]

bufs = {}
for path, old, new in EDITS:
    if path not in bufs:
        bufs[path] = io.open(path, encoding='utf-8').read()
    s = bufs[path]
    assert s.count(old) == 1, f'{path}: цель не найдена однозначно ({s.count(old)}): {old[:70]!r}'
    bufs[path] = s.replace(old, new)

import ast
for path, s in bufs.items():
    if path.endswith('.py'):
        ast.parse(s)

for path, s in bufs.items():
    io.open(path, 'w', encoding='utf-8').write(s)
    print(f'{path}: {hashlib.sha256(s.encode()).hexdigest()[:12]}')
print('B17 (dead-stop, вердикт «мёртвый не играет за живого») наложено:', len(EDITS), 'правок')
