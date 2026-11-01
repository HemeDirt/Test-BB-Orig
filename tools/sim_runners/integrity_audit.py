# -*- coding: utf-8 -*-
"""B21: АУДИТ ЦЕЛОСТНОСТИ ИГРЫ — независимая проверка «игры как таковой».

Не путать с run_tests.sh (регрессии) и validate/fuzz/coverage (инварианты лога):
этот аудит кросс-проверяет СОСТОЯНИЕ против ЛОГА против МОДЕЛИ на широкой сетке конфигов.

Проверки на каждую партию (config × seeds 1..5):
  A. детерминизм: два независимых прогона → sha256 лога совпадает;
  B. выжившие: st['alive'] == число живых в P; st['deaths'] == сумма st['causes'];
  C. неотрицательность: tokens ≥ 0, or_ ≥ 0 у всех; у живых or_ < or_death;
  D. лог → состояние: событий смерти/воскрешений/обрывов(B17) столько же, сколько в st;
     номер последнего cycle_start == st['end'];
  E. hand_limit: рука (Σ карт) ≤ лимита у всех (для конфигов с лимитом);
  F. разбор лога: доля строк, не распознанных bb_events (WARN, с образцами);
  G. build_model smoke: снимочный прогон сходится с логовым (внутренний assert bb_model).

Лимит пользователя: ≤100 партий на конфигурацию (здесь 5×2 прогона = 10).
Usage: python3 integrity_audit.py [--seeds 5] [--out audit_integrity.json]
"""
import argparse, hashlib, json, sys, traceback
import bb_full, bb_core, bb_events

CONFIGS = [
    ('канон N8',            dict(n=8)),
    ('канон N12',           dict(n=12)),
    ('канон N16',           dict(n=16)),
    ('канон N20',           dict(n=20)),
    ('plane N8',            dict(n=8, sit='plane')),
    ('pole N8',             dict(n=8, sit='pole')),
    ('purg N12',            dict(n=12, sit='purg')),
    ('hrono N8',            dict(n=8, sit='hrono')),
    ('amkary N12',          dict(n=12, sit='amkary')),
    ('rpds_economy N12',    dict(n=12, cfg=dict(mode='rpds_economy'))),
    ('draft N8 rpds',       dict(n=8, cfg=dict(mode='rpds_economy', draft=True))),
    ('hand_limit=7 N8',     dict(n=8, cfg=dict(hand_limit=7))),
    ('revive_esc N16',      dict(n=16, cfg=dict(revive_esc=True))),
    ('reputation ON N8',    dict(n=8, cfg=dict(reputation=True))),
    ('tilt ON N8',          dict(n=8, cfg=dict(tilt=True))),          # №12/B22
    ('reserve ON N8',       dict(n=8, cfg=dict(reserve=True))),       # №13/B23
    ('reserve+gate N12',    dict(n=12, cfg=dict(reserve=True, reserve_gate=True))),   # №13/B23b STRICT
    ('strict reserve N8',   dict(n=8, cfg=dict(reserve=True, reserve_gate=True, reserve_strict=True))),  # №13/B23b
    ('grudge ON N8',        dict(n=8, cfg=dict(grudge=True))),          # №14/B25
    ('grudge window N12',   dict(n=12, cfg=dict(grudge_window=True))),  # №14/B25
    ('ablate all N8',       dict(n=8, cfg=dict(ablate='all'))),
    ('traitor+blind N8',    dict(n=8, cfg=dict(traitor=True, blind_kill=True))),
    ('lives=2 N12',         dict(n=12, cfg=dict(lives=2))),
    ('D6 N8',               dict(n=8, cfg=dict(dice=bb_core.D6))),
    ('random_outcome N8',   dict(n=8, cfg=dict(random_outcome=True))),
    ('misc N12',            dict(n=12, cfg=dict(queue_reverse=True, escalation=True, pressure=True))),
]

REVIVE_TYPES = {'revive_tokens', 'revive_necro', 'revive_agent'}   # B21b: 🚌 больше не безмолвен


def run_once(spec, seed):
    log = []
    st, P = bb_full.run_game(seed, spec['n'], log=log, situation=spec.get('sit', 'base'),
                             cfg=spec.get('cfg'))
    return log, st, P


def check_game(name, spec, seed, fails, warns):
    tag = f"{name}/seed{seed}"
    log, st, P = run_once(spec, seed)
    log2, st2, P2 = run_once(spec, seed)
    h1 = hashlib.sha256('\n'.join(log).encode()).hexdigest()
    h2 = hashlib.sha256('\n'.join(log2).encode()).hexdigest()
    if h1 != h2:
        fails.append(f'{tag}: A детерминизм — sha разошёлся')
    # B
    alive_n = sum(1 for p in P if p['alive'] and not p['limbo'])   # st['alive'] не считает лимбо
    if st['alive'] != alive_n:
        fails.append(f"{tag}: B st['alive']={st['alive']} != живых вне лимбо {alive_n}")
    if st['deaths'] != sum(st['causes'].values()):
        fails.append(f"{tag}: B deaths={st['deaths']} != Σcauses={sum(st['causes'].values())}")
    # C
    for p in P:
        if p['tokens'] < 0 or p['or_'] < 0:
            fails.append(f"{tag}: C P{p['seat']} tokens={p['tokens']} or_={p['or_']}")
        if p['alive'] and not p.get('is_doll') and p['or_'] >= ((spec.get('cfg') or {}).get('or_death', 3)):
            fails.append(f"{tag}: C живой P{p['seat']} с or_={p['or_']} ≥ or_death")
    # D: лог → состояние
    ev = bb_events.parse_log(log)
    n_death = sum(1 for e in ev if e['type'] == 'death')
    n_rev = sum(1 for e in ev if e['type'] in REVIVE_TYPES)   # реинкарнация Буддиста — ПРЕДОТВРАЩЕНИЕ смерти, не воскрешение
    n_stop = sum(1 for e in ev if e['type'] == 'midturn_stop')
    cycles = [e['c'] for e in ev if e['type'] == 'cycle_start']
    if n_death != st['deaths']:
        fails.append(f"{tag}: D событий смерти {n_death} != st deaths {st['deaths']}")
    if n_rev != st['revives']:
        fails.append(f"{tag}: D событий воскрешения {n_rev} != st revives {st['revives']}")
    if n_stop != st['midturn_stops']:
        fails.append(f"{tag}: D обрывов B17 {n_stop} != st {st['midturn_stops']}")
    if cycles and max(cycles) != st['end']:
        fails.append(f"{tag}: D последний цикл лога {max(cycles)} != st end {st['end']}")
    # E: hand_limit
    cfg = spec.get('cfg') or {}
    lim = cfg.get('hand_limit')
    if lim:
        for p in P:
            hs = sum(len(l) for l in p['hand'].values())
            if hs > lim:
                fails.append(f"{tag}: E P{p['seat']} рука {hs} > лимита {lim}")
    # F: нераспознанные строки
    others = [e for e in ev if e['type'] == 'other']
    if others:
        warns.append(f"{tag}: F нераспознанных строк {len(others)}, напр.: {others[0]['text'][:60]}")
    return h1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', type=int, default=5)
    ap.add_argument('--out', default='audit_integrity.json')
    a = ap.parse_args()
    fails, warns, hashes = [], [], {}
    n_games = 0
    for name, spec in CONFIGS:
        for seed in range(1, a.seeds + 1):
            try:
                h = check_game(name, spec, seed, fails, warns)
                hashes[f'{name}/seed{seed}'] = h[:12]
                n_games += 1
            except Exception:
                fails.append(f'{name}/seed{seed}: EXCEPTION\n{traceback.format_exc(limit=3)}')
    # G: модель (3 контрольных конфига)
    import bb_model
    for name, spec, seed in ((CONFIGS[0][0], CONFIGS[0][1], 3), (CONFIGS[4][0], CONFIGS[4][1], 77), (CONFIGS[10][0], CONFIGS[10][1], 4)):
        try:
            m = bb_model.build_model(seed, spec['n'], sit=spec.get('sit', 'base'), cfg=spec.get('cfg'))
            assert isinstance(m, dict) and m, 'пустая модель'
        except Exception:
            fails.append(f"G build_model {name}/seed{seed}: {traceback.format_exc(limit=2)}")
    res = dict(configs=len(CONFIGS), seeds=a.seeds, games=n_games,
               fails=fails, warns=warns, hashes=hashes)
    json.dump(res, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'АУДИТ ЦЕЛОСТНОСТИ: конфигов {len(CONFIGS)}, партий {n_games} (×2 прогона), model-smoke 3')
    for w in warns[:10]:
        print('  WARN', w)
    if warns and len(warns) > 10:
        print(f'  ... ещё WARN: {len(warns) - 10}')
    if fails:
        for f in fails[:15]:
            print('  FAIL', f)
        print(f'ИТОГ: ПРОВАЛОВ {len(fails)} — целостность НАРУШЕНА')
        sys.exit(1)
    print(f'ИТОГ: 0 провалов, {len(warns)} предупреждений — ЦЕЛОСТНОСТЬ ПОДТВЕРЖДЕНА')


if __name__ == '__main__':
    main()
