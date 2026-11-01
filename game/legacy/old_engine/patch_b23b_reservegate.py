# -*- coding: utf-8 -*-
"""B23b / меню №13: STRICT-гейт и ЖЁСТКОЕ планирование резерва.

Зачем: при буквальном правиле (reserve_gate) реактивная карта почти никогда не взводится —
ход без единого потраченного РПД в каноне редкость (~5%): бот почти всегда или делает
РПДС-заявку, или РПД-действие. Значит «сознательное резервирование» обязано быть жёстким.

Флаг reserve_strict (HOUSE, default OFF, работает вместе с reserve + reserve_gate):
  с реактивной картой на руке choose() ДЕТЕРМИНИРОВАННО возвращает 'skip' (ГСЧ не трогает —
  число вызовов rng не меняется), т.е. бот сознательно пропускает ход целиком:
  ни заявки РПДС, ни РПД-действий → карта объявляется/взводится в конце хода.

Гроссбух: reserve_forced — жёстких пропусков, reserve_kept — ходов, где резерв сохранён,
reserve_burned — где не уберегли (РПД всё же потрачены); reserve_armed теперь считает и
взвод через ветку объявления обмена (при STRICT реактивная карта объявляется как обмен 🎴);
or_dealt — сколько ОР вообще роздано: без этого «ценность сэкономленного действия» не
отличить от простого падения агрессии.

Правки: bb_full.py (флаг, st, choose, конец хода, ветка объявления, wound),
fuzz_test.py (переключатель). Обвязка bb.py/integrity_audit/run_tests/test_effects —
в patch_b23_reserve.py (общие списки ключей и шаги приёмки).

Протокол: точные якоря, assert count==1, ast.parse до записи, запись в конце.
"""
import ast, sys

EDITS = []  # (path, old, new)

def add(path, old, new):
    EDITS.append((path, old, new))

add('bb_full.py',
    '             tilt=False,       # №12/B22: тильт — собственный откат/крит-провал сдвигает агрессию на цикл по темпераменту (HOUSE, default off)\n             reserve=False,    # №13/B23: планирование резерва — реактивная карта обмена важнее заявки РПДС (HOUSE, default off)\n             reserve_gate=False)  # №13/B23b: гейт «РПД не тратились» распространяется и на реактивные карты обмена (HOUSE, default off)',
    '             tilt=False,       # №12/B22: тильт — собственный откат/крит-провал сдвигает агрессию на цикл по темпераменту (HOUSE, default off)\n             reserve=False,    # №13/B23: планирование резерва — реактивная карта обмена важнее заявки РПДС (HOUSE, default off)\n             reserve_gate=False,  # №13/B23b: гейт «РПД не тратились» распространяется и на реактивные карты обмена (HOUSE, default off)\n             reserve_strict=False)  # №13/B23b: жёсткий резерв — с реактивной картой ход пропускается целиком (нужен вместе с reserve_gate)')

add('bb_full.py',
    '              reserve_decision=0, reserve_wasted=0, reserve_gate_blocked=0,   # №13/B23: решения; сгоревшие карты; блокировки строгим гейтом',
    '              reserve_decision=0, reserve_wasted=0, reserve_gate_blocked=0,   # №13/B23: решения; сгоревшие карты; блокировки строгим гейтом\n              reserve_forced=0, reserve_kept=0, reserve_burned=0, or_dealt=0,   # №13/B23b: жёсткие пропуски; сохранённые; не убережённые; ОР-давление')

add('bb_full.py',
    "        if C['reserve'] and a.get('exch') in RV:   # №13/B23: реактивная карта на руке — РПД бережём",
    "        if C['reserve_strict'] and a.get('exch') in RV:   # №13/B23b: жёсткое планирование — ход целиком пропускается\n            st['reserve_forced'] += 1\n            return 'skip'\n        if C['reserve'] and a.get('exch') in RV:   # №13/B23: реактивная карта на руке — РПД бережём")

add('bb_full.py',
    "        ex = p['exch']\n        if ex in RV and p['used_rpd']:   # №13/B23: реакция была на руке, но РПД потрачены\n            st['reserve_spend'] += 1",
    "        ex = p['exch']\n        if ex in RV and p['used_rpd']:   # №13/B23: реакция была на руке, но РПД потрачены\n            st['reserve_spend'] += 1\n            if C['reserve_strict']: st['reserve_burned'] += 1   # №13/B23b: жёсткий режим не уберёг\n        elif ex in RV and not p['used_rpd'] and C['reserve_strict']:   # №13/B23b: резерв сохранён\n            st['reserve_kept'] += 1")

add('bb_full.py',
    "        elif ex in ('ОТРАТ', 'ПУСТО', 'СПАС') and p['alive'] and not p['limbo'] and p['pers']['arch'] != 'suicider':   # B17: и реактивные не взводит\n            st['reserve_armed'] += 1; st['reserve_arm_kinds'][ex] = st['reserve_arm_kinds'].get(ex, 0) + 1   # №13/B23: взвод из обмена\n            if ex == 'ОТРАТ': p['reflect'] = True",
    "        elif ex in ('ОТРАТ', 'ПУСТО', 'СПАС') and p['alive'] and not p['limbo'] and p['pers']['arch'] != 'suicider' and not (C['reserve_gate'] and p['used_rpd']):   # B17: мёртвый не взводит; B23b: STRICT-гейт по used_rpd\n            st['reserve_armed'] += 1; st['reserve_arm_kinds'][ex] = st['reserve_arm_kinds'].get(ex, 0) + 1   # №13/B23: взвод из обмена\n            if ex == 'ОТРАТ': p['reflect'] = True")

add('bb_full.py',
    "            if ex == 'СПАС': p['save_ally'] = True\n\n    c = 1",
    "            if ex == 'СПАС': p['save_ally'] = True\n        elif ex in RV and C['reserve_gate']:   # №13/B23b: STRICT — РПД потрачены, реакция не взводится\n            st['reserve_gate_blocked'] += 1\n\n    c = 1")

add('bb_full.py',
    "            elif ex == 'ОБМЕН_СПЕЦ': p['spec_used'] = False\n            p['exch'] = None",
    "            elif ex == 'ОБМЕН_СПЕЦ': p['spec_used'] = False\n            if ex in RV and p['pers']['arch'] != 'suicider':   # №13/B23b: реактивная карта взводится и через ветку объявления\n                st['reserve_armed'] += 1; st['reserve_arm_kinds'][ex] = st['reserve_arm_kinds'].get(ex, 0) + 1\n                if ex == 'ОТРАТ': p['reflect'] = True\n                if ex == 'ПУСТО': p['pustoe'] = True\n                if ex == 'СПАС': p['save_ally'] = True\n            p['exch'] = None")

add('bb_full.py',
    '        p[\'or_\'] += amt; say(f\'    P{p["seat"]}: +{amt} ОР → {p["or_"]}\')',
    '        p[\'or_\'] += amt; st[\'or_dealt\'] += amt; say(f\'    P{p["seat"]}: +{amt} ОР → {p["or_"]}\')')

add('fuzz_test.py',
    "               'tilt', 'reserve']   # B22/№12, B23/№13",
    "               'tilt', 'reserve', 'reserve_gate', 'reserve_strict']   # B22/№12, B23/№13")

# --- проверка и запись ---
srcs = {}
applied = skipped = 0
for path, old, new in EDITS:
    if path not in srcs:
        srcs[path] = open(path, encoding='utf-8').read()
    if new in srcs[path]:        # правка уже применена (повторный запуск патча)
        skipped += 1
        continue
    cnt = srcs[path].count(old)
    if cnt != 1:
        print(f'FAIL: якорь встречается {cnt} раз (нужно 1) в {path}:\n{old[:140]}')
        sys.exit(1)
    srcs[path] = srcs[path].replace(old, new, 1)
    applied += 1

for path in srcs:
    if path.endswith('.py'):
        try:
            ast.parse(srcs[path])
        except SyntaxError as e:
            print(f'FAIL: синтаксис {path}: {e}')
            sys.exit(1)

for path, txt in srcs.items():
    open(path, 'w', encoding='utf-8').write(txt)
print(f'OK: B23b/№13 — STRICT-гейт reserve_gate и жёсткое планирование reserve_strict; '
      f'файлов: {len(srcs)}, правок: {applied} (пропущено уже применённых: {skipped})')
