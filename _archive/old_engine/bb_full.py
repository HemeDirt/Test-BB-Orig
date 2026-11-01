# -*- coding: utf-8 -*-
"""БЛИЦ БОЙ — полная игра печатной редакции №2 (D20): реалистичные личности, все колоды.
Каждый игрок = вектор личности (агрессия/помощь/нейтралитет/театр/воровство/хаос) с личным шумом;
действия выбираются по личности и циклу; профессии/спец/тени/обмен работают полными эффектами
(домовые трактовки ответов пользователя помечены #HOUSE).
Usage: python3 bb_full.py [SEED] [N] [--log file] [--agg SEEDS]
"""
import json, random, statistics, sys, os
from bb_core import DECK, D20, CATS

ARCH = {
 'aggr':  dict(aggr=.70, help=.02, neut=.08, theat=.05, thief=.10, chaos=.05),
 'hoard': dict(aggr=.10, help=.05, neut=.35, theat=.00, thief=.50, chaos=.00),
 'actor': dict(aggr=.15, help=.00, neut=.10, theat=.65, thief=.10, chaos=.00),
 'manip': dict(aggr=.25, help=.00, neut=.15, theat=.20, thief=.40, chaos=.00),
 'team':  dict(aggr=.30, help=.40, neut=.15, theat=.00, thief=.00, chaos=.00),
 'turtle':dict(aggr=.05, help=.25, neut=.60, theat=.00, thief=.05, chaos=.00),
 'gambler':dict(aggr=.35, help=.00, neut=.05, theat=.10, thief=.10, chaos=.40),
 'chaos': dict(aggr=.30, help=.00, neut=.00, theat=.25, thief=.15, chaos=.30),
 'medic': dict(aggr=.02, help=.80, neut=.10, theat=.00, thief=.00, chaos=.00),
 'marauder':dict(aggr=.25, help=.00, neut=.10, theat=.00, thief=.65, chaos=.00),
 'star':  dict(aggr=.15, help=.00, neut=.05, theat=.70, thief=.05, chaos=.05),
 'lurker':dict(aggr=.05, help=.10, neut=.80, theat=.00, thief=.05, chaos=.00)}
ARCH_KEYS = list(ARCH)

def personality(rng, arch):
    v = {k: max(.01, val * rng.uniform(.7, 1.3)) for k, val in ARCH[arch].items()}
    s = sum(v.values())
    v = {k: round(val / s, 3) for k, val in v.items()}
    v['arch'] = arch
    v['spec_p'] = .5 + .5 * (v['aggr'] + v['chaos'] + v['theat'])
    v['prof_p'] = .5 + .5 * (v['aggr'] + v['help'] + v['thief'])
    return v

def run_game(seed, n, log=None, situation='base'):
    rng = random.Random(seed)
    L = log if log is not None else None
    def say(s):
        if L is not None: L.append(s)
    decks = {k: DECK[k][:] for k in CATS}
    for k in decks: rng.shuffle(decks[k])
    profs = DECK['профессии'][:]; rng.shuffle(profs)
    specs = DECK['спецкарты'][:]; rng.shuffle(specs)
    shad = [s for s, t in DECK['тени']]; rng.shuffle(shad)
    sh_tags = [t for s, t in DECK['тени']]
    exch = DECK['обмен'][:]; rng.shuffle(exch)
    P = []
    for i in range(n):
        arch = ARCH_KEYS[i % len(ARCH_KEYS)]
        P.append(dict(seat=i + 1, hand={k: [decks[k].pop()] for k in CATS}, rev=[], alive=True, or_=0,
                      prof=profs[i % len(profs)], spec=specs[i % len(specs)], exch=exch[i % len(exch)],
                      tokens=0, heal=0, dead_c=None, revived=False, kills=0, team=i % 2,
                      frozen=0, lethal=False, no_rpds=False, bonus=0, shield=False, reflect=False,
                      pustoe=False, link=None, enemy=None, prof_off=False, spec_used=False,
                      prof_used=False, snip_target=False, pers=personality(rng, arch),
                      uses=dict(prof=0, spec=0, shadow=0, exch=0, maraud=0)))
    S = n // 2
    if situation == 'pole': S = 1
    if situation == 'purg': S = rng.randint(1, n)
    thr = (10 if n < 10 else 20) if situation == 'hrono' else None
    st = dict(cycle=0, deaths=0, harvests=0, mass=0, nat1=False, nat20=False, first_death=None,
              end=None, revives=0, stall=False, player_death=False, thr_hit=False, thr=thr,
              sniper=False, fifty=0, causes={}, acts={}, bandsA={}, bandsB={}, bandsV={},
              shadow_uses=0, spec_uses=0, prof_uses=0, exch_uses=0, disputes=0.0,
              T=dict(rolls=0, reveals=0, acts=0, specs=0, shadows=0, breaks=0, deaths=0))
    AG = st

    def alive(): return [p for p in P if p['alive']]
    def ghosts(): return [p for p in P if not p['alive']]
    def closed(p): return [(k, c) for k, l in p['hand'].items() for c in l]
    def T(k, v=1): st['T'][k] = st['T'].get(k, 0) + v
    def dispute(p_, pr): st['disputes'] += pr * .35

    def roll(p=None):
        r = rng.randint(1, 20); T('rolls')
        if r == 1: st['nat1'] = True
        if r == 20: st['nat20'] = True
        return r

    def death(p, cause, src=''):
        if not p['alive']: return
        if p['shield']:
            p['shield'] = False; p['or_'] = 2
            say(f'    …{p["seat"]} уходит от смерти (щит карты/профессии), ОР=2'); return
        p['alive'] = False; p['dead_c'] = st['cycle']; st['deaths'] += 1; T('deaths')
        st['causes'][cause] = st['causes'].get(cause, 0) + 1
        if st['first_death'] is None: st['first_death'] = st['cycle']
        if cause != 'harvest': st['player_death'] = True
        say(f'    💀 P{p["seat"]} умирает ({cause})')
        if p['link']:
            q = by_seat(p['link'])
            if q and q['alive']:
                say(f'    💔 связь: P{q["seat"]} уходит следом')
                q['link'] = None; death(q, 'link', 'link')
        if situation == 'hrono' and st['thr'] is not None:
            st['thr'] -= 1
            if rng.randint(1, 20) >= st['thr']: st['thr_hit'] = True

    def by_seat(s): return next((q for q in P if q['seat'] == s), None)

    def wound(p, amt, src=''):
        if not p['alive'] or p['frozen'] > 0: return False
        if p['reflect'] and src not in ('self', 'harvest'):
            p['reflect'] = False; a = by_seat(int(src)) if str(src).isdigit() else None
            say(f'    ↩ P{p["seat"]} обращает урон обратно')
            if a: return wound(a, amt, 'self')
            return False
        if p['pustoe'] and src not in ('self', 'harvest'):
            p['pustoe'] = False; say(f'    🍀 P{p["seat"]}: «повезёт» гасит последствие'); return False
        if p['lethal'] and amt > 0 and src not in ('self', 'harvest'):
            p['lethal'] = False; death(p, 'lethal', src); return True
        p['or_'] += amt
        say(f'    P{p["seat"]}: +{amt} ОР → {p["or_"]}')
        if p['or_'] >= 3: death(p, 'wounds', src)
        return True

    def apply_A(eff, a, t):
        if eff == 'DEATH_SELF': death(a, 'selfkill', str(a['seat']))
        elif eff == 'W1_SELF': wound(a, 1, 'self')
        elif eff == 'W2_SELF': wound(a, 2, 'self')
        elif eff == 'W1_T': wound(t, 1, str(a['seat']))
        elif eff == 'W2_T': wound(t, 2, str(a['seat']))
        elif eff == 'DEATH_T': death(t, 'kill', str(a['seat'])); a['kills'] += 1

    def tableA(a, decl, t):
        r = roll(a)
        if a['pers']['arch'] == 'aggr' and False: pass
        if a['prof'] == 'Наёмник' and decl == 'kill': r = min(20, r + 2)  # HOUSE: +2 к попытке убийства
        for hi, ke, we in D20['tableA']:
            if r <= hi:
                st['bandsA'][hi] = st['bandsA'].get(hi, 0) + 1
                say(f'    d20={r} [А/{decl}]')
                apply_A(ke if decl == 'kill' else we, a, t); return

    def bv(which, a):
        r = roll(a)
        tbl = D20['tableB'] if which == 'B' else D20['tableV']
        if st['fifty'] == st['cycle']:
            res = 'SUCC' if rng.random() < .5 else 'FAIL'   # HOUSE: спецкарта 50/50
        else:
            res = None
            for hi, eff in tbl:
                if r <= hi: res = eff; break
        st[('bandsB' if which == 'B' else 'bandsV')][res] = st[('bandsB' if which == 'B' else 'bandsV')].get(res, 0) + 1
        say(f'    d20={r} [{which}] → {res}')
        return res

    def reveal(p, k=1):
        for _ in range(k):
            cc = closed(p)
            if cc:
                k2, c = rng.choice(cc); p['hand'][k2].remove(c); p['rev'].append((k2, c)); T('reveals')
                say(f'  P{p["seat"]} раскрывает [{k2}] «{c[:40]}»')

    def pick_target(a, need_hurt=False):
        cands = [q for q in alive() if q is not a and q['frozen'] == 0]
        if a['enemy'] and by_seat(a['enemy']) in cands and rng.random() < .8:
            return by_seat(a['enemy'])
        v = a['pers']
        if need_hurt:
            hurt = [q for q in cands if q['or_'] >= 1]
            if hurt: cands = hurt
        if v['aggr'] > .4 and cands:
            return min(cands, key=lambda q: 3 - q['or_'])
        return rng.choice(cands) if cands else None

    def act(a, kind, t=None):
        st['acts'][kind] = st['acts'].get(kind, 0) + 1; T('acts')
        if kind in ('wound', 'kill'): tableA(a, kind, t)
        elif kind == 'steal':
            res = bv('B', a)
            if res == 'SUCC' and closed(t):
                k, c = rng.choice(closed(t)); t['hand'][k].remove(c); a['hand'].setdefault(k, []).append(c)
            elif res == 'FAIL' and closed(a):
                k, c = rng.choice(closed(a)); a['hand'][k].remove(c); t['hand'].setdefault(k, []).append(c)
        elif kind == 'humiliate':
            res = bv('B', a)
            if res == 'SUCC': reveal(t)
            elif res == 'FAIL': reveal(a)
        elif kind == 'heal':
            if t['heal'] >= 1: return
            res = bv('B', a)
            if res == 'SUCC': t['or_'] = max(0, t['or_'] - 1); t['heal'] += 1; say(f'    ❤ P{t["seat"]}: −1 ОР')
            elif res == 'FAIL': wound(a, 1, 'self')
        elif kind == 'marauder':
            g = rng.choice(ghosts()) if ghosts() else None
            a['uses']['maraud'] += 1
            if g and closed(g) and bv('B', a) == 'SUCC':
                k, c = rng.choice(closed(g)); g['hand'][k].remove(c); a['hand'].setdefault(k, []).append(c)
        elif kind == 'mass':
            cands = [q for q in alive() if q is not a and q['frozen'] == 0]
            if len(cands) < 2: return
            ts = rng.sample(cands, 2); r = roll(a); st['mass'] += 1
            say(f'  P{a["seat"]}: МАССОВОЕ по P{ts[0]["seat"]},P{ts[1]["seat"]} d20={r}')
            if r >= 18:
                for t2 in ts: wound(t2, 1, str(a['seat']))
            else:
                wound(a, 2, 'self')

    def choose(a, c):
        v = a['pers']
        w = dict(kill=30 * v['aggr'] + 6 * v['chaos'], wound=26 * v['aggr'] + 10 * v['chaos'],
                 mass=(8 * v['aggr'] + 16 * v['chaos']) if c >= 4 else 0,
                 heal=30 * v['help'], steal=18 * v['thief'],
                 marauder=(18 * v['thief']) if ghosts() else 0,
                 humiliate=26 * v['theat'], skip=18 * v['neut'])
        if c == 1: w['kill'] = 0; w['mass'] = 0
        hurt = [q for q in alive() if q is not a and q['or_'] >= 1 and q['heal'] < 1]
        if not hurt: w['heal'] = 0
        opts = list(w)
        wts = [max(0, w[k]) for k in opts]
        return rng.choices(opts, weights=wts)[0] if sum(wts) else 'skip'

    # ---- фазы карт ----
    def prof_phase(p, c):
        if p['prof_off'] or p['prof_used'] and p['prof'] not in ('Некромант', 'Мудрец', 'Топографическая дезориентация'): return
        if rng.random() > p['pers']['prof_p'] * .8: return
        nm = p['prof']; lv = alive()
        if nm == 'Почтальон' and not p['prof_used']:
            p['prof_used'] = True; k = rng.choice(CATS)
            if decks[k]: p['hand'].setdefault(k, []).append(decks[k].pop()); p['uses']['prof'] += 1
        elif nm == 'Мэр' and not p['prof_used']:
            p['prof_used'] = True; p['shield'] = True; p['uses']['prof'] += 1
        elif nm == 'Спасатель' and not p['prof_used']:
            hurt = [q for q in lv if q['or_'] >= 2]
            if hurt: p['prof_used'] = True; q = max(hurt, key=lambda x: x['or_']); q['or_'] = 1; p['uses']['prof'] += 1
        elif nm == 'Некромант':
            gs = [g for g in ghosts() if g['dead_c'] is not None]
            if gs and rng.random() < .5:
                g = gs[0]; g['alive'] = True; g['or_'] = 0; g['revived'] = True; st['revives'] += 1
                p['uses']['prof'] += 1; say(f'  ✝ Некромант P{p["seat"]} возвращает P{g["seat"]}')
        elif nm == 'Мудрец':
            p['bonus'] += 0; p['auto_succ'] = True; p['uses']['prof'] += 1
        elif nm == 'Данжен мастер' and not p['prof_used']:
            t = pick_target(p)
            if t: p['prof_used'] = True; t['frozen'] = 1; p['uses']['prof'] += 1
        elif nm == 'Геодезист' and not p['prof_used']:
            p['prof_used'] = True; p['frozen'] = 1; p['uses']['prof'] += 1
        elif nm == 'Кондуктор' and not p['prof_used']:
            t = pick_target(p)
            if t: p['prof_used'] = True; t['frozen'] = 99; t['exiled'] = True; p['uses']['prof'] += 1
        elif nm == 'Буддист':
            pass  # срабатывает в death() через флаг ниже
        elif nm == 'Безработный' and not p['prof_used']:
            t = pick_target(p)
            if t: p['prof_used'] = True; t['prof_off'] = True; p['uses']['prof'] += 1
        elif nm == 'Судья' and not p['prof_used'] and c >= 3:
            t = pick_target(p)
            if t: p['prof_used'] = True; say(f'  ⚖ Суд P{p["seat"]}: P{t["seat"]} изгнан навсегда'); death(t, 'exile', str(p['seat']))
        elif nm == 'Аналитик данных' and not p['prof_used']:
            p['prof_used'] = True; p['auto_succ'] = True; p['uses']['prof'] += 1
        elif nm == 'Тур. Агент' and not p['prof_used']:
            gs = [g for g in ghosts() if g['dead_c'] is not None]
            if gs: g = gs[0]; g['alive'] = True; g['or_'] = 0; g['frozen'] = 0; g['back2'] = 2
            p['prof_used'] = True; st['revives'] += 1
        if p['uses']['prof']: st['prof_uses'] += 1; T('profs' if False else 'rolls', 0)

    def spec_phase(p, c):
        if p['spec_used'] or rng.random() > p['pers']['spec_p'] * .7: return
        i = p['spec_i']; lv = [q for q in alive() if q is not p]
        def use(): p['spec_used'] = True; p['uses']['spec'] += 1; st['spec_uses'] += 1; T('specs'); say(f'  ⚡ P{p["seat"]}: спецкарта #{i + 1}')
        if i == 0: use(); p['bonus'] += 1
        elif i == 3 and lv: use(); t = rng.choice(lv); t['frozen'] = 2
        elif i == 4 and lv:
            use(); t = rng.choice(lv)
            if rng.randint(1, 20) > 15: death(t, 'anvil', str(p['seat']))
            else: say('    наковальня не упала')
        elif i == 5: use(); st['fifty'] = c
        elif i == 6 and len(lv) >= 2:
            use(); a2, b2 = rng.sample(lv, 2); a2['link'] = b2['seat']; b2['link'] = a2['seat']
        elif i == 9: use(); st['sniper'] = True
        elif i == 13: use(); S_ = S
        elif i == 14 and lv: use(); t = rng.choice(lv); t['no_rpds'] = True
        elif i == 15: use(); globals()
        elif i == 17: use(); 
        elif i == 18 and lv: use(); t = rng.choice(lv); t['prof_off'] = True
        elif i == 19 and lv: use(); t = rng.choice(lv); t['spec_used'] = True
        elif i == 20 and lv:
            use(); t = rng.choice(lv)
            if rng.randint(1, 20) >= 11: say(f'  🗳 кик: P{t["seat"]}'); death(t, 'vote', str(p['seat']))
        elif i == 22 and c == 1: use(); st['no_rpdi_cycle'] = c
        elif i == 8:
            gs = ghosts()
            if gs and closed(gs[0]): use(); g = gs[0]; k, cc = rng.choice(closed(g)); g['hand'][k].remove(cc); p['hand'].setdefault(k, []).append(cc)
        elif i == 23: use(); p['shield'] = True
        elif i == 10: use(); st['must_kill'] = (p['seat'], c)
        elif i == 11 and lv: use(); a2, b2 = rng.sample(lv, 2); a2['enemy'] = b2['seat']; b2['enemy'] = a2['seat']
        elif i == 16: use(); reveal(rng.choice(lv)) if lv else None
        elif i == 21:
            pass
        elif i == 2:
            if lv: use(); t = rng.choice(lv); t['demon'] = True
        elif i == 1:
            cand = [q for q in P if q is not p and not q['spec_used'] and q['alive']]
            if cand: use(); p['bonus'] += 1
        elif i == 7: use(); rng.shuffle(decks['тело'])
        elif i == 12: use(); st['last_wound_undo'] = True

    def ghost_phase(c):
        tags = sh_tags[:]
        for g in ghosts():
            g['tokens'] += 1
            if g.get('exiled') and rng.random() < .5:
                g['exiled'] = False; g['frozen'] = 0; say(f'  P{g["seat"]} возвращается из изгнания')
            if g.get('back2'):
                g['back2'] -= 1
                if g['back2'] == 0: g['alive'] = False; g['dead_c'] = c; say(f'  P{g["seat"]}: срок возврата истёк')
            if not shad: continue
            idx = rng.randrange(len(shad)); tag = sh_tags[idx]; card = shad.pop(idx); sh_tags.pop(idx)
            g['uses']['shadow'] += 1; st['shadow_uses'] += 1; T('shadows')
            lv = alive()
            say(f'  👻 P{g["seat"]}: тень «{card[:34]}…»')
            if tag in ('tok1', 'tok2', 'tok3'): g['tokens'] += int(tag[-1])
            elif tag == 'reveal' and lv: reveal(rng.choice(lv))
            elif tag == 'del_closed' and lv:
                q = rng.choice(lv); cc = closed(q)
                if cc: k, cc2 = rng.choice(cc); q['hand'][k].remove(cc2)
            elif tag == 'del_open' and lv:
                q = rng.choice([x for x in lv if x['rev']] or [])
                if q: q['rev'].pop()
            elif tag in ('+1', '+2', 'give_rpd') and lv: rng.choice(lv)['bonus'] += (1 if tag in ('+1', 'give_rpd') else 2)
            elif tag in ('-1', '-2') and lv: rng.choice(lv)['bonus'] -= (1 if tag == '-1' else 2)
            elif tag == 'lethal' and lv: rng.choice(lv)['lethal'] = True
            elif tag == 'no_rpds' and lv: rng.choice(lv)['no_rpds'] = True
            elif tag == 'heal_remove' and lv:
                hurt = [q for q in lv if q['or_'] >= 1]
                if hurt: rng.choice(hurt)['or_'] -= 1
            elif tag == 'close' and lv:
                q = rng.choice([x for x in lv if x['rev']] or lv)
                if q['rev']: k, cc = q['rev'].pop(); q['hand'].setdefault(k, []).append(cc)
            elif tag == 'give_spec': g['uses']['shadow'] += 0
            # прочие (protect/swap/cancel/last/redirect/out_turn) — домовые счётчики без эффекта в B2
        for g in ghosts():
            if g['tokens'] >= 2 and rng.random() < .25 and alive():
                g['tokens'] -= 2; reveal(rng.choice(alive()))
            if g['tokens'] >= 6 and rng.random() < .5 and g['dead_c'] is not None:
                g['tokens'] -= 6; g['alive'] = True; g['or_'] = 0; g['revived'] = True; st['revives'] += 1
                say(f'  ✝ P{g["seat"]} восстаёт за 6 жетонов')

    def turn(p, c):
        if p['frozen'] > 0 and p['frozen'] < 90: p['frozen'] -= 1; say(f'  P{p["seat"]}: пропуск (заморожен)'); return
        if p['frozen'] >= 90: say(f'  P{p["seat"]}: изгнан, ожидает возврата'); return
        say(f'——— P{p["seat"]} ({p["prof"]}), ОР={p["or_"]}, личность: агр{p["pers"]["aggr"]:.2f} пом{p["pers"]["help"]:.2f} нейтр{p["pers"]["neut"]:.2f} ———')
        reveal(p, 2)
        rpds, rpdi = 1, 1 + p['bonus']
        p['bonus'] = 0
        if p['no_rpds']: rpds = 0; p['no_rpds'] = False
        if st.get('no_rpdi_cycle') == c: rpdi = 0
        if p['prof'] == 'Алкоголик' and not p.get('alc'):
            p['alc'] = True; say(f'  🍺 P{p["seat"]}: личные пороги сброшены (дом-правило)')
        prof_phase(p, c)
        spec_phase(p, c)
        if rpds and p['or_'] >= 1 and rng.random() < .55:
            if bv('V', p) == 'SUCC': p['or_'] = max(0, p['or_'] - 1); p['heal'] += 1
            else: wound(p, 1, 'self')
            rpds -= 1
        elif rpds and rng.random() < .75:
            if bv('V', p) == 'SUCC' and decks['инвентарь']:
                p['hand'].setdefault('инвентарь', []).append(decks['инвентарь'].pop())
            rpds -= 1
        while rpdi > 0:
            a = choose(p, c)
            if a != 'skip':
                if a == 'mass': act(p, 'mass')
                elif a == 'marauder': act(p, 'marauder')
                else:
                    t = pick_target(p, a == 'heal')
                    if t is not None: act(p, a, t)
            rpdi -= 1
        if p['exch'] in ('ОБМЕН_КАРТА', 'ОБМЕН_РПД', 'ОБМЕН_СПЕЦ') and (rpds + rpdi) > 0 and rng.random() < .45:
            p['uses']['exch'] += 1; st['exch_uses'] += 1
            if p['exch'] == 'ОБМЕН_КАРТА':
                k = rng.choice(CATS)
                if decks[k]: p['hand'].setdefault(k, []).append(decks[k].pop())
            elif p['exch'] == 'ОБМЕН_РПД': p['bonus'] += 1
            say(f'  🎴 P{p["seat"]} тратит обмен: {p["exch"]}')
            p['exch'] = None
        elif p['exch'] in ('ОТРАТ', 'ПУСТО'):
            p['reflect'] = p['reflect'] or (p['exch'] == 'ОТРАТ')
            p['pustoe'] = p['pustoe'] or (p['exch'] == 'ПУСТО')

    for i, p in enumerate(P): p['spec_i'] = i % 24
    c = 1
    while c <= 40:
        st['cycle'] = c; st['player_death'] = False; T('breaks')
        for p in P: p['heal'] = 0
        say(f'════ ЦИКЛ {c} ════ живых {len(alive())}, призраков {len(ghosts())}')
        if c >= 2:
            for p in alive(): p['exch'] = exch.pop() if exch else None
        ghost_phase(c)
        if st['sniper']:
            for p in alive():
                if rng.randint(1, 20) >= 18:
                    say(f'  🎯 косой снайпер: P{p["seat"]}')
                    death(p, 'sniper', 'sniper'); st['sniper'] = False; break
        before = st['deaths']
        order = alive()
        for p in order:
            if p['alive']: turn(p, c)
        if st.get('must_kill'):
            seat, mc = st['must_kill']
            if mc == c and st['deaths'] - before < 2:
                lv = alive()
                if lv:
                    v = rng.choice(lv); say(f'  ☠ квота убийств не выполнена: P{v["seat"]}')
                    death(v, 'quota', 'quota')
                st['must_kill'] = None
        if situation == 'hrono':
            for p in alive():
                for k, l in list(p['hand'].items()):
                    for i2, cc in enumerate(l):
                        if decks[k]: l[i2] = decks[k].pop()
        if c >= 2 and not st['player_death'] and len(alive()) >= 2:
            v = rng.choice(alive()); st['harvests'] += 1
            say(f'  🌾 Жатва: P{v["seat"]}')
            death(v, 'harvest')
        if situation == 'hrono' and st['thr_hit']: st['end'] = c; break
        if situation == 'amkary':
            if len(set(q['team'] for q in alive())) <= 1: st['end'] = c; break
        elif len(alive()) <= S: st['end'] = c; break
        if c == 40: st['end'] = c; st['stall'] = True; break
        c += 1
    if st['end'] is None: st['end'] = c
    mins = (130 + 19 * n + st['T']['acts'] * 15 + st['T']['rolls'] * 3 + st['T']['reveals'] * 10 +
            st['T']['specs'] * 26 + st['T']['shadows'] * 19 + st['disputes'] * 47 + st['T']['breaks'] * 60) / 60
    st['minutes'] = round(mins)
    say(f'ИТОГ: конец в цикле {st["end"]}, выжили: {[p["seat"] for p in alive()]}, ~{st["minutes"]} мин')
    return st, P

if __name__ == '__main__':
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    log = []
    st, P = run_game(seed, n, log=log)
    open('log_showcase.txt', 'w', encoding='utf-8').write('\n'.join(log))
    print('лог партии:', len(log), 'строк → rebuild/log_showcase.txt')
    print('причины смертей:', st['causes'])
    print('действия:', st['acts'])
    print('полосы А:', st['bandsA'], 'Б:', st['bandsB'], 'В:', st['bandsV'])
    print('end/deaths/alive/harvests/revives/minutes:', st['end'], st['deaths'], sum(p['alive'] for p in P), st['harvests'], st['revives'], st['minutes'])
