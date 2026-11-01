# -*- coding: utf-8 -*-
"""№9 ДРАФТ РАСКРЫТЫХ (draft) — замер «раскрытия как информация против как ресурса», B16.

Метод: парные сиды 1..G (как в №25/№7): для каждой оси прогоняем канон (draft=False) и
драфт (draft=True) на ОДНИХ И ТЕХ ЖЕ сидах → дельта к канону на том же «судьбе стола».
Лимит пользователя: ≤100 партий на конфигурацию за прогон.

Семантика драфта (HOUSE, вердикт «кроме профок и спецок»): каждая раскрытая бытовая карта
уходит в общий пул; РПДС «add» при успехе берёт сперва из пула. В каноне раскрытие —
чистая информация (карта лежит в личной зоне rev); в драфте — ещё и ресурс стола.

Фокус-метрики (меню №9):
  * takes / left / peak — сколько раскрытий забрали (ресурс), сколько осело (информация), пик пула;
  * util% = takes/(takes+left) — доля раскрытий, ставших ресурсом (в драфте takes+left = все раскрытия);
  * gained, собиратели (hoard/collector_live/marauder) — кому рециркуляция на пользу;
  * end / deaths / drag — рамка: двигает ли драфт длину партии и темп.

Usage:
  python3 run_draft.py --games 100 --out draft.json --md DRAFT.md
"""
import argparse, json, statistics, sys, time
import multiprocessing as mp
import bb_full

AXES = [('N8/base', 8, 'base', {}),
        ('N12/base', 12, 'base', {}),
        ('N8/econ', 8, 'base', dict(mode='rpds_economy')),     # экономика РПДС: add — главная заявка
        ('N12/lim7', 12, 'base', dict(hand_limit=7))]          # дефицит руки + рециркуляция пула
COLL_ARCHS = ('hoard', 'collector_live', 'marauder')


def is_collector(p):
    return (p['pers'].get('arch') in COLL_ARCHS or 'hoard' in (p.get('archs') or [])
            or p['pers'].get('agenda') == 'hidden_hoard')


def _work(job):
    axis, draft, seed, n, sit, basecfg = job
    cfg = dict(basecfg)
    if draft: cfg['draft'] = True
    st, P = bb_full.run_game(seed, n, log=None, situation=sit, cfg=cfg or None)
    coll = [(1 if (p['alive'] and not p['limbo']) else 0, p['gained']) for p in P if is_collector(p)]
    takes, left = st['draft_takes'], st['draft_left']
    m = dict(end=st['end'], deaths=st['deaths'], alive=st['alive'], drag=round(st['drag_sum'], 2),
             takes=takes, peak=st['draft_pool_peak'], left=left,
             util=round(takes / (takes + left), 3) if (takes + left) else 0.0,
             add=st['rpds_types'].get('add', 0), burns=st['limit_burns'], maxhand=st['max_hand'],
             gained=sum(p['gained'] for p in P), gained_max=max(p['gained'] for p in P),
             rev_pct=1 if st['revives'] else 0, harv_pct=1 if st['harvests'] else 0,
             n_coll=len(coll), coll_surv=sum(c[0] for c in coll), coll_gained=sum(c[1] for c in coll))
    return axis, draft, seed, m


def agg(rows):
    col = lambda k: [r[k] for r in rows]
    takes, left = sum(col('takes')), sum(col('left'))
    return dict(games=len(rows),
                end_mean=round(statistics.mean(col('end')), 2), end_sd=round(statistics.pstdev(col('end')), 2),
                p90=sorted(col('end'))[int(.9 * len(rows)) - 1],
                deaths_mean=round(statistics.mean(col('deaths')), 2),
                alive_mean=round(statistics.mean(col('alive')), 2),
                takes_mean=round(statistics.mean(col('takes')), 2),
                peak_mean=round(statistics.mean(col('peak')), 1),
                left_mean=round(statistics.mean(col('left')), 1),
                util_pct=round(100 * takes / (takes + left), 1) if (takes + left) else 0.0,
                add_mean=round(statistics.mean(col('add')), 2),
                burns_mean=round(statistics.mean(col('burns')), 2),
                maxhand_mean=round(statistics.mean(col('maxhand')), 2),
                gained_mean=round(statistics.mean(col('gained')), 2),
                gained_max_mean=round(statistics.mean(col('gained_max')), 2),
                drag_mean=round(statistics.mean(col('drag')), 2),
                rev_pct=round(100 * sum(col('rev_pct')) / len(rows)),
                harv_pct=round(100 * sum(col('harv_pct')) / len(rows)),
                coll_per_game=round(statistics.mean(col('n_coll')), 2),
                coll_surv_pct=round(100 * sum(col('coll_surv')) / max(1, sum(col('n_coll')))),
                coll_gained_mean=round(sum(col('coll_gained')) / len(rows), 2))


def pair_stats(base_rows, var_rows, key):
    dl = [v[key] - b[key] for b, v in zip(base_rows, var_rows)]
    mu = statistics.mean(dl)
    sd = statistics.pstdev(dl) if len(dl) > 1 else 0.0
    sem = sd / len(dl) ** .5 if sd else 0.0
    mark = ''
    if sem and abs(mu) >= 3 * sem: mark = '✳✳'
    elif sem and abs(mu) >= 2 * sem: mark = '✳'
    return dict(delta=round(mu, 3), sd=round(sd, 3), sem=round(sem, 3), mark=mark)


def main():
    ap = argparse.ArgumentParser(description='№9 draft: ценность раскрытий как информации против как ресурса')
    ap.add_argument('--games', type=int, default=100)
    ap.add_argument('--out', default='draft.json')
    ap.add_argument('--md', default='DRAFT.md')
    ap.add_argument('--pool', type=int, default=8)
    a = ap.parse_args()
    if a.games > 100:
        sys.exit('лимит пользователя: не более 100 партий на конфигурацию за прогон')

    jobs = [(ax, d, s, n, sit, bc) for ax, n, sit, bc in AXES for d in (False, True)
            for s in range(1, a.games + 1)]
    t0 = time.time()
    with mp.Pool(min(a.pool, mp.cpu_count())) as pool:
        res = pool.map(_work, jobs, chunksize=8)
    el = time.time() - t0

    by = {}
    for axis, draft, seed, m in res:
        by.setdefault((axis, draft), []).append((seed, m))
    data = {}
    for key, lst in by.items():
        lst.sort()
        data[key] = [m for _, m in lst]

    out = dict(meta=dict(games=a.games, axes=[x[0] for x in AXES], seeds=f'1..{a.games} (парные)',
                         date=time.strftime('%Y-%m-%d'), core='B16', seconds=round(el, 1),
                         games_total=len(jobs)),
               runs={f'{ax}|{"draft" if d else "canon"}': agg(data[(ax, d)])
                     for ax, _, _, _ in AXES for d in (False, True)},
               pairs={})
    for ax, n, sit, bc in AXES:
        base, var = data[(ax, False)], data[(ax, True)]
        out['pairs'][ax] = {k: pair_stats(base, var, k) for k in ('end', 'deaths', 'gained', 'util', 'drag')}

    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # ─────────────────────────── отчёт MD ───────────────────────────
    L = []
    L.append('# №9 ДРАФТ РАСКРЫТЫХ (draft) — замер B16\n')
    L.append(f'Дата: {out["meta"]["date"]}. Ядро: B16 (patch_b16_draft). '
             f'Партий всего: {len(jobs)} ({len(AXES)} оси × 2 конфига × {a.games}), {el:.0f} с.\n')
    L.append('Метод: парные сиды 1..%d — дельта draft−canon на том же сиде. ✳ = |Δ| ≥ 2·SEM, ✳✳ ≥ 3·SEM. '
             'Лимит ≤100 партий/конфиг соблюдён.\n' % a.games)
    L.append('Семантика: раскрытая бытовая карта → общий пул (кроме профок/спецок — они и не раскрываются '
             'через reveal()); РПДС «add» при успехе берёт сперва из пула. util% = takes/(takes+left) — '
             'доля раскрытий, ставших ресурсом; в драфте takes+left = все раскрытия партии.\n')
    hdr = ('| конфиг | end (Δ) | смертей (Δ) | util% (Δ) | takes/партию | пик пула | осело в пуле | '
           'РПДС add/партию | gained (Δ) | выжив. собир. % | gained собир. |')
    sep = '|' + '---|' * 11
    for ax, n, sit, bc in AXES:
        extra = f', доп. {bc}' if bc else ''
        L.append(f'\n## Ось {ax} (N={n}, {sit}{extra})\n')
        L.append(hdr); L.append(sep)
        rc = out['runs'][f'{ax}|canon']; rd = out['runs'][f'{ax}|draft']; pr = out['pairs'][ax]
        L.append(f"| канон | {rc['end_mean']} | {rc['deaths_mean']} | — | — | — | — | {rc['add_mean']} | "
                 f"{rc['gained_mean']} | {rc['coll_surv_pct']}% | {rc['coll_gained_mean']} |")
        L.append(f"| draft | {rd['end_mean']} ({pr['end']['delta']:+.2f}{pr['end']['mark']}) | "
                 f"{rd['deaths_mean']} ({pr['deaths']['delta']:+.2f}{pr['deaths']['mark']}) | "
                 f"{rd['util_pct']}% ({pr['util']['delta']:+.2f}{pr['util']['mark']}) | {rd['takes_mean']} | "
                 f"{rd['peak_mean']} | {rd['left_mean']} | {rd['add_mean']} | "
                 f"{rd['gained_mean']} ({pr['gained']['delta']:+.2f}{pr['gained']['mark']}) | "
                 f"{rd['coll_surv_pct']}% | {rd['coll_gained_mean']} |")
        L.append(f"\nРамка: p90 end канон {rc['p90']} / draft {rd['p90']}; drag {rc['drag_mean']} → "
                 f"{rd['drag_mean']} ({pr['drag']['delta']:+.2f}{pr['drag']['mark']}); "
                 f"воскресения {rc['rev_pct']}% → {rd['rev_pct']}%; Жатва {rc['harv_pct']}% → {rd['harv_pct']}%; "
                 f"сгорания лимита {rc['burns_mean']} → {rd['burns_mean']}; пик руки {rc['maxhand_mean']} → {rd['maxhand_mean']}.")
    open(a.md, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print(f'{a.out} + {a.md}: {len(jobs)} партий за {el:.0f} с')
    for ax, n, sit, bc in AXES:
        rc = out['runs'][f'{ax}|canon']; rd = out['runs'][f'{ax}|draft']; pr = out['pairs'][ax]
        print(f"{ax}: end {rc['end_mean']}→{rd['end_mean']} ({pr['end']['delta']:+.2f}{pr['end']['mark']}), "
              f"util {rd['util_pct']}%, takes {rd['takes_mean']}, пул оседает {rd['left_mean']}, "
              f"gained {pr['gained']['delta']:+.2f}{pr['gained']['mark']}, собиратели {rc['coll_surv_pct']}%→{rd['coll_surv_pct']}%")


if __name__ == '__main__':
    main()
