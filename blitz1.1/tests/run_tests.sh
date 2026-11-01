#!/usr/bin/env bash
# Приёмочный прогон проекта БЛИЦ БОЙ — новая живая линия (src/bb.py + src/game_sim.py).
# Старая линия B1–B25 (bb_full и её тесты) мертва: нет deck_print.json. Лежит в archive/old_engine/.
# Запуск из любой папки:  bash tests/run_tests.sh
set -u
R="$(cd "$(dirname "$0")/.." && pwd)"   # корень проекта blitz/
FAIL=0
step(){ printf '\n\033[1m== %s\033[0m\n' "$1"; }
chk(){ if [ "$1" -ne 0 ]; then echo "  ✗ ПРОВАЛ: $2"; FAIL=$((FAIL+1)); else echo "  ✓ $2"; fi; }

step "1. синтаксис модулей ядра"
python3 - "$R" <<'PY'
import ast, sys, os
R = sys.argv[1]
for f in ('src/bb.py','src/game_sim.py','src/make_web.py','blitz.py'):
    ast.parse(open(os.path.join(R,f), encoding='utf-8').read())
print('  все модули парсятся')
PY
chk $? "ast.parse модулей ядра"

step "2. детерминизм партии (seed 5): два прогона — одинаковый лог"
python3 - "$R" <<'PY'
import sys, os, hashlib, subprocess
R = sys.argv[1]
def run(seed):
    return subprocess.run([sys.executable, os.path.join(R,'src','game_sim.py'), str(seed)],
                          capture_output=True, text=True).stdout
a, b = run(5), run(5)
assert a == b and len(a) > 500, 'НЕДЕТЕРМИНИЗМ или пустой лог'
print(f'  sha256={hashlib.sha256(a.encode()).hexdigest()[:16]} OK ({len(a.splitlines())} строк лога)')
PY
chk $? "детерминизм seed 5"

step "3. пакет партий без падений (node, 30 сидов)"
if command -v node >/dev/null 2>&1; then
  node "$R/src/test_game.js" 2>&1 | tail -1
  chk ${PIPESTATUS[0]} "test_game.js"
else
  python3 - "$R" <<'PY'
import sys, os, subprocess
R = sys.argv[1]
for s in range(1, 31):
    r = subprocess.run([sys.executable, os.path.join(R,'src','game_sim.py'), str(s), '--quiet'],
                       capture_output=True, text=True)
    assert r.returncode == 0, f'ПАДЕНИЕ на seed {s}: {r.stderr[-200:]}'
print('  30 партий (python) без падений')
PY
  chk $? "batch 30 партий (python)"
fi

step "4. канонные колоды: статистика и целостность"
python3 "$R/src/bb.py" deck 2>&1 | tail -2
chk ${PIPESTATUS[0]} "bb.py deck"

step "5. живая веб-страница: генерация"
python3 "$R/src/make_web.py" 777 2>&1 | tail -1
chk $? "make_web.py → docs/preview/index.html"

printf '\n\033[1mИТОГ: %s\033[0m\n' "$([ "$FAIL" -eq 0 ] && echo 'ВСЁ ЗЕЛЁНОЕ' || echo "ПРОВАЛОВ: $FAIL")"
exit $((FAIL>0))
