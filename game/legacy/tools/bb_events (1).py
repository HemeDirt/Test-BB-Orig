# -*- coding: utf-8 -*-
"""Event-sourcing (№18) + полный разбор лога партии (B13, для HTML-вьюера №21).

Два уровня API:
  parse_log(lines)     → список событий ПОЛНОГО каталога (72 шаблона say() ядра B25),
                         каждое: {'type', 'c' (цикл), 'ln' (номер строки), ...поля}
  log_to_events(lines) → ОБРАТНО СОВМЕСТИМАЯ лента (как в №18): только старые типы,
                         поля type/c/... без 'ln'. Используется bb.py events и CLI.

Каталог покрыт тестом coverage_test.py: каждый шаблон say() из bb_full.py обязан
распознаваться (неизвестные строки → type='other', они видны в отчёте покрытия).
"""
import re, sys, json

# (regex, тип события, функция m→поля). Порядок важен: более частные шаблоны выше.
PAT = [
 # ---- структура партии ----
 (r'^\s*════ ЦИКЛ (\d+) ════ живых (\d+), призраков (\d+), лимбо (\d+)', 'cycle_start',
  lambda m: dict(c=int(m[1]), alive=int(m[2]), ghosts=int(m[3]), limbo=int(m[4]))),
 (r'^\s*ИТОГ: конец в цикле (\d+), выжили: \[([^\]]*)\]', 'final',
  lambda m: dict(end=int(m[1]), surv=[int(x) for x in re.findall(r'\d+', m[2])])),
 # ---- ход игрока ----
 (r'^\s*——— P(\d+) \((.*?)\), ОР=(\d+), агр([\d.]+) пом([\d.]+) нейтр([\d.]+) кров([\d.]+)'
  r'(?: страх([\d.]+))?(?:, повестка:([a-z_]+))?', 'turn_start',
  lambda m: dict(seat=int(m[1]), prof=m[2], **{'or': int(m[3])}, aggr=float(m[4]),
                 help=float(m[5]), neut=float(m[6]), blood=float(m[7]),
                 fear=float(m[8]) if m[8] else None, agenda=m[9] or None)),
 (r'^\s*P(\d+): пропуск \(лимбо/заморозка\)', 'skip', lambda m: dict(seat=int(m[1]))),
 (r'^\s*⏸ P(\d+) в лимбо \(([^)]*)\)', 'limbo', lambda m: dict(seat=int(m[1]), kind=m[2])),
 (r'^\s*🧸 чучело P(\d+): стоит без действий', 'doll_idle', lambda m: dict(seat=int(m[1]))),
 # ---- раскрытия / карты ----
 (r'^\s*P(\d+) раскрывает \[([^\]]+)\] «(.*)»', 'reveal',
  lambda m: dict(seat=int(m[1]), cat=m[2], card=m[3])),
 (r'^\s*➖ P(\d+) теряет собственную карту \[([^\]]+)\]', 'lose_card',
  lambda m: dict(seat=int(m[1]), cat=m[2])),
 (r'^\s*🔥 лимит руки: P(\d+) — рука полна, «(.*)» сгорает', 'hand_limit_burn',
  lambda m: dict(seat=int(m[1]), card=m[2])),   # B15/№7: карта сгорела на полной руке
 (r'^\s*🃏 драфт: P(\d+) берёт из пула \[([^\]]+)\] «(.*)»', 'draft_take',
  lambda m: dict(seat=int(m[1]), cat=m[2], card=m[3])),   # B16/№9: РПДС «add» забрал карту из общего пула
 (r'^\s*⛔ P(\d+): смерть посреди хода', 'midturn_stop',
  lambda m: dict(seat=int(m[1]))),   # B17: живой ход оборван смертью/лимбо
 (r'^\s*↯ P(\d+): тильт (вспышка|заморозка) \(temper ([+-][\d.]+), ([^)]+)\) до ц\.(\d+)', 'tilt',
  lambda m: dict(seat=int(m[1]), dir=m[2], temper=float(m[3]), src=m[4], until=int(m[5]))),   # №12/B22
 (r'^\s*🧊 P(\d+): резерв — РПД не тратятся ради обмена «([^»]+)» \(угроза ([\d.]+)\)', 'reserve',
  lambda m: dict(seat=int(m[1]), card=m[2], threat=float(m[3]))),   # №13/B23: планирование резерва
 (r'^\s*💢 P(\d+): обида на P(\d+) \(сила ([\d.]+)\) → месть', 'grudge',
  lambda m: dict(seat=int(m[1]), to=int(m[2]), force=float(m[3]))),   # №14/B25: долгая память обид — месть
 (r'^\s*📜 летописец P(\d+) вскрывает карту живого', 'chronicler', lambda m: dict(seat=int(m[1]))),
 # ---- РПДС / РПДИ / броски ----
 (r'^\s*P(\d+): РПДС «([^»]+)»', 'rpds', lambda m: dict(seat=int(m[1]), kind=m[2])),
 (r'^\s*P(\d+): МАССОВОЕ РАНЕНИЕ по (.+?) d20=(\d+)', 'mass_wound',
  lambda m: dict(seat=int(m[1]), targets=[int(x) for x in re.findall(r'\d+', m[2])], face=int(m[3]))),
 (r'^\s*P(\d+): МАСС-КРАЖА по (.+?) d20=(\d+)', 'mass_steal',
  lambda m: dict(seat=int(m[1]), targets=[int(x) for x in re.findall(r'\d+', m[2])], face=int(m[3]))),
 (r'^\s*провал масс-кражи: P(\d+) отдаёт (\d+) карт', 'mass_steal_fail',
  lambda m: dict(seat=int(m[1]), cards=int(m[2]))),
 (r'^\s*d20=(\d+) \[([АБВVB])\s*(?:/\s*([a-z_]+))?\s*\](?:\s*→\s*(\S+))?', 'roll',
  lambda m: dict(face=int(m[1]), table={'V': 'В', 'B': 'Б'}.get(m[2], m[2]),
                 kind=m[3], res=m[4])),
 # ---- урон / лечение / жизни ----
 (r'^\s*P(\d+): \+(\d) ОР → (\d+)', 'wound',
  lambda m: dict(seat=int(m[1]), amt=int(m[2]), total=int(m[3]))),
 (r'^\s*❤ P(\d+): −(\d) ОР', 'heal', lambda m: dict(seat=int(m[1]), amt=int(m[2]))),
 (r'^\s*💫 P(\d+) теряет жизнь \(осталось (\d+)\)', 'life_lost',
  lambda m: dict(seat=int(m[1]), left=int(m[2]))),
 (r'^\s*🛡 P(\d+) переживает удар \(ОР=(\d+)\)', 'survive_hit',
  lambda m: dict(seat=int(m[1]), or_=int(m[2]))),
 (r'^\s*🐾 Тварь P(\d+): автоспасение, ОР=(\d+)', 'beast_save',
  lambda m: dict(seat=int(m[1]), or_=int(m[2]))),
 (r'^\s*   давление дуэли: P(\d+) \+1 ОР', 'pressure', lambda m: dict(seat=int(m[1]))),
 # ---- смерть / жатва / воскрешение ----
 (r'^\s*💀 P(\d+) умирает \(([^)]+)\)', 'death', lambda m: dict(seat=int(m[1]), cause=m[2])),
 (r'^\s*🌾 Жатва-эскалация \(k=(\d+)\): P(\d+)', 'harvest_esc',
  lambda m: dict(seat=int(m[2]), k=int(m[1]))),
 (r'^\s*🌾 Жатва-лидер: P(\d+)', 'harvest_leader', lambda m: dict(seat=int(m[1]))),
 (r'^\s*🌾 Жатва: P(\d+)', 'harvest', lambda m: dict(seat=int(m[1]))),
 (r'^\s*🚫 Жатва отменена спецкартой P(\d+)', 'harvest_cancel', lambda m: dict(seat=int(m[1]))),
 (r'^\s*✝ P(\d+) восстаёт за (\d+) жетонов', 'revive_tokens',
  lambda m: dict(seat=int(m[1]), price=int(m[2]))),
 (r'^\s*✝ Некромант P(\d+) возвращает P(\d+)', 'revive_necro',
  lambda m: dict(seat=int(m[1]), target=int(m[2]))),
 (r'^\s*🚌 Тур\. Агент P(\d+): путёвка на жизнь — P(\d+) возвращается', 'revive_agent',
  lambda m: dict(seat=int(m[1]), target=int(m[2]))),   # B21b
 (r'^\s*☸ Буддист P(\d+): авто-реинкарнация', 'reincarnate', lambda m: dict(seat=int(m[1]))),
 (r'^\s*↔ P(\d+) вернулся из (изгнания|кика)', 'return',
  lambda m: dict(seat=int(m[1]), whence=m[2])),
 (r'^\s*⚖ суд: P(\d+) выбит навсегда', 'judged', lambda m: dict(seat=int(m[1]))),
 (r'^\s*🧸 чучело из P(\d+): место занято', 'doll_made', lambda m: dict(seat=int(m[1]))),
 (r'^\s*☠ квота не выполнена: P(\d+)', 'quota_fail', lambda m: dict(seat=int(m[1]))),
 # ---- спецкарты / тени / обмен / профессии ----
 (r'^\s*⚡ P(\d+): спецкарта #(\d+)', 'spec', lambda m: dict(seat=int(m[1]), idx=int(m[2]))),
 (r'^\s*👻 P(\d+): тень «(.*)»', 'shadow', lambda m: dict(seat=int(m[1]), card=m[2])),
 (r'^\s*🎴 P(\d+) объявляет обмен «([^»]+)»', 'exchange',
  lambda m: dict(seat=int(m[1]), card=m[2])),
 (r'^\s*P(\d+): профессия открыта: (.*)', 'prof_open', lambda m: dict(seat=int(m[1]), prof=m[2])),
 (r'^\s*🪞 P(\d+): стойка отражения объявлена', 'reflect_stance', lambda m: dict(seat=int(m[1]))),
 (r'^\s*🪞 Стекольщик P(\d+): отражение в P(\d+)', 'reflect',
  lambda m: dict(seat=int(m[1]), to=int(m[2]))),
 (r'^\s*↩ P(\d+): «обрат» возвращает урон', 'reflect_back', lambda m: dict(seat=int(m[1]))),
 (r'^\s*🔁 Сменщик P(\d+) переводит итог на P(\d+)', 'shift',
  lambda m: dict(seat=int(m[1]), to=int(m[2]))),
 (r'^\s*🍀 P(\d+): «повезёт» гасит последствие', 'lucky', lambda m: dict(seat=int(m[1]))),
 (r'^\s*🎭 P(\d+): действие по приколу', 'for_fun', lambda m: dict(seat=int(m[1]))),
 (r'^\s*🎭 P(\d+): «лечение» вхолостую', 'heal_void', lambda m: dict(seat=int(m[1]))),
 (r'^\s*наковальня не упала', 'anvil_miss', lambda m: {}),
 (r'^\s*📜 истина P(\d+): ([a-z_]+)', 'truth', lambda m: dict(seat=int(m[1]), eff=m[2])),
 (r'^\s*P(\d+): Один-1 раздаёт эффекты', 'one1', lambda m: dict(seat=int(m[1]))),
 # ---- социальные механики ----
 (r'^\s*🤝 сделка: P(\d+) ↔ P(\d+)', 'deal', lambda m: dict(a=int(m[1]), b=int(m[2]))),
 (r'^\s*💞 связка: P(\d+) ↔ P(\d+)', 'link', lambda m: dict(a=int(m[1]), b=int(m[2]))),
 (r'^\s*🗡 ПРЕДАТЕЛЬСТВО: P(\d+) рвёт пакт с P(\d+)', 'betrayal',
  lambda m: dict(by=int(m[1]), whom=int(m[2]))),
 (r'^\s*🗡 предатель P(\d+) получает новую цель: P(\d+)', 'traitor_target',
  lambda m: dict(seat=int(m[1]), target=int(m[2]))),
 (r'^\s*🗡 предатели: \[([^\]]*)\] с целями \[([^\]]*)\]', 'traitors',
  lambda m: dict(who=[int(x) for x in re.findall(r'\d+', m[1])],
                 tgt=[int(x) for x in re.findall(r'\d+', m[2])])),
 (r'^\s*🗳 кик P(\d+)', 'kick', lambda m: dict(seat=int(m[1]))),
 (r'^\s*🎬 ФИЛЬМ: герои \[([^\]]*)\], злодеи \[([^\]]*)\]', 'film',
  lambda m: dict(heroes=[int(x) for x in re.findall(r'\d+', m[1])],
                 villains=[int(x) for x in re.findall(r'\d+', m[2])])),
 (r'^\s*🎬 герой P(\d+): убийство не-злодея запрещено', 'film_guard',
  lambda m: dict(seat=int(m[1]))),
 # ---- доп. условия / вторая личность ----
 (r'^\s*🎯 доп\. условие включено: (.*)', 'cond_on', lambda m: dict(name=m[1])),
 (r'^\s*🎯 косой снайпер: P(\d+)', 'cond_sniper', lambda m: dict(seat=int(m[1]))),
 (r'^\s*🙈 слепое убийство: цель случайна → P(\d+)', 'blind_kill', lambda m: dict(seat=int(m[1]))),
 (r'^\s*🙈 слепое убийство: живых нет', 'blind_empty', lambda m: dict()),   # B14: стол вымер во время хода
 (r'^\s*👹 доп\. условие: вторая личность в P(\d+)', 'demon_on', lambda m: dict(seat=int(m[1]))),
 (r'^\s*👹 инициатива второй личности: (\d+) → (действует|спит)', 'demon_init',
  lambda m: dict(face=int(m[1]), act=(m[2] == 'действует'))),
 (r'^\s*👹 вторая личность P(\d+) действует сама: ([a-z_]+)', 'demon_act',
  lambda m: dict(seat=int(m[1]), kind=m[2])),
 # ---- ситуативные финалы ----
 (r'^\s*🎲 финал самолёта: P(\d+)', 'plane_final', lambda m: dict(seat=int(m[1]))),
]
PAT = [(re.compile(rx), t, f) for rx, t, f in PAT]

# обратная совместимость №18: какие типы уходили в старую ленту и как маппились поля
LEGACY_TYPES = {'cycle_start', 'turn_start', 'reveal', 'roll', 'wound', 'death', 'harvest',
                'spec', 'shadow', 'exchange', 'cond_sniper', 'demon_init', 'deal', 'reflect',
                'doll_made', 'film', 'betrayal', 'revive_tokens', 'revive_agent'}


def parse_log(lines):
    """Полный разбор лога: список событий с циклом и номером строки."""
    out, cur = [], 0
    for ln, line in enumerate(lines):
        if not line.strip():
            continue
        for rx, t, fn in PAT:
            m = rx.search(line)
            if m:
                d = fn(m)
                if t == 'cycle_start':
                    cur = d['c']
                d.setdefault('c', cur)
                out.append(dict(type=t, ln=ln, **d))
                break
        else:
            out.append(dict(type='other', c=cur, ln=ln, text=line.strip()))
    return out


def log_to_events(lines):
    """Лента событий формата №18 (обратно совместимо: bb.py events, events_demo.jsonl)."""
    ev = []
    for e in parse_log(lines):
        if e['type'] not in LEGACY_TYPES:
            continue
        d = {k: v for k, v in e.items() if k != 'ln'}
        if d['type'] == 'roll':                      # старая лента знала только face/table
            d = dict(type='roll', face=d['face'], table=d['table'], c=d['c'])
        elif d['type'] == 'demon_init':              # старое поле face
            d = dict(type='demon_init', face=d['face'], c=d['c'])
        elif d['type'] == 'reflect':                 # старое поле from
            d = dict(type='reflect', **{'from': d['seat']}, to=d['to'], c=d['c'])
        elif d['type'] == 'doll_made':
            d = dict(type='doll', seat=d['seat'], c=d['c'])
        elif d['type'] == 'reveal':                  # старое поле cat без текста карты
            d = dict(type='reveal', seat=d['seat'], cat=d['cat'], c=d['c'])
        elif d['type'] == 'turn_start':              # старое: seat/or
            d = dict(type='turn_start', seat=d['seat'], c=d['c'], **{'or': d['or']})
        elif d['type'] == 'exchange':
            d = dict(type='exchange', seat=d['seat'], c=d['c'])
        ev.append(d)
    return ev


if __name__ == '__main__':
    inp, out = sys.argv[1], sys.argv[2]
    ev = log_to_events(open(inp, encoding='utf-8').read().splitlines())
    with open(out, 'w', encoding='utf-8') as f:
        for e in ev:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
    print('events written:', out, len(ev))
