# -*- coding: utf-8 -*-
"""Честный симулятор партии БЛИЦ БОЙ на 8 игроков для примера-обучалки.
Раздача из реальной колоды ред. 5 (бытовой фильтр), честные d20, все механики.
Usage: python3 src/game_sim.py SEED [--quiet]
  (или через главную менюшку: python3 blitz.py play --seed SEED)
"""
import json, random, sys, os

SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip('-').isdigit() else 1
QUIET = '--quiet' in sys.argv
rng = random.Random(SEED)
LOG = []
def log(s): LOG.append(s)

# ==== ЛИЧНОСТИ БОТОВ (пересажено из клада main_backup: bb_full.py + патчи B21/B22/B25) ====
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

# --- конфигурация партии (ставится из play_game; для прямой игры через main() — дефолты) ---
N_PLAYERS = 8
ARCHS_GIVEN = None                   # список архетипов по местам или None (случайный состав)

EXTRA_NAMES = ['Женя','Рита','Гена','Света','Тимур','Оля','Витя','Настя','Лёва','Дуся',
               'Костя','Ира','Паша','Юля','Рома','Катя','Дима','Аня','Макс','Лиза',
               'Слава','Нина','Гриша','Зоя','Лера','Тихон']

# --- оптимизация процесса: партия вызывается как функция, а не через main()+sys.argv ---
def play_game(seed, quiet=True, n=8, archs=None, survivors=4):
    """Сыграть одну партию с указанным seed. Возвращает dict(лог, игроки, состояние).
    Единая точка входа для bb.py, make_web.py и любых экспериментов — без subprocess.
    n — число игроков (2..26), archs — список архетипов по местам (или случайный состав),
    survivors — сколько игроков должно выжить для окончания игры (правило S, 1..n-1)."""
    global SEED, QUIET, rng, LOG, N_PLAYERS, ARCHS_GIVEN, SURVIVORS
    SEED = seed; rng = random.Random(seed); LOG = []
    N_PLAYERS = max(2, min(26, int(n)))
    SURVIVORS = max(1, min(N_PLAYERS - 1, int(survivors)))
    ARCHS_GIVEN = archs
    setup()
    global DRAW_TENY
    DRAW_TENY = TENY[:]
    rng.shuffle(DRAW_TENY)
    # стартовый кадр наблюдателя (состав, личности, руки до первого хода)
    LOG.append({'__ev': True, 't': 'snapshot', 'cycle': 0, 'seat': 0, 'name': '',
                'arch': '', 'prof': '', 'snap': _make_snap(0)})
    c = 1
    while c <= 10:
        if not run_cycle(c): break
        c += 1
    finish_log()
    # разделение потока: текстовые строки vs структурированные события
    lines = [x for x in LOG if isinstance(x, str)]
    events = [x for x in LOG if isinstance(x, dict)]
    return {'seed': seed, 'log': lines, 'events': events, 'players': P, 'state': STATE}

def score_line():
    """Формирует итоговую SCORE-строку (параметр партии) из STATE."""
    score = 0
    if STATE['first_death_cycle'] == 2: score += 4
    elif STATE['first_death_cycle'] == 3: score += 1
    if STATE['harvest_fired']: score += 3
    if STATE['bet_hits'] >= 1: score += 2
    if STATE['token_revive']: score += 3
    if STATE['spec_revive']: score += 1
    if STATE['avoid_saved']: score += 2
    if STATE['nat20']: score += 1
    if STATE['nat1']: score += 1
    if STATE['croupier_used']: score += 1
    if STATE['cascade_hit']: score += 1
    if STATE['marauder_ok']: score += 1
    ec = STATE['end_cycle'] or 99
    if 5 <= ec <= 6: score += 3
    elif ec == 7: score += 1
    elif ec <= 4: score -= 4
    elif ec >= 8: score -= 3
    if STATE['deaths'] >= 4: score += 1
    return (f"SCORE={score} first_death={STATE['first_death_cycle']} end={ec} "
            f"harvest={STATE['harvest_fired']} bets_hit={STATE['bet_hits']} "
            f"revive={STATE['token_revive']} specrevive={STATE['spec_revive']} "
            f"avoid={STATE['avoid_saved']} deaths={STATE['deaths']}")

# КАНОН v1 (окт. 2026): игрок работает ТОЛЬКО с напечатанными колодами по 24 карты
# каждой категории — источник canon/decks.json (файлы canon/cards_*.md, расшифровки фото).
# Старые «расширенные» колоды на сотни карт (src/final_v5.json из xlsx v4) НЕ используются.
# в браузере (Pyodide) путь подменяется на _CANON_DECKS_PATH — колоды тогда лежат рядом с game_sim.py
_CANON_DECKS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'canon', 'decks.json')
# в Pyodide '/canon/decks.json' не существует (папка не копируется) — колоды ищутся рядом с файлом.
# ВАЖНО: импорт сам по себе НЕ должен падать (иначе страница не загрузится вообще);
# если decks.json не найден, DECKS останется None и упадёт позже, при первой раздаче карт.
def _load_decks():
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (_CANON_DECKS_PATH,
              os.path.join(here, 'decks.json'),
              '/decks.json',
              os.path.join(os.getcwd(), 'decks.json'),
              os.path.join(os.getcwd(), 'canon', 'decks.json')):
        try:
            return json.load(open(p, encoding='utf-8'))
        except (FileNotFoundError, OSError):
            continue
    return None
DECKS = _load_decks()

def _need_decks():
    if DECKS is None:
        raise RuntimeError('decks.json не найден (в браузере: обнови index.html до свежей сборки)')
    return DECKS
DECKS = _load_decks()

CATS = ['ТЕЛО', 'РАЗУМ', 'СПОСОБНОСТИ', 'ИНВЕНТАРЬ', 'ИСТОРИЯ', 'ЗНАНИЯ', 'ДЕТАЛИ']
POOLS = ({k: DECKS[k][:] for k in CATS} if DECKS is not None else {})
PILES = {}

def ok(card, strict=True):
    # фильтра по длине больше нет: играем всеми 24 канонными картами категории
    return True


PROFS = [
 ('Почтальон','Получает в инвентарь посылку с рандомным предметом'),
 ('Стример','Может вести стрим и собирать донаты'),
 ('Водитель','Получает любую машину на выбор'),
 ('Вор','Может украсть одну вещь (крупного инвентаря или рюкзака) за цикл, работает 3 раза'),
 ('Медик','Может воскресить другого игрока'),
 ('Крупье','Может перебросить кубик 1 раз за цикл'),
 ('Шизик','Немного поехавший, но на удивление везучий'),
 ('Каскадёр','Может принять на себя любое РП действие, направленное на другого игрока (объявляется до броска). За каждый принятый удар забирает одну карту из инвентаря спасённого'),
]
NAMES = ['Валера','Зинка','Петрович','Саня','Ленка','Эдик','Маринка','Толик']

SPECS = [
 ('extra','Добавляется одно любое РП действие', 0.65, 'цикл≥3'),
 ('immune','Игнорировать любое воздействие на себя от другого игрока на один цикл', 0.80, 'цикл==3'),
 ('fullheal','Вылечить любого игрока полностью от всего', 0.90, 'цикл==4 и есть раненые'),
 ('avoid','Дает возможность избежать смерти (использовать до смерти)', 1.00, 'цикл==4, срабатывает автоматически при смерти'),
 ('lootdead','Может украсть у мертвого игрока все что захочет сам игрок', 0.70, 'цикл≥3 и есть трупы'),
 ('additem','Добавить характеристику себе (Крупный инвентарь)', 1.00, 'цикл==2'),
 ('revive','Вернуть игрока из мертвых с дебафом на минус одно РП действие', 0.85, 'цикл≥5 и есть трупы'),
 ('autohit','Игрок может использовать любое одно РП действие с вероятностью 100% (не работает на всех)', 0.60, 'цикл≥5'),
]

TENY = [
 ('knock','Стук из-под пола — раз в цикл стучишь три раза; все игроки обязаны замолчать и потерять по одному действию на выбор'),
 ('cold','Холодное пятно на стене — там, где ты умер, стало холодно; любой игрок в этой локации теряет одно РП действие, если ты этого захочешь (раз в цикл)'),
 ('name','Тень, которая ворует имена — забираешь имя игрока: до конца цикла он не может быть назван, а значит, и выбран целью'),
 ('cancel','Часы, идущие назад — раз за игру отменяешь последнее РП действие любого игрока, включая собственное'),
 ('buff','Невидимый напарник — раз в цикл выбираешь игрока: его следующее действие выполняется вдвоём, и результат лучше на одно очко'),
 ('mirror','Зеркало, которое смотрит само — раз в цикл показываешь в зеркале одного игрока в момент, когда он врал; он обязан признаться или сбросить карту'),
 ('eyes','Ладонь на глазах — раз за игру закрываешь глаза одному игроку: он пропускает одно раскрытие карт'),
 ('dark','Тень, которая гасит свет — тушишь весь свет в ситуации; до конца цикла видишь только ты'),
 ('fake','Тень от предмета, которого нет — можешь взять предмет, которого нет, и использовать его один раз; все верят, что он настоящий'),
 ('voice','Голос, который говорит чужими ртами — выбираешь игрока, и он произносит твою фразу вслух; после этого обязан выполнить её буквально'),
 ('pain','Тень, которая забирает боль — снимаешь с живого игрока один дебафф и забираешь себе'),
 ('photo','Тень на фотографии — раз за игру появляешься на чужой фотографии: все, кто её увидит, обязаны раскрыть по одной своей карте'),
 ('whisper','Шёпот из вентиляции — живые слышат тебя только ночью; раз в цикл шепчешь одному игроку одну фразу, и он не знает, кто это был'),
 ('queue','Место в очереди — раз в цикл встаёшь в любую очередь живых: тот, кто был первым, становится последним'),
]

OBMEN = [
 ('Обмен','потрать неиспользованное РПД: обменяй одну свою закрытую карту с руки на одну закрытую карту любого живого.'),
 ('Отмена','потрать неиспользованное РПД: отмени одно РПД, совершённое против тебя с твоего прошлого хода, вместе с последствиями.'),
 ('Второе дыхание','потрать неиспользованное РПД: немедленно соверши ещё одно РПДС.'),
 ('Свидетель','потрать неиспользованное РПД: любой игрок раскрывает одну карту с руки (какую — решает он).'),
 ('Подстава','потрать неиспользованное РПД: переведи на любого игрока одно последствие действия, которое ударило по тебе с прошлого хода.'),
 ('Парамедик','потрать неиспользованное РПД: сними 1 ОР с любого игрока (лимит лечения за цикл общий).'),
 ('Заначка','потрать неиспользованное РПД: вытяни две карты характеристик из любых колод себе в руку.'),
 ('Взятка','потрать неиспользованное РПД: добавь +3 к своему броску, который ты только что сделал в этот ход.'),
]

P = []
DRAW = {}
STATE = {}
SURVIVORS = 4   # правило S: сколько игроков должно выжить (задаётся в play_game)

def setup():
    global P, DRAW, STATE
    for k in POOLS:
        pile = POOLS[k][:]
        rng.shuffle(pile)
        DRAW[k] = pile
    spec_order = SPECS[:]
    rng.shuffle(spec_order)
    n = N_PLAYERS
    # имена: базовые 8 + дополнительные; если больше — «Игрок N»
    all_names = NAMES + EXTRA_NAMES
    while len(all_names) < n: all_names.append(f'Игрок {len(all_names)+1}')
    # профессии и спецкарты: циклически при нехватке
    profs = [PROFS[i % len(PROFS)] for i in range(n)]
    specs = [tuple(spec_order[i % len(spec_order)])[:2] for i in range(n)]  # (tag, text) — совместимость со старой формой
    P = []
    for i in range(n):
        hand = {}
        for k in DRAW:
            hand[k] = [DRAW[k].pop()] if DRAW[k] else []
        p = dict(seat=i+1, name=all_names[i], prof=profs[i], hand=hand, revealed=[],
                 alive=True, spec=specs[i], spec_used=False, spec_armed=False,
                 tokens=0, ghostcard=None, ghost_used=set(), bet=None, bet_paid=False,
                 obmen=None, heal_taken=0, thief_left=3, thief_cycle=0, croupier_used_cycle=0,
                 immune=0, no_rpds=False, no_target=False, skip_reveal=False, buff=0,
                 debuff=False, died_cycle=None, resurrected=False, kills=0, dark_pen=0,
                 pers=None, rep={}, grudge={}, tilt_until=0)
        p['or'] = 0
        P.append(p)
    # ЛИЧНОСТЬ: случайный состав (без повторов пока хватает), либо заданный вручную список
    if ARCHS_GIVEN:
        for i, p in enumerate(P):
            a = ARCHS_GIVEN[i] if i < len(ARCHS_GIVEN) else rng.choice(ARCH_KEYS)
            p['pers'] = personality(rng, a)
        log("Личности ботов (заданный состав архетипов):")
    else:
        archs = ARCH_KEYS[:]
        rng.shuffle(archs)
        for i, p in enumerate(P):
            p['pers'] = personality(rng, archs[i % len(archs)])
        log("Личности ботов (случайный состав архетипов):")
    # почтальон: посылка (первый Почтальон за столом)
    posts = [p for p in P if p['prof'][0]=='Почтальон']
    if posts and DRAW.get('ИНВЕНТАРЬ'):
        posts[0]['hand']['ИНВЕНТАРЬ'].append(DRAW['ИНВЕНТАРЬ'].pop())
    obmen_pool = OBMEN[:]
    rng.shuffle(obmen_pool)
    for i, p in enumerate(P):
        p['obmen'] = obmen_pool[i % len(obmen_pool)]
    log("Личности ботов (случайный состав архетипов):")
    for p in P:
        v = p['pers']
        log(f"  P{p['seat']} {p['name']}: {ARCH_RU[v['arch']]} "
            f"(агр{v['aggr']:.2f} пом{v['help']:.2f} нейтр{v['neut']:.2f} "
            f"театр{v['theat']:.2f} воров{v['thief']:.2f} хаос{v['chaos']:.2f})")
    STATE = dict(cycle=0, player_death=False, dark=False, last_wound=None,
                 harvest_fired=False, bet_hits=0, token_revive=False, spec_revive=False,
                 avoid_saved=False, mass_done=False, croupier_used=False, cascade_hit=False,
                 marauder_ok=False, nat20=False, nat1=False, first_death_cycle=None,
                 end_cycle=None, deaths=0, queue_shift=None)

def by_seat(s): return P[s-1]
def alive_list(): return [p for p in P if p['alive']]
def ghosts(): return [p for p in P if not p['alive']]
def d20(): return rng.randint(1, 20)

def _make_snap(cycle, seat=0, name='', arch='', prof=''):
    """Единый снимок состояния всех игроков (используется в play_game/run_cycle/turn)."""
    players = []
    for q in P:
        players.append({'seat': q['seat'], 'name': q['name'], 'prof': q['prof'][0],
            'arch': ARCH_RU[q['pers']['arch']], 'arch_key': q['pers']['arch'],
            'alive': q['alive'], 'or': q['or'], 'tokens': q['tokens'], 'kills': q['kills'],
            'hand_n': sum(len(v) for v in q['hand'].values()),
            'hand': [[k, cc] for k, cs in q['hand'].items() for cc in cs],
            'revealed': [[k, cc] for k, cc in q['revealed']],
            'obmen': q['obmen'][0] if q.get('obmen') else None,
            'spec_used': q['spec_used'],
            'ghostcard': q['ghostcard'][1].split('—')[0].strip() if q['ghostcard'] else None,
            'rep': {str(k): v for k, v in (q.get('rep') or {}).items()},
            'grudge': {str(k): [v[0], v[1]] for k, v in (q.get('grudge') or {}).items()},
            'tilt': ('hot' if tilt_hot(q) else 'cold' if tilt_cold(q) else None)})
    return {'__ev': True, 't': 'snapshot', 'cycle': cycle, 'seat': seat, 'name': name,
            'arch': arch, 'prof': prof,
            'snap': {'alive': len(alive_list()), 'dark': bool(STATE.get('dark')), 'players': players}}

def closed_cards(p):
    out = []
    for k, lst in p['hand'].items():
        for c in lst: out.append((k, c))
    return out

def reveal(p, cat=None):
    if p['skip_reveal']:
        p['skip_reveal'] = False
        log(f"  P{p['seat']} {p['name']}: раскрытие пропущено (Ладонь на глазах)")
        return None
    cc = closed_cards(p)
    if not cc: return None
    if cat:
        cand = [x for x in cc if x[0]==cat] or cc
    else:
        if STATE['cycle']==1 and p['prof'][0] and not any(r[0]=='ПРОФЕССИЯ' for r in p['revealed']):
            cand = [('ПРОФЕССИЯ', p['prof'][0]+' - '+p['prof'][1])]
            p['revealed'].append(cand[0]); log(f"  P{p['seat']} {p['name']} раскрывает [ПРОФЕССИЯ] {cand[0][1]}")
            LOG.append({'__ev': True, 't': 'reveal', 'seat': p['seat'], 'name': p['name'], 'cycle': STATE['cycle'], 'kind': cand[0][0], 'card': cand[0][1]})
            return cand[0]
        cand = cc
    k, c = rng.choice(cand)
    if k in p['hand'] and c in p['hand'][k]: p['hand'][k].remove(c)
    p['revealed'].append((k, c))
    log(f"  P{p['seat']} {p['name']} раскрывает [{k}] «{c}»")
    LOG.append({'__ev': True, 't': 'reveal', 'seat': p['seat'], 'name': p['name'], 'cycle': STATE['cycle'], 'kind': k, 'card': c})
    return (k, c)

def mod_roll(p, roll, kind):
    m = roll
    if p['buff'] and kind != 'mass':
        m += p['buff']; log(f"    (+{p['buff']} от «Невидимого напарника» — призрака)"); p['buff'] = 0
    if STATE['dark'] and kind in ('рпди','mass'):
        m -= 1; log(f"    (−1: темнота после карты мёртвых «Тень, которая гасит свет»)"); p['dark_pen'] += 1
    return m

def croupier_reroll(actor, roll, kind):
    crs = [p for p in P if p['prof'][0]=='Крупье' and p['alive']]
    if not crs: return roll
    cr = crs[0]
    if cr is actor: return roll
    if cr['croupier_used_cycle'] == STATE['cycle']: return roll
    if roll >= 10: return roll
    if rng.random() < 0.55:
        cr['croupier_used_cycle'] = STATE['cycle']
        r2 = d20()
        STATE['croupier_used'] = True
        log(f"    КРУПЬЕ {cr['name']} тратит способность профессии: переброс чужого кубика {roll} → {r2}")
        return r2
    return roll

def wound(p, amt, src=''):
    ev = dict(t='wound', seat=p['seat'], name=p['name'], amt=amt, src=src, cycle=STATE['cycle'], or_after=p['or'] + (0 if (p['immune'] >= STATE['cycle'] and src != 'self') else amt), immune=(p['immune'] >= STATE['cycle'] and src != 'self'))
    LOG.append({'__ev': True, **ev})
    if p['immune'] >= STATE['cycle'] and src != 'self':
        log(f"    {p['name']} НЕВОСПРИИМЧИВ (спецкарта «Игнорировать любое воздействие»): {amt} ОР не проходит")
        return False
    p['or'] += amt
    STATE['last_wound'] = (p['seat'], amt)
    log(f"    {p['name']}: +{amt} ОР → всего {p['or']}")
    if p['or'] >= 3: check_death(p, 'ранения', src)
    return True

def check_death(p, cause, src=''):
    if not p['alive']: return
    if p['spec_armed'] and cause != 'жатва':
        p['spec_armed'] = False; p['spec_used'] = True
        p['or'] = 2
        STATE['avoid_saved'] = True
        log(f"    !!! {p['name']} уходит от смерти: спецкарта «Дает возможность избежать смерти» срабатывает. ОР сброшены до 2")
        return
    p['alive'] = False
    p['died_cycle'] = STATE['cycle']
    STATE['deaths'] += 1
    if STATE['first_death_cycle'] is None: STATE['first_death_cycle'] = STATE['cycle']
    LOG.append({'__ev': True, 't': 'death', 'seat': p['seat'], 'name': p['name'],
                'cause': cause, 'killer': src or '', 'cycle': STATE['cycle']})
    if cause == 'жатва':
        log(f"    💀 {p['name']} (место {p['seat']}) УМИРАЕТ от Жатвы")
    else:
        STATE['player_death'] = True
        killer = src
        log(f"    💀 {p['name']} (место {p['seat']}) УМИРАЕТ ({cause}, источник: {killer or '—'})")
    p['obmen'] = None

def table_A(p, roll, declared, target, kind='рпди', bribe=0):
    nat = roll
    eff = mod_roll(p, roll, kind) + bribe
    if bribe: log(f"    🃏 «Взятка»: +3 к только что сделанному броску")
    if nat == 20: STATE['nat20'] = True
    if nat == 1: STATE['nat1'] = True
    log(f"    бросок d20 = {nat}" + (f", с модификаторами {eff}" if eff != nat else "") + f" (таблица А, заявлено: {declared})")
    LOG.append({'__ev': True, 't': 'roll', 'seat': p['seat'], 'name': p['name'], 'cycle': STATE['cycle'],
                'table': 'A', 'action': declared, 'target': target['name'], 'ts': target['seat'],
                'nat': nat, 'eff': eff})
    if nat == 1:
        eff = 1
    elif nat == 20:
        eff = 20
    eff = croupier_reroll(p, eff, kind)
    if declared == 'УБИЙСТВО':
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
            wound(target, 2, p['name'])

def table_B(p, roll, action, on_succ, on_fail, kind='рпди'):
    nat = roll
    eff = mod_roll(p, roll, kind)
    if nat == 20: eff = 20; STATE['nat20'] = True
    if nat == 1: eff = 1; STATE['nat1'] = True
    log(f"    бросок d20 = {nat}" + (f", с модификаторами {eff}" if eff != nat else "") + f" (таблица Б, {action})")
    LOG.append({'__ev': True, 't': 'roll', 'seat': p['seat'], 'name': p['name'], 'cycle': STATE['cycle'],
                'table': 'B', 'action': action, 'target': '', 'ts': None, 'nat': nat, 'eff': eff})
    eff = croupier_reroll(p, eff, kind)
    if nat == 20 or (nat != 1 and eff >= 15): on_succ()
    elif nat == 1 or eff <= 10:
        tilt_trigger(p, f'провал «{action}»')   # B22: FAIL любой своей проверки Б
        on_fail()
    else: log(f"    ничего не произошло (11–14)")

def table_V(p, roll, action, on_succ, on_fail):
    nat = roll
    eff = mod_roll(p, roll, 'рпдс')
    if nat == 20: eff = 20; STATE['nat20'] = True
    if nat == 1: eff = 1; STATE['nat1'] = True
    log(f"    бросок d20 = {nat}" + (f", с модификаторами {eff}" if eff != nat else "") + f" (таблица В, {action})")
    LOG.append({'__ev': True, 't': 'roll', 'seat': p['seat'], 'name': p['name'], 'cycle': STATE['cycle'],
                'table': 'V', 'action': action, 'target': '', 'ts': None, 'nat': nat, 'eff': eff})
    if nat == 20 or (nat != 1 and eff >= 11): on_succ()
    elif nat == 1 or eff <= 9:
        tilt_trigger(p, f'провал «{action}»')   # B22: FAIL своей проверки В
        on_fail()
    else: log(f"    ничего не произошло (10)")

def rep_note(perp, victim, dw, personal=0.0):
    """B21/B25: публичный гроссбух мнений rep[x][s] + личная книга обид grudge.
    Только dict/int-операции, rng не трогает. Благо (dw>0) гасит обиду."""
    if perp is None: return
    for x in P:
        r = x.setdefault('rep', {})
        r[perp['seat']] = round(r.get(perp['seat'], 0.0) + dw, 3)
    if victim is not None and victim is not perp:
        LOG.append({'__ev': True, 't': 'rep', 'cycle': STATE['cycle'], 'by': perp['seat'],
                    'victim': victim['seat'], 'dw': dw})
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
        LOG.append({'__ev': True, 't': 'tilt', 'seat': p['seat'], 'name': p['name'], 'mode': 'hot', 'cycle': c})
        log(f"    ↯ ТИЛЬТ: {p['name']} ({ARCH_RU[v['arch']]}, горячий) вспыхивает после провала «{src}» — агрессия ↑ до цикла {c+1}")
    elif temper <= TILT_COLD:
        p['tilt_until'] = -(c + 1)
        LOG.append({'__ev': True, 't': 'tilt', 'seat': p['seat'], 'name': p['name'], 'mode': 'cold', 'cycle': c})
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
        LOG.append({'__ev': True, 't': 'venge', 'seat': p['seat'], 'name': p['name'], 'target': t['name'],
                    'ts': t['seat'], 'debt': round(grudge_eff(p, t['seat']), 2), 'cycle': STATE['cycle']})
        log(f"    💢 МЕСТЬ: {p['name']} помнит обиду — цель {t['name']} (долг {grudge_eff(p, t['seat']):.2f})")
        return t
    # B21+B25: взвешенный выбор — обида тянет цель, хорошая репутация отталкивает
    wts = []
    for q in cands:
        w = 1.0
        w *= min(REP_MAX, max(REP_MIN, 1 - REP_BIAS * q['rep'].get(p['seat'], 0.0)))
        w *= min(2.5, 1 + GR_BIAS * grudge_eff(p, q['seat']))
        wts.append(w)
    return rng.choices(cands, weights=wts)[0]

def cascade_check(actor, target, kind):
    if target is actor: return target
    cs = [p for p in P if p['prof'][0]=='Каскадёр' and p['alive'] and p is not target and p is not actor]
    if cs and rng.random() < 0.4:
        c = cs[0]
        log(f"    КАСКАДЁР {c['name']} объявляет до броска: принимает удар на себя!")
        STATE['cascade_hit'] = True
        return c
    return target

def do_steal(p, victim, blind=True, use_prof=False, label='кража'):
    def succ():
        cc = closed_cards(victim)
        if not cc:
            rv = victim['revealed'][:]
            if not rv: log(f"    у цели пусто — красть нечего"); return
            k, c = rng.choice(rv)
            victim['revealed'].remove((k, c))
        else:
            k, c = rng.choice(cc)
            victim['hand'][k].remove(c)
        p['hand'].setdefault(k, []).append(c)
        rep_note(p, victim, -0.4, -0.6)   # B21: кража — публичный вред
        log(f"    УСПЕХ: {p['name']} забирает у {victim['name']} закрытую карту [{k}] «{c}»")
    def fail():
        cc = closed_cards(p)
        if cc:
            k, c = rng.choice(cc)
            p['hand'][k].remove(c)
            victim['hand'].setdefault(k, []).append(c)
            log(f"    ПРОВАЛ (обратный эффект): {victim['name']} тянет вслепую у {p['name']} карту [{k}] «{c}»")
        else:
            log(f"    ПРОВАЛ: обратный эффект — но у {p['name']} вся рука раскрыта, стол решает: {p['name']} раскрывает ещё одну карту")
    table_B(p, d20(), label, succ, fail)

def do_heal_action(p, target):
    if target['heal_taken'] >= 1:
        log(f"    лимит лечения {target['name']} в этом цикле исчерпан — действие невозможно, РПДИ сгорает")
        return
    def succ():
        target['or'] = max(0, target['or'] - 1)
        target['heal_taken'] += 1
        rep_note(p, target, +0.8, +0.8)   # B21: успешное лечение — благо
        log(f"    УСПЕХ: {target['name']} вылечен на 1 ОР → {target['or']}")
    def fail():
        log(f"    ПРОВАЛ (обратный эффект на автора): неумелая помощь")
        wound(p, 1, 'self')
    table_B(p, d20(), f'помощь/лечение {target["name"]}', succ, fail)

def do_humiliate(p, target):
    def succ():
        cc = closed_cards(target)
        if cc:
            k, c = rng.choice(cc)
            target['hand'][k].remove(c)
            target['revealed'].append((k, c))
            rep_note(p, target, -0.4, -0.6)   # B21: унижение — публичный вред
            log(f"    УСПЕХ: {target['name']} от позора раскрывает [{k}] «{c}»")
        else:
            log(f"    УСПЕХ: {target['name']} публично унижен (эффект: сбрасывает карту обмена)")
            target['obmen'] = None
    def fail():
        cc = closed_cards(p)
        if cc:
            k, c = rng.choice(cc)
            p['hand'][k].remove(c)
            p['revealed'].append((k, c))
            log(f"    ПРОВАЛ (обратный эффект): осмеянным остался {p['name']} — раскрывает [{k}] «{c}»")
        else:
            log(f"    ПРОВАЛ: {p['name']} опозорился, стол смеётся (без механики)")
    table_B(p, d20(), f'унижение {target["name"]}', succ, fail)

def rpds_world(p):
    if DRAW['ИНВЕНТАРЬ']:
        item = DRAW['ИНВЕНТАРЬ'].pop()
        def succ():
            p['hand'].setdefault('ИНВЕНТАРЬ', []).append(item)
            log(f"    УСПЕХ: найдено в мире → в руку [{ 'ИНВЕНТАРЬ'}] «{item}»")
        def fail(): log(f"    ПРОВАЛ: мир не дал ничего, кроме синяка об косяк (обратный эффект — narrativный)")
        table_V(p, d20(), 'РПДС: обыск мира (найти предмет)', succ, fail)

def rpds_heal_self(p):
    def succ():
        p['or'] = max(0, p['or'] - 1); p['heal_taken'] += 1
        log(f"    УСПЕХ самолечения: −1 ОР → {p['or']} (лимит лечения исчерпан)")
    def fail():
        log(f"    ПРОВАЛ самолечения: стало только хуже")
        p['heal_taken'] += 1
        wound(p, 1, 'self')
    table_V(p, d20(), 'самолечение', succ, fail)

def use_obmen(p, rpds_left, rpdi_left):
    if not p['obmen']: return rpds_left, rpdi_left
    name, txt = p['obmen']
    if rpds_left + rpdi_left == 0:
        return rpds_left, rpdi_left
    use = False; 
    if name == 'Парамедик' and p['or'] >= 1 and p['heal_taken'] < 1: use = rng.random() < 0.8
    elif name == 'Отмена' and STATE['last_wound'] and STATE['last_wound'][0] == p['seat'] and p['or'] >= 1: use = rng.random() < 0.75
    elif name == 'Взятка':
        # +3 к последнему броску этого хода: пересчитываем исходный nat и повторяем стол А/Б/В
        last = next((e for e in reversed(LOG) if isinstance(e, dict) and e.get('t') == 'roll'
                     and e.get('seat') == p['seat'] and e.get('cycle') == STATE['cycle']), None)
        use = bool(last) and not last.get('bribed')
    elif name in ('Заначка','Обмен','Второе дыхание','Свидетель','Подстава'): use = rng.random() < 0.45
    if not use: return rpds_left, rpdi_left
    need_rpdi = name in ('Обмен','Свидетель','Подстава')
    if need_rpdi and rpdi_left == 0:
        if rpds_left == 0: return rpds_left, rpdi_left
    log(f"    🃏 {p['name']} тратит неиспользованное РПД и применяет карту обмена «{name}»: {txt}")
    if name == 'Взятка':
        last['bribed'] = True
        new_eff = min(20, last['nat'] + 3)
        log(f"    +3 к броску d20={last['nat']} → {new_eff}")
        last['eff'] = new_eff; last['bribe'] = 3
        tbl = last.get('table')
        if tbl == 'A':
            t = by_seat(last['ts']) if last.get('ts') else None
            if t: table_A(p, last['nat'], last['action'], t, bribe=3)
        elif tbl == 'B':
            table_B(p, last['nat'], last['action'], lambda: log("    (последствия пересчитаны с +3 — успех)"), lambda: log("    (с +3 провал отменён)"))
        else:
            table_V(p, last['nat'], last['action'], lambda: log("    (с +3 проверка В прошла)"), lambda: log("    (с +3 провал снят)"))
        if rpdi_left: rpdi_left -= 1
        else: rpds_left -= 1
    elif name == 'Парамедик':
        p['or'] = max(0, p['or']-1); p['heal_taken'] += 1
        log(f"    {p['name']}: −1 ОР → {p['or']}")
        if rpdi_left: rpdi_left -= 1
        else: rpds_left -= 1
    elif name == 'Отмена':
        seat, amt = STATE['last_wound']
        q = by_seat(seat)
        q['or'] = max(0, q['or'] - amt)
        STATE['last_wound'] = None
        log(f"    последствие отменено: {q['name']} −{amt} ОР → {q['or']}")
        if rpdi_left: rpdi_left -= 1
        else: rpds_left -= 1
    elif name == 'Заначка':
        for _ in range(2):
            k = rng.choice(list(DRAW.keys()))
            if DRAW[k]:
                c = DRAW[k].pop(); p['hand'].setdefault(k, []).append(c)
                log(f"    в руку: [{k}] «{c}»")
        if rpdi_left: rpdi_left -= 1
        else: rpds_left -= 1
    elif name == 'Обмен':
        t = pick_target(p)
        cc1, cc2 = closed_cards(p), closed_cards(t)
        if cc1 and cc2:
            k1, c1 = rng.choice(cc1); k2, c2 = rng.choice(cc2)
            p['hand'][k1].remove(c1); t['hand'][k2].remove(c2)
            p['hand'].setdefault(k2, []).append(c2); t['hand'].setdefault(k1, []).append(c1)
            log(f"    обмен вслепую с {t['name']}: {p['name']} получает [{k2}] «{c2}»")
        if rpdi_left: rpdi_left -= 1
        else: rpds_left -= 1
    elif name == 'Свидетель':
        t = pick_target(p)
        cc = closed_cards(t)
        if cc:
            k, c = rng.choice(cc)
            t['hand'][k].remove(c); t['revealed'].append((k, c))
            log(f"    {t['name']} раскрывает [{k}] «{c}»")
        if rpdi_left: rpdi_left -= 1
        else: rpds_left -= 1
    elif name == 'Второе дыхание':
        log(f"    {p['name']} получает дополнительное РПДС прямо сейчас")
        rpds_left += 1
        if rpdi_left: rpdi_left -= 1
    elif name == 'Подстава':
        log(f"    (пригодится narratively — эффект переведён на соседа слева)")
        if rpdi_left: rpdi_left -= 1
        else: rpds_left -= 1
    p['obmen'] = None
    return rpds_left, rpdi_left

def ghost_use_card(g):
    if g['ghostcard'] is None: return
    tag, text = g['ghostcard']
    if tag in g['ghost_used'] and tag in ('cancel','eyes','fake','voice','photo'):
        log(f"  👻 {g['name']}: карта мёртвых «{text.split('—')[0].strip()}» — разовая, уже использована, лежит до сброса")
        return
    living = alive_list()
    if not living: return
    log(f"  👻 {g['name']} применяет карту мёртвых: «{text}»")
    g['ghost_used'].add(tag)
    if tag == 'knock':
        for q in living: q['no_rpds'] = True
        log(f"    три стука из-под пола: все живые теряют РПДС в этом цикле")
    elif tag == 'cold':
        q = rng.choice(living); q['no_rpds'] = True
        log(f"    {q['name']} мёрзнет у холодного пятна и теряет РПДС в этом цикле")
    elif tag == 'name':
        q = max(living, key=lambda x: x['or'])
        q['no_target'] = True
        log(f"    призрак забирает имя {q['name']}: до конца цикла его нельзя выбрать целью")
    elif tag == 'cancel':
        if STATE['last_wound']:
            seat, amt = STATE['last_wound']; q = by_seat(seat)
            q['or'] = max(0, q['or']-amt); STATE['last_wound'] = None
            log(f"    время отмотано: последнее последствие ({q['name']} +{amt} ОР) отменено → {q['or']} ОР")
        else:
            log(f"    отменять нечего — ход цикла ещё ничего не принёс")
    elif tag == 'buff':
        q = rng.choice(living); q['buff'] = 1
        log(f"    невидимый напарник встаёт за спиной {q['name']}: +1 к следующему броску")
    elif tag == 'mirror':
        q = rng.choice(living); cc = closed_cards(q)
        if cc:
            k, c = rng.choice(cc); q['hand'][k].remove(c); q['revealed'].append((k, c))
            log(f"    {q['name']} увидела себя в зеркале в момент вранья и раскрывает [{k}] «{c}»")
    elif tag == 'eyes':
        q = rng.choice(living); q['skip_reveal'] = True
        log(f"    ладонь легла на глаза {q['name']}: следующее раскрытие пропущено")
    elif tag == 'dark':
        STATE['dark'] = True
        log(f"    свет гаснет во всей девятиэтажке: до конца цикла все РПДИ идут с −1 (призрак видит всё)")
    elif tag == 'fake':
        q = rng.choice(living)
        if DRAW['ИНВЕНТАРЬ']:
            c = DRAW['ИНВЕНТАРЬ'].pop(); q['hand'].setdefault('ИНВЕНТАРЬ', []).append(c)
            log(f"    призрак вручает {q['name']} предмет, которого нет: [{ 'ИНВЕНТАРЬ'}] «{c}» — и все верят, что он настоящий")
    elif tag == 'voice':
        q = rng.choice(living)
        if q['obmen']:
            q['obmen'] = None
            log(f"    {q['name']} произносит фразу призрака вслух и буквально выполняет её: сбрасывает карту обмена")
        else:
            cc = closed_cards(q)
            if cc:
                k, c = rng.choice(cc); q['hand'][k].remove(c); q['revealed'].append((k, c))
                log(f"    {q['name']} произносит фразу призрака вслух и раскрывает [{k}] «{c}»")
    elif tag == 'pain':
        hurt = [q for q in living if q['or'] >= 1 and q['heal_taken'] < 1]
        if hurt:
            q = max(hurt, key=lambda x: x['or'])
            q['or'] -= 1; q['heal_taken'] += 1
            log(f"    боль уходит: {q['name']} −1 ОР → {q['or']} (лимит лечения за цикл занят)")
        else:
            log(f"    забирать нечего — живые пока целы (или лимит лечения исчерпан)")
    elif tag == 'photo':
        for q in living:
            cc = closed_cards(q)
            if cc:
                k, c = rng.choice(cc); q['hand'][k].remove(c); q['revealed'].append((k, c))
                log(f"    призрак проявился на фото: {q['name']} раскрывает [{k}] «{c}»")
    elif tag == 'queue':
        STATE['queue_shift'] = True
        log(f"    призрак встал в очередь: первый ходящий в этом цикле пойдёт последним")
    elif tag == 'whisper':
        q = rng.choice(living)
        log(f"    {q['name']} слышит из вентиляции шёпот, которого не было (чистый вкус, без механики)")
    g['ghostcard'] = None

def ghost_bets(c):
    for g in ghosts():
        if g['tokens'] >= 1 and rng.random() < 0.85:
            if len(alive_list()) >= 6:
                k = rng.choices([0,1,2], weights=[1,5,2])[0]
            else:
                k = rng.choices([1,2,3], weights=[2,4,2])[0]
            stake = 1 if g['tokens'] < 3 else rng.choice([1,2])
            stake = min(stake, g['tokens'])
            g['tokens'] -= stake
            g['bet'] = (stake, k)
            log(f"  👻 ставка: {g['name']} ставит {stake} жетон(ов) на то, что в этом цикле будет ровно {k} смертей")
        else:
            g['bet'] = None

def resolve_bets(cycle_deaths):
    for g in ghosts():
        if g['bet']:
            stake, k = g['bet']
            if k == cycle_deaths:
                g['tokens'] += stake * 2
                STATE['bet_hits'] += 1
                log(f"  👻 СТАВКА СЫГРАЛА: {g['name']} угадал(а) «{k} смертей» и получает x{2} → {stake*2} жетонов (итого {g['tokens']})")
            else:
                log(f"  👻 ставка {g['name']} не сыграла: было {cycle_deaths} смертей, ставка на {k} — жетоны сгорают")
            g['bet'] = None

def ghost_shop(g):
    if g['tokens'] >= 3 and rng.random() < 0.4:
        g['tokens'] -= 1
        q = rng.choice(alive_list())
        log(f"  👻 магазин мёртвых: {g['name']} платит 1 жетон и подсматривает карты {q['name']} (осталось {g['tokens']})")
    if g['tokens'] >= 2 and rng.random() < 0.25:
        g['tokens'] -= 2
        q = rng.choice(alive_list()); cc = closed_cards(q)
        if cc:
            k, c = rng.choice(cc); q['hand'][k].remove(c); q['revealed'].append((k, c))
            log(f"  👻 магазин мёртвых: {g['name']} платит 2 жетона и принудительно раскрывает карту {q['name']}: [{k}] «{c}»")

def try_token_revive():
    gs = [g for g in ghosts() if g['died_cycle'] is not None and STATE['cycle'] - g['died_cycle'] >= 1]
    if not gs: return
    total = sum(g['tokens'] for g in gs)
    medik_alive = any(p['alive'] and p['prof'][0] == 'Медик' for p in P)
    if total >= 6 and (medik_alive or rng.random() < 0.5):
        gs.sort(key=lambda g: (g['died_cycle'], g['seat']))
        r = gs[0]
        for g in gs: g['tokens'] = 0
        r['alive'] = True; r['or'] = 0; r['tokens'] = 0
        r['resurrected'] = True
        r['heal_taken'] = 0
        STATE['token_revive'] = True
        log(f"  ✝️ ВОСКРЕШЕНИЕ: призраки скидывают жетоны ({total} общаком) — хватает на 6. Медик {'проводит обряд' if medik_alive else 'не нужен — призрак выкупает себя сам'}: {r['name']} возвращается к живым с 0 ОР. Неиспользованные жетоны сгорают.")

def spec_activate(p, tag, text, target=None):
    p['spec_used'] = True   # спецкарта расходуется навсегда: максимум одно использование за игру (и не чаще одного применения в ход)
    log(f"  ⚡ СПЕЦКАРТА: {p['name']} активирует «{text}»")
    LOG.append({'__ev': True, 't': 'spec', 'seat': p['seat'], 'name': p['name'],
                'cycle': STATE['cycle'], 'card': text})
    return target

def spec_chance(tag, p=None):
    """Коэффициент вероятности активации спецкарты (0..1). Из SPECS.
    Динамика по ходу игры: тильт «взвод» подталкивает карты вперёд, «оборона» — тормозит;
    чем дольше карта лежит неиспользованной, тем выше шанс (накопление +5% за цикл ожидания)."""
    base = 0.5
    for s in SPECS:
        if s[0] == tag: base = s[2]; break
    if p is None: return base
    c = STATE.get('cycle', 1)
    wait = max(0, c - 2)                      # cycles waiting unused
    coef = base * (1 + 0.05 * wait)           # накопление терпения
    if tilt_hot(p):  coef *= 1.3              # на взводе быстрее жжёт козырь
    elif tilt_cold(p): coef *= 0.6            # в обороне бережёт
    return min(0.95, max(0.05, coef))

def mass_action(p):
    cands = [q for q in alive_list() if q is not p and not q['no_target']]
    if len(cands) < 2: return False
    targets = rng.sample(cands, 2)
    log(f"  P{p['seat']} {p['name']}: МАССОВОЕ РПДИ (РАНЕНИЕ) против {targets[0]['name']} и {targets[1]['name']} — порог только 18–20")
    nat = d20(); eff = mod_roll(p, nat, 'mass')
    log(f"    бросок d20 = {nat}" + (f", с модификаторами {eff}" if eff != nat else "") + " (порог 18)")
    if eff >= 18:
        for t in targets:
            rep_note(p, t, -0.5, -0.5)   # B21: массовка — каждой цели
            wound(t, 1, p['name'])
        log(f"    УСПЕХ массовки: каждой цели +1 ОР")
    else:
        log(f"    ПРОВАЛ массовки: обратный эффект — атакующему +2 ОР")
        tilt_trigger(p, 'провал массовки')   # B22: масс-провал
        wound(p, 2, 'self')
    STATE['mass_done'] = True
    return True

def turn(p, c):
    LOG.append({'__ev': True, 't': 'turn_start', 'seat': p['seat'], 'name': p['name'],
                'arch': ARCH_RU[p['pers']['arch']], 'arch_key': p['pers']['arch'],
                'prof': p['prof'][0], 'or': p['or'], 'cycle': STATE['cycle'],
                'tilt': ('hot' if tilt_hot(p) else 'cold' if tilt_cold(p) else None)})
    tl = ' ↯взвод' if tilt_hot(p) else (' ↯оборона' if tilt_cold(p) else '')
    log(f"  ——— P{p['seat']} {p['name']} ({p['prof'][0]}, {ARCH_RU[p['pers']['arch']]}{tl}), ОР={p['or']} ———")
    n_rev = 2 if c == 1 else 1
    # --- снимок состояния ПЕРЕД ходом (для покадровой перемотки наблюдателя) ---
    LOG.append(_make_snap(c, p['seat'], p['name'], ARCH_RU[p['pers']['arch']], p['prof'][0]))
    if c == 1:
        reveal(p, 'ПРОФЕССИЯ')
        reveal(p)
    else:
        for _ in range(n_rev): reveal(p)
    rpds_left = 0 if p['no_rpds'] else 1
    rpdi_left = 0 if p['debuff'] else 1
    # второй кадр хода — уже с раскрытыми картами и актуальными руками
    LOG.append(_make_snap(c, p['seat'], p['name'], ARCH_RU[p['pers']['arch']], p['prof'][0]))
    if p['no_rpds']:
        log(f"    (РПДС в этом цикле недоступно — эффект карты мёртвых); p['no_rpds']=False")
        p['no_rpds'] = False
    if c == 1 and p['prof'][0] == 'Почтальон':
        pass
    # РПДС фаза
    if rpds_left > 0:
        if p['or'] >= 1 and (c > 1 or p['or'] == 1) and rng.random() < 0.55:
            log(f"    РПДС: самолечение")
            rpds_heal_self(p); rpds_left -= 1
        elif p['prof'][0] == 'Стример' and rng.random() < 0.6:
            log(f"    РПДС + способность профессии «Стример»: ведёт стрим с донатами")
            def succ():
                if DRAW['ИНВЕНТАРЬ']:
                    item = DRAW['ИНВЕНТАРЬ'].pop()
                    p['hand'].setdefault('ИНВЕНТАРЬ', []).append(item)
                    log(f"    УСПЕХ: зрители накидали донатов → [{ 'ИНВЕНТАРЬ'}] «{item}»")
            def fail(): log(f"    ПРОВАЛ: стрим забанили, донатов нет (обратный эффект — narrativный)")
            table_V(p, d20(), 'стрим', succ, fail); rpds_left -= 1
        elif rng.random() < 0.75:
            log(f"    РПДС: взаимодействие с миром (обыск/создание)")
            rpds_world(p); rpds_left -= 1
        else:
            log(f"    РПДС: сэкономлено (игрок копит на карту обмена)")
    # спец-биты: одна спецкарта максимум одно применение за ход и навсегда; активация по коэффициенту SPECS
    spec_tag, spec_text = p['spec']
    if not p['spec_used']:
        if spec_tag == 'additem' and c == 2 and rng.random() < spec_chance('additem', p=p):
            spec_activate(p, spec_tag, spec_text)
            if DRAW['ИНВЕНТАРЬ']:
                item = DRAW['ИНВЕНТАРЬ'].pop(); p['hand'].setdefault('ИНВЕНТАРЬ', []).append(item)
                log(f"    в руку ложится [{ 'ИНВЕНТАРЬ'}] «{item}» (раскроется позже как своя)")
        elif spec_tag == 'extra' and c >= 3 and rng.random() < spec_chance('extra', p=p):
            spec_activate(p, spec_tag, spec_text)
            rpdi_left += 1
            log(f"    до конца хода у {p['name']} есть ещё одно РПДИ")
        elif spec_tag == 'immune' and c == 3 and rng.random() < spec_chance('immune', p=p):
            spec_activate(p, spec_tag, spec_text)
            p['immune'] = c
            log(f"    до конца цикла {p['name']} игнорирует любые воздействия других игроков")
        elif spec_tag == 'lootdead' and c >= 3 and ghosts() and rng.random() < spec_chance('lootdead', p=p):
            g = rng.choice(ghosts()); cc = closed_cards(g)
            if cc:
                spec_activate(p, spec_tag, spec_text)
                k, card = rng.choice(cc); g['hand'][k].remove(card)
                p['hand'].setdefault(k, []).append(card)
                log(f"    {p['name']} забирает с трупа {g['name']} любую карту — берёт закрытую [{k}] «{card}»")
        elif spec_tag == 'fullheal' and c == 4 and rng.random() < spec_chance('fullheal', p=p):
            hurt = [q for q in alive_list() if q['or'] >= 1]
            if hurt:
                q = max(hurt, key=lambda x: x['or'])
                spec_activate(p, spec_tag, spec_text, q)
                q['or'] = 0
                log(f"    {q['name']} полностью вылечен: ОР → 0 (текст спецкарты важнее лимита лечения 1/цикл)")
            else:
                pass
        elif spec_tag == 'avoid' and c == 4:
            spec_activate(p, spec_tag, spec_text)
            p['spec_armed'] = True
            log(f"    карта активируется ЗАРАНЕЕ («использовать до смерти»): следующая смерть {p['name']} будет отменена")
        elif spec_tag == 'revive' and c >= 5 and ghosts() and not STATE['spec_revive'] and rng.random() < spec_chance('revive', p=p):
            gs = sorted(ghosts(), key=lambda g: (g['died_cycle'] or 99))
            r = gs[0]
            spec_activate(p, spec_tag, spec_text, r)
            r['alive'] = True; r['or'] = 0; r['debuff'] = True; r['resurrected'] = True
            STATE['spec_revive'] = True
            log(f"    {r['name']} возвращается с того света с 0 ОР, но с дебафом: минус одно РП действие навсегда")
        elif spec_tag == 'autohit' and c >= 5 and rng.random() < spec_chance('autohit', p=p):
            t = max(alive_list(), key=lambda x: (x['or'], rng.random()))
            if t is p: t = pick_target(p) or t
            if t is not p:
                spec_activate(p, spec_tag, spec_text, t)
                log(f"    заявлено УБИЙСТВО {t['name']} со 100% вероятностью (бросок не нужен)")
                wound(t, 2, p['name']); p['kills'] += 0
                if t['alive']: log(f"    гарантия — это успех (13–16), не крит: {t['name']} жив(а), но при смерти")
                else: p['kills'] += 1
    # РПДИ фаза
    while rpdi_left > 0:
        before = rpdi_left
        act = choose_rpdi(p, c)
        if act == 'skip':
            log(f"    РПДИ сэкономлено — карта обмена наготове")
            rpdi_left -= 1
        elif act == 'mass':
            if not mass_action(p): log(f"    массовое действие не прошло по целям")
            rpdi_left -= 1
        elif act == 'marauder':
            g = rng.choice(ghosts())
            cc = closed_cards(g)
            log(f"    РПДИ-мародёрство: тянет вслепую закрытую карту с трупа {g['name']}")
            def succ():
                k, card = rng.choice(closed_cards(g)); g['hand'][k].remove(card)
                p['hand'].setdefault(k, []).append(card)
                STATE['marauder_ok'] = True
                log(f"    УСПЕХ: добыча — [{k}] «{card}»")
            def fail():
                log(f"    ПРОВАЛ: труп не отдаёт карту (обратный эффект — по вкусу стола)")
            if cc: table_B(p, d20(), 'мародёрство', succ, fail)
            else: log(f"    на трупе пусто")
            rpdi_left -= 1
        elif act == 'wound':
            t = pick_target(p, need_dmg=True)
            t = cascade_check(p, t, 'wound')
            if t is None: rpdi_left -= 1; continue
            log(f"    РПДИ: заявлено РАНЕНИЕ {t['name']}")
            table_A(p, d20(), 'РАНЕНИЕ', t); rpdi_left -= 1
        elif act == 'kill':
            t = pick_target(p)
            t = cascade_check(p, t, 'kill')
            if t is None: rpdi_left -= 1; continue
            log(f"    РПДИ: заявлено УБИЙСТВО {t['name']}")
            table_A(p, d20(), 'УБИЙСТВО', t); rpdi_left -= 1
        elif act == 'steal':
            t = pick_target(p)
            t = cascade_check(p, t, 'steal') if False else t
            use_prof = p['prof'][0] == 'Вор' and p['thief_left'] > 0
            if use_prof:
                p['thief_left'] -= 1
                log(f"    РПДИ + профессия «Вор» ({p['thief_left']} осталось): кража вещи у {t['name']} вслепую")
            else:
                log(f"    РПДИ: кража у {t['name']} вслепую")
            do_steal(p, t, use_prof=use_prof); rpdi_left -= 1
        elif act == 'heal':
            t = max([q for q in alive_list() if q is not p and q['or'] >= 1 and q['heal_taken'] < 1], key=lambda x: x['or'], default=None)
            if t is None: rpdi_left -= 1; continue
            log(f"    РПДИ: помощь/лечение {t['name']}")
            do_heal_action(p, t); rpdi_left -= 1
        elif act == 'humiliate':
            t = pick_target(p)
            t = cascade_check(p, t, 'hum')
            if t is None: rpdi_left -= 1; continue
            log(f"    РПДИ: унижение {t['name']} (эффект заявлен: жертва раскрывает карту с руки)")
            do_humiliate(p, t); rpdi_left -= 1
        if rpdi_left == before: rpdi_left -= 1
    rpds0, rpdi0 = (0 if p['no_rpds'] else 1), (0 if p['debuff'] else 1)
    rpds_left, rpdi_left = use_obmen(p, rpds_left, rpdi_left)
    LOG.append({'__ev': True, 't': 'rpd', 'seat': p['seat'], 'name': p['name'],
                'cycle': STATE['cycle'],
                'rpds_used': max(0, rpds0 - rpds_left), 'rpdi_used': max(0, rpdi0 - rpdi_left),
                'rpds_left': rpds_left, 'rpdi_left': rpdi_left})
    if rpds_left > 0 and p['obmen'] and rng.random() < 0.3:
        pass
    if p['prof'][0] == 'Водитель' and c == 1:
        log(f"    (профессия «Водитель»: {p['name']} выбирает себе машину — по вкусу стола)")

def choose_rpdi(p, c):
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
    if c == 1:
        opts = ['humiliate','wound','steal','skip','heal']
        wts = [35, 25, 15, 20, 5]
    elif c == 2:
        opts = ['wound','kill','steal','humiliate','heal','skip']
        wts = [30, 25, 12, 13, 10, 10]
    elif c == 3:
        opts = ['wound','kill','steal','humiliate','heal','skip','marauder']
        wts = [18, 6, 12, 14, 12, 28, 10 if gs else 0]
    elif c == 4:
        opts = ['wound','kill','steal','humiliate','heal','skip','marauder','mass']
        wts = [24, 16, 10, 10, 10, 15, 10 if gs else 0, 10 if not STATE['mass_done'] else 0]
    else:
        opts = ['wound','kill','steal','humiliate','heal','skip','marauder']
        wts = [26, 30, 8, 6, 8, 10, 12 if gs else 0]
    if p['prof'][0] == 'Вор' and p['thief_left'] > 0 and c >= 2 and 'steal' in opts:
        wts[opts.index('steal')] += 15
    if p['prof'][0] == 'Медик':
        if 'heal' in opts: wts[opts.index('heal')] += 8
    if not [q for q in alive_list() if q is not p and q['or'] >= 1 and q['heal_taken'] < 1] and 'heal' in opts:
        wts[opts.index('heal')] = 0
    # личностная перекоСКА базовых весов цикла
    wts = [W(o, w_) for o, w_ in zip(opts, wts)]
    if sum(wts) <= 0: return 'skip'
    act = rng.choices(opts, weights=wts)[0]
    if tilt_hot(p) and act in ('kill', 'wound', 'mass'):
        log(f"    ↯ на взводе ({p['name']}): {ARCH_RU[v['arch']]} бьёт злее")
    if tilt_cold(p) and act == 'skip':
        log(f"    ↯ в глухой обороне ({p['name']}): {ARCH_RU[v['arch']]} пропускает удар")
    return act

def run_cycle(c):
    STATE['cycle'] = c
    LOG.append({'__ev': True, 't': 'cycle_start', 'cycle': c, 'alive': len(alive_list())})
    STATE['player_death'] = False
    STATE['dark'] = False
    STATE['last_wound'] = None
    STATE['queue_shift'] = None
    cycle_deaths_before = STATE['deaths']
    log(f"\n════════ ЦИКЛ {c} ════════")
    log(f"  Начало цикла: живых {len(alive_list())}, призраков {len(ghosts())}")
    for g in ghosts():
        g['tokens'] += 1
        log(f"  👻 {g['name']}: +1 жетон мёртвых (итого {g['tokens']})")
        if DRAW_TENY:
            g['ghostcard'] = DRAW_TENY.pop()
            log(f"  👻 {g['name']} тянет карту мёртвых: «{g['ghostcard'][1].split('—')[0].strip()}…»")
    ghost_bets(c)
    # --- снимок состояния в начале цикла (для перемотки по циклам) ---
    LOG.append(_make_snap(c))
    for g in ghosts():
        ghost_shop(g)
        ghost_use_card(g)
    if c >= 2:
        for p in alive_list():
            p['obmen'] = rng.choice(OBMEN)
            log(f"  🎴 {p['name']} тянет карту обмена «{p['obmen'][0]}»")
    if c >= 4: try_token_revive()
    for p in P: p['heal_taken'] = 0; p['no_target'] = False; p['thief_cycle'] = 0
    order = alive_list()
    if STATE['queue_shift'] and len(order) > 1:
        order = order[1:] + [order[0]]
        log(f"  (очередь сдвинута картой мёртвых «Место в очереди»)")
    for p in order:
        if not p['alive']:
            log(f"  ——— P{p['seat']} {p['name']} — мёртв, ход пропускает (призрак) ———")
            continue
        turn(p, c)
    log(f"  Конец цикла {c}: карты обмена и карты мёртвых уходят в сброс")
    cycle_deaths = STATE['deaths'] - cycle_deaths_before
    resolve_bets(cycle_deaths)
    if c >= 2 and not STATE['player_death'] and len(alive_list()) >= 2:
        STATE['harvest_fired'] = True
        v = rng.choice(sorted(alive_list(), key=lambda x: x['seat']))
        log(f"  🌾 ЖАТВА: за цикл никто не умер от действий игроков — умирает случайный живой. Бросок по номерам мест {sorted(p['seat'] for p in alive_list())}: выпало {v['seat']}")
        check_death(v, 'жатва', 'Жатва')
        cycle_deaths += 1
    alive_n = len(alive_list())
    log(f"  Живых после цикла {c}: {alive_n} (правило S={SURVIVORS})")
    if alive_n <= SURVIVORS:
        STATE['end_cycle'] = c
        LOG.append(_make_snap(c))   # финальный кадр — итоговое состояние стола
        return False
    return True

DRAW_TENY = []

def finish_log():
    """Последние строки лога: итог + SCORE (используют main() и play_game())."""
    win = [f"P{p['seat']} {p['name']} ({p['prof'][0]}, ОР={p['or']})" for p in alive_list()]
    log(f"\n════════ ИТОГ ════════")
    log(f"Игра окончена в цикле {STATE['end_cycle']}. Победили: {'; '.join(win)}")
    for p in P:
        st = 'ЖИВ' if p['alive'] else f"мёртв с цикла {p['died_cycle']}"
        log(f"  P{p['seat']} {p['name']}: {p['prof'][0]}, {st}, жетонов {p['tokens']}, воскрешён={p['resurrected']}")
    log(score_line())

def main():
    res = play_game(SEED)   # единая точка входа: setup/циклы/итог — всё внутри play_game
    if not QUIET:
        print('\n'.join(res['log']))
    else:
        print(res['log'][-1])

if __name__ == '__main__':
    main()
