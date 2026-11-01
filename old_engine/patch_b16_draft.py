# -*- coding: utf-8 -*-
"""B16 (№9): драфт раскрытых — конфиг draft, по умолчанию ВЫКЛ (False), baseline бит-в-бит.

Правило (HOUSE, вердикт пользователя «Отлично, но кроме профок и спецок»):
  * каждая раскрытая картой reveal() карта (а это всегда карта одной из 9 бытовых категорий —
    профки/спецки через reveal() не раскрываются) уходит НЕ в личную зону p['rev'], а в ОБЩИЙ ПУЛ;
  * РПДС «add» при успехе берёт карту сперва из пула (случайную), пул пуст — из колоды (канон);
  * «world» остаётся на колоде инвентаря; провалы «add» — по-канону (сброс своей закрытой);
  * следствия пула (честные, замеряемые): тени «del_open»/«close» и возврат lose_own по rev
    больше не находят личных раскрытых — эффекты гаснут; чучело наследует пустой rev;
  * draft=False (канон): ветки мертвы, ГСЧ не тратится, лог не меняется — 27144feca7c0f261.

Новый шаблон лога «🃏 драфт: P# берёт из пула […] «…»» = 67-й: парсер (тип draft_take),
вьюер, EXPECT/SAMPLES/CASES покрытия. Фазз: draft в переключателях + 2 инварианта.
Статистика: st['draft_takes'], st['draft_pool_peak'], st['draft_left'] (пул на момент финала).

Запуск: python3 patch_b16_draft.py
"""
import io, hashlib

EDITS = [
 # ============ bb_full.py ============
 # 1. конфиг: новая ручка (default off)
 ('bb_full.py',
  r"""             hand_limit=None)  # №7/B15: потолок закрытых карт в руке (None/0 = без лимита, канон); избыток сгорает; ≥7=len(CATS)
""",
  r"""             hand_limit=None, # №7/B15: потолок закрытых карт в руке (None/0 = без лимита, канон); избыток сгорает; ≥7=len(CATS)
             draft=False)     # №9/B16: раскрытые карты уходят в общий пул, РПДС «add» берёт оттуда (HOUSE, default off)
"""),
 # 2. статистика партии
 ('bb_full.py',
  r"""              limit_burns=0, max_hand=0)
""",
  r"""              limit_burns=0, max_hand=0, draft_takes=0, draft_pool_peak=0, draft_left=0)
"""),
 # 3. пул драфта (замыкание; в canon пуст и не трогается)
 ('bb_full.py',
  r"""    if P: st['max_hand'] = max(sum(len(l) for l in p['hand'].values()) for p in P)   # B15c: старт тоже входит в пик
""",
  r"""    if P: st['max_hand'] = max(sum(len(l) for l in p['hand'].values()) for p in P)   # B15c: старт тоже входит в пик
    draft_pool = []   # №9/B16: общий пул раскрытых карт [(категория, карта)]; живёт только при C['draft']
"""),
 # 4. reveal(): раскрытая карта → пул вместо личной зоны rev
 ('bb_full.py',
  r"""            cat, c = pick; p['hand'][cat].remove(c); p['rev'].append((cat, c))
            say(f'  P{p["seat"]} раскрывает [{cat}] «{c[:38]}»')
""",
  r"""            cat, c = pick; p['hand'][cat].remove(c)
            if C['draft']:   # №9/B16: раскрытие уходит в общий пул (личная зона rev не пополняется)
                draft_pool.append((cat, c))
                if len(draft_pool) > st['draft_pool_peak']: st['draft_pool_peak'] = len(draft_pool)
            else:
                p['rev'].append((cat, c))
            say(f'  P{p["seat"]} раскрывает [{cat}] «{c[:38]}»')
"""),
 # 5. РПДС «add»: успех — сперва драфт из пула, пул пуст — колода (канон)
 ('bb_full.py',
  r"""        elif kind == 'add':
            if res == 'SUCC':
                k = rng.choice(CATS)
                if decks[k]: take(p, k, decks[k].pop())
""",
  r"""        elif kind == 'add':
            if res == 'SUCC':
                if C['draft'] and draft_pool:   # №9/B16: раскрытые — ресурс, РПДС забирает из пула
                    k, c = draft_pool.pop(rng.randrange(len(draft_pool)))
                    st['draft_takes'] += 1
                    say(f'  🃏 драфт: P{p["seat"]} берёт из пула [{k}] «{c[:38]}»')
                    take(p, k, c)
                else:
                    k = rng.choice(CATS)
                    if decks[k]: take(p, k, decks[k].pop())
"""),
 # 6. финал: остаток пула — в статистику
 ('bb_full.py',
  r"""    st['alive'] = len(alive())
""",
  r"""    st['alive'] = len(alive())
    st['draft_left'] = len(draft_pool)   # №9/B16: сколько раскрытий так и не забрали (чистая информация)
"""),
 # ============ bb_events.py: 67-й шаблон ============
 ('bb_events.py',
  r"""  parse_log(lines)     → список событий ПОЛНОГО каталога (66 шаблонов say() ядра B15),
""",
  r"""  parse_log(lines)     → список событий ПОЛНОГО каталога (67 шаблонов say() ядра B16),
"""),
 ('bb_events.py',
  r""" (r'^\s*🔥 лимит руки: P(\d+) — рука полна, «(.*)» сгорает', 'hand_limit_burn',
  lambda m: dict(seat=int(m[1]), card=m[2])),   # B15/№7: карта сгорела на полной руке
""",
  r""" (r'^\s*🔥 лимит руки: P(\d+) — рука полна, «(.*)» сгорает', 'hand_limit_burn',
  lambda m: dict(seat=int(m[1]), card=m[2])),   # B15/№7: карта сгорела на полной руке
 (r'^\s*🃏 драфт: P(\d+) берёт из пула \[([^\]]+)\] «(.*)»', 'draft_take',
  lambda m: dict(seat=int(m[1]), cat=m[2], card=m[3])),   # B16/№9: РПДС «add» забрал карту из общего пула
"""),
 # ============ bb_html.py: рендер события во вьюере ============
 ('bb_html.py',
  r""" hand_limit_burn:{i:'🔥',l:'лимит руки: сгорание',g:'карты',r:e=>one(e.seat)+'— рука полна, «'+esc(e.card)+'» сгорает'},
""",
  r""" hand_limit_burn:{i:'🔥',l:'лимит руки: сгорание',g:'карты',r:e=>one(e.seat)+'— рука полна, «'+esc(e.card)+'» сгорает'},
 draft_take:{i:'🃏',l:'драфт из пула',g:'карты',c:'card',r:e=>one(e.seat)+'забирает из пула <b>['+esc(e.cat)+']</b> «'+esc(e.card)+'» (РПДС-драфт)'},
"""),
 # ============ coverage_test.py: EXPECT + SAMPLES + 2 кейса ============
 ('coverage_test.py',
  r"""Часть A (наблюдения): 22 партии на разных конфигах/ситуациях — каждая непустая строка лога
""",
  r"""Часть A (наблюдения): 25 партий на разных конфигах/ситуациях — каждая непустая строка лога
"""),
 ('coverage_test.py',
  r"""Часть B (синтетика): все 64 шаблона say() из bb_full.py, включая редкие ветви, которые в
""",
  r"""Часть B (синтетика): все 67 шаблонов say() из bb_full.py, включая редкие ветви, которые в
"""),
 ('coverage_test.py',
  r""" '🔥 лимит руки: P# — рука полна, «#» сгорает': 'hand_limit_burn',
""",
  r""" '🔥 лимит руки: P# — рука полна, «#» сгорает': 'hand_limit_burn',
 '🃏 драфт: P# берёт из пула [#] «#»': 'draft_take',
"""),
 ('coverage_test.py',
  r"""SAMPLES = {
 '🔥 лимит руки: P# — рука полна, «#» сгорает': '    🔥 лимит руки: P3 — рука полна, «Кровать-трансформер» сгорает',
""",
  r"""SAMPLES = {
 '🔥 лимит руки: P# — рука полна, «#» сгорает': '    🔥 лимит руки: P3 — рука полна, «Кровать-трансформер» сгорает',
 '🃏 драфт: P# берёт из пула [#] «#»': '  🃏 драфт: P4 берёт из пула [разум] «Спокойствие»',
"""),
 ('coverage_test.py',
  r"""    (55, 12, 'base', dict(hand_limit=7)),   # B15/№7: живые сгорания лимита руки (потолок ≥7=len(CATS), B15b)
""",
  r"""    (55, 12, 'base', dict(hand_limit=7)),   # B15/№7: живые сгорания лимита руки (потолок ≥7=len(CATS), B15b)
    (57, 8, 'base', dict(draft=True)),      # B16/№9: драфт раскрытых — пул + захваты РПДС «add»
    (58, 8, 'base', dict(mode='rpds_economy', draft=True)),   # B16/№9: экономика РПДС вся на драфте
"""),
 # ============ fuzz_test.py: переключатель + инварианты ============
 ('fuzz_test.py',
  r"""    TOGGLES = ['blind_kill', 'queue_reverse', 'traitor', 'spec_cycle', 'escalation', 'pressure',
               'or_noise', 'crit_price', 'pacifist_c1', 'random_outcome', 'revive_esc']
""",
  r"""    TOGGLES = ['blind_kill', 'queue_reverse', 'traitor', 'spec_cycle', 'escalation', 'pressure',
               'or_noise', 'crit_price', 'pacifist_c1', 'random_outcome', 'revive_esc', 'draft']
"""),
 ('fuzz_test.py',
  r"""        if cfg['hand_limit'] and any(sum(len(l) for l in p['hand'].values()) > cfg['hand_limit'] for p in P):
            fails.append((combo, seed, 'hand over limit'))   # B15/№7: рука никогда не превышает потолок
""",
  r"""        if cfg['hand_limit'] and any(sum(len(l) for l in p['hand'].values()) > cfg['hand_limit'] for p in P):
            fails.append((combo, seed, 'hand over limit'))   # B15/№7: рука никогда не превышает потолок
        if cfg.get('draft'):   # B16/№9: при драфте личных раскрытых нет, захватов не больше успехов «add»
            if any(p['rev'] for p in P): fails.append((combo, seed, 'rev non-empty under draft'))
            if st['draft_takes'] > st['rpds_types'].get('add', 0): fails.append((combo, seed, 'draft takes > add'))
"""),
 # ============ bb.py: ключ конфига в CLI ============
 ('bb.py',
  r"""            'random_outcome', 'ablate', 'revive_esc', 'hand_limit']
""",
  r"""            'random_outcome', 'ablate', 'revive_esc', 'hand_limit', 'draft']
"""),
 ('bb.py',
  r"""BOOL_KEYS = {'fear', 'blind_kill', 'queue_reverse', 'traitor', 'spec_cycle', 'escalation', 'pressure',
             'or_noise', 'crit_price', 'pacifist_c1', 'random_outcome', 'revive_esc'}
""",
  r"""BOOL_KEYS = {'fear', 'blind_kill', 'queue_reverse', 'traitor', 'spec_cycle', 'escalation', 'pressure',
             'or_noise', 'crit_price', 'pacifist_c1', 'random_outcome', 'revive_esc', 'draft'}
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
print('B16 (draft, №9) наложено:', len(EDITS), 'правок')
