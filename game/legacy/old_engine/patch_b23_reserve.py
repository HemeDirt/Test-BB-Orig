# -*- coding: utf-8 -*-
"""B23 / меню №13: ПЛАНИРОВАНИЕ РЕЗЕРВА (HOUSE-флаги, default OFF).

Мера из меню: «бот с реактивной обменкой сознательно оставляет РПД нетронутым чаще;
ценность сэкономленного действия».

Находка разбора канона (до всяких флагов): гейт «обмен активируется только если игрок
не потратил РПД» в коде относится ЛИШЬ к ветке ОБМЕН_КАРТА/ОБМЕН_РПД/ОБМЕН_СПЕЦ —
ветка взвода реактивных карт (ОТРАТ/ПУСТО/СПАС) `used_rpd` не проверяет. Поэтому в каноне
реакция взводится почти всегда (≈95% ходов с реактивной картой), а бережно относиться
к РПД боту незачем: «экономия действия» ничего не добавляет. Печатный текст карт при этом
говорит именно про «неиспользованное РП-действие».

Флаги (оба default OFF, канон бит-совпадает):
  reserve       — бот бережёт РПД: с реактивной картой на руке заявка РПДС пропускается
                  (строка ленты 🧊, событие 'reserve', 71-й шаблон), а вес skip в РПД-действиях
                  умножается на 1 + reserve_value;
  reserve_gate  — правило буквально: РПД потрачены → реактивная карта НЕ взводится
                  (счётчик reserve_gate_blocked); без reserve бот при этом просто теряет реакцию.

Ценность резерва (структурная оценка, коэффициенты НЕ тюнились — меню №10):
  reserve_value(p) = RV[карта] × угроза × 0.9,
  RV = 1.0 (ОТРАТ: гасит урон и возвращает атакующему) / 0.7 (ПУСТО: гасит) / 0.0
       (СПАС: флаг save_ally в ядре не читается нигде — карта-декорация, вторая находка B23);
  угроза = (0.35 + 0.5 × средняя агрессия живых противников) × (живых − 1)/N.

Гроссбух ведётся ВСЕГДА (dict/int-операции, ГСЧ не трогает → OFF бит-совпадает):
  reserve_turns    — ходов с реактивной картой (возможность спланировать);
  reserve_decision — из них таких, где заявка РПДС реально состоялась бы;
  reserve_hold     — ON: заявок, от которых отказались ради резерва (+ reserve_holders по местам);
  reserve_spend    — реактивных ходов, где РПД всё же потрачены;
  reserve_acts     — решений choose() под множителем skip (только ON);
  reserve_armed / reserve_arm_kinds — взводов карты и их состав;
  reserve_saved / reserve_back — ОР, сэкономленные держателю / возвращённые атакующему;
  reserve_wasted   — реактивных карт, сгоревших при перевыдаче обмена;
  reserve_lost     — взведённых карт, сгоревших при обрыве хода (B17);
  or_dealt         — сколько ОР вообще роздано (знаменатель «ценности защиты»).

Правки: bb_full.py (флаги, st, RV/reserve_value, choose, turn, конец хода, ветки взвода,
wound, перевыдача обмена, обрыв хода), bb_events.py (PAT 'reserve' + счётчик шаблонов),
bb_html.py (карта типа), coverage_test.py (EXPECT+SAMPLES+живой кейс+докстринг),
bb.py (CFG_KEYS+BOOL_KEYS), fuzz_test.py (переключатель), integrity_audit.py (3 конфига),
run_tests.sh (шаг 6i), test_effects.py (2 свидетеля + 4 теста).
Жёсткий вариант планирования (reserve_strict) дописывает patch_b23b_reservegate.py.

Протокол: точные якоря, assert count==1, ast.parse до записи, запись в конце.
"""
import ast, sys

EDITS = []  # (path, old, new)

def add(path, old, new):
    EDITS.append((path, old, new))

add('bb_full.py',
    '             tilt=False)       # №12/B22: тильт — собственный откат/крит-провал сдвигает агрессию на цикл по темпераменту (HOUSE, default off)',
    '             tilt=False,       # №12/B22: тильт — собственный откат/крит-провал сдвигает агрессию на цикл по темпераменту (HOUSE, default off)\n             reserve=False,    # №13/B23: планирование резерва — реактивная карта обмена важнее заявки РПДС (HOUSE, default off)\n             reserve_gate=False)  # №13/B23b: гейт «РПД не тратились» распространяется и на реактивные карты обмена (HOUSE, default off)')

add('bb_full.py',
    '              limit_burns=0, max_hand=0, draft_takes=0, draft_pool_peak=0, draft_left=0, midturn_stops=0)',
    '              limit_burns=0, max_hand=0, draft_takes=0, draft_pool_peak=0, draft_left=0, midturn_stops=0,\n              reserve_turns=0, reserve_hold=0, reserve_spend=0, reserve_acts=0, reserve_armed=0,   # №13/B23: гроссбух резерва (ведётся всегда)\n              reserve_decision=0, reserve_wasted=0, reserve_gate_blocked=0,   # №13/B23: решения; сгоревшие карты; блокировки строгим гейтом\n              reserve_forced=0, reserve_kept=0, reserve_burned=0, or_dealt=0,   # №13/B23b: жёсткие пропуски; сохранённые; не убережённые; ОР-давление\n              reserve_arm_kinds={}, reserve_saved=0, reserve_back=0, reserve_lost=0, reserve_holders={})')

add('bb_full.py',
    "    def choose(a, c):\n        v = a['pers']",
    '    RV = {\'ОТРАТ\': 1.0, \'ПУСТО\': 0.7, \'СПАС\': 0.0}   # №13/B23: ценность взведённой реактивной карты (СПАС в ядре не читается)\n\n    def reserve_value(p):\n        """№13/B23: ценность «сэкономленного действия» — зачем беречь РПД ради обмена.\n        Структурная оценка (коэффициенты не тюнились, меню №10): RV карты × угроза × K.\n        Угроза = (0.35 + 0.5×средняя агрессия живых противников) × (живых−1)/N — доля\n        чужих ходов, способных выбрать меня целью. Возвращает 0.0, если карты нет/она не реактивная."""\n        ex = p.get(\'exch\')\n        if ex not in RV:\n            return 0.0\n        lv = alive()\n        foes = [q for q in lv if q is not p]\n        if not foes:\n            return 0.0\n        ag = sum(q[\'pers\'][\'aggr\'] for q in foes) / len(foes)\n        threat = (.35 + .5 * ag) * (len(lv) - 1) / max(1, len(P))\n        return round(RV[ex] * threat * .9, 3)\n\n    def choose(a, c):\n        v = a[\'pers\']')

add('bb_full.py',
    "            st['tilt_acts'] += 1",
    "            st['tilt_acts'] += 1\n        if C['reserve_strict'] and a.get('exch') in RV:   # №13/B23b: жёсткое планирование — ход целиком пропускается\n            st['reserve_forced'] += 1\n            return 'skip'\n        if C['reserve'] and a.get('exch') in RV:   # №13/B23: реактивная карта на руке — РПД бережём\n            w['skip'] *= 1 + reserve_value(a)\n            st['reserve_acts'] += 1")

add('bb_full.py',
    '        if rpds: rpds_phase(p)',
    '        if p[\'exch\'] in RV:   # №13/B23: гроссбух возможности (обе руки, ГСЧ не трогает)\n            st[\'reserve_turns\'] += 1\n            if rpds:\n                st[\'reserve_decision\'] += 1   # заявка была бы — решение «тратить или беречь» реально стоит\n        if C[\'reserve\'] and rpds and p[\'exch\'] in RV:   # №13/B23: РПД бережём — обмен важнее заявки\n            rv = reserve_value(p)\n            rpds = 0\n            st[\'reserve_hold\'] += 1\n            st[\'reserve_holders\'][p[\'seat\']] = st[\'reserve_holders\'].get(p[\'seat\'], 0) + 1\n            say(f\'  🧊 P{p["seat"]}: резерв — РПД не тратятся ради обмена «{p["exch"]}» (угроза {rv:.2f})\')\n        if rpds: rpds_phase(p)')

add('bb_full.py',
    "        ex = p['exch']",
    "        ex = p['exch']\n        if ex in RV and p['used_rpd']:   # №13/B23: реакция была на руке, но РПД потрачены\n            st['reserve_spend'] += 1")

add('bb_full.py',
    "        elif ex in ('ОТРАТ', 'ПУСТО', 'СПАС') and p['alive'] and not p['limbo'] and p['pers']['arch'] != 'suicider':   # B17: и реактивные не взводит\n            if ex == 'ОТРАТ': p['reflect'] = True",
    "        elif ex in ('ОТРАТ', 'ПУСТО', 'СПАС') and p['alive'] and not p['limbo'] and p['pers']['arch'] != 'suicider':   # B17: и реактивные не взводит\n            st['reserve_armed'] += 1; st['reserve_arm_kinds'][ex] = st['reserve_arm_kinds'].get(ex, 0) + 1   # №13/B23: взвод из обмена\n            if ex == 'ОТРАТ': p['reflect'] = True")

add('bb_full.py',
    "        for p in alive(): p['exch'] = exch.pop() if exch else None   # HOUSE: обмен каждый цикл",
    "        for p in P:   # №13/B23: учёт сгоревших реактивных карт (мёртвые/невзведённые)\n            if p['exch'] in RV and not (p['reflect'] or p['pustoe'] or p['save_ally']):\n                st['reserve_wasted'] += 1\n        for p in alive(): p['exch'] = exch.pop() if exch else None   # HOUSE: обмен каждый цикл")

add('bb_full.py',
    "            p['reflect'] = False; a = by_seat(int(src)) if str(src).isdigit() else None",
    "            p['reflect'] = False; a = by_seat(int(src)) if str(src).isdigit() else None\n            st['reserve_saved'] += amt   # №13/B23: держатель не получил ОР")

add('bb_full.py',
    '            say(f\'    ↩ P{p["seat"]}: «обрат» возвращает урон\')',
    '            say(f\'    ↩ P{p["seat"]}: «обрат» возвращает урон\')\n            st[\'reserve_back\'] += amt   # №13/B23: урон вернулся атакующему')

add('bb_full.py',
    '            p[\'pustoe\'] = False; say(f\'    🍀 P{p["seat"]}: «повезёт» гасит последствие\'); return False',
    '            p[\'pustoe\'] = False; st[\'reserve_saved\'] += amt   # №13/B23: держатель не получил ОР\n            say(f\'    🍀 P{p["seat"]}: «повезёт» гасит последствие\'); return False')

add('bb_full.py',
    "            st['midturn_stops'] += 1",
    "            st['midturn_stops'] += 1\n            st['reserve_lost'] += sum(1 for f in ('reflect', 'pustoe') if p.get(f))   # №13/B23")

add('bb_events.py',
    '  parse_log(lines)     → список событий ПОЛНОГО каталога (68 шаблонов say() ядра B17),',
    '  parse_log(lines)     → список событий ПОЛНОГО каталога (71 шаблон say() ядра B23),')

add('bb_events.py',
    '  lambda m: dict(seat=int(m[1]), dir=m[2], temper=float(m[3]), src=m[4], until=int(m[5]))),   # №12/B22',
    "  lambda m: dict(seat=int(m[1]), dir=m[2], temper=float(m[3]), src=m[4], until=int(m[5]))),   # №12/B22\n (r'^\\s*🧊 P(\\d+): резерв — РПД не тратятся ради обмена «([^»]+)» \\(угроза ([\\d.]+)\\)', 'reserve',\n  lambda m: dict(seat=int(m[1]), card=m[2], threat=float(m[3]))),   # №13/B23: планирование резерва")

add('bb_html.py',
    " tilt:{i:'↯',l:'тильт',g:'действия',c:'wou',r:e=>one(e.seat)+'тильт — '+esc(e.dir)+' (temper '+e.temper+', '+esc(e.src)+'), до ц.'+e.until},   // №12/B22",
    " tilt:{i:'↯',l:'тильт',g:'действия',c:'wou',r:e=>one(e.seat)+'тильт — '+esc(e.dir)+' (temper '+e.temper+', '+esc(e.src)+'), до ц.'+e.until},   // №12/B22\n reserve:{i:'🧊',l:'резерв РПД',g:'карты',c:'card',r:e=>one(e.seat)+'бережёт РПД ради обмена «'+esc(e.card)+'» (угроза '+e.threat+')'},   // №13/B23")

add('coverage_test.py',
    'Часть B (синтетика): все 67 шаблонов say() из bb_full.py, включая редкие ветви, которые в',
    'Часть B (синтетика): все 71 шаблон say() из bb_full.py, включая редкие ветви, которые в')

add('coverage_test.py',
    " '↯ P#: тильт # (#) до ц.#': 'tilt',   # №12/B22",
    " '↯ P#: тильт # (#) до ц.#': 'tilt',   # №12/B22\n '🧊 P#: резерв — РПД не тратятся ради обмена «#» (#)': 'reserve',   # №13/B23")

add('coverage_test.py',
    " '↯ P#: тильт # (#) до ц.#': '  ↯ P3: тильт вспышка (temper +0.42, откат) до ц.5',",
    " '↯ P#: тильт # (#) до ц.#': '  ↯ P3: тильт вспышка (temper +0.42, откат) до ц.5',\n '🧊 P#: резерв — РПД не тратятся ради обмена «#» (#)': '  🧊 P4: резерв — РПД не тратятся ради обмена «ПУСТО» (угроза 0.31)',")

add('coverage_test.py',
    "    (3, 8, 'base', dict(tilt=True)),       # №12/B22: живой кейс тильта (↯ вспышка+заморозка)",
    "    (3, 8, 'base', dict(tilt=True)),       # №12/B22: живой кейс тильта (↯ вспышка+заморозка)\n    (2, 8, 'base', dict(reserve=True)),    # №13/B23: живой кейс планирования резерва (🧊)")

add('bb.py',
    "            'random_outcome', 'ablate', 'revive_esc', 'hand_limit', 'draft', 'reputation', 'tilt']",
    "            'random_outcome', 'ablate', 'revive_esc', 'hand_limit', 'draft', 'reputation', 'tilt',\n            'reserve', 'reserve_gate', 'reserve_strict']")

add('bb.py',
    "             'or_noise', 'crit_price', 'pacifist_c1', 'random_outcome', 'revive_esc', 'draft', 'reputation', 'tilt'}",
    "             'or_noise', 'crit_price', 'pacifist_c1', 'random_outcome', 'revive_esc', 'draft', 'reputation', 'tilt',\n             'reserve', 'reserve_gate', 'reserve_strict'}")

add('fuzz_test.py',
    "               'tilt']   # B22/№12",
    "               'tilt', 'reserve']   # B22/№12, B23/№13")

add('integrity_audit.py',
    "    ('tilt ON N8',          dict(n=8, cfg=dict(tilt=True))),          # №12/B22",
    "    ('tilt ON N8',          dict(n=8, cfg=dict(tilt=True))),          # №12/B22\n    ('reserve ON N8',       dict(n=8, cfg=dict(reserve=True))),       # №13/B23\n    ('reserve+gate N12',    dict(n=12, cfg=dict(reserve=True, reserve_gate=True))),   # №13/B23b STRICT\n    ('strict reserve N8',   dict(n=8, cfg=dict(reserve=True, reserve_gate=True, reserve_strict=True))),  # №13/B23b")

add('test_effects.py',
    "    'tilt':     (12, 8,  'base',  {'tilt': True}),   # №12/B22: вспышки/заморозки в ленте",
    "    'tilt':     (12, 8,  'base',  {'tilt': True}),   # №12/B22: вспышки/заморозки в ленте\n    'reserve':  (2, 8,   'base',  {'reserve': True}),  # №13/B23: удержания РПД + взвод обмена\n    'rvgate':   (2, 8,   'base',  {'reserve': True, 'reserve_gate': True}),  # №13/B23b: строгий гейт")

add('test_effects.py',
    'def test_baseline_anchor():',
    "def test_reserve():         # №13/B23: ON — удержания в ленте, обмен взводится\n    st, P, cnt = run('reserve')\n    assert cnt['reserve'] >= 1, 'свидетель резерва не сработал'\n    assert st['reserve_hold'] >= 1 and st['reserve_armed'] >= 1, 'ON: нет ни удержания, ни взвода'\n    assert st['reserve_acts'] >= 1, 'ON: choose() не видел реактивной карты'\n\n\ndef test_reserve_off_ledger():  # №13/B23: OFF — гроссбух ведётся, строк 🧊 нет, удержаний нет\n    seed, n, sit, _ = W['reserve']\n    log = []\n    st, P = bb_full.run_game(seed, n, log=log, situation=sit, cfg={})\n    assert st['reserve_turns'] > 0, 'OFF: возможностей не видно — гроссбух мёртв'\n    assert st['reserve_hold'] == 0 and st['reserve_acts'] == 0, 'OFF: поведение просочилось'\n    assert collections.Counter(e['type'] for e in parse_log(log))['reserve'] == 0\n\n\ndef test_reserve_gate():    # №13/B23b: STRICT — потраченные РПД не дают реакции взвестись\n    seed, n, sit, _ = W['rvgate']\n    st_g, P = bb_full.run_game(seed, n, situation=sit, cfg={'reserve_gate': True})\n    st_r, P = bb_full.run_game(seed, n, situation=sit, cfg={'reserve': True, 'reserve_gate': True})\n    st_0, P = bb_full.run_game(seed, n, situation=sit, cfg={})\n    assert st_0['reserve_gate_blocked'] == 0, 'OFF: гейт просочился в канон'\n    assert st_g['reserve_gate_blocked'] >= 1, 'STRICT: ни одной блокировки — не на чём мерить'\n    assert st_g['reserve_armed'] < st_0['reserve_armed'], 'STRICT: гейт не сократил взводы'\n    assert st_g['reserve_armed'] == 0, 'STRICT: при потраченных РПД реакция обязана молчать'\n    assert st_r['reserve_hold'] >= 1, 'STRICT+резерв: удержаний нет'\n    st_s, P = bb_full.run_game(seed, n, situation=sit,\n                               cfg={'reserve': True, 'reserve_gate': True, 'reserve_strict': True})\n    assert st_s['reserve_forced'] >= 1 and st_s['reserve_kept'] >= 1, 'жёсткий режим: нет пропусков/сохранений'\n    assert st_s['reserve_armed'] >= 1, 'жёсткий режим: реакция не взводится'\n    assert st_s['reserve_burned'] + st_s['reserve_kept'] >= 1, 'жёсткий режим: гроссбух не сходится'\n\n\ndef test_reserve_bounds():  # №13/B23: инварианты гроссбуха резерва\n    for code in ('reserve', 'midturn', 'lucky'):\n        seed, n, sit, _ = W[code]\n        for arm in ({}, {'reserve': True}):\n            st, P = bb_full.run_game(seed, n, situation=sit, cfg=arm)\n            assert st['reserve_hold'] <= st['reserve_turns'], code\n            assert st['reserve_acts'] >= st['reserve_hold'], code\n            assert sum(st['reserve_holders'].values()) == st['reserve_hold'], code\n            if not arm.get('reserve'):\n                assert st['reserve_hold'] == 0 and st['reserve_acts'] == 0, code\n\n\ndef test_baseline_anchor():")

add('run_tests.sh',
    'chk $? "тильт smoke"',
    'chk $? "тильт smoke"\n\nstep "6i. №13/B23: планирование резерва (ON детерминирован и меняет игру; гроссбух ведётся и при OFF)"\npython3 - <<\'PY\'\nimport hashlib, bb_full\ndef h(seed, n, cfg):\n    log = []\n    bb_full.run_game(seed, n, log=log, cfg=cfg)\n    return hashlib.sha256(\'\\n\'.join(log).encode()).hexdigest()\non1 = h(2, 8, {\'reserve\': True}); on2 = h(2, 8, {\'reserve\': True})\nassert on1 == on2, \'reserve ON недетерминирован\'\ndiff = sum(h(s, 8, {}) != h(s, 8, {\'reserve\': True}) for s in range(1, 13))\nassert diff >= 1, \'reserve ON не изменил ни одной партии из 12\'\nlog = []\nst, P = bb_full.run_game(2, 8, log=log, cfg={\'reserve\': True})\nassert st[\'reserve_hold\'] > 0 and not any(\'РПДС\' in l and \'🧊\' in l for l in log), \'ON: удержаний нет\'\nlog = []\nst, P = bb_full.run_game(2, 8, log=log, cfg={})   # OFF: гроссбух ведётся, 🧊 в логе нет\nassert st[\'reserve_turns\'] > 0, \'OFF: нет возможностей — не на чём мерить\'\nassert not any(\'🧊\' in l for l in log), \'OFF: строки резерва просочились в канон\'\nassert st[\'reserve_hold\'] == 0 and st[\'reserve_acts\'] == 0, \'OFF: поведение просочилось\'\ng1 = h(2, 8, {\'reserve\': True, \'reserve_gate\': True}); g2 = h(2, 8, {\'reserve\': True, \'reserve_gate\': True})\nassert g1 == g2, \'reserve+gate недетерминирован\'\ndiff_gate = sum(h(s, 8, {\'reserve_gate\': True}) != h(s, 8, {}) for s in range(1, 13))\nassert diff_gate >= 1, \'гейт не изменил ни одной партии из 12 — не на чём мерить\'\nstg, Pg = bb_full.run_game(2, 8, cfg={\'reserve_gate\': True})\nassert stg[\'reserve_gate_blocked\'] >= 0\nstr2, P2 = bb_full.run_game(2, 8, cfg={\'reserve\': True, \'reserve_gate\': True})\nst0, P0 = bb_full.run_game(2, 8, cfg={})\nassert stg[\'reserve_armed\'] < st0[\'reserve_armed\'], \'STRICT: гейт не сократил число взводов\'\nassert str2[\'reserve_hold\'] >= 1, \'STRICT+резерв: удержаний нет\'\nsts, Ps = bb_full.run_game(2, 8, cfg={\'reserve\': True, \'reserve_gate\': True, \'reserve_strict\': True})\nassert sts[\'reserve_forced\'] >= 1 and sts[\'reserve_kept\'] >= 1, \'жёсткий режим: нет пропусков/сохранений\'\nassert sts[\'reserve_armed\'] >= 1, \'жёсткий режим: реакция не взводится\'\nassert h(2, 8, {\'reserve\': True, \'reserve_gate\': True, \'reserve_strict\': True}) == h(2, 8, {\'reserve\': True, \'reserve_gate\': True, \'reserve_strict\': True}), \'жёсткий режим недетерминирован\'\nprint(f\'  6i OK: ON детерминирован, расхождение {diff}/12; OFF возможности {st["reserve_turns"]}, взводов {st["reserve_armed"]}; \'\n      f\'гейт изменил {diff_gate}/12 партий (блокировки {stg["reserve_gate_blocked"]}, взводы {st0["reserve_armed"]}→{stg["reserve_armed"]}); \'\n      f\'STRICT взводов {str2["reserve_armed"]}, жёсткий: пропусков {sts["reserve_forced"]}, сохранено {sts["reserve_kept"]}, взводов {sts["reserve_armed"]}\')\nPY\nchk $? "резерв smoke"')

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
print(f'OK: B23/№13 — планирование резерва (флаг default OFF, гроссбух всегда, 🧊 = 71-й шаблон); '
      f'файлов: {len(srcs)}, правок: {applied} (пропущено уже применённых: {skipped})')
