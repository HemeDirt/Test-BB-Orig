"""Экспорт чистой колоды редакции 5 в Excel: «карты_настолка_v5.xlsx».

Механика отделения карт от основного списка (без макросов — обычный .xlsx):
  1. колонка «Статус» с выпадающим списком: в игре / свалка / под вопросом;
  2. «свалка» — строка гаснет (серый + зачёркнутый) и АВТОМАТИЧЕСКИ появляется
     во второй таблице «СВАЛКА» ВНИЗУ ТОГО ЖЕ ЛИСТА (формулы, ничего не переносится);
  3. «под вопросом» — жёлтая подсветка;
  4. автофильтр по статусу — спрятать свалку в один клик;
  5. лист «ПОИСК» — живой поиск по всем 2686 картам сразу, с фильтром по статусу
     и гиперссылкой-прыжком к карте;
  6. лист «СВОДКА» — живые счётчики по каждой категории.

Запуск:
    python3 src/export_v5_xlsx.py                    # полная колода
    python3 src/export_v5_xlsx.py --limit 12 --out test/mini_v5.xlsx
"""
from __future__ import annotations

import json
import os
import sys

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.formula import ArrayFormula

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "final_v5.json")
DATA_SHEET = "_ДАННЫЕ"
PS = "'ПОИСК'"          # имя листа ПОИСК в формулах (в кавычках)

STATUSES = ["в игре", "свалка", "под вопросом"]
DV_STATUSES = '"' + ",".join(STATUSES) + '"'
DV_SEARCH = '"' + ",".join(["все"] + STATUSES) + '"'
SEARCH_ROWS = 500          # вместимость листа ПОИСК (строк результатов)

# категория -> (имя листа, тип, подпись колонки A, подпись колонки B, разделитель)
LAYOUT = {
    "1. ПРОФЕССИЯ 🟡":               ("1 ПРОФЕССИЯ",        "split2", "Профессия",   "Способность", " - "),
    "2. ТЕЛО 🔴":                    ("2 ТЕЛО",             "plain",  "Карта",       None,          None),
    "3. РАЗУМ И ХАРАКТЕР 🟠":        ("3 РАЗУМ И ХАРАКТЕР", "plain",  "Карта",       None,          None),
    "4. СПОСОБНОСТИ ⚪":              ("4 СПОСОБНОСТИ",      "plain",  "Карта",       None,          None),
    "5. ИНВЕНТАРЬ 🟤":               ("5 ИНВЕНТАРЬ",        "plain",  "Карта",       None,          None),
    "6. ИСТОРИЯ ⚫":                  ("6 ИСТОРИЯ",          "plain",  "Карта",       None,          None),
    "7. ЗНАНИЯ 🟢":                  ("7 ЗНАНИЯ",           "plain",  "Карта",       None,          None),
    "8. ДЕТАЛИ 🌸":                  ("8 ДЕТАЛИ",           "plain",  "Карта",       None,          None),
    "9. СПЕЦИАЛЬНЫЕ ВОЗМОЖНОСТИ 🃏":  ("9 СПЕЦВОЗМОЖНОСТИ",  "plain",  "Карта",       None,          None),
    "10. ТЕНЬ 🌑":                   ("10 ТЕНЬ",            "split2", "Тень",        "Механика",    " — "),
}

# пометки для спорных карт (найдены проверкой; сами ничего не правим)
PRESET_NOTES = {}   # в редакции 5 спорные дубли устранены — пометок нет

# ── стили ────────────────────────────────────────────────────────────────────
C_ACCENT = "C00000"
F_TITLE = Font(bold=True, size=14, color="FFFFFF")
F_HEAD = Font(bold=True, size=11, color="FFFFFF")
F_BODY = Font(size=11)
F_DUMP = Font(size=11, italic=True, color="7F7F7F")
F_GREY = Font(size=10, color="808080", italic=True)
FILL_TITLE = PatternFill("solid", fgColor="1F1F1F")
FILL_HEAD = PatternFill("solid", fgColor="404040")
FILL_DUMP_HEAD = PatternFill("solid", fgColor="7F7F7F")
FILL_DUMP_SUB = PatternFill("solid", fgColor="D9D9D9")
FILL_STRIPE = PatternFill("solid", fgColor="F7F7F7")
FILL_INPUT = PatternFill("solid", fgColor="FFF2CC")
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="top")
CTR = Alignment(horizontal="center", vertical="center", wrap_text=True)
THIN = Side(style="thin", color="D0D0D0")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
MED = Side(style="medium", color="BF8F00")
BOX_INPUT = Border(left=MED, right=MED, top=MED, bottom=MED)


def split_card(text: str, sep: str | None):
    if sep and sep in text:
        a, b = text.split(sep, 1)
        return a.strip(), (b.strip() or None)
    return text.strip(), None


def title_bar(ws, text, ncol, row=1, height=26):
    last = get_column_letter(ncol)
    ws.merge_cells(f"A{row}:{last}{row}")
    c = ws.cell(row=row, column=1, value=text)
    c.font, c.fill = F_TITLE, FILL_TITLE
    c.alignment = Alignment(vertical="center", horizontal="left", indent=1)
    ws.row_dimensions[row].height = height


def build(limit: int | None = None, out: str | None = None, only: str | None = None):
    deck = json.load(open(SRC, encoding="utf-8"))
    wb = Workbook()

    summary = wb.active
    summary.title = "СВОДКА"
    search = wb.create_sheet("ПОИСК")

    stats = []        # для СВОДКИ
    index_rows = []   # для служебного листа: (карта, лист, формула статуса, ссылка, № в листе)

    # ───────────────────────── ЛИСТЫ КАТЕГОРИЙ ─────────────────────────
    for key, (sheet_name, kind, col_a, col_b, sep) in LAYOUT.items():
        if only and only not in sheet_name:
            continue
        cards = deck[key]
        if limit:
            cards = cards[:limit]
        n = len(cards)
        split = kind == "split2"
        ws = wb.create_sheet(sheet_name)

        headers = (["№", col_a, col_b, "Статус", "Заметка / причина"] if split
                   else ["№", col_a, "Статус", "Заметка / причина"])
        ncol = len(headers)
        last_col = get_column_letter(ncol)
        status_col = get_column_letter(ncol - 1)
        note_col = get_column_letter(ncol)
        first, last = 3, 2 + n

        cat_short = key.split(" ", 1)[1]
        title_bar(ws, f"{cat_short}   ·   {n} карт   ·   статус меняется в колонке «{status_col}», "
                      f"свалка собирается внизу листа", ncol)
        for c, h in enumerate(headers, start=1):
            cell = ws.cell(row=2, column=c, value=h)
            cell.font, cell.fill, cell.border, cell.alignment = F_HEAD, FILL_HEAD, BORDER, CTR
        ws.row_dimensions[2].height = 22

        notes = PRESET_NOTES.get(sheet_name, {})
        for i, card in enumerate(cards):
            r = first + i
            ws.cell(row=r, column=1, value=i + 1).alignment = CENTER
            if split:
                a, b = split_card(card, sep)
                ws.cell(row=r, column=2, value=a).alignment = WRAP
                if b:
                    ws.cell(row=r, column=3, value=b).alignment = WRAP
            else:
                ws.cell(row=r, column=2, value=card).alignment = WRAP
            ws.cell(row=r, column=ncol - 1, value="в игре").alignment = CENTER
            ws.cell(row=r, column=ncol, value=notes.get(card.strip(), "")).alignment = WRAP
            for c in range(1, ncol + 1):
                cell = ws.cell(row=r, column=c)
                cell.font, cell.border = F_BODY, BORDER
                if i % 2 == 1 and c != ncol - 1:
                    cell.fill = FILL_STRIPE
            index_rows.append((card, sheet_name, status_col, r, i + 1))

        # выпадающий список статусов
        dv = DataValidation(type="list", formula1=DV_STATUSES, allow_blank=False,
                            showDropDown=False, showErrorMessage=True,
                            errorStyle="warning", errorTitle="Статус карты",
                            error="Лучше выбрать из списка: в игре / свалка / под вопросом.\n"
                                  "Иначе карта не попадёт в автосвалку и в счётчики.",
                            promptTitle="Статус карты",
                            prompt="в игре — карта в колоде\n"
                                   "свалка — погаснет и уедет в таблицу «СВАЛКА» внизу этого листа\n"
                                   "под вопросом — жёлтая подсветка, надо подумать",
                            showInputMessage=True)
        ws.add_data_validation(dv)
        dv.add(f"{status_col}{first}:{status_col}{last}")

        ws.auto_filter.ref = f"A2:{last_col}{last}"
        ws.freeze_panes = f"A{first}"

        rng = f"A{first}:{last_col}{last}"
        ws.conditional_formatting.add(rng, FormulaRule(
            formula=[f'${status_col}{first}="свалка"'],
            font=Font(color="A6A6A6", strike=True), fill=PatternFill("solid", bgColor="F2F2F2")))
        ws.conditional_formatting.add(rng, FormulaRule(
            formula=[f'${status_col}{first}="под вопросом"'],
            font=Font(color="7F6000"), fill=PatternFill("solid", bgColor="FFF2CC")))

        widths = [5, 30, 74, 15, 34] if split else [5, 100, 15, 34]
        for c, w in enumerate(widths[:ncol], start=1):
            ws.column_dimensions[get_column_letter(c)].width = w

        # ── СВАЛКА: вторая таблица внизу того же листа, на формулах ──
        dtitle = last + 4
        dhead = dtitle + 1
        d0 = dhead + 1

        ws.merge_cells(f"A{dtitle}:{last_col}{dtitle}")
        dt = ws.cell(row=dtitle, column=1)
        dt.value = (f"⬇  СВАЛКА  ·  сюда сами попадают карты со статусом «свалка»  ·  "
                    f"вмещает {n} шт.  ·  ничего не удаляется")
        dt.font, dt.fill = Font(bold=True, size=12, color="FFFFFF"), FILL_DUMP_HEAD
        dt.alignment = Alignment(vertical="center", horizontal="left", indent=1)
        ws.row_dimensions[dtitle].height = 24

        for c, h in enumerate(headers, start=1):
            cell = ws.cell(row=dhead, column=c, value=h)
            cell.font = Font(bold=True, size=11, color="404040")
            cell.fill, cell.border, cell.alignment = FILL_DUMP_SUB, BORDER, CTR

        mirror = [2, 3] if split else [2]
        small = (f'SMALL(IF(${status_col}${first}:${status_col}${last}="свалка",'
                 f'ROW(${status_col}${first}:${status_col}${last})-{first - 1}),')
        for k in range(1, n + 1):
            r = d0 + k - 1
            ws.cell(row=r, column=1, value=f'=IF($B{r}="","",{k})').alignment = CENTER
            for col in mirror + [ncol - 1, ncol]:
                L = get_column_letter(col)
                f = f'=IFERROR(T(INDEX(${L}${first}:${L}${last},{small}{k}))),"")'
                ws.cell(row=r, column=col, value=ArrayFormula(f"{L}{r}", f))
                ws.cell(row=r, column=col).alignment = CTR if col == ncol - 1 else WRAP
            for c in range(1, ncol + 1):
                ws.cell(row=r, column=c).font = F_DUMP

        stats.append((sheet_name, key, n, status_col, last))

    # ───────────────────────── СЛУЖЕБНЫЙ ЛИСТ (зеркало) ─────────────────────────
    ws = wb.create_sheet(DATA_SHEET)
    ws.sheet_state = "hidden"
    dh = ["№", "Карта", "Категория (лист)", "Статус", "Ссылка", "№ в листе", "Совпал?", "Порядок"]
    for c, h in enumerate(dh, start=1):
        cell = ws.cell(row=2, column=c, value=h)
        cell.font, cell.fill, cell.alignment = F_HEAD, FILL_HEAD, CTR
    title_bar(ws, "СЛУЖЕБНЫЙ ЛИСТ — зеркало колоды для листа «ПОИСК». Здесь ничего не правим: "
                  "статусы подтягиваются из листов категорий сами.", len(dh))
    d_first = 3
    d_last = d_first + len(index_rows) - 1
    for i, (card, sheet_name, status_col, row, local) in enumerate(index_rows):
        r = d_first + i
        ws.cell(row=r, column=1, value=i + 1)
        ws.cell(row=r, column=2, value=card)
        ws.cell(row=r, column=3, value=sheet_name)
        ws.cell(row=r, column=4, value=f"='{sheet_name}'!{status_col}{row}")
        ws.cell(row=r, column=5, value=f"'{sheet_name}'!A{row}")
        ws.cell(row=r, column=6, value=local)
        ws.cell(row=r, column=7, value=(
            f'=IF(AND(ISNUMBER(SEARCH({PS}!$C$3,$B{r})),'
            f'OR({PS}!$C$4="все",$D{r}={PS}!$C$4)),1,0)'))
        ws.cell(row=r, column=8, value=f'=IF($G{r}=1,COUNTIF($G${d_first}:$G{r},1),"")')
    for c, w in enumerate([6, 90, 20, 14, 22, 9, 8, 8], start=1):
        ws.column_dimensions[get_column_letter(c)].width = w

    # ───────────────────────── ЛИСТ «ПОИСК» ─────────────────────────
    ws = search
    title_bar(ws, "ПОИСК ПО ВСЕЙ КОЛОДЕ  ·  ищет сразу по всем 10 категориям  ·  статус подтягивается живой", 5)
    ws["A3"] = "🔎 Искать (часть слова):"
    ws["A4"] = "Статус:"
    ws["A5"] = "Найдено:"
    for rr in (3, 4, 5):
        ws.merge_cells(f"A{rr}:B{rr}")
        ws.cell(row=rr, column=1).font = Font(bold=True, size=11)
        ws.cell(row=rr, column=1).alignment = Alignment(horizontal="right", vertical="center")
        inp = ws.cell(row=rr, column=3, value=("профессия" if rr == 3 else "все"))
        inp.fill, inp.border = FILL_INPUT, BOX_INPUT
        inp.font = Font(bold=True, size=11, color="7F6000")
        inp.alignment = Alignment(horizontal="center", vertical="center")
    dv_s = DataValidation(type="list", formula1=DV_SEARCH, allow_blank=False, showDropDown=False)
    ws.add_data_validation(dv_s)
    dv_s.add("C4")
    ws["D3"] = "← впиши любое слово или кусок слова (регистр не важен; «*» и «?» работают как маски)"
    ws["D4"] = "← можно искать, например, только среди отправленных в свалку"
    ws["D3"].font = ws["D4"].font = F_GREY
    ws["C5"] = f"=COUNTIF('{DATA_SHEET}'!$G${d_first}:$G${d_last},1)"
    ws["C5"].font = Font(bold=True, size=12, color=C_ACCENT)
    ws["C5"].alignment = Alignment(horizontal="center", vertical="center")
    ws["D5"] = f"← показаны первые {SEARCH_ROWS} совпадений"
    ws["D5"].font = F_GREY

    ph = ["№", "Карта", "Категория", "Статус", "Перейти"]
    for c, h in enumerate(ph, start=1):
        cell = ws.cell(row=7, column=c, value=h)
        cell.font, cell.fill, cell.border, cell.alignment = F_HEAD, FILL_HEAD, BORDER, CTR
    ws.freeze_panes = "A8"

    q = f"'{DATA_SHEET}'"
    for k in range(1, SEARCH_ROWS + 1):
        r = 7 + k
        m = f"MATCH({k},{q}!$H${d_first}:$H${d_last},0)"
        ws.cell(row=r, column=1, value=f'=IF($B{r}="","",{k})').alignment = CENTER
        for col, src in ((2, "B"), (3, "C"), (4, "D")):
            cell = ws.cell(row=r, column=col,
                           value=f'=IFERROR(INDEX({q}!${src}${d_first}:${src}${d_last},{m}),"")')
            cell.alignment = WRAP if col == 2 else CENTER
            cell.font = F_BODY
        ws.cell(row=r, column=5,
                value=(f'=IF($B{r}="","",HYPERLINK("#"&INDEX({q}!$E${d_first}:$E${d_last},{m}),"→ к карте"))'))
        ws.cell(row=r, column=5).alignment = CENTER
        ws.cell(row=r, column=5).font = Font(size=11, color="0563C1", underline="single")
        for c in range(1, 6):
            ws.cell(row=r, column=c).border = BORDER
    ws.conditional_formatting.add(f"A8:E{7 + SEARCH_ROWS}", FormulaRule(
        formula=['$D8="свалка"'], font=Font(color="A6A6A6", strike=True)))
    for c, w in enumerate([6, 96, 22, 15, 12], start=1):
        ws.column_dimensions[get_column_letter(c)].width = w

    # ───────────────────────── СВОДКА ─────────────────────────
    ws = summary
    ws.sheet_view.showGridLines = False
    title_bar(ws, "БЛИЦ БОЙ  ·  колода ред. 5 (чистая)  ·  пульт управления", 7, height=30)
    howto = [
        "",
        "КАК ОТДЕЛИТЬ НЕНУЖНЫЕ КАРТЫ (всё в один клик, макросов нет — файл обычный .xlsx):",
        "1. Открой лист категории. В колонке «Статус» у каждой карты — выпадающий список.",
        "2. Кликни ячейку статуса → выбери «свалка». Карта тут же погаснет (серый + зачёркнутый) и",
        "   АВТОМАТИЧЕСКИ появится в таблице «СВАЛКА» в самом низу ЭТОГО ЖЕ листа. Ничего не удаляется.",
        "3. Вернуть в игру — тем же списком выбери «в игре»: карта уйдёт из свалки обратно в список.",
        "4. «под вопросом» — жёлтая подсветка, для карт, над которыми надо подумать.",
        "5. Кнопка автофильтра в шапке → по колонке «Статус» оставь только «в игре»: свалка не мозолит",
        "   глаза, хотя физически лежит в том же листе. Фильтр снимается той же кнопкой.",
        "6. В «Заметка / причина» пиши, за что карта выкинута — заметка уедет в свалку вместе с ней.",
        "7. Лист «ПОИСК» ищет сразу по всей колоде (по слову + по статусу) и прыгает к карте ссылкой.",
        "",
        "ВАЖНО: не вставляй и не удаляй строки внутри таблицы «СВАЛКА» — там формулы. Если свалка",
        "переполнится (статус «свалка» получит больше карт, чем строк в таблице), допиши внизу ещё",
        "строку и протяни формулу из предыдущей — Excel сам её подхватит.",
    ]
    r = 2
    for line in howto:
        cell = ws.cell(row=r, column=1, value=line)
        cell.font = (Font(bold=True, size=11, color=C_ACCENT)
                     if line.startswith(("КАК", "ВАЖНО")) else Font(size=11, color="404040"))
        r += 1
    r += 1
    head = r
    for c, h in enumerate(["Категория", "Лист", "Всего карт", "в игре", "под вопросом", "свалка", "свалка %"], 1):
        cell = ws.cell(row=head, column=c, value=h)
        cell.font, cell.fill, cell.border, cell.alignment = F_HEAD, FILL_HEAD, BORDER, CTR
    ws.row_dimensions[head].height = 22

    f0 = head + 1
    for i, (sheet_name, key, n, status_col, last) in enumerate(stats):
        rr = f0 + i
        q = f"'{sheet_name}'"
        ws.cell(row=rr, column=1, value=key).font = Font(bold=True, size=11)
        ws.cell(row=rr, column=2, value=sheet_name).font = F_BODY
        ws.cell(row=rr, column=3, value=f"=COUNTA({q}!$B$3:$B${last})")
        ws.cell(row=rr, column=4, value=f'=COUNTIF({q}!${status_col}$3:${status_col}${last},"в игре")')
        ws.cell(row=rr, column=5, value=f'=COUNTIF({q}!${status_col}$3:${status_col}${last},"под вопросом")')
        ws.cell(row=rr, column=6, value=f'=COUNTIF({q}!${status_col}$3:${status_col}${last},"свалка")')
        pc = ws.cell(row=rr, column=7, value=f"=IFERROR(F{rr}/C{rr},0)")
        pc.number_format = "0.0%"
        for c in range(1, 8):
            cell = ws.cell(row=rr, column=c)
            cell.border = BORDER
            if c >= 3:
                cell.alignment = Alignment(horizontal="center")
                cell.font = Font(size=11, bold=(c == 6))
            if i % 2 == 1:
                cell.fill = FILL_STRIPE
    tot = f0 + len(stats)
    ws.cell(row=tot, column=1, value="ИТОГО")
    for c, col in ((3, "C"), (4, "D"), (5, "E"), (6, "F")):
        cell = ws.cell(row=tot, column=c, value=f"=SUM({col}{f0}:{col}{tot - 1})")
        cell.alignment = Alignment(horizontal="center")
    pc = ws.cell(row=tot, column=7, value=f"=IFERROR(F{tot}/C{tot},0)")
    pc.number_format, pc.alignment = "0.0%", Alignment(horizontal="center")
    for c in range(1, 8):
        cell = ws.cell(row=tot, column=c)
        cell.font = Font(bold=True, size=12, color="FFFFFF")
        cell.fill, cell.border = FILL_TITLE, BORDER
    ws.cell(row=tot + 2, column=1,
            value="Счётчики живые: пометил карту «свалка» — цифры пересчитались сами. "
                  "Служебный лист «_ДАННЫЕ» скрыт и работает на «ПОИСК».").font = F_GREY
    for c, w in enumerate([34, 22, 12, 10, 14, 10, 11], 1):
        ws.column_dimensions[get_column_letter(c)].width = w

    wb.active = 0
    path = out or os.path.join(ROOT, "карты_настолка_v5.xlsx")
    wb.properties.title = "Блиц Бой — колода ред. 5 (чистая)"
    wb.properties.creator = "Блиц Бой"
    wb.save(path)
    return path, stats, len(index_rows)


if __name__ == "__main__":
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    p, st, total = build(limit=lim, out=out, only=only)
    print(f"сохранено: {p}")
    print(f"категорий: {len(st)}   карт: {total}   размер: {os.path.getsize(p)/1024:.0f} КБ")
    for s, k, n, sc, last in st:
        print(f"   {s:20} {n:4} карт   статус в колонке {sc}   строки 3..{last}")
