# -*- coding: utf-8 -*-
"""БЛИЦ БОЙ — единый CLI (№17) поверх ядра B11.

Команды:
  play    одна партия: сводка + (опц.) лог, JSONL-события, md-отчёт
  batch   серия партий ОДНОЙ конфигурации (≤100 — правило пользователя), агрегат + json
  matrix  матрица конфигураций из json-файла: [{'name','n','sit','cfg'}, ...] (≤100 партий на конфиг)
  events  конвертация сохранённого лога в JSONL-ленту (№18)
  view    HTML-вьюер партии (№21): самодостаточная страница (лента/места/графики/лог)
          — либо пересчётом из сида, либо из уже сохранённого лога (--log PATH)
  csv     экспорт JSON-результатов прогонов в CSV (№23): автоопределение формы
          (rows/runs/pairs/counts/meta/factors), длинный формат по партиям, utf-8-sig, «;» под Excel

Конфиги (--cfg ключ=значение, повторно): ключи ядра C; true/false, числа, none, строки;
  dice=D20|D6; ablate=spec|prof|shad|exch|traits|all; harvest_mode=std|off_after_corpse|...
Примеры:
  python3 bb.py play --seed 777 --n 8 --sit plane --log log.txt --events ev.jsonl
  python3 bb.py batch --n 12 --games 100 --cfg harvest_mode=late --out late12.json
  python3 bb.py matrix --in configs.json --out results.json
  python3 bb.py view --seed 777 --n 8 --sit plane --out VIEW_777.html
  python3 bb.py view --log log.txt --out VIEW_log.html        # без снимков: лента+лог+фильтры
  python3 bb.py csv tornado_n8.json --out tornado_n8.csv --all  # длинный формат: run,game,end,deaths,…
"""
import argparse, json, statistics, sys
from collections import Counter
import bb_full
from bb_core import D20, D6
from bb_events import log_to_events, parse_log

SITS = ['base', 'plane', 'pole', 'purg', 'hrono', 'amkary']
CFG_KEYS = ['or_death', 'reveal', 'mode', 'agenda_p', 'fear', 'dice', 'harvest_mode', 'harvest_pick',
            'blind_kill', 'queue_reverse', 'traitor', 'spec_cycle', 'rpds', 'rpdi', 'lives',
            'escalation', 'pressure', 'or_noise', 'crit_price', 'pacifist_c1', 'hrono_start',
            'random_outcome', 'ablate', 'revive_esc', 'hand_limit', 'draft', 'reputation', 'tilt',
            'reserve', 'reserve_gate', 'reserve_strict', 'grudge', 'grudge_window']
BOOL_KEYS = {'fear', 'blind_kill', 'queue_reverse', 'traitor', 'spec_cycle', 'escalation', 'pressure',
             'or_noise', 'crit_price', 'pacifist_c1', 'random_outcome', 'revive_esc', 'draft', 'reputation', 'tilt',
             'reserve', 'reserve_gate', 'reserve_strict', 'grudge', 'grudge_window'}
INT_KEYS = {'or_death', 'reveal', 'rpds', 'rpdi', 'lives', 'hrono_start', 'hand_limit'}
FLOAT_KEYS = {'agenda_p'}

def parse_cfg(pairs):
    cfg = {}
    for kv in pairs or []:
        if '=' not in kv:
            sys.exit(f'--cfg ожидает ключ=значение, получено: {kv!r}')
        k, v = kv.split('=', 1)
        if k not in CFG_KEYS:
            sys.exit(f'неизвестный ключ конфига {k!r}. Допустимые: {", ".join(CFG_KEYS)}')
        if k in BOOL_KEYS:
            cfg[k] = v.lower() in ('true', '1', 'yes', 'да')
        elif k in INT_KEYS:
            cfg[k] = None if v.lower() == 'none' else int(v)
        elif k in FLOAT_KEYS:
            cfg[k] = float(v)
        elif k == 'dice':
            cfg[k] = {'D20': D20, 'D6': D6}[v.upper()]
        else:
            cfg[k] = None if v.lower() == 'none' else v
    return cfg

def aggregate(name, sts, extra=None):
    g = len(sts)
    ends = sorted(r['end'] for r in sts)
    causes = Counter()
    for r in sts: causes.update(r['causes'])
    row = dict(name=name, games=g,
               end=round(statistics.mean(ends), 2),
               p10=ends[max(0, int(.1 * g) - 1)], p50=ends[int(.5 * g) - 1] if g >= 2 else ends[0],
               p90=ends[int(.9 * g) - 1],
               deaths=round(statistics.mean(r['deaths'] for r in sts), 2),
               alive=round(statistics.mean(r['alive'] for r in sts), 2),
               harv_pct=round(100 * sum(1 for r in sts if r['harvests']) / g),
               rev_pct=round(100 * sum(1 for r in sts if r['revives']) / g),
               revives=round(statistics.mean(r['revives'] for r in sts), 2),
               stall_pct=round(100 * sum(1 for r in sts if r['stall']) / g),
               first_death=round(statistics.mean([r['first_death'] or r['end'] for r in sts]), 2),
               spec_uses=round(statistics.mean(r['spec_uses'] for r in sts), 2),
               prof_uses=round(statistics.mean(r['prof_uses'] for r in sts), 2),
               shadow_uses=round(statistics.mean(r['shadow_uses'] for r in sts), 2),
               exch_uses=round(statistics.mean(r['exch_uses'] for r in sts), 2),
               drag=round(statistics.mean(r['drag_sum'] for r in sts), 1),
               causes=dict(causes.most_common(6)))
    if extra: row.update(extra)
    return row

def print_row(r):
    print(f"{r['name']:<22} end {r['end']:>5} (p10 {r['p10']}, p50 {r['p50']}, p90 {r['p90']})  "
          f"смертей {r['deaths']:>4}  жив. {r['alive']:>4}  Жатва {r['harv_pct']:>3}%  воскр {r['rev_pct']:>3}%  пат {r['stall_pct']:>3}%")

def _work(job):
    name, seed, n, sit, cfg = job
    st, P = bb_full.run_game(seed, n, situation=sit, cfg=cfg)
    return name, st

def run_games(configs, games, pool_size=8):
    import multiprocessing as mp
    for c in configs:
        if games > 100:
            sys.exit('лимит пользователя: не более 100 партий на конфигурацию за прогон')
    jobs = [(c['name'], s, c['n'], c['sit'], c['cfg']) for c in configs for s in range(1, games + 1)]
    with mp.Pool(min(pool_size, mp.cpu_count())) as pool:
        out = pool.map(_work, jobs)
    res = {}
    for name, st in out:
        res.setdefault(name, []).append(st)
    return res

def cmd_play(a):
    cfg = parse_cfg(a.cfg)
    need_log = bool(a.log or a.events or a.verbose or a.html)
    if a.html or a.json_model:
        import bb_model, bb_html
        m = bb_model.build_model(a.seed, a.n, a.sit, cfg)
        st = dict(end=m['meta']['end'], deaths=m['meta']['deaths'], harvests=m['meta']['harvests'],
                  revives=m['meta']['revives'], first_death=m['meta']['first_death'], stall=m['meta']['stall'])
        surv, log = m['meta']['survivors'], m['log']
    else:
        log = [] if need_log else None
        st, P = bb_full.run_game(a.seed, a.n, log=log, situation=a.sit, cfg=cfg)
        surv = [p['seat'] for p in P if p['alive'] and not p['limbo']]
    print(f'партия seed={a.seed} N={a.n} sit={a.sit} cfg={ {k: (str(v) if v is not None else None) for k, v in cfg.items()} }')
    print(f'ИТОГ: конец в цикле {st["end"]}, выжили {surv}, смертей {st["deaths"]}, Жатв {st["harvests"]}, '
          f'воскрешений {st["revives"]}, первая смерть ц.{st["first_death"]}, пат {"да" if st["stall"] else "нет"}')
    if a.log and log is not None:
        open(a.log, 'w', encoding='utf-8').write('\n'.join(log))
        print('лог:', a.log)
    if a.events and log is not None:
        ev = parse_log(log)          # B13: полная лента (53 типа) вместо урезанной №18 (18 типов)
        with open(a.events, 'w', encoding='utf-8') as f:
            for e in ev: f.write(json.dumps(e, ensure_ascii=False) + '\n')
        print('события:', a.events, len(ev), 'шт')
    if a.html:
        import bb_html
        p, size = bb_html.write_page(m, a.html)
        print('вьюер:', p, f'{size/1024:.0f} КБ (открой в браузере, интернет не нужен)')
    if a.json_model:
        json.dump(m, open(a.json_model, 'w', encoding='utf-8'), ensure_ascii=False)
        print('модель:', a.json_model)
    if a.verbose and log is not None:
        print('\n'.join(log))

def cmd_batch(a):
    cfg = parse_cfg(a.cfg)
    name = a.name or f'batch_N{a.n}_{a.sit}'
    res = run_games([dict(name=name, n=a.n, sit=a.sit, cfg=cfg)], a.games)
    row = aggregate(name, res[name])
    print_row(row)
    print('причины:', ', '.join(f'{k}×{v}' for k, v in row['causes'].items()))
    if a.out:
        json.dump([row], open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('сохранено:', a.out)

def cmd_matrix(a):
    configs = json.load(open(a.infile, encoding='utf-8'))
    for c in configs:
        c.setdefault('n', 8); c.setdefault('sit', 'base'); c.setdefault('cfg', {})
        if c['sit'] not in SITS: sys.exit(f'неизвестная ситуация {c["sit"]!r} в {c["name"]!r}')
    games = min(a.games, 100)
    res = run_games(configs, games, a.pool)
    rows = [aggregate(c['name'], res[c['name']], extra=dict(n=c['n'], sit=c['sit'], cfg={k: str(v) for k, v in c['cfg'].items()}))
            for c in configs]
    for r in rows: print_row(r)
    if a.out:
        json.dump(rows, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('сохранено:', a.out, f'({len(configs)} конфигов × {games} партий)')

def cmd_view(a):
    """№21: HTML-вьюер партии. Либо пересчёт из сида (полная модель: места/графики/обменки),
    либо страница из уже сохранённого лога (лента+фильтры+лог, без карточек мест)."""
    import bb_html
    if a.log:
        lines = open(a.log, encoding='utf-8').read().splitlines()
        p, size = bb_html.write_page_from_log(lines, a.out)
        print(f'вьюер из лога: {p} {size/1024:.0f} КБ (строк {len(lines)}; без снимков — карточки мест и ОР-график пусты)')
        return
    import bb_model
    cfg = parse_cfg(a.cfg)
    m = bb_model.build_model(a.seed, a.n, a.sit, cfg)
    p, size = bb_html.write_page(m, a.out)
    print(f'вьюер: {p} {size/1024:.0f} КБ | seed {a.seed} N{a.n} {a.sit} | конец ц.{m["meta"]["end"]}, '
          f'выжили {m["meta"]["survivors"]}, событий {m["meta"]["events"]}')


def cmd_events(a):
    lines = open(a.logfile, encoding='utf-8').read().splitlines()
    ev = log_to_events(lines) if a.legacy else parse_log(lines)
    with open(a.out, 'w', encoding='utf-8') as f:
        for e in ev: f.write(json.dumps(e, ensure_ascii=False) + '\n')
    print('события:', a.out, len(ev), 'шт')

def cmd_csv(a):
    """№23: JSON-результаты прогонов → CSV (автоопределение формы — см. csv_export.py)."""
    import csv_export
    for p, name, n in csv_export.export(a.infile, a.out, table=a.table, sep=a.sep, all_sections=a.all_sections):
        print(f'csv: {p} [{name}] строк: {n}')

def main():
    ap = argparse.ArgumentParser(prog='bb.py', description='БЛИЦ БОЙ — CLI симулятора печатной ред. №2 (ядро B11)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('play', help='одна партия')
    p.add_argument('--seed', type=int, default=1); p.add_argument('--n', type=int, default=8)
    p.add_argument('--sit', default='base', choices=SITS)
    p.add_argument('--cfg', action='append', metavar='K=V')
    p.add_argument('--log', metavar='PATH'); p.add_argument('--events', metavar='PATH')
    p.add_argument('--html', metavar='PATH', help='№21: самодостаточная HTML-страница партии')
    p.add_argument('--json-model', dest='json_model', metavar='PATH', help='выгрузить модель партии в json')
    p.add_argument('-v', '--verbose', action='store_true', help='печатать лог в консоль')
    p.set_defaults(fn=cmd_play)
    b = sub.add_parser('batch', help='серия партий одной конфигурации (≤100)')
    b.add_argument('--n', type=int, default=8); b.add_argument('--sit', default='base', choices=SITS)
    b.add_argument('--games', type=int, default=100); b.add_argument('--cfg', action='append', metavar='K=V')
    b.add_argument('--name'); b.add_argument('--out', metavar='PATH.json')
    b.set_defaults(fn=cmd_batch)
    m = sub.add_parser('matrix', help='матрица конфигураций из json')
    m.add_argument('--in', dest='infile', required=True, metavar='PATH.json')
    m.add_argument('--games', type=int, default=100); m.add_argument('--pool', type=int, default=8)
    m.add_argument('--out', metavar='PATH.json')
    m.set_defaults(fn=cmd_matrix)
    v = sub.add_parser('view', help='№21: HTML-вьюер партии')
    v.add_argument('--seed', type=int, default=1); v.add_argument('--n', type=int, default=8)
    v.add_argument('--sit', default='base', choices=SITS)
    v.add_argument('--cfg', action='append', metavar='K=V')
    v.add_argument('--log', metavar='PATH', help='строить страницу из сохранённого лога (без пересчёта)')
    v.add_argument('--out', required=True, metavar='PATH.html')
    v.set_defaults(fn=cmd_view)
    e = sub.add_parser('events', help='лог → JSONL-лента событий')
    e.add_argument('logfile'); e.add_argument('out')
    e.add_argument('--legacy', action='store_true', help='старый формат №18 (18 типов, без номеров строк)')
    e.set_defaults(fn=cmd_events)
    c = sub.add_parser('csv', help='№23: JSON-результаты → CSV (Excel/pandas)')
    c.add_argument('infile', metavar='IN.json'); c.add_argument('--out', required=True, metavar='OUT.csv')
    c.add_argument('--table', default='auto', choices=['auto', 'runs', 'rows', 'pairs', 'counts', 'factors', 'meta'])
    c.add_argument('--all', dest='all_sections', action='store_true', help='все секции (файлы с суффиксами)')
    c.add_argument('--sep', default=';', help='разделитель (default «;» под русский Excel)')
    c.set_defaults(fn=cmd_csv)
    a = ap.parse_args()
    a.fn(a)

if __name__ == '__main__':
    main()
