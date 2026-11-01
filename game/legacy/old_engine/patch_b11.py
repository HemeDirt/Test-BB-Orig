# -*- coding: utf-8 -*-
"""Патч B11: №22 абляция подсистем (ablate) + №8-TEST дорожающее воскрешение (revive_esc).
Протокол: все замены проверяются assert-ом; файл пишется только в конце."""
import io
p = 'bb_full.py'
src = io.open(p, encoding='utf-8').read()
reps = []
def rep(old, new, n=1):
    global src
    assert src.count(old) == n, f'MISS ({src.count(old)} != {n}): {old[:70]!r}'
    src = src.replace(old, new)
    reps.append(old[:50])

# P1: конфиги
rep("""             random_outcome=False)  # исход РПД/РПДС выбирается равномерно случайно вместо полос кубика""",
    """             random_outcome=False,  # исход РПД/РПДС выбирается равномерно случайно вместо полос кубика
             ablate=None,      # №22 абляция: 'spec'|'prof'|'shad'|'exch'|'traits'|'all' — подсистема выключается
             revive_esc=False) # №8-TEST: воскрешение за жетоны дорожает +1 за каждое воскрешение (HOUSE, только тесты)""")

# P2: блоки абляции после настройки колод
rep("""    exch = DECK['обмен'][:]; rng.shuffle(exch)
    apool = (C['arch_pool'] or ARCH_KEYS)[:]; rng.shuffle(apool)""",
    """    exch = DECK['обмен'][:]; rng.shuffle(exch)
    ABL = {'spec', 'prof', 'shad', 'exch', 'traits'} if C['ablate'] == 'all' else ({C['ablate']} if C['ablate'] else set())
    if 'traits' in ABL: decks = {k: [] for k in CATS}   # №22+п.7: бытовые колоды аблируем одной группой
    if 'shad' in ABL: shad, sh_tags = [], []
    if 'exch' in ABL: exch = []
    apool = (C['arch_pool'] or ARCH_KEYS)[:]; rng.shuffle(apool)""")

# P3: раздача руки — безопасно при пустых колодах
rep("""        hand0 = {} if C['mode'] == 'rpds_economy' else {k: [decks[k].pop()] for k in CATS}""",
    """        hand0 = {} if C['mode'] == 'rpds_economy' else {k: ([decks[k].pop()] if decks[k] else []) for k in CATS}""")

# P4/P5: раздача профессии и спецкарты с учётом абляции
rep("""                      prof=profs[i % len(profs)], prof_name=profs[i % len(profs)].split(' — ')[0],
                      spec_i=spec_order[i % len(spec_order)], exch=None, tokens=0, heal=0,""",
    """                      prof=('— (абляция)' if 'prof' in ABL else profs[i % len(profs)]),
                      prof_name=('—' if 'prof' in ABL else profs[i % len(profs)].split(' — ')[0]),
                      spec_i=(None if 'spec' in ABL else spec_order[i % len(spec_order)]), exch=None, tokens=0, heal=0,""")

# P6: гейт spec_phase (None = спецкарты аблированы)
rep("""        if p['spec_turn'] or p['spec_used'] or rng.random() > p['pers']['spec_p'] * .55: return   # B10: темп спецкарт""",
    """        if p['spec_i'] is None or p['spec_turn'] or p['spec_used'] or rng.random() > p['pers']['spec_p'] * .55: return   # B10 темп; None = абляция""")

# P7: spec_cycle не возвращает спецкарты при абляции
rep("""        if C['spec_cycle']:
            for p in alive():""",
    """        if C['spec_cycle'] and 'spec' not in ABL:
            for p in alive():""")

# P8: лестница цены воскрешения (№8-TEST)
rep("""            if g.get('no_revive') or not wish:
                pass
            elif g['tokens'] >= 6 and rng.random() < pr and g['dead_c'] is not None:
                g['tokens'] -= 6; g['alive'] = True; g['or_'] = 0; g['revived'] = True; st['revives'] += 1
                say(f'  ✝ P{g["seat"]} восстаёт за 6 жетонов')""",
    """            price = 6 + (st['revives'] if C['revive_esc'] else 0)   # №8-TEST HOUSE: лестница цены
            if g.get('no_revive') or not wish:
                pass
            elif g['tokens'] >= price and rng.random() < pr and g['dead_c'] is not None:
                g['tokens'] -= price; g['alive'] = True; g['or_'] = 0; g['revived'] = True; st['revives'] += 1
                say(f'  ✝ P{g["seat"]} восстаёт за {price} жетонов')""")

io.open(p, 'w', encoding='utf-8').write(src)
print('OK, замен:', len(reps))
for r in reps: print(' -', r)
