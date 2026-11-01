# -*- coding: utf-8 -*-
"""B22 / меню №12: ТИЛЬТ ботов (HOUSE-флаг, default OFF).

Суть (меню №12, вердикт «можно»): после СОБСТВЕННОГО отката/крит-провала игрок
сдвигает агрессию на один цикл — вверх или вниз по темпераменту.
  temper = aggr + blood − detach (из pers, детерминированно):
    ≥ +0.25 — «горячий»: вспышка  → kill ×1.35, wound ×1.25, mass ×1.2, skip ×0.7;
    ≤ −0.25 — «холодный»: заморозка → kill ×0.75, wound ×0.8, mass ×0.8, skip ×1.3, heal ×1.15;
    между — без сдвига (tilt_dir=0, только учёт).
  Окно: остаток текущего цикла + следующий (tilt_until = цикл_триггера + 1).
Триггеры (только собственные провальные исходы):
  «откат»      — SELF-полоса таблицы А (W1_SELF/W2_SELF/DEATH_SELF) при атаке;
  «крит-провал» — FAIL любой своей проверки Б/В (кража, унижение, лечение, мародёрка, РПДС);
  «масс-провал» — провал массового ранения / масс-кражи.
НЕ триггеры (осознанно): урон от карт/теней/Жатвы/давления (не свой провал), цена крита
(crit_price — успех с ценой), отражение Стекольщиком (внешний эффект), чучела (не действуют).

Гроссбух ведётся ВСЕГДА (dict/int-операции, ГСЧ не трогает → канон бит-совпадает):
  st['tilt_trig'/'tilt_hot'/'tilt_cold'/'tilt_mid'] — триггеры по направлениям;
  st['tilt_chain_attack'] — «месть»: своя атака (kill/wound/mass) в окне после триггера;
  st['tilt_chain_fail']   — полная цепочка «провал→месть→провал» (мера из меню №12);
  st['tilt_acts'] — решений choose() под тильтом (только ON).
ON дополнительно: сдвиг весов в choose() + строка ленты ↯ (событие 'tilt', 70-й шаблон).
Коэффициенты выбраны «на глаз» и НЕ тюнились (меню №10: канон-вероятности заморожены —
тильт множит веса только при включённом HOUSE-флаге, как fear/panic).

Правки: bb_full.py (флаг, st, tilt_note, 4 точки триггеров, учёт мести, блок choose),
bb_events.py (PAT 'tilt'), bb_html.py (карта типа), coverage_test.py (EXPECT+SAMPLES+кейс),
bb.py (CFG_KEYS+BOOL_KEYS), fuzz_test.py (переключатель), integrity_audit.py (конфиг),
run_tests.sh (шаг 6h), test_effects.py (свидетель + 3 теста).

Протокол: точные якоря, assert count==1, ast.parse до записи, запись в конце.
"""
import ast, sys

EDITS = []  # (path, old, new)

def add(path, old, new):
    EDITS.append((path, old, new))

BB = 'bb_full.py'

# 1) cfg-флаг
add(BB, "             reputation=False) # №11/B21: репутация ботов — публичный гроссбух мнений, bias выбора цели (HOUSE, default off)",
        "             reputation=False, # №11/B21: репутация ботов — публичный гроссбух мнений, bias выбора цели (HOUSE, default off)\n"
        "             tilt=False)       # №12/B22: тильт — собственный откат/крит-провал сдвигает агрессию на цикл по темпераменту (HOUSE, default off)")

# 2) st-счётчики (якорь — строка гроссбуха репутации)
add(BB, "              rep_harm=0, rep_enemy=0, rep_bene=0, rep_good=0,   # №11/B21: гроссбух репутации (ведётся всегда)",
        "              rep_harm=0, rep_enemy=0, rep_bene=0, rep_good=0,   # №11/B21: гроссбух репутации (ведётся всегда)\n"
        "              tilt_trig=0, tilt_hot=0, tilt_cold=0, tilt_mid=0, tilt_chain_attack=0, tilt_chain_fail=0, tilt_acts=0,   # №12/B22: гроссбух тильта (ведётся всегда)")

# 3) tilt_note — перед apply_A; там же хук SELF-полосы таблицы А
add(BB, "    def apply_A(eff, a, t):\n        if eff == 'DEATH_SELF': death(a, 'selfkill', str(a['seat']))",
"""    def tilt_note(p, src):
        \"\"\"№12/B22: собственный откат/крит-провал — триггер тильта.
        Гроссбух ведётся ВСЕГДА (dict/int-операции, ГСЧ не трогает → канон бит-совпадает);
        сдвиг весов и строка ленты — только при C['tilt'].
        temper = aggr + blood − detach: ≥ +0.25 — вспышка (агрессия↑), ≤ −0.25 — заморозка (агрессия↓),
        между — без сдвига. Окно: остаток текущего цикла + следующий. Цепочка «провал→месть→провал»:
        tilt_avenged — своя атака в окне после триггера; повторный провал в том же окне — chain_fail.\"\"\"
        if p is None or p.get('is_doll'):
            return
        v = p['pers']
        temper = round(v['aggr'] + v['blood'] - v['detach'], 2)
        d = 1 if temper >= .25 else (-1 if temper <= -.25 else 0)
        st['tilt_trig'] += 1
        st['tilt_hot' if d > 0 else ('tilt_cold' if d < 0 else 'tilt_mid')] += 1
        prev = p.get('tilt_trig_c')
        if prev is not None and st['cycle'] - prev <= 1 and p.get('tilt_avenged'):
            st['tilt_chain_fail'] += 1
        p['tilt_trig_c'] = st['cycle']; p['tilt_avenged'] = False
        p['tilt_dir'] = d; p['tilt_until'] = st['cycle'] + 1
        if C['tilt'] and d and p['alive'] and not p['limbo']:
            word = 'вспышка' if d > 0 else 'заморозка'
            say(f'  ↯ P{p["seat"]}: тильт {word} (temper {temper:+.2f}, {src}) до ц.{p["tilt_until"]}')

    def apply_A(eff, a, t):
        if eff in ('DEATH_SELF', 'W1_SELF', 'W2_SELF'): tilt_note(a, 'откат')   # №12/B22
        if eff == 'DEATH_SELF': death(a, 'selfkill', str(a['seat']))""")

# 4) bv: FAIL — крит-провал (кража/унижение/лечение/мародёрка/РПДС)
add(BB, "        say(f'    d20={r} [{which}] → {res}')\n        return res",
        "        say(f'    d20={r} [{which}] → {res}')\n"
        "        if res == 'FAIL': tilt_note(a, 'крит-провал')   # №12/B22\n"
        "        return res")

# 5) act: учёт «мести» — своя атака в окне после триггера
add(BB, "        if t is not None and not reflected and kind in ('wound', 'kill', 'steal', 'humiliate'):\n"
        "            rep_note(a, t, -1.5 if kind == 'kill' else (-0.7 if kind == 'wound' else -0.4),   # №11/B21\n"
        "                     -1.5 if kind == 'kill' else (-0.7 if kind == 'wound' else -0.6))",
        "        if t is not None and not reflected and kind in ('wound', 'kill', 'steal', 'humiliate'):\n"
        "            rep_note(a, t, -1.5 if kind == 'kill' else (-0.7 if kind == 'wound' else -0.4),   # №11/B21\n"
        "                     -1.5 if kind == 'kill' else (-0.7 if kind == 'wound' else -0.6))\n"
        "        if (not reflected) and kind in ('kill', 'wound', 'mass'):   # №12/B22: «месть» в цепочке провал→месть→провал\n"
        "            tc = a.get('tilt_trig_c')\n"
        "            if tc is not None and st['cycle'] - tc <= 1 and not a.get('tilt_avenged'):\n"
        "                st['tilt_chain_attack'] += 1; a['tilt_avenged'] = True")

# 6) mass: провал — самомасс-урон, это откат массовой атаки
add(BB, "            else: wound(a, 2, 'self')",
        "            else: tilt_note(a, 'масс-провал'); wound(a, 2, 'self')   # №12/B22")

# 7) mass_steal: провал — отдача своих карт
add(BB, "            else:\n                cc = closed(a)\n                give = cc[:len(ts)]",
        "            else:\n                tilt_note(a, 'масс-провал')   # №12/B22\n"
        "                cc = closed(a)\n                give = cc[:len(ts)]")

# 8) choose(): сдвиг весов под тильтом (только ON)
add(BB, "        if st['panic'] > 0:\n            w['kill'] *= .8; w['heal'] *= 1.2; w['skip'] *= 1.1",
        "        if st['panic'] > 0:\n            w['kill'] *= .8; w['heal'] *= 1.2; w['skip'] *= 1.1\n"
        "        if C['tilt'] and a.get('tilt_dir') and st['cycle'] <= a.get('tilt_until', -1):   # №12/B22: тильт — сдвиг агрессии на цикл\n"
        "            if a['tilt_dir'] > 0:\n"
        "                w['kill'] *= 1.35; w['wound'] *= 1.25; w['mass'] *= 1.2; w['skip'] *= .7\n"
        "            else:\n"
        "                w['kill'] *= .75; w['wound'] *= .8; w['mass'] *= .8; w['skip'] *= 1.3; w['heal'] *= 1.15\n"
        "            st['tilt_acts'] += 1")

# 9) bb_events: PAT 'tilt' (после midturn_stop — свой уникальный префикс ↯)
add('bb_events.py',
    r" (r'^\s*⛔ P(\d+): смерть посреди хода', 'midturn_stop'," "\n"
    r"  lambda m: dict(seat=int(m[1]))),   # B17: живой ход оборван смертью/лимбо",
    r" (r'^\s*⛔ P(\d+): смерть посреди хода', 'midturn_stop'," "\n"
    r"  lambda m: dict(seat=int(m[1]))),   # B17: живой ход оборван смертью/лимбо" "\n"
    r" (r'^\s*↯ P(\d+): тильт (вспышка|заморозка) \(temper ([+-][\d.]+), ([^)]+)\) до ц\.(\d+)', 'tilt'," "\n"
    r"  lambda m: dict(seat=int(m[1]), dir=m[2], temper=float(m[3]), src=m[4], until=int(m[5]))),   # №12/B22")

# 10) bb_html: карта типа (группа «действия», цвет урона — про агрессию)
add('bb_html.py',
    " for_fun:{i:'🎭',l:'действие по приколу',g:'профессии',r:e=>one(e.seat)+'действие по приколу (без нагрузки)'},",
    " for_fun:{i:'🎭',l:'действие по приколу',g:'профессии',r:e=>one(e.seat)+'действие по приколу (без нагрузки)'},\n"
    " tilt:{i:'↯',l:'тильт',g:'действия',c:'wou',r:e=>one(e.seat)+'тильт — '+esc(e.dir)+' (temper '+e.temper+', '+esc(e.src)+'), до ц.'+e.until},   // №12/B22")

# 11) coverage_test: EXPECT + SAMPLES + живой кейс
add('coverage_test.py',
    " '⛔ P#: смерть посреди хода — оставшиеся РПД и обмен сгорают': 'midturn_stop',",
    " '⛔ P#: смерть посреди хода — оставшиеся РПД и обмен сгорают': 'midturn_stop',\n"
    " '↯ P#: тильт # (#) до ц.#': 'tilt',   # №12/B22")
add('coverage_test.py',
    " '⛔ P#: смерть посреди хода — оставшиеся РПД и обмен сгорают': '  ⛔ P2: смерть посреди хода — оставшиеся РПД и обмен сгорают',",
    " '⛔ P#: смерть посреди хода — оставшиеся РПД и обмен сгорают': '  ⛔ P2: смерть посреди хода — оставшиеся РПД и обмен сгорают',\n"
    " '↯ P#: тильт # (#) до ц.#': '  ↯ P3: тильт вспышка (temper +0.42, откат) до ц.5',")
add('coverage_test.py',
    "    (4, 8, 'base', {}),                     # B21b: живой кейс возврата Тур. Агента (🚌)",
    "    (4, 8, 'base', {}),                     # B21b: живой кейс возврата Тур. Агента (🚌)\n"
    "    (12, 8, 'base', dict(tilt=True)),      # №12/B22: живой кейс тильта (↯)")

# 12) bb.py: CFG_KEYS + BOOL_KEYS (урок B21: оба списка!)
add('bb.py',
    "            'random_outcome', 'ablate', 'revive_esc', 'hand_limit', 'draft', 'reputation']",
    "            'random_outcome', 'ablate', 'revive_esc', 'hand_limit', 'draft', 'reputation', 'tilt']")
add('bb.py',
    "             'or_noise', 'crit_price', 'pacifist_c1', 'random_outcome', 'revive_esc', 'draft', 'reputation'}",
    "             'or_noise', 'crit_price', 'pacifist_c1', 'random_outcome', 'revive_esc', 'draft', 'reputation', 'tilt'}")

# 13) fuzz_test: переключатель тильта в случайные конфиги
add('fuzz_test.py',
    "               'or_noise', 'crit_price', 'pacifist_c1', 'random_outcome', 'revive_esc', 'draft']",
    "               'or_noise', 'crit_price', 'pacifist_c1', 'random_outcome', 'revive_esc', 'draft',\n"
    "               'tilt']   # B22/№12")

# 14) integrity_audit: конфигурация tilt ON
add('integrity_audit.py',
    "    ('reputation ON N8',    dict(n=8, cfg=dict(reputation=True))),",
    "    ('reputation ON N8',    dict(n=8, cfg=dict(reputation=True))),\n"
    "    ('tilt ON N8',          dict(n=8, cfg=dict(tilt=True))),          # №12/B22")

# 15) run_tests.sh: шаг 6h — тильт smoke
add('run_tests.sh',
    'chk $? "репутация smoke"\n',
    'chk $? "репутация smoke"\n'
    '\n'
    'step "6h. №12/B22: тильт (ON детерминирован и меняет игру; гроссбух ведётся и при OFF)"\n'
    "python3 - <<'PY'\n"
    'import hashlib, bb_full\n'
    'def h(seed, n, cfg):\n'
    '    log = []\n'
    '    bb_full.run_game(seed, n, log=log, cfg=cfg)\n'
    "    return hashlib.sha256('\\n'.join(log).encode()).hexdigest()\n"
    "on1 = h(12, 8, {'tilt': True}); on2 = h(12, 8, {'tilt': True})\n"
    "assert on1 == on2, 'tilt ON недетерминирован'\n"
    "diff = sum(h(s, 8, {}) != h(s, 8, {'tilt': True}) for s in range(1, 13))\n"
    "assert diff >= 1, 'tilt ON не изменил ни одной партии из 12'\n"
    'log = []\n'
    'st, P = bb_full.run_game(12, 8, log=log, cfg={})   # OFF: гроссбух ведётся, ↯ в логе нет\n'
    "assert st['tilt_trig'] > 0, 'OFF: нет триггеров — не на чем мерить'\n"
    "assert not any('↯' in l for l in log), 'OFF: строки тильта просочились в канон'\n"
    "assert st['tilt_trig'] == st['tilt_hot'] + st['tilt_cold'] + st['tilt_mid'], 'OFF: направления не сходятся'\n"
    "assert st['tilt_chain_fail'] <= st['tilt_chain_attack'] <= st['tilt_trig'], 'OFF: цепочки вне границ'\n"
    "assert st['tilt_acts'] == 0, 'OFF: tilt_acts должен быть 0'\n"
    'print(f\'  6h OK: ON детерминирован, расхождение {diff}/12; OFF гроссбух trig={st["tilt_trig"]}, месть {st["tilt_chain_attack"]}, цепочки {st["tilt_chain_fail"]}\')\n'
    'PY\n'
    'chk $? "тильт smoke"\n')

# 16) test_effects: свидетель + три теста
add('test_effects.py',
    "    'otrat':    (2,  8,  'base',  {}),\n}",
    "    'otrat':    (2,  8,  'base',  {}),\n"
    "    'tilt':     (12, 8,  'base',  {'tilt': True}),   # №12/B22: вспышки/заморозки в ленте\n}")
add('test_effects.py',
    "def test_baseline_anchor():",
    '''def test_tilt():           # №12/B22: тильт-строки в ленте (ON)
    st, P, cnt = run('tilt')
    assert cnt['tilt'] >= 1, 'свидетель тильта не сработал'
    assert st['tilt_acts'] >= 1, 'ON: ни одного решения под тильтом'


def test_tilt_off_ledger():  # №12/B22: OFF — гроссбух ведётся, строк ↯ нет, сдвигов нет
    seed, n, sit, _ = W['tilt']
    log = []
    st, P = bb_full.run_game(seed, n, log=log, situation=sit, cfg={})
    assert st['tilt_trig'] > 0, 'OFF: триггеров нет — гроссбух мёртв'
    assert st['tilt_acts'] == 0, 'OFF: сдвиги весов просочились'
    assert not any('↯' in l for l in log), 'OFF: строки тильта в каноне'
    assert collections.Counter(e['type'] for e in parse_log(log))['tilt'] == 0


def test_tilt_chain_bounds():  # №12/B22: инварианты цепочки «провал→месть→провал»
    for code in ('tilt', 'midturn', 'betray'):
        seed, n, sit, cfg = W[code]
        for arm in ({}, {'tilt': True}):
            st, P = bb_full.run_game(seed, n, situation=sit, cfg=arm)
            assert st['tilt_trig'] == st['tilt_hot'] + st['tilt_cold'] + st['tilt_mid'], code
            assert st['tilt_chain_fail'] <= st['tilt_chain_attack'] <= st['tilt_trig'], code


def test_baseline_anchor():''')

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
print(f'OK: B22/№12 — тильт (флаг default OFF, гроссбух всегда, ↯ = 70-й шаблон); файлов: {len(srcs)}')
