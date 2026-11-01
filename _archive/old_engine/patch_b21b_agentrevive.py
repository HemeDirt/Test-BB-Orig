# -*- coding: utf-8 -*-
"""B21b: целостность — воскрешение «Тур. Агента» было БЕЗМОЛВНЫМ (аудит, канон N8/seed4).

Найдено integrity_audit.py: st['revives'] увеличивается (bb_full, ветка профессии «Тур. Агент»),
но в лог не пишется ни строки → вьюер показывает восставшего призрака без причины;
лента событий (bb_events) и маятник (B19) систематически недосчитывали этот путь
(в N12 ~35% партий имели молчаливое воскрешение). Baseline 777/plane не затронут
(в той партии воскрешений нет вовсе) — правка baseline-безопасна, как B17.

Правки:
  bb_full.py     — say-строка 🚌 в ветке «Тур. Агент»;
  bb_events.py   — PAT 'revive_agent' + LEGACY_TYPES;
  bb_html.py     — карта типа (иконка/подпись) + два кортежа учёта воскрешений;
  bb_model.py    — кортеж путей воскрешения;
  coverage_test.py — шаблон + живой кейс (4, 8, 'base', {});
  run_pendulum.py  — REVIVE_PATH['revive_agent'].

Протокол: точные якоря, assert count==1, ast.parse, запись в конце.
"""
import ast, sys

EDITS = []
def add(path, old, new): EDITS.append((path, old, new))

# 1) bb_full: say-строка
add('bb_full.py',
    "                g = gs[0]; g['alive'] = True; g['or_'] = 0; g['back2'] = 2; p['prof_used'] = True; st['revives'] += 1\n",
    "                g = gs[0]; g['alive'] = True; g['or_'] = 0; g['back2'] = 2; p['prof_used'] = True; st['revives'] += 1\n"
    "                say(f'  🚌 Тур. Агент P{p[\"seat\"]}: путёвка на жизнь — P{g[\"seat\"]} возвращается')   # B21b: было безмолвно\n")

# 2) bb_events: PAT + LEGACY
add('bb_events.py',
    " (r'^\\s*☸ Буддист P(\\d+): авто-реинкарнация', 'reincarnate', lambda m: dict(seat=int(m[1]))),",
    " (r'^\\s*🚌 Тур\\. Агент P(\\d+): путёвка на жизнь — P(\\d+) возвращается', 'revive_agent',\n"
    "  lambda m: dict(seat=int(m[1]), target=int(m[2]))),   # B21b\n"
    " (r'^\\s*☸ Буддист P(\\d+): авто-реинкарнация', 'reincarnate', lambda m: dict(seat=int(m[1]))),")
add('bb_events.py',
    "                'doll_made', 'film', 'betrayal', 'revive_tokens'}",
    "                'doll_made', 'film', 'betrayal', 'revive_tokens', 'revive_agent'}")

# 3) bb_html: карта + кортежи
add('bb_html.py',
    " revive_necro:{i:'✝',l:'воскрешение Некромантом',g:'воскрешение',c:'rev',r:e=>'Некромант '+one(e.seat)+'возвращает '+one(e.target)},",
    " revive_necro:{i:'✝',l:'воскрешение Некромантом',g:'воскрешение',c:'rev',r:e=>'Некромант '+one(e.seat)+'возвращает '+one(e.target)},\n"
    " revive_agent:{i:'🚌',l:'возврат Тур. Агентом',g:'воскрешение',c:'rev',r:e=>'Тур. Агент '+one(e.seat)+'оформил путёвку — '+one(e.target)+' возвращается'},")
add('bb_html.py',
    "                  revives=sum(1 for e in ev if e['type'] in ('revive_tokens', 'revive_necro', 'reincarnate')),",
    "                  revives=sum(1 for e in ev if e['type'] in ('revive_tokens', 'revive_necro', 'revive_agent', 'reincarnate')),")
add('bb_html.py',
    "        elif e['type'] in ('revive_tokens', 'revive_necro', 'reincarnate'):",
    "        elif e['type'] in ('revive_tokens', 'revive_necro', 'revive_agent', 'reincarnate'):")

# 4) bb_model: кортеж путей
add('bb_model.py',
    "                        ('revive_tokens', 'revive_necro', 'reincarnate')),",
    "                        ('revive_tokens', 'revive_necro', 'revive_agent', 'reincarnate')),")

# 5) coverage_test: шаблон + живой кейс
add('coverage_test.py',
    " '⛔ P#: смерть посреди хода — оставшиеся РПД и обмен сгорают': 'midturn_stop',",
    " '⛔ P#: смерть посреди хода — оставшиеся РПД и обмен сгорают': 'midturn_stop',\n"
    " '🚌 Тур. Агент P#: путёвка на жизнь — P# возвращается': 'revive_agent',")
add('coverage_test.py',
    "    (7, 8, 'base', {}),                     # B17: живой кейс обрыва хода смертью (⛔)",
    "    (7, 8, 'base', {}),                     # B17: живой кейс обрыва хода смертью (⛔)\n"
    "    (4, 8, 'base', {}),                     # B21b: живой кейс возврата Тур. Агента (🚌)")

# 6) run_pendulum: путь воскрешения
add('run_pendulum.py',
    "REVIVE_PATH = {'revive_tokens': 'жетоны призрака', 'revive_necro': 'профессор', 'reincarnate': 'перерождение'}",
    "REVIVE_PATH = {'revive_tokens': 'жетоны призрака', 'revive_necro': 'профессор', 'reincarnate': 'перерождение',\n"
    "               'revive_agent': 'тур. агент'}   # B21b: путь был безмолвным — маятник B19 чуть недосчитывал воскрешения")

# --- проверка и запись ---
srcs = {}
for path, old, new in EDITS:
    if path not in srcs:
        srcs[path] = open(path, encoding='utf-8').read()
    cnt = srcs[path].count(old)
    if cnt != 1:
        print(f'FAIL: якорь встречается {cnt} раз (нужно 1) в {path}:\n{old[:120]}')
        sys.exit(1)
    srcs[path] = srcs[path].replace(old, new, 1)

for path in srcs:
    if path.endswith('.py'):
        try:
            ast.parse(srcs[path])
        except SyntaxError as e:
            print(f'FAIL: синтаксис {path}: {e}')
            sys.exit(1)

for path, txt in srcs.items():
    open(path, 'w', encoding='utf-8').write(txt)
print('OK: B21b — 🚌 Тур. Агент больше не безмолвствует (6 файлов, синтаксис проверен)')
