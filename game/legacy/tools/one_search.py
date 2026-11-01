"""Один прогон поиска в отдельном процессе (чтобы не копились графы в памяти).
   python3 test/one_search.py <файл> <слово> <статус>"""
import warnings, sys
warnings.filterwarnings("ignore")
from openpyxl import load_workbook
path, term, stf = sys.argv[1], sys.argv[2], sys.argv[3]
wb = load_workbook(path)
SERVICE=("СВОДКА","ПОИСК","_ДАННЫЕ")
cats=[s for s in wb.sheetnames if s not in SERVICE]
allc=[]
for name in cats:
    ws=wb[name]
    split = ws.cell(row=2,column=3).value != "Статус"
    sc = 4 if split else 3
    dtitle = next(r for r in range(3, ws.max_row+2)
                  if isinstance(ws.cell(row=r,column=1).value,str) and ws.cell(row=r,column=1).value.startswith("⬇"))
    n = dtitle-6
    for i in range(1,n+1):
        r=2+i
        a=ws.cell(row=r,column=2).value or ""
        b=ws.cell(row=r,column=3).value if split else None
        sep=" - " if name=="1 ПРОФЕССИЯ" else " — "
        allc.append((f"{a}{sep}{b}" if (split and b) else a, name, ws.cell(row=r,column=sc).value))
wb["ПОИСК"]["C3"]=term; wb["ПОИСК"]["C4"]=stf
tmp=path.replace(".xlsx",f"_s.xlsx"); wb.save(tmp)
import formulas
sol=formulas.ExcelModel().loads(tmp).finish().calculate()
f2=tmp.split("/")[-1]
def v2(cell):
    x=sol.get(f"'[{f2}]ПОИСК'!{cell}"); x=getattr(x,"value",x)
    try: return x[0][0]
    except Exception: return x
want=[c for c in allc if term.lower() in c[0].lower() and (stf=="все" or c[2]==stf)]
got=[];gotcat=[];gotst=[]
for k in range(1,251):
    b=v2(f"B{7+k}")
    if b in (None,""): break
    got.append(b); gotcat.append(v2(f"C{7+k}")); gotst.append(v2(f"D{7+k}"))
cnt=v2("C5")
good = got==[w[0] for w in want][:len(got)] and int(cnt or 0)==len(want)
print(f"{'OK  ' if good else 'FAIL'} поиск {term!r:9} статус={stf:14} найдено={cnt} (эталон {len(want)}) "
      f"показано={len(got)}" + (f"  1-й: {str(got[0])[:36]!r} → {gotcat[0]} [{gotst[0]}]" if got else ""))
if not good:
    print("   эталон:",[w[0][:30] for w in want[:3]]); print("   получено:",[g[:30] for g in got[:3]])
