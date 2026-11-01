"""Универсальная проверка любого собранного файла: сама определяет размеры листов,
помечает часть карт «свалка»/«под вопросом», пересчитывает движком `formulas`
и сверяет автосвалку, СВОДКУ и ПОИСК.

    python3 test/verify_any.py <файл.xlsx> [шаг_пометки=37]
"""
import warnings, sys, time
warnings.filterwarnings("ignore")
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter as gc

path = sys.argv[1]
step = int(sys.argv[2]) if len(sys.argv) > 2 else 37
SERVICE = ("СВОДКА", "ПОИСК", "_ДАННЫЕ")

wb = load_workbook(path)
cats = [s for s in wb.sheetnames if s not in SERVICE]
info = {}
for name in cats:
    ws = wb[name]
    split = ws.cell(row=2, column=3).value != "Статус"
    dtitle = next(r for r in range(3, ws.max_row + 2)
                  if isinstance(ws.cell(row=r, column=1).value, str)
                  and ws.cell(row=r, column=1).value.startswith("⬇"))
    n = dtitle - 6                      # dtitle = (2 + n) + 4
    info[name] = dict(split=split, sc=4 if split else 3, n=n, d0=dtitle + 2,
                      dcap=dtitle + 1 + n)

# ── помечаем: каждую step-ю карту в свалку, каждую (step*2)-ю под вопросом ──
plan = {}
for name, d in info.items():
    ws = wb[name]
    dumped, doubt = [], []
    for i in range(1, d["n"] + 1):
        r = 2 + i
        if i % step == 0:
            ws.cell(row=r, column=d["sc"], value="свалка"); dumped.append(i)
        elif i % (step * 2) == 0:
            ws.cell(row=r, column=d["sc"], value="под вопросом"); doubt.append(i)
    plan[name] = (dumped, doubt)
wb.save(path)
print(f"помечено: свалка {sum(len(v[0]) for v in plan.values())}, "
      f"под вопросом {sum(len(v[1]) for v in plan.values())} (шаг {step})", flush=True)

t0 = time.time()
import formulas
fname = path.split("/")[-1]
sol = formulas.ExcelModel().loads(path).finish().calculate()
print(f"пересчёт: {time.time()-t0:.0f} с, узлов {len(sol)}", flush=True)

def val(sheet, cell):
    x = sol.get(f"'[{fname}]{sheet.upper()}'!{cell}")
    if x is None: return None
    x = getattr(x, "value", x)
    try: return x[0][0]
    except Exception: return x

ok, fails = True, []
def chk(c, m):
    global ok
    if not c: ok = False; fails.append(m)

print("\n— АВТОСВАЛКА ВНИЗУ ЛИСТА —")
for name in cats:
    d = info[name]; ws = wb[name]; dumped, doubt = plan[name]
    want = [(ws.cell(row=2 + i, column=2).value,
             ws.cell(row=2 + i, column=3).value if d["split"] else None) for i in dumped]
    got = []
    for k in range(1, d["n"] + 1):
        b = val(name, f"B{d['d0'] + k - 1}")
        if b in (None, ""): continue
        got.append((b, val(name, f"C{d['d0'] + k - 1}") if d["split"] else None))
    good = [w[0] for w in want] == [g[0] for g in got]
    mech = (not d["split"]) or all((w[1] or "") == (g[1] or "") for w, g in zip(want, got))
    zero = any(g[1] == 0 or g[1] is None and d["split"] and w[1] for g, w in zip(got, want))
    chk(good and mech, f"{name}: автосвалка")
    ex = (f"  1-я: {str(got[0][0])[:28]!r} | мех {str(got[0][1])[:30]!r}" if got and d["split"]
          else (f"  1-я: {str(got[0][0])[:46]!r}" if got else ""))
    print(f"{'OK  ' if good and mech else 'FAIL'} {name:20} карт {d['n']:4}  в свалке {len(got):3}/{len(want):3}"
          f"  вместимость {d['n']}  «0»-артефакт: {bool(zero)}{ex}", flush=True)
    if not good:
        print("   ждали:", [w[0][:30] for w in want[:3]], "\n   получили:", [g[0][:30] for g in got[:3]])

if "СВОДКА" in wb.sheetnames:
    print("\n— СВОДКА —")
    sws = wb["СВОДКА"]
    head = next(r for r in range(1, 90) if sws.cell(row=r, column=1).value == "Категория")
    td = 0
    for i, name in enumerate(cats):
        rr = head + 1 + i; d = info[name]; dumped, doubt = plan[name]
        vse, igra, vop, sval = (val("СВОДКА", f"{c}{rr}") for c in "CDEF")
        good = (int(vse) == d["n"] and int(sval) == len(dumped)
                and int(vop) == len(doubt) and int(igra) == d["n"] - len(dumped) - len(doubt))
        td += len(dumped); chk(good, f"СВОДКА {name}")
        print(f"{'OK  ' if good else 'FAIL'} {name:20} всего={int(vse):4} в игре={int(igra):4} "
              f"под вопросом={int(vop):3} свалка={int(sval):3}")
    tr = head + 1 + len(cats)
    it = int(val("СВОДКА", f"F{tr}")); chk(it == td, "СВОДКА ИТОГО")
    print(f"{'OK  ' if it == td else 'FAIL'} ИТОГО свалка={it} (эталон {td}), "
          f"всего карт={int(val('СВОДКА', f'C{tr}'))}")

if "ПОИСК" in wb.sheetnames:
    print("\n— ПОИСК ПО ВСЕЙ КОЛОДЕ —")
    allc = []
    for name in cats:
        d = info[name]; ws = wb[name]
        for i in range(1, d["n"] + 1):
            r = 2 + i
            a = ws.cell(row=r, column=2).value or ""
            b = ws.cell(row=r, column=3).value if d["split"] else None
            sep = " - " if name == "1 ПРОФЕССИЯ" else " — "
            allc.append((f"{a}{sep}{b}" if (d["split"] and b) else a, name,
                         ws.cell(row=r, column=d["sc"]).value))
    for term, stf in [("а", "все"), ("а", "свалка"), ("тень", "все"),
                      ("игрок", "под вопросом"), ("qqq", "все")]:
        wb2 = load_workbook(path); wb2["ПОИСК"]["C3"] = term; wb2["ПОИСК"]["C4"] = stf
        tmp = path.replace(".xlsx", "_s.xlsx"); wb2.save(tmp)
        s2 = formulas.ExcelModel().loads(tmp).finish().calculate()
        f2 = tmp.split("/")[-1]
        def v2(cell):
            x = s2.get(f"'[{f2}]ПОИСК'!{cell}"); x = getattr(x, "value", x)
            try: return x[0][0]
            except Exception: return x
        want = [c for c in allc if term.lower() in c[0].lower() and (stf == "все" or c[2] == stf)]
        got, gotcat = [], []
        for k in range(1, 251):
            b = v2(f"B{7 + k}")
            if b in (None, ""): break
            got.append(b); gotcat.append(v2(f"C{7 + k}"))
        cnt = int(v2("C5") or 0)
        good = got == [w[0] for w in want][:len(got)] and cnt == len(want)
        chk(good, f"ПОИСК {term}/{stf}")
        print(f"{'OK  ' if good else 'FAIL'} поиск {term!r:8} статус={stf:14} найдено={cnt:5} "
              f"(эталон {len(want):5}) показано={len(got):3}"
              + (f"  1-й: {str(got[0])[:32]!r} → {gotcat[0]}" if got else ""), flush=True)
        if not good:
            print("   эталон:", [w[0][:26] for w in want[:3]], "\n   получено:", [g[:26] for g in got[:3]])

print("\n— СТРУКТУРА —")
for name in cats:
    d = info[name]; ws = wb[name]
    dv = any(f"{gc(d['sc'])}3" in str(v.sqref) for v in ws.data_validations.dataValidation)
    cf = sum(len(v) for v in ws.conditional_formatting._cf_rules.values())
    arr = sum(1 for row in ws.iter_rows() for c in row
              if c.data_type == "f" and getattr(c.value, "text", "").startswith("="))
    chk(dv and cf == 2, f"{name}: dv/cf")
    print(f"{'OK  ' if dv and cf == 2 else 'FAIL'} {name:20} список статусов={dv}  подсветок={cf}  "
          f"строк={ws.max_row:4}  массивных формул в свалке={arr}")
print("\n" + ("✅ ВСЁ РАБОТАЕТ" if ok else "❌ ПРОБЛЕМЫ:\n  " + "\n  ".join(fails)))
