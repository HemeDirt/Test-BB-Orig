import zipfile, re, sys, os, html
def docx_txt(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml').decode('utf-8')
    xml = re.sub(r'<w:tab[^>]*/>', '\t', xml)
    xml = re.sub(r'</w:tc>', ' | ', xml)
    xml = re.sub(r'</w:p>', '\n', xml)
    xml = re.sub(r'<w:br[^>]*/>', '\n', xml)
    txt = re.sub(r'<[^>]+>', '', xml)
    return html.unescape(txt)
src, dst = sys.argv[1], sys.argv[2]
t = docx_txt(src)
t = re.sub(r'\n{3,}', '\n\n', t)
open(dst, 'w').write(t)
print(dst, len(t.encode('utf-8')), 'bytes')
