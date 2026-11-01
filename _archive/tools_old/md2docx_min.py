# -*- coding: utf-8 -*-
"""Минимальный md->docx (заголовки, таблицы, списки, bold/italic/code). Usage: md2docx_min.py in.md out.docx"""
import re, sys
from docx import Document
from docx.shared import Pt, Cm

def add_runs(p, text):
    parts = re.split(r'(\*\*.+?\*\*|\*[^*]+?\*|`[^`]+?`)', text)
    for part in parts:
        if not part: continue
        if part.startswith('**') and part.endswith('**'):
            r = p.add_run(part[2:-2]); r.bold = True
        elif part.startswith('*') and part.endswith('*') and len(part) > 2:
            r = p.add_run(part[1:-1]); r.italic = True
        elif part.startswith('`') and part.endswith('`'):
            r = p.add_run(part[1:-1]); r.font.name = 'Consolas'; r.font.size = Pt(9)
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
                r.font.size = Pt(8.5)
                if i == 0: r.bold = True
    doc.add_paragraph()

def convert(md_path, docx_path):
    lines = open(md_path, encoding='utf-8').read().split('\n')
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(1.6)
    st = doc.styles['Normal']; st.font.name = 'Calibri'; st.font.size = Pt(10.5)
    table_rows = []
    for raw in lines:
        line = raw.rstrip()
        if line.startswith('|'):
            cells = [c.strip() for c in line.strip('|').split('|')]
            if all(re.fullmatch(r':?-{2,}:?', c or '--') for c in cells): continue
            table_rows.append(cells); continue
        if table_rows:
            flush_table(doc, table_rows); table_rows = []
        if not line.strip(): continue
        m = re.match(r'^(#{1,4})\s+(.*)$', line)
        if m:
            h = doc.add_heading('', level=min(len(m.group(1)), 4))
            add_runs(h, m.group(2)); continue
        m = re.match(r'^\s*[-*]\s+(.*)$', line)
        if m:
            p = doc.add_paragraph(style='List Bullet'); add_runs(p, m.group(1)); continue
        m = re.match(r'^\s*(\d+)[.)]\s+(.*)$', line)
        if m:
            p = doc.add_paragraph(style='List Number'); add_runs(p, m.group(2)); continue
        p = doc.add_paragraph(); add_runs(p, line)
    if table_rows: flush_table(doc, table_rows)
    doc.save(docx_path)
    print('saved', docx_path)

if __name__ == '__main__':
    convert(sys.argv[1], sys.argv[2])
