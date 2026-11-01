# -*- coding: utf-8 -*-
"""№25: отчёт по карте чувствительности — TORNADO.md + самодостаточная SVG-диаграмма.

Вход: json из run_tornado.py (парные прогоны, сиды 1..G одинаковые у всех вариантов).
Считаем ПАРНУЮ дельту: delta[i] = метрика_варианта[i] − метрика_BASE[i] по одному и тому же сиду,
поэтому шум ГСЧ вычитается и виден именно эффект ручки, а не удача жребия.
Значимость: |t| = |mean(delta)| / SE(delta), SE = sd/sqrt(G); порог «не отличимо от шума» |t| < 2.

Usage:
  python3 tornado_report.py --in tornado_n8.json tornado_n12.json \
         --md TORNADO.md --html VIEW_tornado.html
"""
import argparse, json, math, statistics, html as H

W, PAD_L, PAD_R, ROW = 980, 300, 90, 26          # геометрия SVG
REPRO = ('python3 run_tornado.py --n 8  --sit base --games 100 --context --out tornado_n8.json\n'
         'python3 run_tornado.py --n 12 --sit base --games 100 --out tornado_n12.json\n'
         'python3 run_triggers.py --n 8 12 --games 100 --out tornado_triggers.json\n'
         'python3 tornado_report.py --in tornado_n8.json tornado_n12.json --triggers tornado_triggers.json '
         '--md TORNADO.md --html VIEW_tornado.html --verdict VERDICT_tornado.md\n'
         'bash run_tests.sh   # validate + fuzz + baseline бит-в-бит + покрытие парсера + вьюеры\n')
METRICS = [('end', 'Длина партии (циклы)', '#2f6fb0', '#c9762f'),
           ('deaths', 'Число смертей', '#a83246', '#2f8f7a')]


def paired(base, var, key):
    d = [v - b for v, b in zip(var[key], base[key])]
    g = len(d)
    m = statistics.mean(d)
    sd = statistics.pstdev(d) if g > 1 else 0.0
    se = sd / math.sqrt(g) if g else 0.0
    return dict(mean=m, se=se, t=(m / se if se > 1e-9 else (math.inf if abs(m) > 1e-9 else 0.0)))


def load_triggers(path):
    """json из run_triggers.py → {id фактора: срабатываний за 100 партий} (по первому подходящему ключу)."""
    if not path:
        return {}
    d = json.load(open(path, encoding='utf-8'))['counts']
    return {n: {k: v for k, v in c.items()} for n, c in d.items()}


def trig_for(triggers, fac_id, n):
    c = triggers.get(str(n), {})
    if fac_id in c:
        return c[fac_id]
    for k, v in c.items():
        if k.startswith(fac_id + '='):
            return v
    return None


def analyse(doc, triggers=None):
    """→ список факторов с вариантами, парными дельтами и разбросом (для tornado)."""
    runs, base = doc['runs'], doc['runs']['BASE']
    out = []
    for fac in doc['factors']:
        vs = []
        for v in fac['variants']:
            key = f'{fac["id"]}|{v["label"]}'
            r = runs[key]
            e, d = paired(base, r, 'end'), paired(base, r, 'deaths')
            vs.append(dict(label=v['label'], cfg=v['cfg'], n=v['n'], sit=v['sit'], run=r, de=e, dd=d))
        spread = {}
        for mk in ('end', 'deaths'):
            vals = [v['de' if mk == 'end' else 'dd']['mean'] for v in vs] + [0.0]   # 0 = канон
            spread[mk] = dict(lo=min(vals), hi=max(vals), width=max(vals) - min(vals))
        noise = dict(end=statistics.mean([v['de']['se'] for v in vs]),
                     deaths=statistics.mean([v['dd']['se'] for v in vs]))
        out.append(dict(id=fac['id'], name=fac['name'], note=fac['note'], base=fac['base'],
                        group=fac['group'], variants=vs, spread=spread, noise=noise,
                        triggers=trig_for(triggers or {}, fac['id'], doc['meta']['n'])))
    return out


def sig_mark(t):
    if not math.isfinite(t): return '∞'
    a = abs(t)
    return '—' if a < 2 else ('✳' if a < 4 else '✳✳')


def svg_tornado(facs, mk, title, sub):
    """Статический SVG: по фактору — полоса от min до max парной дельты (0 = канон)."""
    facs = [f for f in facs if f['group'] == 'HANDLES']
    facs = sorted(facs, key=lambda f: -f['spread'][mk]['width'])
    col_pos, col_neg = {m[0]: (m[2], m[3]) for m in METRICS}[mk]
    top = max(max(abs(f['spread'][mk]['hi']), abs(f['spread'][mk]['lo'])) for f in facs)
    noise = statistics.mean([f['noise'][mk] for f in facs])
    top = max(top, 4 * noise) * 1.08
    h = PAD_R + len(facs) * ROW + 46
    x0, scale = PAD_L, (W - PAD_L - PAD_R) / 2 / top
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" font-family="Segoe UI,Arial,sans-serif">',
         f'<text x="14" y="22" font-size="17" font-weight="700" fill="#17242f">{H.escape(title)}</text>',
         f'<text x="14" y="40" font-size="12" fill="#5c6b78">{H.escape(sub)}</text>']
    # шкала
    step = 10 ** math.floor(math.log10(top)) if top >= 1 else .1
    while top / step < 3: step /= 2
    while top / step > 7: step *= 2
    v = -math.floor(top / step) * step
    while v <= top + 1e-9:
        x = x0 + v * scale
        s.append(f'<line x1="{x:.1f}" y1="52" x2="{x:.1f}" y2="{h - 18}" stroke="#dfe5ea" stroke-width="1"/>')
        s.append(f'<text x="{x:.1f}" y="{h - 4}" font-size="11" fill="#7b8894" text-anchor="middle">{v:+g}</text>')
        v += step
    # зона шума
    s.append(f'<rect x="{x0 - 2 * noise * scale:.1f}" y="52" width="{4 * noise * scale:.1f}" height="{h - 70}" '
             f'fill="#9aa7b2" opacity="0.16"/>')
    s.append(f'<text x="{x0:.1f}" y="64" font-size="11" fill="#7b8894" text-anchor="middle">серое = ±2σ шума (100 партий)</text>')
    s.append(f'<line x1="{x0}" y1="52" x2="{x0}" y2="{h - 18}" stroke="#17242f" stroke-width="1.6"/>')
    for i, f in enumerate(facs):
        y = 74 + i * ROW
        lo, hi = f['spread'][mk]['lo'], f['spread'][mk]['hi']
        lab = f'{f["name"]}'
        s.append(f'<text x="{PAD_L - 10}" y="{y + 5}" font-size="12.5" fill="#17242f" text-anchor="end">{H.escape(lab)}</text>')
        s.append(f'<text x="{PAD_L - 10}" y="{y + 17}" font-size="10" fill="#8593a0" text-anchor="end">канон: {H.escape(str(f["base"]))}</text>')
        if hi >= 0 and lo <= 0:
            s.append(f'<rect x="{x0 + lo * scale:.1f}" y="{y - 8}" width="{max(1.2, (hi - lo) * scale):.1f}" height="13" '
                     f'fill="{col_pos}" opacity="0.85" rx="2"/>')
        else:
            a, b = sorted([lo, hi])
            s.append(f'<rect x="{x0 + a * scale:.1f}" y="{y - 8}" width="{max(1.2, (b - a) * scale):.1f}" height="13" '
                     f'fill="{col_neg if (a + b) / 2 < 0 else col_pos}" opacity="0.85" rx="2"/>')
        s.append(f'<text x="{x0 + hi * scale + 5:.1f}" y="{y + 4}" font-size="10.5" fill="#4a5a67">{hi:+.2f}</text>')
        if abs(lo) > .005:
            s.append(f'<text x="{x0 + lo * scale - 5:.1f}" y="{y + 4}" font-size="10.5" fill="#4a5a67" text-anchor="end">{lo:+.2f}</text>')
    s.append('</svg>')
    return '\n'.join(s)


def md_table(facs, mk, group='HANDLES'):
    rows = [f for f in facs if f['group'] == group]
    rows = sorted(rows, key=lambda f: -f['spread'][mk]['width'])
    has_trig = any(f['triggers'] is not None for f in rows)
    head = '| Фактор (канон) | Разброс | Сильнее всего «−» | Сильнее всего «+» | Срабаты-<br>ваний/100 | Вердикт |'
    L = [head, '|---|---|---|---|' + ('---|' if has_trig else '') + '---|']
    for f in rows:
        sp = f['spread'][mk]
        key = 'de' if mk == 'end' else 'dd'
        vs = sorted(f['variants'], key=lambda v: v[key]['mean'])
        lo, hi = vs[0], vs[-1]
        dlo, dhi = lo[key], hi[key]
        tmax = max(abs(v[key]['t']) for v in vs)
        verdict = 'шум' if tmax < 2 else ('заметно' if tmax < 6 else 'СИЛЬНО')
        base_lbl = str(f['base']) if 'канон' in str(f['base']) else f'канон ({f["base"]})'
        if lo is hi and dlo['mean'] >= 0:
            lo_s, hi_s = f'{base_lbl} +0.00 —', f'{hi["label"]} {dhi["mean"]:+.2f} {sig_mark(dhi["t"])}'
        elif lo is hi:
            lo_s, hi_s = f'{lo["label"]} {dlo["mean"]:+.2f} {sig_mark(dlo["t"])}', f'{base_lbl} +0.00 —'
        else:
            lo_s = f'{lo["label"]} {dlo["mean"]:+.2f} {sig_mark(dlo["t"])}'
            hi_s = f'{hi["label"]} {dhi["mean"]:+.2f} {sig_mark(dhi["t"])}'
        trig = f'| {f["triggers"]} ' if (has_trig and f['triggers'] is not None) else ('| — ' if has_trig else '')
        L.append(f'| **{f["name"]}** ({f["base"]}) | {sp["width"]:.2f} | {lo_s} | {hi_s} {trig}| {verdict} |')
    return '\n'.join(L)


def md_variants(f, mk):
    key = 'de' if mk == 'end' else 'dd'
    L = ['| Вариант | end ср. | Δend (t) | смертей | Δсмертей (t) | p90 | Жатва | воскр. | пат |',
         '|---|---|---|---|---|---|---|---|---|']
    b = None
    for v in sorted(f['variants'], key=lambda v: v[key]['mean']):
        r = v['run']
        L.append(f'| {v["label"]} | {r["end_mean"]:.2f} | {v["de"]["mean"]:+.2f} ({sig_mark(v["de"]["t"])}) '
                 f'| {r["deaths_mean"]:.2f} | {v["dd"]["mean"]:+.2f} ({sig_mark(v["dd"]["t"])}) | {r["p90"]} '
                 f'| {r["harv_pct"]}% | {r["rev_pct"]}% | {r["stall_pct"]}% |')
    return '\n'.join(L)


def build_md(docs, ana):
    L = ['# КАРТА ЧУВСТВИТЕЛЬНОСТИ «БЛИЦ БОЙ» (№25, tornado) — ядро B14', '']
    for doc in docs:
        m = doc['meta']
        L.append(f'- прогон: N={m["n"]}, ситуация {m["sit"]}, {m["games"]} партий на вариант '
                 f'(**лимит пользователя ≤100 соблюдён**), всего {m["games_total"]} партий, {m["seconds"]} с.')
    L += ['', '## Как читать', '',
          '1. **Парный метод.** Все варианты прогнаны на одних и тех же сидах 1..100. Дельта = результат варианта минус '
          'результат канона **на том же сиде**, поэтому удача жребия вычитается, а не усредняется.',
          '2. **Разброс фактора** = расстояние между самым «укорачивающим» и самым «удлиняющим» вариантом этой ручки. '
          'Чем длиннее полоса на диаграмме — тем сильнее ручка управляет длиной партии/смертностью.',
          '3. **Серая зона на диаграмме** = ±2σ статистического шума при 100 партиях. Полоса внутри серого — ручка не работает.',
          '4. **Значимость**: `—` |t|<2 (не отличимо от шума), `✳` 2..4, `✳✳` >4 (эффект надёжный).',
          '5. Канонические значения НЕ менялись (меню п.10 — заморозка): это замер, а не тюнинг.',
          '6. Колонка «срабатываний за 100 партий» (run_triggers.py) показывает, сколько раз ветка ручки реально '
          'выстрелила. Если срабатываний много, а разброс в пределах серой зоны — ручка живая, но на темп не влияет.', '']
    for doc, facs in zip(docs, ana):
        m = doc['meta']
        base = doc['runs']['BASE']
        L += [f'## Прогон N={m["n"]}, ситуация {m["sit"]}', '',
              f'Канон: end **{base["end_mean"]}** (p50 {statistics.median(base["end"]):.0f}, p90 {base["p90"]}), '
              f'смертей **{base["deaths_mean"]}**, выживает {base["alive_mean"]}, Жатва в {base["harv_pct"]}% партий, '
              f'воскрешения в {base["rev_pct"]}%, пат {base["stall_pct"]}%.', '',
              '### Длина партии (end)', '', md_table(facs, 'end'), '',
              '### Смертность (deaths)', '', md_table(facs, 'deaths'), '']
        ctx = [f for f in facs if f['group'] == 'CONTEXT']
        if ctx:
            L += ['### Рамка партии (не ручки настройки)', '',
                  '| Условие | end ср. | Δend | смертей | Δсмертей | p90 | Жатва | воскр. |',
                  '|---|---|---|---|---|---|---|---|']
            for f in ctx:
                for v in sorted(f['variants'], key=lambda v: v['n']):
                    r = v['run']
                    L.append(f'| {f["name"]}: **{v["label"]}** | {r["end_mean"]:.2f} | {v["de"]["mean"]:+.2f} '
                             f'| {r["deaths_mean"]:.2f} | {v["dd"]["mean"]:+.2f} | {r["p90"]} | {r["harv_pct"]}% | {r["rev_pct"]}% |')
            L.append('')
        top = sorted([f for f in facs if f['group'] == 'HANDLES'], key=lambda f: -f['spread']['end']['width'])[:6]
        L += ['### Топ-6 рычагов темпа — все варианты', '']
        for f in top:
            L += [f'#### {f["name"]} (канон: {f["base"]})', f'_{f["note"]}_', '', md_variants(f, 'end'), '']
    return '\n'.join(L)


def build_html(docs, ana, path, verdict=''):
    css = ('body{margin:0;background:#f2f5f7;color:#17242f;font:14px/1.5 "Segoe UI",Arial,sans-serif}'
           '.wrap{max-width:1040px;margin:0 auto;padding:18px}'
           'h1{font-size:22px;margin:6px 0 2px}h2{font-size:17px;margin:22px 0 6px;border-bottom:2px solid #d6dee4;padding-bottom:4px}'
           '.sub{color:#5c6b78;font-size:12.5px;margin-bottom:14px}'
           '.card{background:#fff;border:1px solid #dfe5ea;border-radius:10px;padding:10px 12px;margin:10px 0;box-shadow:0 1px 2px rgba(20,40,60,.05)}'
           'table{border-collapse:collapse;width:100%;font-size:12.5px}'
           'th,td{border-bottom:1px solid #e7edf1;padding:4px 6px;text-align:left}'
           'th{background:#eef3f6;font-weight:600}tr:hover td{background:#f7fbfd}'
           '.note{background:#fff8e6;border:1px solid #f0dfae;border-radius:8px;padding:8px 10px;font-size:12.5px;margin:10px 0}'
           '.k{font-weight:700}.neg{color:#a83246}.pos{color:#1f6f4f}')
    body = [f'<h1>КАРТА ЧУВСТВИТЕЛЬНОСТИ «БЛИЦ БОЙ» (№25)</h1>',
            '<div class="sub">однофакторный tornado · парные сиды 1..100 · ≤100 партий на конфигурацию · ядро B14 · '
            'серым показан уровень статистического шума</div>',
            '<div class="note"><b>Как читать.</b> Ноль на шкале = каноническая настройка (её значения не менялись). '
            'Полоса фактора тянется от самого «укорачивающего» варианта к самому «удлиняющему». '
            'Длинная полоса = ручка сильно управляет игрой; полоса внутри серой зоны = ручка не работает (эффект меньше шума 100 партий).</div>']
    for doc, facs in zip(docs, ana):
        m, base = doc['meta'], doc['runs']['BASE']
        body.append(f'<h2>Прогон N={m["n"]} · ситуация {m["sit"]} · {m["games"]} партий на вариант</h2>')
        body.append(f'<div class="sub">Канон: end <b>{base["end_mean"]}</b> (p90 {base["p90"]}), смертей <b>{base["deaths_mean"]}</b>, '
                    f'Жатва {base["harv_pct"]}%, воскрешения {base["rev_pct"]}%, пат {base["stall_pct"]}%</div>')
        for mk, title, _a, _b in METRICS:
            unit = 'цикла' if mk == 'end' else 'смертей'
            body.append('<div class="card">' + svg_tornado(
                facs, mk, f'{title}: разброс по факторам',
                f'Δ относительно канона ({unit}), N={m["n"]}/{m["sit"]}') + '</div>')
        # сводная таблица
        rows = sorted([f for f in facs if f['group'] == 'HANDLES'], key=lambda f: -f['spread']['end']['width'])
        has_trig = any(f['triggers'] is not None for f in rows)
        body.append('<div class="card"><table><tr><th>Фактор (канон)</th><th>Разброс end</th><th>Разброс смертей</th>'
                    '<th>Сильнее всего укорачивает</th><th>Сильнее всего удлиняет</th>'
                    + ('<th>Срабатываний<br>за 100 партий</th>' if has_trig else '') + '<th>Сила</th></tr>')
        for f in rows:
            vs = sorted(f['variants'], key=lambda v: v['de']['mean'])
            lo, hi = vs[0], vs[-1]
            tmax = max(max(abs(v['de']['t']), abs(v['dd']['t'])) for v in vs)
            strong = 'шум' if tmax < 2 else ('заметно' if tmax < 6 else '<b>СИЛЬНО</b>')
            base_lbl = str(f['base']) if 'канон' in str(f['base']) else f'канон ({f["base"]})'
            if lo is hi:
                if lo['de']['mean'] >= 0:
                    lo_s, hi_s = f'<span style="color:#8593a0">{H.escape(base_lbl)} +0.00</span>', \
                        f'{H.escape(hi["label"])} <span class="pos">{hi["de"]["mean"]:+.2f}</span>'
                else:
                    lo_s, hi_s = f'{H.escape(lo["label"])} <span class="neg">{lo["de"]["mean"]:+.2f}</span>', \
                        f'<span style="color:#8593a0">{H.escape(base_lbl)} +0.00</span>'
            else:
                lo_s = f'{H.escape(lo["label"])} <span class="neg">{lo["de"]["mean"]:+.2f}</span>'
                hi_s = f'{H.escape(hi["label"])} <span class="pos">{hi["de"]["mean"]:+.2f}</span>'
            trig = f'<td>{f["triggers"] if f["triggers"] is not None else "—"}</td>' if has_trig else ''
            body.append(f'<tr><td>{H.escape(f["name"])} <span style="color:#8593a0">({H.escape(str(f["base"]))})</span></td>'
                        f'<td>{f["spread"]["end"]["width"]:.2f}</td><td>{f["spread"]["deaths"]["width"]:.2f}</td>'
                        f'<td>{lo_s}</td><td>{hi_s}</td>{trig}<td>{strong}</td></tr>')
        body.append('</table></div>')
        ctx = [f for f in facs if f['group'] == 'CONTEXT']
        if ctx:
            body.append('<div class="card"><h2 style="margin-top:4px">Рамка партии (условия, не ручки)</h2><table>'
                        '<tr><th>Условие</th><th>end</th><th>Δend</th><th>смертей</th><th>Δсмертей</th><th>p90</th>'
                        '<th>Жатва</th><th>воскр.</th><th>пат</th></tr>')
            for f in ctx:
                for v in sorted(f['variants'], key=lambda v: (v['sit'], v['n'])):
                    r = v['run']
                    body.append(f'<tr><td>{H.escape(f["name"])}: <b>{H.escape(v["label"])}</b></td><td>{r["end_mean"]:.2f}</td>'
                                f'<td>{v["de"]["mean"]:+.2f}</td><td>{r["deaths_mean"]:.2f}</td><td>{v["dd"]["mean"]:+.2f}</td>'
                                f'<td>{r["p90"]}</td><td>{r["harv_pct"]}%</td><td>{r["rev_pct"]}%</td><td>{r["stall_pct"]}%</td></tr>')
            body.append('</table></div>')
    if verdict:
        vd = verdict.replace('\n\n', '</p><p>').replace('\n', ' ')
        body.append('<div class="card"><h2 style="margin-top:4px">ВЕРДИКТ</h2><p>' + vd + '</p></div>')
    page = ('<!doctype html><html lang="ru"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>БЛИЦ БОЙ — карта чувствительности (№25)</title>'
            f'<style>{css}</style></head><body><div class="wrap">' + '\n'.join(body) +
            '</div></body></html>')
    open(path, 'w', encoding='utf-8').write(page)
    return path, len(page)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', nargs='+', required=True)
    ap.add_argument('--md', default='TORNADO.md'); ap.add_argument('--html', default='VIEW_tornado.html')
    ap.add_argument('--verdict', help='md-файл с текстом ВЕРДИКТА: пришивается в конец отчёта и в HTML')
    ap.add_argument('--triggers', help='json из run_triggers.py: колонка «срабатываний за 100 партий»')
    a = ap.parse_args()
    docs = [json.load(open(p, encoding='utf-8')) for p in a.inp]
    trig = load_triggers(a.triggers)
    ana = [analyse(d, trig) for d in docs]
    md = build_md(docs, ana)
    verdict = open(a.verdict, encoding='utf-8').read().strip() if a.verdict else ''
    if verdict:
        md += '\n## ВЕРДИКТ\n\n' + verdict + '\n\n## Воспроизведение\n\n```\n' + REPRO + '```\n'
    open(a.md, 'w', encoding='utf-8').write(md)
    p, size = build_html(docs, ana, a.html, verdict)
    print(f'{a.md} ({len(md.splitlines())} строк) | {p} ({size / 1024:.0f} КБ)')
    for doc, facs in zip(docs, ana):
        m = doc['meta']
        top = sorted([f for f in facs if f['group'] == 'HANDLES'], key=lambda f: -f['spread']['end']['width'])
        print(f'N{m["n"]}/{m["sit"]} топ-8 рычагов темпа: ' + ', '.join(
            f'{f["name"]}({f["spread"]["end"]["width"]:.2f})' for f in top[:8]))


if __name__ == '__main__':
    main()
