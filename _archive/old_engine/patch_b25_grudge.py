# -*- coding: utf-8 -*-
"""B25 / меню №14: ДОЛГАЯ ПАМЯТЬ ОБИД — месть на всю партию с затуханием vs окно 2 цикла.

Суть (по меню): бот помнит, кто его бил/крал/унижал, — и эта память живёт ВСЮ партию,
затухая с циклами (флаг `grudge`), либо умирает через 2 цикла (флаг `grudge_window` —
короткая память; работает и отдельно от grudge). Оба флага HOUSE, default OFF —
канон бит-в-бит (grudge_eff при OFF возвращает 0.0 до всяких счётчиков, ГСЧ не трогается).

Гроссбух (ведётся ВСЕГДА, rng не трогает): личная книга обид p['grudge']:
seat → [сила, цикл последней обиды]; пишется в rep_note() из тех же ПУБЛИЧНЫХ событий,
что и репутация B21 (открытая информация — откаты №1–2 соблюдены): вред dw<0 добавляет
|personal| (kill 1.5, wound 0.7, steal/humiliate 0.6, mass/betrayal…), благодеяние dw>0
гасит обиду к нулю. Счётчики st: grudge_notes/soothes/peak — всегда; grudge_revenge
(месть через список vengeance), grudge_marked (взвешенный выбор пал на должника),
grudge_faded (оценки увядших записей) — при флагах.

Применение (только ON) в pick_target, guard `agg = harmful and not need_hurt`
(агрессивные выборы; Священник и лечение — мимо):
  1) список мести: обида ≥ GR_VENG (1.0) встает рядом с dealt_k≥2 и rep≤−2; выбор —
     публичная строка 💢 (событие grudge, 72-й шаблон);
  2) веса целей: × min(2.5, 1 + GR_BIAS·eff) — обидчик желаннее непрерывно.
Коэффициенты GR_DECAY=0.8, GR_WIN=2, GR_VENG=1.0, GR_BIAS=0.45 — «на глаз», НЕ тюнятся
(меню №10 заморожено). Затухание ленивое: eff = сила × 0.8^Δ (Δ = циклы с последней обиды),
порог увядания 0.05 (kill живёт значимым ~13 циклов, wound ~7).

Файлы: bb_full.py (8 правок), bb_events.py (PAT+докстринг), bb_html.py (карта ленты),
coverage_test.py (EXPECT+SAMPLES+живой кейс), bb.py (ОБА списка ключей),
fuzz_test.py (2 тумблера + попутно закрыт пропуск B21: reputation; 2 инварианта),
integrity_audit.py (2 конфига → 26), run_tests.sh (шаг 6j), test_effects.py
(2 свидетеля + 4 теста → 46).

Протокол: точные якоря, assert count==1, ast.parse до записи, запись в конце; идемпотентен.
"""
import ast, sys

EDITS = []  # (path, old, new)

def add(path, old, new):
    EDITS.append((path, old, new))

# ---------------------------------------------------------------- bb_full.py: флаги
add('bb_full.py',
    '             reserve_strict=False)  # №13/B23b: жёсткий резерв — с реактивной картой ход пропускается целиком (нужен вместе с reserve_gate)',
    '             reserve_strict=False,  # №13/B23b: жёсткий резерв — с реактивной картой ход пропускается целиком (нужен вместе с reserve_gate)\n'
    '             grudge=False,     # №14/B25: долгая память обид — месть через всю партию с затуханием ×0.8/цикл (HOUSE, default off)\n'
    '             grudge_window=False)  # №14/B25: окно памяти обид 2 цикла вместо затухания (работает и отдельно от grudge)')

# ---------------------------------------------------------------- bb_full.py: поле игрока + чучело
add('bb_full.py',
    "                      lives=C['lives'], my_acts={}, is_traitor=False, traitor_target=None, rl={}, rep={},",
    "                      lives=C['lives'], my_acts={}, is_traitor=False, traitor_target=None, rl={}, rep={}, grudge={},   # №14/B25: память обид: seat → [сила, цикл последней]")

add('bb_full.py',
    "                pd = dict(seat=g['seat'], is_doll=True, alive=True, limbo=None, frozen=0, or_=0, hand=g['hand'], prof_name='Чучело', archs=[], rep={}, pact=[], demon=None, gained=0, heals_done=0,",
    "                pd = dict(seat=g['seat'], is_doll=True, alive=True, limbo=None, frozen=0, or_=0, hand=g['hand'], prof_name='Чучело', archs=[], rep={}, grudge={}, pact=[], demon=None, gained=0, heals_done=0,")

# ---------------------------------------------------------------- bb_full.py: гроссбух st
add('bb_full.py',
    '              reserve_arm_kinds={}, reserve_saved=0, reserve_back=0, reserve_lost=0, reserve_holders={})',
    '              reserve_arm_kinds={}, reserve_saved=0, reserve_back=0, reserve_lost=0, reserve_holders={},\n'
    '              grudge_notes=0, grudge_soothes=0, grudge_peak=0.0,   # №14/B25: гроссбух обид (ведётся всегда)\n'
    '              grudge_revenge=0, grudge_marked=0, grudge_faded=0)   # №14/B25: мести; помеченные цели; увядшие оценки (при флагах)')

# ---------------------------------------------------------------- bb_full.py: запись обид в rep_note
add('bb_full.py',
    "        if victim is not None and victim is not perp:\n"
    "            r = victim.setdefault('rep', {})\n"
    "            r[perp['seat']] = round(r.get(perp['seat'], 0.0) + personal, 3)",
    "        if victim is not None and victim is not perp:\n"
    "            r = victim.setdefault('rep', {})\n"
    "            r[perp['seat']] = round(r.get(perp['seat'], 0.0) + personal, 3)\n"
    "            g = victim.setdefault('grudge', {})   # №14/B25: личная память обид (гроссбух ведётся всегда, rng не трогает)\n"
    "            e = g.get(perp['seat'])\n"
    "            if dw < 0:\n"
    "                w = abs(personal) if personal else abs(dw)\n"
    "                if e: e[0] = round(e[0] + w, 3); e[1] = st['cycle']\n"
    "                else: g[perp['seat']] = [round(w, 3), st['cycle']]\n"
    "                st['grudge_notes'] += 1\n"
    "                st['grudge_peak'] = max(st['grudge_peak'], g[perp['seat']][0])\n"
    "            elif dw > 0 and e:   # благодеяние гасит обиду (пол — ноль)\n"
    "                e[0] = round(max(0.0, e[0] - abs(dw)), 3)\n"
    "                st['grudge_soothes'] += 1\n"
    "                if e[0] <= 0: del g[perp['seat']]")

# ---------------------------------------------------------------- bb_full.py: grudge_eff + применение в pick_target
add('bb_full.py',
    '    def pick_target(a, need_hurt=False, harmful=True):',
    "    GR_DECAY, GR_WIN, GR_VENG, GR_BIAS = 0.8, 2, 1.0, 0.45   # №14/B25: затухание/цикл; окно; порог мести; наклон веса (на глаз, НЕ тюнятся — №10 заморожен)\n"
    "\n"
    "    def grudge_eff(a, q):\n"
    "        \"\"\"№14/B25: действующая сила обиды a на q; 0.0 при выключенных флагах (канон бит-в-бит).\n"
    "        decay (grudge): сила × GR_DECAY^Δциклов — память на всю партию с затуханием;\n"
    "        window (grudge_window): Δ ≤ GR_WIN без затухания, дальше запись мертва.\n"
    "        grudge_faded — оценки увядших записей (сила < 0.05 или окно вышло).\"\"\"\n"
    "        if not (C['grudge'] or C['grudge_window']):\n"
    "            return 0.0\n"
    "        e = a.get('grudge', {}).get(q['seat'])\n"
    "        if not e or e[0] <= 0:\n"
    "            return 0.0\n"
    "        d = st['cycle'] - e[1]\n"
    "        eff = (e[0] if d <= GR_WIN else 0.0) if C['grudge_window'] else e[0] * GR_DECAY ** d\n"
    "        if eff < 0.05:\n"
    "            st['grudge_faded'] += 1\n"
    "            return 0.0\n"
    "        return eff\n"
    "\n"
    "    def pick_target(a, need_hurt=False, harmful=True):")

add('bb_full.py',
    "        vengeance = [q for q in cands if q['dealt_k'] >= 2\n"
    "                     or (C['reputation'] and a.get('rep', {}).get(q['seat'], 0.0) <= -2.0)]   # №11/B21\n"
    "        if vengeance and rng.random() < .2 + .25 * v['coop']:   # B10: месть мягче (aggr-тюнинг)\n"
    "            return max(vengeance, key=threat)",
    "        agg = harmful and not need_hurt   # №14/B25: обида ведёт месть только в агрессивных выборах (Священник/heal — мимо)\n"
    "        vengeance = [q for q in cands if q['dealt_k'] >= 2\n"
    "                     or (C['reputation'] and a.get('rep', {}).get(q['seat'], 0.0) <= -2.0)   # №11/B21\n"
    "                     or (agg and grudge_eff(a, q) >= GR_VENG)]   # №14/B25: старая обида — повод для мести\n"
    "        if vengeance and rng.random() < .2 + .25 * v['coop']:   # B10: месть мягче (aggr-тюнинг)\n"
    "            t = max(vengeance, key=threat)\n"
    "            ge = grudge_eff(a, t) if agg else 0.0   # №14/B25\n"
    "            if ge >= GR_VENG:\n"
    "                st['grudge_revenge'] += 1\n"
    "                say(f'  💢 P{a[\"seat\"]}: обида на P{t[\"seat\"]} (сила {ge:.2f}) → месть')\n"
    "            return t")

add('bb_full.py',
    "        if C['reputation']:   # №11/B21: враги (rep<0) желаннее, благодетели реже\n"
    "            wts = [w * min(2.5, max(.25, 1 - .18 * a.get('rep', {}).get(q['seat'], 0.0))) for w, q in zip(wts, cands)]\n"
    "        return rng.choices(cands, weights=wts)[0]",
    "        if C['reputation']:   # №11/B21: враги (rep<0) желаннее, благодетели реже\n"
    "            wts = [w * min(2.5, max(.25, 1 - .18 * a.get('rep', {}).get(q['seat'], 0.0))) for w, q in zip(wts, cands)]\n"
    "        if agg and (C['grudge'] or C['grudge_window']):   # №14/B25: обидчик желаннее — до ×2.5\n"
    "            wts = [w * min(2.5, 1 + GR_BIAS * grudge_eff(a, q)) for w, q in zip(wts, cands)]\n"
    "        t = rng.choices(cands, weights=wts)[0]\n"
    "        if agg and grudge_eff(a, t) >= GR_VENG:   # №14/B25: выбор пал на должника по обиде\n"
    "            st['grudge_marked'] += 1\n"
    "        return t")

# ---------------------------------------------------------------- bb_events.py: 72-й шаблон (тип grudge)
add('bb_events.py',
    '  parse_log(lines)     → список событий ПОЛНОГО каталога (71 шаблон say() ядра B23),',
    '  parse_log(lines)     → список событий ПОЛНОГО каталога (72 шаблона say() ядра B25),')

add('bb_events.py',
    " (r'^\\s*🧊 P(\\d+): резерв — РПД не тратятся ради обмена «([^»]+)» \\(угроза ([\\d.]+)\\)', 'reserve',\n"
    "  lambda m: dict(seat=int(m[1]), card=m[2], threat=float(m[3]))),   # №13/B23: планирование резерва",
    " (r'^\\s*🧊 P(\\d+): резерв — РПД не тратятся ради обмена «([^»]+)» \\(угроза ([\\d.]+)\\)', 'reserve',\n"
    "  lambda m: dict(seat=int(m[1]), card=m[2], threat=float(m[3]))),   # №13/B23: планирование резерва\n"
    " (r'^\\s*💢 P(\\d+): обида на P(\\d+) \\(сила ([\\d.]+)\\) → месть', 'grudge',\n"
    "  lambda m: dict(seat=int(m[1]), to=int(m[2]), force=float(m[3]))),   # №14/B25: долгая память обид — месть")

# ---------------------------------------------------------------- bb_html.py: карта ленты
add('bb_html.py',
    " reserve:{i:'🧊',l:'резерв РПД',g:'карты',c:'card',r:e=>one(e.seat)+'бережёт РПД ради обмена «'+esc(e.card)+'» (угроза '+e.threat+')'},   // №13/B23",
    " reserve:{i:'🧊',l:'резерв РПД',g:'карты',c:'card',r:e=>one(e.seat)+'бережёт РПД ради обмена «'+esc(e.card)+'» (угроза '+e.threat+')'},   // №13/B23\n"
    " grudge:{i:'💢',l:'обида',g:'действия',c:'wou',r:e=>one(e.seat)+'обида на '+one(e.to)+' (сила '+e.force+') → месть'},   // №14/B25")

# ---------------------------------------------------------------- coverage_test.py: EXPECT + SAMPLES + живой кейс
add('coverage_test.py',
    'Часть B (синтетика): все 71 шаблон say() из bb_full.py, включая редкие ветви, которые в',
    'Часть B (синтетика): все 72 шаблона say() из bb_full.py, включая редкие ветви, которые в')

add('coverage_test.py',
    " '🧊 P#: резерв — РПД не тратятся ради обмена «#» (#)': 'reserve',   # №13/B23",
    " '🧊 P#: резерв — РПД не тратятся ради обмена «#» (#)': 'reserve',   # №13/B23\n"
    " '💢 P#: обида на P# (#) → месть': 'grudge',   # №14/B25")

add('coverage_test.py',
    " '🧊 P#: резерв — РПД не тратятся ради обмена «#» (#)': '  🧊 P4: резерв — РПД не тратятся ради обмена «ПУСТО» (угроза 0.31)',",
    " '🧊 P#: резерв — РПД не тратятся ради обмена «#» (#)': '  🧊 P4: резерв — РПД не тратятся ради обмена «ПУСТО» (угроза 0.31)',\n"
    " '💢 P#: обида на P# (#) → месть': '  💢 P3: обида на P5 (сила 1.23) → месть',")

add('coverage_test.py',
    "    (2, 8, 'base', dict(reserve=True)),    # №13/B23: живой кейс планирования резерва (🧊)",
    "    (2, 8, 'base', dict(reserve=True)),    # №13/B23: живой кейс планирования резерва (🧊)\n"
    "    (2, 8, 'base', dict(grudge=True)),     # №14/B25: живой кейс мести по обиде (💢)")

# ---------------------------------------------------------------- bb.py: ОБА списка ключей (урок B21)
add('bb.py',
    "            'reserve', 'reserve_gate', 'reserve_strict']",
    "            'reserve', 'reserve_gate', 'reserve_strict', 'grudge', 'grudge_window']")

add('bb.py',
    "             'reserve', 'reserve_gate', 'reserve_strict'}",
    "             'reserve', 'reserve_gate', 'reserve_strict', 'grudge', 'grudge_window'}")

# ---------------------------------------------------------------- fuzz_test.py: тумблеры + инварианты
add('fuzz_test.py',
    "    TOGGLES = ['blind_kill', 'queue_reverse', 'traitor', 'spec_cycle', 'escalation', 'pressure',\n"
    "               'or_noise', 'crit_price', 'pacifist_c1', 'random_outcome', 'revive_esc', 'draft',\n"
    "               'tilt', 'reserve', 'reserve_gate', 'reserve_strict']   # B22/№12, B23/№13",
    "    TOGGLES = ['blind_kill', 'queue_reverse', 'traitor', 'spec_cycle', 'escalation', 'pressure',\n"
    "               'or_noise', 'crit_price', 'pacifist_c1', 'random_outcome', 'revive_esc', 'draft',\n"
    "               'reputation', 'tilt', 'reserve', 'reserve_gate', 'reserve_strict',   # B21/№11 (пропуск закрыт B25), B22/№12, B23/№13\n"
    "               'grudge', 'grudge_window']   # №14/B25")

add('fuzz_test.py',
    "        if cfg.get('draft'):   # B16/№9: при драфте личных раскрытых нет, захватов не больше успехов «add»\n"
    "            if any(p['rev'] for p in P): fails.append((combo, seed, 'rev non-empty under draft'))\n"
    "            if st['draft_takes'] > st['rpds_types'].get('add', 0): fails.append((combo, seed, 'draft takes > add'))",
    "        if cfg.get('draft'):   # B16/№9: при драфте личных раскрытых нет, захватов не больше успехов «add»\n"
    "            if any(p['rev'] for p in P): fails.append((combo, seed, 'rev non-empty under draft'))\n"
    "            if st['draft_takes'] > st['rpds_types'].get('add', 0): fails.append((combo, seed, 'draft takes > add'))\n"
    "        if any(v[0] < 0 for p in P for v in p.get('grudge', {}).values()): fails.append((combo, seed, 'negative grudge'))   # №14/B25\n"
    "        if not (cfg.get('grudge') or cfg.get('grudge_window')) and (st['grudge_revenge'] or st['grudge_marked'] or st['grudge_faded']):\n"
    "            fails.append((combo, seed, 'grudge behaviour while OFF'))   # №14/B25: OFF — поведение не просачивается")

# ---------------------------------------------------------------- integrity_audit.py: 26 конфигов
add('integrity_audit.py',
    "    ('strict reserve N8',   dict(n=8, cfg=dict(reserve=True, reserve_gate=True, reserve_strict=True))),  # №13/B23b",
    "    ('strict reserve N8',   dict(n=8, cfg=dict(reserve=True, reserve_gate=True, reserve_strict=True))),  # №13/B23b\n"
    "    ('grudge ON N8',        dict(n=8, cfg=dict(grudge=True))),          # №14/B25\n"
    "    ('grudge window N12',   dict(n=12, cfg=dict(grudge_window=True))),  # №14/B25")

# ---------------------------------------------------------------- run_tests.sh: шаг 6j
add('run_tests.sh',
    'chk $? "резерв smoke"',
    '''chk $? "резерв smoke"

step "6j. №14/B25: долгая память обид (ON детерминирован и меняет игру; гроссбух ведётся и при OFF)"
python3 - <<'PY'
import hashlib, bb_full
def h(seed, n, cfg):
    log = []
    bb_full.run_game(seed, n, log=log, cfg=cfg)
    return hashlib.sha256('\\n'.join(log).encode()).hexdigest()
on1 = h(2, 8, {'grudge': True}); on2 = h(2, 8, {'grudge': True})
assert on1 == on2, 'grudge ON недетерминирован'
diff = sum(h(s, 8, {}) != h(s, 8, {'grudge': True}) for s in range(1, 13))
assert diff >= 1, 'grudge ON не изменил ни одной партии из 12'
log = []
st, P = bb_full.run_game(2, 8, log=log, cfg={'grudge': True})
assert st['grudge_revenge'] >= 1 and any('💢' in l for l in log), 'ON: мести по обиде нет'
assert all(v[0] >= 0 for p in P for v in p.get('grudge', {}).values()), 'ON: отрицательная обида'
log = []
st, P = bb_full.run_game(2, 8, log=log, cfg={})   # OFF: гроссбух ведётся, 💢 в логе нет
assert st['grudge_notes'] > 0, 'OFF: обид не видно — гроссбух мёртв'
assert not any('💢' in l for l in log), 'OFF: строки обид просочились в канон'
assert st['grudge_revenge'] == 0 and st['grudge_marked'] == 0 and st['grudge_faded'] == 0, 'OFF: поведение просочилось'
w1 = h(2, 8, {'grudge_window': True}); w2 = h(2, 8, {'grudge_window': True})
assert w1 == w2, 'grudge_window недетерминирован'
stw, Pw = bb_full.run_game(2, 8, cfg={'grudge_window': True})
assert stw['grudge_faded'] >= 1, 'WINDOW: ни одной увядшей записи — не на чём мерить'
print(f'  6j OK: ON детерминирован, расхождение {diff}/12; OFF notes={st["grudge_notes"]}, peak={st["grudge_peak"]}; WINDOW faded={stw["grudge_faded"]}, месть {stw["grudge_revenge"]}')
PY
chk $? "память обид smoke"''')

# ---------------------------------------------------------------- test_effects.py: свидетели + 4 теста
add('test_effects.py',
    "    'rvgate':   (2, 8,   'base',  {'reserve': True, 'reserve_gate': True}),  # №13/B23b: строгий гейт",
    "    'rvgate':   (2, 8,   'base',  {'reserve': True, 'reserve_gate': True}),  # №13/B23b: строгий гейт\n"
    "    'grudge':   (2, 8,   'base',  {'grudge': True}),   # №14/B25: месть по старой обиде (💢)\n"
    "    'grwin':    (2, 8,   'base',  {'grudge_window': True}),  # №14/B25: окно 2 цикла — записи увядают")

add('test_effects.py',
    '# ---------------------------------------------------------------- раннер без pytest',
    '''def test_grudge():          # №14/B25: ON — месть по обиде (💢 в ленте и в счётчике)
    st, P, cnt = run('grudge')
    assert cnt['grudge'] >= 1, 'свидетель обиды не сработал'
    assert st['grudge_revenge'] >= 1 and st['grudge_notes'] >= 1


def test_grudge_off_ledger():  # №14/B25: OFF — гроссбух ведётся, строк 💢 нет, поведение не просачивается
    seed, n, sit, _ = W['grudge']
    log = []
    st, P = bb_full.run_game(seed, n, log=log, situation=sit, cfg={})
    assert st['grudge_notes'] > 0, 'OFF: обид нет — гроссбух мёртв'
    assert st['grudge_revenge'] == 0 and st['grudge_marked'] == 0, 'OFF: поведение просочилось'
    assert collections.Counter(e['type'] for e in parse_log(log))['grudge'] == 0


def test_grudge_window():   # №14/B25: окно 2 цикла — старые записи увядают (faded)
    st, P, cnt = run('grwin')
    assert st['grudge_notes'] > 0
    assert st['grudge_faded'] >= 1, 'свидетель окна: ни одной увядшей оценки'


def test_grudge_ledger_bounds():  # №14/B25: сила обиды неотрицательна; мести ≤ агрессивных актов
    for code in ('grudge', 'grwin'):
        seed, n, sit, cfg = W[code]
        st, P = bb_full.run_game(seed, n, situation=sit, cfg=cfg)
        assert all(v[0] >= 0 for p in P for v in p.get('grudge', {}).values()), code
        harm = sum(st['acts'].get(k, 0) for k in ('kill', 'wound', 'steal', 'humiliate', 'mass', 'mass_steal'))
        assert st['grudge_revenge'] <= harm, code


# ---------------------------------------------------------------- раннер без pytest''')

# ---------------------------------------------------------------- применение
srcs = {}
applied = skipped = 0
for path, old, new in EDITS:
    if path not in srcs:
        srcs[path] = open(path, encoding='utf-8').read()
    if new in srcs[path]:
        skipped += 1
        continue
    cnt = srcs[path].count(old)
    if cnt != 1:
        print(f'FAIL: якорь встречается {cnt} раз (нужен 1): {path}: {old[:90]!r}')
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
print(f'OK: B25/№14 — долгая память обид (grudge/grudge_window); файлов: {len(srcs)}, правок: {applied} (пропущено уже применённых: {skipped})')
