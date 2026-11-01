# -*- coding: utf-8 -*-
"""B18/тройка: bb.py += субкоманда csv (№23); run_tests.sh += шаги 4b (№20), 6f (№19), 8b (№23).
Протокол: точные цели (count==1), ast.parse до записи, запись в конце."""
import ast

def patch(path, pairs, is_py=True):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        c = s.count(old)
        assert c == 1, f'{path}: цель найдена {c} раз (нужно 1): {old[:70]!r}'
        s = s.replace(old, new)
    if is_py:
        ast.parse(s)
    open(path, 'w', encoding='utf-8').write(s)
    print(f'OK {path}: {len(pairs)} правок')

# ---------------------------------------------------------------- bb.py
CSV_DOC = """  view    HTML-вьюер партии (№21): самодостаточная страница (лента/места/графики/лог)
          — либо пересчётом из сида, либо из уже сохранённого лога (--log PATH)
"""
CSV_DOC_NEW = CSV_DOC + """  csv     экспорт JSON-результатов прогонов в CSV (№23): автоопределение формы
          (rows/runs/pairs/counts/meta/factors), длинный формат по партиям, utf-8-sig, «;» под Excel
"""

EX_OLD = "  python3 bb.py view --log log.txt --out VIEW_log.html        # без снимков: лента+лог+фильтры\n"
EX_NEW = EX_OLD + "  python3 bb.py csv tornado_n8.json --out tornado_n8.csv --all  # длинный формат: run,game,end,deaths,…\n"

CMD = '''def cmd_csv(a):
    """№23: JSON-результаты прогонов → CSV (автоопределение формы — см. csv_export.py)."""
    import csv_export
    for p, name, n in csv_export.export(a.infile, a.out, table=a.table, sep=a.sep, all_sections=a.all):
        print(f'csv: {p} [{name}] строк: {n}')

def main():'''

SUB_OLD = "    e.set_defaults(fn=cmd_events)\n    a = ap.parse_args()"
SUB_NEW = """    e.set_defaults(fn=cmd_events)
    c = sub.add_parser('csv', help='№23: JSON-результаты → CSV (Excel/pandas)')
    c.add_argument('infile', metavar='IN.json'); c.add_argument('--out', required=True, metavar='OUT.csv')
    c.add_argument('--table', default='auto', choices=['auto', 'runs', 'rows', 'pairs', 'counts', 'factors', 'meta'])
    c.add_argument('--all', dest='all_sections', action='store_true', help='все секции (файлы с суффиксами)')
    c.add_argument('--sep', default=';', help='разделитель (default «;» под русский Excel)')
    c.set_defaults(fn=cmd_csv)
    a = ap.parse_args()"""

patch('bb.py', [(CSV_DOC, CSV_DOC_NEW), (EX_OLD, EX_NEW), ('def main():', CMD), (SUB_OLD, SUB_NEW)])

# ---------------------------------------------------------------- run_tests.sh
MOD_OLD = "          'validate.py','fuzz_test.py','coverage_test.py'):"
MOD_NEW = "          'validate.py','fuzz_test.py','coverage_test.py',\n          'test_effects.py','make_fingerprints.py','csv_export.py'):"

S4_OLD = 'chk $? "end 5 / выжили [4,5,6,7] / смертей 5 / хэш лога 27144feca7c0f261"\n'
S4_NEW = S4_OLD + '''
step "4b. регрессионные отпечатки эталонов (№20: 12 конфигов × сиды 1..20)"
python3 make_fingerprints.py | tail -2
chk ${PIPESTATUS[0]} "fingerprints.json совпадает с ядром"
'''

S6_OLD = 'chk $? "midturn-stop: 4/[2,3,6,8]/4/1 обрыв"\n'
S6_NEW = S6_OLD + '''
step "6f. юнит-тесты веток механик (№19: 31 свидетель + 4 структурных)"
if python3 -c "import pytest" 2>/dev/null; then
  python3 -m pytest test_effects.py -q 2>&1 | tail -2
  chk ${PIPESTATUS[0]} "pytest test_effects.py"
else
  python3 test_effects.py | tail -2
  chk ${PIPESTATUS[0]} "test_effects.py (встроенный раннер)"
fi
'''

S8_OLD = 'chk $? "VIEW_tornado.html"\n'
S8_NEW = S8_OLD + '''
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
'''

patch('run_tests.sh', [(MOD_OLD, MOD_NEW), (S4_OLD, S4_NEW), (S6_OLD, S6_NEW), (S8_OLD, S8_NEW)], is_py=False)
print('B18/тройка: патч применён')
