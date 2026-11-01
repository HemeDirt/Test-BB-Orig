# -*- coding: utf-8 -*-
import re, sys
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC = sys.argv[1] if len(sys.argv) > 1 else 'ПРАВИЛА_БЛИЦ_БОЙ_ред4.0_КАНОН.md'
OUT = sys.argv[2] if len(sys.argv) > 2 else SRC.replace('.md', '.docx')

doc = Document()
# базовые стили
st = doc.styles['Normal']
st.font.name = 'Calibri'
st.font.size = Pt(10.5)
st.element.rPr.rFonts.set(qn('w:eastAsia'), 'Calibri')
st.element.rPr.rFonts.set(qn('w:cs'), 'Calibri')
pf = st.paragraph_format
pf.space_after = Pt(5); pf.space_before = Pt(0); pf.line_spacing = 1.08
for sec in doc.sections:
    sec.left_margin = Cm(1.8); sec.right_margin = Cm(1.8)
    sec.top_margin = Cm(1.6); sec.bottom_margin = Cm(1.6)
for name, size, color in (('Heading 1',17,'1F3864'),('Heading 2',13.5,'2E5496'),('Heading 3',11.5,'2E5496')):
    s = doc.styles[name]
    s.font.size = Pt(size); s.font.color.rgb = RGBColor.from_string(color); s.font.name='Calibri'
    s.paragraph_format.space_before = Pt(12); s.paragraph_format.space_after = Pt(5)

TOKEN = re.compile(r'(\*\*.+?\*\*|`[^`]+?`|\*[^*]+?\*)')
def add_runs(p, text):
    text = text.replace('▸4.0', '▸ 4.0')
    for part in TOKEN.split(text):
        if not part: continue
        if part.startswith('**') and part.endswith('**'):
            r = p.add_run(part[2:-2]); r.bold = True
        elif part.startswith('`') and part.endswith('`'):
            r = p.add_run(part[1:-1]); r.font.name = 'Consolas'
            r.font.size = Pt(9.5); r.font.color.rgb = RGBColor.from_string('8B3A00')
        elif part.startswith('*') and part.endswith('*') and len(part) > 2:
            r = p.add_run(part[1:-1]); r.italic = True
        else:
            p.add_run(part)

def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement('w:shd'); sh.set(qn('w:val'),'clear'); sh.set(qn('w:fill'),hexcolor)
    tcPr.append(sh)

def add_table(rows):
    hdr = [c.strip() for c in rows[0].strip('|').split('|')]
    body = []
    for r in rows[2:]:
        body.append([c.strip() for c in r.strip('|').split('|')])
    ncol = len(hdr)
    t = doc.add_table(rows=1, cols=ncol)
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(hdr):
        cell = t.rows[0].cells[i]
        cell.text = ''
        p = cell.paragraphs[0]; p.paragraph_format.space_after = Pt(1)
        add_runs(p, h)
        for run in p.runs: run.bold = True; run.font.size = Pt(9.5)
        shade(cell, 'DCE6F1')
    for br in body:
        cells = t.add_row().cells
        for i in range(ncol):
            v = br[i] if i < len(br) else ''
            cell = cells[i]; cell.text=''
            p = cell.paragraphs[0]; p.paragraph_format.space_after = Pt(1)
            add_runs(p, v)
            for run in p.runs: run.font.size = Pt(9.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)

lines = open(SRC, encoding='utf-8').read().split('\n')
i = 0; first_h1 = True; buf = []
def flush_buf():
    global buf
    if buf:
        p = doc.add_paragraph(); add_runs(p, ' '.join(buf)); buf = []
while i < len(lines):
    ln = lines[i]
    s = ln.strip()
    if s.startswith('|'):
        flush_buf(); rows = []
        while i < len(lines) and lines[i].strip().startswith('|'):
            rows.append(lines[i].strip()); i += 1
        add_table(rows); continue
    if not s:
        flush_buf(); i += 1; continue
    if s == '---':
        flush_buf(); i += 1; continue
    m = re.match(r'^(#{1,3})\s+(.*)$', s)
    if m:
        flush_buf()
        lvl = len(m.group(1)); txt = m.group(2).strip()
        if lvl == 1 and not first_h1:
            doc.add_page_break()
        first_h1 = False
        h = doc.add_heading(level=lvl); add_runs(h, txt.replace('**',''))
        i += 1; continue
    m = re.match(r'^-\s+\[\s\]\s+(.*)$', s)
    if m:
        flush_buf(); p = doc.add_paragraph(style='List Bullet'); add_runs(p, '☐ ' + m.group(1)); i += 1; continue
    m = re.match(r'^[-*]\s+(.*)$', s)
    if m:
        flush_buf(); p = doc.add_paragraph(style='List Bullet'); add_runs(p, m.group(1)); i += 1; continue
    m = re.match(r'^(\d+)\.\s+(.*)$', s)
    if m:
        flush_buf(); p = doc.add_paragraph(style='List Number'); add_runs(p, m.group(2)); i += 1; continue
    if s.startswith('> '):
        flush_buf(); p = doc.add_paragraph(); p.paragraph_format.left_indent = Cm(0.6)
        add_runs(p, s[2:]); i += 1; continue
    buf.append(s); i += 1
flush_buf()
doc.save(OUT)
print('сохранено:', OUT)
