# -*- coding: utf-8 -*-
"""№19 (B18): юнит-тесты веток механик на «свидетелях».

Принцип: у каждой ветки механики есть СИД-СВИДЕТЕЛЬ — минимальный сид (перебор 1..300, N8/N12),
на котором ветка гарантированно срабатывает. Тест прогоняет партию и проверяет предикат:
тип события в ленте (bb_events.parse_log, коды типов — без вкусовых описаний) и/или счётчик st.
Таблица свидетелей снята в раунде B18 (копия /tmp/mech_seeds.json) и зашита ниже как W.

Запуск:  python3 -m pytest test_effects.py -q      (если pytest установлен)
         python3 test_effects.py                   (встроенный раннер, тот же набор)
"""
import collections
import hashlib

import bb_full
from bb_events import parse_log

# код механики -> (seed, n, situation, cfg). Свидетель = ветка срабатывает хотя бы раз.
W = {
    'glass':    (11, 8,  'base',  {}),
    'buddhist': (5,  8,  'base',  {}),
    'doll':     (6,  8,  'base',  {}),
    'link':     (12, 8,  'base',  {}),
    'sniper':   (4,  8,  'base',  {}),
    'quota':    (13, 8,  'base',  {}),
    'hcancel':  (29, 12, 'base',  {}),
    'hleader':  (1,  8,  'base',  {'harvest_pick': 'leader'}),
    'hburn':    (2,  12, 'base',  {'hand_limit': 7}),
    'draft':    (1,  8,  'base',  {'draft': True}),
    'lives':    (1,  8,  'base',  {'lives': 2}),
    'vfx':      (6,  8,  'base',  {}),
    'midturn':  (7,  8,  'base',  {}),
    'twin':     (2,  12, 'base',  {'traitor': True}),
    'pressure': (1,  8,  'base',  {'pressure': True}),
    'escal':    (1,  12, 'base',  {'harvest_mode': 'escalate'}),
    'anvil':    (6,  8,  'base',  {}),
    'chronist': (264, 12, 'base', {}),
    'deal':     (2,  12, 'base',  {}),
    'betray':   (1,  12, 'base',  {}),
    'demon':    (1,  8,  'base',  {}),
    'one1':     (13, 8,  'base',  {}),
    'kick':     (2,  8,  'base',  {}),
    'plane':    (1,  8,  'plane', {}),
    'blind':    (1,  8,  'base',  {'blind_kill': True}),
    'truth':    (1,  8,  'base',  {}),
    'shift':    (3,  8,  'base',  {}),
    'beast':    (1,  8,  'base',  {}),
    'guard':    (2,  8,  'base',  {}),
    'lucky':    (3,  8,  'base',  {}),
    'otrat':    (2,  8,  'base',  {}),
    'tilt':     (12, 8,  'base',  {'tilt': True}),   # №12/B22: вспышки/заморозки в ленте
    'reserve':  (2, 8,   'base',  {'reserve': True}),  # №13/B23: удержания РПД + взвод обмена
    'rvgate':   (2, 8,   'base',  {'reserve': True, 'reserve_gate': True}),  # №13/B23b: строгий гейт
    'grudge':   (2, 8,   'base',  {'grudge': True}),   # №14/B25: месть по старой обиде (💢)
    'grwin':    (2, 8,   'base',  {'grudge_window': True}),  # №14/B25: окно 2 цикла — записи увядают
}


def run(code):
    """Прогнать свидетеля: вернуть (st, P, Counter типов ленты)."""
    seed, n, sit, cfg = W[code]
    log = []
    st, P = bb_full.run_game(seed, n, log=log, situation=sit, cfg=cfg)
    return st, P, collections.Counter(e['type'] for e in parse_log(log))


def survivors(P):
    return [p['seat'] for p in P if p['alive'] and not p['limbo']]


# ---------------------------------------------------------------- ветки механик

def test_glass():          # отражение: стойка
    st, P, ty = run('glass');      assert ty['reflect_stance'] >= 1

def test_otrat():          # отражение: возврат
    st, P, ty = run('otrat');      assert ty['reflect_back'] >= 1

def test_buddhist():       # перерождение
    st, P, ty = run('buddhist');   assert ty['reincarnate'] >= 1

def test_doll():           # кукла создана и простаивала
    st, P, ty = run('doll')
    assert ty['doll_made'] == 1 and st['dolls'] == 1 and ty['doll_idle'] >= 1

def test_link():           # связка партнёров
    st, P, ty = run('link');       assert ty['link'] >= 1

def test_sniper():         # условный триггер: снайпер
    st, P, ty = run('sniper');     assert ty['cond_sniper'] >= 1

def test_quota():          # провал квоты
    st, P, ty = run('quota');      assert ty['quota_fail'] >= 1

def test_hcancel():        # отмена Жатвы
    st, P, ty = run('hcancel')
    assert ty['harvest_cancel'] >= 1 and st['hc_used'] == 1

def test_hleader():        # Жатва бьёт по лидеру (harvest_pick=leader)
    st, P, ty = run('hleader')
    assert ty['harvest_leader'] >= 1 and st['harvests'] == ty['harvest_leader']

def test_hburn():          # сгорание сверх лимита руки
    st, P, ty = run('hburn')
    assert ty['hand_limit_burn'] == st['limit_burns'] >= 1 and st['max_hand'] == 7

def test_draft():          # взятие из общего пула (draft)
    st, P, ty = run('draft')
    assert ty['draft_take'] == st['draft_takes'] >= 1

def test_lives():          # вторая жизнь: потеря жизни без смерти
    st, P, ty = run('lives');      assert ty['life_lost'] >= 1

def test_vfx():            # фильм показан
    st, P, ty = run('vfx');        assert ty['film'] >= 1

def test_midturn():        # B17: смерть обрывает живой ход
    st, P, ty = run('midturn')
    assert ty['midturn_stop'] == st['midturn_stops'] >= 1

def test_twin():           # пара предателей назначена, цель достигнута
    st, P, ty = run('twin')
    assert ty['traitors'] == 1 and len(st['traitors']) == 2 and st['traitor_win'] == 9

def test_pressure():       # давление стола
    st, P, ty = run('pressure');   assert ty['pressure'] >= 1

def test_escal():          # эскалация Жатвы (harvest_mode=escalate)
    st, P, ty = run('escal')
    assert ty['harvest_esc'] >= 1 and st['harvests'] >= 1

def test_anvil():          # промах тяжёлого урона
    st, P, ty = run('anvil');      assert ty['anvil_miss'] >= 1

def test_chronist():       # хроно-обновление рук
    st, P, ty = run('chronist');   assert ty['chronicler'] >= 1

def test_deal():           # сделка состоялась
    st, P, ty = run('deal')
    assert ty['deal'] == st['deals'] >= 1

def test_betray():         # предательство исполнено
    st, P, ty = run('betray')
    assert ty['betrayal'] == st['betrayals'] >= 1

def test_demon():          # внешняя сущность действует
    st, P, ty = run('demon')
    assert ty['demon_act'] == st['demon_acts'] >= 1 and ty['demon_init'] >= 1

def test_one1():           # эффект «единица»
    st, P, ty = run('one1');       assert ty['one1'] >= 1

def test_kick():           # пинок/сброс
    st, P, ty = run('kick');       assert ty['kick'] >= 1

def test_plane():          # финал ситуации plane
    st, P, ty = run('plane');      assert ty['plane_final'] == 1

def test_blind():          # слепое убийство (blind_kill)
    st, P, ty = run('blind');      assert ty['blind_kill'] >= 1

def test_truth():          # проверка правды
    st, P, ty = run('truth');      assert ty['truth'] >= 1

def test_shift():          # сдвиг очерёдности
    st, P, ty = run('shift');      assert ty['shift'] >= 1

def test_beast():          # спасбросок от зверя
    st, P, ty = run('beast');      assert ty['beast_save'] >= 1

def test_guard():          # удар пережит (защита)
    st, P, ty = run('guard');      assert ty['survive_hit'] >= 1

def test_lucky():          # удача
    st, P, ty = run('lucky');      assert ty['lucky'] >= 1


# ---------------------------------------------------------------- структурные

def test_tilt():           # №12/B22: тильт-строки в ленте (ON)
    st, P, cnt = run('tilt')
    assert cnt['tilt'] >= 1, 'свидетель тильта не сработал'
    assert st['tilt_acts'] >= 1, 'ON: ни одного решения под тильтом'


def test_tilt_off_ledger():  # №12/B22: OFF — гроссбух ведётся, строк ↯ нет, сдвигов нет
    seed, n, sit, _ = W['tilt']
    log = []
    st, P = bb_full.run_game(seed, n, log=log, situation=sit, cfg={})
    assert st['tilt_trig'] > 0, 'OFF: триггеров нет — гроссбух мёртв'
    assert st['tilt_acts'] == 0, 'OFF: сдвиги весов просочились'
    assert not any('↯' in l for l in log), 'OFF: строки тильта в каноне'
    assert collections.Counter(e['type'] for e in parse_log(log))['tilt'] == 0


def test_tilt_chain_bounds():  # №12/B22: инварианты цепочки «провал→месть→провал»
    for code in ('tilt', 'midturn', 'betray'):
        seed, n, sit, cfg = W[code]
        for arm in ({}, {'tilt': True}):
            st, P = bb_full.run_game(seed, n, situation=sit, cfg=arm)
            assert st['tilt_trig'] == st['tilt_hot'] + st['tilt_cold'] + st['tilt_mid'], code
            assert st['tilt_chain_fail'] <= st['tilt_chain_attack'] <= st['tilt_trig'], code


def test_reserve():         # №13/B23: ON — удержания в ленте, обмен взводится
    st, P, cnt = run('reserve')
    assert cnt['reserve'] >= 1, 'свидетель резерва не сработал'
    assert st['reserve_hold'] >= 1 and st['reserve_armed'] >= 1, 'ON: нет ни удержания, ни взвода'
    assert st['reserve_acts'] >= 1, 'ON: choose() не видел реактивной карты'


def test_reserve_off_ledger():  # №13/B23: OFF — гроссбух ведётся, строк 🧊 нет, удержаний нет
    seed, n, sit, _ = W['reserve']
    log = []
    st, P = bb_full.run_game(seed, n, log=log, situation=sit, cfg={})
    assert st['reserve_turns'] > 0, 'OFF: возможностей не видно — гроссбух мёртв'
    assert st['reserve_hold'] == 0 and st['reserve_acts'] == 0, 'OFF: поведение просочилось'
    assert collections.Counter(e['type'] for e in parse_log(log))['reserve'] == 0


def test_reserve_gate():    # №13/B23b: STRICT — потраченные РПД не дают реакции взвестись
    seed, n, sit, _ = W['rvgate']
    st_g, P = bb_full.run_game(seed, n, situation=sit, cfg={'reserve_gate': True})
    st_r, P = bb_full.run_game(seed, n, situation=sit, cfg={'reserve': True, 'reserve_gate': True})
    st_0, P = bb_full.run_game(seed, n, situation=sit, cfg={})
    assert st_0['reserve_gate_blocked'] == 0, 'OFF: гейт просочился в канон'
    assert st_g['reserve_gate_blocked'] >= 1, 'STRICT: ни одной блокировки — не на чём мерить'
    assert st_g['reserve_armed'] < st_0['reserve_armed'], 'STRICT: гейт не сократил взводы'
    assert st_g['reserve_armed'] == 0, 'STRICT: при потраченных РПД реакция обязана молчать'
    assert st_r['reserve_hold'] >= 1, 'STRICT+резерв: удержаний нет'
    st_s, P = bb_full.run_game(seed, n, situation=sit,
                               cfg={'reserve': True, 'reserve_gate': True, 'reserve_strict': True})
    assert st_s['reserve_forced'] >= 1 and st_s['reserve_kept'] >= 1, 'жёсткий режим: нет пропусков/сохранений'
    assert st_s['reserve_armed'] >= 1, 'жёсткий режим: реакция не взводится'
    assert st_s['reserve_burned'] + st_s['reserve_kept'] >= 1, 'жёсткий режим: гроссбух не сходится'


def test_reserve_bounds():  # №13/B23: инварианты гроссбуха резерва
    for code in ('reserve', 'midturn', 'lucky'):
        seed, n, sit, _ = W[code]
        for arm in ({}, {'reserve': True}):
            st, P = bb_full.run_game(seed, n, situation=sit, cfg=arm)
            assert st['reserve_hold'] <= st['reserve_turns'], code
            assert st['reserve_acts'] >= st['reserve_hold'], code
            assert sum(st['reserve_holders'].values()) == st['reserve_hold'], code
            if not arm.get('reserve'):
                assert st['reserve_hold'] == 0 and st['reserve_acts'] == 0, code


def test_baseline_anchor():
    """Якорь базы: seed 777, N8, plane — end/выжившие/смерти/хэш лога бит-в-бит."""
    log = []
    st, P = bb_full.run_game(777, 8, log=log, situation='plane')
    h = hashlib.sha256('\n'.join(log).encode()).hexdigest()
    assert st['end'] == 5 and survivors(P) == [4, 5, 6, 7] and st['deaths'] == 5
    assert h.startswith('27144feca7c0f261'), f'лог изменился: {h[:16]}'


def test_determinism():
    """Один сид = одна партия: два прогона идентичны (включая лог)."""
    outs = []
    for _ in range(2):
        log = []
        st, P = bb_full.run_game(42, 8, log=log, situation='base')
        outs.append((st['end'], tuple(survivors(P)), st['deaths'],
                     hashlib.sha256('\n'.join(log).encode()).hexdigest()))
    assert outs[0] == outs[1]


def test_handlimit_guard():
    """Гард B15b: hand_limit < 7 категорий — ValueError (стартовая рука уже выше)."""
    try:
        bb_full.run_game(1, 8, cfg=dict(hand_limit=5))
        assert False, 'гард hand_limit<7 не сработал'
    except ValueError:
        pass


def test_max_hand_bounds():
    """Экономика печати самоограничена: пик руки 7..9 на всех свидетелях (старт = 7)."""
    for code in W:
        seed, n, sit, cfg = W[code]
        st, P = bb_full.run_game(seed, n, situation=sit, cfg=cfg)
        assert 7 <= st['max_hand'] <= 9, f'{code}: max_hand={st["max_hand"]}'


def test_grudge():          # №14/B25: ON — месть по обиде (💢 в ленте и в счётчике)
    st, P, cnt = run('grudge')
    assert cnt['grudge'] >= 1, 'свидетель обиды не сработал'
    assert st['grudge_revenge'] >= 1 and st['grudge_notes'] >= 1


def test_grudge_off_ledger():  # №14/B25: OFF — гроссбух ведётся, строк 💢 нет, поведение не просачивается
    seed, n, sit, _ = W['grudge']
    log = []
    st, P = bb_full.run_game(seed, n, log=log, situation=sit, cfg={})
    assert st['grudge_notes'] > 0, 'OFF: обид нет — гроссбух мёртв'
    assert st['grudge_revenge'] == 0 and st['grudge_marked'] == 0, 'OFF: поведение просочилось'
    assert collections.Counter(e['type'] for e in parse_log(log))['grudge'] == 0


def test_grudge_window():   # №14/B25: окно 2 цикла — старые записи увядают (faded)
    st, P, cnt = run('grwin')
    assert st['grudge_notes'] > 0
    assert st['grudge_faded'] >= 1, 'свидетель окна: ни одной увядшей оценки'


def test_grudge_ledger_bounds():  # №14/B25: сила обиды неотрицательна; мести ≤ агрессивных актов
    for code in ('grudge', 'grwin'):
        seed, n, sit, cfg = W[code]
        st, P = bb_full.run_game(seed, n, situation=sit, cfg=cfg)
        assert all(v[0] >= 0 for p in P for v in p.get('grudge', {}).values()), code
        harm = sum(st['acts'].get(k, 0) for k in ('kill', 'wound', 'steal', 'humiliate', 'mass', 'mass_steal'))
        assert st['grudge_revenge'] <= harm, code


# ---------------------------------------------------------------- раннер без pytest

if __name__ == '__main__':
    import sys
    import traceback
    tests = sorted((n, f) for n, f in globals().items() if n.startswith('test_') and callable(f))
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f'  ok  {name}')
        except Exception:
            failed.append(name)
            print(f'  FAIL {name}')
            traceback.print_exc()
    print(f'итого: {len(tests)} тестов, провалов: {len(failed)}' + (f' ({", ".join(failed)})' if failed else ''))
    sys.exit(1 if failed else 0)
