# -*- coding: utf-8 -*-
"""Фазз-валидатор (усиление): случайные конфиги × партии + инварианты, включая режимы Жатвы."""
import random, itertools, bb_full, validate
from bb_core import D6, D20
MODES = ['std', 'off_after_corpse', 'off_after_death', 'off', 'max2', 'quiet2', 'late']
rng = random.Random(77)
fails = []
checked = 0
for combo in range(60):
    TOGGLES = ['blind_kill', 'queue_reverse', 'traitor', 'spec_cycle', 'escalation', 'pressure',
               'or_noise', 'crit_price', 'pacifist_c1', 'random_outcome', 'revive_esc', 'draft',
               'reputation', 'tilt', 'reserve', 'reserve_gate', 'reserve_strict',   # B21/№11 (пропуск закрыт B25), B22/№12, B23/№13
               'grudge', 'grudge_window']   # №14/B25
    cfg = dict(harvest_mode=rng.choice(MODES), or_death=rng.choice([2, 3, 4, 7]),
               reveal=rng.choice([1, 2, 3]), dice=rng.choice([D20, D6]), fear=rng.choice([True, False]),
               mode=rng.choice(['std', 'rpds_economy']),
               harvest_pick=rng.choice(['random', 'leader']), lives=rng.choice([1, 1, 2]),
               rpds=rng.choice([0, 1, 2]), rpdi=rng.choice([0, 1, 2]), agenda_p=rng.choice([0, .25, .5]),
               hand_limit=rng.choice([None, None, 7, 9, 12]))   # B15/№7 (≥7=len(CATS), B15b)
    for t in TOGGLES:            # B14: каждый переключатель случайно вкл/выкл
        if rng.random() < .35: cfg[t] = True
    sit = rng.choice(['base', 'plane', 'pole', 'purg', 'hrono', 'amkary'])
    n = rng.choice([4, 6, 8, 12])
    for seed in range(1, 5):
        log = []
        st, P = bb_full.run_game(seed, n, log=log, situation=sit, cfg=cfg)
        checked += 1
        if not (1 <= st['end'] <= 40): fails.append((combo, seed, 'end range'))
        if st['alive'] != len([p for p in P if p['alive'] and not p['limbo']]): fails.append((combo, seed, 'alive mismatch'))
        if any(p['or_'] < 0 for p in P): fails.append((combo, seed, 'negative OR'))
        if cfg['hand_limit'] and any(sum(len(l) for l in p['hand'].values()) > cfg['hand_limit'] for p in P):
            fails.append((combo, seed, 'hand over limit'))   # B15/№7: рука никогда не превышает потолок
        if cfg.get('draft'):   # B16/№9: при драфте личных раскрытых нет, захватов не больше успехов «add»
            if any(p['rev'] for p in P): fails.append((combo, seed, 'rev non-empty under draft'))
            if st['draft_takes'] > st['rpds_types'].get('add', 0): fails.append((combo, seed, 'draft takes > add'))
        if any(v[0] < 0 for p in P for v in p.get('grudge', {}).values()): fails.append((combo, seed, 'negative grudge'))   # №14/B25
        if not (cfg.get('grudge') or cfg.get('grudge_window')) and (st['grudge_revenge'] or st['grudge_marked'] or st['grudge_faded']):
            fails.append((combo, seed, 'grudge behaviour while OFF'))   # №14/B25: OFF — поведение не просачивается
        if cfg['harvest_mode'] == 'off' and st['harvests']: fails.append((combo, seed, 'harvest in off mode'))
        if cfg['harvest_mode'] == 'max2' and st['harvests'] > 2: fails.append((combo, seed, 'harvest>2 in max2'))
        if cfg['harvest_mode'] == 'off_after_death':
            fd = st['first_death'] or 99
            for c, d, h, al in st['cycle_sum']:
                if h and c > fd: fails.append((combo, seed, f'harvest after first death c{c}'))
        bad = validate.check_log(log, st, rev_cap=cfg['reveal'])
        if bad: fails.append((combo, seed, bad[:2]))
print(f'fuzz: конфигураций 60 × 4 партии = {checked} прогонов; НАРУШЕНИЙ: {len(fails)}')
for f_ in fails[:8]: print('  ', f_)
