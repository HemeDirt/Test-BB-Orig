# -*- coding: utf-8 -*-
"""№23 (B18): экспорт JSON-результатов прогонов в CSV («длинный формат» для Excel/pandas).

Автоопределение формы входного json:
  A) список строк-словарей (batch/matrix: matrix_*.json)      → таблица rows: строка на конфиг,
     вложенные словари разворачиваются в колонки «a.b», списки скаляров склеиваются через |
  B) словарь имя→агрегат (matrix_results.json)                 → то же, name из ключа
  C) файлы прогонов с секциями (tornado_*.json, handlimit.json, draft.json, tornado_triggers.json):
     runs   — если внутри ПАРНЫЕ МАССИВЫ по партиям (tornado: end[100], deaths[100]) → длинный
              формат: строка на партию (run, game, …массивы…, скаляры-агрегаты повторяются);
              если скаляры (handlimit/draft) → строка на прогон
     pairs  — строка на (прогон, метрика): pair, metric, delta, sd, sem, mark
     counts — строка на (N, триггер): n, trigger, count
     meta   — key/value;  factors — строка на фактор (variants json-строкой)

Кодировка utf-8-sig (BOM) — кириллица открывается в Excel без плясок; разделитель по умолчанию «;»
(русский Excel), для pandas/инструментов — --sep ,.

CLI:  python3 csv_export.py IN.json OUT.csv [--table auto|runs|rows|pairs|counts|meta|factors] [--all] [--sep ;]
      python3 bb.py csv IN.json --out OUT.csv [...]            # то же через единый CLI
API:  export(infile, outpath, table='auto', sep=';', all_sections=False) -> [(path, section, nrows), ...]
"""
import argparse
import csv
import json
import os

SECTION_ORDER = ['runs', 'rows', 'counts', 'pairs', 'factors', 'meta']


def _flat(v):
    """Значение ячейки: словари/списки → строка (json / |), остальное как есть."""
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return '|'.join(json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else str(x) for x in v)
    return v


def flatten(d, prefix=''):
    """Словарь → плоская строка: вложенные словари в колонки 'a.b'."""
    row = {}
    for k, v in d.items():
        key = f'{prefix}{k}'
        if isinstance(v, dict):
            row.update(flatten(v, key + '.'))
        else:
            row[key] = _flat(v)
    return row


def _runs_rows(runs):
    """runs: имя → dict. Массивы равной длины >1 = попартичные серии → длинный формат."""
    arrays = {}
    for name, r in runs.items():
        lens = {len(v) for v in r.values() if isinstance(v, list) and len(v) > 1
                and all(isinstance(x, (int, float)) for x in v)}
        arrays[name] = lens
    long_form = any(lens for lens in arrays.values())
    rows = []
    if long_form:
        for name, r in runs.items():
            keys = [k for k, v in r.items() if isinstance(v, list) and len(v) > 1]
            g = min((len(r[k]) for k in keys), default=0)
            scal = {k: _flat(v) for k, v in r.items() if k not in keys}
            for i in range(g):
                row = {'run': name, 'game': i + 1}
                row.update({k: r[k][i] for k in keys})
                row.update(scal)
                rows.append(row)
    else:
        for name, r in runs.items():
            rows.append(dict(run=name, **flatten(r)))
    return rows


def _pairs_rows(pairs):
    rows = []
    for pair, metrics in pairs.items():
        for metric, d in metrics.items():
            if isinstance(d, dict):
                rows.append(dict(pair=pair, metric=metric, **{k: _flat(v) for k, v in d.items()}))
            else:
                rows.append(dict(pair=pair, metric=metric, value=_flat(d)))
    return rows


def detect(data):
    """json → {section: [row-dict, ...]} (пустые секции не включаются)."""
    sec = {}
    if isinstance(data, list):
        sec['rows'] = [flatten(x) if isinstance(x, dict) else {'value': _flat(x)} for x in data]
        return sec
    if not isinstance(data, dict):
        return {'rows': [{'value': _flat(data)}]}
    if 'runs' in data and isinstance(data['runs'], dict):
        sec['runs'] = _runs_rows(data['runs'])
    if 'pairs' in data and isinstance(data['pairs'], dict):
        sec['pairs'] = _pairs_rows(data['pairs'])
    if 'counts' in data and isinstance(data['counts'], dict):
        sec['counts'] = [dict(n=n, trigger=t, count=_flat(c))
                         for n, dd in data['counts'].items() for t, c in dd.items()]
    if 'factors' in data and isinstance(data['factors'], list):
        sec['factors'] = [flatten(f) for f in data['factors']]
    if 'meta' in data and isinstance(data['meta'], dict):
        sec['meta'] = [{'key': k, 'value': _flat(v)} for k, v in data['meta'].items()]
    if not sec:   # форма B: словарь имя→агрегат (или произвольный плоский словарь)
        nested = all(isinstance(v, dict) for v in data.values()) and data
        if nested:
            sec['rows'] = [dict(name=k, **flatten(v)) for k, v in data.items()]
        else:
            sec['rows'] = [flatten(data)]
    return sec


def _columns(rows):
    cols = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    return cols


def write_csv(path, rows, sep=';'):
    cols = _columns(rows)
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=sep, restval='')
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def export(infile, outpath, table='auto', sep=';', all_sections=False):
    """Главный вход. Возвращает [(path, section, nrows), ...]."""
    data = json.load(open(infile, encoding='utf-8'))
    sec = detect(data)
    if not sec:
        raise ValueError(f'{infile}: не нашёл ни одной таблицы')
    if table != 'auto':
        if table not in sec:
            raise ValueError(f'{infile}: секции {table!r} нет, есть {", ".join(sec)}')
        sec = {table: sec[table]}
    elif not all_sections:
        pick = next((s for s in SECTION_ORDER if s in sec), None)
        sec = {pick: sec[pick]}
    out = []
    multi = all_sections and len(sec) > 1
    for name, rows in sec.items():
        p = outpath
        if multi:
            stem, ext = os.path.splitext(outpath)
            p = f'{stem}.{name}{ext or ".csv"}'
        out.append((p, name, write_csv(p, rows, sep)))
    return out


def main():
    ap = argparse.ArgumentParser(prog='csv_export.py', description='№23: JSON результатов → CSV (длинный формат)')
    ap.add_argument('infile'); ap.add_argument('outpath')
    ap.add_argument('--table', default='auto', choices=['auto'] + SECTION_ORDER)
    ap.add_argument('--all', dest='all_sections', action='store_true',
                    help='выгрузить все найденные секции (файлы с суффиксом .runs/.pairs/…)')
    ap.add_argument('--sep', default=';', help='разделитель (по умолчанию «;» под русский Excel)')
    a = ap.parse_args()
    for p, name, n in export(a.infile, a.outpath, a.table, a.sep, a.all_sections):
        print(f'csv: {p} [{name}] строк: {n}')


if __name__ == '__main__':
    main()
