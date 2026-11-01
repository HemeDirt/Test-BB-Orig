# -*- coding: utf-8 -*-
"""№7 ЛИМИТ РУКИ (hand_limit) — замер влияния потолка карт на экономику и длину партий, B15.

Метод: парные сиды 1..G (как в №25): для каждой оси (N, ситуация) прогоняем канон (hand_limit=None)
и значения лимита на ОДНИХ И ТЕХ ЖЕ сидах → дельта к канону на том же «судьбе стола».
Лимит пользователя: ≤100 партий на конфигурацию за прогон.

Фокус-метрики (меню №7): «насколько собиратели ломают игру без лимита»:
  * gained / gained_max  — счётчик украденного (у воров), пик на игрока;
  * hand_sum / hand_max  — карты в игре на конец партии (все места, включая призраков);
  * собиратели           — архетипы hoard/collector_live/marauder + повестка hidden_hoard
                           + заработанный ярлык 'hoard' (5+ краж): выживаемость, руки, gained;
  * burns                — срабатывания лимита (сгоревшие карты), доля партий со сгораниями;
  * end / deaths / drag  — рамка: меняется ли длина партии и темп.

Usage:
  python3 run_handlimit.py --games 100 --out handlimit.json --md HANDLIMIT.md
"""
import argparse, json, statistics, sys, time
import multiprocessing as mp
from collections import Counter
import bb_full

AXES = [('N8/base', 8, 'base'), ('N8/plane', 8, 'plane'), ('N12/base', 12, 'base'), ('N16/base', 16, 'base')]
LIMITS = [None, 7, 9, 12, 15]          # None = канон (без лимита); 7 = len(CATS), «нулевое накопление»
COLL_ARCHS = ('hoard', 'collector_live', 'marauder')


def is_collector(p):
    return (p['pers'].get('arch') in COLL_ARCHS or 'hoard' in (p.get('archs') or [])
            or p['pers'].get('agenda') == 'hidden_hoard')


def _work(job):
    axis, lim, seed, n, sit = job
    cfg = None if lim is None else dict(hand_limit=lim)
    st, P = bb_full.run_game(seed, n, log=None, situation=sit, cfg=cfg)
    hands = [sum(len(l) for l in p['hand'].values()) for p in P]
    coll = [(1 if (p['alive'] and not p['limbo']) else 0, p['gained'],
             sum(len(l) for l in p['hand'].values()), p['revived']) for p in P if is_collector(p)]
    m = dict(end=st['end'], deaths=st['deaths'], alive=st['alive'], burns=st['limit_burns'],
             maxhand=st['max_hand'], drag=round(st['drag_sum'], 2),
             hand_sum=sum(hands), hand_max=max(hands) if hands else 0,
             gained=sum(p['gained'] for p in P), gained_max=max(p['gained'] for p in P),
             rev_pct=1 if st['revives'] else 0, harv_pct=1 if st['harvests'] else 0,
             n_coll=len(coll), coll_surv=sum(c[0] for c in coll), coll_gained=sum(c[1] for c in coll),
             coll_hand=sum(c[2] for c in coll), coll_max=max((c[2] for c in coll), default=0),
             causes=dict(st['causes']))
    return axis, lim, seed, m


def agg(rows, g):
    """строка агрегатов по списку игр одной конфигурации"""
    col = lambda k: [r[k] for r in rows]
    d = dict(games=len(rows),
             end_mean=round(statistics.mean(col('end')), 2), end_sd=round(statistics.pstdev(col('end')), 2),
             p90=sorted(col('end'))[int(.9 * len(rows)) - 1],
             deaths_mean=round(statistics.mean(col('deaths')), 2),
             burns_mean=round(statistics.mean(col('burns')), 2),
             burns_pct=round(100 * sum(1 for b in col('burns') if b) / len(rows)),
             maxhand_mean=round(statistics.mean(col('maxhand')), 2),
             hand_sum_mean=round(statistics.mean(col('hand_sum')), 1),
             hand_max_mean=round(statistics.mean(col('hand_max')), 1),
             gained_mean=round(statistics.mean(col('gained')), 2),
             gained_max_mean=round(statistics.mean(col('gained_max')), 2),
             drag_mean=round(statistics.mean(col('drag')), 2),
             rev_pct=round(100 * sum(col('rev_pct')) / len(rows)),
             harv_pct=round(100 * sum(col('harv_pct')) / len(rows)),
             coll_per_game=round(statistics.mean(col('n_coll')), 2),
             coll_surv_pct=round(100 * sum(col('coll_surv')) / max(1, sum(col('n_coll')))),
             coll_gained_mean=round(sum(col('coll_gained')) / len(rows), 2),
             coll_hand_mean=round(sum(col('coll_hand')) / len(rows), 1),
             coll_max_mean=round(statistics.mean(col('coll_max')), 1))
    return d


def pair_stats(base_rows, var_rows, key):
    """парная дельта (вариант − канон) по одному и тому же сиду"""
    dl = [v[key] - b[key] for b, v in zip(base_rows, var_rows)]
    mu = statistics.mean(dl)
    sd = statistics.pstdev(dl) if len(dl) > 1 else 0.0
    sem = sd / len(dl) ** .5 if sd else 0.0
    mark = ''
    if sem and abs(mu) >= 3 * sem: mark = '✳✳'
    elif sem and abs(mu) >= 2 * sem: mark = '✳'
    return dict(delta=round(mu, 3), sd=round(sd, 3), sem=round(sem, 3), mark=mark)


def main():
    ap = argparse.ArgumentParser(description='№7 hand_limit: влияние потолка руки')
    ap.add_argument('--games', type=int, default=100)
    ap.add_argument('--out', default='handlimit.json')
    ap.add_argument('--md', default='HANDLIMIT.md')
    ap.add_argument('--pool', type=int, default=8)
    a = ap.parse_args()
    if a.games > 100:
        sys.exit('лимит пользователя: не более 100 партий на конфигурацию за прогон')

    jobs = [(ax, lim, s, n, sit) for ax, n, sit in AXES for lim in LIMITS for s in range(1, a.games + 1)]
    t0 = time.time()
    with mp.Pool(min(a.pool, mp.cpu_count())) as pool:
        res = pool.map(_work, jobs, chunksize=8)
    el = time.time() - t0

    by = {}
    for axis, lim, seed, m in res:
        by.setdefault((axis, lim), []).append((seed, m))
    data = {}
    for (axis, lim), lst in by.items():
        lst.sort()
        data[f'{axis}|{lim}'] = [m for _, m in lst]

    out = dict(meta=dict(games=a.games, axes=[x[0] for x in AXES], limits=LIMITS,
                         seeds=f'1..{a.games} (парные)', date=time.strftime('%Y-%m-%d'),
                         core='B15', seconds=round(el, 1), games_total=len(jobs)),
               runs={k: agg(v, a.games) for k, v in data.items()},
               pairs={})
    for ax, n, sit in AXES:
        base = data[f'{ax}|None']
        for lim in LIMITS[1:]:
            var = data[f'{ax}|{lim}']
            out['pairs'][f'{ax}|{lim}'] = {k: pair_stats(base, var, k)
                                           for k in ('end', 'deaths', 'gained', 'hand_sum', 'drag')}
            out['pairs'][f'{ax}|{lim}']['burns_mean'] = round(statistics.mean([r['burns'] for r in var]), 2)
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # ─────────────────────────── отчёт MD ───────────────────────────
    L = []
    L.append('# №7 ЛИМИТ РУКИ (hand_limit) — замер B15\n')
    L.append(f'Дата: {out["meta"]["date"]}. Ядро: B15 (patch_b15_handlimit + b15b + b15c). '
             f'Партий всего: {len(jobs)} ({len(AXES)} оси × {len(LIMITS)} значений × {a.games}), {el:.0f} с.\n')
    L.append('Метод: парные сиды 1..%d — дельта к канону (hand_limit=None) на том же сиде. '
             '✳ = |Δ| ≥ 2·SEM, ✳✳ ≥ 3·SEM. Лимит ≤100 партий/конфиг соблюдён.\n' % a.games)
    L.append('Семантика: потолок ЗАКРЫТЫХ карт; избыток СГОРАЕТ (сброс, строка лога «🔥 лимит руки»); '
             'раскрытые не считаются; обмен 1-на-1 и хроно-обновление лимит не трогают; '
             'тень «close» на полной руке не срабатывает; гард: hand_limit ≥ 7 = len(CATS).\n')
    hdr = ('| значение | end (Δ) | смертей (Δ) | сгораний/партию | партий со сгор. | пик руки | '
           'карт в игре к концу (Δ) | gained всего (Δ) | gained макс/игрока | собирателей/партию | '
           'выжив. собир. % | рука собир. к концу |')
    sep = '|' + '---|' * 12
    for ax, n, sit in AXES:
        L.append(f'\n## Ось {ax} (N={n}, ситуация {sit})\n')
        L.append(hdr); L.append(sep)
        for lim in LIMITS:
            r = out['runs'][f'{ax}|{lim}']
            if lim is None:
                de = dd = dg = dh = ''
                label = 'канон (без лимита)'
            else:
                pr = out['pairs'][f'{ax}|{lim}']
                de = f"{pr['end']['delta']:+.2f}{pr['end']['mark']}"
                dd = f"{pr['deaths']['delta']:+.2f}{pr['deaths']['mark']}"
                dg = f"{pr['gained']['delta']:+.2f}{pr['gained']['mark']}"
                dh = f"{pr['hand_sum']['delta']:+.1f}{pr['hand_sum']['mark']}"
                label = f'лимит {lim}'
            L.append(f"| {label} | {r['end_mean']} ({de}) | {r['deaths_mean']} ({dd}) | {r['burns_mean']} | "
                     f"{r['burns_pct']}% | {r['maxhand_mean']} | {r['hand_sum_mean']} ({dh}) | "
                     f"{r['gained_mean']} ({dg}) | {r['gained_max_mean']} | {r['coll_per_game']} | "
                     f"{r['coll_surv_pct']}% | {r['coll_hand_mean']} |")
    # собиратели в каноне — «насколько ломают без лимита»
    L.append('\n## Собиратели без лимита (канон) и под лимитом\n')
    L.append('| ось | собирателей/партию | gained собирателей | макс. рука собирателя (среднее пиков) | '
             'выживаемость собирателей | gained макс/игрока (все) |')
    L.append('|' + '---|' * 6)
    for ax, n, sit in AXES:
        rc = out['runs'][f'{ax}|None']
        r7 = out['runs'][f'{ax}|7']
        L.append(f"| {ax} канон | {rc['coll_per_game']} | {rc['coll_gained_mean']} | {rc['coll_max_mean']} | "
                 f"{rc['coll_surv_pct']}% | {rc['gained_max_mean']} |")
        L.append(f"| {ax} лимит 7 | {r7['coll_per_game']} | {r7['coll_gained_mean']} | {r7['coll_max_mean']} | "
                 f"{r7['coll_surv_pct']}% | {r7['gained_max_mean']} |")
    open(a.md, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print(f'{a.out} + {a.md}: {len(jobs)} партий за {el:.0f} с')
    for ax, n, sit in AXES:
        rc = out['runs'][f'{ax}|None']
        row = f'{ax}: канон end {rc["end_mean"]}, hand_sum {rc["hand_sum_mean"]}, gained {rc["gained_mean"]}'
        for lim in LIMITS[1:]:
            pr = out['pairs'][f'{ax}|{lim}']
            row += f' | lim{lim}: Δend {pr["end"]["delta"]:+.2f}{pr["end"]["mark"]}, burns {pr["burns_mean"]}'
        print(row)


if __name__ == '__main__':
    main()
