"""Update the MIM rows of 'Persona KPI  Metrics Coverage' (sheet3.xml) for MIM V5 (4 Nov 2026), by editing the XML.

The workbook keeps its evidence screenshots as in-cell pictures (rich values, vm=...); openpyxl would drop them, so
only sheet3.xml and workbook.xml are rewritten and every other part is copied byte for byte.
Usage: update_mim_v5.py SRC.xlsx OUT.xlsx   (SRC = the 30 Oct MIM V3 update)
"""
import re
import sys
import zipfile
from xml.sax.saxutils import escape

SRC, OUT = sys.argv[1:3]
SHEET, WB = 'xl/worksheets/sheet3.xml', 'xl/workbook.xml'
LAST_MIM = 162
NOW = 'MIM V5 (4 Nov 2026): '

# ---- existing MIM rows: (Overall Status, Explanation, {other column: new text}) ----
EXISTING = {
    122: ('Partial', 'Section 1 opens with KPI tiles: Needs attention now (P1 + P2 over 8 h + P3 over 24 h, with a priority strip), Active P1, P2 over 8 h and P3 over 24 h, each green at 0. There is still no single P1 + P2 count.', {}),
    125: ('Fail', 'No count of all active incidents. Needs attention now counts only incidents past their target (every P1, P2 over 8 h, P3 over 24 h).', {}),
    130: ('Pass', 'Active Incidents (P1 · P2 over 8 h · P3 over 24 h): number, priority, CI, state, Opened (added 4 Nov), SLA (from servicenow-task-sla), assignment group, assignee, group manager and short description. P2 / P3 are listed only once past their 8 h / 24 h target.', {}),
    131: ('Pass', 'Combined with the row above in Active Incidents. The CI support group column was removed from Escalate at the team\'s request (4 Nov); Escalate now shows each incident\'s State and Opened.', {}),
    134: ('Partial', 'No per-CI counts. Active Incidents lists each incident with its CI; Escalate shows the picked CI\'s incidents with their state, opened time and owners.', {}),
    143: ('Pass', 'Open Alerts with No Incident: with an incident or a CI picked, only alerts on that CI and on CIs linked to it in the CMDB (4 Nov); every alert when nothing is picked. The count by severity is also a tile in section 1 (Open alerts, no incident).',
          {'D': 'Netcool alerts still open on a CI that has no open incident; with an incident or CI picked, only that CI\'s and its CMDB-linked CIs\'',
           'H': 'Open Alerts with No Incident (Table); Open alerts, no incident (Metric tile)'}),
    144: ('Pass', 'Escalate: State (from the incident\'s latest record, as in Active Incidents) and Opened added, CI support group removed, at the team\'s request (4 Nov).',
          {'D': 'Active incidents on the selected CI with their state, when opened, assignment group, assignee and group manager',
           'J': 'CI, incident, priority, state, opened, class, environment, assignment group, assignee, group manager (with emails)'}),
    150: ('Pass', 'Application Health lists only the applications MIM escalates: In Production, Operational and monitored in cmdb_with_apm_flag (138 on 2 Nov), or the one picked in the Monitored application control (top bar).', {}),
    151: ('Pass', 'The Telemetry control was replaced by the Monitored application control (3 Nov). Monitored applications that send no APM data yet are listed last in Application Health as "Enrolled - no telemetry yet" when no CI is picked.',
          {'D': 'Monitored applications (In Production, Operational, is_monitored) that send no APM data yet',
           'H': 'Application Health, listed last as "Enrolled - no telemetry yet" (Table)'}),
    152: ('Pass', 'Services of the Application lists only services of the monitored applications, or of the one picked in the Monitored application control.', {}),
}

# ---- KPIs new in MIM V5 ----
# (template, KPI, definition, unit, source, index, panel, notes, dimensions, scope, section)
NEW = [
    ('Overview', 'Incidents needing attention now', 'Active incidents past their target in one number: every P1, P2 open longer than 8 h, P3 open longer than 24 h, split by priority', 'count', 'logs', 'servicenow-incidents', 'Needs attention now (Metric tile with priority strip)',
     'Same incidents as Active Incidents. Green at 0. Last 7 days (fixed).', 'priority', 'count', 1),
    ('Overview', 'Open alerts with no incident (count)', 'Open Netcool alerts on production CIs with no open incident, counted by severity (Critical, Major, other)', 'count', 'logs', '.ds-bridge-alerts-netcool-default-*, servicenow-incidents', 'Open alerts, no incident (Metric tile with severity strip)',
     'Same alerts as the Open Alerts with No Incident table with nothing picked. Last 24 h.', 'severity', 'count', 1),
    ('Detailed', 'Monitored applications in scope', 'The applications MIM escalates: cmdb_with_apm_flag with install status In Production, operational status Operational and is_monitored true', 'count', 'CMDB', 'cmdb_with_apm_flag', 'Monitored application (control, top bar)',
     'Scopes Application Health, Services of the Application and the section 3 Application / Service lists. Dynamic: follows the index.', 'application', 'count', 3),
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
