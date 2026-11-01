# -*- coding: utf-8 -*-
"""Эксперимент D6: оверлей поверх sim/sim_n.py БЕЗ правки ядра.

Заменяет таблицы А/Б/В и массовое действие на D6-версии (по карточке-вкладышу),
отключает модификаторы бросков и переброс Крупье. Конфигурации:
  base           — контроль (оригинальные таблицы D20);
  d6             — вариант D6 (лимит лечения сохранён);
  d6_healcap_off — вариант D6 плюс снятый лимит лечения (мягкий дом-вариант).

Usage: python3 run_d6_experiment.py [SEEDS]   (положить в корень проекта, рядом с sim/)
Выход: печать сравнительной таблицы + d6_results.json.
"""
import sys, os, json, statistics

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sim'))
import sim_n as S

SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 200
NS = (6, 8, 12, 16)

# --- originals (для возврата в base) ---
ORIG = dict(d20=S.d20, mod_roll=S.mod_roll, croupier=S.croupier_reroll,
            table_A=S.table_A, table_B=S.table_B, table_V=S.table_V, mass=S.mass_action)

def d6_roll():
    r = S.rng.randint(1, 6)
    S.STATE['rolls'][r] = S.STATE['rolls'].get(r, 0) + 1
    return r

def d6_table_A(p, roll, declared, target, kind='рпди'):
    S.log(f'    d6 = {roll} [таблица А, {declared}] (вариант D6)')
    if declared == 'УБИЙСТВО':
        if roll == 1:
            S.log('    ОТКАТ: атакующий умирает сам'); S.check_death(p, 'крит-провал собственного убийства', p['name'])
        elif roll == 2: S.wound(p, 1, 'свой провал')
        elif roll <= 4: S.log('    ничего не произошло')
        elif roll == 5: S.wound(target, 2, p['name'])
        else:
            S.log('    ПОЛНЫЙ УСПЕХ: цель умирает сразу'); p['kills'] += 1
            S.check_death(target, 'убийство', p['name'])
    else:
        if roll == 1: S.wound(p, 2, 'self')
        elif roll == 2: S.wound(p, 1, 'self')
        elif roll <= 4: S.log('    ничего не произошло')
        elif roll == 5: S.wound(target, 1, p['name'])
        else: S.wound(target, 2, p['name'])

def d6_table_B(p, roll, action, on_succ, on_fail, kind='рпди'):
    S.log(f'    d6 = {roll} [таблица Б, {action}] (вариант D6)')
    if roll >= 5: on_succ()
    elif roll <= 2: on_fail()
    else: S.log('    ничего не произошло (3–4)')

def d6_table_V(p, roll, action, on_succ, on_fail):
    S.log(f'    d6 = {roll} [таблица В, {action}] (вариант D6)')
    if roll >= 5: on_succ()
    elif roll <= 2: on_fail()
    else: S.log('    ничего не произошло (3–4)')

def d6_mass(p):
    cands = [q for q in S.alive_list() if q is not p and not q['no_target']]
    if len(cands) < 2: return False
    targets = S.rng.sample(cands, 2)
    roll = d6_roll()
    S.log(f'  P{p["seat"]}: МАССОВОЕ D6 против P{targets[0]["seat"]} и P{targets[1]["seat"]} — d6 = {roll}')
    if roll == 6:
        for t in targets: S.wound(t, 1, p['name'])
        S.log('    УСПЕХ массового: каждой цели +1 ОР')
    else:
        S.log('    ПРОВАЛ массового: +2 ОР атакующему')
        S.wound(p, 2, 'self')
    S.STATE['mass_count'] += 1
    return True

def set_d6(on):
    if on:
        S.d20 = d6_roll
        S.mod_roll = lambda p, roll, kind: roll
        S.croupier_reroll = lambda actor, roll, kind: roll
        S.table_A, S.table_B, S.table_V, S.mass_action = d6_table_A, d6_table_B, d6_table_V, d6_mass
    else:
        S.d20, S.mod_roll, S.croupier_reroll = ORIG['d20'], ORIG['mod_roll'], ORIG['croupier']
        S.table_A, S.table_B, S.table_V, S.mass_action = ORIG['table_A'], ORIG['table_B'], ORIG['table_V'], ORIG['mass']

def agg(rows):
    n = len(rows)
    pc = lambda k: round(100 * sum(1 for r in rows if r[k]) / n, 1)
    return dict(games=n,
                end=round(statistics.mean(r['end'] for r in rows), 2),
                deaths=round(statistics.mean(r['deaths'] for r in rows), 2),
                alive=round(statistics.mean(r['alive'] for r in rows), 2),
                harvest_pct=pc('harvests'), revive_pct=round(100 * sum(1 for r in rows if r['token_revive'] or r['spec_revive']) / n, 1),
                mass_pct=pc('mass'), stall_pct=pc('stall'), nat1_pct=pc('nat1'))

CONFIGS = [('base', False, {}), ('d6', True, {}), ('d6_healcap_off', True, {'healcap_off': True})]
out = {}
for name, is_d6, mods in CONFIGS:
    set_d6(is_d6)
    out[name] = {}
    for n in NS:
        rows = [S.run_game(s, n, 'base', mods) for s in range(1, SEEDS + 1)]
        out[name][str(n)] = agg(rows)
        a = out[name][str(n)]
        print(f'{name:15s} N={n:2d}: end~{a["end"]:5} deaths~{a["deaths"]:5} alive~{a["alive"]:5} '
              f'harv%={a["harvest_pct"]:5} rev%={a["revive_pct"]:5} mass%={a["mass_pct"]:5} stall%={a["stall_pct"]:4}', flush=True)
set_d6(False)
json.dump(out, open('d6_results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\nсохранено d6_results.json')
print('Сравнение base vs d6 (end):', {n: (out['base'][n]['end'], out['d6'][n]['end']) for n in map(str, NS)})
