# -*- coding: utf-8 -*-
"""№12/B22: ТИЛЬТ — парное измерение OFF vs ON.

Оси: N ∈ {8,12,16}, ситуация base, семена 1..100 (пары), ≤100 партий на конфигурацию.
Метрики на партию (из st):
  end, deaths, surv; aggr — агрессивные акты (kill+wound+mass из st['acts']);
  trig — триггеры тильта (откат/крит-провал/масс-провал), hot/cold/mid — по темпераменту;
  ca — «месть» (своя атака в окне триггера), cf — полная цепочка «провал→месть→провал»;
  ta — решений choose() под сдвигом весов (ON; при OFF всегда 0).
Гроссбух ведётся в обеих руках ( rng не трогает) → цепочки измеримы и на каноне.
Парный дельта-тест: mean(on−off) по семенам, t ≈ mean/(std/√100); значимость ✳ |t|≥2, ✳✳ |t|≥3;
порог шума по длительности 0.4 цикла (как B17/B21).

Usage: python3 run_tilt.py --games 100 --out tilt.json --md TILT.md
       python3 run_tilt.py --md-only            # пересобрать MD из сохранённого json
"""
import argparse, json, statistics, sys, time
import multiprocessing as mp
import bb_full

NS = (8, 12, 16)


def _work(job):
    n, seed, on = job
    st, P = bb_full.run_game(seed, n, log=None, situation='base',
                             cfg={'tilt': bool(on)})
    a = st['acts']
    return dict(n=n, seed=seed, on=int(on), end=st['end'], deaths=st['deaths'],
                surv=st['alive'], aggr=a.get('kill', 0) + a.get('wound', 0) + a.get('mass', 0),
                trig=st['tilt_trig'], hot=st['tilt_hot'], cold=st['tilt_cold'], mid=st['tilt_mid'],
                ca=st['tilt_chain_attack'], cf=st['tilt_chain_fail'], ta=st['tilt_acts'])


def agg(rows):
    g = len(rows)
    def m(k): return round(statistics.mean(r[k] for r in rows), 3)
    trig = sum(r['trig'] for r in rows) or 1
    ca = sum(r['ca'] for r in rows)
    return dict(games=g, end=m('end'), deaths=m('deaths'), aggr=m('aggr'),
                p90=sorted(r['end'] for r in rows)[int(.9 * g) - 1],
                trig_pg=m('trig'),
                hot_pct=round(100 * sum(r['hot'] for r in rows) / trig, 1),
                cold_pct=round(100 * sum(r['cold'] for r in rows) / trig, 1),
                mid_pct=round(100 * sum(r['mid'] for r in rows) / trig, 1),
                revenge_pct=round(100 * ca / trig, 1),
                chain_pct=round(100 * sum(r['cf'] for r in rows) / ca, 1) if ca else 0.0,
                chain_pg=m('cf'), ta_pg=m('ta'))


def paired(off_rows, on_rows, key):
    d = [b[key] - a[key] for a, b in zip(sorted(off_rows, key=lambda r: r['seed']),
                                         sorted(on_rows, key=lambda r: r['seed']))]
    mu = statistics.mean(d)
    sd = statistics.stdev(d) if len(d) > 1 else 0.0
    t = mu / (sd / len(d) ** .5) if sd else float('inf') if mu else 0.0
    return dict(delta=round(mu, 3), t=round(t, 2),
                same=round(100 * sum(1 for x in d if x == 0) / len(d), 1))


def sig(t):
    return '✳✳' if abs(t) >= 3 else ('✳' if abs(t) >= 2 else '')


def build_md(res, games):
    L = ['# №12/B22: ТИЛЬТ ботов — отчёт', '',
         f'Прогон: {time.strftime("%Y-%m-%d %H:%M")}, семян 1..{games} (пары), N ∈ {{{", ".join(map(str, NS))}}}, ситуация base.',
         f'Всего партий: {res["total_games"]} (по {games} на конфигурацию — лимит соблюдён). Ядро: `tilt=False` канон, `True` — HOUSE.', '',
         '## Механика (ON)', '',
         '- триггеры: собственный **откат** (SELF-полоса таблицы А), **крит-провал** (FAIL проверки Б/В), **масс-провал**;',
         '- `temper = aggr + blood − detach`: ≥ +0.25 — **вспышка** (kill ×1.35, wound ×1.25, mass ×1.2, skip ×0.7), ≤ −0.25 — **заморозка** (kill ×0.75, wound ×0.8, mass ×0.8, skip ×1.3, heal ×1.15), между — без сдвига;',
         '- окно сдвига: остаток текущего цикла + следующий; мера меню — цепочки **«провал→месть→провал»** (trig → своя атака в окне → новый провал);',
         '- гроссбух (счётчики trig/hot/cold/mid/ca/cf) ведётся ВСЕГДА, включая OFF — цепочки измеримы на каноне; сдвиг весов и строки ↯ — только ON;',
         '- коэффициенты НЕ тюнились (меню №10 — заморозка канона): ±0.25 / ×1.35…×0.7 выбраны «на глаз».', '',
         '## Результаты', '']
    for n in NS:
        x = res['axes'][str(n)]
        o, k = x['off'], x['on']
        pe, pd_, pa = x['p_end'], x['p_deaths'], x['p_aggr']
        pt, pc = x['p_trig'], x['p_cf']
        L += [f'### N{n}', '',
              '| метрика | OFF (канон) | ON | Δ (t) |', '|---|---|---|---|',
              f"| длительность, циклов | {o['end']} | {k['end']} | {pe['delta']:+} (t={pe['t']}) {sig(pe['t'])} |",
              f"| p90 | {o['p90']} | {k['p90']} | {k['p90'] - o['p90']:+} |",
              f"| смертей/партию | {o['deaths']} | {k['deaths']} | {pd_['delta']:+.3f} (t={pd_['t']}) {sig(pd_['t'])} |",
              f"| агрессивных актов/партию | {o['aggr']} | {k['aggr']} | {pa['delta']:+.2f} (t={pa['t']}) {sig(pa['t'])} |",
              f"| триггеров/партию | {o['trig_pg']} | {k['trig_pg']} | {pt['delta']:+.2f} (t={pt['t']}) {sig(pt['t'])} |",
              f"| …вспышка/заморозка/ровно, % | {o['hot_pct']}/{o['cold_pct']}/{o['mid_pct']} | {k['hot_pct']}/{k['cold_pct']}/{k['mid_pct']} | |",
              f"| месть после триггера, % | {o['revenge_pct']} | {k['revenge_pct']} | {k['revenge_pct'] - o['revenge_pct']:+.1f} п.п. |",
              f"| цепочка «провал→месть→провал», % от местей | {o['chain_pct']} | {k['chain_pct']} | {k['chain_pct'] - o['chain_pct']:+.1f} п.п. |",
              f"| полных цепочек/партию | {o['chain_pg']} | {k['chain_pg']} | {pc['delta']:+.3f} (t={pc['t']}) {sig(pc['t'])} |",
              f"| решений под сдвигом/партию | 0 | {k['ta_pg']} | |",
              f"| партии с идентичным исходом, % | — | {pe['same']} | |", '']
    L += ['## Выводы', '']
    L += res.get('conclusions') or ['(заполняются после прогона)']
    L += ['', '## Воспроизведение', '',
          '```', 'python3 run_tilt.py --games 100 --out tilt.json --md TILT.md', '```', '']
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--games', type=int, default=100)
    ap.add_argument('--out', default='tilt.json')
    ap.add_argument('--md', default='TILT.md')
    ap.add_argument('--md-only', action='store_true')
    a = ap.parse_args()

    if a.md_only:
        res = json.load(open(a.out, encoding='utf-8'))
        open(a.md, 'w', encoding='utf-8').write(build_md(res, res['games_per_config']))
        print(f'пересобрано: {a.md}')
        return

    jobs = [(n, s, on) for n in NS for on in (0, 1) for s in range(1, a.games + 1)]
    print(f'партий: {len(jobs)} (осей {len(NS)} × 2 руки × {a.games})', flush=True)
    t0 = time.time()
    with mp.Pool(min(8, mp.cpu_count() or 2)) as pool:
        rows = pool.map(_work, jobs, chunksize=8)
    print(f'время: {time.time() - t0:.1f} с', flush=True)

    res = {'games_per_config': a.games, 'total_games': len(rows), 'ns': list(NS), 'axes': {}}
    for n in NS:
        off = [r for r in rows if r['n'] == n and not r['on']]
        on = [r for r in rows if r['n'] == n and r['on']]
        res['axes'][str(n)] = dict(off=agg(off), on=agg(on),
                                   p_end=paired(off, on, 'end'), p_deaths=paired(off, on, 'deaths'),
                                   p_aggr=paired(off, on, 'aggr'), p_trig=paired(off, on, 'trig'),
                                   p_ca=paired(off, on, 'ca'), p_cf=paired(off, on, 'cf'))
    json.dump(res, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(a.md, 'w', encoding='utf-8').write(build_md(res, a.games))
    print(f'записано: {a.out}, {a.md}')
    for n in NS:
        x = res['axes'][str(n)]
        pe, pa = x['p_end'], x['p_aggr']
        print(f"N{n}: end {x['off']['end']}→{x['on']['end']} (Δ{pe['delta']:+}, t={pe['t']}), "
              f"aggr {x['off']['aggr']}→{x['on']['aggr']} (t={pa['t']}), "
              f"trig {x['off']['trig_pg']}→{x['on']['trig_pg']}, "
              f"месть {x['off']['revenge_pct']}→{x['on']['revenge_pct']}%, "
              f"цепочки {x['off']['chain_pct']}→{x['on']['chain_pct']}%, same {pe['same']}%")


if __name__ == '__main__':
    main()
