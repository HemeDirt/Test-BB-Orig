# -*- coding: utf-8 -*-
"""Генерирует web/index.html — интерактивная страница игры БЛИЦ БОЙ (все данные вшиты)."""
import sys, io, json, random, os, datetime
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

def run_game(seed, n=8):
    """Один импорт, вызов партии как функции — без argv-хаков и subprocess."""
    import game_sim as gs
    res = gs.play_game(seed, n=n)
    data = {
        'seed': seed, 'n': len(res['players']), 'log': res['log'], 'events': res['events'],
        'state': {k: v for k, v in res['state'].items()},
        'players': [{'seat': p['seat'], 'name': p['name'], 'prof': list(p['prof']),
                     'alive': p['alive'], 'or': p['or'], 'died_cycle': p['died_cycle'],
                     'tokens': p['tokens'], 'kills': p['kills'],
                     'hand_n': sum(len(v) for v in p['hand'].values()),
                     'hand': [[k, c] for k, cs in p['hand'].items() for c in cs],
                     'revealed': [[k, c] for k, c in p['revealed']],
                     'spec_used': p['spec_used'], 'spec': list(p['spec']),
                     'obmen': list(p['obmen']) if p.get('obmen') else None,
                     'pers': dict(p.get('pers') or {}),
                     'rep': {str(k): v for k, v in (p.get('rep') or {}).items()},
                     'grudge': {str(k): v for k, v in (p.get('grudge') or {}).items()}}
                    for p in res['players']],
        'arch_ru': getattr(gs, 'ARCH_RU', {}),
        'arch_vec': getattr(gs, 'ARCH', {}),
    }
    return data, {'PROFS': [list(x) for x in gs.PROFS], 'SPECS': [list(x) for x in gs.SPECS],
                  'TENY': [list(x) for x in gs.TENY], 'OBMEN': [list(x) for x in gs.OBMEN],
                  'DECKS': gs.DECKS}

def parse_args(argv):
    """Понимает 'make_web.py 5', '--seed 5 --n 12' и флаги blitz.py."""
    seed, n = 777, 8
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--seed' and i + 1 < len(argv):
            seed = int(argv[i + 1]); i += 2
        elif a.startswith('--seed='):
            seed = int(a.split('=', 1)[1]); i += 1
        elif a == '--n' and i + 1 < len(argv):
            n = int(argv[i + 1]); i += 2
        elif a.startswith('--n='):
            n = int(a.split('=', 1)[1]); i += 1
        elif a.isdigit():
            seed = int(a); i += 1
        else:
            i += 1  # незнакомые флаги молча пропускаем
    return seed, n

seed, n = parse_args(sys.argv[1:])
data, cards = run_game(seed, n)
# --- Наблюдатель: страница с покадровой перемоткой (данные в game.js, страница в observer.html) ---
import json as _json
engine_src = {'game_sim.py': open(os.path.join(ROOT, 'game_sim.py'), encoding='utf-8').read()}
obs_data = {'DATA': data, 'CARDS': cards, 'SRC': engine_src}
obs_js = 'window.GAME=' + _json.dumps(obs_data, ensure_ascii=False) + ';'
tpl_obs = open(os.path.join(ROOT, 'observer_template.html'), encoding='utf-8').read()

def write_site(dd):
    """Пишет сайт в папку dd: observer.html+game.js (модульный вариант) И index.html — ОДИН самодостаточный файл для GitHub Pages."""
    os.makedirs(dd, exist_ok=True)
    open(os.path.join(dd, 'game.js'), 'w', encoding='utf-8').write(obs_js)
    open(os.path.join(dd, 'observer.html'), 'w', encoding='utf-8').write(tpl_obs)
    single = tpl_obs.replace('<script src="game.js"></script>', '<script>' + obs_js + '</script>')
    open(os.path.join(dd, 'index.html'), 'w', encoding='utf-8').write(single)
    return len(single)

# Основная папка сайта по договорённости: blitz/docs/index.html (без preview/)
for d in ('docs', 'web'):
    dd = os.path.join(ROOT, '..', d)
    sz = write_site(dd)
    print(f'OK site: {dd}/index.html ({sz//1024} КБ, один файл), observer.html + game.js, seed={seed}, n={n}')
# Копия в docs/preview для совместимости со старыми ссылками
import shutil as _sh
_pv = os.path.join(ROOT, '..', 'docs', 'preview')
os.makedirs(_pv, exist_ok=True)
for f in ('index.html', 'observer.html', 'game.js'):
    _sh.copyfile(os.path.join(ROOT, '..', 'docs', f), os.path.join(_pv, f))
print('OK копия: docs/preview/')
print(f'Партия: log={len(data["log"])} строк, events={len(data["events"])}, players={data["n"]}, кадров перемотки={sum(1 for e in data["events"] if e.get("t")=="snapshot")}')
