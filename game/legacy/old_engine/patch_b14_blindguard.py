# -*- coding: utf-8 -*-
"""B14: аварийный гард «слепого убийства» при пустом столе + расширение фазза переключателями.

НАЙДЕНО прогоном №25 (tornado): blind_kill, N=8, seed 45, base — стол вымирает внутри хода
(P7 убил себя вслепую → P6 умер по связке), а цикл РПДИ продолжает выбирать действие и падает
на rng.choice(alive()) с пустым списком. Единственное падение на 5300 партий всех вариантов №25.

Правка ТОЧЕЧНАЯ: семантику «мёртвый игрок доигрывает ход» НЕ трогаем (в базе это 268 случаев
на 600 партий — изменение сломало бы канонический baseline и требует отдельного решения пользователя).
Гард срабатывает только когда живых нет вообще → при blind_kill=False (канон) ветка недостижима,
baseline бит-в-бит сохраняется.

Запуск: python3 patch_b14_blindguard.py   (файлы пишутся только после всех assert'ов)
"""
import hashlib, io, sys

CORE = 'bb_full.py'
FUZZ = 'fuzz_test.py'

src = io.open(CORE, encoding='utf-8').read()
fz = io.open(FUZZ, encoding='utf-8').read()

# ── 1. гард слепого убийства ────────────────────────────────────────────
OLD = """                elif a == 'kill' and C['blind_kill']:
                    t = rng.choice(alive())  # вслепую, включая себя
"""
NEW = """                elif a == 'kill' and C['blind_kill']:
                    lv = alive()
                    if not lv:  # B14: стол вымер прямо во время хода — выбирать некого
                        say('  🙈 слепое убийство: живых нет, цель не выбирается')
                        break
                    t = rng.choice(lv)  # вслепую, включая себя
"""
assert src.count(OLD) == 1, f'цель №1 не найдена однозначно: {src.count(OLD)}'
src = src.replace(OLD, NEW)

# ── 2. фазз: случайные переключатели (чтобы этот класс багов ловился сам) ─
OLD_F = """    cfg = dict(harvest_mode=rng.choice(MODES), or_death=rng.choice([2, 3, 4, 7]),
               reveal=rng.choice([1, 2, 3]), dice=rng.choice([D20, D6]), fear=rng.choice([True, False]),
               mode=rng.choice(['std', 'rpds_economy']))
"""
NEW_F = """    TOGGLES = ['blind_kill', 'queue_reverse', 'traitor', 'spec_cycle', 'escalation', 'pressure',
               'or_noise', 'crit_price', 'pacifist_c1', 'random_outcome', 'revive_esc']
    cfg = dict(harvest_mode=rng.choice(MODES), or_death=rng.choice([2, 3, 4, 7]),
               reveal=rng.choice([1, 2, 3]), dice=rng.choice([D20, D6]), fear=rng.choice([True, False]),
               mode=rng.choice(['std', 'rpds_economy']),
               harvest_pick=rng.choice(['random', 'leader']), lives=rng.choice([1, 1, 2]),
               rpds=rng.choice([0, 1, 2]), rpdi=rng.choice([0, 1, 2]), agenda_p=rng.choice([0, .25, .5]))
    for t in TOGGLES:            # B14: каждый переключатель случайно вкл/выкл
        if rng.random() < .35: cfg[t] = True
"""
assert fz.count(OLD_F) == 1, f'цель №2 не найдена однозначно: {fz.count(OLD_F)}'
fz = fz.replace(OLD_F, NEW_F)

io.open(CORE, 'w', encoding='utf-8').write(src)
io.open(FUZZ, 'w', encoding='utf-8').write(fz)
print('B14 наложено:', CORE, hashlib.sha256(src.encode()).hexdigest()[:12], '|', FUZZ,
      hashlib.sha256(fz.encode()).hexdigest()[:12])

# ── 3. самопроверка: аварийный сид теперь проходит ───────────────────────
sys.path.insert(0, '.')
import importlib, bb_full
importlib.reload(bb_full)
st, P = bb_full.run_game(45, 8, log=None, situation='base', cfg=dict(blind_kill=True))
print(f'проверка seed 45/N8/blind_kill: end {st["end"]}, смертей {st["deaths"]}, живых {st["alive"]} — ОК')
assert 1 <= st['end'] <= 40
