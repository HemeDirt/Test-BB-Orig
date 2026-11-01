#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Быстрая статистика: python3 tools/batch_stats.py [число_партий=100] [--start-seed N]
Считает партии через единый движок game_sim.play_game() — без subprocess, ~1000 партий в секунду."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import game_sim as gs

n = int(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 100
start = 1
for a in sys.argv[1:]:
    if a.startswith('--start-seed'): start = int(a.split('=')[1]) if '=' in a else int(sys.argv[sys.argv.index(a)+1])

from collections import Counter
rows = []
for i in range(n):
    res = gs.play_game(start + i)
    st = res['state']
    sc = int(gs.score_line().split()[0].split('=')[1])
    rows.append((sc, st['first_death_cycle'], st['end_cycle'] or 99, st['deaths'],
                 st['harvest_fired'], st['bet_hits'], st['token_revive'], st['spec_revive']))

import statistics as s
print(f"Партий: {n} (seeds {start}..{start+n-1})")
print(f"SCORE: среднее {s.mean(r[0] for r in rows):.2f}, медиана {s.median(r[0] for r in rows)}")
print(f"Конец цикла: {dict(sorted(Counter(r[2] for r in rows).items()))}")
print(f"Первая смерть: {dict(sorted(Counter(r[1] for r in rows).items()))}")
print(f"Жатва: {sum(r[4] for r in rows)/n:.0%} | Ставки призраков бьют: {sum(1 for r in rows if r[5]>0)/n:.0%}"
      f" | Воскрешение жетонами: {sum(r[6] for r in rows)/n:.0%} | Спец-воскрешение: {sum(r[7] for r in rows)/n:.0%}")
print(f"Средне смертей за партию: {s.mean(r[3] for r in rows):.2f}")
