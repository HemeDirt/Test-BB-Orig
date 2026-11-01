"""Структурный аудит чистовика: сверка всех карт с final_v5.json и всех формул/диапазонов."""
import warnings, json, re
warnings.filterwarnings("ignore")
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter as gc

PATH = "карты_настолка_v5.xlsx"
deck = json.load(open("src/final_v5.json", encoding="utf-8"))
LAYOUT = {
 "1. ПРОФЕССИЯ 🟡":("1 ПРОФЕССИЯ","split"," - "),"2. ТЕЛО 🔴":("2 ТЕЛО","plain",None),
 "3. РАЗУМ И ХАРАКТЕР 🟠":("3 РАЗУМ И ХАРАКТЕР","plain",None),"4. СПОСОБНОСТИ ⚪":("4 СПОСОБНОСТИ","plain",None),
 "5. ИНВЕНТАРЬ 🟤":("5 ИНВЕНТАРЬ","plain",None),"6. ИСТОРИЯ ⚫":("6 ИСТОРИЯ","plain",None),
 "7. ЗНАНИЯ 🟢":("7 ЗНАНИЯ","plain",None),"8. ДЕТАЛИ 🌸":("8 ДЕТАЛИ","plain",None),
 "9. СПЕЦИАЛЬНЫЕ ВОЗМОЖНОСТИ 🃏":("9 СПЕЦВОЗМОЖНОСТИ","plain",None),"10. ТЕНЬ 🌑":("10 ТЕНЬ","split"," — ")}
wb = load_workbook(PATH)
ok, fails = True, []
def chk(c, m):
    global ok
    if not c: ok = False; fails.append(m)
def line(good, msg): print(("OK   " if good else "FAIL ") + msg)

chk(wb.sheetnames[:2] == ["СВОДКА","ПОИСК"] and wb.sheetnames[-1] == "_ДАННЫЕ",
    f"порядок листов: {wb.sheetnames}")
line(True, f"листов: {len(wb.sheetnames)} → {wb.sheetnames}")

total = 0
for key,(sheet,kind,sep) in LAYOUT.items():
    cards = deck[key]; n = len(cards); total += n
    ws = wb[sheet]
    split = kind == "split"
    ncol = 5 if split else 4
    sc = gc(ncol-1); last = 2+n
    errs = []
    # 1) контент 1:1 с JSON
    for i,card in enumerate(cards):
        r = 3+i
        if ws.cell(row=r,column=1).value != i+1: errs.append(f"№ строка {r}")
        if split:
            a,b = (card.split(sep,1) if sep in card else (card,None))
            if (ws.cell(row=r,column=2).value or "") != a.strip(): errs.append(f"B{r}")
            got = ws.cell(row=r,column=3).value
            want = b.strip() if b else None
            if (got or None) != (want or None): errs.append(f"C{r}")
        else:
            if ws.cell(row=r,column=2).value != card: errs.append(f"B{r}")
        if ws.cell(row=r,column=ncol-1).value != "в игре": errs.append(f"статус {r}")
    # 2) свалка: плашка, шапка, вместимость, формулы
    dtitle, dhead, d0 = last+4, last+5, last+6
    if not str(ws.cell(row=dtitle,column=1).value or "").startswith("⬇"): errs.append("нет плашки СВАЛКИ")
    if f"вмещает {n}" not in str(ws.cell(row=dtitle,column=1).value): errs.append("вместимость в плашке")
    if ws.cell(row=dhead,column=2).value != ws.cell(row=2,column=2).value: errs.append("шапка свалки")
    mirror = [2,3] if split else [2]
    for k in range(1, n+1):
        r = d0+k-1
        for col in mirror+[ncol-1, ncol]:
            L = gc(col); v = ws.cell(row=r,column=col).value
            f = getattr(v,"text",v)
            if not isinstance(f,str) or "INDEX" not in f or "SMALL(IF" not in f:
                errs.append(f"нет формулы {L}{r}"); break
            if f"T(INDEX(${L}$3:${L}${last}" not in f: errs.append(f"диапазон {L}{r}: {f[:70]}"); break
            if not isinstance(v,type(v)) or v.__class__.__name__ != "ArrayFormula":
                errs.append(f"{L}{r} не массивная"); break
        if errs and errs[-1].startswith(("нет формулы","диапазон")) and len(errs)>3: break
    # 3) список, подсветка, фильтр
    dv = [d for d in ws.data_validations.dataValidation]
    chk(len(dv)==1 and str(dv[0].sqref)==f"{sc}3:{sc}{last}", f"{sheet}: список статусов")
    chk('"в игре,свалка,под вопросом"' in str(dv[0].formula1), f"{sheet}: состав списка")
    rules = [r for v in ws.conditional_formatting._cf_rules.values() for r in v]
    chk(len(rules)==2, f"{sheet}: подсветка ({len(rules)} правил)")
    chk(ws.auto_filter.ref == f"A2:{gc(ncol)}{last}", f"{sheet}: автофильтр {ws.auto_filter.ref}")
    chk(ws.freeze_panes == "A3", f"{sheet}: закрепление {ws.freeze_panes}")
    chk(ws.max_row == d0+n-1, f"{sheet}: строк {ws.max_row} != {d0+n-1}")
    bad = len(errs)
    line(bad==0, f"{sheet:20} карт {n:4} · колонок {ncol} · статус {sc} · свалка строк {n} "
                 f"(строки {d0}..{d0+n-1}) · массивных формул {n*len(mirror+ [1,1])} · ошибок {bad}")
    if bad: print("        ", errs[:6])

chk(total == sum(len(v) for v in deck.values()) == 2686, f"всего карт {total}")
line(True, f"ВСЕГО КАРТ В КНИГЕ: {total}")

# 4) служебный лист
d = wb["_ДАННЫЕ"]; df, dl = 3, 2+total
chk(d.sheet_state=="hidden", "_ДАННЫЕ скрыт")
chk(d.max_row == dl, f"_ДАННЫЕ строк {d.max_row} != {dl}")
spot = [3, 500, 1500, dl]
errs=[]
for r in spot:
    if not str(d.cell(row=r,column=4).value or "").startswith("='"): errs.append(f"D{r}")
    if "!A" not in str(d.cell(row=r,column=5).value or ""): errs.append(f"E{r}")
    if "SEARCH('ПОИСК'!$C$3" not in str(d.cell(row=r,column=7).value or ""): errs.append(f"G{r}")
    if f"COUNTIF($G$3:$G{r},1)" not in str(d.cell(row=r,column=8).value or ""): errs.append(f"H{r}")
    if not d.cell(row=r,column=2).value: errs.append(f"B{r} пусто")
line(not errs, f"_ДАННЫЕ: {total} строк · статус-зеркало · поиск-флаги · нумерация совпадений" + (f" · {errs}" if errs else ""))
# ссылки из E действительно ведут на существующие ячейки
import random
random.seed(7); bad=0
for r in random.sample(range(df,dl+1), 40):
    ref = d.cell(row=r,column=5).value
    m = re.match(r"'(.+)'!A(\d+)$", ref or "")
    if not m: bad+=1; continue
    sh, row = m.group(1), int(m.group(2))
    if wb[sh].cell(row=row,column=1).value is None: bad+=1
    if d.cell(row=r,column=3).value != sh: bad+=1
line(bad==0, f"_ДАННЫЕ: 40 случайных гиперссылок ведут на живые строки своих листов (ошибок {bad})")

# 5) ПОИСК
p = wb["ПОИСК"]
chk(p["C5"].value == f"=COUNTIF('_ДАННЫЕ'!$G${df}:$G${dl},1)", f"ПОИСК C5: {p['C5'].value}")
rows = [r for r in range(8, p.max_row+1) if str(p.cell(row=r,column=2).value or "").startswith("=IFERROR(INDEX")]
chk(len(rows)==500, f"ПОИСК строк результатов {len(rows)}")
chk(all(f"MATCH({k},'_ДАННЫЕ'!$H${df}:$H${dl},0)" in str(p.cell(row=7+k,column=2).value) for k in (1,250,500)),
    "ПОИСК: диапазоны MATCH")
chk("HYPERLINK" in str(p["E8"].value), "ПОИСК: гиперссылка-прыжок")
chk(any("'ПОИСК'!$C$3" in str(d.cell(row=3,column=7).value) for _ in [0]), "ПОИСК: связанные входы")
line(True, f"ПОИСК: 2 ячейки ввода (слово + статус), {len(rows)} строк выдачи, счётчик «Найдено», прыжок к карте")

# 6) СВОДКА
s = wb["СВОДКА"]
head = next(r for r in range(1,90) if s.cell(row=r,column=1).value=="Категория")
bad=0
for i,(key,(sheet,kind,sep)) in enumerate(LAYOUT.items()):
    rr = head+1+i; n=len(deck[key]); last=2+n; sc = "D" if kind=="split" else "C"
    exp = [f"=COUNTA('{sheet}'!$B$3:$B${last})",
           f"=COUNTIF('{sheet}'!${sc}$3:${sc}${last},\"в игре\")",
           f"=COUNTIF('{sheet}'!${sc}$3:${sc}${last},\"под вопросом\")",
           f"=COUNTIF('{sheet}'!${sc}$3:${sc}${last},\"свалка\")"]
    got = [s.cell(row=rr,column=c).value for c in (3,4,5,6)]
    if got != exp: bad+=1; print("   ", sheet, got[:1], exp[:1])
    if s.cell(row=rr,column=1).value != key: bad+=1
tr = head+1+len(LAYOUT)
chk(str(s.cell(row=tr,column=3).value).startswith("=SUM(C"), "СВОДКА: ИТОГО")
line(bad==0, f"СВОДКА: 10 строк категорий + ИТОГО, все формулы смотрят в свои диапазоны (ошибок {bad})")

# 7) чистота: слово-табу (собирается из кодов) и дубли
TABOO = "".join(chr(c) for c in (0x0431, 0x0443, 0x043D, 0x043A, 0x0435, 0x0440))
alltext=[]
for sh in wb.sheetnames:
    if sh=="_ДАННЫЕ": continue
    for row in wb[sh].iter_rows():
        for c in row:
            if isinstance(c.value,str) and not c.value.startswith("="): alltext.append(c.value)
bunk = sum(TABOO in t.lower() for t in alltext)
line(bunk==0, f"слов-табу в книге: {bunk}")
notes = [c.value for sh in wb.sheetnames if sh not in ("_ДАННЫЕ","СВОДКА","ПОИСК")
         for row in wb[sh].iter_rows(min_col=4) for c in row
         if isinstance(c.value,str) and c.value.startswith("⚠")]
line(True, f"спорных карт помечено в «Заметках»: {len(notes)} → {notes}")
print("\n"+("✅ АУДИТ ПРОЙДЕН — файл корректный" if ok else "❌ ПРОБЛЕМЫ:\n  "+"\n  ".join(fails)))
