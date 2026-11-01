# -*- coding: utf-8 -*-
"""№25 (дополнение): ЧАСТОТА СРАБАТЫВАНИЯ ручек — чтобы отличить «ручка не влияет» от «ручка не работает».

Метод: bb_full.py копируется во временный модуль со счётчиками на ветках конфигов (правка только
добавляет globals()['CNT_*'] += 1, ГСЧ не трогает — контрольная партия 777/plane/N8 остаётся 5/5).
Затем 100 партий на каждую ручку (лимит пользователя) и подсчёт срабатываний.

Usage: python3 run_triggers.py --n 8 12 --games 100 --out tornado_triggers.json
"""
import argparse, hashlib, io, json, os, sys, tempfile

FLAGS = [  # (имя ручки, cfg, имя счётчика, маркер строки в bb_full.py, тип вставки)
 ('blind_kill', dict(blind_kill=True), 'CNT_blind', "elif a == 'kill' and C['blind_kill']:", 'block'),
 ('harvest_pick=leader', dict(harvest_pick='leader'), 'CNT_leader', "elif C['harvest_pick'] == 'leader':", 'block'),
 ('pressure', dict(pressure=True), 'CNT_press', "if C['pressure'] and c >= 2 and not st['player_death']:", 'block'),
 ('spec_cycle', dict(spec_cycle=True), 'CNT_speccyc', "if C['spec_cycle'] and 'spec' not in ABL:", 'block'),
 ('traitor', dict(traitor=True), 'CNT_traitor', "if C['traitor']:", 'block'),
 ('mode=rpds_economy', dict(mode='rpds_economy', reveal=1), 'CNT_econ', "if C['mode'] == 'rpds_economy':", 'block'),
 ('random_outcome', dict(random_outcome=True), 'CNT_rand', "if C['random_outcome']:", 'block'),
 ('crit_price', dict(crit_price=True), 'CNT_crit', "if C['crit_price'] and r0 == dice['faces']: wound(a, 1, 'self')", 'append'),
 ('or_noise', dict(or_noise=True), 'CNT_noise', "if C['or_noise'] and rng.random() < .6: o += rng.choice([-1, 0, 1])", 'append'),
 ('pacifist_c1', dict(pacifist_c1=True), 'CNT_pacif', "if c == 1 and C['pacifist_c1']: rpdi = 0", 'append'),
 ('queue_reverse', dict(queue_reverse=True), 'CNT_qrev', "if C['queue_reverse'] and c % 2 == 0: order = order[::-1]", 'append'),
 ('escalation', dict(escalation=True), 'CNT_escal', "if C['escalation'] and st['cycle'] >= 4 and src not in ('self', 'harvest'): amt += 1", 'append'),
]


def make_instrumented(dst_dir):
    lines = io.open('bb_full.py', encoding='utf-8').read().split('\n')
    marks_a = {m: c for _n, _cfg, c, m, t in FLAGS if t == 'append'}
    marks_b = {m: c for _n, _cfg, c, m, t in FLAGS if t == 'block'}
    out, na, nb = [], 0, 0
    for i, l in enumerate(lines):
        s = l.strip()
        if s in marks_a:
            out.append(l + f"; globals()['{marks_a[s]}']=globals().get('{marks_a[s]}',0)+1"); na += 1; continue
        out.append(l)
        if s in marks_b:
            nxt = lines[i + 1] if i + 1 < len(lines) else ''
            ind = (nxt[:len(nxt) - len(nxt.lstrip())] if nxt.strip() else l[:len(l) - len(l.lstrip())] + '    ')
            out.append(f"{ind}globals()['{marks_b[s]}']=globals().get('{marks_b[s]}',0)+1"); nb += 1
    assert na == sum(1 for *_x, t in FLAGS if t == 'append') + 1, f'append-маркеров {na}'  # crit_price встречается дважды
    assert nb == len(marks_b), f'block-маркеров {nb} из {len(marks_b)}'
    p = os.path.join(dst_dir, 'bb_instr.py')
    io.open(p, 'w', encoding='utf-8').write('\n'.join(out))
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, nargs='+', default=[8, 12])
    ap.add_argument('--games', type=int, default=100); ap.add_argument('--out', default='tornado_triggers.json')
    ap.add_argument('--sit', default='base')
    a = ap.parse_args()
    if a.games > 100:
        sys.exit('лимит пользователя: не более 100 партий на конфигурацию за прогон')
    tmp = tempfile.mkdtemp(prefix='bbtrig_')
    make_instrumented(tmp)
    sys.path.insert(0, tmp)
    import bb_instr as B
    st, _ = B.run_game(777, 8, log=None, situation='plane', cfg=None)
    assert (st['end'], st['deaths']) == (5, 5), 'инструментация изменила канон!'
    res = {}
    for n in a.n:
        res[str(n)] = {}
        for name, cfg, cnt, _m, _t in FLAGS:
            for k in [k for k in vars(B) if k.startswith('CNT_')]:
                delattr(B, k)
            for s in range(1, a.games + 1):
                B.run_game(s, n, log=None, situation=a.sit, cfg=cfg)
            res[str(n)][name] = vars(B).get(cnt, 0)
        print(f'N{n}: ' + ', '.join(f'{k}={v}' for k, v in res[str(n)].items()), flush=True)
    out = dict(meta=dict(games=a.games, sit=a.sit, note='срабатываний ветки за 100 партий; счётчики не трогают ГСЧ',
                         core_sha=hashlib.sha256(io.open('bb_full.py', 'rb').read()).hexdigest()[:12]),
               counts=res)
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('сохранено:', a.out)


if __name__ == '__main__':
    main()
