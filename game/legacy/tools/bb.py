#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""БЛИЦ БОЙ — автономный CLI (реестовая сборка 2026-10-17).

Единственная точка входа поверх рабочего симулятора game_sim.py.
Команды:
  python3 bb.py play  [--seed N] [--n 8] [--log ФАЙЛ] [--quiet]   — сыграть партию
  python3 bb.py batch [--games 100] [--out ФАЙЛ.json]             — серия партий + статистика
  python3 bb.py html  [--seed N] [--out ФАЙЛ.html]                — самодостаточная HTML-страница партии
  python3 bb.py deck  каталог                                      — показать статистику колод
"""
import sys, os, io, json, random, argparse, statistics

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

def _load_game_sim(seed):
    """Импортирует game_sim как модуль и переинициализирует ГСЧ под seed."""
    # чистим кэш, чтобы повторные вызовы давали свежую среду
    for m in ('game_sim',):
        sys.modules.pop(m, None)
    saved_argv = sys.argv
    sys.argv = ['game_sim.py', str(seed)]  # game_sim читает сид из argv при импорте
    try:
        import game_sim
    finally:
        sys.argv = saved_argv
    game_sim.rng = random.Random(seed)
    game_sim.LOG = []
    game_sim.SEED = seed
    return game_sim

def cmd_play(args):
    gs = _load_game_sim(args.seed)
    # перехватываем print из main()
    buf = io.StringIO()
    real_stdout = sys.stdout
    if args.log or args.quiet:
        sys.stdout = buf
    try:
        gs.main()
    finally:
        sys.stdout = real_stdout
    text = '\n'.join(gs.LOG)
    if args.log:
        with open(args.log, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
        print(f"Лог сохранён: {args.log} ({len(gs.LOG)} строк)")
    elif not args.quiet:
        print(text)
    else:
        print(text.splitlines()[-1])

def cmd_batch(args):
    results = []
    gs0 = _load_game_sim(args.start_seed)
    # читаем SCORE-строки прогоном каждого сида в subprocess-free режиме:
    # проще всего — импортировать и вызывать setup/run_cycle напрямую
    import subprocess
    for i in range(args.games):
        seed = args.start_seed + i
        p = subprocess.run([sys.executable, os.path.join(ROOT, 'game_sim.py'), str(seed), '--quiet'],
                           capture_output=True, text=True)
        line = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else ''
        rec = {'seed': seed}
        for tok in line.replace('SCORE=', 'score=').split():
            if '=' in tok:
                k, v = tok.split('=', 1)
                if v in ('True', 'False'):
                    v = v == 'True'
                else:
                    try: v = int(v)
                    except ValueError: pass
                rec[k] = v
        results.append(rec)
    ok = [r for r in results if 'score' in r]
    scores = [r['score'] for r in ok]
    ends = [r.get('end', 99) for r in ok]
    stats = {
        'games': len(results), 'finished': len(ok),
        'avg_score': round(statistics.mean(scores), 2) if scores else None,
        'median_end_cycle': statistics.median(ends) if ends else None,
        'first_death_dist': {}, 'harvest_rate': None, 'revive_rate': None,
    }
    from collections import Counter
    stats['first_death_dist'] = dict(Counter(r.get('first_death') for r in ok))
    stats['harvest_rate'] = round(sum(1 for r in ok if r.get('harvest')) / len(ok), 3) if ok else None
    stats['revive_rate'] = round(sum(1 for r in ok if r.get('specrevive')) / len(ok), 3) if ok else None
    stats['end_dist'] = dict(Counter(ends))
    out = {'stats': stats, 'games': results}
    if args.out:
        json.dump(out, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"Сохранено: {args.out}")
    print(json.dumps(stats, ensure_ascii=False, indent=1))

HTML_TMPL = """<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>БЛИЦ БОЙ — seed %(seed)s</title>
<style>
body{margin:0;background:#0e1116;color:#dde5ef;font:14px/1.5 ui-sans-serif,system-ui,sans-serif}
header{position:sticky;top:0;background:#12171f;border-bottom:1px solid #28303c;padding:10px 16px}
h1{font-size:16px;margin:0} .sub{color:#8b98a9;font-size:12px}
main{max-width:900px;margin:0 auto;padding:12px 16px}
.cycle{margin:18px 0 6px;font-weight:700;color:#f2b544;border-bottom:1px solid #28303c;padding-bottom:4px}
.turn{margin:10px 0 4px;font-weight:600;color:#7fd4f2}
.ln{padding:1px 0 1px 8px;border-left:2px solid transparent;white-space:pre-wrap}
.dth{border-left-color:#f2736f;color:#f2736f}.har{border-left-color:#7ee081;color:#7ee081}
.rev{border-left-color:#7fd4f2;color:#7fd4f2}.card{border-left-color:#8fe3c8;color:#8fe3c8}
.roll{color:#b9a6f5}.act{color:#f2a05c}
footer{color:#8b98a9;font-size:12px;padding:16px;text-align:center}
</style></head><body>
<header><h1>БЛИЦ БОЙ <span class="sub">партия seed %(seed)s · 8 игроков · «Ночь в панельке»</span></h1></header>
<main>%(body)s</main>
<footer>Сгенерировано bb.py html · %(date)s</footer>
</body></html>"""

def esc(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def cmd_html(args):
    gs = _load_game_sim(args.seed)
    buf = io.StringIO(); real = sys.stdout
    sys.stdout = buf
    try: gs.main()
    finally: sys.stdout = real
    parts = []
    for ln in gs.LOG:
        s = ln.strip()
        cls = 'ln'
        if s.startswith('════════ ЦИКЛ'):
            parts.append(f'<div class="cycle">{esc(s)}</div>'); continue
        if s.startswith('———'):
            parts.append(f'<div class="turn">{esc(s)}</div>'); continue
        if 'УМИРАЕТ' in s or '💀' in s: cls += ' dth'
        elif 'ЖАТВА' in s or '🌾' in s: cls += ' har'
        elif 'возвращается с того света' in s or 'воскрес' in s.lower(): cls += ' rev'
        elif 'раскрывает' in s or '«' in s and 'карт' in s: cls += ' card'
        elif 'бросок d20' in s: cls += ' roll'
        elif 'РПДС:' in s or 'РПДИ' in s: cls += ' act'
        parts.append(f'<div class="{cls}">{esc(ln)}</div>')
    import datetime
    html = HTML_TMPL % {'seed': args.seed, 'body': '\n'.join(parts),
                        'date': datetime.date.today().isoformat()}
    out = args.out or f'VIEW_bb_seed{args.seed}.html'
    open(out, 'w', encoding='utf-8').write(html)
    print(f"Страница сохранена: {out} ({len(html)//1024} КБ). Откройте двойным кликом в браузере.")

def cmd_deck(args):
    data = json.load(open(os.path.join(ROOT, 'canon', 'decks.json'), encoding='utf-8'))
    for k, v in data.items():
        print(f"{k}: {len(v)} карт")
        if args.show:
            for c in v[:24]:
                print('   ', c)

def main():
    ap = argparse.ArgumentParser(description='БЛИЦ БОЙ — запускатор')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p1 = sub.add_parser('play'); p1.add_argument('--seed', type=int, default=777)
    p1.add_argument('--log'); p1.add_argument('--quiet', action='store_true')
    p2 = sub.add_parser('batch'); p2.add_argument('--games', type=int, default=100)
    p2.add_argument('--start-seed', type=int, default=1); p2.add_argument('--out')
    p3 = sub.add_parser('html'); p3.add_argument('--seed', type=int, default=777); p3.add_argument('--out')
    p4 = sub.add_parser('deck'); p4.add_argument('--show', action='store_true')
    args = ap.parse_args()
    {'play': cmd_play, 'batch': cmd_batch, 'html': cmd_html, 'deck': cmd_deck}[args.cmd](args)

if __name__ == '__main__':
    main()
