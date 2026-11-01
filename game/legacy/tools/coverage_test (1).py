# -*- coding: utf-8 -*-
"""B13/№21: тест ПОКРЫТИЯ парсера событий bb_events.parse_log.

Часть A (наблюдения): 26 партий на разных конфигах/ситуациях — каждая непустая строка лога
  обязана распознаться (type != 'other') и в ТИП, ожидаемый для ближайшего шаблона say()
  из bb_full.py (защита от «распознал не тем паттерном»).
Часть B (синтетика): все 72 шаблона say() из bb_full.py, включая редкие ветви, которые в
  выборке не встретились (Судья, Жатва-лидер, давление дуэли, летописец, ФИЛЬМ-герой,
  возврат из кика, потеря собственной карты) — проверяются на образцах строк.

Usage: python3 coverage_test.py   (exit 0 = покрытие полное)
"""
import re, sys, difflib, collections
import bb_full, bb_events
from bb_core import D6

NUM = re.compile(r'\d+')


def norm(s):
    """Строка лога → шаблон (числа→#, «…»→«#», […]→[#], (…)→(#))."""
    s = s.strip()
    s = NUM.sub('#', s)                       # сначала числа: иначе «0.12» даёт «#.#» вместо «#»
    s = re.sub(r'«[^»]*»', '«#»', s)
    s = re.sub(r'\[[^\]]*\]', '[#]', s)
    s = re.sub(r'\([^)]*\)', '(#)', s)
    s = re.sub(r'«#»[»"]+', '«#»', s)          # вложенные кавычки в тексте карт
    s = re.sub(r'повестка:[a-z_]+', 'повестка:#', s)
    s = re.sub(r'(:\s*)([A-Za-z_]+)\s*$', r'\1#', s)   # латинские хвосты: истина/личность → #
    s = re.sub(r'(профессия открыта:\s*).*$', r'\1#', s)
    return re.sub(r'\s+', ' ', s)


def code_templates():
    """Все строковые литералы say(...) из bb_full.py → нормализованные шаблоны."""
    src = open('bb_full.py', encoding='utf-8').read()
    i, out = 0, []
    while True:
        j = src.find('say(', i)
        if j < 0:
            break
        k = j + 4
        while src[k] in ' \n':
            k += 1
        if src[k] in 'fF':
            k += 1
        q = src[k]
        if q in '"\'':
            k += 1
            buf = []
            while True:
                if src[k] == '\\':
                    buf.append(src[k:k + 2]); k += 2; continue
                if src[k] == q:
                    break
                if src[k] == '{':
                    d = 1; k += 1
                    while d:
                        if src[k] == '{':
                            d += 1
                        elif src[k] == '}':
                            d -= 1
                        k += 1
                    buf.append('#'); continue
                buf.append(src[k]); k += 1
            out.append(norm(''.join(buf)))
        i = k
    return sorted(set(out))


# шаблон кода → ожидаемый тип события (часть A сверяет тип, часть B гоняет образцы)
EXPECT = {
 'P# раскрывает [#] «#»': 'reveal',
 'P#: +# ОР → #': 'wound',
 '❤ P#: −# ОР': 'heal',
 'P#: РПДС «#»': 'rpds',
 'P#: пропуск (#)': 'skip',
 'd#=# [#]': 'roll',
 'd#=# [#] → #': 'roll',
 '════ ЦИКЛ # ════ живых #, призраков #, лимбо #': 'cycle_start',
 'ИТОГ: конец в цикле #, выжили: #': 'final',
 '——— P# (#), ОР=#, агр# пом# нейтр# кров# страх#': 'turn_start',
 '💀 P# умирает (#)': 'death',
 '🌾 Жатва: P#': 'harvest',
 '🌾 Жатва-лидер: P#': 'harvest_leader',
 '🌾 Жатва-эскалация (#): P#': 'harvest_esc',
 '🚫 Жатва отменена спецкартой P#': 'harvest_cancel',
 '⚡ P#: спецкарта ##': 'spec',
 '👻 P#: тень «#»': 'shadow',
 '🎴 P# объявляет обмен «#» (#)': 'exchange',
 'P#: профессия открыта: #': 'prof_open',
 '✝ P# восстаёт за # жетонов': 'revive_tokens',
 '✝ Некромант P# возвращает P#': 'revive_necro',
 '☸ Буддист P#: авто-реинкарнация с новой рукой': 'reincarnate',
 '↔ P# вернулся из изгнания': 'return',
 '↔ P# вернулся из кика': 'return',
 '⚖ суд: P# выбит навсегда': 'judged',
 '🧸 чучело P#: стоит без действий (#)': 'doll_idle',
 '🧸 чучело из P#: место занято, владелец не воскреснет': 'doll_made',
 '☠ квота не выполнена: P#': 'quota_fail',
 '💫 P# теряет жизнь (#), ОР сброшены': 'life_lost',
 '🛡 P# переживает удар (#)': 'survive_hit',
 '🐾 Тварь P#: автоспасение, ОР=#': 'beast_save',
 'давление дуэли: P# +# ОР': 'pressure',
 '⏸ P# в лимбо (#)': 'limbo',
 '🪞 P#: стойка отражения объявлена (#)': 'reflect_stance',
 '🪞 Стекольщик P#: отражение в P#': 'reflect',
 '↩ P#: «#» возвращает урон': 'reflect_back',
 '🔁 Сменщик P# переводит итог на P#': 'shift',
 '🍀 P#: «#» гасит последствие': 'lucky',
 '🎭 P#: действие по приколу (#)': 'for_fun',
 '🎭 P#: «#» вхолостую (#)': 'heal_void',
 'наковальня не упала': 'anvil_miss',
 '📜 истина P#: #': 'truth',
 '📜 летописец P# вскрывает карту живого': 'chronicler',
 '🤝 сделка: P# ↔ P#': 'deal',
 '💞 связка: P# ↔ P#': 'link',
 '🗡 ПРЕДАТЕЛЬСТВО: P# рвёт пакт с P#': 'betrayal',
 '🗡 предатель P# получает новую цель: P#': 'traitor_target',
 '🗡 предатели: # с целями #': 'traitors',
 '🗳 кик P#': 'kick',
 '🎬 ФИЛЬМ: герои #, злодеи #, остальные второстепенные': 'film',
 '🎬 герой P#: убийство не-злодея запрещено → ранение': 'film_guard',
 '🎯 доп. условие включено: #': 'cond_on',
 '🎯 косой снайпер: P#': 'cond_sniper',
 '🙈 слепое убийство: цель случайна → P#': 'blind_kill',
 '🙈 слепое убийство: живых нет, цель не выбирается': 'blind_empty',
 '👹 доп. условие: вторая личность в P# (#)': 'demon_on',
 '👹 инициатива второй личности: # → #': 'demon_init',
 '👹 вторая личность P# действует сама: #': 'demon_act',
 '🎲 финал самолёта: P#': 'plane_final',
 '➖ P# теряет собственную карту [#]': 'lose_card',
 '🔥 лимит руки: P# — рука полна, «#» сгорает': 'hand_limit_burn',
 '🃏 драфт: P# берёт из пула [#] «#»': 'draft_take',
 '⛔ P#: смерть посреди хода — оставшиеся РПД и обмен сгорают': 'midturn_stop',
 '↯ P#: тильт # (#) до ц.#': 'tilt',   # №12/B22
 '🧊 P#: резерв — РПД не тратятся ради обмена «#» (#)': 'reserve',   # №13/B23
 '💢 P#: обида на P# (#) → месть': 'grudge',   # №14/B25
 '🚌 Тур. Агент P#: путёвка на жизнь — P# возвращается': 'revive_agent',
 'P#: Один-# раздаёт эффекты (#)': 'one1',
 'P#: МАССОВОЕ РАНЕНИЕ по P#,P# d#=#': 'mass_wound',
 'P#: МАСС-КРАЖА по P#,P# d#=#': 'mass_steal',
 'd#=# [#] → случайная ответка': 'roll',
 '🎯 доп. условие включено: косой снайпер': 'cond_on',
 'провал масс-кражи: P# отдаёт # карт (#)': 'mass_steal_fail',
}

# образцы строк для шаблонов, которых нет в выборке (часть B)
SAMPLES = {
 '🔥 лимит руки: P# — рука полна, «#» сгорает': '    🔥 лимит руки: P3 — рука полна, «Кровать-трансформер» сгорает',
 '🃏 драфт: P# берёт из пула [#] «#»': '  🃏 драфт: P4 берёт из пула [разум] «Спокойствие»',
 '⛔ P#: смерть посреди хода — оставшиеся РПД и обмен сгорают': '  ⛔ P2: смерть посреди хода — оставшиеся РПД и обмен сгорают',
 '↯ P#: тильт # (#) до ц.#': '  ↯ P3: тильт вспышка (temper +0.42, откат) до ц.5',
 '🧊 P#: резерв — РПД не тратятся ради обмена «#» (#)': '  🧊 P4: резерв — РПД не тратятся ради обмена «ПУСТО» (угроза 0.31)',
 '💢 P#: обида на P# (#) → месть': '  💢 P3: обида на P5 (сила 1.23) → месть',
 '🙈 слепое убийство: живых нет, цель не выбирается': '  🙈 слепое убийство: живых нет, цель не выбирается',
 'давление дуэли: P# +# ОР': '   давление дуэли: P4 +1 ОР',
 '↔ P# вернулся из кика': '  ↔ P6 вернулся из кика',
 '⚖ суд: P# выбит навсегда': '  ⚖ суд: P3 выбит навсегда',
 '➖ P# теряет собственную карту [#]': '    ➖ P5 теряет собственную карту [разум]',
 '🌾 Жатва-лидер: P#': '  🌾 Жатва-лидер: P9',
 '🎬 герой P#: убийство не-злодея запрещено → ранение': '    🎬 герой P2: убийство не-злодея запрещено → ранение',
 '📜 летописец P# вскрывает карту живого': '  📜 летописец P7 вскрывает карту живого',
 '🎬 ФИЛЬМ: герои #, злодеи #, остальные второстепенные': '  🎬 ФИЛЬМ: герои [3, 7], злодеи [1, 5], остальные второстепенные',
 '🗡 предатели: # с целями #': '  🗡 предатели: [6] с целями [7]',
 'ИТОГ: конец в цикле #, выжили: #': 'ИТОГ: конец в цикле 5, выжили: [4, 5, 6, 7]',
 '👹 инициатива второй личности: # → #': '    👹 инициатива второй личности: 18 → действует',
 '👹 вторая личность P# действует сама: #': '  👹 вторая личность P3 действует сама: kill',
 '📜 истина P#: #': '  📜 истина P7: auto_kill',
 'd#=# [#] → #': '    d20=14 [В] → SUCC',
 'P#: профессия открыта: #': '  P2: профессия открыта: Мудрец — одна истина за цикл',
 '——— P# (#), ОР=#, агр# пом# нейтр# кров# страх#':
     '——— P1 (Кондуктор — может выгнать), ОР=2, агр0.58 пом0.03 нейтр0.10 кров0.84 страх0.31, '
     'повестка:protect_one ———',
}

CASES = [
    (777, 8, 'plane', {}), (168804, 12, 'hrono', {}), (3, 6, 'amkary', {}), (2026, 16, 'base', {}),
    (99, 4, 'purg', {}), (555, 2, 'base', {}), (11, 10, 'pole', {}),
    (4242, 14, 'base', dict(harvest_mode='escalate', revive_esc=True)),
    (8, 9, 'base', dict(dice=D6, ablate='spec')), (31337, 12, 'plane', dict(pressure=True, escalation=True)),
    (606, 8, 'base', dict(traitor=True, blind_kill=True, queue_reverse=True, spec_cycle=True,
                          crit_price=True, pacifist_c1=True)),
    (1717, 10, 'amkary', dict(lives=3, harvest_mode='off', rpdi=2)),
    (5150, 8, 'base', dict(mode='rpds_economy', fear=False)), (909, 20, 'base', {}),
    (55, 12, 'base', dict(hand_limit=7)),   # B15/№7: живые сгорания лимита руки (потолок ≥7=len(CATS), B15b)
    (57, 8, 'base', dict(draft=True)),      # B16/№9: драфт раскрытых — пул + захваты РПДС «add»
    (7, 8, 'base', {}),                     # B17: живой кейс обрыва хода смертью (⛔)
    (4, 8, 'base', {}),                     # B21b: живой кейс возврата Тур. Агента (🚌)
    (3, 8, 'base', dict(tilt=True)),       # №12/B22: живой кейс тильта (↯ вспышка+заморозка)
    (2, 8, 'base', dict(reserve=True)),    # №13/B23: живой кейс планирования резерва (🧊)
    (2, 8, 'base', dict(grudge=True)),     # №14/B25: живой кейс мести по обиде (💢)
    (58, 8, 'base', dict(mode='rpds_economy', draft=True)),   # B16/№9: экономика РПДС вся на драфте
    (1234, 6, 'base', dict(harvest_mode='max2', harvest_pick='leader')),
    (42, 8, 'purg', dict(reveal=3, or_death=2)), (77, 12, 'amkary', dict(agenda_p=.9)),
    (31, 8, 'base', dict(ablate='all')), (64, 9, 'hrono', dict(hrono_start=20)),
    (81, 7, 'plane', dict(random_outcome=True, or_noise=True)),
    (23, 8, 'base', dict(pressure=True, harvest_pick='leader', lives=2)),
    (730, 12, 'base', dict(mode='rpds_economy', harvest_mode='late', spec_cycle=True)),
]


def part_a():
    tpl = code_templates()
    miss_expect = [t for t in tpl if t not in EXPECT and t not in SAMPLES]
    seen, lines_by, others, wrong = collections.Counter(), {}, collections.Counter(), collections.Counter()
    matched_tpl = collections.defaultdict(set)
    total = 0
    for seed, n, sit, cfg in CASES:
        log = []
        bb_full.run_game(seed, n, log=log, situation=sit, cfg=cfg)
        lines = [l for l in log if l.strip()]
        ev = bb_events.parse_log(log)
        assert len(ev) == len(lines), f'seed {seed}: событий {len(ev)} != строк {len(lines)}'
        for line, e in zip(lines, ev):
            total += 1
            k = norm(line)
            seen[k] += 1
            lines_by.setdefault(k, line.strip())
            if e['type'] == 'other':
                others[k] += 1
                continue
            near = difflib.get_close_matches(k, list(EXPECT), n=1, cutoff=.72)
            if near:
                matched_tpl[near[0]].add(k)
                if EXPECT[near[0]] != e['type']:
                    wrong[(k, EXPECT[near[0]], e['type'])] += 1
    return tpl, seen, lines_by, others, wrong, total, miss_expect, matched_tpl


def part_b(tpl):
    """Образцы строк для всех шаблонов кода (редкие ветви включительно)."""
    bad = []
    for t in tpl:
        sample = SAMPLES.get(t)
        if sample is None:
            continue
        ev = bb_events.parse_log([sample])
        if len(ev) != 1 or ev[0]['type'] != EXPECT.get(t):
            bad.append((t, sample, ev[:1]))
    return bad


def main():
    tpl, seen, lines_by, others, wrong, total, miss_expect, matched_tpl = part_a()
    unmatched = [k for k in seen if not difflib.get_close_matches(k, list(EXPECT), n=1, cutoff=.72)]
    bad_b = part_b(tpl)
    print(f'A. партий {len(CASES)}, строк {total}, шаблонов say() в коде {len(tpl)}, наблюдаемых форм {len(seen)}')
    print(f'   type=other (не распознано): {sum(others.values())}')
    for k, v in others.most_common(8):
        print('     ', v, lines_by[k][:95])
    print(f'   неверный тип: {sum(wrong.values())}')
    for k, v in wrong.most_common(8):
        print('     ', v, k)
    print(f'   строк без близкого шаблона кода: {len(unmatched)}')
    for k in unmatched[:8]:
        print('     ', lines_by[k][:95])
    nover = [t for t in tpl if t not in SAMPLES and t not in matched_tpl]
    print(f'B. шаблонов кода без проверки (нет ни наблюдения, ни образца): {len(nover)}')
    for t in nover[:8]:
        print('     ', t[:95])
    print(f'   шаблонов без ожидаемого типа и без образца: {len(miss_expect)}')
    for t in miss_expect[:8]:
        print('     ', t[:95])
    print(f'   образцы с ошибкой: {len(bad_b)}')
    for t, s, e in bad_b[:8]:
        print('     ', t[:60], '|', s[:60], '|', e)
    ok = not (sum(others.values()) or sum(wrong.values()) or unmatched or miss_expect or bad_b or nover)
    print('ИТОГ:', 'ПОКРЫТИЕ ПОЛНОЕ — все шаблоны ядра распознаются' if ok else 'ЕСТЬ ПРОБЕЛЫ')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
