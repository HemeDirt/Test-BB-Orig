# -*- coding: utf-8 -*-
"""№20 (B18): регрессионные отпечатки эталонных конфигураций.

Идея: baseline (seed 777/plane/N8) ловит только одну партию. Отпечаток ловит ЛЮБОЕ изменение
поведения ядра на 20 партиях × 12 эталонных конфигурациях (иерархия рычагов из №25: рамка,
жизни, режим Жатвы, экономика, лимит руки, драфт, абляция, кубик D6, вкусовые ручки).

Вектор партии: (end, deaths, survivors(sorted), harvests, revives, midturn_stops,
                limit_burns, draft_takes, dolls, betrayals)
Отпечаток конфига = sha256(канонический json векторов сидов 1..20)[:16].

Запуск:  python3 make_fingerprints.py           — сверка с fingerprints.json (код возврата 1 при расхождении)
         python3 make_fingerprints.py --update   — переснять эталон (ТОЛЬКО после принятого изменения ядра)
В приёмке: run_tests.sh шаг 4b.
"""
import hashlib
import json
import statistics
import sys
import time

import bb_full
from bb_core import D6

GAMES = 20          # сидов на конфиг (не путать с лимитом 100 партий на замер эффекта)
FP_LEN = 16

# (имя, N, ситуация, cfg) — cfg сериализуется: объекты с __name__ (кубики) пишутся именем
CONFIGS = [
    ('base_n8',       8,  'base',  {}),
    ('base_n12',      12, 'base',  {}),
    ('plane_n8',      8,  'plane', {}),
    ('hrono_n12',     12, 'hrono', {}),
    ('ordeath5_n8',   8,  'base',  {'or_death': 5}),
    ('lives2_n8',     8,  'base',  {'lives': 2}),
    ('late_n8',       8,  'base',  {'harvest_mode': 'late'}),
    ('econ_n8',       8,  'base',  {'mode': 'rpds_economy'}),
    ('lim7_n12',      12, 'base',  {'hand_limit': 7}),
    ('draft_econ_n8', 8,  'base',  {'mode': 'rpds_economy', 'draft': True}),
    ('ablate_all_n8', 8,  'base',  {'ablate': 'all'}),
    ('d6_n8',         8,  'base',  {'dice': D6}),
]

PATH = 'fingerprints.json'


def vectors(n, sit, cfg):
    out = []
    for s in range(1, GAMES + 1):
        st, P = bb_full.run_game(s, n, log=None, situation=sit, cfg=cfg)
        surv = sorted(p['seat'] for p in P if p['alive'] and not p['limbo'])
        out.append([st['end'], st['deaths'], surv, st['harvests'], st['revives'],
                    st['midturn_stops'], st['limit_burns'], st['draft_takes'],
                    st['dolls'], st['betrayals']])
    return out


def fingerprint(vecs):
    return hashlib.sha256(json.dumps(vecs, separators=(',', ':')).encode()).hexdigest()[:FP_LEN]


def cfg_repr(cfg):
    return {k: (getattr(v, '__name__', v) if not isinstance(v, (int, float, str, bool, type(None))) else v)
            for k, v in cfg.items()}


def compute():
    fps = {}
    for name, n, sit, cfg in CONFIGS:
        v = vectors(n, sit, cfg)
        fps[name] = dict(sha=fingerprint(v), n=n, sit=sit, cfg=cfg_repr(cfg),
                         end_mean=round(statistics.mean(x[0] for x in v), 2),
                         deaths_mean=round(statistics.mean(x[1] for x in v), 2))
    return fps


def main():
    core_sha = hashlib.sha256(open('bb_full.py', 'rb').read()).hexdigest()[:FP_LEN]
    fps = compute()
    if '--update' in sys.argv:
        doc = dict(meta=dict(games=GAMES, seeds=f'1..{GAMES}', core_sha=core_sha,
                             date=time.strftime('%Y-%m-%d'),
                             note='эталон переснимать только вместе с принятым изменением ядра'),
                   fps=fps)
        json.dump(doc, open(PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'отпечатки пересняты: {len(fps)} конфигов × {GAMES} сидов → {PATH} (core_sha {core_sha})')
        return 0
    try:
        ref = json.load(open(PATH, encoding='utf-8'))['fps']
    except FileNotFoundError:
        print(f'{PATH} не найден — снимите эталон: python3 make_fingerprints.py --update')
        return 1
    bad = [(k, ref.get(k, {}).get('sha'), fps[k]['sha']) for k in fps if ref.get(k, {}).get('sha') != fps[k]['sha']]
    gone = [k for k in ref if k not in fps]
    for k, old, new in bad:
        print(f'  РАСХОЖДЕНИЕ {k}: эталон {old} → сейчас {new} (end_mean {fps[k]["end_mean"]})')
    for k in gone:
        print(f'  конфиг {k} исчез из набора')
    if bad or gone:
        print(f'ПРОВАЛ: {len(bad)} расхождений, {len(gone)} пропавших. Если изменение ядра принято — '
              f'переснимите: python3 make_fingerprints.py --update')
        return 1
    print(f'  все {len(fps)} отпечатков совпадают (core_sha {core_sha}, seeds 1..{GAMES})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
