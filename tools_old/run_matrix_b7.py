# -*- coding: utf-8 -*-
"""Расширенная матрица B7: ≤100 партий на конфиг. Usage: python3 run_matrix_b7.py"""
import json, statistics, bb_full, multiprocessing as mp

def _w(a):
    s, n, sit, cfg = a
    st, P = bb_full.run_game(s, n, situation=sit, cfg=cfg)
    return st
from bb_core import D6
from collections import Counter

def ci(v):
    g = len(v); m = statistics.mean(v); sd = statistics.pstdev(v) or 0
    return round(m, 2), round(m - 1.96 * sd / g ** .5, 2), round(m + 1.96 * sd / g ** .5, 2)

def run(name, n=8, situation='base', cfg=None):
    causes = Counter(); acts = Counter(); extra = Counter()
    with mp.Pool(min(8, mp.cpu_count())) as pool:
        rows = pool.map(_w, [(s, n, situation, cfg) for s in range(1, 101)])
    for st in rows:
        causes.update(st['causes']); acts.update(st['acts'])
        extra['sniper_cond'] += sum(1 for c in st['conditions'] if c['type'] == 'sniper') or (1 if st['causes'].get('sniper') else 0)
        extra['demon'] += st['demon_acts']; extra['betray'] += st['betrayals']; extra['doll'] += st['dolls']
        extra['hc'] += st['hc_used']; extra['fun'] += st['acts'].get('fun', 0)
        extra['film'] += 1 if st['roles'] else 0
        for k, v in st['ghost_archs'].items(): extra['ghost_' + k] += v
    g = len(rows)
    e = ci([r['end'] for r in rows]); d = ci([r['deaths'] for r in rows])
    out = dict(name=name, n=n, situation=situation, end=e, end_p90=sorted(r['end'] for r in rows)[89],
               deaths=d, alive=round(statistics.mean(r['alive'] for r in rows), 2),
               harvest_pct=round(100 * sum(1 for r in rows if r['harvests']) / g),
               revive_pct=round(100 * sum(1 for r in rows if r['revives']) / g),
               stall_pct=round(100 * sum(1 for r in rows if r['stall']) / g),
               thr_hit_pct=round(100 * sum(1 for r in rows if r['thr_hit']) / g),
               causes=dict(causes.most_common(5)), acts=dict(acts.most_common(7)), extra=dict(extra))
    print(f'{name:14s} N{n:<2} {situation:7s} end={e[0]:.2f}[{e[1]:.2f}-{e[2]:.2f}] p90={out["end_p90"]:2} '
          f'deaths={d[0]:.2f} alive={out["alive"]:4} harv%={out["harvest_pct"]:3} rev%={out["revive_pct"]:3} '
          f'thr%={out["thr_hit_pct"]:3} | топ-причины {list(out["causes"].items())[:3]}', flush=True)
    return out

RES = []
for sit in ('base', 'plane', 'pole', 'purg', 'hrono', 'amkary'):
    RES.append(run('sit_' + sit, situation=sit))
RES.append(run('dth7', cfg=dict(or_death=7)))
RES.append(run('rpds_economy', cfg=dict(mode='rpds_economy', reveal=1)))
for n in (4, 6, 8, 10, 12, 16, 20):
    RES.append(run(f'N{n}', n=n))
for n in (4, 6, 8, 10, 12, 16):
    RES.append(run(f'D6_N{n}', n=n, cfg=dict(dice=D6)))
RES.append(run('neg_all', cfg=dict(arch_pool=['rampage', 'aggr', 'chaos', 'gambler', 'marauder', 'manip'])))
RES.append(run('pos_all', cfg=dict(arch_pool=['medic', 'team', 'loyal', 'unionist', 'turtle', 'hoard'])))
RES.append(run('harv_late', cfg=dict(harvest_mode='late')))
RES.append(run('harv_max2', cfg=dict(harvest_mode='max2')))
json.dump(RES, open('matrix_b7.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('saved matrix_b7.json')
