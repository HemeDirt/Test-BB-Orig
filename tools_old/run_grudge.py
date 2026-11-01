# -*- coding: utf-8 -*-
"""№14/B25: ДОЛГАЯ ПАМЯТЬ ОБИД — парное измерение пяти рук.

Руки (все на одном ядре, sit=base, семена 1..G парами):
  OFF        — канон (память обид ведётся в гроссбухе, но на поведение не влияет);
  DECAY      — `grudge`: месть на всю партию с затуханием ×0.8/цикл (порог увядания 0.05);
  WINDOW     — `grudge_window`: короткая память — окно 2 цикла, без затухания внутри окна;
  DECAY+REP  — долгая память + репутация B21 (два слоя вражды вместе);
  WINDOW+REP — окно + репутация.

Оси: N ∈ {8,12,16}; ≤100 партий на конфигурацию (лимит пользователя).

Меры из меню — «месть на всю партию с затуханием vs окно 2 цикла»:
  1) поведение: grudge_revenge (цель привела в список мести обида, 💢), grudge_marked
     (взвешенный выбор пал на должника), доля от агрессивных актов, партии с местью;
  2) гроссбух: grudge_notes/soothes/peak — сколько обид вообще копится (ведётся всегда);
  3) исходы: end/deaths/surv/aggr/kills — делает ли долгая память игру длиннее/кровавее.

Парный дельта-тест против OFF: mean(рука−off) по семенам, t ≈ mean/(std/√G); ✳ |t|≥2, ✳✳ |t|≥3.
Дополнительно: DECAY против WINDOW на тех же семенах (прямой ответ на вопрос меню).

Usage: python3 run_grudge.py --games 100 --out grudge.json --md GRUDGE.md
       python3 run_grudge.py --md-only        # пересобрать MD из сохранённого json
"""
import argparse, json, statistics, time
import multiprocessing as mp
import bb_full

NS = (8, 12, 16)
ARMS = [
    ('OFF',        {}),
    ('DECAY',      {'grudge': True}),
    ('WINDOW',     {'grudge_window': True}),
    ('DECAY+REP',  {'grudge': True, 'reputation': True}),
    ('WINDOW+REP', {'grudge_window': True, 'reputation': True}),
]
NAMES = [a for a, _ in ARMS]


def _work(job):
    n, seed, ai = job
    name, cfg = ARMS[ai]
    st, P = bb_full.run_game(seed, n, log=None, situation='base', cfg=cfg)
    a = st['acts']
    aggr = a.get('kill', 0) + a.get('wound', 0) + a.get('mass', 0)
    return dict(n=n, seed=seed, arm=name,
                end=st['end'], deaths=st['deaths'], surv=st['alive'],
                aggr=aggr, kills=a.get('kill', 0), heals=a.get('heal', 0),
                acts=sum(a.values()), rpds=sum(st['rpds_types'].values()),
                notes=st['grudge_notes'], soothes=st['grudge_soothes'], peak=st['grudge_peak'],
                revenge=st['grudge_revenge'], marked=st['grudge_marked'], faded=st['grudge_faded'],
                rep_harm=st['rep_harm'])


def agg(rows):
    g = len(rows)
    def m(k): return round(statistics.mean(r[k] for r in rows), 3)
    aggr = sum(r['aggr'] for r in rows) or 1
    rev = sum(r['revenge'] for r in rows)
    mrk = sum(r['marked'] for r in rows)
    return dict(games=g, end=m('end'), deaths=m('deaths'), surv=m('surv'),
                p90=sorted(r['end'] for r in rows)[int(.9 * g) - 1],
                aggr=m('aggr'), kills=m('kills'), heals=m('heals'), acts=m('acts'), rpds=m('rpds'),
                notes_pg=m('notes'), soothes_pg=m('soothes'), peak_max=max(r['peak'] for r in rows),
                revenge_pg=m('revenge'), marked_pg=m('marked'), faded_pg=m('faded'),
                mark_share=round(100 * (rev + mrk) / aggr, 1),
                fire_games=round(100 * sum(1 for r in rows if (r['revenge'] + r['marked']) > 0) / g, 1),
                rep_harm_pg=m('rep_harm'))


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
    L = ['# №14/B25: ДОЛГАЯ ПАМЯТЬ ОБИД — отчёт', '',
         f'Прогон: {time.strftime("%Y-%m-%d %H:%M")}, семена 1..{games} (пары), N ∈ {{{", ".join(map(str, NS))}}}, ситуация base.',
         f'Всего партий: {res["total_games"]} (по {games} на каждую из {len(ARMS)} рук на ось — лимит ≤100 на конфигурацию соблюдён).', '',
         '## Что мерили', '',
         'Меню №14: «долгая память обид — месть на всю партию с затуханием vs окно 2 цикла».',
         'Обида пишется из ПУБЛИЧНЫХ событий (те же, что видит репутация B21 — откаты №1–2 соблюдены): ',
         'вред добавляет силу (kill 1.5, wound 0.7, steal/humiliate 0.6, mass 0.5, предательство 1.5), ',
         'лечение гасит (−0.8, пол ноль). Применение (только при флагах, только агрессивные выборы): ',
         'обида ≥ 1.0 ставит обидчика в список мести (строка 💢), любая живая обида множит вес цели ',
         '×min(2.5, 1+0.45·сила). DECAY: сила × 0.8^Δциклов (kill значим ~13 циклов, wound ~7); ',
         'WINDOW: Δ ≤ 2 цикла без затухания, дальше запись мертва. Коэффициенты «на глаз», НЕ тюнятся (№10).', '',
         '## Сводка (на партию)', '']
    for n in NS:
        x = A[str(n)]
        L += [f'### N{n}', '',
              '| метрика | ' + ' | '.join(NAMES) + ' |', '|' + '---|' * (len(NAMES) + 1)]
        rows = [
            ('обид записано (гроссбух, всегда)', 'notes_pg', '{:.2f}'),
            ('…погашено лечением', 'soothes_pg', '{:.2f}'),
            ('пик силы обиды за партию', 'peak_max', '{:.1f}'),
            ('местей по обиде (💢)', 'revenge_pg', '{:.2f}'),
            ('выбор пал на должника', 'marked_pg', '{:.2f}'),
            ('увядших оценок (память истекла)', 'faded_pg', '{:.2f}'),
            ('обида в агрессивных актах, %', 'mark_share', '{:.1f}'),
            ('партий с местью по обиде, %', 'fire_games', '{:.1f}'),
            ('агрессивных актов', 'aggr', '{:.2f}'),
            ('убийств-актов', 'kills', '{:.2f}'),
            ('лечений', 'heals', '{:.2f}'),
            ('заявок РПДС', 'rpds', '{:.2f}'),
            ('смертей', 'deaths', '{:.2f}'),
            ('длительность, циклов', 'end', '{:.2f}'),
            ('p90 длительности', 'p90', '{}'),
        ]
        for label, key, fmt in rows:
            cells = []
            for a in NAMES:
                v = x[a][key]
                cells.append('—' if v is None else fmt.format(v))
            L.append(f'| {label} | ' + ' | '.join(cells) + ' |')
        L += ['', f'**Δ против OFF (парный тест, {games} пар)**', '',
              '| метрика | ' + ' | '.join(NAMES[1:]) + ' |', '|' + '---|' * len(NAMES)]
        for key, label in (('end', 'длительность'), ('deaths', 'смерти'), ('surv', 'выжили'),
                           ('aggr', 'агрессивные акты'), ('kills', 'убийства-акты'), ('heals', 'лечения')):
            cells = []
            for a in NAMES[1:]:
                d = x['p_' + a][key]
                cells.append(f"{d['delta']:+.2f} (t={d['t']}){sig(d['t'])}")
            L.append(f'| {label} | ' + ' | '.join(cells) + ' |')
        L.append('| партий с тем же исходом по длительности, % | ' +
                 ' | '.join(f"{x['p_' + a]['end']['same']:.0f}" for a in NAMES[1:]) + ' |')
        L.append('')
    L += ['## DECAY против WINDOW (прямой ответ меню, те же семена)', '']
    for n in NS:
        x = A[str(n)]
        dw = x['dw']
        L += [f'**N{n}:** ' + '; '.join(
            f"{lab} {dw[k]['delta']:+.2f} (t={dw[k]['t']}){sig(dw[k]['t'])}"
            for k, lab in (('end', 'длительность'), ('deaths', 'смерти'), ('aggr', 'агрессия'),
                           ('revenge', 'мести 💢'), ('marked', 'помеченные'))) + '.', '']
    L += ['## Выводы', '']
    L += res.get('conclusions') or ['(заполняются после прогона)']
    L += ['', '## Воспроизведение', '',
          '```', 'python3 run_grudge.py --games 100 --out grudge.json --md GRUDGE.md', '```', '']
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--games', type=int, default=100)
    ap.add_argument('--out', default='grudge.json')
    ap.add_argument('--md', default='GRUDGE.md')
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
            x['p_' + name] = {k: paired(off, by[name], k)
                              for k in ('end', 'deaths', 'surv', 'aggr', 'kills', 'heals')}
        x['dw'] = {k: paired(by['WINDOW'], by['DECAY'], k)
                   for k in ('end', 'deaths', 'aggr', 'revenge', 'marked')}
        res['axes'][str(n)] = x
    json.dump(res, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(a.md, 'w', encoding='utf-8').write(build_md(res, a.games))
    print(f'записано: {a.out}, {a.md}')
    for n in NS:
        x = res['axes'][str(n)]
        line = [f"N{n}:"]
        for name in NAMES:
            y = x[name]
            line.append(f"{name} обид {y['notes_pg']} месть {y['revenge_pg']} помеч {y['marked_pg']} "
                        f"({y['mark_share']}% агрессии) увяд {y['faded_pg']} end {y['end']} смерти {y['deaths']}")
        print('  ' + ' | '.join(line))


if __name__ == '__main__':
    main()
