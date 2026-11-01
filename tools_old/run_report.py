# -*- coding: utf-8 -*-
"""Одиночная витринная партия + полный отчёт (B3). Usage: python3 run_report.py [SEED] [N] [SITUATION]"""
import sys, random, bb_full

SITS = ['base', 'plane', 'pole', 'purg', 'hrono', 'amkary']
SIT_RU = dict(base='Ночь в панельке (база печати)', plane='Самолёт в Гренландию', pole='Поле на остановке',
              purg='Чистилище', hrono='Машина времени (Пьяная хронология)', amkary='Амкары и Касторама (команды)')
seed = int(sys.argv[1]) if len(sys.argv) > 1 else random.Random(20261002).randint(1, 999999)
n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
sit = sys.argv[3] if len(sys.argv) > 3 else random.Random(seed).choice(SITS)
log = []
st, P = bb_full.run_game(seed, n, log=log, situation=sit)
L = []; A = L.append
A('# ПОЛНЫЙ ОТЧЁТ ПАРТИИ «БЛИЦ БОЙ» (печатная ред. №2, D20, ядро B3)')
A('')
A(f'- Сид **{seed}**, ситуация **{SIT_RU[sit]}** (`{sit}`), игроков **{n}**.')
A(f'- Итог: конец в цикле **{st["end"]}**, выжили **{[p["seat"] for p in P if p["alive"] and not p["limbo"]]}**, '
  f'смертей {st["deaths"]}, Жатв {st["harvests"]}, воскрешений {st["revives"]}, лимбо-событий {st["limbo_events"]}.')
A(f'- Первая смерть: цикл {st["first_death"]}; нат.1 {st["nat1"]}, нат.20 {st["nat20"]}; пат {"да" if st["stall"] else "нет"}.')
A('')
A('## Игроки')
A('| Место | Профессия | Архетип (агр/пом/нейтр/кров) | Повестка | Судьба | ОР | Уб. | Раскр. | Спец/Тень/Обмен |')
A('|---|---|---|---|---|---|---|---|---|')
for p in P:
    v = p['pers']
    fate = ('лимбо' if p['limbo'] else 'жив') if p['alive'] else f'умер ц.{p["dead_c"]}'
    A(f'| P{p["seat"]} | {p["prof"][:30]} | {v["arch"]} ({v["aggr"]:.2f}/{v["help"]:.2f}/{v["neut"]:.2f}/{v["blood"]:.2f}) | '
      f'{v["agenda"] or "—"} | {fate} | {p["or_"]} | {p["kills"]} | {len(p["rev"])} | '
      f'{p["uses"]["spec"]}/{p["uses"]["shadow"]}/{p["uses"]["exch"]} |')
A('')
A('## Ход циклов')
A('| Цикл | Смертей | Жатва | Живых на конец |')
A('|---|---|---|---|')
for c, d, h, al in st['cycle_sum']:
    A(f'| {c} | {d} | {"да" if h else "нет"} | {al} |')
A('')
ta = sum(v for k, v in st['acts'].items() if not k.startswith('rpds'))
A(f'## Действия РПДИ (всего {ta})')
A('')
A(', '.join(f'{k} — {v} ({round(100*v/ta)}%)' for k, v in sorted(st['acts'].items(), key=lambda x: -x[1]) if not k.startswith('rpds')))
A('')
tr = sum(st['rpds_types'].values())
A(f'## Типы РПДС (всего {tr}, все через таблицу В)')
A('')
A(', '.join(f'{k} — {v} ({round(100*v/tr)}%)' for k, v in sorted(st['rpds_types'].items(), key=lambda x: -x[1])) if tr else '—')
A('')
tb = sum(st['bandsA'].values())
if tb:
    A(f'## Полосы таблицы А ({tb} бросков): ' + ', '.join(
        f'{lbl} — {round(100*st["bandsA"].get(k,0)/tb)}%'
        for lbl, k in (('1–4', 4), ('5–8', 8), ('9–12', 12), ('13–16', 16), ('17–20', 20))))
    A('')
A(f'## d20 ({sum(st["rollhist"].values())} бросков)')
A('')
A('`' + ' '.join(f'{f}:{st["rollhist"].get(f,0)}' for f in range(1, 21)) + '`')
A('')
tc = sum(st['causes'].values())
A(f'## Причины смертей ({tc})')
A('')
A(', '.join(f'{k} — {v} ({round(100*v/tc)}%)' for k, v in sorted(st['causes'].items(), key=lambda x: -x[1])) if tc else '—')
A('')
A('## Полный лог партии')
A('')
A('```')
L.extend(log)
A('```')
out = '\n'.join(L)
fn = f'REPORT_game_{seed}_N{n}_{sit}.md'
open(fn, 'w', encoding='utf-8').write(out)
print('отчёт:', fn, len(out), 'байт; end', st['end'], 'выжили', [p['seat'] for p in P if p['alive'] and not p['limbo']])
