# -*- coding: utf-8 -*-
"""Матрица прогонов: ≤100 партий на конфигурацию. Usage: python3 run_matrix.py"""
import json, statistics, bb_full
from collections import Counter

SEEDS = range(1, 101)
def agg(rows, P_all):
    g = len(rows)
    ends = sorted(r['end'] for r in rows)
    causes = Counter(); acts = Counter()
    for r in rows: causes.update(r['causes']); acts.update(r['acts'])
    return dict(games=g, end=round(statistics.mean(ends), 2), p90=ends[int(.9 * g) - 1],
                deaths=round(statistics.mean(r['deaths'] for r in rows), 2),
                alive=round(statistics.mean(r['alive'] for r in rows), 2),
                harvest_pct=round(100 * sum(1 for r in rows if r['harvests']) / g),
                revive_pct=round(100 * sum(1 for r in rows if r['revives']) / g),
                stall_pct=round(100 * sum(1 for r in rows if r['stall']) / g),
                causes=dict(causes.most_common(4)), acts=dict(acts.most_common(5)))

RES = {}
def run(name, **kw):
    rows = []
    for s in SEEDS:
        st, P = bb_full.run_game(s, kw.get('n', 8), log=None, situation=kw.get('situation', 'base'), cfg=kw.get('cfg'))
        rows.append(st)
    RES[name] = agg(rows, None)
    a = RES[name]
    print(f'{name:22s} end~{a["end"]:5} p90={a["p90"]:2} deaths~{a["deaths"]:5} alive~{a["alive"]:4} '
          f'harv%={a["harvest_pct"]:3} rev%={a["revive_pct"]:3} stall%={a["stall_pct"]:3} | {a["causes"]}', flush=True)

for sit in ('base', 'plane', 'pole', 'purg', 'hrono', 'amkary'):
    run('sit_' + sit, situation=sit)
run('dth7', cfg=dict(or_death=7))
run('rpds_economy', cfg=dict(mode='rpds_economy', reveal=1))
for n in (4, 6, 8, 10, 12, 16, 20):
    run(f'N{n}', n=n)
run('peaceful', cfg=dict(arch_pool=['medic', 'turtle', 'lurker', 'hoard', 'team', 'actor'], agenda_p=.05))
run('base_ref', cfg=None)
json.dump(RES, open('matrix_results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('saved matrix_results.json')
