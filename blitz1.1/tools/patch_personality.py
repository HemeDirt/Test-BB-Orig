# -*- coding: utf-8 -*-
"""Пересадка личностей ботов (архетипы B-линии + репутация B21 + тильт B22 + обиды B25)
в рабочую игру blitz/src/game_sim.py. Источник знаний — архив main_backup (НЕ трогаем его).
Протокол: точные якоря, assert count==1, ast.parse до записи."""
import io, ast

PATH = 'src/game_sim.py'
src = io.open(PATH, encoding='utf-8').read()

def rep(old, new):
    global src
    n = src.count(old)
    assert n == 1, f"anchor count={n}: {old[:60]!r}"
    src = src.replace(old, new)

# ---------- 1. Модуль личности (перед play_game) ----------
rep(
"# --- оптимизация процесса: партия вызывается как функция, а не через main()+sys.argv ---",
'''# ==== ЛИЧНОСТИ БОТОВ (пересажено из клада main_backup: bb_full.py + патчи B21/B22/B25) ====
# 12 архетипов: вектор (агрессия/помощь/нейтралитет/театр/воровство/хаос) + личный шум ±30%
ARCH = {
 'aggr':     dict(aggr=.70, help=.02, neut=.08, theat=.05, thief=.10, chaos=.05),
 'hoard':    dict(aggr=.10, help=.05, neut=.35, theat=.00, thief=.50, chaos=.00),
 'actor':    dict(aggr=.15, help=.00, neut=.10, theat=.65, thief=.10, chaos=.00),
 'manip':    dict(aggr=.25, help=.00, neut=.15, theat=.20, thief=.40, chaos=.00),
 'team':     dict(aggr=.30, help=.40, neut=.15, theat=.00, thief=.00, chaos=.00),
 'turtle':   dict(aggr=.05, help=.25, neut=.60, theat=.00, thief=.05, chaos=.00),
 'gambler':  dict(aggr=.35, help=.00, neut=.05, theat=.10, thief=.10, chaos=.40),
 'chaos':    dict(aggr=.30, help=.00, neut=.00, theat=.25, thief=.15, chaos=.30),
 'medic':    dict(aggr=.02, help=.80, neut=.10, theat=.00, thief=.00, chaos=.00),
 'marauder': dict(aggr=.25, help=.00, neut=.10, theat=.00, thief=.65, chaos=.00),
 'star':     dict(aggr=.15, help=.00, neut=.05, theat=.70, thief=.05, chaos=.05),
 'lurker':   dict(aggr=.05, help=.10, neut=.80, theat=.00, thief=.05, chaos=.00)}
ARCH_RU = {'aggr':'Агрессор','hoard':'Копитель','actor':'Актёр','manip':'Манипулятор',
 'team':'Командный','turtle':'Черепаха','gambler':'Азартный','chaos':'Хаотик',
 'medic':'Медик','marauder':'Мародёр','star':'Звезда','lurker':'Скрытень'}
ARCH_KEYS = list(ARCH)

def personality(rng, arch):
    v = {k: max(.01, val * rng.uniform(.7, 1.3)) for k, val in ARCH[arch].items()}
    s = sum(v.values())
    v = {k: round(val / s, 3) for k, val in v.items()}
    v['arch'] = arch
    return v

# Коэффициенты из патчей (выбраны «на глаз», НЕ тюнились — как завещано в клады)
REP_BIAS = 0.18                      # B21: clamp(1 − 0.18·rep, 0.25…2.5)
REP_MIN, REP_MAX = 0.25, 2.5
GR_DECAY, GR_VENG, GR_BIAS = 0.8, 1.0, 0.45   # B25: долгая память обид
TILT_HOT, TILT_COLD = 0.25, -0.25             # B22: порог темперамента

# --- оптимизация процесса: партия вызывается как функция, а не через main()+sys.argv ---''')

# ---------- 2. setup(): слова личности + случайный состав архетипов ----------
rep(
"""                 immune=0, no_rpds=False, no_target=False, skip_reveal=False, buff=0,
                 debuff=False, died_cycle=None, resurrected=False, kills=0, dark_pen=0)
        p['or'] = 0
        P.append(p)""",
"""                 immune=0, no_rpds=False, no_target=False, skip_reveal=False, buff=0,
                 debuff=False, died_cycle=None, resurrected=False, kills=0, dark_pen=0,
                 pers=None, rep={}, grudge={}, tilt_until=0)
        p['or'] = 0
        P.append(p)
    # ЛИЧНОСТЬ: случайный состав архетипы раздаются без повторов (8 из 12)
    archs = ARCH_KEYS[:]
    rng.shuffle(archs)
    for i, p in enumerate(P):
        p['pers'] = personality(rng, archs[i])""")

rep(
"""    STATE = dict(cycle=0,""",
"""    log("Личности ботов (случайный состав архетипов):")
    for p in P:
        v = p['pers']
        log(f"  P{p['seat']} {p['name']}: {ARCH_RU[v['arch']]} "
            f"(агр{v['aggr']:.2f} пом{v['help']:.2f} нейтр{v['neut']:.2f} "
            f"театр{v['theat']:.2f} воров{v['thief']:.2f} хаос{v['chaos']:.2f})")
    STATE = dict(cycle=0,""")

# ---------- 3. Помощники: гроссбух, обиды, тильт — перед pick_target ----------
rep(
"""def pick_target(p, need_dmg=False):
    cands = [q for q in alive_list() if q is not p and not q['no_target']]
    if not cands: cands = [q for q in alive_list() if q is not p]
    if not cands: return None
    if need_dmg:
        soft = [q for q in cands if q['or'] <= 1]
        if soft and STATE['cycle'] == 1: cands = soft
    return rng.choice(cands)""",
'''def rep_note(perp, victim, dw, personal=0.0):
    """B21/B25: публичный гроссбух мнений rep[x][s] + личная книга обид grudge.
    Только dict/int-операции, rng не трогает. Благо (dw>0) гасит обиду."""
    if perp is None: return
    for x in P:
        r = x.setdefault('rep', {})
        r[perp['seat']] = round(r.get(perp['seat'], 0.0) + dw, 3)
    if victim is not None and victim is not perp:
        rv = victim.setdefault('rep', {})
        rv[perp['seat']] = round(rv.get(perp['seat'], 0.0) + personal, 3)
        g = victim.setdefault('grudge', {})
        cur = g.get(perp['seat'], [0.0, 0])[0]
        if dw < 0:
            g[perp['seat']] = [round(cur + abs(personal or 0.5), 2), STATE['cycle']]
        elif dw > 0:
            g[perp['seat']] = [0.0, STATE['cycle']]

def grudge_eff(p, seat):
    """B25: обида затухает: сила × 0.8^(циклы с последней обиды), увядает ниже 0.05."""
    g = p.get('grudge', {}).get(seat)
    if not g or g[0] <= 0: return 0.0
    eff = g[0] * (GR_DECAY ** max(0, STATE['cycle'] - g[1]))
    return eff if eff >= 0.05 else 0.0

def tilt_trigger(p, src):
    """B22: собственный провал сдвигает поведение на цикл по темпераменту.
    temper = aggr + chaos − neut: ≥+0.25 вспышка (tilt_until>0), ≤−0.25 заморозка (<0)."""
    v = p['pers']
    temper = v['aggr'] + v['chaos'] - v['neut']
    c = STATE['cycle']
    if temper >= TILT_HOT:
        p['tilt_until'] = c + 1
        log(f"    ↯ ТИЛЬТ: {p['name']} ({ARCH_RU[v['arch']]}, горячий) вспыхивает после провала «{src}» — агрессия ↑ до цикла {c+1}")
    elif temper <= TILT_COLD:
        p['tilt_until'] = -(c + 1)
        log(f"    ↯ ТИЛЬТ: {p['name']} ({ARCH_RU[v['arch']]}, холодный) замыкается после провала «{src}» — уходит в оборону")
    else:
        log(f"    ↯ {p['name']} пережил провал «{src}» ровно (без тильта)")

def tilt_hot(p):
    return p['tilt_until'] > 0 and STATE['cycle'] <= p['tilt_until']

def tilt_cold(p):
    return p['tilt_until'] < 0 and STATE['cycle'] <= -p['tilt_until']

def pick_target(p, need_dmg=False):
    cands = [q for q in alive_list() if q is not p and not q['no_target']]
    if not cands: cands = [q for q in alive_list() if q is not p]
    if not cands: return None
    if need_dmg:
        soft = [q for q in cands if q['or'] <= 1]
        if soft and STATE['cycle'] == 1: cands = soft
    # B25: МЕсть — должник с живой обидой ≥ GR_VENG становится приоритетной целью
    debtors = [q for q in cands if grudge_eff(p, q['seat']) >= GR_VENG]
    if debtors:
        t = max(debtors, key=lambda q: grudge_eff(p, q['seat']))
        log(f"    💢 МЕСТЬ: {p['name']} помнит обиду — цель {t['name']} (долг {grudge_eff(p, t['seat']):.2f})")
        return t
    # B21+B25: взвешенный выбор — обида тянет цель, хорошая репутация отталкивает
    wts = []
    for q in cands:
        w = 1.0
        w *= min(REP_MAX, max(REP_MIN, 1 - REP_BIAS * q['rep'].get(p['seat'], 0.0)))
        w *= min(2.5, 1 + GR_BIAS * grudge_eff(p, q['seat']))
        wts.append(w)
    return rng.choices(cands, weights=wts)[0]''')

io.open(PATH, 'w', encoding='utf-8').write(src)
ast.parse(src)
print("stage A ok (личность + гроссбухи + месть/репутация в pick_target)")
