# -*- coding: utf-8 -*-
"""Этап B: личность влияет на действия (choose_rpdi), события пишутся в гроссбух
(rep_note), собственные провалы триггерят тильт (tilt_trigger). Источник коэффициентов —
main_backup/bb_full.py choose() + патчи B21/B22/B25. Протокол: якоря, assert==1, ast.parse."""
import io, ast

PATH = 'src/game_sim.py'
src = io.open(PATH, encoding='utf-8').read()

def rep(old, new):
    global src
    n = src.count(old)
    assert n == 1, f"anchor count={n}: {old[:60]!r}"
    src = src.replace(old, new)

# ---------- B1. table_A: крит-провалы → тильт; успех/урон → гроссбух ----------
rep(
"""    if declared == 'УБИЙСТВО':
        if eff <= 4:
            log(f"    КРИТ-ПРОВАЛ: удар возвращается в автора")
            check_death(p, 'крит-провал собственного убийства', p['name'])
        elif eff <= 8: wound(p, 1, 'свой провал'); 
        elif eff <= 12: log(f"    ничего не произошло")
        elif eff <= 16: wound(target, 2, p['name'])
        else:
            log(f"    КРИТ: цель умирает сразу")
            target['or'] = max(target['or'], 0)
            p['kills'] += 1
            check_death(target, 'крит убийства', p['name'])
    else:
        if eff <= 4:
            log(f"    КРИТ-ПРОВАЛ: +2 ОР автору")
            wound(p, 2, 'self')
        elif eff <= 8: wound(p, 1, 'self')
        elif eff <= 12: log(f"    ничего не произошло")
        elif eff <= 16: wound(target, 1, p['name'])
        else:
            log(f"    КРИТ: +2 ОР цели")
            wound(target, 2, p['name'])""",
"""    if declared == 'УБИЙСТВО':
        if eff <= 4:
            log(f"    КРИТ-ПРОВАЛ: удар возвращается в автора")
            rep_note(p, target, -1.5, -1.5)   # B21: попытка убийства — публичный вред
            tilt_trigger(p, 'крит-провал убийства')   # B22
            check_death(p, 'крит-провал собственного убийства', p['name'])
        elif eff <= 8:
            rep_note(p, target, -0.7, -0.7)
            tilt_trigger(p, 'откат убийства')
            wound(p, 1, 'свой провал')
        elif eff <= 12: log(f"    ничего не произошло")
        elif eff <= 16:
            rep_note(p, target, -0.7, -0.7)
            wound(target, 2, p['name'])
        else:
            log(f"    КРИТ: цель умирает сразу")
            rep_note(p, target, -1.5, -1.5)
            p['kills'] += 1
            check_death(target, 'крит убийства', p['name'])
            target['or'] = max(target['or'], 0)
    else:
        if eff <= 4:
            log(f"    КРИТ-ПРОВАЛ: +2 ОР автору")
            rep_note(p, target, -0.7, -0.7)
            tilt_trigger(p, 'крит-провал ранения')
            wound(p, 2, 'self')
        elif eff <= 8:
            rep_note(p, target, -0.7, -0.7)
            tilt_trigger(p, 'откат ранения')
            wound(p, 1, 'self')
        elif eff <= 12: log(f"    ничего не произошло")
        elif eff <= 16:
            rep_note(p, target, -0.7, -0.7)
            wound(target, 1, p['name'])
        else:
            log(f"    КРИТ: +2 ОР цели")
            rep_note(p, target, -0.7, -0.7)
            wound(target, 2, p['name'])""")

# ---------- B2. table_B/table_V: ПРОВАЛ своей проверки → тильт ----------
rep(
"""    eff = croupier_reroll(p, eff, kind)
    if nat == 20 or (nat != 1 and eff >= 15): on_succ()
    elif nat == 1 or eff <= 10: on_fail()
    else: log(f"    ничего не произошло (11–14)")""",
"""    eff = croupier_reroll(p, eff, kind)
    if nat == 20 or (nat != 1 and eff >= 15): on_succ()
    elif nat == 1 or eff <= 10:
        tilt_trigger(p, f'провал «{action}»')   # B22: FAIL любой своей проверки Б
        on_fail()
    else: log(f"    ничего не произошло (11–14)")""")

rep(
"""    if nat == 20 or (nat != 1 and eff >= 11): on_succ()
    elif nat == 1 or eff <= 9: on_fail()
    else: log(f"    ничего не произошло (10)")""",
"""    if nat == 20 or (nat != 1 and eff >= 11): on_succ()
    elif nat == 1 or eff <= 9:
        tilt_trigger(p, f'провал «{action}»')   # B22: FAIL своей проверки В
        on_fail()
    else: log(f"    ничего не произошло (10)")""")

# ---------- B3. Гроссбух в краже / лечении / унижении ----------
rep(
"""        p['hand'].setdefault(k, []).append(c)
        log(f"    УСПЕХ: {p['name']} забирает у {victim['name']} закрытую карту [{k}] «{c}»")""",
"""        p['hand'].setdefault(k, []).append(c)
        rep_note(p, victim, -0.4, -0.6)   # B21: кража — публичный вред
        log(f"    УСПЕХ: {p['name']} забирает у {victim['name']} закрытую карту [{k}] «{c}»")""")

rep(
"""        target['or'] = max(0, target['or'] - 1)
        target['heal_taken'] += 1
        log(f"    УСПЕХ: {target['name']} вылечен на 1 ОР → {target['or']}")""",
"""        target['or'] = max(0, target['or'] - 1)
        target['heal_taken'] += 1
        rep_note(p, target, +0.8, +0.8)   # B21: успешное лечение — благо
        log(f"    УСПЕХ: {target['name']} вылечен на 1 ОР → {target['or']}")""")

rep(
"""            target['revealed'].append((k, c))
            log(f"    УСПЕХ: {target['name']} от позора раскрывает [{k}] «{c}»")""",
"""            target['revealed'].append((k, c))
            rep_note(p, target, -0.4, -0.6)   # B21: унижение — публичный вред
            log(f"    УСПЕХ: {target['name']} от позора раскрывает [{k}] «{c}»")""")

# ---------- B4. Массовка: успех/провал ----------
rep(
"""    if eff >= 18:
        for t in targets: wound(t, 1, p['name'])
        log(f"    УСПЕХ массовки: каждой цели +1 ОР")
    else:
        log(f"    ПРОВАЛ массовки: обратный эффект — атакующему +2 ОР")
        wound(p, 2, 'self')""",
"""    if eff >= 18:
        for t in targets:
            rep_note(p, t, -0.5, -0.5)   # B21: массовка — каждой цели
            wound(t, 1, p['name'])
        log(f"    УСПЕХ массовки: каждой цели +1 ОР")
    else:
        log(f"    ПРОВАЛ массовки: обратный эффект — атакующему +2 ОР")
        tilt_trigger(p, 'провал массовки')   # B22: масс-провал
        wound(p, 2, 'self')""")

io.open(PATH, 'w', encoding='utf-8').write(src)
ast.parse(src)
print("stage B ok (события → гроссбух, провалы → тильт)")
