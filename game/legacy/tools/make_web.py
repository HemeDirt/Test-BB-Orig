# -*- coding: utf-8 -*-
"""Генерирует web/index.html — интерактивная страница игры БЛИЦ БОЙ (все данные вшиты)."""
import sys, io, json, random, os, datetime
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

def run_game(seed):
    for m in ('game_sim',): sys.modules.pop(m, None)
    saved = sys.argv; sys.argv = ['game_sim.py', str(seed)]
    import game_sim as gs; sys.argv = saved
    gs.rng = random.Random(seed); gs.LOG = []; gs.SEED = seed
    buf = io.StringIO(); real = sys.stdout; sys.stdout = buf
    try: gs.main()
    finally: sys.stdout = real
    data = {
        'seed': seed, 'log': gs.LOG,
        'state': {k: v for k, v in gs.STATE.items()},
        'players': [{'seat': p['seat'], 'name': p['name'], 'prof': list(p['prof']),
                     'alive': p['alive'], 'or': p['or'], 'died_cycle': p['died_cycle'],
                     'tokens': p['tokens'], 'kills': p['kills'],
                     'revealed': [[k, c] for k, c in p['revealed']],
                     'spec_used': p['spec_used']} for p in gs.P],
    }
    return data, {'PROFS': [list(x) for x in gs.PROFS], 'SPECS': [list(x) for x in gs.SPECS],
                  'TENY': [list(x) for x in gs.TENY], 'OBMEN': [list(x) for x in gs.OBMEN],
                  'DECKS': gs.DECKS}

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 777
data, cards = run_game(seed)
html = open(os.path.join(ROOT, 'template_index.html'), encoding='utf-8').read()
html = html.replace('/*__DATA__*/null', json.dumps(data, ensure_ascii=False))
html = html.replace('/*__CARDS__*/null', json.dumps(cards, ensure_ascii=False))
out = os.path.join(ROOT, 'web', 'index.html')
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'w', encoding='utf-8').write(html)
print(f'OK: {out} ({len(html)//1024} КБ), seed={seed}, log={len(data["log"])} строк')
