# -*- coding: utf-8 -*-
"""№29: winrate архетипов по ситуациям — матрица 23×6.
100 партий (сиды 1..100) на ситуацию, N8, дефолтный cfg. Ключ — базовый архетип
pers['arch'] (не меняется за игру; подмешанные archs и призрачные роли не в счёт).
Победа = игрок жив на конец партии (в amkary — выжившая команда)."""
import json, statistics, bb_full
from collections import Counter, defaultdict

SEEDS = range(1, 101)
SITS = ('base', 'plane', 'pole', 'purg', 'hrono', 'amkary')
N = 8

OUT = {}
for sit in SITS:
    apps = Counter(); wins = Counter()
    ends = []; deaths = []
    for s in SEEDS:
        st, P = bb_full.run_game(s, N, log=None, situation=sit, cfg=None)
        ends.append(st['end']); deaths.append(st['deaths'])
        for p in P:
            a = p['pers']['arch']
            apps[a] += 1
            if p['alive']: wins[a] += 1
    tot_apps = sum(apps.values()); tot_wins = sum(wins.values())
    OUT[sit] = dict(
        games=len(SEEDS), end=round(statistics.mean(ends), 2),
        deaths=round(statistics.mean(deaths), 2),
        surv_rate=round(tot_wins / tot_apps, 3),          # базовая планка: доля выживших мест
        archs={a: dict(apps=apps[a], wins=wins[a],
                       wr=round(100 * wins[a] / apps[a], 1))
               for a in sorted(apps)})
    print(f'{sit:7s} end~{OUT[sit]["end"]:5} deaths~{OUT[sit]["deaths"]:5} '
          f'планка={100*OUT[sit]["surv_rate"]:.0f}% архетипов={len(apps)}', flush=True)

json.dump(OUT, open('winrate.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('saved winrate.json')

# сводка: лучший/худший относительно планки каждой ситуации
for sit in SITS:
    d = OUT[sit]; base = 100 * d['surv_rate']
    rank = sorted(d['archs'].items(), key=lambda kv: -kv[1]['wr'])
    top = [(a, v['wr'], v['apps']) for a, v in rank[:3]]
    bot = [(a, v['wr'], v['apps']) for a, v in rank[-3:]]
    print(f'{sit:7s} планка {base:.0f}% | ТОП {top} | НИЗ {bot}', flush=True)
