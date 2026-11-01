#!/usr/bin/env bash
# B13/B14: полный прогон приёмки после правок ядра/парсера/вьюера/отчётов.
# FULL=1 bash run_tests.sh — добавляет sweep всех вариантов №25 (5300 партий).
# Usage: bash run_tests.sh
set -u
cd "$(dirname "$0")"
FAIL=0
step(){ printf '\n\033[1m== %s\033[0m\n' "$1"; }
chk(){ if [ "$1" -ne 0 ]; then echo "  ✗ ПРОВАЛ: $2"; FAIL=$((FAIL+1)); else echo "  ✓ $2"; fi; }

step "1. синтаксис модулей"
python3 - <<'PY'
import ast, sys
for f in ('bb_core.py','bb_full.py','bb_events.py','bb_model.py','bb_html.py','bb.py',
          'validate.py','fuzz_test.py','coverage_test.py',
          'test_effects.py','make_fingerprints.py','csv_export.py'):
    ast.parse(open(f, encoding='utf-8').read())
print('  все модули парсятся')
PY
chk $? "ast.parse всех модулей"

step "2. наблюдатель-валидатор (инварианты правил)"
python3 validate.py | tail -2
chk ${PIPESTATUS[0]} "validate.py"

step "3. фазз (60 конфигов × 4 партии)"
python3 fuzz_test.py | tail -2
chk ${PIPESTATUS[0]} "fuzz_test.py"

step "4. базовая партия бит-в-бит: seed 777, N=8, plane"
python3 - <<'PY'
import hashlib, bb_full
log=[]; st,P=bb_full.run_game(777,8,log=log,situation='plane')
surv=[p['seat'] for p in P if p['alive'] and not p['limbo']]
h=hashlib.sha256('\n'.join(log).encode()).hexdigest()
print(f"  end={st['end']} выжили={surv} смертей={st['deaths']} sha256(лог)={h[:16]}")
assert st['end']==5 and surv==[4,5,6,7] and st['deaths']==5, 'BASELINE BROKEN'
assert h.startswith('27144feca7c0f261'), f'ЛОГ ИЗМЕНИЛСЯ: {h[:16]} != 27144feca7c0f261'
PY
chk $? "end 5 / выжили [4,5,6,7] / смертей 5 / хэш лога 27144feca7c0f261"

step "4b. регрессионные отпечатки эталонов (№20: 12 конфигов × сиды 1..20)"
python3 make_fingerprints.py | tail -2
chk ${PIPESTATUS[0]} "fingerprints.json совпадает с ядром"

step "5. покрытие парсера событий (все шаблоны say() ядра)"
python3 coverage_test.py | tail -3
chk ${PIPESTATUS[0]} "coverage_test.py"

step "6. регрессия B14: слепое убийство при пустом столе (seed 45, N8)"
python3 - <<'PY'
import bb_full
st, P = bb_full.run_game(45, 8, log=None, situation='base', cfg=dict(blind_kill=True))
print(f"  end={st['end']} смертей={st['deaths']} живых={st['alive']} (стол вымер — гард сработал)")
assert (st['end'], st['deaths'], st['alive']) == (5, 8, 0), 'РЕГРЕССИЯ B14'
PY
chk $? "blind_kill/seed45: 5/8/0"

step "6c. регрессия B15/№7: лимит руки (seed 55, N12, base, hand_limit=7)"
python3 - <<'PY'
import bb_full
log=[]; st,P=bb_full.run_game(55,12,log=log,situation='base',cfg=dict(hand_limit=7))
surv=[p['seat'] for p in P if p['alive'] and not p['limbo']]
burn=[l for l in log if 'лимит руки' in l]
print(f"  end={st['end']} surv={surv} смертей={st['deaths']} сгораний={st['limit_burns']} (строк в логе {len(burn)}) maxhand={st['max_hand']}")
assert (st['end'], st['deaths'], surv, st['limit_burns'], len(burn), st['max_hand']) == (10, 10, [3,5,12], 1, 1, 7), 'РЕГРЕССИЯ B15'  # переснято после B17 (обрыв хода смертью)
try:
    bb_full.run_game(1, 8, cfg=dict(hand_limit=5)); assert False, 'гард hand_limit<7 не сработал'
except ValueError: pass
print("  гард hand_limit<7 (ValueError): OK")
PY
chk $? "hand_limit=7: 10/10/[3,5,12]/burns=1 + гард (после B17)"

step "6d. регрессия B16/№9: драфт раскрытых (seed 58, N8, rpds_economy, draft=1)"
python3 - <<'PY'
import bb_full
log=[]; st,P=bb_full.run_game(58,8,log=log,situation='base',cfg=dict(mode='rpds_economy',draft=True))
surv=[p['seat'] for p in P if p['alive'] and not p['limbo']]
dl=[l for l in log if 'драфт:' in l]
print(f"  end={st['end']} surv={surv} смертей={st['deaths']} takes={st['draft_takes']} peak={st['draft_pool_peak']} left={st['draft_left']} (строк {len(dl)})")
assert (st['end'], surv, st['deaths'], st['draft_takes'], st['draft_pool_peak'], st['draft_left'], len(dl)) == (4, [4,5,7,8], 4, 4, 6, 5, 4), 'РЕГРЕССИЯ B16'
# канон не затронут: draft выключен — пул пуст, личных rev полным-полно
st2, P2 = bb_full.run_game(58, 8, log=None, situation='base', cfg=dict(mode='rpds_economy'))
assert st2['draft_takes'] == 0 and st2['draft_left'] == 0 and any(p['rev'] for p in P2), 'канон сломан'
print("  draft=off: takes=0, rev на местах — канон не затронут")
PY
chk $? "draft: 4/[4,5,7,8]/4/takes=4 + канон off"

step "6e. регрессия B17: смерть обрывает живой ход (seed 7, N8, base)"
python3 - <<'PY'
import bb_full
log=[]; st,P=bb_full.run_game(7,8,log=log,situation='base')
surv=[p['seat'] for p in P if p['alive'] and not p['limbo']]
stop=[l for l in log if l.strip().startswith('⛔')]
print(f"  end={st['end']} surv={surv} смертей={st['deaths']} обрывов={st['midturn_stops']} (строк ⛔ {len(stop)})")
assert (st['end'], surv, st['deaths'], st['midturn_stops'], len(stop)) == (4, [2,3,6,8], 4, 1, 1), 'РЕГРЕССИЯ B17'
PY
chk $? "midturn-stop: 4/[2,3,6,8]/4/1 обрыв"

step "6f. юнит-тесты веток механик (№19: 31 свидетель + 4 структурных)"
if python3 -c "import pytest" 2>/dev/null; then
  python3 -m pytest test_effects.py -q 2>&1 | tail -2
  chk ${PIPESTATUS[0]} "pytest test_effects.py"
else
  python3 test_effects.py | tail -2
  chk ${PIPESTATUS[0]} "test_effects.py (встроенный раннер)"
fi

step "6g. №11/B21: репутация (ON детерминирована и меняет игру; OFF=канон проверяют baseline+отпечатки)"
python3 - <<'PY'
import hashlib, bb_full
def h(seed, n, cfg):
    log = []
    bb_full.run_game(seed, n, log=log, cfg=cfg)
    return hashlib.sha256('\n'.join(log).encode()).hexdigest()
on1 = h(7, 8, {'reputation': True}); on2 = h(7, 8, {'reputation': True})
assert on1 == on2, 'reputation ON недетерминирована'
diff = sum(h(s, 8, {}) != h(s, 8, {'reputation': True}) for s in range(1, 13))
assert diff >= 1, 'reputation ON не изменила ни одной партии из 12'
print(f'  6g OK: ON детерминирована, расхождение с каноном {diff}/12 партий')
PY
chk $? "репутация smoke"

step "6h. №12/B22: тильт (ON детерминирован и меняет игру; гроссбух ведётся и при OFF)"
python3 - <<'PY'
import hashlib, bb_full
def h(seed, n, cfg):
    log = []
    bb_full.run_game(seed, n, log=log, cfg=cfg)
    return hashlib.sha256('\n'.join(log).encode()).hexdigest()
on1 = h(12, 8, {'tilt': True}); on2 = h(12, 8, {'tilt': True})
assert on1 == on2, 'tilt ON недетерминирован'
diff = sum(h(s, 8, {}) != h(s, 8, {'tilt': True}) for s in range(1, 13))
assert diff >= 1, 'tilt ON не изменил ни одной партии из 12'
log = []
st, P = bb_full.run_game(12, 8, log=log, cfg={})   # OFF: гроссбух ведётся, ↯ в логе нет
assert st['tilt_trig'] > 0, 'OFF: нет триггеров — не на чем мерить'
assert not any('↯' in l for l in log), 'OFF: строки тильта просочились в канон'
assert st['tilt_trig'] == st['tilt_hot'] + st['tilt_cold'] + st['tilt_mid'], 'OFF: направления не сходятся'
assert st['tilt_chain_fail'] <= st['tilt_chain_attack'] <= st['tilt_trig'], 'OFF: цепочки вне границ'
assert st['tilt_acts'] == 0, 'OFF: tilt_acts должен быть 0'
print(f'  6h OK: ON детерминирован, расхождение {diff}/12; OFF гроссбух trig={st["tilt_trig"]}, месть {st["tilt_chain_attack"]}, цепочки {st["tilt_chain_fail"]}')
PY
chk $? "тильт smoke"

step "6i. №13/B23: планирование резерва (ON детерминирован и меняет игру; гроссбух ведётся и при OFF)"
python3 - <<'PY'
import hashlib, bb_full
def h(seed, n, cfg):
    log = []
    bb_full.run_game(seed, n, log=log, cfg=cfg)
    return hashlib.sha256('\n'.join(log).encode()).hexdigest()
on1 = h(2, 8, {'reserve': True}); on2 = h(2, 8, {'reserve': True})
assert on1 == on2, 'reserve ON недетерминирован'
diff = sum(h(s, 8, {}) != h(s, 8, {'reserve': True}) for s in range(1, 13))
assert diff >= 1, 'reserve ON не изменил ни одной партии из 12'
log = []
st, P = bb_full.run_game(2, 8, log=log, cfg={'reserve': True})
assert st['reserve_hold'] > 0 and not any('РПДС' in l and '🧊' in l for l in log), 'ON: удержаний нет'
log = []
st, P = bb_full.run_game(2, 8, log=log, cfg={})   # OFF: гроссбух ведётся, 🧊 в логе нет
assert st['reserve_turns'] > 0, 'OFF: нет возможностей — не на чём мерить'
assert not any('🧊' in l for l in log), 'OFF: строки резерва просочились в канон'
assert st['reserve_hold'] == 0 and st['reserve_acts'] == 0, 'OFF: поведение просочилось'
g1 = h(2, 8, {'reserve': True, 'reserve_gate': True}); g2 = h(2, 8, {'reserve': True, 'reserve_gate': True})
assert g1 == g2, 'reserve+gate недетерминирован'
diff_gate = sum(h(s, 8, {'reserve_gate': True}) != h(s, 8, {}) for s in range(1, 13))
assert diff_gate >= 1, 'гейт не изменил ни одной партии из 12 — не на чём мерить'
stg, Pg = bb_full.run_game(2, 8, cfg={'reserve_gate': True})
assert stg['reserve_gate_blocked'] >= 0
str2, P2 = bb_full.run_game(2, 8, cfg={'reserve': True, 'reserve_gate': True})
st0, P0 = bb_full.run_game(2, 8, cfg={})
assert stg['reserve_armed'] < st0['reserve_armed'], 'STRICT: гейт не сократил число взводов'
assert str2['reserve_hold'] >= 1, 'STRICT+резерв: удержаний нет'
sts, Ps = bb_full.run_game(2, 8, cfg={'reserve': True, 'reserve_gate': True, 'reserve_strict': True})
assert sts['reserve_forced'] >= 1 and sts['reserve_kept'] >= 1, 'жёсткий режим: нет пропусков/сохранений'
assert sts['reserve_armed'] >= 1, 'жёсткий режим: реакция не взводится'
assert h(2, 8, {'reserve': True, 'reserve_gate': True, 'reserve_strict': True}) == h(2, 8, {'reserve': True, 'reserve_gate': True, 'reserve_strict': True}), 'жёсткий режим недетерминирован'
print(f'  6i OK: ON детерминирован, расхождение {diff}/12; OFF возможности {st["reserve_turns"]}, взводов {st["reserve_armed"]}; '
      f'гейт изменил {diff_gate}/12 партий (блокировки {stg["reserve_gate_blocked"]}, взводы {st0["reserve_armed"]}→{stg["reserve_armed"]}); '
      f'STRICT взводов {str2["reserve_armed"]}, жёсткий: пропусков {sts["reserve_forced"]}, сохранено {sts["reserve_kept"]}, взводов {sts["reserve_armed"]}')
PY
chk $? "резерв smoke"

step "6j. №14/B25: долгая память обид (ON детерминирован и меняет игру; гроссбух ведётся и при OFF)"
python3 - <<'PY'
import hashlib, bb_full
def h(seed, n, cfg):
    log = []
    bb_full.run_game(seed, n, log=log, cfg=cfg)
    return hashlib.sha256('\n'.join(log).encode()).hexdigest()
on1 = h(2, 8, {'grudge': True}); on2 = h(2, 8, {'grudge': True})
assert on1 == on2, 'grudge ON недетерминирован'
diff = sum(h(s, 8, {}) != h(s, 8, {'grudge': True}) for s in range(1, 13))
assert diff >= 1, 'grudge ON не изменил ни одной партии из 12'
log = []
st, P = bb_full.run_game(2, 8, log=log, cfg={'grudge': True})
assert st['grudge_revenge'] >= 1 and any('💢' in l for l in log), 'ON: мести по обиде нет'
assert all(v[0] >= 0 for p in P for v in p.get('grudge', {}).values()), 'ON: отрицательная обида'
log = []
st, P = bb_full.run_game(2, 8, log=log, cfg={})   # OFF: гроссбух ведётся, 💢 в логе нет
assert st['grudge_notes'] > 0, 'OFF: обид не видно — гроссбух мёртв'
assert not any('💢' in l for l in log), 'OFF: строки обид просочились в канон'
assert st['grudge_revenge'] == 0 and st['grudge_marked'] == 0 and st['grudge_faded'] == 0, 'OFF: поведение просочилось'
w1 = h(2, 8, {'grudge_window': True}); w2 = h(2, 8, {'grudge_window': True})
assert w1 == w2, 'grudge_window недетерминирован'
stw, Pw = bb_full.run_game(2, 8, cfg={'grudge_window': True})
assert stw['grudge_faded'] >= 1, 'WINDOW: ни одной увядшей записи — не на чём мерить'
print(f'  6j OK: ON детерминирован, расхождение {diff}/12; OFF notes={st["grudge_notes"]}, peak={st["grudge_peak"]}; WINDOW faded={stw["grudge_faded"]}, месть {stw["grudge_revenge"]}')
PY
chk $? "память обид smoke"

step "6b. все варианты карты чувствительности №25 без падений (FULL=1 — прогон)"
if [ "${FULL:-0}" = "1" ]; then
  python3 - <<'PY'
import sys, traceback
import run_tornado as RT, bb_full
jobs = [('BASE', None, 8, 'base')]
for fac in RT.HANDLES + RT.CONTEXT:
    for label, cfg, vn, vsit in RT._norm_variants(fac):
        jobs.append((label, cfg, vn or 8, vsit or 'base'))
bad = 0
for name, cfg, n, sit in jobs:
    for s in range(1, 101):
        try:
            bb_full.run_game(s, n, log=None, situation=sit, cfg=cfg)
        except Exception as e:
            bad += 1; print('  ПАДЕНИЕ', name, s, n, sit, type(e).__name__, e)
print(f"  конфигураций {len(jobs)} × 100 партий = {len(jobs) * 100}, падений {bad}")
assert bad == 0, 'есть падения в карте чувствительности'
PY
  chk $? "sweep №25 (5300 партий)"
else
  echo "  пропущено (запуск: FULL=1 bash run_tests.sh)"
fi

step "7. HTML-вьюер: витринные страницы партий"
if command -v node >/dev/null 2>&1; then
  for f in VIEW_game_*.html; do
    out=$(node view_test.js "$f" 2>&1 | tail -1)
    printf '  %-34s %s\n' "$f" "$out"
    case "$out" in *"0 провалов"*) ;; *) FAIL=$((FAIL+1));; esac
  done
else
  echo "  node не найден — пропускаю (проверь вручную в браузере)"
fi
chk 0 "вьюеры партий"

step "8. страница карты чувствительности (SVG, самодостаточность)"
python3 - <<'PY'
import re, os, xml.etree.ElementTree as ET
f = 'VIEW_tornado.html'
if not os.path.exists(f):
    print('  нет файла — пропускаю'); raise SystemExit(0)
s = open(f, encoding='utf-8').read()
svgs = re.findall(r'<svg.*?</svg>', s, re.S)
for g in svgs: ET.fromstring(g)
ext = [u for u in re.findall(r'(?:src|href)="([^"]+)"', s)]
print(f"  {len(s) // 1024} КБ, svg-блоков {len(svgs)} (все валидны), таблиц {s.count('<table')}, внешних ссылок {len(ext)}")
assert len(svgs) >= 4 and not ext and 'ВЕРДИКТ' in s, 'страница tornado неполная'
PY
chk $? "VIEW_tornado.html"

step "8b. CSV-экспорт (№23): smoke на сохранённых результатах"
python3 - <<'PY'
import csv, os, tempfile
import csv_export
src = [f for f in ('tornado_n8.json', 'matrix_b8.json', 'handlimit.json', 'draft.json',
                   'tornado_triggers.json', 'matrix_results.json') if os.path.exists(f)]
assert src, 'нет ни одного json результатов'
total = 0
for f in src:
    out = os.path.join(tempfile.gettempdir(), f.replace('.json', '.csv'))
    for p, sec, n in csv_export.export(f, out, all_sections=True):
        assert n > 0, f'{f}/{sec}: пустая таблица'
        rows = list(csv.reader(open(p, encoding='utf-8-sig'), delimiter=';'))
        assert len(rows) == n + 1 and rows[0], f'{p}: шапка+строки не сошлись'
        total += 1
print(f'  файлов {len(src)} → csv-таблиц {total}, все с шапкой и строками')
PY
chk $? "csv_export: автоопределение 6 форматов"

printf '\n\033[1mИТОГ: %s\033[0m\n' "$([ "$FAIL" -eq 0 ] && echo 'ВСЁ ЗЕЛЁНОЕ' || echo "ПРОВАЛОВ: $FAIL")"
exit $((FAIL>0))
