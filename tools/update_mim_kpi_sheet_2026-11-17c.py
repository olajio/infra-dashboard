"""Update the MIM rows of 'Persona KPI  Metrics Coverage' (sheet3.xml) for MIM V5 patch 17c (17 Nov 2026): P1 MTTR from
the time the incident became a P1, P2 Duration, Linked incidents, On Hold P1s shown (James Patock's proposal).

Edits cells in place by rewriting sheet3.xml only (no rows added or moved); every other part, including the in-cell
evidence pictures, is copied byte for byte (openpyxl would drop them).
Usage: update_mim_kpi_sheet_2026-11-17c.py SRC.xlsx OUT.xlsx
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
               'and P2 over 8 h, each green at 0. Since 17 Nov On Hold P1s count as active (On Hold P2s do not).'},
    123: {'S': 'P1 MTTR = hours from the time the incident became a P1 (from the ServiceNow incident timeline; the opened '
               'time if opened as a P1) to resolved, or to now while open. Shown per incident in Active Incidents (Time as '
               'P1 / Duration) and as a rolling 7-day median on the P1 / P2 chart; no single MTTR tile. P2 uses Duration '
               '(opened to resolved).'},
    126: {'S': 'No count, and since 13 Nov no SLA column in Active Incidents (removed at the team\'s request). Agreed 17 '
               'Nov (James Patock): MIM reports P1 MTTR and P2 Duration instead of the ServiceNow SLAs.'},
    127: {'S': 'No count; the SLA column ("Breaching") was removed on 13 Nov. Replaced by P1 MTTR / P2 Duration against '
               'the 4 h / 8 h targets (17 Nov).'},
    128: {'S': 'No count; the SLA column ("Within SLA") was removed on 13 Nov. Replaced by P1 MTTR / P2 Duration against '
               'the 4 h / 8 h targets (17 Nov).'},
    130: {'S': 'Active Incidents (P1 · P2 over 8 h): number, priority, CI, state, Opened, Time as P1 / Duration (h), '
               'Linked incidents, assignment group, assignee, group manager and short description. On Hold P1s shown.'},
    132: {'S': 'P1 / P2 Time to Resolve vs Target: rolling 7-day median for each of the last 7 days, against 4 h / 8 h '
               'lines. P1 line = MTTR from the time the incident became a P1 (since 17 Nov); P2 line = Duration, opened to '
               'resolved. P3 removed 17 Nov.'},
}
CHECK = {122: ('C', 'Active Major Incidents'), 123: ('C', 'MTTR'), 126: ('C', 'Breached P1/P2 incidents'),
         127: ('C', 'Approaching breach P1/P2'), 128: ('C', 'Healthly P1/P2 - under 80% of SLA'),
         130: ('D', 'SLA Breach deatils of open P1/P2 incidents'), 132: ('C', 'MTTR Trend')}

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
