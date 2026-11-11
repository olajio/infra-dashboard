"""Update the MIM rows of 'Persona KPI  Metrics Coverage' (sheet3.xml) for MIM V5 patch 11a (11 Nov 2026): Alerts on this CI removed.

Edits cells in place by rewriting sheet3.xml only (no rows added or moved); every other part, including the in-cell
evidence pictures, is copied byte for byte (openpyxl would drop them).
Usage: update_mim_kpi_sheet_2026-11-11.py SRC.xlsx OUT.xlsx
"""
import re
import sys
import zipfile
from xml.sax.saxutils import escape

SRC, OUT = sys.argv[1:3]
SHEET = 'xl/worksheets/sheet3.xml'
NOW = 'MIM V5 (11 Nov 2026): '

# row: {column: text}; column S (Explanation) gets the NOW prefix
ROWS = {
    143: {'S': 'Open Alerts with No Incident: with an incident or a CI picked, only open alerts on CIs linked to it in the '
               'CMDB with no incident of their own; every alert when nothing is picked. In section 2 next to Escalation '
               'Channel; its tile in section 1 follows the same controls. Since 11 Nov this is the only Netcool alert '
               'table (Alerts on this CI removed).'},
    145: {'S': 'New KPI since MIM V3 (section 2). Full width since 11 Nov (Alerts on this CI, beside it, removed).'},
    146: {'O': 'Fail', 'H': 'None (Alerts on this CI removed 11 Nov)',
          'S': 'Alerts on this CI was removed from MIM V5 on 11 Nov at the team\'s request. Alerts on CIs linked to the '
               'picked CI are in Open Alerts with No Incident; the picked CI\'s own Netcool alerts are no longer shown.'},
}
CHECK = {143: ('C', 'Open alerts with no incident'), 145: ('C', 'Changes on the CI'), 146: ('C', 'Alerts on the CI')}

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
