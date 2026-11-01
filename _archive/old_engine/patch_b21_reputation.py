# -*- coding: utf-8 -*-
"""B21 / меню №11: РЕПУТАЦИЯ ботов (HOUSE-флаг, default OFF).

Суть: публичный гроссбух мнений rep[x][s] (>0 — благодетель, <0 — обидчик).
Ведётся ВСЕГДА (чистые dict-операции, ГСЧ не трогает → канон бит-совпадает),
а влияет на игру только при cfg['reputation']=True:
  1) pick_target: финальные веса × clamp(1 − 0.18·rep, 0.25…2.5) — враги желаннее, благодетели реже;
  2) ветка vengeance: кандидаты с личной обидой rep ≤ −2 joining dealt_k ≥ 2;
  3) предатель при потере цели выбирает новую с теми же весами (вместо rng.choice).
Учёт в гроссбухе (публичные события, открытая информация — меню №1/№2):
  kill −1.5 (жертве дополнительно −1.5), wound −0.7/−0.7, steal −0.4/−0.6,
  humiliate −0.4/−0.6, mass/mass_steal −0.5/−0.5 каждой цели,
  успешный heal +0.8/+0.8, разрыв пакта (ПРЕДАТЕЛЬСТВО) −1.5/−1.5.
Статы st['rep_harm'/'rep_enemy'/'rep_bene'/'rep_good'] — для измерений в обеих руках.
Не покрыто (осознанно): слепое убийство (цель случайна by design), отражение стеклом
(внешний агрессор уже учтён), спасение/щит (пассив, нет точки «спас credited»).
Коэффициенты выбраны «на глаз» и НЕ тюнились (меню №10: веса заморожены — канон не трогаем).

Протокол: точные якоря, assert count==1, ast.parse до записи, запись в конце.
"""
import ast, sys

EDITS = []  # (path, old, new)

def add(path, old, new):
    EDITS.append((path, old, new))

BB = 'bb_full.py'

# 1) cfg-флаг
add(BB, "             draft=False)     # №9/B16: раскрытые карты уходят в общий пул, РПДС «add» берёт оттуда (HOUSE, default off)",
        "             draft=False,    # №9/B16: раскрытые карты уходят в общий пул, РПДС «add» берёт оттуда (HOUSE, default off)\n"
        "             reputation=False) # №11/B21: репутация ботов — публичный гроссбух мнений, bias выбора цели (HOUSE, default off)")

# 2) st-счётчики (якорь — строка инициализации st)
add(BB, "exch_uses=0, limbo_events=0, agenda_uses=0, rpds_types={}, ghost_archs={}, betrayals=0, demon_acts=0, deals=0,",
        "exch_uses=0, limbo_events=0, agenda_uses=0, rpds_types={}, ghost_archs={}, betrayals=0, demon_acts=0, deals=0,\n"
        "              rep_harm=0, rep_enemy=0, rep_bene=0, rep_good=0,   # №11/B21: гроссбух репутации (ведётся всегда)")

# 3) rep={} в основном словаре игрока
add(BB, "                      lives=C['lives'], my_acts={}, is_traitor=False, traitor_target=None, rl={},",
        "                      lives=C['lives'], my_acts={}, is_traitor=False, traitor_target=None, rl={}, rep={},")

# 4) rep={} в словаре чучела (иначе setdefault-наследование даст АЛИАС гроссбуха P[0]!)
add(BB, "pd = dict(seat=g['seat'], is_doll=True, alive=True, limbo=None, frozen=0, or_=0, hand=g['hand'], prof_name='Чучело', archs=[], pact=[], demon=None, gained=0, heals_done=0,",
        "pd = dict(seat=g['seat'], is_doll=True, alive=True, limbo=None, frozen=0, or_=0, hand=g['hand'], prof_name='Чучело', archs=[], rep={}, pact=[], demon=None, gained=0, heals_done=0,")

# 5) помощник rep_note — перед pick_target
add(BB, "    def pick_target(a, need_hurt=False, harmful=True):",
"""    def rep_note(perp, victim, dw, personal=0.0):
        \"\"\"№11/B21: публичный гроссбух репутации. rep[x][s] — мнение x о s (>0 друг, <0 враг).
        Ведётся всегда (rng не трогает); bias применения — только при C['reputation'].
        dw — публичная дельта (видят все, информация открытая), personal — dodatk жертве.\"\"\"
        if perp is None:
            return
        if victim is not None:
            prior = perp.get('rep', {}).get(victim['seat'], 0.0)
            if dw < 0:
                st['rep_harm'] += 1
                if prior <= -1: st['rep_enemy'] += 1
                elif prior >= 1: st['rep_bene'] += 1
            elif dw > 0:
                st['rep_good'] += 1
        for x in P:
            r = x.setdefault('rep', {})
            r[perp['seat']] = round(r.get(perp['seat'], 0.0) + dw, 3)
        if victim is not None and victim is not perp:
            r = victim.setdefault('rep', {})
            r[perp['seat']] = round(r.get(perp['seat'], 0.0) + personal, 3)

    def pick_target(a, need_hurt=False, harmful=True):""")

# 6) vengeance: личная обида присоединяется к глобальным убийцам (только ON)
add(BB, "        vengeance = [q for q in cands if q['dealt_k'] >= 2]",
        "        vengeance = [q for q in cands if q['dealt_k'] >= 2\n"
        "                     or (C['reputation'] and a.get('rep', {}).get(q['seat'], 0.0) <= -2.0)]   # №11/B21")

# 7) финальные веса pick_target: репутационный множитель (только ON)
add(BB, "        wts = [max(.2, 1.2 - q['pers']['detach']) for q in cands]   # незаметных выбирают реже",
        "        wts = [max(.2, 1.2 - q['pers']['detach']) for q in cands]   # незаметных выбирают реже\n"
        "        if C['reputation']:   # №11/B21: враги (rep<0) желаннее, благодетели реже\n"
        "            wts = [w * min(2.5, max(.25, 1 - .18 * a.get('rep', {}).get(q['seat'], 0.0))) for w, q in zip(wts, cands)]")

# 8) act(): учёт вредных действий (после геройского даунгрейда — по фактическому исходу)
add(BB, """        if kind == 'kill' and st['roles'].get(a['seat']) == 'hero' and st['roles'].get(t['seat']) != 'villain':
            say(f'    🎬 герой P{a["seat"]}: убийство не-злодея запрещено → ранение')
            kind = 'wound'
        if kind in ('wound', 'kill'):""",
"""        if kind == 'kill' and st['roles'].get(a['seat']) == 'hero' and st['roles'].get(t['seat']) != 'villain':
            say(f'    🎬 герой P{a["seat"]}: убийство не-злодея запрещено → ранение')
            kind = 'wound'
        if t is not None and not reflected and kind in ('wound', 'kill', 'steal', 'humiliate'):
            rep_note(a, t, -1.5 if kind == 'kill' else (-0.7 if kind == 'wound' else -0.4),   # №11/B21
                     -1.5 if kind == 'kill' else (-0.7 if kind == 'wound' else -0.6))
        if kind in ('wound', 'kill'):""")

# 9) mass: учёт по каждой цели
add(BB, "            ts = rng.sample(cands, 2); r = roll(); st['mass'] += 1",
        "            ts = rng.sample(cands, 2); r = roll(); st['mass'] += 1\n"
        "            for t2 in ts: rep_note(a, t2, -0.5, -0.5)   # №11/B21")

# 10) mass_steal: учёт по каждой цели
add(BB, "            ts = rng.sample(cands, k); r = roll(); st['mass'] += 1",
        "            ts = rng.sample(cands, k); r = roll(); st['mass'] += 1\n"
        "            for t2 in ts: rep_note(a, t2, -0.5, -0.5)   # №11/B21")

# 11) успешный heal: плюс к репутации
add(BB, "                t['or_'] = max(0, t['or_'] - 1); t['heal'] += 1; a['heals_done'] += 1",
        "                t['or_'] = max(0, t['or_'] - 1); t['heal'] += 1; a['heals_done'] += 1\n"
        "                rep_note(a, t, 0.8, 0.8)   # №11/B21")

# 12) ПРЕДАТЕЛЬСТВО (разрыв пакта): публичный минус
add(BB, "                    st['betrayals'] += 1",
        "                    st['betrayals'] += 1\n"
        "                    rep_note(p, other, -1.5, -1.5)   # №11/B21")

# 13) предатель выбирает новую цель по репутации (только ON; 1 draw, как rng.choice)
add(BB, """                        if cands:
                            tr['target'] = rng.choice(cands)['seat']""",
"""                        if cands:
                            if C['reputation']:   # №11/B21: самая дурная слава — приоритет
                                wt = [max(.2, 1 - .18 * by_seat(tr['seat']).get('rep', {}).get(q['seat'], 0.0)) for q in cands]
                                tr['target'] = rng.choices(cands, weights=wt)[0]['seat']
                            else:
                                tr['target'] = rng.choice(cands)['seat']""")

# --- bb.py: CLI-список bool-ключей
add('bb.py', "            'random_outcome', 'ablate', 'revive_esc', 'hand_limit', 'draft']",
             "            'random_outcome', 'ablate', 'revive_esc', 'hand_limit', 'draft', 'reputation']")

# --- run_tests.sh: шаг 6g (после 6f)
add('run_tests.sh', """else
  python3 test_effects.py | tail -2
  chk ${PIPESTATUS[0]} "test_effects.py (встроенный раннер)"
fi""",
"""else
  python3 test_effects.py | tail -2
  chk ${PIPESTATUS[0]} "test_effects.py (встроенный раннер)"
fi

step "6g. №11/B21: репутация (ON детерминирована и меняет игру; OFF=канон проверяют baseline+отпечатки)"
python3 - <<'PY'
import hashlib, bb_full
def h(seed, n, cfg):
    log = []
    bb_full.run_game(seed, n, log=log, cfg=cfg)
    return hashlib.sha256('\\n'.join(log).encode()).hexdigest()
on1 = h(7, 8, {'reputation': True}); on2 = h(7, 8, {'reputation': True})
assert on1 == on2, 'reputation ON недетерминирована'
diff = sum(h(s, 8, {}) != h(s, 8, {'reputation': True}) for s in range(1, 13))
assert diff >= 1, 'reputation ON не изменила ни одной партии из 12'
print(f'  6g OK: ON детерминирована, расхождение с каноном {diff}/12 партий')
PY
chk $? "репутация smoke\"""")

# --- проверка якорей и запись ---
srcs = {}
for path, old, new in EDITS:
    if path not in srcs:
        srcs[path] = open(path, encoding='utf-8').read()
    cnt = srcs[path].count(old)
    if cnt != 1:
        print(f'FAIL: якорь встречается {cnt} раз (нужно 1) в {path}:\n{old[:120]}')
        sys.exit(1)
    srcs[path] = srcs[path].replace(old, new, 1)

for path in ('bb_full.py', 'bb.py'):
    try:
        ast.parse(srcs[path])
    except SyntaxError as e:
        print(f'FAIL: синтаксис {path}: {e}')
        sys.exit(1)

for path, txt in srcs.items():
    open(path, 'w', encoding='utf-8').write(txt)
print('OK: B21/№11 репутация — 13 правок bb_full.py + bb.py + run_tests.sh (шаг 6g), синтаксис проверен')
