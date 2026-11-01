# -*- coding: utf-8 -*-
"""B13: снимки состояний игроков для HTML-вьюера партии (п.21 меню).

Три вставки в bb_full.py, все под гардом `if st.get('snap') is not None` — по умолчанию
ключ отсутствует, ветка мертва, ГСЧ не тратится, лог не меняется (baseline бит-в-бит).

Протокол: assert на точное совпадение целей замен → замена → запись файла только в конце.
После: ast.parse + validate.py + fuzz_test.py + базовая партия seed 777/N8/plane.
Usage: python3 patch_b13_snap.py
"""
import ast, sys

FN = 'bb_full.py'
src = open(FN, encoding='utf-8').read()
orig = src

# ---- вставка 1: начальное состояние (c=0) после раздачи рук/пактов ----
A_OLD = """    S = n // 2
    if situation == 'pole': S = 1
    if situation == 'purg': S = max(1, rng.randint(1, n) - 2)   # HOUSE: W = dN − 2
"""
A_NEW = """    S = n // 2
    if situation == 'pole': S = 1
    if situation == 'purg': S = max(1, rng.randint(1, n) - 2)   # HOUSE: W = dN − 2
    if SNAP is not None: SNAP.append((0, _snap(P)))   # B13: снимок старта (для HTML-вьюера, п.21)
"""

# ---- вставка 2: конец цикла (перед всеми break-проверками) ----
B_OLD = """        st['cycle_sum'].append((c, cd, st['harvests'] - hb, len(alive())))
"""
B_NEW = """        st['cycle_sum'].append((c, cd, st['harvests'] - hb, len(alive())))
        if SNAP is not None: SNAP.append((c, _snap(P)))   # B13: снимок на конец цикла
"""

# ---- вставка 3: финал самолёта рвёт цикл до cycle_sum ----
C_OLD = """                    say(f'  🎲 финал самолёта: P{v[\"seat\"]}')
                    death(v, 'forced', 'plane')
            st['end'] = c; break
"""
C_NEW = """                    say(f'  🎲 финал самолёта: P{v[\"seat\"]}')
                    death(v, 'forced', 'plane')
            if SNAP is not None: SNAP.append((c, _snap(P)))   # B13: снимок перед досрочным финалом
            st['end'] = c; break
"""

# ---- вставка 4: хелпер _snap + глобальный держатель SNAP (рядом с ARCH_KEYS) ----
D_OLD = """ARCH_KEYS = list(ARCH)
AGENDAS = ['secret_kill', 'sabotage_heal', 'protect_one', 'hidden_hoard']
"""
D_NEW = """ARCH_KEYS = list(ARCH)
AGENDAS = ['secret_kill', 'sabotage_heal', 'protect_one', 'hidden_hoard']

# --- B13 (п.21 HTML-вьюер): необязательный приёмник снимков состояний. ---
# bb_html подставляет сюда список перед прогоном и забирает его обратно; в обычном
# режиме SNAP is None — все ветки снимков мертвы, ГСЧ не тратится, лог не меняется.
SNAP = None
SNAP_KEYS = ('seat', 'alive', 'or_', 'lives', 'tokens', 'dead_c', 'revived', 'kills', 'heal',
             'limbo', 'frozen', 'lethal', 'is_doll', 'no_revive', 'spec_used', 'prof_used',
             'used_rpd', 'exch', 'spec_i', 'prof', 'prof_name', 'team', 'bonus', 'shield',
             'reflect', 'pustoe', 'save_ally', 'demon', 'pact', 'is_traitor', 'traitor_target',
             'rev_cycle', 'rev_cnt', 'dealt_w', 'dealt_k', 'gained', 'heals_done', 'hold_hc')

def _snap(P):
    \"\"\"Компактный слепок партии: (профессии/архетипы/повестки + список состояний мест).\"\"\"
    meta = [[p['seat'], p.get('prof_name') or '', p['pers'].get('arch') or '',
             p['pers'].get('agenda') or '', list(p.get('archs') or [])] for p in P]
    rows = [{k: p.get(k) for k in SNAP_KEYS} for p in P]
    return dict(meta=meta, rows=rows)
"""

PATCHES = [('A: снимок старта', A_OLD, A_NEW), ('B: снимок конца цикла', B_OLD, B_NEW),
           ('C: снимок финала самолёта', C_OLD, C_NEW), ('D: хелпер _snap/SNAP', D_OLD, D_NEW)]

for name, old, new in PATCHES:
    cnt = src.count(old)
    assert cnt == 1, f'{name}: цель найдена {cnt} раз (нужно ровно 1)'
    assert new not in src, f'{name}: замена уже применена'
    src = src.replace(old, new)

assert src != orig, 'файл не изменился'
ast.parse(src)          # синтаксис до записи
open(FN, 'w', encoding='utf-8').write(src)
print(f'OK: {FN} пропатчен (B13, {len(PATCHES)} вставки), +{len(src) - len(orig)} байт')
for name, _, _ in PATCHES:
    print('  ✓', name)
