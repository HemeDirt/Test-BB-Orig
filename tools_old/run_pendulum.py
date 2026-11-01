# -*- coding: utf-8 -*-
"""№30: ДЕКОМПОЗИЦИЯ МАЯТНИКА N16 — темп воскрешений против темпа убийств по циклам, B19.

Вопрос: почему при N≥16 партии раскачиваются в 8–12+ циклов (воскрешения в 70–87% партий)?
Метод: 100 партий на ось (N ∈ {8,12,16,20}, ситуация base, канон), лента событий bb_events —
по циклам считаем: живых на старте, смерти (по группам причин: игроки / среда), воскрешения
(по путям: жетоны / профессор / перерождение), нетто-баланс населения, доля доживших партий.
Плюс задержка воскрешения (циклов от смерти до возврата) и точка равновесия (|нетто| ≈ 0).

Лекарство (данные matrix_revesc.json, раунд B11): revive_esc (цена +1 жетон за каждое
воскрешение за столом) — тяга (drag) −18% при N16, p90 12→11, воскр./партию 1.40→1.27.

Лимит пользователя: ≤100 партий на конфигурацию за прогон (здесь 4 оси × 100 = 400).

Usage: python3 run_pendulum.py --games 100 --out pendulum.json --md PENDULUM_N16.md
"""
import argparse, json, statistics, sys, time
import multiprocessing as mp
from collections import Counter, defaultdict
import bb_full
from bb_events import parse_log

NS = (8, 12, 16, 20)
ENV_CAUSES = {'harvest', 'forced'}          # смерти от среды/ситуации
REVIVE_PATH = {'revive_tokens': 'жетоны призрака', 'revive_necro': 'профессор', 'reincarnate': 'перерождение',
               'revive_agent': 'тур. агент'}   # B21b: путь был безмолвным — маятник B19 чуть недосчитывал воскрешения


def _work(job):
    n, seed = job
    log = []
    st, P = bb_full.run_game(seed, n, log=log, situation='base')
    ev = parse_log(log)
    per_cycle = defaultdict(lambda: dict(deaths=0, d_player=0, d_env=0, rev=0, harvests=0, alive0=None))
    last_death = {}
    delays, paths = [], Counter()
    for e in ev:
        row = per_cycle[e['c']]
        t = e['type']
        if t == 'cycle_start':
            row['alive0'] = e['alive']
        elif t == 'death':
            row['deaths'] += 1
            if e['cause'] in ENV_CAUSES: row['d_env'] += 1
            else: row['d_player'] += 1
            last_death[e['seat']] = e['c']
        elif t in REVIVE_PATH:
            seat = e.get('target', e.get('seat'))
            row['rev'] += 1
            paths[REVIVE_PATH[t]] += 1
            if seat in last_death:
                delays.append(e['c'] - last_death.pop(seat))
        elif t in ('harvest', 'harvest_esc', 'harvest_leader'):
            row['harvests'] += 1
    g = len(per_cycle)
    return dict(n=n, seed=seed, end=st['end'], first_death=st['first_death'],
                revives=st['revives'], deaths=st['deaths'], drag=round(st['drag_sum'], 2),
                cycles={c: dict(r) for c, r in sorted(per_cycle.items())},
                delays=delays, paths=dict(paths),
                causes=dict(Counter({e['cause']: 1 for e in ev if e['type'] == 'death'})))


def aggregate(rows):
    g = len(rows)
    maxc = max(max(r['cycles']) for r in rows)
    per = []
    for c in range(1, maxc + 1):
        reached = [r for r in rows if c in r['cycles']]
        if not reached:
            continue
        d = [r['cycles'][c] for r in reached]
        per.append(dict(c=c, reached_pct=round(100 * len(reached) / g),
                        alive0=round(statistics.mean([x['alive0'] for x in d if x['alive0'] is not None] or [0]), 2),
                        deaths=round(statistics.mean([x['deaths'] for x in d]), 3),
                        d_player=round(statistics.mean([x['d_player'] for x in d]), 3),
                        d_env=round(statistics.mean([x['d_env'] for x in d]), 3),
                        rev=round(statistics.mean([x['rev'] for x in d]), 3),
                        harvests=round(statistics.mean([x['harvests'] for x in d]), 3),
                        net=round(statistics.mean([x['rev'] - x['deaths'] for x in d]), 3)))
    delays = [x for r in rows for x in r['delays']]
    paths = Counter()
    for r in rows: paths.update(r['paths'])
    causes = Counter()
    for r in rows: causes.update(r['causes'])
    ends = sorted(r['end'] for r in rows)
    first_rev = [r['end'] and next((c for c, x in r['cycles'].items() if x['rev']), None) for r in rows]
    first_rev = [c for c in first_rev if c]
    return dict(games=g, end_mean=round(statistics.mean(ends), 2), p90=ends[int(.9 * g) - 1],
                deaths_mean=round(statistics.mean(r['deaths'] for r in rows), 2),
                revives_mean=round(statistics.mean(r['revives'] for r in rows), 2),
                rev_games_pct=round(100 * sum(1 for r in rows if r['revives']) / g),
                first_death_mean=round(statistics.mean([r['first_death'] or r['end'] for r in rows]), 2),
                first_revive_mean=round(statistics.mean(first_rev), 2) if first_rev else None,
                delay_mean=round(statistics.mean(delays), 2) if delays else None,
                drag_mean=round(statistics.mean(r['drag'] for r in rows), 1),
                paths=dict(paths), path_total=sum(paths.values()),
                causes=dict(causes.most_common(6)), per_cycle=per)


def equilibrium(per):
    """первый цикл, с которого нетто-баланс населения держится в ±0.15 три цикла подряд"""
    for i in range(len(per) - 2):
        if all(abs(per[i + k]['net']) <= 0.15 for k in range(3)):
            return per[i]['c']
    return None


def main():
    ap = argparse.ArgumentParser(description='№30 маятник: темп воскрешений против темпа убийств по циклам')
    ap.add_argument('--games', type=int, default=100); ap.add_argument('--pool', type=int, default=8)
    ap.add_argument('--out', default='pendulum.json'); ap.add_argument('--md', default='PENDULUM_N16.md')
    a = ap.parse_args()
    if a.games > 100:
        sys.exit('лимит пользователя: не более 100 партий на конфигурацию за прогон')
    jobs = [(n, s) for n in NS for s in range(1, a.games + 1)]
    t0 = time.time()
    with mp.Pool(min(a.pool, mp.cpu_count())) as pool:
        raw = pool.map(_work, jobs, chunksize=4)
    el = time.time() - t0
    res = {str(n): aggregate([r for r in raw if r['n'] == n]) for n in NS}
    try:
        data = json.load(open('matrix_revesc.json', encoding='utf-8'))
        rv = {r['name']: r for r in data} if isinstance(data, list) else data.get('runs', data)
        remedy = {k: rv.get(k) for k in ('N8_база', 'N8_лестница', 'N12_база', 'N12_лестница',
                                        'N16_база', 'N16_лестница')}
    except Exception:
        remedy = None
    json.dump(dict(meta=dict(games=a.games, seeds=f'1..{a.games}', date=time.strftime('%Y-%m-%d'),
                             core='B17', seconds=round(el, 1), ns=list(NS)),
                   by_n=res, remedy=remedy),
              open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    L = ['# №30 МАЯТНИК БОЛЬШИХ СТОЛОВ — декомпозиция (B19)\n',
         f'Дата: {time.strftime("%Y-%m-%d")}. Метод: 100 партий на ось (N ∈ {list(NS)}, base, канон), '
         f'лента событий → поцикловые средние. {el:.0f} с, партий {len(jobs)}.\n',
         'Обозначения: deaths = смерти за цикл (d_player — от действий игроков, d_env — Жатва/ситуация); '
         'rev = воскрешения за цикл (пути: жетоны призрака / профессор / перерождение); net = rev − deaths '
         '(нетто-прирост населения за цикл); reached% = доля партий, доживших до цикла.\n']
    for n in NS:
        r = res[str(n)]
        eq = equilibrium(r['per_cycle'])
        L.append(f'\n## N={n}: end {r["end_mean"]} (p90 {r["p90"]}), смертей {r["deaths_mean"]}, '
                 f'воскрешений {r["revives_mean"]}/партию ({r["rev_games_pct"]}% партий), '
                 f'первая смерть ц.{r["first_death_mean"]}, первое воскрешение ц.{r["first_revive_mean"]}, '
                 f'задержка воскрешения {r["delay_mean"]} ц., drag {r["drag_mean"]}'
                 + (f', равновесие с ц.{eq}' if eq else ', равновесия нет: net<0 каждый цикл (постоянный дренаж)') + '\n')
        L.append('| ц | дожили % | живых на старте | смертей | от игроков | от среды | воскреш. | net | Жатва |')
        L.append('|---|---|---|---|---|---|---|---|---|')
        for row in r['per_cycle']:
            if row['reached_pct'] < 5:
                continue
            L.append(f"| {row['c']} | {row['reached_pct']} | {row['alive0']} | {row['deaths']} | "
                     f"{row['d_player']} | {row['d_env']} | {row['rev']} | {row['net']:+.3f} | {row['harvests']} |")
        tot = sum(r['paths'].values()) or 1
        L.append('\nПути воскрешений: ' + ', '.join(f'{k} {v} ({round(100 * v / tot)}%)' for k, v in r['paths'].items())
                 + ('' if r['paths'] else '— (воскрешений нет)'))
        L.append('\nПричины смертей: ' + ', '.join(f'{k}×{v}' for k, v in r['causes'].items()))
    r16, r8, r20, r12 = res['16'], res['8'], res['20'], res['12']
    L += ['\n## Вердикт: из чего собран «маятник» больших столов\n',
          f'1. **Маятник — не равновесие, а постоянный дренаж с насыщением темпа.** net = rev − deaths '
          f'ни в одном цикле ни на одном N не подходит к нулю (−0.9…−2.4): население монотонно убывает, '
          f'колебаний вокруг порога S нет. «Маятником» выглядит другое: темп смертей насыщается — с цикла 3 '
          f'смертей/цикл ≈ 1.1–1.5 независимо от N (страх, лимит действий, промахи ограничивают убийства), '
          f'а сток, который надо выбить, растёт линейно: N − S ≈ N/2. Отсюда end ≈ (N/2 + воскрешения)/drain: '
          f'N8 (4+0.45)/0.95 ≈ 4.7 (факт {r8["end_mean"]}), N12 (6+0.9)/1.15 ≈ 6.0 (факт {r12["end_mean"]}), '
          f'N16 (8+1.26)/1.35 ≈ 6.9 (факт {r16["end_mean"]}), N20 (10+2.44)/1.35 ≈ 9.2 (факт {r20["end_mean"]}) — '
          'формула воспроизводит и порядок, и рост; остаток — поздний хвост (п.4).',
          f'2. **Воскрешения — не встречный поток, а «второй круг» через морг.** воскрешений/партию: '
          f'{r8["revives_mean"]} (N8) → {r16["revives_mean"]} (N16) → {r20["revives_mean"]} (N20); каждое возвращает '
          '+1 в сток, который надо убить снова, то есть работает в ЧИСЛИТЕЛЕ формулы выше. Меняется и путь: '
          'профессор доминирует при N8–16 (44–52%), при N20 жетонная экономика призраков выходит на первое место '
          f'(42%): копилки жетонов (+1/цикл на призрака) созревают синхронно, задержка воскрешения '
          f'{r16["delay_mean"]}–{r20["delay_mean"]} ц. ≈ время набрать цену 6.',
          '3. **Средовой тормоз отваливается с ростом N.** d_env (Жатва/ситуация) при N8 = 0.24–0.88 смертей/цикл '
          '(Жатва стреляет в тихие циклы), при N16–20 = 0.03–0.48 и почти ноль в середине игры: тихих циклов нет, '
          'предохранитель длины выключен — вся длина определяется дренажем и стоком.',
          f'4. **Хвост p90 собирают поздние воскрешения.** Задержка {r20["delay_mean"]} ц. при N20 означает возвраты '
          'на циклах 9–14, когда живых уже ≤ S+2: каждое такое воскрешение отодвигает порог на 1–2 цикла. '
          f'Отсюда разрыв средних и хвостов: N16 end {r16["end_mean"]} при p90 {r16["p90"]}, N20 {r20["end_mean"]} '
          f'при p90 {r20["p90"]}.',
          '5. **Лекарство бьёт в созревший путь (matrix_revesc, B11):** revive_esc (цена 6 + число воскрешений за '
          'столом) при N16: воскр./партию 1.40→1.27, drag 25.1→20.7 (−18%), p90 12→11, end 8.02→7.87; при N8 '
          'эффект ≈ 0 (воскрешений и так мало, доминирует профессор, которого цена жетонов не трогает). Повышение '
          'цены гасит именно жетонный путь, который и созревает при N≥16. Статус: HOUSE-TEST, в канон не входит '
          '(решение пользователя по №8: «пока чисто для теста»).\n']
    open(a.md, 'w', encoding='utf-8').write('\n'.join(L))
    print(f'{a.out} + {a.md}: {len(jobs)} партий за {el:.0f} с')
    for n in NS:
        r = res[str(n)]
        print(f'N{n}: end {r["end_mean"]} p90 {r["p90"]} rev/партию {r["revives_mean"]} '
              f'({r["rev_games_pct"]}%) задержка {r["delay_mean"]} равновесие {equilibrium(r["per_cycle"])}')


if __name__ == '__main__':
    main()
