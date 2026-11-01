# -*- coding: utf-8 -*-
"""№13/B23: ПЛАНИРОВАНИЕ РЕЗЕРВА — парное измерение пяти рук.

Руки (все на одном ядре, sit=base, семена 1..G парами):
  OFF      — канон (reserve=False, reserve_gate=False);
  RES      — мягкое планирование: бот бережёт РПД (🧊), но правило обмена остаётся мягким;
  GATE     — буквальное правило: РПД потрачены → реакция не взводится (поведение бота прежнее);
  RES+GATE — планирование при буквальном правиле (без жёсткости почти не срабатывает);
  STRICT   — RES+GATE+reserve_strict: с реактивной картой ход пропускается целиком.

Оси: N ∈ {8,12,16}; ≤100 партий на конфигурацию (лимит пользователя).

Мера из меню — «ценность сэкономленного действия». Считаем в трёх единицах:
  1) ОР:   saved (держатель не получил урон) + back (урон вернулся атакующему);
           знаменатель — or_dealt (сколько ОР вообще роздано: без него защиту не отличить
           от простого падения агрессии);
  2) действия: rpds (заявки РПДС) и acts (РПД-акты) — цена резерва;
  3) исходы: deaths/end/surv и выживаемость держателей резерва.

Парный дельта-тест против OFF: mean(рука−off) по семенам, t ≈ mean/(std/√G); ✳ |t|≥2, ✳✳ |t|≥3.

Usage: python3 run_reserve.py --games 100 --out reserve.json --md RESERVE.md
       python3 run_reserve.py --md-only        # пересобрать MD из сохранённого json
"""
import argparse, json, statistics, time
import multiprocessing as mp
import bb_full

NS = (8, 12, 16)
ARMS = [
    ('OFF',      {}),
    ('RES',      {'reserve': True}),
    ('GATE',     {'reserve_gate': True}),
    ('RES+GATE', {'reserve': True, 'reserve_gate': True}),
    ('STRICT',   {'reserve': True, 'reserve_gate': True, 'reserve_strict': True}),
]
NAMES = [a for a, _ in ARMS]
KEYS = ('end', 'deaths', 'surv', 'aggr', 'rpds', 'acts', 'turns', 'decision', 'hold', 'spend',
        'armed', 'kinds', 'gate_blocked', 'saved', 'back', 'or_dealt', 'wasted', 'lost',
        'exch', 'forced', 'kept', 'burned', 'holder_n', 'holder_surv', 'cards')


def _work(job):
    n, seed, ai = job
    name, cfg = ARMS[ai]
    st, P = bb_full.run_game(seed, n, log=None, situation='base', cfg=cfg)
    a = st['acts']
    holders = set(st['reserve_holders'])
    live = {p['seat'] for p in P if p['alive'] and not p['limbo'] and not p.get('is_doll')}
    kinds = st['reserve_arm_kinds']
    return dict(n=n, seed=seed, arm=name,
                end=st['end'], deaths=st['deaths'], surv=st['alive'],
                aggr=a.get('kill', 0) + a.get('wound', 0) + a.get('mass', 0),
                rpds=sum(st['rpds_types'].values()), acts=sum(a.values()),
                turns=st['reserve_turns'], decision=st['reserve_decision'], hold=st['reserve_hold'],
                spend=st['reserve_spend'], armed=st['reserve_armed'],
                kinds=[kinds.get('ОТРАТ', 0), kinds.get('ПУСТО', 0), kinds.get('СПАС', 0)],
                gate_blocked=st['reserve_gate_blocked'], saved=st['reserve_saved'],
                back=st['reserve_back'], or_dealt=st['or_dealt'], wasted=st['reserve_wasted'],
                lost=st['reserve_lost'], exch=st['exch_uses'], forced=st['reserve_forced'],
                kept=st['reserve_kept'], burned=st['reserve_burned'],
                holder_n=len(holders), holder_surv=len(holders & live),
                cards=sum(len(l) for p in P for l in p['hand'].values() if not p.get('is_doll')))


def agg(rows):
    g = len(rows)
    def m(k): return round(statistics.mean(r[k] for r in rows), 3)
    turns = sum(r['turns'] for r in rows) or 1
    armed = sum(r['armed'] for r in rows)
    dealt = sum(r['or_dealt'] for r in rows) or 1
    hn = sum(r['holder_n'] for r in rows)
    prot = sum(r['saved'] + r['back'] for r in rows)
    ks = [sum(r['kinds'][i] for r in rows) for i in range(3)]
    return dict(games=g, end=m('end'), deaths=m('deaths'), surv=m('surv'), aggr=m('aggr'),
                p90=sorted(r['end'] for r in rows)[int(.9 * g) - 1],
                rpds=m('rpds'), acts=m('acts'), cards=m('cards'),
                turns_pg=m('turns'), decision_pg=m('decision'), hold_pg=m('hold'),
                spend_pg=m('spend'), armed_pg=m('armed'),
                arm_rate=round(100 * armed / turns, 1),
                kinds_pct=[round(100 * k / armed, 1) if armed else 0.0 for k in ks],
                gate_blocked_pg=m('gate_blocked'),
                saved_pg=m('saved'), back_pg=m('back'), prot_pg=round(prot / g, 3),
                prot_share=round(100 * prot / dealt, 1), or_dealt_pg=m('or_dealt'),
                wasted_pg=m('wasted'), lost_pg=m('lost'), exch_pg=m('exch'),
                fired_games=round(100 * sum(1 for r in rows if (r['saved'] + r['back']) > 0) / g, 1),
                or_per_fired=round(prot / max(1, sum(1 for r in rows if (r['saved'] + r['back']) > 0)), 2),
                forced_pg=m('forced'), kept_pg=m('kept'), burned_pg=m('burned'),
                holder_n_pg=m('holder_n'),
                holder_surv_rate=round(100 * sum(r['holder_surv'] for r in rows) / hn, 1) if hn else None)


def paired(off, rows, key):
    d = [b[key] - a[key] for a, b in zip(sorted(off, key=lambda r: r['seed']),
                                         sorted(rows, key=lambda r: r['seed']))]
    mu = statistics.mean(d)
    sd = statistics.stdev(d) if len(d) > 1 else 0.0
    t = mu / (sd / len(d) ** .5) if sd else (float('inf') if mu else 0.0)
    return dict(delta=round(mu, 3), t=round(t, 2),
                same=round(100 * sum(1 for x in d if x == 0) / len(d), 1))


def sig(t):
    return '✳✳' if abs(t) >= 3 else ('✳' if abs(t) >= 2 else '')


def build_md(res, games):
    A = res['axes']
    L = ['# №13/B23: ПЛАНИРОВАНИЕ РЕЗЕРВА — отчёт', '',
         f'Прогон: {time.strftime("%Y-%m-%d %H:%M")}, семена 1..{games} (пары), N ∈ {{{", ".join(map(str, NS))}}}, ситуация base.',
         f'Всего партий: {res["total_games"]} (по {games} на каждую из {len(ARMS)} рук на ось — лимит ≤100 на конфигурацию соблюдён).', '',
         '## Что мерили и почему пять рук', '',
         'Меню №13: «бот с реактивной обменкой сознательно оставляет РПД нетронутым чаще; мера — ценность сэкономленного действия».', '',
         'Разбор канона дал две находки, которые и определили набор рук:', '',
         '1. **Гейт обмена в коде мягче правила.** Ветка взвода реактивных карт (ОТРАТ/ПУСТО/СПАС) не проверяет `used_rpd` — '
         'условие «РПД не тратились» стоит только на ветке ОБМЕН_КАРТА/ОБМЕН_РПД/ОБМЕН_СПЕЦ. '
         'Поэтому в каноне реакция взводится почти всегда, и «беречь РПД» боту незачем.',
         '2. **Флаг `save_ally` (карта СПАС) в ядре не читается нигде** — ни одного потребителя; '
         'это карта-декорация (4 из 24 в колоде обмена).', '',
         'Отсюда руки: `OFF` (канон), `RES` (мягкое планирование), `GATE` (буквальное правило без планирования), '
         '`RES+GATE` (планирование при буквальном правиле), `STRICT` (то же + сознательный пропуск всего хода).', '',
         '## Сводка (на партию)', '']
    for n in NS:
        x = A[str(n)]
        L += [f'### N{n}', '',
              '| метрика | ' + ' | '.join(NAMES) + ' |', '|' + '---|' * (len(NAMES) + 1)]
        rows = [
            ('возможностей (реактивная карта в ходу)', 'turns_pg', '{:.2f}'),
            ('…из них с реальной заявкой РПДС', 'decision_pg', '{:.2f}'),
            ('удержано заявок РПДС', 'hold_pg', '{:.2f}'),
            ('взводов реакции', 'armed_pg', '{:.2f}'),
            ('доля взвода от возможностей, %', 'arm_rate', '{:.1f}'),
            ('блокировок строгим гейтом', 'gate_blocked_pg', '{:.2f}'),
            ('жёстких пропусков хода', 'forced_pg', '{:.2f}'),
            ('резерв сохранён / не убережён', None, None),
            ('ОР сэкономлено держателю', 'saved_pg', '{:.2f}'),
            ('ОР возвращено атакующему', 'back_pg', '{:.2f}'),
            ('защита, % от всего розданного ОР', 'prot_share', '{:.1f}'),
            ('роздано ОР всего', 'or_dealt_pg', '{:.2f}'),
            ('партий, где защита сработала, %', 'fired_games', '{:.1f}'),
            ('сгорело карт при перевыдаче', 'wasted_pg', '{:.2f}'),
            ('заявок РПДС (цена)', 'rpds', '{:.2f}'),
            ('РПД-актов (цена)', 'acts', '{:.2f}'),
            ('агрессивных актов', 'aggr', '{:.2f}'),
            ('закрытых карт на финише', 'cards', '{:.2f}'),
            ('выживаемость держателей, %', 'holder_surv_rate', '{}'),
            ('смертей', 'deaths', '{:.2f}'),
            ('длительность, циклов', 'end', '{:.2f}'),
            ('p90 длительности', 'p90', '{}'),
        ]
        for label, key, fmt in rows:
            if key is None:
                cells = [f"{x[a]['kept_pg']:.2f} / {x[a]['burned_pg']:.2f}" for a in NAMES]
            else:
                cells = []
                for a in NAMES:
                    v = x[a][key]
                    cells.append('—' if v is None else fmt.format(v))
            L.append(f'| {label} | ' + ' | '.join(cells) + ' |')
        L += ['', f'**Δ против OFF (парный тест, {games} пар)**', '',
              '| метрика | ' + ' | '.join(NAMES[1:]) + ' |', '|' + '---|' * len(NAMES)]
        for key, label in (('end', 'длительность'), ('deaths', 'смерти'), ('surv', 'выжили'),
                           ('rpds', 'заявки РПДС'), ('acts', 'РПД-акты'), ('aggr', 'агрессивные акты'),
                           ('armed', 'взводы реакции'), ('prot', 'защита, ОР')):
            cells = []
            for a in NAMES[1:]:
                d = x['p_' + a][key]
                cells.append(f"{d['delta']:+.2f} (t={d['t']}){sig(d['t'])}")
            L.append(f'| {label} | ' + ' | '.join(cells) + ' |')
        L.append('| партий с тем же исходом по длительности, % | ' +
                 ' | '.join(f"{x['p_' + a]['end']['same']:.0f}" for a in NAMES[1:]) + ' |')
        L += ['', 'Состав взводов (ОТРАТ / ПУСТО / СПАС, %): ' +
              '; '.join(f"{a} {'/'.join(map(str, x[a]['kinds_pct']))}" for a in NAMES) + '.', '']
    L += ['## Ценность сэкономленного действия', '']
    L += res.get('value_lines') or ['(заполняется после прогона)']
    L += ['', '## Выводы', '']
    L += res.get('conclusions') or ['(заполняются после прогона)']
    L += ['', '## Воспроизведение', '',
          '```', 'python3 run_reserve.py --games 100 --out reserve.json --md RESERVE.md', '```', '']
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--games', type=int, default=100)
    ap.add_argument('--out', default='reserve.json')
    ap.add_argument('--md', default='RESERVE.md')
    ap.add_argument('--md-only', action='store_true')
    a = ap.parse_args()

    if a.md_only:
        res = json.load(open(a.out, encoding='utf-8'))
        open(a.md, 'w', encoding='utf-8').write(build_md(res, res['games_per_config']))
        print(f'пересобрано: {a.md}')
        return

    jobs = [(n, s, ai) for n in NS for ai in range(len(ARMS)) for s in range(1, a.games + 1)]
    print(f'партий: {len(jobs)} (осей {len(NS)} × рук {len(ARMS)} × {a.games})', flush=True)
    t0 = time.time()
    with mp.Pool(min(8, mp.cpu_count() or 2)) as pool:
        rows = pool.map(_work, jobs, chunksize=8)
    print(f'время: {time.time() - t0:.1f} с', flush=True)

    res = {'games_per_config': a.games, 'total_games': len(rows), 'ns': list(NS),
           'arms': NAMES, 'axes': {}}
    for n in NS:
        by = {name: [r for r in rows if r['n'] == n and r['arm'] == name] for name in NAMES}
        off = by['OFF']
        x = {name: agg(by[name]) for name in NAMES}
        for name in NAMES[1:]:
            x['p_' + name] = {k: paired(off, by[name], k) for k in ('end', 'deaths', 'surv', 'rpds', 'acts', 'aggr', 'armed', 'hold')}
            d = [b['saved'] + b['back'] - (o['saved'] + o['back'])
                 for o, b in zip(sorted(off, key=lambda r: r['seed']), sorted(by[name], key=lambda r: r['seed']))]
            mu = statistics.mean(d)
            sd = statistics.stdev(d) if len(d) > 1 else 0.0
            x['p_' + name]['prot'] = dict(delta=round(mu, 3),
                                          t=round(mu / (sd / len(d) ** .5), 2) if sd else (float('inf') if mu else 0.0),
                                          same=round(100 * sum(1 for v in d if v == 0) / len(d), 1))
        res['axes'][str(n)] = x
    json.dump(res, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(a.md, 'w', encoding='utf-8').write(build_md(res, a.games))
    print(f'записано: {a.out}, {a.md}')
    for n in NS:
        x = res['axes'][str(n)]
        line = [f"N{n}:"]
        for name in NAMES:
            y = x[name]
            line.append(f"{name} взводы {y['armed_pg']}({y['arm_rate']}%) защ {y['prot_pg']}ОР "
                        f"({y['prot_share']}% розданного) РПДС {y['rpds']} акты {y['acts']} "
                        f"end {y['end']} смерти {y['deaths']}")
        print('  ' + ' | '.join(line))


if __name__ == '__main__':
    main()
