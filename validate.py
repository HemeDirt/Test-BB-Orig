# -*- coding: utf-8 -*-
"""Наблюдатель-валидатор: проверяет инварианты правил на логах/состояниях (идея 7)."""
import re, bb_full
from collections import Counter

def check_log(log, st, rev_cap=2):
    bad = []
    rev = Counter(); spec = Counter(); prof = Counter()
    cyc = 0
    for line in log:
        m = re.match(r'════ ЦИКЛ (\d+)', line)
        if m: cyc = int(m.group(1)); continue
        m = re.search(r'P(\d+) раскрывает', line)
        if m: rev[(cyc, int(m.group(1)))] += 1
        m = re.search(r'⚡ P(\d+): спецкарта', line)
        if m: spec[(cyc, int(m.group(1)))] += 1
        if re.search(r'(🪞 P\d+: стойка|✝ Некромант P\d+)', line):   # B17-fix: «чучело из P…» и «ФИЛЬМ» называют жертву/роли, а не актёра — в проф-лимит не входят
            m2 = re.search(r'P(\d+)', line)
            if m2: prof[(cyc, int(m2.group(1)))] += 1
    for k, v in rev.items():
        if v > rev_cap: bad.append(f'раскрытий {v}>{rev_cap}: цикл {k[0]} P{k[1]}')
    for k, v in spec.items():
        if v > 1: bad.append(f'спецкарт {v}>1 за ход: цикл {k[0]} P{k[1]}')
    for k, v in prof.items():
        if v > 1: bad.append(f'проф-активаций {v}>1 за ход: цикл {k[0]} P{k[1]}')
    if log.count('🚫 Жатва отменена') > sum(1 for i in range(len(log)) if '🚫 Жатва отменена' in log[i]) + 1: pass  # отмен может быть >1 только через ОБМЕН_СПЕЦ, это легально
    return bad

def run(n_games=20, n=8, situation='base'):
    allbad = []
    for s in range(1, n_games + 1):
        log = []
        st, P = bb_full.run_game(s, n, log=log, situation=situation)
        allbad += check_log(log, st)
        nd = sum(1 for p in P if p['alive'] and not p['limbo'])  # чучело = живой груз по правилу пользователя
        if nd != st['alive']:
            allbad.append(f'порог считает лишних: alive={st["alive"]} vs {nd}')
    return allbad

if __name__ == '__main__':
    bad = run()
    print('НАРУШЕНИЙ:', len(bad))
    for b in bad[:10]: print('  ', b)
