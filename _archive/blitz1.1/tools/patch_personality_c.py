# -*- coding: utf-8 -*-
"""Этап C: характер определяет ДЕЙСТВИЯ (choose_rpdi) — мозг choose() из main_backup/bb_full.py.
Веса канонной таблицы цикла — база; личность их перекашивает; тильт докручивает окно.
+ строка личности в ходовой ленте. Протокол: якоря, assert==1, ast.parse."""
import io, ast

PATH = 'src/game_sim.py'
src = io.open(PATH, encoding='utf-8').read()

def rep(old, new):
    global src
    n = src.count(old)
    assert n == 1, f"anchor count={n}: {old[:60]!r}"
    src = src.replace(old, new)

# ---------- C1. Личностные веса вместо плоских ----------
rep(
"""def choose_rpdi(p, c):
    gs = ghosts()
    opts, wts = [], []
    if c == 1:""",
'''def choose_rpdi(p, c):
    """Выбор РПДИ: базовая таблица цикла × вектор личности × тильт (B22).
    Формула весов пересажена из choose() старой линии (main_backup/bb_full.py)."""
    gs = ghosts()
    v = p['pers']
    # множители тильта: горячая вспышка — атака↑ пропуск↓; заморозка — наоборот
    if tilt_hot(p):
        tm = dict(kill=1.35, wound=1.25, mass=1.2, skip=0.7, heal=1.0, steal=1.0, humiliate=1.0, marauder=1.0)
    elif tilt_cold(p):
        tm = dict(kill=0.75, wound=0.8, mass=0.8, skip=1.3, heal=1.15, steal=1.0, humiliate=1.0, marauder=1.0)
    else:
        tm = dict(kill=1.0, wound=1.0, mass=1.0, skip=1.0, heal=1.0, steal=1.0, humiliate=1.0, marauder=1.0)
    base_scale = sum(tm.values()) / len(tm)   # не раздуваем суммарный вес
    def W(act, base):
        pers_w = {
            'kill':      30 * v['aggr'] + 6 * v['chaos'],
            'wound':     26 * v['aggr'] + 10 * v['chaos'],
            'mass':      8 * v['aggr'] + 16 * v['chaos'],
            'heal':      30 * v['help'],
            'steal':     18 * v['thief'],
            'marauder':  18 * v['thief'],
            'humiliate': 26 * v['theat'],
            'skip':      18 * v['neut'],
        }[act]
        return max(0.0, base * (pers_w / 15.0) * tm[act])
    opts, wts = [], []
    if c == 1:''')

rep(
"""    if p['spec'][0] == 'extra':
        pass
    return rng.choices(opts, weights=wts)[0]""",
"""    # личностная перекоСКА базовых весов цикла
    wts = [W(o, w_) for o, w_ in zip(opts, wts)]
    if sum(wts) <= 0: return 'skip'
    act = rng.choices(opts, weights=wts)[0]
    if tilt_hot(p) and act in ('kill', 'wound', 'mass'):
        log(f"    ↯ на взводе ({p['name']}): {ARCH_RU[v['arch']]} бьёт злее")
    if tilt_cold(p) and act == 'skip':
        log(f"    ↯ в глухой обороне ({p['name']}): {ARCH_RU[v['arch']]} пропускает удар")
    return act""")

# ---------- C2. Строка личности в ленте хода ----------
rep(
"""    log(f"  ——— P{p['seat']} {p['name']} ({p['prof'][0]}), ОР={p['or']} ———")""",
"""    tl = ' ↯взвод' if tilt_hot(p) else (' ↯оборона' if tilt_cold(p) else '')
    log(f"  ——— P{p['seat']} {p['name']} ({p['prof'][0]}, {ARCH_RU[p['pers']['arch']]}{tl}), ОР={p['or']} ———")""")

io.open(PATH, 'w', encoding='utf-8').write(src)
ast.parse(src)
print("stage C ok (характер выбирает действия, тильт двигает веса)")
