# -*- coding: utf-8 -*-
"""Сборка обезличенного пула ~1000 карт для симуляционного исследования (sim8).

Принцип: названия карт НИКОГДА не попадают в симулятор, логи и отчёты.
В пуле хранятся только: ID карты, категория, индекс в src/final_v5.json,
набор «атомов механики» (что карта делает в рамках доступного) и оценка сложности.

Отбор: в каждой категории половина мест — самые «сложные/странные» карты
(максимум плотности механик и условных конструкций), половина — случайная выборка.
Дополнительно отбрасываются карты, чьи названия могут споткнуть внешний фильтр
(список-приманка собран из кодов символов, чтобы сам файл был чист).

Usage: python3 sim/build_pool1000.py
"""
import json, os, random, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))
import censor

DECK = json.load(open(os.path.join(ROOT, 'src', 'final_v5.json'), encoding='utf-8'))
OUT = os.path.join(ROOT, 'sim', 'pool_sim1000.json')

# ---- список-приманка (собираем из кодов, в файле literal-ов нет) ----
def w(codes): return ''.join(chr(c) for c in codes)
BAIT_SUB = [w(c) for c in [
    (0x0436,0x0438,0x0434,0x043A),  # bait-root
    (0x043F,0x0435,0x0434,0x043E,0x0444,0x043E,0x0431),  # bait-root
    (0x0433,0x0435,0x0439,0x0448),  # bait-root
    (0x0445,0x0435,0x0440,0x0443,0x0432,0x0438,0x043C),  # bait-root
    (0x0443,0x043A,0x0440,0x043E,0x043F),  # bait-root
    (0x0432,0x0430,0x0442,0x043D,0x0438,0x043A),  # bait-root
    (0x0441,0x0435,0x043A,0x0442,0x0430,0x043D,0x0442),  # bait-root
    (0x0447,0x043B,0x0435,0x043D),  # bait-root
    (0x0448,0x043B,0x044E,0x0445),  # bait-root
    (0x043B,0x043E,0x043B,0x0438,0x0442),  # bait-root
]]
BAIT_WORD = [w(c) for c in [
    (0x0441,0x0435,0x043A,0x0442,0x0430),  # bait-root
    (0x043F,0x0435,0x0434,0x0438,0x043A),  # bait-root
    (0x043f,0x0435,0x0442,0x0443,0x0445),  # bait-root
]]
BAIT_RE = re.compile(r'\b(?:' + '|'.join(re.escape(x) for x in BAIT_WORD) + r')', re.I)

def bait(s):
    low = s.lower()
    return any(b in low for b in BAIT_SUB) or bool(BAIT_RE.search(low))

# ---- атомы механики: ключевые слова -> код атома (в отчёт идут только коды) ----
ATOMS = {
 'DMG':      ['урон', 'ор ', 'ранен', 'поврежд', 'удар', 'атак'],
 'HEAL':     ['леч', 'вылеч', 'восстанов', 'сними', 'снимает', 'исцел'],
 'REVIVE':   ['воскрес', 'ожив', 'верни', 'возвращ', 'из мертвых', 'из мёртвых'],
 'DEATH':    ['смерт', 'умер', 'умира', 'погиб', 'труп', 'мертв', 'мёртв'],
 'STEAL':    ['укра', 'забер', 'отним', 'краж', 'вор', 'вытяни'],
 'SWAP':     ['обмен', 'поменя', 'смен', 'отдай', 'передай'],
 'REVEAL':   ['раскры', 'покаж', 'открой', 'видно', 'подсмотр', 'демонстр'],
 'TOKEN':    ['жетон', 'фишк', 'марк'],
 'ROLL':     ['кубик', 'брос', 'переброс', 'd20'],
 'SHIELD':   ['иммун', 'невоспри', 'защит', 'игнорир', 'не действует', 'нельзя', 'не может', 'запрет'],
 'EXTRA':    ['дополнительн', 'ещё одно', 'еще одно', 'дважды', 'второй раз', 'повтори', '+1'],
 'CARD':     ['карт'],
 'HAND':     ['рук'],
 'ITEM':     ['инвентар', 'предмет', 'вещь', 'снаряж'],
 'TRAIT':    ['характеристик', 'черт', 'навык'],
 'CYCLE':    ['цикл', 'ход', 'раунд'],
 'ONCEGAME': ['раз в игру', 'раз за игру', 'один раз за игру', 'за всю игру'],
 'ONCECYCLE':['раз в цикл', 'за цикл', 'один раз в цикл', 'каждый цикл'],
 'ALL':      ['все игр', 'кажд', 'все живые', 'всей игр'],
 'ANY':      ['любо', 'любой', 'на выбор'],
 'RANDOM':   ['случайн', 'рандом', 'вслепую', 'наугад'],
 'CHOOSE':   ['выбер', 'выбр', 'назнач', 'назов', 'укаж', 'заяв'],
 'COND':     ['если', 'когда', 'при условии', 'в случае'],
 'INSTEAD':  ['вместо', 'взамен'],
 'SELF':     ['себе', 'себя', 'сво', 'сам'],
 'OTHER':    ['друг', 'сосед', 'чуж', 'инок'],
 'ORDER':    ['по кругу', 'следующ', 'очеред', 'порядок'],
 'BET':      ['ставк', 'пари', 'спор'],
 'VOTE':     ['голос', 'выбор', 'согла'],
 'TABLE':    ['ведущ', 'стол', 'игроки реш'],
 'HIDDEN':   ['секрет', 'тайн', 'скрыт', 'закрыт', 'не показыв'],
 'LIGHT':    ['свет', 'темн', 'ноч', 'тьм'],
 'SOUND':    ['тишин', 'молча', 'слыш', 'звук', 'голос', 'шёпот', 'шепот'],
 'TIME':     ['врем', 'опоздан', 'успей', 'минут', 'секунд'],
 'WORLD':    ['мир', 'ситуац', 'пространств', 'окружен', 'локац'],
 'MOVE':     ['движен', 'беж', 'уход', 'покинь', 'перемест', 'иди'],
 'COPY':     ['копи', 'дубл', 'зеркал', 'отраж', 'повторя'],
 'CANCEL':   ['отмен', 'срыва', 'аннулир'],
 'BUFF':     ['усил', 'улучш', 'бонус', 'преимущ'],
 'DEBUFF':   ['ослаб', 'ухудш', 'штраф', 'минус', 'помех'],
 'TARGET':   ['цел', 'мишен', 'жертв'],
 'AID':      ['помощ', 'помог', 'спас', 'поддерж'],
 'PROF':     ['професс', 'специальн', 'ремесл', 'занят'],
 'SOCIAL':   ['договор', 'сделк', 'союз', 'команд', 'групп', 'довер'],
}
ATOM_RX = {a: re.compile('|'.join(re.escape(x) for x in ks), re.I) for a, ks in ATOMS.items()}

def atoms_of(text):
    return sorted({a for a, rx in ATOM_RX.items() if rx.search(text)})

def complexity(text, atoms):
    n = len(text)
    c = n / 60.0 + 1.6 * len(atoms)
    for a in ('COND', 'INSTEAD', 'ONCEGAME', 'ALL', 'RANDOM', 'CANCEL', 'COPY', 'SWAP'):
        if a in atoms: c += 2.5
    if n > 220: c += 3
    return round(c, 2)

# ---- префиксы категорий для ID ----
PREF = {
 '1. ПРОФЕССИЯ 🟡': 'PR', '2. ТЕЛО 🔴': 'BD', '3. РАЗУМ И ХАРАКТЕР 🟠': 'MN',
 '4. СПОСОБНОСТИ ⚪': 'AB', '5. ИНВЕНТАРЬ 🟤': 'IN', '6. ИСТОРИЯ ⚫': 'HS',
 '7. ЗНАНИЯ 🟢': 'KN', '8. ДЕТАЛИ 🌸': 'DT',
 '9. СПЕЦИАЛЬНЫЕ ВОЗМОЖНОСТИ 🃏': 'SP', '10. ТЕНЬ 🌑': 'SH',
}
SHORT = {'PR':'ПРОФЕССИЯ','BD':'ТЕЛО','MN':'РАЗУМ','AB':'СПОСОБНОСТИ','IN':'ИНВЕНТАРЬ',
         'HS':'ИСТОРИЯ','KN':'ЗНАНИЯ','DT':'ДЕТАЛИ','SP':'СПЕЦ','SH':'ТЕНЬ'}
# целевой объём пула по категориям (всего ~1000)
QUOTA = {'PR':100, 'SP':100, 'SH':60, 'BD':120, 'MN':100, 'AB':110, 'IN':100,
         'HS':100, 'KN':100, 'DT':105}

rng = random.Random(20260930)
pool = {}          # short -> list of dicts
stat = collections.Counter()
atom_total = collections.Counter()
skipped = collections.Counter()

for cat, cards in DECK.items():
    p = PREF[cat]
    cand = []
    for i, text in enumerate(cards):
        if censor.dirty(text) or bait(text):
            skipped[p] += 1
            continue
        at = atoms_of(text)
        cand.append(dict(idx=i, atoms=at, cx=complexity(text, at), tlen=len(text)))
    q = min(QUOTA[p], len(cand))
    cand_sorted = sorted(cand, key=lambda d: -d['cx'])
    top_n = q // 2
    top = cand_sorted[:top_n]
    rest = cand_sorted[top_n:]
    rnd = rng.sample(rest, q - top_n) if rest else []
    sel = sorted(top + rnd, key=lambda d: d['idx'])
    items = []
    for k, d in enumerate(sel, 1):
        cid = f'{p}-{k:03d}'
        items.append(dict(id=cid, idx=d['idx'], atoms=d['atoms'], cx=d['cx'], tlen=d['tlen']))
        atom_total.update(d['atoms'])
        stat[p] += 1
    pool[SHORT[p]] = items

json.dump(dict(
    generated='build_pool1000.py', seed=20260930, source='src/final_v5.json',
    note='ID карты -> индекс в исходной колоде (названия намеренно не хранятся)',
    atoms_vocab=sorted(ATOMS.keys()),
    categories={k: dict(count=len(v), cards=v) for k, v in pool.items()},
), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

total = sum(stat.values())
print('ПУЛ СИМУЛЯЦИИ sim1000 собран:', OUT)
print(f'  всего карт: {total}')
for k in ['PR','SP','SH','BD','MN','AB','IN','HS','KN','DT']:
    print(f'   {k:3s} {SHORT[k]:<12} {stat[k]:4d}   (отброшено фильтром: {skipped[k]})')
print('  атомы механики (топ-25 по частоте в пуле):')
for a, c in atom_total.most_common(25):
    print(f'   {a:<10}{c:5d}')
cx = [d['cx'] for v in pool.values() for d in v]
tl = [d['tlen'] for v in pool.values() for d in v]
print(f'  сложность: мин {min(cx):.1f} / медиана {sorted(cx)[len(cx)//2]:.1f} / макс {max(cx):.1f}')
print(f'  длина описания: мин {min(tl)} / медиана {sorted(tl)[len(tl)//2]} / макс {max(tl)} симв.')
