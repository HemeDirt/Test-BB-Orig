# -*- coding: utf-8 -*-
"""№25 КАРТА ЧУВСТВИТЕЛЬНОСТИ (tornado) — однофакторные замеры ядра B13.

Метод: меняем ОДИН параметр за раз, остальные — канон. Сиды 1..G общие для всех вариантов
(парное сравнение: одна и та же «судьба стола» при разных ручках) → шум ГСЧ вычитается.
Лимит пользователя соблюдается: ≤100 партий на конфигурацию за прогон.

Факторы делятся на две группы:
  HANDLES  — ручки настройки (то, что ведущий может изменить до партии);
  CONTEXT  — условия партии (размер стола, ситуация): не «ручка», а рамка, вынесено отдельно.
ЗАМОРОЖЕНО (меню п.10): полосы кубика, веса/вероятности ботов в каноне НЕ меняем.
Вариант «состав архетипов» присутствует только как ЗАМЕР чувствительности, канон остаётся прежним.

Usage:
  python3 run_tornado.py --n 8  --sit base --games 100 --out tornado_n8.json
  python3 run_tornado.py --n 12 --sit base --games 100 --out tornado_n12.json
  python3 tornado_report.py --in tornado_n8.json --md TORNADO_N8.md --html VIEW_tornado_n8.html
"""
import argparse, json, statistics, sys, time
import multiprocessing as mp
from collections import Counter
import bb_full
from bb_core import D20, D6

# ─────────────────────────── ТАБЛИЦА ФАКТОРОВ ───────────────────────────
# variants: (метка, cfg-дополнение, необязательные n/sit) — базовый вариант НЕ перечисляется,
# он прогоняется один раз как BASE и служит точкой отсчёта для всех парных дельт.
HANDLES = [
 dict(id='or_death', name='Порог смерти (ОР)', note='сколько очков ран (ОР) накапливается до смерти',
      base='3', variants=[('2', dict(or_death=2)), ('4', dict(or_death=4)), ('5', dict(or_death=5))]),
 dict(id='reveal', name='Раскрытий за цикл', note='сколько карт вскрывается в фазе раскрытия',
      base='2', variants=[('1', dict(reveal=1)), ('3', dict(reveal=3))]),
 dict(id='rpdi', name='РПДИ (личных раскрытий на игрока)', note='личные карты, вскрываемые игроком за цикл',
      base='1', variants=[('0', dict(rpdi=0)), ('2', dict(rpdi=2))]),
 dict(id='rpds', name='РПДС (общих раскрытий)', note='общие карты стола за цикл',
      base='1', variants=[('0', dict(rpds=0)), ('2', dict(rpds=2))]),
 dict(id='agenda_p', name='Доля игроков с личной целью', note='вероятность, что у игрока есть скрытая цель-агенда',
      base='0.25', variants=[('0 (целей нет)', dict(agenda_p=0.0)), ('0.50', dict(agenda_p=.5))]),
 dict(id='lives', name='Жизни', note='сколько смертей переживает тело до выбывания',
      base='1', variants=[('2', dict(lives=2)), ('3', dict(lives=3))]),
 dict(id='fear', name='Страх', note='механика страха (давит на веса осторожных действий)',
      base='вкл', variants=[('выкл', dict(fear=False))]),
 dict(id='dice', name='Кубик', note='гранность кубика; все полосы таблиц пересчитываются пропорционально',
      base='D20', variants=[('D6', dict(dice=D6))]),
 dict(id='harvest_mode', name='Режим Жатвы', note='когда срабатывает Жатва (массовая казнь стола)',
      base='std', variants=[('off (нет Жатвы)', dict(harvest_mode='off')),
                            ('off_after_death (до первой смерти)', dict(harvest_mode='off_after_death')),
                            ('off_after_corpse (пока нет мертвецов)', dict(harvest_mode='off_after_corpse')),
                            ('late (с цикла 4)', dict(harvest_mode='late')),
                            ('max2 (не больше 2 за партию)', dict(harvest_mode='max2')),
                            ('quiet2 (после тихого цикла)', dict(harvest_mode='quiet2')),
                            ('escalate (позже, но пачкой)', dict(harvest_mode='escalate'))]),
 dict(id='harvest_pick', name='Выбор жертвы Жатвой', note='кого берёт Жатва: случайно или «лидера» по вкладу',
      base='random', variants=[('leader (по ущербу)', dict(harvest_pick='leader'))]),
 dict(id='mode', name='Режим раздачи/экономики', note='std — карты на руке; rpds_economy — рука пуста, всё через раскрытия',
      base='std', variants=[('rpds_economy', dict(mode='rpds_economy', reveal=1))]),
 dict(id='ablate', name='Карты (абляция)', note='какая колода выключена целиком; замер из №22',
      base='все на месте', variants=[('без спецкарт', dict(ablate='spec')), ('без профессий', dict(ablate='prof')),
                                     ('без теней', dict(ablate='shad')), ('без обмена', dict(ablate='exch')),
                                     ('без 8 бытовых колод', dict(ablate='traits')),
                                     ('без ВСЕХ карт', dict(ablate='all'))]),
 dict(id='arch_pool', name='Состав архетипов (ЗАМЕР, канон не тронут)',
      note='пул личностей: канон — все 23; вариант — «мирный стол» без агрессоров',
      base='канон (23 архетипа)',
      variants=[('мирный пул', dict(arch_pool=['medic', 'turtle', 'lurker', 'hoard', 'team', 'actor'], agenda_p=.05))]),
 dict(id='blind_kill', name='Слепое убийство', note='убийство без указания цели (жребий)', base='выкл',
      variants=[('вкл', dict(blind_kill=True))]),
 dict(id='queue_reverse', name='Обратная очередь', note='порядок хода разворачивается', base='выкл',
      variants=[('вкл', dict(queue_reverse=True))]),
 dict(id='traitor', name='Предатель', note='в начале партии объявляются предатели', base='выкл',
      variants=[('вкл', dict(traitor=True))]),
 dict(id='spec_cycle', name='Спецкарта по циклам', note='выдача спецкарт привязана к циклу', base='выкл',
      variants=[('вкл', dict(spec_cycle=True))]),
 dict(id='escalation', name='Эскалация', note='давление растёт с каждым циклом', base='выкл',
      variants=[('вкл', dict(escalation=True))]),
 dict(id='pressure', name='Давление', note='каждый цикл добавляет ОР всем живым', base='выкл',
      variants=[('вкл', dict(pressure=True))]),
 dict(id='or_noise', name='Шум ОР', note='случайная прибавка/потеря ОР', base='выкл', variants=[('вкл', dict(or_noise=True))]),
 dict(id='crit_price', name='Цена крита', note='критический провал бьёт по самому игроку', base='выкл',
      variants=[('вкл', dict(crit_price=True))]),
 dict(id='pacifist_c1', name='Пацифизм цикла 1', note='в первом цикле нельзя наносить урон', base='выкл',
      variants=[('вкл', dict(pacifist_c1=True))]),
 dict(id='random_outcome', name='Случайный исход РПД/РПДС', note='исход раскрытия выбирается равномерно вместо полос кубика',
      base='выкл', variants=[('вкл', dict(random_outcome=True))]),
 dict(id='revive_esc', name='Лестница воскрешений (HOUSE-TEST)', note='воскрешение дорожает +1 жетон за каждое состоявшееся',
      base='выкл', variants=[('вкл', dict(revive_esc=True))]),
]
CONTEXT = [
 dict(id='table_size', name='Размер стола (N)', note='число игроков; не ручка, а условие партии',
      base='8', variants=[('4', dict(), 4), ('6', dict(), 6), ('12', dict(), 12), ('16', dict(), 16), ('20', dict(), 20)]),
 dict(id='situation', name='Ситуация', note='раскладка стола из печатной редакции',
      base='base', variants=[('plane (самолёт)', dict(), None, 'plane'), ('pole (полюс)', dict(), None, 'pole'),
                             ('purg (чистилище)', dict(), None, 'purg'), ('hrono (машина времени)', dict(), None, 'hrono'),
                             ('amkary (две команды)', dict(), None, 'amkary')]),
]


def _norm_variants(fac):
    """приводим варианты к словарям: (label, cfg, n, sit)"""
    out = []
    for v in fac['variants']:
        label, cfg = v[0], v[1]
        n = v[2] if len(v) > 2 else None
        sit = v[3] if len(v) > 3 else None
        out.append((label, cfg, n, sit))
    return out


def _work(job):
    key, seed, n, sit, cfg = job
    st, _P = bb_full.run_game(seed, n, log=None, situation=sit, cfg=cfg)
    return key, st


def main():
    ap = argparse.ArgumentParser(description='№25 tornado: однофакторная карта чувствительности')
    ap.add_argument('--n', type=int, default=8); ap.add_argument('--sit', default='base')
    ap.add_argument('--games', type=int, default=100); ap.add_argument('--out', required=True)
    ap.add_argument('--pool', type=int, default=8); ap.add_argument('--context', action='store_true',
                                                                    help='прогнать и блок CONTEXT (N/ситуации)')
    a = ap.parse_args()
    if a.games > 100:
        sys.exit('лимит пользователя: не более 100 партий на конфигурацию за прогон')

    factors = HANDLES + (CONTEXT if a.context else [])
    jobs = [('BASE', s, a.n, a.sit, None) for s in range(1, a.games + 1)]
    plan = []
    for fac in factors:
        for label, cfg, vn, vsit in _norm_variants(fac):
            key = f'{fac["id"]}|{label}'
            plan.append(dict(key=key, factor=fac['id'], label=label, cfg={k: str(v) for k, v in cfg.items()},
                             n=vn or a.n, sit=vsit or a.sit))
            for s in range(1, a.games + 1):
                jobs.append((key, s, vn or a.n, vsit or a.sit, cfg or None))

    t0 = time.time()
    with mp.Pool(min(a.pool, mp.cpu_count())) as pool:
        res = pool.map(_work, jobs, chunksize=8)
    el = time.time() - t0

    acc = {}
    for key, st in res:
        d = acc.setdefault(key, dict(end=[], deaths=[], alive=[], first=[], drag=[], harv=0, rev=0, stall=0,
                                     causes=Counter(), uses=Counter()))
        d['end'].append(st['end']); d['deaths'].append(st['deaths']); d['alive'].append(st['alive'])
        d['first'].append(st['first_death'] or st['end']); d['drag'].append(round(st['drag_sum'], 2))
        d['harv'] += 1 if st['harvests'] else 0; d['rev'] += 1 if st['revives'] else 0
        d['stall'] += 1 if st['stall'] else 0
        d['causes'].update(st['causes'])
        d['uses'].update(dict(spec=st['spec_uses'], prof=st['prof_uses'], shad=st['shadow_uses'], exch=st['exch_uses']))

    g = a.games
    runs = {}
    for key, d in acc.items():
        runs[key] = dict(end=d['end'], deaths=d['deaths'],
                         end_mean=round(statistics.mean(d['end']), 3), end_sd=round(statistics.pstdev(d['end']), 3),
                         p90=sorted(d['end'])[int(.9 * g) - 1],
                         deaths_mean=round(statistics.mean(d['deaths']), 3),
                         alive_mean=round(statistics.mean(d['alive']), 2),
                         first_death_mean=round(statistics.mean(d['first']), 2),
                         drag_mean=round(statistics.mean(d['drag']), 2),
                         harv_pct=round(100 * d['harv'] / g), rev_pct=round(100 * d['rev'] / g),
                         stall_pct=round(100 * d['stall'] / g),
                         causes=dict(d['causes'].most_common(5)),
                         uses={k: round(v / g, 2) for k, v in d['uses'].items()})
    out = dict(meta=dict(n=a.n, sit=a.sit, games=g, context=bool(a.context), date=time.strftime('%Y-%m-%d'),
                         core='B13', seeds=f'1..{g} (парные: один и тот же сид у всех вариантов)',
                         seconds=round(el, 1), variants=len(plan) + 1, games_total=len(jobs)),
               factors=[dict(id=f['id'], name=f['name'], note=f['note'], base=f['base'],
                             group='CONTEXT' if f in CONTEXT else 'HANDLES',
                             variants=[dict(label=l, cfg={k: str(v) for k, v in c.items()}, n=vn or a.n, sit=vsit or a.sit)
                                       for l, c, vn, vsit in _norm_variants(f)]) for f in factors],
               runs=runs)
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{a.out}: {len(jobs)} партий ({len(plan)} вариантов + BASE × {g}), {el:.1f} с, '
          f'{len(jobs) / max(el, .001):.0f} парт/с')
    b = runs['BASE']
    print(f'BASE N{a.n}/{a.sit}: end {b["end_mean"]} (p90 {b["p90"]}), смертей {b["deaths_mean"]}, '
          f'Жатва {b["harv_pct"]}%, воскр {b["rev_pct"]}%, пат {b["stall_pct"]}%')


if __name__ == '__main__':
    main()
