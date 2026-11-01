# -*- coding: utf-8 -*-
"""B15 (№7): лимит руки hand_limit — конфиг по умолчанию ВЫКЛ (None), baseline бит-в-бит.

Правило (канон по вердикту пользователя «лимит руки пусть будет, чтобы не ломать симуляцию»):
  * hand_limit = потолок ЗАКРЫТЫХ карт в руке живого/призрака (раскрытые rev — публичная зона, не считаются);
  * карта, которая вошла бы в полную руку, СГОРАЕТ (в сброс, из обращения не возвращается), пишется строка лога;
  * обмен 1-на-1 (сделки, ОБМЕН_КАРТА-в-руку не входит) и хроно-обновление размер руки не меняют — лимит не трогают;
  * тень «close» (вернуть раскрытую в руку) на полной руке не срабатывает — карта остаётся раскрытой;
  * hand_limit=None/0 = лимита нет (канон 268 партий не меняется); осмысленные значения ≥7 = len(CATS)
    (стартовая рука = 7 карт, по одной в категорию; лимит 7 = «нулевое накопление») — см. patch_b15b_handfix.py.

Все 11 точек входа карт в руку переводятся на единый helper take(); добавляется статистика
st['limit_burns'] / st['max_hand']. Новый шаблон лога заводится в парсер (66-й), вьюер и покрытие.
Фазз усилен: hand_limit в случайных конфигах + инвариант «рука не больше лимита».

Запуск: python3 patch_b15_handlimit.py
"""
import io, hashlib

EDITS = [
 # ============ bb_full.py ============
 # 1. конфиг: новая ручка (default off)
 ('bb_full.py',
  r"""             revive_esc=False) # №8-TEST: воскрешение за жетоны дорожает +1 за каждое воскрешение (HOUSE, только тесты)
""",
  r"""             revive_esc=False, # №8-TEST: воскрешение за жетоны дорожает +1 за каждое воскрешение (HOUSE, только тесты)
             hand_limit=None)  # №7/B15: потолок закрытых карт в руке (None/0 = без лимита, канон); избыток сгорает; ≥5
"""),
 # 2. статистика партии
 ('bb_full.py',
  r"""              exch_uses=0, limbo_events=0, agenda_uses=0, rpds_types={}, ghost_archs={}, betrayals=0, demon_acts=0, deals=0)
""",
  r"""              exch_uses=0, limbo_events=0, agenda_uses=0, rpds_types={}, ghost_archs={}, betrayals=0, demon_acts=0, deals=0,
              limit_burns=0, max_hand=0)
"""),
 # 3. единая точка входа карт в руку
 ('bb_full.py',
  r"""    def closed(p): return [(k, c) for k, l in p['hand'].items() for c in l]
    def by_seat(s): return next((q for q in P if q['seat'] == s), None)
""",
  r"""    def closed(p): return [(k, c) for k, l in p['hand'].items() for c in l]
    def by_seat(s): return next((q for q in P if q['seat'] == s), None)

    # --- №7/B15: лимит руки. hand_limit=None (канон) — take() просто кладёт карту, лог/ГСЧ не меняются. ---
    def hsize(p): return sum(len(l) for l in p['hand'].values())
    def full(p): return bool(C['hand_limit']) and hsize(p) >= C['hand_limit']
    def take(p, k, c):
        # Карта входит в руку; если рука полна — СГОРАЕТ (сброс, вне обращения). True = вошла.
        if full(p):
            st['limit_burns'] += 1
            say(f'    🔥 лимит руки: P{p["seat"]} — рука полна, «{c[:38]}» сгорает')
            return False
        p['hand'].setdefault(k, []).append(c)
        if hsize(p) > st['max_hand']: st['max_hand'] = hsize(p)
        return True
"""),
 # 4. кража: успех (цель → вор) и провал (вор → цель)
 ('bb_full.py',
  r"""                k, c = rng.choice(closed(t)); t['hand'][k].remove(c); a['hand'].setdefault(k, []).append(c); a['gained'] += 1
""",
  r"""                k, c = rng.choice(closed(t)); t['hand'][k].remove(c); take(a, k, c); a['gained'] += 1
"""),
 ('bb_full.py',
  r"""                k, c = rng.choice(closed(a)); a['hand'][k].remove(c); t['hand'].setdefault(k, []).append(c)
""",
  r"""                k, c = rng.choice(closed(a)); a['hand'][k].remove(c); take(t, k, c)
"""),
 # 5. мародёрка (призрак → вор)
 ('bb_full.py',
  r"""                k, c = rng.choice(closed(g)); g['hand'][k].remove(c); a['hand'].setdefault(k, []).append(c)
""",
  r"""                k, c = rng.choice(closed(g)); g['hand'][k].remove(c); take(a, k, c)
"""),
 # 6. масс-кража: успех (цели → вор)
 ('bb_full.py',
  r"""                        k, c = rng.choice(closed(t2)); t2['hand'][k].remove(c); a['hand'].setdefault(k, []).append(c)
""",
  r"""                        k, c = rng.choice(closed(t2)); t2['hand'][k].remove(c); take(a, k, c)
"""),
 # 7. масс-кража: провал (вор → цели)
 ('bb_full.py',
  r"""                    ts[idx]['hand'].setdefault(k, []).append(c)
""",
  r"""                    take(ts[idx], k, c)
"""),
 # 8. РПДС «world»: инвентарь из колоды
 ('bb_full.py',
  r"""            if res == 'SUCC' and decks['инвентарь']: p['hand'].setdefault('инвентарь', []).append(decks['инвентарь'].pop())
""",
  r"""            if res == 'SUCC' and decks['инвентарь']: take(p, 'инвентарь', decks['инвентарь'].pop())
"""),
 # 9. РПДС «add»: карта из колоды
 ('bb_full.py',
  r"""        elif kind == 'add':
            if res == 'SUCC':
                k = rng.choice(CATS)
                if decks[k]: p['hand'].setdefault(k, []).append(decks[k].pop())
""",
  r"""        elif kind == 'add':
            if res == 'SUCC':
                k = rng.choice(CATS)
                if decks[k]: take(p, k, decks[k].pop())
"""),
 # 10. Почтальон: карта из колоды
 ('bb_full.py',
  r"""            if decks[k]: p['hand'].setdefault(k, []).append(decks[k].pop()); p['prof_used'] = True
""",
  r"""            if decks[k]: take(p, k, decks[k].pop()); p['prof_used'] = True
"""),
 # 11. спецкарта i==8: карта первого призрака → игрок
 ('bb_full.py',
  r"""                use(); g = gs[0]; k, cc = rng.choice(closed(g)); g['hand'][k].remove(cc); p['hand'].setdefault(k, []).append(cc)
""",
  r"""                use(); g = gs[0]; k, cc = rng.choice(closed(g)); g['hand'][k].remove(cc); take(p, k, cc)
"""),
 # 12. тень «close»: на полной руке карта остаётся раскрытой (кандидаты фильтруются)
 ('bb_full.py',
  r"""            elif tag == 'close' and lv:
                cand = [x for x in lv if x['rev']]
""",
  r"""            elif tag == 'close' and lv:
                cand = [x for x in lv if x['rev'] and not full(x)]   # B15: полная рука — возврат не срабатывает
"""),
 # 13. ОБМЕН_КАРТА: карта из колоды
 ('bb_full.py',
  r"""            if ex == 'ОБМЕН_КАРТА':
                k = rng.choice(CATS)
                if decks[k]: p['hand'].setdefault(k, []).append(decks[k].pop())
""",
  r"""            if ex == 'ОБМЕН_КАРТА':
                k = rng.choice(CATS)
                if decks[k]: take(p, k, decks[k].pop())
"""),
 # ============ bb_events.py: 66-й шаблон ============
 ('bb_events.py',
  r""" (r'^\s*➖ P(\d+) теряет собственную карту \[([^\]]+)\]', 'lose_card',
  lambda m: dict(seat=int(m[1]), cat=m[2])),
""",
  r""" (r'^\s*➖ P(\d+) теряет собственную карту \[([^\]]+)\]', 'lose_card',
  lambda m: dict(seat=int(m[1]), cat=m[2])),
 (r'^\s*🔥 лимит руки: P(\d+) — рука полна, «(.*)» сгорает', 'hand_limit_burn',
  lambda m: dict(seat=int(m[1]), card=m[2])),   # B15/№7: карта сгорела на полной руке
"""),
 # ============ bb_html.py: каталог рендера ленты ============
 ('bb_html.py',
  r""" lose_card:{i:'➖',l:'потеря карты',g:'карты',r:e=>one(e.seat)+'теряет собственную карту ['+esc(e.cat)+']'},
""",
  r""" lose_card:{i:'➖',l:'потеря карты',g:'карты',r:e=>one(e.seat)+'теряет собственную карту ['+esc(e.cat)+']'},
 hand_limit_burn:{i:'🔥',l:'лимит руки: сгорание',g:'карты',r:e=>one(e.seat)+'— рука полна, «'+esc(e.card)+'» сгорает'},
"""),
 # ============ coverage_test.py: ожидание + образец + живая партия с лимитом ============
 ('coverage_test.py',
  r""" '➖ P# теряет собственную карту [#]': 'lose_card',
""",
  r""" '➖ P# теряет собственную карту [#]': 'lose_card',
 '🔥 лимит руки: P# — рука полна, «#» сгорает': 'hand_limit_burn',
"""),
 ('coverage_test.py',
  r"""SAMPLES = {
""",
  r"""SAMPLES = {
 '🔥 лимит руки: P# — рука полна, «#» сгорает': '    🔥 лимит руки: P3 — рука полна, «Кровать-трансформер» сгорает',
"""),
 ('coverage_test.py',
  r"""    (5150, 8, 'base', dict(mode='rpds_economy', fear=False)), (909, 20, 'base', {}),
""",
  r"""    (5150, 8, 'base', dict(mode='rpds_economy', fear=False)), (909, 20, 'base', {}),
    (55, 12, 'base', dict(hand_limit=6)),   # B15/№7: живые сгорания лимита руки
"""),
 # ============ fuzz_test.py: ручка в конфигах + инвариант ============
 ('fuzz_test.py',
  r"""               rpds=rng.choice([0, 1, 2]), rpdi=rng.choice([0, 1, 2]), agenda_p=rng.choice([0, .25, .5]))
""",
  r"""               rpds=rng.choice([0, 1, 2]), rpdi=rng.choice([0, 1, 2]), agenda_p=rng.choice([0, .25, .5]),
               hand_limit=rng.choice([None, None, 5, 7, 10]))   # B15/№7
"""),
 ('fuzz_test.py',
  r"""        if any(p['or_'] < 0 for p in P): fails.append((combo, seed, 'negative OR'))
""",
  r"""        if any(p['or_'] < 0 for p in P): fails.append((combo, seed, 'negative OR'))
        if cfg['hand_limit'] and any(sum(len(l) for l in p['hand'].values()) > cfg['hand_limit'] for p in P):
            fails.append((combo, seed, 'hand over limit'))   # B15/№7: рука никогда не превышает потолок
"""),
]

bufs = {}
for path, old, new in EDITS:
    if path not in bufs:
        bufs[path] = io.open(path, encoding='utf-8').read()
    s = bufs[path]
    assert s.count(old) == 1, f'{path}: цель не найдена однозначно ({s.count(old)}): {old[:70]!r}'
    bufs[path] = s.replace(old, new)

import ast
for path, s in bufs.items():
    if path.endswith('.py'):
        ast.parse(s)   # синтаксис до записи

for path, s in bufs.items():
    io.open(path, 'w', encoding='utf-8').write(s)
    print(f'{path}: {hashlib.sha256(s.encode()).hexdigest()[:12]}')
print('B15 (hand_limit, №7) наложено:', len(EDITS), 'правок')
