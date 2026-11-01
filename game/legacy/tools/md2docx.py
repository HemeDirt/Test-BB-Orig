# -*- coding: utf-8 -*-
"""Простой конвертер markdown-подмножества -> docx (python-docx).
Usage: python3 src/md2docx.py input.md output.docx [--title "Заголовок"]
Поддержка: #/##/###/####, таблицы |...|, списки -/1., цитаты >, **bold**, *italic*, `code`, ---.
"""
import re, sys
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

def add_runs(p, text):
    # разбивка на **bold**, *italic*, `code`
    parts = re.split(r'(\*\*.+?\*\*|\*[^*]+?\*|`[^`]+?`)', text)
    for part in parts:
        if not part: continue
        if part.startswith('**') and part.endswith('**'):
            r = p.add_run(part[2:-2]); r.bold = True
        elif part.startswith('*') and part.endswith('*') and len(part) > 2:
            r = p.add_run(part[1:-1]); r.italic = True
        elif part.startswith('`') and part.endswith('`'):
            r = p.add_run(part[1:-1]); r.font.name = 'Consolas'; r.font.size = Pt(9.5)
        else:
            p.add_run(part)

def flush_table(doc, rows):
    if not rows: return
    ncols = max(len(r) for r in rows)
    t = doc.add_table(rows=len(rows), cols=ncols)
    t.style = 'Table Grid'
    for i, row in enumerate(rows):
        for j in range(ncols):
            cell = t.cell(i, j)
            txt = row[j] if j < len(row) else ''
            cell.paragraphs[0].text = ''
            add_runs(cell.paragraphs[0], txt)
            for r in cell.paragraphs[0].runs:
                r.font.size = Pt(9.5)
                if i == 0: r.bold = True
    doc.add_paragraph()

def convert(md_path, docx_path, title=None):
    lines = open(md_path, encoding='utf-8').read().split('\n')
    doc = Document()
    # A4
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2)
    st = doc.styles['Normal']
    st.font.name = 'Calibri'; st.font.size = Pt(11)

    table_rows = []
    quote_buf = []
    def flush_quote():
        nonlocal quote_buf
        if quote_buf:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.75)
            add_runs(p, '\n'.join(quote_buf))
            for r in p.runs: r.italic = True
            quote_buf = []
    for raw in lines:
        line = raw.rstrip()
        # таблица
        if line.startswith('|'):
            flush_quote()
            cells = [c.strip() for c in line.strip('|').split('|')]
            if all(re.fullmatch(r':?-{2,}:?', c or '--') for c in cells):
                continue
            table_rows.append(cells)
            continue
        else:
            if table_rows:
                flush_table(doc, table_rows); table_rows = []
        if line.startswith('> ') or line == '>':
            quote_buf.append(line[2:] if line.startswith('> ') else '')
            continue
        else:
            flush_quote()
        if not line.strip():
            continue
        if line.strip() == '---':
            continue
        m = re.match(r'^(#{1,4})\s+(.*)$', line)
        if m:
            lvl = len(m.group(1))
            h = doc.add_heading('', level=min(lvl, 4))
            add_runs(h, m.group(2))
            continue
        m = re.match(r'^\s*[-*]\s+(.*)$', line)
        if m:
            p = doc.add_paragraph(style='List Bullet')
            add_runs(p, m.group(1))
            continue
        m = re.match(r'^\s*(\d+)[.)]\s+(.*)$', line)
        if m:
            p = doc.add_paragraph(style='List Number')
            add_runs(p, m.group(2))
            continue
        p = doc.add_paragraph()
        add_runs(p, line)
    if table_rows: flush_table(doc, table_rows)
    flush_quote()
    doc.save(docx_path)
    print('saved', docx_path)

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    convert(a[0], a[1])
