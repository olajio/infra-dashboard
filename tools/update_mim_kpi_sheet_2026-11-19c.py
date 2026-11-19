"""Update the MIM rows of 'Persona KPI  Metrics Coverage' (sheet3.xml) to MIM V5 as of 19 Nov 2026, by editing the XML,
and add the KPIs new since 4 Nov after the last MIM row (the method of update_mim_kpi_sheet_v5.py: rows below the MIM
block are shifted down; the in-cell evidence pictures and every other part are kept byte for byte).
Usage: update_mim_kpi_sheet_2026-11-19c.py SRC.xlsx OUT.xlsx
"""
import re
import sys
import zipfile
from xml.sax.saxutils import escape

SRC, OUT = sys.argv[1:3]
SHEET, WB = 'xl/worksheets/sheet3.xml', 'xl/workbook.xml'
LAST_MIM = 165
NOW = 'MIM V5 (19 Nov 2026): '
HEALTH = ('Follows the Health window control (default 24 h, up to 7 days); the panel reads 30 days since 19 Nov (5 years '
          'before), so nothing shown changes.')

# ---- existing MIM rows: (Overall Status, Explanation, {other column: new text}) ----
EXISTING = {
    140: ('Pass', 'Active P1 tile: every active P1, any age, On Hold P1s included; green at 0. Beside it Active P2, Active P3 '
                  'and P1 MTTR (90 days).', {'H': 'Active P1 (Metric tile)'}),
    143: ('Pass', 'Open Alerts with No Incident: with an incident or a CI picked, only open alerts on CIs linked to it in the '
                  'CMDB with no incident of their own; every alert when nothing is picked. Reads the last 7 days since 16 '
                  'Nov (CMDB links are re-sent daily). In section 2 next to Escalation Channel; its count is a tile in section 1.', {}),
    144: ('Pass', 'Escalation Channel: one row per active P1, P2 or P3 on the picked CI, filtered by the Priorities control, '
                  'with State, Opened and Age (since 18 Nov).',
          {'J': 'CI, incident, priority, state, opened, age, class, environment, assignment group, assignee, group manager (with emails)'}),
    150: ('Pass', 'Application Health lists only the applications MIM escalates: In Production, Operational and monitored in '
                  'cmdb_with_apm_flag, or the one picked in the Monitored application control. Fixed 17-18 Nov when new text '
                  'fields in cmdb_with_apm_flag (ci.name, service.name) broke the panel.', {}),
    152: ('Pass', 'Services of the Application lists only services of the monitored applications, or of the one picked in the '
                  'Monitored application control. Fixed 17-18 Nov with Application Health (cmdb_with_apm_flag field types).', {}),
}
for n in range(156, 163):
    EXISTING[n] = ('Pass', 'Section 3. ' + HEALTH, {})

# ---- KPIs new since 4 Nov ----
# (template, KPI, definition, unit, source, index, panel, notes, dimensions, scope, section)
NEW = [
    ('Overview', 'Active P2 incidents', 'Every active P2 incident, any age (On Hold P2s not counted)', 'count', 'logs',
     'servicenow-incidents', 'Active P2 (Metric tile)', 'Replaced P2 over 8 h on 17 Nov. Same incidents as the P2 rows of Active Incidents. Green at 0.',
     'priority', 'count', 1),
    ('Overview', 'Active P3 incidents', 'Every active P3 incident, any age (On Hold P3s not counted)', 'count', 'logs',
     'servicenow-incidents', 'Active P3 (Metric tile)', 'Back on 18 Nov (for the demo; MIM may drop P3 later). Same incidents as the P3 rows of Active Incidents.',
     'priority', 'count', 1),
    ('Overview', 'Priority filter', 'Pick which priorities (P1, P2, P3) the incident tables and the Time to Resolve chart show',
     'N/A', 'logs', 'servicenow-incidents', 'Priorities (multi-select control, top bar)',
     'Default P1, P2, P3. Filters Active Incidents, Escalation Channel and Time to Resolve; the tiles show one priority each.',
     'priority', 'N/A', 1),
    ('Overview', 'Incident age', 'Time since the incident was opened (e.g. "1 d 16 h")', 'time', 'logs',
     'servicenow-incidents', 'Age column in Active Incidents and Escalation Channel', 'Added 18 Nov.', 'incident', 'N/A', 1),
    ('Overview', 'Linked incidents (user impact of a P1)', 'How many incidents name this one as their parent incident',
     'count', 'logs', 'servicenow-incidents', 'Linked incidents column in Active Incidents',
     'Added 17 Nov. Child incidents updated in the last 7 days (about 2,500 for the 12-13 Nov Email/Exchange P1).', 'incident', 'count', 1),
]
K = len(NEW)

zin = zipfile.ZipFile(SRC)
sheet = zin.read(SHEET).decode('utf-8')
wb = zin.read(WB).decode('utf-8')


def shift_row(n):
    return n + K if n > LAST_MIM else n


def shift_ref(ref):          # A1 or $A$1
    m = re.fullmatch(r'(\$?[A-Z]{1,3}\$?)(\d+)', ref)
    return m.group(1) + str(shift_row(int(m.group(2)))) if m else ref


def shift_range(rng):        # A1:B5, or a single cell
    return ':'.join(shift_ref(p) for p in rng.split(':'))


def shift_sqref(sq):
    return ' '.join(shift_range(r) for r in sq.split())


def col_of(ref):
    return re.match(r'[A-Z]+', ref).group(0)


def inline(ref, style, text):
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{escape(text)}</t></is></c>'


rows = list(re.finditer(r'<row r="(\d+)"[^>]*?(?:/>|>.*?</row>)', sheet, re.S))
by_num = {int(m.group(1)): m for m in rows}
tmpl = by_num[LAST_MIM].group(0)
styles = {col_of(c): s for c, s in re.findall(r'<c r="([A-Z]+)\d+" s="(\d+)"', tmpl)}
COLS = [chr(65 + i) for i in range(19)]   # A..S


def set_cell(row_xml, ref, style_default, text):
    pat = re.compile(rf'<c r="{ref}"(?: [^>]*?)?(?:/>|>.*?</c>)', re.S)
    m = pat.search(row_xml)
    st = re.search(r' s="(\d+)"', m.group(0)).group(1) if m else style_default
    new = inline(ref, st, text)
    assert m, ref
    return row_xml[:m.start()] + new + row_xml[m.end():]


out, prev = [], 0
for m in rows:
    n = int(m.group(1))
    xml = m.group(0)
    out.append(sheet[prev:m.start()])
    prev = m.end()
    if n in EXISTING:
        status, why, extra = EXISTING[n]
        xml = set_cell(xml, f'O{n}', styles['O'], status)
        xml = set_cell(xml, f'S{n}', styles['S'], NOW + why)
        for col, text in extra.items():
            xml = set_cell(xml, f'{col}{n}', styles[col], text)
    if n > LAST_MIM:
        xml = re.sub(r'(<row r=")(\d+)', lambda mm: mm.group(1) + str(shift_row(int(mm.group(2)))), xml, count=1)
        xml = re.sub(r'(<c r="[A-Z]+)(\d+)"', lambda mm: f'{mm.group(1)}{shift_row(int(mm.group(2)))}"', xml)
    out.append(xml)
    if n == LAST_MIM:
        for i, (tpl, kpi, dfn, unit, src, idx, panel, notes, dims, scope, sec) in enumerate(NEW, 1):
            r = LAST_MIM + i
            vals = {'A': 'MIM', 'B': tpl, 'C': kpi, 'D': dfn, 'E': unit, 'F': src, 'G': idx, 'H': panel, 'I': notes, 'J': dims,
                    'K': scope, 'N': 'N/A', 'O': 'Pass',
                    'S': f'{NOW}new KPI achieved in MIM V5 (section {sec}); not in the earlier MIM KPI list.'}
            cells = ''.join(inline(f'{c}{r}', styles[c], vals[c]) if c in vals else f'<c r="{c}{r}" s="{styles[c]}"/>' for c in COLS)
            out.append(f'<row r="{r}" spans="1:19">{cells}</row>')
out.append(sheet[prev:])
sheet = ''.join(out)

# references to rows below the MIM block
sheet = re.sub(r'<dimension ref="([^"]+)"/>', lambda m: f'<dimension ref="{shift_range(m.group(1))}"/>', sheet)
sheet = re.sub(r'(<autoFilter ref=")([^"]+)"', lambda m: m.group(1) + shift_range(m.group(2)) + '"', sheet)
sheet = re.sub(r'(<selection [^>]*activeCell=")([^"]+)(" sqref=")([^"]+)"',
               lambda m: m.group(1) + shift_ref(m.group(2)) + m.group(3) + shift_sqref(m.group(4)) + '"', sheet)


def fix_cf(m):
    sq, body = m.group(1), m.group(2)
    first_old = sq.split()[0].split(':')[0]
    first_new = shift_sqref(sq).split()[0].split(':')[0]
    if first_old != first_new:   # the rule's formula is relative to the first cell
        body = body.replace(f',{first_old})', f',{first_new})')
    return f'<conditionalFormatting sqref="{shift_sqref(sq)}">{body}</conditionalFormatting>'


sheet = re.sub(r'<conditionalFormatting sqref="([^"]+)">(.*?)</conditionalFormatting>', fix_cf, sheet, flags=re.S)
wb = re.sub(r"('Persona KPI  Metrics Coverage'!)\$A\$1:\$S\$(\d+)",
            lambda m: f"{m.group(1)}$A$1:$S${shift_row(int(m.group(2)))}", wb)

with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == SHEET:
            data = sheet.encode('utf-8')
        elif item.filename == WB:
            data = wb.encode('utf-8')
        zout.writestr(item, data)
print(f'{len(EXISTING)} MIM rows updated, {K} rows added after row {LAST_MIM}')
