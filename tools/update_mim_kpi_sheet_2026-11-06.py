"""Update the MIM rows of 'Persona KPI  Metrics Coverage' (sheet3.xml) for MIM V5 patch 06a (6 Nov 2026).

Edits cells in place by rewriting sheet3.xml only (no rows added or moved); every other part, including the in-cell
evidence pictures, is copied byte for byte (openpyxl would drop them).
Usage: update_mim_kpi_sheet_2026-11-06.py SRC.xlsx OUT.xlsx
"""
import re
import sys
import zipfile
from xml.sax.saxutils import escape

SRC, OUT = sys.argv[1:3]
SHEET = 'xl/worksheets/sheet3.xml'
NOW = 'MIM V5 (6 Nov 2026): '

# row: {column: text}; column S (Explanation) gets the NOW prefix
ROWS = {
    131: {'S': 'Combined with the row above in Active Incidents. Escalate was renamed Escalation Channel (6 Nov); it '
               'shows each incident\'s State and Opened, without the CI support group (4 Nov).'},
    132: {'S': 'P1 / P2 / P3 Time to Resolve vs Target: daily average (not median) for P1, P2 and P3 against 4 h / 8 h / '
               '24 h lines, last 7 days, age so far of active incidents (not resolution times). Since 6 Nov all lines '
               'share one hours axis: the P3 24 h line was on a separate right-hand axis and read as about 1 h.'},
    134: {'S': 'No per-CI counts. Active Incidents lists each incident with its CI; Escalation Channel shows the picked '
               'CI\'s incidents with their state, opened time and owners.'},
    137: {'S': 'No breakdown by assignment group; the group is shown per incident in Active Incidents and Escalation '
               'Channel.'},
    143: {'S': 'Open Alerts with No Incident: with an incident or a CI picked, only alerts on that CI and on CIs linked to '
               'it in the CMDB; every alert when nothing is picked. Since 6 Nov it sits in section 2, next to Escalation '
               'Channel, and the Open alerts, no incident tile (section 1) follows the same controls.'},
    144: {'H': 'Escalation Channel (Table)',
          'S': 'Escalate renamed Escalation Channel (6 Nov), now side by side with Open Alerts with No Incident at the '
               'top of section 2. State and Opened added, CI support group removed (4 Nov).'},
    145: {'S': 'New KPI since MIM V3 (section 2). Since 6 Nov side by side with Alerts on this CI.'},
    146: {'S': 'New KPI since MIM V3 (section 2). Since 6 Nov side by side with Changes in the Last 7 Days on this CI.'},
    164: {'D': 'Open Netcool alerts on production CIs with no open incident; with an incident or CI picked, only that '
               'CI\'s and its CMDB-linked CIs\'',
          'H': 'Open alerts, no incident (Metric tile, Critical count under the number)',
          'I': 'Same alerts as the Open Alerts with No Incident table, following the Incident / CI controls (6 Nov: '
               'rebuilt as a Lens metric, as a Vega tile cannot read controls). Last 24 h. Green at 0.',
          'S': 'Follows the Incident / CI controls since 6 Nov, like the table; it counted every alert before.'},
}
CHECK = {131: ('C', 'N/A'), 132: ('C', 'MTTR Trend'), 134: ('C', 'P1/P2 Incidents by CI'), 143: ('C', 'Open alerts with no incident'),
         144: ('C', 'Who to escalate to'), 145: ('C', 'Changes on the CI'), 146: ('C', 'Alerts on the CI'),
         164: ('C', 'Open alerts with no incident (count)')}

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
