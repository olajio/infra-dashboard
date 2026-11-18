"""Update the MIM rows of 'Persona KPI  Metrics Coverage' (sheet3.xml) for MIM V5 patch 18a (18 Nov 2026): P3 back (any
age), Priorities control, Age columns, Time to Resolve with a P3 line.

Edits cells in place by rewriting sheet3.xml only (no rows added or moved); every other part, including the in-cell
evidence pictures, is copied byte for byte (openpyxl would drop them).
Usage: update_mim_kpi_sheet_2026-11-18a.py SRC.xlsx OUT.xlsx
"""
import re
import sys
import zipfile
from xml.sax.saxutils import escape

SRC, OUT = sys.argv[1:3]
SHEET = 'xl/worksheets/sheet3.xml'
NOW = 'MIM V5 (18 Nov 2026): '

# row: {column: text}; column S (Explanation) gets the NOW prefix
ROWS = {
    122: {'S': 'Section 1 opens with KPI tiles: Needs attention now (every active P1, P2 and P3, with a priority strip), '
               'Active P1, Active P2 and Active P3 (any age), each green at 0. On Hold P1s count as active (On Hold P2s '
               'and P3s do not). A multi-select Priorities control (P1, P2, P3) in the top bar filters the tables and '
               'the Time to Resolve chart.'},
    125: {'S': 'No count of all active incidents. Needs attention now counts every active P1, P2 and P3 (any age); P4 / '
               'P5 are not on MIM.'},
    130: {'S': 'Active Incidents (P1 · P2 · P3): every active P1, P2 and P3, any age, filtered by the Priorities control: '
               'number, priority, CI, state, Opened, Age, Time as P1 / Duration (h), Linked incidents, assignment '
               'group, assignee, group manager and short description. On Hold P1s shown.'},
    131: {'S': 'Combined with the row above in Active Incidents. Escalation Channel (renamed 6 Nov) shows each active P1, '
               'P2 or P3 on the picked CI with its State, Opened and Age (since 18 Nov), filtered by the Priorities '
               'control.'},
    132: {'S': 'P1 / P2 / P3 Time to Resolve vs Target: rolling 7-day median for each of the last 7 days, against 4 h / '
               '8 h / 24 h lines. P1 line = MTTR from the time the incident became a P1; P2 and P3 lines = Duration, '
               'opened to resolved. P3 back 18 Nov; follows the Priorities control.'},
    142: {'O': 'Fail', 'H': 'None (replaced 18 Nov by the Active P3 tile, any age)',
          'S': 'P3 removed 17 Nov, back 18 Nov at the team\'s request as every active P3 whatever its age (Active P3 '
               'tile); the 24 h P3 target is on the Time to Resolve chart.'},
    163: {'D': 'Active P1, P2 and P3 incidents in one number, split by priority',
          'S': 'New KPI in MIM V5 (section 1). Since 18 Nov every active P1, P2 and P3, any age.'},
}
CHECK = {122: ('C', 'Active Major Incidents'), 125: ('C', 'Total active incidents'),
         130: ('D', 'SLA Breach deatils of open P1/P2 incidents'), 131: ('D', 'Active P1/P2 — Pending Action'),
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
