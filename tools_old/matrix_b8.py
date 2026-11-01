# -*- coding: utf-8 -*-
"""Матрица B8: новые режимы × N=4..20 (дуэли N=2), 100 партий/конфиг, parallel."""
import json, statistics, multiprocessing as mp
import bb_full
from collections import Counter

NS = (4, 6, 8, 10, 12, 16, 18, 20)
def _w(a):
    name, s, n, cfg = a
    st, P = bb_full.run_game(s, n, cfg=cfg)
    return name, st

CONFIGS = [(f'blind_N{n}', n, dict(blind_kill=True)) for n in NS] + \
          [(f'queue_rev_N{n}', n, dict(queue_reverse=True)) for n in NS] + \
          [(f'traitor_N{n}', n, dict(traitor=True)) for n in NS] + \
          [(f'harv_leader_N{n}', n, dict(harvest_pick='leader')) for n in NS] + \
          [(f'harv_escal_N{n}', n, dict(harvest_mode='escalate')) for n in NS] + \
          [(f'spec_cycle_N{n}', n, dict(spec_cycle=True)) for n in NS] + \
          [(f'no_rpds_N{n}', n, dict(rpds=0)) for n in NS] + \
          [('duel_lives3', 2, dict(lives=3)), ('duel_lives7', 2, dict(lives=7))]

if __name__ == '__main__':
    jobs = [(name, s, n, cfg) for name, n, cfg in CONFIGS for s in range(1, 101)]
    with mp.Pool(min(8, mp.cpu_count())) as pool:
        out = pool.map(_w, jobs)
    RES = {}
    for name, st in out:
        RES.setdefault(name, []).append(st)
    rows = []
    for name, sts in RES.items():
        g = len(sts); ends = sorted(r['end'] for r in sts)
        causes = Counter(); tw = sum(1 for r in sts if r.get('traitor_win'))
        for r in sts: causes.update(r['causes'])
        tc = sum(causes.values()) or 1
        row = dict(name=name, end=round(statistics.mean(ends), 2), p90=ends[int(.9 * g) - 1],
                   deaths=round(statistics.mean(r['deaths'] for r in sts), 2),
                   alive=round(statistics.mean(r['alive'] for r in sts), 2),
                   harv_pct=round(100 * sum(1 for r in sts if r['harvests']) / g),
                   rev_pct=round(100 * sum(1 for r in sts if r['revives']) / g),
                   stall_pct=round(100 * sum(1 for r in sts if r['stall']) / g),
                   traitor_win_pct=tw,
                   selfkill_pct=round(100 * causes['selfkill'] / tc),
                   harvest_share=round(100 * causes['harvest'] / tc),
                   harv_per_game=round(sum(r['harvests'] for r in sts) / g, 2),
                   spec_per_game=round(sum(r['spec_uses'] for r in sts) / g, 1))
        rows.append(row)
        print(f'{name:16s} end={row["end"]:5.2f} p90={row["p90"]:2} deaths={row["deaths"]:5} alive={row["alive"]:4} '
              f'harv%={row["harv_pct"]:3} harv/game={row["harv_per_game"]:4} rev%={row["rev_pct"]:3} stall%={row["stall_pct"]:2} '
              f'tw%={row["traitor_win_pct"]:2} selfkill%={row["selfkill_pct"]:2} spec/g={row["spec_per_game"]:4}', flush=True)
    json.dump(rows, open('matrix_b8.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('saved matrix_b8.json')
