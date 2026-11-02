"""БЛИЦ БОЙ — эталонный движок печатной редакции №2 (S1a, синтез).
Каркас: game/legacy/old_engine/bb_full.py (440 строк, md5 314f892c) + правила v3
(docs/rules/ПРАВИЛА_БЛИЦ_БОЙ_v3.md) + листы печати №2 (_inbox/ПАКЕТ_КОЛОДА_ПЕЧАТЬ2.md,
_inbox/СИТУАЦИИ_ПЕЧАТЬ2.md). Из 21 названного в допуске legacy-модуля на диске реально
лежали только bb_full.py и bb_core.py — факт зафиксирован в CONFLICTS C32; поведение
отсутствующих модулей восстановлено из правил в объёме прогонов новой эпохи
(base N8, Поле, Чистилище, Машина времени/Пьяная хронология, Амкары, harvest off/после
трупа, late, leader, max2, дуэль, aggr). Список «не перенесено» — в отчёте Р3.
Каждый rng-вызов идёт через _Rng (журнал вызовов) — это опора гард-теста флагов OFF.
Конфигурация — ЕДИНСТВЕННЫЙ блок CFG: game/config.py (дефолты = печать №2).
Использование: import bb_full; bb_full.run_game(seed, n, cfg=..., situation='base')
ВНИМАНИЕ: S1a запрещает прогоны — файл написан и проверен только компиляцией и гард-тестом.
"""
import json, math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from config import CFG_DEFAULTS, make_cfg
ROOT = os.path.dirname(HERE)
CATS = ['тело', 'разум', 'способности', 'инвентарь', 'история', 'знания', 'детали']
SHEET = {'тело': 'ТЕЛО', 'разум': 'РАЗУМ', 'способности': 'СПОСОБНОСТИ', 'инвентарь': 'ИНВЕНТАРЬ', 'история': 'ИСТОРИЯ', 'знания': 'ЗНАНИЯ', 'детали': 'ДЕТАЛИ'}
TABLE_A = [(4, 'DEATH_SELF', 'W2_SELF'), (8, 'W1_SELF', 'W1_SELF'), (12, 'NONE', 'NONE'), (16, 'W2_T', 'W1_T'), (20, 'DEATH_T', 'W2_T')]
TABLE_B = [(10, 'FAIL'), (14, 'NONE'), (20, 'SUCC')]
TABLE_V = [(9, 'FAIL'), (10, 'NONE'), (20, 'SUCC')]
MASS_THR = 18
MASS_OTHER_THR = 15
ARCH = {'aggr': dict(aggr=0.7, help=0.02, neut=0.08, theat=0.05, thief=0.1, chaos=0.05), 'hoard': dict(aggr=0.1, help=0.05, neut=0.35, theat=0.0, thief=0.5, chaos=0.0), 'actor': dict(aggr=0.15, help=0.0, neut=0.1, theat=0.65, thief=0.1, chaos=0.0), 'manip': dict(aggr=0.25, help=0.0, neut=0.15, theat=0.2, thief=0.4, chaos=0.0), 'team': dict(aggr=0.3, help=0.4, neut=0.15, theat=0.0, thief=0.0, chaos=0.0), 'turtle': dict(aggr=0.05, help=0.25, neut=0.6, theat=0.0, thief=0.05, chaos=0.0), 'gambler': dict(aggr=0.35, help=0.0, neut=0.05, theat=0.1, thief=0.1, chaos=0.4), 'chaos': dict(aggr=0.3, help=0.0, neut=0.0, theat=0.25, thief=0.15, chaos=0.3), 'medic': dict(aggr=0.02, help=0.8, neut=0.1, theat=0.0, thief=0.0, chaos=0.0), 'marauder': dict(aggr=0.25, help=0.0, neut=0.1, theat=0.0, thief=0.65, chaos=0.0), 'star': dict(aggr=0.15, help=0.0, neut=0.05, theat=0.7, thief=0.05, chaos=0.05), 'lurker': dict(aggr=0.05, help=0.1, neut=0.8, theat=0.0, thief=0.05, chaos=0.0)}
ARCH_KEYS = list(ARCH)

class _Rng:
    """Обёртка random.Random с журналом вызовов: базой гард-теста флагов OFF."""

    def __init__(self, seed):
        self._r = random.Random(seed)
        self.calls = []

    def _log(self, name, out):
        self.calls.append((name, out))
        return out

    def randint(self, a, b):
        return self._log('randint', self._r.randint(a, b))

    def choice(self, seq):
        return self._log('choice', self._r.choice(seq))

    def sample(self, seq, k):
        return self._log('sample', self._r.sample(seq, k))

    def shuffle(self, seq):
        self._log('shuffle', len(seq))
        return self._r.shuffle(seq)

    def random(self):
        return self._log('random', self._r.random())

    def uniform(self, a, b):
        return self._log('uniform', self._r.uniform(a, b))

    def randrange(self, n):
        return self._log('randrange', self._r.randrange(n))

    def choices(self, pop, weights=None, k=1):
        return self._log('choices', self._r.choices(pop, weights=weights, k=k))

def load_deck(cfg):
    """deck_source: print2 → data/deck/deck_print2.json; archive → canon/decks.json (md5 6f8542a7)."""
    if cfg['deck_source'] == 'print2':
        return json.load(open(os.path.join(ROOT, 'data', 'deck', 'deck_print2.json'), encoding='utf-8'))
    if cfg['deck_source'] == 'archive':
        return json.load(open(os.path.join(ROOT, '_archive', 'blitz1.1', 'src', 'canon', 'decks.json'), encoding='utf-8'))
    raise ValueError(f"неизвестный deck_source: {cfg['deck_source']}")

def exchange_pool(cfg, deck):
    """Лист ОБМЕН по флагу exchange_revision (§9.2; тиражи — C2/C27)."""
    rev = cfg['exchange_revision']
    if rev == 'off':
        return None
    cards = deck['ОБМЕН'][:]
    if rev == 'photo':
        return cards
    if rev == 'cards_exchange_md':

        def find(sub):
            for t in set(cards):
                if sub in t:
                    return t
            raise KeyError(f'ОБМЕН: не найден текст «{sub}»')
        obr = find('обратить любое РП-действие')
        sps = find('спасти игрока от')
        kart = find('на любую карту характеристик')
        rpd = find('на другое РП действие')
        spec = 'обмен-спец'
        lucky = find('повезет')
        pool = [obr] * 5 + [sps] * 4 + [kart] * 3 + [rpd] * 1 + [spec] * 2 + [lucky] * 9
        assert len(pool) == 24
        return pool
    raise ValueError(f'неизвестный exchange_revision: {rev}')

def classify_exchange(text):
    """Механическая метка карты обмена по дословному тексту листа (печатные тексты не меняются)."""
    if text is None:
        return None
    if 'обратить любое РП-действие' in text:
        return 'ОТРАТ'
    if 'спасти игрока от' in text:
        return 'СПАС'
    if 'на любую карту характеристик' in text:
        return 'ОБМЕН_КАРТА'
    if 'на другое РП действие' in text:
        return 'ОБМЕН_РПД'
    if text == 'обмен-спец':
        return 'ОБМЕН_СПЕЦ'
    if 'повезет' in text:
        return 'ПУСТО'
    return None

def personality(rng, arch):
    v = {k: max(0.01, val * rng.uniform(0.7, 1.3)) for k, val in ARCH[arch].items()}
    s = sum(v.values())
    v = {k: round(val / s, 3) for k, val in v.items()}
    v['arch'] = arch
    v['spec_p'] = 0.5 + 0.5 * (v['aggr'] + v['chaos'] + v['theat'])
    v['prof_p'] = 0.5 + 0.5 * (v['aggr'] + v['help'] + v['thief'])
    return v
SITUATIONS = {'base': dict(S='half'), 'plane': dict(S='half'), 'pomidor': dict(S='half', verbal_rule=True), 'pole': dict(S=1), 'purg': dict(S='roll', places_d20=True), 'amkary': dict(S='teams'), 'hrono': dict(S='thr', reshuffle_hand=True)}
SITUATIONS.setdefault('samolyot', SITUATIONS['plane'])
SITUATIONS.setdefault('field', SITUATIONS['pole'])
SITUATIONS.setdefault('timemachine', SITUATIONS['hrono'])
SITUATIONS.setdefault('duel', SITUATIONS['base'])

def run_game(seed, n, cfg=None, situation='base', log=None):
    C = cfg or dict(CFG_DEFAULTS)
    if C['prof_complex']:
        raise NotImplementedError('prof_complex: сложные профессии НЕ реализованы — автор напишет отдельный лист (S1a)')
    if C['anarchy_pack']:
        raise NotImplementedError('anarchy_pack: дополнение не канон, не реализовано')
    if C['mode'] not in ('print2', 'archive_v11'):
        raise ValueError(f"неизвестный mode: {C['mode']}")
    if C['reroll'] not in ('others_dice_only', 'any', 'none'):
        raise ValueError(f"неизвестный reroll: {C['reroll']}")
    rng = _Rng(seed)
    L = log

    def say(s):
        if L is not None:
            L.append(s)
    deck = load_deck(C)
    SCHED = SITUATIONS[situation]
    st = dict(cycle=0, deaths=0, harvests=0, mass=0, nat1=False, nat20=False, first_death=None, end=None, revives=0, stall=False, player_death=False, thr_hit=False, thr=None, sniper=False, fifty=0, causes={}, acts={}, shadow_uses=0, spec_uses=0, prof_uses=0, exch_uses=0, bets=0, disputes=0.0, no_rpdi_cycle=None, must_kill=None, T=dict(rolls=0, reveals=0, acts=0, specs=0, shadows=0, breaks=0, deaths=0))
    decks = {k: deck[SHEET[k]][:] for k in CATS}
    for k in decks:
        rng.shuffle(decks[k])
    profs = deck['ПРОФЕССИЯ'][:]
    rng.shuffle(profs)
    specs = deck['СПЕЦКАРТЫ'][:]
    rng.shuffle(specs)
    shad = deck['ТЕНЬ'][:]
    rng.shuffle(shad)
    exch_cards = exchange_pool(C, deck)
    exch = None
    if exch_cards is not None:
        exch = exch_cards[:]
        rng.shuffle(exch)
    if C['draft2']:
        for p_i in range(n):
            for k in CATS:
                if len(decks[k]) >= 3:
                    decks[k].pop(rng.randrange(len(decks[k])))
    if C['pool1000']:
        for k in decks:
            base = deck[SHEET[k]][:]
            reps = math.ceil(1000 / len(base))
            decks[k] = (base * reps)[:1000]
            rng.shuffle(decks[k])
    P = []
    for i in range(n):
        arch = ARCH_KEYS[i % len(ARCH_KEYS)]
        P.append(dict(seat=i + 1, hand={k: [decks[k].pop()] for k in CATS}, rev=[], alive=True, or_=0, prof=profs[i % len(profs)].split('—')[0].strip(), spec_i=i % 24, exch=classify_exchange(exch[i % len(exch)]) if exch else None, exch_raw=exch[i % len(exch)] if exch else None, tokens=0, heal=0, dead_c=None, revived=False, kills=0, team=i % 2, frozen=0, lethal=False, no_rpds=False, bonus=0, shield=False, reflect=False, pustoe=False, link=None, enemy=None, prof_off=False, prof_used=False, spec_used=False, back2=0, exiled=False, alc=False, pers=personality(rng, arch), doll=None, open_hand=False, uses=dict(prof=0, spec=0, shadow=0, exch=0, maraud=0)))
    if C['open_hands']:
        for p in P:
            p['open_hand'] = True
    S = n // 2
    if C['s_plus1']:
        S += 1
    if C['s_third']:
        S = math.ceil(n / 3)
    if SCHED.get('S') == 1:
        S = 1
    elif SCHED.get('S') == 'roll':
        S = rng.randint(1, n)
        st['places'] = S
    if situation == 'amkary':
        S = 0
    if situation == 'hrono':
        st['thr'] = C['time_machine_start_threshold']

    def alive():
        return [p for p in P if p['alive']]

    def ghosts():
        return [p for p in P if not p['alive']]

    def closed(p):
        return [(k, c) for k, l in p['hand'].items() for c in l]

    def by_seat(s):
        return next((q for q in P if q['seat'] == s), None)

    def T(k, v=1):
        st['T'][k] = st['T'].get(k, 0) + v

    def roll(p=None):
        r = rng.randint(1, 20)
        T('rolls')
        if r == 1:
            st['nat1'] = True
        if r == 20:
            st['nat20'] = True
        return r

    def death(p, cause, src=''):
        if not p['alive']:
            return
        if p['shield']:
            p['shield'] = False
            p['or_'] = 2
            say(f"    …{p['seat']} уходит от смерти (щит карты/профессии), ОР=2")
            return
        p['alive'] = False
        p['dead_c'] = st['cycle']
        st['deaths'] += 1
        T('deaths')
        st['causes'][cause] = st['causes'].get(cause, 0) + 1
        if st['first_death'] is None:
            st['first_death'] = st['cycle']
        if cause != 'harvest':
            st['player_death'] = True
        say(f"    💀 P{p['seat']} умирает ({cause})")
        if p['link']:
            q = by_seat(p['link'])
            if q and q['alive']:
                say(f"    💔 связь: P{q['seat']} уходит следом")
                q['link'] = None
                death(q, 'link', 'link')
        if situation == 'hrono' and st['thr'] is not None:
            st['thr'] = max(1, st['thr'] + C['drunk_chronology_step'])
            r = roll()
            if r == C['drunk_chronology_victory_on']:
                st['thr_hit'] = True
            st['thr'] = max(1, st['thr'])

    def wound(p, amt, src=''):
        if not p['alive'] or p['frozen'] > 0:
            return False
        if p['reflect'] and src not in ('self', 'harvest'):
            p['reflect'] = False
            a = by_seat(int(src)) if str(src).isdigit() else None
            say(f"    ↩ P{p['seat']} обращает урон обратно")
            if a:
                return wound(a, amt, 'self')
            return False
        if p['pustoe'] and src not in ('self', 'harvest'):
            p['pustoe'] = False
            say(f"    🍀 P{p['seat']}: «повезёт» гасит последствие")
            return False
        if p['lethal'] and amt > 0 and (src not in ('self', 'harvest')):
            p['lethal'] = False
            death(p, 'lethal', src)
            return True
        p['or_'] += amt
        say(f"    P{p['seat']}: +{amt} ОР → {p['or_']}")
        if p['or_'] >= C['or_death']:
            death(p, 'wounds', src)
        dth_floor = -1
        if C['dth2']:
            dth_floor = -2
        if C['dth4']:
            dth_floor = -4
        if dth_floor != -1 and p['or_'] <= dth_floor and p['alive']:
            death(p, 'deep_wounds', src)
        return True

    def apply_A(eff, a, t):
        if eff == 'DEATH_SELF':
            death(a, 'selfkill', str(a['seat']))
        elif eff == 'W1_SELF':
            wound(a, 1, 'self')
        elif eff == 'W2_SELF':
            wound(a, 2, 'self')
        elif eff == 'W1_T':
            wound(t, 1, str(a['seat']))
        elif eff == 'W2_T':
            wound(t, 2, str(a['seat']))
        elif eff == 'DEATH_T':
            death(t, 'kill', str(a['seat']))
            a['kills'] += 1

    def tableA(a, decl, t):
        r = roll(a)
        if a['prof'] == 'Наёмник' and decl == 'kill':
            r = min(20, r + 2)
        for hi, ke, we in TABLE_A:
            if r <= hi:
                say(f'    d20={r} [А/{decl}]')
                apply_A(ke if decl == 'kill' else we, a, t)
                return

    def bv(which, a):
        tbl = TABLE_B if which == 'B' else TABLE_V
        if st['fifty'] == st['cycle']:
            return 'SUCC' if rng.random() < 0.5 else 'FAIL'
        r = roll(a)
        for hi, eff in tbl:
            if r <= hi:
                say(f'    d20={r} [{which}] → {eff}')
                return eff
        return tbl[-1][1]

    def reveal(p, k=1):
        for _ in range(k):
            cc = closed(p)
            if cc:
                k2, c = rng.choice(cc)
                p['hand'][k2].remove(c)
                p['rev'].append((k2, c))
                T('reveals')
                say(f"  P{p['seat']} раскрывает [{k2}] «{c[:40]}»")

    def pick_target(a, need_hurt=False):
        cands = [q for q in alive() if q is not a and q['frozen'] == 0]
        if C['doll'] and a.get('doll') is not None and (a.get('doll_c') == st['cycle']):
            d = by_seat(a['doll'])
            if d is not None and d['alive'] and (d in cands):
                say(f"  🪆 P{a['seat']}: кукла держит цель P{d['seat']}")
                return d
        if a['enemy'] and by_seat(a['enemy']) in cands and (rng.random() < 0.8):
            return by_seat(a['enemy'])
        if need_hurt:
            hurt = [q for q in cands if q['or_'] >= 1]
            if hurt:
                cands = hurt
        if a['pers']['aggr'] > 0.4 and cands:
            t = min(cands, key=lambda q: 3 - q['or_'])
            if C['doll']:
                a['doll'] = t['seat']
                a['doll_c'] = st['cycle']
            return t
        t = rng.choice(cands) if cands else None
        if C['doll'] and t is not None:
            a['doll'] = t['seat']
            a['doll_c'] = st['cycle']
        return t

    def act(a, kind, t=None):
        st['acts'][kind] = st['acts'].get(kind, 0) + 1
        T('acts')
        if kind in ('wound', 'kill'):
            tableA(a, kind, t)
        elif kind == 'steal':
            res = bv('B', a)
            if res == 'SUCC' and closed(t):
                k, c = rng.choice(closed(t))
                t['hand'][k].remove(c)
                a['hand'].setdefault(k, []).append(c)
            elif res == 'FAIL' and closed(a):
                k, c = rng.choice(closed(a))
                a['hand'][k].remove(c)
                t['hand'].setdefault(k, []).append(c)
        elif kind == 'humiliate':
            res = bv('B', a)
            if res == 'SUCC':
                reveal(t)
            elif res == 'FAIL':
                reveal(a)
        elif kind == 'heal':
            if t['heal'] >= C['heal_cap_per_cycle']:
                return
            res = bv('B', a)
            if res == 'SUCC':
                t['or_'] = max(0, t['or_'] - 1)
                t['heal'] += 1
                say(f"    ❤ P{t['seat']}: −1 ОР")
            elif res == 'FAIL':
                wound(a, 1, 'self')
        elif kind == 'marauder':
            g = rng.choice(ghosts()) if ghosts() else None
            a['uses']['maraud'] += 1
            if g and closed(g) and (bv('B', a) == 'SUCC'):
                k, c = rng.choice(closed(g))
                g['hand'][k].remove(c)
                a['hand'].setdefault(k, []).append(c)
        elif kind == 'mass':
            cands = [q for q in alive() if q is not a and q['frozen'] == 0]
            if len(cands) < 2:
                return
            ts = rng.sample(cands, 2)
            r = roll(a)
            st['mass'] += 1
            mass_thr = MASS_THR
            if C['mass_low']:
                mass_thr = 17
            say(f"  P{a['seat']}: МАССОВОЕ по P{ts[0]['seat']},P{ts[1]['seat']} d20={r}")
            if r >= mass_thr:
                for t2 in ts:
                    wound(t2, 1, str(a['seat']))
            else:
                wound(a, 2, 'self')

    def choose(a, c):
        v = a['pers']
        w = dict(kill=30 * v['aggr'] + 6 * v['chaos'], wound=26 * v['aggr'] + 10 * v['chaos'], mass=8 * v['aggr'] + 16 * v['chaos'] if c >= 4 else 0, heal=30 * v['help'], steal=18 * v['thief'], marauder=18 * v['thief'] if ghosts() else 0, humiliate=26 * v['theat'], skip=18 * v['neut'])
        if c == 1:
            w['kill'] = 0
            w['mass'] = 0
        hurt = [q for q in alive() if q is not a and q['or_'] >= 1 and (q['heal'] < C['heal_cap_per_cycle'])]
        if not hurt:
            w['heal'] = 0
        opts = list(w)
        wts = [max(0, w[k]) for k in opts]
        if C['pressure'] and st['cycle'] > 8:
            wts = [x * (2.0 if k == 'kill' else 1.0) for x, k in zip(wts, opts)]
        return rng.choices(opts, weights=wts)[0] if sum(wts) else 'skip'
    COMPLEX_PROFS = {'Сменщик', 'Один-1', 'Топографическая дезориентация', 'Пропагандист', 'Демонолог', 'Священник', 'Буддист'}

    def prof_phase(p, c):
        if not C['prof_simple'] or p['prof_off'] or p['prof'] in COMPLEX_PROFS:
            return
        if p['prof_used'] and p['prof'] not in ('Некромант', 'Мудрец'):
            return
        if rng.random() > p['pers']['prof_p'] * 0.8:
            return
        nm = p['prof']
        lv = alive()
        if nm == 'Почтальон' and (not p['prof_used']):
            p['prof_used'] = True
            k = rng.choice(CATS)
            if decks[k]:
                p['hand'].setdefault(k, []).append(decks[k].pop())
                p['uses']['prof'] += 1
        elif nm == 'Мэр' and (not p['prof_used']):
            p['prof_used'] = True
            p['shield'] = True
            p['uses']['prof'] += 1
        elif nm == 'Спасатель' and (not p['prof_used']):
            hurt = [q for q in lv if q['or_'] >= 2]
            if hurt:
                p['prof_used'] = True
                q = max(hurt, key=lambda x: x['or_'])
                q['or_'] = 1
                p['uses']['prof'] += 1
        elif nm == 'Некромант':
            gs = [g for g in ghosts() if g['dead_c'] is not None]
            if gs and rng.random() < 0.5:
                g = gs[0]
                g['alive'] = True
                g['or_'] = 0
                g['revived'] = True
                st['revives'] += 1
                p['uses']['prof'] += 1
                say(f"  ✝ Некромант P{p['seat']} возвращает P{g['seat']}")
        elif nm == 'Мудрец':
            p['auto_succ'] = True
            p['uses']['prof'] += 1
        elif nm == 'Данжен мастер' and (not p['prof_used']):
            t = pick_target(p)
            if t:
                p['prof_used'] = True
                t['frozen'] = 1
                p['uses']['prof'] += 1
        elif nm == 'Геодезист' and (not p['prof_used']):
            p['prof_used'] = True
            p['frozen'] = 1
            p['uses']['prof'] += 1
        elif nm == 'Кондуктор' and (not p['prof_used']):
            t = pick_target(p)
            if t:
                p['prof_used'] = True
                t['frozen'] = 99
                t['exiled'] = True
                p['uses']['prof'] += 1
        elif nm == 'Безработный' and (not p['prof_used']):
            t = pick_target(p)
            if t:
                p['prof_used'] = True
                t['prof_off'] = True
                p['uses']['prof'] += 1
        elif nm == 'Судья' and (not p['prof_used']) and (c >= 3):
            t = pick_target(p)
            if t:
                p['prof_used'] = True
                say(f"  ⚖ Суд P{p['seat']}: P{t['seat']} изгнан навсегда")
                death(t, 'exile', str(p['seat']))
        elif nm == 'Аналитик данных' and (not p['prof_used']):
            p['prof_used'] = True
            p['auto_succ'] = True
            p['uses']['prof'] += 1
        elif nm == 'Тур. Агент' and (not p['prof_used']):
            gs = [g for g in ghosts() if g['dead_c'] is not None]
            if gs:
                g = gs[0]
                g['alive'] = True
                g['or_'] = 0
                g['frozen'] = 0
                g['back2'] = 2
            p['prof_used'] = True
            st['revives'] += 1
        if p['uses']['prof']:
            st['prof_uses'] += 1

    def spec_phase(p, c):
        if p.get('spec_blocked'):
            return
        if not C['special_cards'] or (p['spec_used'] and (not C['spec_cycle'])) or p.get('spec_used_turn') or (rng.random() > p['pers']['spec_p'] * 0.7):
            return
        i = p['spec_i']
        lv = [q for q in alive() if q is not p]

        def use():
            p['spec_used_turn'] = True
            p['uses']['spec'] += 1
            st['spec_uses'] += 1
            T('specs')
            say(f"  ⚡ P{p['seat']}: спецкарта #{i + 1}")
        if i == 0:
            use()
            p['bonus'] += 1
        elif i == 3 and lv:
            use()
            t = rng.choice(lv)
            t['frozen'] = 2
        elif i == 4 and lv:
            use()
            t = rng.choice(lv)
            if rng.randint(1, 20) > 15:
                death(t, 'anvil', str(p['seat']))
            else:
                say('    наковальня не упала')
        elif i == 5:
            use()
            st['fifty'] = c
        elif i == 6 and len(lv) >= 2:
            use()
            a2, b2 = rng.sample(lv, 2)
            a2['link'] = b2['seat']
            b2['link'] = a2['seat']
        elif i == 7:
            use()
            rng.shuffle(decks['тело'])
        elif i == 8:
            gs = ghosts()
            if gs and closed(gs[0]):
                use()
                g = gs[0]
                k, cc = rng.choice(closed(g))
                g['hand'][k].remove(cc)
                p['hand'].setdefault(k, []).append(cc)
        elif i == 9:
            use()
            st['sniper'] = True
        elif i == 10:
            use()
            st['must_kill'] = (p['seat'], c)
        elif i == 11 and len(lv) >= 2:
            use()
            a2, b2 = rng.sample(lv, 2)
            a2['enemy'] = b2['seat']
            b2['enemy'] = a2['seat']
        elif i == 13:
            use()
            st['place_half'] = True
        elif i == 14 and lv:
            use()
            t = rng.choice(lv)
            t['no_rpds'] = True
        elif i == 15:
            use()
            p['bonus'] += 3
        elif i == 17:
            use()
        elif i == 18 and lv:
            use()
            t = rng.choice(lv)
            t['prof_off'] = True
        elif i == 19 and lv:
            use()
            t = rng.choice(lv)
            t['prof_used'] = t['prof_used']
            cand = [q for q in P if q is not p and q['alive'] and (not q['uses']['spec'])]
            if cand:
                rng.choice(cand)['spec_blocked'] = True
        elif i == 20 and lv:
            use()
            t = rng.choice(lv)
            if rng.randint(1, 20) >= 11:
                say(f"  🗳 кик: P{t['seat']}")
                death(t, 'vote', str(p['seat']))
        elif i == 22 and c == 1:
            use()
            st['no_rpdi_cycle'] = c
        elif i == 23:
            use()
            p['shield'] = True
        elif i == 1:
            cand = [q for q in P if q is not p and q['alive'] and (not q['uses']['spec'])]
            if cand:
                use()
                p['bonus'] += 1
        elif i == 2:
            if lv:
                use()
                t = rng.choice(lv)
                t['demon'] = True
        elif i == 12:
            use()
            st['last_wound_undo'] = True
        elif i == 16:
            if lv:
                use()
                reveal(rng.choice(lv))
        if p['uses']['spec']:
            p['spec_used'] = True

    def ghost_phase(c):
        for g in ghosts():
            g['tokens'] += C['ghost_token_per_cycle'] * (2 if C['tokens2'] else 1)
            if g.get('exiled') and rng.random() < 0.5:
                g['exiled'] = False
                g['frozen'] = 0
                say(f"  P{g['seat']} возвращается из изгнания")
            if g.get('back2'):
                g['back2'] -= 1
                if g['back2'] == 0:
                    g['alive'] = False
                    g['dead_c'] = c
                    say(f"  P{g['seat']}: срок возврата истёк")
            if C['ghost_bets']:
                if g['tokens'] >= 1:
                    bet = rng.randint(1, max(1, len(alive())))
                    g['tokens'] -= 1
                    st['bets'] += 1
                    g['_bet'] = bet
            if not C['soul_cards']:
                continue
            if shad:
                idx = rng.randrange(len(shad))
                card = shad.pop(idx)
                g['uses']['shadow'] += 1
                st['shadow_uses'] += 1
                T('shadows')
                tag = None
                lv = alive()
                say(f"  👻 P{g['seat']}: карта мёртвых «{card[:34]}…»")
                txt = card
                if 'Раскрывает одну закрытую' in txt and lv:
                    reveal(rng.choice(lv))
                elif 'жето' in txt.lower():
                    g['tokens'] += 1
                elif '+1 РП' in txt and lv:
                    rng.choice(lv)['bonus'] += 1
                elif '−1 РП' in txt or '-1 РП' in txt:
                    pass
                elif 'убивает' in txt.lower() and lv:
                    death(rng.choice(lv), 'dead_card')
                elif 'ранит' in txt.lower() and lv:
                    wound(rng.choice(lv), 1, 'ghost')
            if g['tokens'] >= C['shop_reveal_cost'] and rng.random() < 0.25 and alive():
                g['tokens'] -= C['shop_reveal_cost']
                reveal(rng.choice(alive()))
            rc = 5 if C['revive5'] else C['revive_cost']
            if g['tokens'] >= rc and rng.random() < 0.5 and (g['dead_c'] is not None):
                g['tokens'] -= rc
                g['alive'] = True
                g['or_'] = 0
                g['revived'] = True
                st['revives'] += 1
                say(f"  ✝ P{g['seat']} восстаёт за {rc} жетонов")
        if C['ghost_bets']:
            pass

    def turn(p, c):
        if p['frozen'] > 0 and p['frozen'] < 90:
            p['frozen'] -= 1
            say(f"  P{p['seat']}: пропуск (заморожен)")
            if C['forced']:
                t = pick_target(p, need_hurt=True)
                if t is not None:
                    say(f"  ⛓ P{p['seat']}: вынужденное действие")
                    act(p, 'wound', t)
            return
        if p['frozen'] >= 90:
            say(f"  P{p['seat']}: изгнан, ожидает возврата")
            return
        p['spec_used_turn'] = False
        say(f"——— P{p['seat']} ({p['prof']}), ОР={p['or_']}, личность: агр{p['pers']['aggr']:.2f} пом{p['pers']['help']:.2f} нейтр{p['pers']['neut']:.2f} ———")
        rv, rpds, rpdi = (C['reveal_per_turn'], 1, 1 + p['bonus'])
        if C['rpdi_plus1']:
            rpdi += 1
        if SCHED.get('sched'):
            sc = SCHED['sched']
            i2 = min(c - 1, len(sc) - 1)
            rv, rpds, rpdi = (sc[i2][0], sc[i2][1], sc[i2][2] + p['bonus'])
        else:
            rpds, rpdi = (rpds, rpdi)
        if C['rpdi_extra'] and c >= 3 and (p is alive()[len(alive()) // 2]):
            rpdi += 1
        p['bonus'] = 0
        if p['no_rpds']:
            rpds = 0
            p['no_rpds'] = False
        if st.get('no_rpdi_cycle') == c:
            rpdi = 0
        if p['prof'] == 'Алкоголик' and (not p['alc']):
            p['alc'] = True
            p['alc_di'] = sorted((rng.randint(1, 20) for _ in range(4)))
            p['alc_ds'] = sorted((rng.randint(1, 20) for _ in range(3)))
            say(f"  🍺 P{p['seat']}: личные пороги Алкоголика сброшены (печатный текст листа №02)")
        reveal(p, rv)
        prof_phase(p, c)
        spec_phase(p, c)
        if rpds and p['or_'] >= 1 and (rng.random() < 0.55):
            if bv('V', p) == 'SUCC':
                p['or_'] = max(0, p['or_'] - 1)
                p['heal'] += 1
            else:
                wound(p, 1, 'self')
            rpds -= 1
        elif rpds and rng.random() < 0.75:
            if bv('V', p) == 'SUCC' and decks['инвентарь']:
                p['hand'].setdefault('инвентарь', []).append(decks['инвентарь'].pop())
            rpds -= 1
        while rpdi > 0:
            a = choose(p, c)
            if a != 'skip':
                if a == 'mass':
                    act(p, 'mass')
                elif a == 'marauder':
                    act(p, 'marauder')
                else:
                    t = pick_target(p, a == 'heal')
                    if t is not None:
                        act(p, a, t)
            rpdi -= 1
        if exch is not None and p['exch'] in ('ОБМЕН_КАРТА', 'ОБМЕН_РПД', 'ОБМЕН_СПЕЦ') and (rpds + rpdi > 0) and (rng.random() < 0.45):
            p['uses']['exch'] += 1
            st['exch_uses'] += 1
            if p['exch'] == 'ОБМЕН_КАРТА':
                k = rng.choice(CATS)
                if decks[k]:
                    p['hand'].setdefault(k, []).append(decks[k].pop())
            elif p['exch'] == 'ОБМЕН_РПД':
                p['bonus'] += 1
            elif p['exch'] == 'ОБМЕН_СПЕЦ':
                p['spec_used'] = False
                p['spec_used_turn'] = False
            say(f"  🎴 P{p['seat']} тратит обмен: {p['exch']}")
            p['exch'] = None
        elif p['exch'] == 'ОТРАТ':
            p['reflect'] = True
        elif p['exch'] == 'ПУСТО':
            p['pustoe'] = True
        elif p['exch'] == 'СПАС' and p['or_'] >= 2 and (rpds + rpdi > 0):
            p['shield'] = True
            p['exch'] = None
            say(f"  🛡 P{p['seat']} тратит обмен: спасение")
    c = 1
    while c <= C['cycle_cap']:
        st['cycle'] = c
        st['player_death'] = False
        T('breaks')
        for p in P:
            p['heal'] = 0
            if C['doll']:
                p['doll'] = None
            pass
        say(f'════ ЦИКЛ {c} ════ живых {len(alive())}, призраков {len(ghosts())}')
        if c >= 2 and exch is not None:
            for p in alive():
                p['exch'] = classify_exchange(exch.pop()) if exch else None
                p['exch_raw'] = None
        ghost_phase(c)
        if st['sniper']:
            for p in alive():
                if rng.randint(1, 20) >= 18:
                    say(f"  🎯 косой снайпер: P{p['seat']}")
                    death(p, 'sniper', 'sniper')
                    st['sniper'] = False
                    break
        before = st['deaths']
        for p in alive():
            if p['alive']:
                turn(p, c)
        if st.get('must_kill'):
            seat, mc = st['must_kill']
            if mc == c and st['deaths'] - before < 2:
                lv = alive()
                if lv:
                    v = rng.choice(lv)
                    say(f"  ☠ квота убийств не выполнена: P{v['seat']}")
                    death(v, 'quota', 'quota')
                st['must_kill'] = None
        if SCHED.get('reshuffle_hand'):
            for p in alive():
                for k, l in list(p['hand'].items()):
                    for i2 in range(len(l)):
                        if decks[k]:
                            l[i2] = decks[k].pop()
        if C['harvest'] and c >= 2:
            hm = C['harvest_mode']
            fire = True
            victims_n = max(1, int(C['harvest_k']))
            if hm == 'quiet':
                fire = False
            elif hm == 'quiet2':
                fire = st['deaths'] - before == 0
            elif hm == 'off_after_corpse':
                fire = not any((q['revived'] for q in P))
            elif hm == 'off_after_death':
                fire = st['deaths'] == 0
            elif hm == 'late':
                fire = c >= 4
            elif hm == 'escalate':
                victims_n = math.ceil(1.9 + 0.32 * len(alive())) + 1
            if fire and (not st['player_death']) and (len(alive()) >= 2):
                pool_a = alive()
                if hm == 'leader':
                    mx = max((q['kills'] for q in pool_a))
                    ld = [q for q in pool_a if q['kills'] == mx]
                    v = rng.choice(ld)
                else:
                    v = rng.choice(pool_a)
                st['harvests'] += 1
                say(f"  🌾 Жатва[{hm}]: P{v['seat']}")
                death(v, 'harvest')
                extra = victims_n - 1
                while extra > 0:
                    lv2 = alive()
                    if len(lv2) < 2:
                        break
                    v2 = rng.choice(lv2)
                    st['harvests'] += 1
                    say(f"  🌾 Жатва[{hm}]+: P{v2['seat']}")
                    death(v2, 'harvest')
                    extra -= 1
        if situation == 'hrono' and st['thr_hit']:
            st['end'] = c
            break
        if situation == 'amkary' and len(set((q['team'] for q in alive()))) <= 1:
            st['end'] = c
            break
        if C['duel_kit_c'] and len(alive()) <= 1:
            st['end'] = c
            break
        if SCHED.get('S') == 'half' or SCHED.get('places') or isinstance(SCHED.get('S'), int):
            if len(alive()) <= S:
                st['end'] = c
                break
        if c == C['cycle_cap']:
            st['end'] = c
            st['stall'] = True
            break
        c += 1
    if st['end'] is None:
        st['end'] = c
    mins = (130 + 19 * n + st['T']['acts'] * 15 + st['T']['rolls'] * 3 + st['T']['reveals'] * 10 + st['T']['specs'] * 26 + st['T']['shadows'] * 19 + st['disputes'] * 47 + st['T']['breaks'] * 60) / 60
    st['minutes'] = round(mins)
    say(f"ИТОГ: конец в цикле {st['end']}, выжили: {[p['seat'] for p in alive()]}, ~{st['minutes']} мин")
    return (st, P)
if __name__ == '__main__':
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    log = []
    st, P = run_game(seed, n, log=log)
    print('причины смертей:', st['causes'])
    print('end/deaths/harvests/revives:', st['end'], st['deaths'], st['harvests'], st['revives'])