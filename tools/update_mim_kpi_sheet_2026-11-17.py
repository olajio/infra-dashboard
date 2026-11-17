"""Update the MIM rows of 'Persona KPI  Metrics Coverage' (sheet3.xml) for MIM V5 patch 17a (17 Nov 2026): P3 removed.

Edits cells in place by rewriting sheet3.xml only (no rows added or moved); every other part, including the in-cell
evidence pictures, is copied byte for byte (openpyxl would drop them).
Usage: update_mim_kpi_sheet_2026-11-17.py SRC.xlsx OUT.xlsx
"""
import re
import sys
import zipfile
from xml.sax.saxutils import escape

SRC, OUT = sys.argv[1:3]
SHEET = 'xl/worksheets/sheet3.xml'
NOW = 'MIM V5 (17 Nov 2026): '

# row: {column: text}; column S (Explanation) gets the NOW prefix
ROWS = {
    122: {'S': 'Section 1 opens with KPI tiles: Needs attention now (P1 + P2 over 8 h, with a priority strip), Active P1 '
               'and P2 over 8 h, each green at 0. P3 removed from MIM on 17 Nov. There is still no single P1 + P2 count.'},
    123: {'S': 'No single MTTR figure, but the P1 / P2 Time to Resolve chart shows the median time from opened to resolved '
               'of the P1 and P2 incidents resolved each day (resolved_at; P3 removed 17 Nov).'},
    125: {'S': 'No count of all active incidents. Needs attention now counts only incidents past their target (every P1, '
               'P2 over 8 h). P3 removed from MIM on 17 Nov.'},
    130: {'S': 'Active Incidents (P1 · P2 over 8 h): number, priority, CI, state, Opened, assignment group, assignee, '
               'group manager and short description. P2s are listed once past their 8 h target. P3 removed 17 Nov.'},
    132: {'S': 'P1 / P2 Time to Resolve vs Target: for the incidents resolved each day, the median hours from opened to '
               'resolved, split by priority, against 4 h / 8 h lines, last 7 days. Median per day, as the KPI asks. '
               'P3 removed 17 Nov.'},
    142: {'O': 'Fail', 'H': 'None (P3 over 24 h tile removed 17 Nov)',
          'S': 'Removed on 17 Nov at the team\'s request: MIM covers P1 and P2 only.'},
    163: {'D': 'Active incidents past their target in one number: every P1 and P2 open longer than 8 h, split by priority',
          'S': 'New KPI in MIM V5 (section 1). P3 removed 17 Nov: P1 + P2 over 8 h.'},
}
CHECK = {122: ('C', 'Active Major Incidents'), 123: ('C', 'MTTR'), 125: ('C', 'Total active incidents'), 130: ('C', 'N/A'),
         132: ('C', 'MTTR Trend'), 142: ('C', 'P3 incidents over 24 h target'), 163: ('C', 'Incidents needing attention now')}

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
