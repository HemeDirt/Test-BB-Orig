# -*- coding: utf-8 -*-
"""B13 (п.21): модель партии для HTML-вьюера — всё, что нужно странице, одним JSON-совместимым dict.

Два прогона одного сида (детерминированно идентичны):
  1) с логом            → лента событий (bb_events.parse_log) + исходный текст;
  2) со снимками SNAP   → состояния мест на конец каждого цикла (профессия/спецка/обмен/ОР/жетоны…).
Плюс запись перемешиваний ГСЧ (_record_shuffles) — чтобы назвать стартовую руку, профессию
и спецкарту каждого места без вскрытия ядра.

Usage:
  import bb_model; m = bb_model.build_model(777, 8, 'plane'); print(m['final'])
"""
import json, os, random, collections
import bb_full, bb_events
from bb_core import DECK, CATS

HERE = os.path.dirname(os.path.abspath(__file__))

ARCH_RU = {
 'aggr': 'Агрессор', 'hoard': 'Плюшкин', 'actor': 'Актёр', 'manip': 'Манипулятор', 'team': 'Командный',
 'turtle': 'Черепаха', 'gambler': 'Азартный', 'chaos': 'Хаотик', 'medic': 'Медик', 'marauder': 'Мародёр',
 'star': 'Звезда', 'lurker': 'Тихушник', 'fun': 'Весельчак', 'rampage': 'Берсерк', 'fixated': 'Зацикленный',
 'loyal': 'Верный', 'fun_late': 'Поздний весельчак', 'suicider': 'Самоубийца', 'unionist': 'Союзник',
 'paranoid': 'Параноик', 'diplomat': 'Дипломат', 'collector_live': 'Собиратель', 'veteran': 'Ветеран'}
AGENDA_RU = {'secret_kill': 'тайное убийство', 'sabotage_heal': 'саботаж лечения',
             'protect_one': 'защита одного', 'hidden_hoard': 'тайный запас', None: None, '': None}
CAUSE_RU = {'wounds': 'раны (ОР)', 'harvest': 'Жатва', 'link': 'связка', 'kill': 'убийство',
            'crit_fail': 'крит-провал', 'exile': 'изгнание/суд', 'forced': 'принудительно (ситуация)',
            'limbo_lost': 'лимбо на пороге', 'anvil': 'наковальня', 'sniper': 'снайпер',
            'mass': 'массовое ранение', 'pressure': 'давление', 'demon': 'вторая личность',
            'betrayal': 'предательство', 'plane': 'финал самолёта', 'quota': 'квота', 'truth': 'истина'}
SIT_RU = {'base': 'Ночь в панельке (база печати)', 'plane': 'Самолёт в Гренландию',
          'pole': 'Поле на остановке', 'purg': 'Чистилище',
          'hrono': 'Машина времени (Пьяная хронология)', 'amkary': 'Амкары и Касторама (команды)'}
# 20 цветов мест: различимые на тёмном фоне, соседние не похожи
PALETTE = ['#f2b544', '#5cc8f2', '#7ee081', '#f27d7d', '#c79bf5', '#4fd6c4', '#f2a0c4', '#d9d36a',
           '#8fb2ff', '#ffa861', '#9be07a', '#e07ab0', '#6fd8f0', '#c9a06a', '#b6b0f5', '#78e0b0',
           '#f28f6a', '#a3d94f', '#69b8e6', '#e6cfa3']


class _Shuffled(list):
    """Список, помеченный как «перемешивается игровым ГСЧ» (не используется: см. _record_shuffles)."""


class _record_shuffles:
    """Контекст: пишет ВСЕ rng.shuffle(...) во время прогона вместе с id генератора.

    Возвращает список записей [(id(rng), копия_после_перемешивания), ...]; вызывающий сам
    находит поток игрового ГСЧ (random.Random(seed)) по характерному первому перемешиванию.
    Порядок shuffle-вызовов в bb_full.run_game: 7 категорий (CATS), профессии, спецкарты,
    тени, обмен, пул архетипов, spec_order — всего 13 записей (индексы 0..12).
    """

    def __init__(self):
        self.rec = []
        self._orig = None

    def __enter__(self):
        self._orig = random.Random.shuffle

        def patched(r, x, *a, **k):
            self._orig(r, x, *a, **k)
            try:
                self.rec.append((id(r), list(x)))
            except TypeError:
                pass
        random.Random.shuffle = patched
        return self.rec

    def __exit__(self, *exc):
        random.Random.shuffle = self._orig
        return False


def _game_stream(rec, seed):
    """Из записи перемешиваний выделить поток игрового ГСЧ (random.Random(seed))."""
    probe = random.Random(seed)
    want = DECK[CATS[0]][:]
    probe.shuffle(want)
    by = collections.OrderedDict()
    for rid, lst in rec:
        by.setdefault(rid, []).append(lst)
    for rid, lists in by.items():
        if lists and lists[0] == want:
            return lists
    return []


def _shadow_full(text):
    """Тень по тексту из лога. Ядро печатает card[:30] и ВСЕГДА добавляет «…», поэтому:
    короткие карты (≤30) приходят как «полный текст + …», длинные — как обрезок. Пробуем оба варианта."""
    t = (text or '').strip()
    tags = dict(DECK['тени'])
    for cand in (t, t.rstrip('…').strip()):
        if not cand:
            continue
        if cand in tags:                                  # точное совпадение (короткая карта)
            return cand, tags[cand]
        hits = [c for c in tags if c.startswith(cand)]     # обрезок длинной карты
        if hits:
            return hits[0], tags[hits[0]]
    return t, None


def _spec_name(i):
    sp = DECK['спецкарты']
    return sp[i] if isinstance(i, int) and 0 <= i < len(sp) else None


def build_model(seed, n, sit='base', cfg=None):
    """Прогнать партию и собрать модель для вьюера. Возвращает dict (JSON-совместимый)."""
    cfg = dict(cfg or {})
    log = []
    with _record_shuffles() as rec:
        st, P = bb_full.run_game(seed, n, log=log, situation=sit, cfg=cfg)
    snap = []
    old = bb_full.SNAP
    bb_full.SNAP = snap
    try:
        st2, P2 = bb_full.run_game(seed, n, situation=sit, cfg=cfg)
    finally:
        bb_full.SNAP = old
    assert st2['end'] == st['end'], 'снимочный прогон разошёлся с логовым'

    ev = bb_events.parse_log(log)
    snaps = {c: s for c, s in snap}
    last_c = max(snaps) if snaps else 0
    start = snaps.get(0, {'meta': [], 'rows': []})
    faces = (cfg.get('dice') or {}).get('faces', 20) if isinstance(cfg.get('dice'), dict) else 20

    # --- расшифровка колод по записанным перемешиваниям (поток игрового ГСЧ)
    recs = _game_stream(rec, seed)
    decks = {k: recs[i] for i, k in enumerate(CATS) if i < len(recs)}
    profs = recs[7] if len(recs) > 7 else []
    specs = recs[8] if len(recs) > 8 else []
    shads = recs[9] if len(recs) > 9 else []
    exchs = recs[10] if len(recs) > 10 else []
    spec_order = recs[12] if len(recs) > 12 else []   # 11 = пул архетипов, 12 = порядок спецкарт
    abl = cfg.get('ablate')
    abl_set = {'spec', 'prof', 'shad', 'exch', 'traits'} if abl == 'all' else ({abl} if abl else set())

    hands = {}
    for i in range(n):
        if cfg.get('mode') == 'rpds_economy' or 'traits' in abl_set:
            hands[i + 1] = {}
        else:
            h = {}
            for k in CATS:
                d = decks.get(k) or []
                h[k] = d[len(d) - 1 - i] if len(d) > i else None
            hands[i + 1] = h
    spec_by_seat = {}
    if spec_order and 'spec' not in abl_set:
        for i in range(n):
            j = spec_order[i % len(spec_order)]
            spec_by_seat[i + 1] = specs[j] if j < len(specs) else None

    # --- игроки ---
    meta = {m[0]: m for m in start['meta']}
    rows0 = {r['seat']: r for r in start['rows']}
    last_rows = {r['seat']: r for r in snaps.get(last_c, {'rows': []})['rows']}
    players = []
    dolls = []
    for p in P:
        if p.get('is_doll'):                 # чучело Таксидермиста: запись-дубль места, не игрок
            dolls.append(dict(seat=p['seat'], prof='Чучело', or_=0, tokens=p.get('tokens', 0)))
            continue
        s = p['seat']
        r0, rl = rows0.get(s, {}), last_rows.get(s, {})
        mrow = meta.get(s, [s, '', '', '', []])
        v = p['pers']
        fate = ('alive' if p['alive'] and not p['limbo'] else
                ('limbo' if p['alive'] else 'dead'))
        players.append(dict(
            seat=s, prof=p.get('prof') or '', prof_name=p.get('prof_name') or mrow[1],
            arch=mrow[2], arch_ru=ARCH_RU.get(mrow[2], mrow[2]), archs=list(p.get('archs') or []),
            agenda=mrow[3], agenda_ru=AGENDA_RU.get(mrow[3], mrow[3]),
            aggr=v['aggr'], help=v['help'], neut=v['neut'], blood=v['blood'],
            fear=v.get('fear'), detach=v.get('detach'), coop=v.get('coop'),
            team=(p['team'] if p['team'] is not None and p['team'] >= 0 else None),
            fate=fate, dead_c=p['dead_c'], revived=p['revived'], limbo=bool(p['limbo']),
            or_=p['or_'], lives=p['lives'], tokens=p['tokens'], kills=p['kills'],
            dealt_w=p.get('dealt_w', 0), dealt_k=p.get('dealt_k', 0),
            uses=dict(p['uses']), hand=hands.get(s, {}),
            spec=(spec_by_seat.get(s) or _spec_name(r0.get('spec_i'))),
            spec_i=r0.get('spec_i'), prof_by_seat=(profs[(s - 1) % len(profs)] if profs else None),
            is_doll=bool(p.get('is_doll')), ghost=(p.get('ghost') or None),
            color=PALETTE[(s - 1) % len(PALETTE)]))

    # --- лента событий с расшифровкой карт ---
    events = []
    for e in ev:
        d = dict(e)
        if d['type'] == 'shadow':
            full, tag = _shadow_full(d.get('card', ''))
            d['card'], d['tag'] = full, tag
        elif d['type'] == 'spec':
            d['name'] = _spec_name(d['idx'] - 1)
        d['raw'] = log[d['ln']].rstrip()
        events.append(d)

    # --- циклы ---
    cs = {e['c']: e for e in events if e['type'] == 'cycle_start'}
    c0 = 0 if any(e['c'] == 0 for e in events) else 1   # пролог: объявления до первого цикла (предатели и т.п.)
    cycles = []
    for c in range(c0, (st['end'] or last_c) + 1):
        h = cs.get(c, {})
        sn = snaps.get(c, {'rows': []})['rows']
        by = collections.defaultdict(lambda: dict(rev=0, dmg=0, heals=0, acts=0, rolls=0))
        for e in events:
            if e['c'] != c:
                continue
            for seat in _seats_of(e):
                if e['type'] == 'reveal':
                    by[seat]['rev'] += 1
                elif e['type'] in ('spec', 'shadow', 'exchange', 'rpds', 'mass_wound', 'mass_steal'):
                    by[seat]['acts'] += 1
                elif e['type'] == 'roll':
                    by[seat]['rolls'] += 1
                elif e['type'] == 'heal':
                    by[seat]['heals'] += 1
            if e['type'] == 'wound':
                by[e['seat']]['dmg'] += e['amt']
        cycles.append(dict(
            c=c, alive=h.get('alive'), ghosts=h.get('ghosts'), limbo=h.get('limbo'),
            deaths=sum(1 for e in events if e['c'] == c and e['type'] == 'death'),
            harvests=sum(1 for e in events if e['c'] == c and e['type'] in
                         ('harvest', 'harvest_esc', 'harvest_leader')),
            revives=sum(1 for e in events if e['c'] == c and e['type'] in
                        ('revive_tokens', 'revive_necro', 'revive_agent', 'reincarnate')),
            rolls=sum(1 for e in events if e['c'] == c and e['type'] == 'roll'),
            nat1=sum(1 for e in events if e['c'] == c and e['type'] == 'roll' and e['face'] == 1),
            nat20=sum(1 for e in events if e['c'] == c and e['type'] == 'roll' and e['face'] == faces),
            rows=[dict(seat=r['seat'], or_=r.get('or_') or 0, alive=r.get('alive'),
                       lives=r.get('lives'), tokens=r.get('tokens'), limbo=r.get('limbo'),
                       exch=r.get('exch'), frozen=r.get('frozen') or 0,
                       kills=r.get('kills') or 0, spec_used=bool(r.get('spec_used')),
                       used_rpd=bool(r.get('used_rpd')), pact=list(r.get('pact') or []),
                       **{('a_' + k): v for k, v in by[r['seat']].items()})
                  for r in sn],
            header=[l for l in log if l.strip().startswith(f'════ ЦИКЛ {c} ')]))

    # --- итог и графики ---
    ortl = [[c['c'], {str(r['seat']): r['or_'] for r in c['rows']}] for c in cycles]
    hist = collections.Counter(e['face'] for e in events if e['type'] == 'roll')
    causes = collections.Counter(e['cause'] for e in events if e['type'] == 'death')
    types = collections.Counter(e['type'] for e in events)
    final_ev = next((e for e in events if e['type'] == 'final'), None)
    model = dict(
        meta=dict(seed=seed, n=n, sit=sit, sit_ru=SIT_RU.get(sit, sit),
                  cfg={k: str(v) for k, v in cfg.items()},
                  core='B13', viewer='1.0', faces=faces,
                  end=st['end'], deaths=st['deaths'], harvests=st['harvests'], revives=st['revives'],
                  first_death=st['first_death'], stall=bool(st['stall']), nat1=bool(st['nat1']),
                  nat20=bool(st['nat20']), limbo_events=st.get('limbo_events', 0),
                  spec_uses=st.get('spec_uses', 0), prof_uses=st.get('prof_uses', 0),
                  shadow_uses=st.get('shadow_uses', 0), exch_uses=st.get('exch_uses', 0),
                  betrayals=st.get('betrayals', 0), deals=st.get('deals', 0),
                  demon_acts=st.get('demon_acts', 0), drag=st.get('drag_sum', 0),
                  survivors=(final_ev or {}).get('surv') or [p['seat'] for p in P if p['alive'] and not p['limbo']],
                  thr=st.get('thr'), lines=len(log), events=len(events)),
        players=players, dolls=dolls, cycles=cycles, events=events, log=log,
        cause_ru=CAUSE_RU, agenda_ru=AGENDA_RU, arch_ru=ARCH_RU,
        shadow_deck=[[c, t] for c, t in DECK['тени']],
        charts=dict(hist=[[f, hist.get(f, 0)] for f in range(1, faces + 1)],
                    alive=[[c['c'], c['alive'], c['ghosts'] or 0, c['limbo'] or 0] for c in cycles],
                    ortl=ortl,
                    causes=[[CAUSE_RU.get(k, k), v] for k, v in causes.most_common()],
                    types=[[k, v] for k, v in types.most_common()]))
    return model


SEAT_FIELDS = {'seat': 1, 'to': 1, 'target': 1, 'whom': 1, 'by': 1, 'a': 1, 'b': 1}


def _seats_of(e):
    """Все места, которых касается событие (для фильтра «мой игрок» и статистики цикла)."""
    out = []
    for k, w in SEAT_FIELDS.items():
        v = e.get(k)
        if isinstance(v, int) and v > 0:
            out.append(v)
    for k in ('targets', 'surv', 'heroes', 'villains', 'who', 'tgt'):
        v = e.get(k)
        if isinstance(v, list):
            out.extend(x for x in v if isinstance(x, int))
    return sorted(set(out))


def seats_of(e):
    return _seats_of(e)


if __name__ == '__main__':
    import sys
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 777
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    sit = sys.argv[3] if len(sys.argv) > 3 else 'plane'
    m = build_model(seed, n, sit)
    out = f'model_{seed}_N{n}_{sit}.json'
    json.dump(m, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    print('модель:', out, os.path.getsize(out), 'байт;',
          'циклов', len(m['cycles']), 'событий', m['meta']['events'],
          '| end', m['meta']['end'], 'выжили', m['meta']['survivors'])
    p1 = m['players'][0]
    print('P1:', p1['prof_name'], p1['arch_ru'], 'судьба', p1['fate'], 'спецка', (p1['spec'] or '')[:40])
    print('     стартовая рука:', {k: (v[:22] if v else None) for k, v in list(p1['hand'].items())[:3]})
