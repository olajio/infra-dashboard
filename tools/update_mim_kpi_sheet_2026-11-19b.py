"""Update the MIM rows of 'Persona KPI  Metrics Coverage' (sheet3.xml) for MIM V5 patches 19a / 19b (19 Nov 2026): Time to
Resolve over 30 days and the P1 MTTR (90 days) tile.

Edits cells in place by rewriting sheet3.xml only (no rows added or moved); every other part, including the in-cell
evidence pictures, is copied byte for byte (openpyxl would drop them).
Usage: update_mim_kpi_sheet_2026-11-19b.py SRC.xlsx OUT.xlsx
"""
import re
import sys
import zipfile
from xml.sax.saxutils import escape

SRC, OUT = sys.argv[1:3]
SHEET = 'xl/worksheets/sheet3.xml'
NOW = 'MIM V5 (19 Nov 2026): '

# row: {column: text}; column S (Explanation) gets the NOW prefix
ROWS = {
    123: {'S': 'P1 MTTR (90 days) tile in section 1 (since 19 Nov): median MTTR of the P1s resolved in the last 90 days, '
               'from when each became a P1 (ServiceNow incident timeline) to resolved, with the count, the average and '
               'how many were within 4 h; red above the 4 h target. Also per open P1 in Active Incidents (Time as P1) and '
               'on the Time to Resolve chart. P2 / P3 use Duration (opened to resolved).'},
    132: {'S': 'P1 / P2 / P3 Time to Resolve vs Target: rolling 7-day median of the resolved incidents for each of the '
               'last 30 days (since 19 Nov; 7 before), against 4 h / 8 h / 24 h lines. P1 line = MTTR from the time the '
               'incident became a P1; P2 and P3 lines = Duration, opened to resolved. Follows the Priorities control.'},
}
CHECK = {123: ('C', 'MTTR'), 132: ('C', 'MTTR Trend')}
zin = zipfile.ZipFile(SRC)
sheet = zin.read(SHEET).decode('utf-8')
shared = [''.join(re.findall(r'<t[^>]*>(.*?)</t>', si, re.S))
          for si in re.findall(r'<si>(.*?)</si>', zin.read('xl/sharedStrings.xml').decode('utf-8'), re.S)]


def text_of(cell):
    if 't="s"' in cell:
        return shared[int(re.search(r'<v>(\d+)</v>', cell).group(1))]
    m = re.search(r'<t[^>]*>(.*?)</t>', cell, re.S)
    return m.group(1) if m else ''


def edit_row(m):
    n = int(m.group(1))
    xml = m.group(0)
    if n not in ROWS:
        return xml
    if n in CHECK:   # make sure the row is the KPI we mean
        col, want = CHECK[n]
        c = re.search(rf'<c r="{col}{n}"(?: [^>]*?)?(?:/>|>.*?</c>)', xml, re.S)
        assert c and text_of(c.group(0)).replace('&amp;', '&') == want, (n, c and text_of(c.group(0)))
    for col, text in ROWS[n].items():
        if col == 'S':
            text = NOW + text
        pat = re.compile(rf'<c r="{col}{n}"(?: [^>]*?)?(?:/>|>.*?</c>)', re.S)
        c = pat.search(xml)
        assert c, (n, col)
        style = re.search(r' s="(\d+)"', c.group(0))
        s_attr = ' s="%s"' % style.group(1) if style else ''
        new = (f'<c r="{col}{n}"{s_attr} t="inlineStr">'
               f'<is><t xml:space="preserve">{escape(text)}</t></is></c>')
        xml = xml[:c.start()] + new + xml[c.end():]
    return xml


sheet = re.sub(r'<row r="(\d+)"[^>]*?(?:/>|>.*?</row>)', edit_row, sheet, flags=re.S)
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        zout.writestr(item, sheet.encode('utf-8') if item.filename == SHEET else zin.read(item.filename))
print(f'{len(ROWS)} MIM rows updated')
