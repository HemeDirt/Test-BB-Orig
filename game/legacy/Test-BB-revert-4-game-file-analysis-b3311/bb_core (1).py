# -*- coding: utf-8 -*-
"""БЛИЦ БОЙ — параметризованное ядро печатной редакции (независимая пересборка, этап B1).
Всё изменяемое — параметры: грани кубика и полосы таблиц (D20/D6/любой), пороги ОР,
Жатва, экономика призраков, расписания. D6 = конфиг D6, а не отдельный код.
Карты-эффекты (профессии/спец/тени) в B1: счётчики + базовые ветви; полные эффекты = этап B2.
Usage: import bb_core; bb_core.run_game(seed, n, dice=bb_core.D6, situation='base')
"""
import json, random, os

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = json.load(open(os.path.join(HERE, 'deck_print.json'), encoding='utf-8'))
CATS = ['тело', 'разум', 'способности', 'инвентарь', 'история', 'знания', 'детали']

# ---- кубики и таблицы как данные: список (верхняя граница, эффект) ----
D20 = dict(faces=20, nat=True,
    tableA=[(4, 'DEATH_SELF', 'W2_SELF'), (8, 'W1_SELF', 'W1_SELF'), (12, 'NONE', 'NONE'),
            (16, 'W2_T', 'W1_T'), (20, 'DEATH_T', 'W2_T')],
    tableB=[(10, 'FAIL'), (14, 'NONE'), (20, 'SUCC')],
    tableV=[(9, 'FAIL'), (10, 'NONE'), (20, 'SUCC')],
    mass_thr=18, mass_other_thr=15, mass_fail_kill='DEATH_SELF')
D6 = dict(faces=6, nat=False,
    tableA=[(1, 'DEATH_SELF', 'W2_SELF'), (2, 'W1_SELF', 'W1_SELF'), (4, 'NONE', 'NONE'),
            (5, 'W2_T', 'W1_T'), (6, 'DEATH_T', 'W2_T')],
    tableB=[(2, 'FAIL'), (4, 'NONE'), (6, 'SUCC')],
    tableV=[(2, 'FAIL'), (4, 'NONE'), (6, 'SUCC')],
    mass_thr=6, mass_other_thr=5, mass_fail_kill='W2_SELF')

BASE = dict(or_death=3, heal_cap=1, reveal=2, rpds=1, rpdi=1, harvest=True, harvest_k=1,
            revive_cost=6, cycle_cap=40, marauder=True, exchange=True, anvil_always_kills=False)

def _band(tbl, r, i):
    for hi, *effs in tbl:
        if r <= hi:
            return effs[i] if len(effs) > 1 else effs[0]
    return tbl[-1][1] if len(tbl[-1]) == 2 else tbl[-1][-1]

def run_game(seed, n, dice=D20, situation='base', cfg=None):
    C = dict(BASE); C.update(cfg or {})
    rng = random.Random(seed)
    decks = {k: DECK[k][:] for k in CATS}
    for k in decks: rng.shuffle(decks[k])
    profs = DECK['профессии'][:]; rng.shuffle(profs)
    specs = DECK['спецкарты'][:]; rng.shuffle(specs)
    shad = DECK['тени'][:]; rng.shuffle(shad)
    exch = DECK['обмен'][:]; rng.shuffle(exch)
    P = []
    for i in range(n):
        P.append(dict(seat=i + 1, hand={k: [decks[k].pop()] for k in CATS}, rev=[], alive=True, or_=0,
                      prof=profs[i % len(profs)], spec=specs[i % len(specs)], exch=exch[i % len(exch)],
                      tokens=0, shadow=None, heal=0, dead_c=None, revived=False, kills=0,
                      team=i % 2, frozen=0, lethal=False, no_rpds=False, bonus=0,
                      uses=dict(prof=0, spec=0, shadow=0, exch=0)))
    S = n // 2
    if situation == 'pole': S = 1
    if situation == 'purg': S = rng.randint(1, n)
    thr = (10 if n < 10 else 20) if situation == 'hrono' else None
    st = dict(cycle=0, deaths=0, harvests=0, mass=0, nat1=False, nat20=False, first_death=None,
              end=None, revives=0, shadow_uses=0, spec_uses=0, prof_uses=0, exch_uses=0,
              stall=False, player_death=False, thr_hit=False, thr=thr)

    def alive(): return [p for p in P if p['alive']]
    def ghosts(): return [p for p in P if not p['alive']]
    def closed(p): return [(k, c) for k, l in p['hand'].items() for c in l]

    def roll():
        r = rng.randint(1, dice['faces'])
        if dice.get('nat'):
            if r == 1: st['nat1'] = True
            if r == dice['faces']: st['nat20'] = True
        return r

    def death(p, cause, src=''):
        if not p['alive']: return
        p['alive'] = False; p['dead_c'] = st['cycle']; st['deaths'] += 1
        if st['first_death'] is None: st['first_death'] = st['cycle']
        if cause != 'harvest': st['player_death'] = True
        if situation == 'hrono' and st['thr'] is not None:
            st['thr'] -= 1
            if rng.randint(1, 20) >= st['thr']: st['thr_hit'] = True

    def wound(p, amt, src=''):
        if not p['alive'] or p['frozen'] > 0: return False
        if p['lethal'] and amt > 0 and src not in ('self', 'harvest'):
            p['lethal'] = False; death(p, 'lethal', src); return True
        p['or_'] += amt
        if p['or_'] >= C['or_death']: death(p, 'wounds', src)
        return True

    def apply_A(eff, a, t):
        if eff == 'DEATH_SELF': death(a, 'selfkill', str(a['seat']))
        elif eff == 'W1_SELF': wound(a, 1, 'self')
        elif eff == 'W2_SELF': wound(a, 2, 'self')
        elif eff == 'W1_T': wound(t, 1, str(a['seat'])); 
        elif eff == 'W2_T': wound(t, 2, str(a['seat']))
        elif eff == 'DEATH_T': death(t, 'kill', str(a['seat'])); a['kills'] += 1

    def tableA(a, decl, t):
        r = roll()
        for hi, ke, we in dice['tableA']:
            if r <= hi: apply_A(ke if decl == 'kill' else we, a, t); return

    def tableBV(tbl, a):
        r = roll()
        for hi, eff in tbl:
            if r <= hi: return eff
        return tbl[-1][1]

    def reveal(p, k=1):
        for _ in range(k):
            cc = closed(p)
            if cc:
                k2, c = rng.choice(cc); p['hand'][k2].remove(c); p['rev'].append((k2, c))

    def act(a, kind, t=None):
        if kind == 'wound': tableA(a, 'wound', t)
        elif kind == 'kill': tableA(a, 'kill', t)
        elif kind == 'steal':
            res = tableBV(dice['tableB'], a)
            if res == 'SUCC' and closed(t):
                k, c = rng.choice(closed(t)); t['hand'][k].remove(c); a['hand'].setdefault(k, []).append(c)
            elif res == 'FAIL' and closed(a):
                k, c = rng.choice(closed(a)); a['hand'][k].remove(c); t['hand'].setdefault(k, []).append(c)
        elif kind == 'humiliate':
            res = tableBV(dice['tableB'], a)
            if res == 'SUCC': reveal(t)
            elif res == 'FAIL': reveal(a)
        elif kind == 'heal':
            if t['heal'] >= C['heal_cap']: return
            res = tableBV(dice['tableB'], a)
            if res == 'SUCC': t['or_'] = max(0, t['or_'] - 1); t['heal'] += 1
            elif res == 'FAIL': wound(a, 1, 'self')
        elif kind == 'marauder':
            gs = ghosts()
            if not gs: return
            g = rng.choice(gs)
            if closed(g) and tableBV(dice['tableB'], a) == 'SUCC':
                k, c = rng.choice(closed(g)); g['hand'][k].remove(c); a['hand'].setdefault(k, []).append(c)

    def mass(a):
        cands = [q for q in alive() if q is not a and q['frozen'] == 0]
        if situation == 'amkary' and rng.random() < 0.85:
            c2 = [q for q in cands if q['team'] != a['team']]
            if len(c2) >= 2: cands = c2
        if len(cands) < 2: return False
        ts = rng.sample(cands, 2); r = roll(); st['mass'] += 1
        if r >= dice['mass_thr']:
            for t in ts: wound(t, 1, str(a['seat']))
        else:
            wound(a, 2, 'self')
        return True

    def choose(c, gs):
        if c == 1: opts, w = ['humiliate', 'wound', 'steal', 'skip', 'heal'], [35, 25, 15, 20, 5]
        elif c == 2: opts, w = ['wound', 'kill', 'steal', 'humiliate', 'heal', 'skip'], [30, 25, 12, 13, 10, 10]
        elif c == 3: opts, w = ['wound', 'kill', 'steal', 'humiliate', 'heal', 'skip', 'marauder'], [18, 6, 12, 14, 12, 28, 10 if gs else 0]
        else: opts, w = ['wound', 'kill', 'steal', 'humiliate', 'heal', 'skip', 'marauder', 'mass'], [24, 16, 10, 10, 10, 15, 10 if gs else 0, 10]
        hurt = [q for q in alive() if q is not cur and q['or_'] >= 1 and q['heal'] < C['heal_cap']]
        if not hurt and 'heal' in opts: w[opts.index('heal')] = 0
        w = [max(0, x) for x in w]
        return rng.choices(opts, weights=w)[0] if sum(w) else 'skip'

    SH = dict(reveal=lambda g: reveal(rng.choice(alive())) if alive() else None,
              tok1=lambda g: g.__setitem__('tokens', g['tokens'] + 1),
              tok2=lambda g: g.__setitem__('tokens', g['tokens'] + 2),
              tok3=lambda g: g.__setitem__('tokens', g['tokens'] + 3),
              del_closed=lambda g: _del(g, False), del_open=lambda g: _del(g, True),
              close=lambda g: _close(g), plus1=lambda g: _bonus(g, 1), plus2=lambda g: _bonus(g, 2),
              minus1=lambda g: _bonus(g, -1), minus2=lambda g: _bonus(g, -2),
              give_rpd=lambda g: _bonus(g, 1), lethal=lambda g: _lethal(g),
              give_spec=lambda g: g.__setitem__('uses', dict(g['uses'], spec=g['uses']['spec'] + 1)))
    def _del(g, opened):
        lv = alive()
        if not lv: return
        q = rng.choice(lv)
        if opened and q['rev']: q['rev'].pop()
        elif not opened and closed(q):
            k, c = rng.choice(closed(q)); q['hand'][k].remove(c)
    def _close(g):
        lv = alive()
        if lv and rng.choice(lv)['rev']:
            q = rng.choice(lv); k, c = q['rev'].pop(); q['hand'].setdefault(k, []).append(c)
    def _bonus(g, d):
        lv = alive()
        if lv: rng.choice(lv)['bonus'] += d
    def _lethal(g):
        lv = alive()
        if lv: rng.choice(lv)['lethal'] = True

    SH_TAGS = {'reveal': 'reveal', 'tok2': 'tok2', 'del_closed': 'del_closed', 'tok1': 'tok1',
               'protect': None, 'swap': None, 'tok3': 'tok3', 'give_rpd': 'give_rpd',
               'give_spec': 'give_spec', 'out_turn': None, '+1': 'plus1', '+2': 'plus2',
               '-1': 'minus1', '-2': 'minus2', 'del_open': 'del_open', 'close': 'close',
               'cancel': None, 'last': None, 'lethal': 'lethal', 'no_rpds': None,
               'redirect': None, 'heal_remove': None}

    def turn(p, c):
        nonlocal cur
        cur = p
        if p['frozen'] > 0: p['frozen'] -= 1; return
        reveal(p, C['reveal'])
        rpds, rpdi = C['rpds'], C['rpdi'] + p['bonus']
        p['bonus'] = 0
        if p['no_rpds']: rpds = 0; p['no_rpds'] = False
        if rpds and p['or_'] >= 1 and rng.random() < 0.55:
            if tableBV(dice['tableV'], p) == 'SUCC': p['or_'] = max(0, p['or_'] - 1); p['heal'] += 1
            else: wound(p, 1, 'self')
            rpds -= 1
        elif rpds and rng.random() < 0.75:
            if tableBV(dice['tableV'], p) == 'SUCC' and decks['инвентарь']:
                p['hand'].setdefault('инвентарь', []).append(decks['инвентарь'].pop())
            rpds -= 1
        gs = ghosts()
        while rpdi > 0:
            a = choose(c, gs)
            if a != 'skip':
                if a == 'mass': mass(p)
                elif a == 'marauder': act(p, 'marauder')
                else:
                    t = rng.choice([q for q in alive() if q is not p and q['frozen'] == 0] or [None])
                    if t is not None: act(p, a, t)
            rpdi -= 1
        if p['exch'] in ('ОБМЕН_КАРТА', 'ОБМЕН_РПД', 'ОБМЕН_СПЕЦ') and (rpds + rpdi) > 0 and rng.random() < 0.45:
            p['uses']['exch'] += 1; st['exch_uses'] += 1
            if p['exch'] == 'ОБМЕН_КАРТА' and decks['тело']:
                k = rng.choice(CATS); p['hand'].setdefault(k, []).append(decks[k].pop()) if decks[k] else None
            elif p['exch'] == 'ОБМЕН_РПД': rpdi += 1
            p['exch'] = None

    cur = None
    c = 1
    while c <= C['cycle_cap']:
        st['cycle'] = c; st['player_death'] = False
        for p in P: p['heal'] = 0
        if c >= 2 and C['exchange']:
            for p in alive(): p['exch'] = exch.pop() if exch else None
        for g in ghosts():
            g['tokens'] += 1
            if shad:
                g['shadow'] = shad.pop()
                tag = g['shadow'][1]
                fn = SH.get(SH_TAGS.get(tag)) if SH_TAGS.get(tag) else None
                if fn and rng.random() < 0.8:
                    fn(g); g['uses']['shadow'] += 1; st['shadow_uses'] += 1
                g['shadow'] = None
        before = st['deaths']
        for p in alive():
            if p['alive']: turn(p, c)
        for g in ghosts():
            if g['tokens'] >= 2 and rng.random() < 0.25 and alive():
                g['tokens'] -= 2; reveal(rng.choice(alive()))
            if g['tokens'] >= C['revive_cost'] and rng.random() < 0.5:
                g['tokens'] -= C['revive_cost']; g['alive'] = True; g['or_'] = 0
                g['revived'] = True; g['dead_c'] = None; st['revives'] += 1
        if situation == 'hrono':
            for p in alive():
                for k, l in list(p['hand'].items()):
                    for i2, cc in enumerate(l):
                        if decks[k]: l[i2] = decks[k].pop()
        if c >= 2 and C['harvest'] and not st['player_death'] and len(alive()) >= 2:
            k = min(C['harvest_k'], len(alive()))
            for v in rng.sample(alive(), k):
                st['harvests'] += 1; death(v, 'harvest')
        if situation == 'hrono' and st['thr_hit']:
            st['end'] = c; break
        if situation == 'amkary':
            if len(set(q['team'] for q in alive())) <= 1: st['end'] = c; break
        elif len(alive()) <= S:
            st['end'] = c; break
        if c == C['cycle_cap']:
            st['end'] = c; st['stall'] = True; break
        c += 1
    if st['end'] is None: st['end'] = c
    return dict(n=n, situation=situation, faces=dice['faces'], end=st['end'], deaths=st['deaths'],
                alive=len(alive()), harvests=st['harvests'], mass=st['mass'], nat1=st['nat1'],
                nat20=st['nat20'], first_death=st['first_death'], revives=st['revives'],
                stall=st['stall'], shadow_uses=st['shadow_uses'], exch_uses=st['exch_uses'],
                thr_hit=st['thr_hit'])

if __name__ == '__main__':
    import statistics
    for name, dice in (('D20', D20), ('D6', D6)):
        for n in (4, 8, 12, 16):
            rows = [run_game(s, n, dice) for s in range(1, 201)]
            m = lambda k: round(statistics.mean(r[k] for r in rows), 2)
            pc = lambda k: round(100 * sum(1 for r in rows if r[k]) / len(rows), 1)
            print(f'{name} N={n:2d}: end~{m("end"):5} deaths~{m("deaths"):5} alive~{m("alive"):5} '
                  f'harv%={pc("harvests"):5} mass%={pc("mass"):5} rev%={pc("revives"):5} stall%={pc("stall"):4}')
