"""Update the Infra / Overview rows of 'Persona KPI  Metrics Coverage' (sheet4.xml) in
"Dashboard Testing and Verification Template-updated.xlsx" to the current Infrastructure Overview v2 (19 Nov 2026).

Usage: update_infra_overview_kpis_2026-11-19.py SRC.xlsx OUT.xlsx

The Infra / Overview block (rows 88-98, Persona = Infra, Template = Overview) described an earlier overview. KPIs that
are not on the current dashboard are removed (Servers Up, Fleet Availability, P3 Incident count, the four Windows /
Linux high CPU / memory tables). Those still on it are updated (Total Servers Monitored, Servers Down, P1 and P2
incident counts). The KPIs of the current dashboard that were missing are added. The block grows from 11 to 12 rows,
so every row below it moves down by one; the evidence pictures of the removed rows go with them, and the kept rows'
pictures (screenshots of the earlier dashboard) are cleared so new evidence can be added. Only sheet4.xml and
workbook.xml change; every other part is copied byte for byte.
"""
import re
import sys
import zipfile
from xml.sax.saxutils import escape

SRC, OUT = sys.argv[1:3]
SHEET, WB = 'xl/worksheets/sheet4.xml', 'xl/workbook.xml'
FIRST, LAST = 88, 98                      # the Infra / Overview block today
NOW = 'Infrastructure Overview v2 (19 Nov 2026): '
INC, ALERTS = 'servicenow-incidents', '.ds-bridge-alerts-netcool-default-*, .alerts-observability.*'

# (keep-from-row or None, C KPI, D definition, E unit, F index, G panel, H source, I query notes, J dims, K scope, N RAG, O, P notes, S)
ROWS = [
    (88, 'Total Servers Monitored', 'Production servers (CMDB class Server, Windows, Linux, AIX, HP-UX, network appliance, '
     'SQL instance; environment prod; Operational) that sent system metrics in the last 24 h', 'count', 'metric*',
     'Servers tile (Metric, main number)', 'metrics', 'ES|QL: latest metric per ci.name_normalized in the last 24 h; COUNT',
     'N/A', 'count', 'Pass', 'Pass', "The tile's subtitle reads \"No data for 10 min (seen in the last day)\", which "
     'describes the servers-down number; consider relabelling.', 'Main number of the Servers tile in section 1.'),
    (90, 'Servers Down', 'Production servers seen in the last 24 h with no metrics in the last 10 minutes: down, or '
     'their agent stopped', 'count', 'metric*', 'Servers tile (Metric, secondary number)', 'metrics',
     'ES|QL: last metric older than 600 s; total - reporting', 'N/A', 'count', 'Pass', 'Pass', '',
     'Servers tile in section 1; green at 0. Also turns a domain tile red.'),
    (92, 'P1 Incident count', 'Active P1 incidents (latest record not On Hold, Resolved, Closed or Canceled; opened in '
     'the last 30 days) whose CI is infrastructure, not an application service', 'count', INC,
     'Active P1 (infrastructure) (Metric tile)', 'logs', 'ES|QL: latest record per incident; infrastructure from the '
     "CI's CMDB class", 'N/A', 'count', 'Pass', 'Pass', '', 'Tile in section 1; green at 0. The incidents are listed in '
     'Active P1 · P2.'),
    (93, 'P2 Incident count', 'Active P2 incidents on infrastructure CIs open longer than 8 h (MIM\'s P2 target)',
     'count', INC, 'P2 over 8 h (infrastructure) (Metric tile)', 'logs', 'ES|QL: latest record per incident; age = now '
     '- opened > 8 h', 'N/A', 'count', 'Pass', 'Pass', 'MIM shows every active P2 since 17 Nov; this tile still '
     'shows P2s over 8 h.', 'Tile in section 1; green at 0.'),
    (None, 'Domain status', 'One RAG tile per infrastructure domain (Server, Database, Middleware, VMware, Cloud, '
     'Network), each linking to its detailed dashboard', 'status', f'{INC}, {ALERTS}, metrics-system.*, GKE and vSphere '
     'metrics', 'Domain status (tiles)', 'logs / metrics', 'Red: an open P1, a Critical alert, a server not reporting, '
     'a GKE cluster critical or silent. Amber: an active P2, a Major alert, a server at 90 % CPU / memory / disk, a GKE '
     'warning. VMware from vSphere thresholds (vmware_data.xlsx). Domain from the CI\'s CMDB class', 'domain',
     'status', 'Pass', 'Pass', '', 'Database and Middleware status comes from incidents and alerts only, and vSphere '
     'covers 4 of 549 ESX hosts: both listed in the Next Release Roadmap (no longer tagged "partial" on the tiles).'),
    (None, 'Critical alerts', 'Open Critical alerts on infrastructure: Netcool alerts open in the last 24 h on '
     'production CIs, and active Elastic paladin-* alerts; the Major count under the number', 'count', ALERTS,
     'Critical alerts (Metric tile)', 'logs', 'Critical = Netcool severity 5 or Elastic critical', 'severity', 'count',
     'Pass', 'Pass', '', 'Tile in section 1; green at 0.'),
    (None, 'Servers under pressure', 'Reporting production servers with CPU p90, memory or their fullest disk at 90 % '
     'or more in the last hour; under the number, how many because of a disk', 'count',
     '.ds-metrics-system.cpu-default*, .ds-metrics-system.memory-default*, .ds-metrics-system.filesystem-default*',
     'Servers under pressure (Metric tile)', 'metrics', 'ES|QL: per server, last hour', 'N/A', 'count', 'Pass', 'Pass',
     '', 'Tile in section 1; green at 0. Replaces the Windows / Linux high CPU and memory tables.'),
    (None, 'Failed changes (7 days)', 'Change requests that ended in the last 7 days with a close code saying '
     'unsuccessful, failed or backed out; under the number, all changes that ended', 'count',
     'servicenow-change-requests', 'Failed changes (7 days) (Metric tile)', 'logs', 'ES|QL: each change once (latest '
     'record); close code', 'N/A', 'count', 'Pass', 'Pass', '', 'Tile in section 1; green at 0.'),
    (None, 'Active P1 · P2 incidents (infrastructure)', 'Active P1 incidents, and P2 incidents open longer than 8 h, '
     'whose CI is infrastructure, with the domain from the CI\'s CMDB class', 'N/A', INC, 'Active P1 · P2 (Table)',
     'logs', 'Click the incident or the CI to open it in ServiceNow, or open MIM', 'incident, priority, CI, domain, '
     'state, opened, assignment group', 'list', 'N/A', 'Pass', '', 'Table in section 1.'),
    (None, 'Open infrastructure alerts by domain', 'Open alerts by domain and severity (Critical, Major, Minor): Netcool '
     'alerts open in the last 24 h on production CIs, and active Elastic paladin-* alerts', 'count', ALERTS,
     'Open infrastructure alerts by domain (bar chart)', 'logs', 'Domain from the CI\'s CMDB class (Netcool alerts on '
     'a node with no CMDB CI count as Network) or, for Elastic, from the rule', 'domain / severity', 'count', 'N/A',
     'Pass', '', 'Chart in section 1.'),
    (None, 'Change Request Summary', 'Changes on infrastructure CIs (or with no CI class): open by type (normal, '
     'standard, emergency), implemented this week against the week before, pending approval, scheduled in the next 7 '
     'days', 'count', 'servicenow-change-requests', 'Change Request Summary (cards)', 'logs', 'Each change counted '
     'once (latest record, updated in the last 30 days); as on Portfolio v4', 'type / state', 'count', 'N/A', 'Pass',
     '', 'Cards in section 1.'),
    (None, 'Infrastructure incidents per domain', 'Incidents (every priority) opened per day in the last 30 days on '
     'infrastructure CIs, by domain', 'count', INC, 'Infrastructure incidents per Domain (trend)', 'logs', 'Domain '
     'from the CI\'s CMDB class', 'day / domain', 'count', 'N/A', 'Pass', '',
     'Trend in section 1: whether a domain is getting better or worse.'),
]
K = len(ROWS) - (LAST - FIRST + 1)          # rows added to the sheet (here +1)

zin = zipfile.ZipFile(SRC)
sheet = zin.read(SHEET).decode('utf-8')
wb = zin.read(WB).decode('utf-8')
shared = [''.join(re.findall(r'<t[^>]*>(.*?)</t>', si, re.S))
          for si in re.findall(r'<si>(.*?)</si>', zin.read('xl/sharedStrings.xml').decode('utf-8'), re.S)]


def text_of(cell):
    if 't="s"' in cell:
        return shared[int(re.search(r'<v>(\d+)</v>', cell).group(1))]
    m = re.search(r'<t[^>]*>(.*?)</t>', cell, re.S)
    return m.group(1) if m else ''


def shift_row(n):
    return n + K if n > LAST else n


def shift_ref(ref):
    m = re.fullmatch(r'(\$?[A-Z]{1,3}\$?)(\d+)', ref)
    return m.group(1) + str(shift_row(int(m.group(2)))) if m else ref


def shift_range(rng):
    return ':'.join(shift_ref(p) for p in rng.split(':'))


def shift_sqref(sq):
    return ' '.join(shift_range(r) for r in sq.split())


rows = list(re.finditer(r'<row r="(\d+)"[^>]*?(?:/>|>.*?</row>)', sheet, re.S))
by_num = {int(m.group(1)): m.group(0) for m in rows}
for n in range(FIRST, LAST + 1):           # make sure this is the block we think it is
    r = by_num[n]
    a = text_of(re.search(rf'<c r="A{n}"[^>]*?(?:/>|>.*?</c>)', r, re.S).group(0))
    b = text_of(re.search(rf'<c r="B{n}"[^>]*?(?:/>|>.*?</c>)', r, re.S).group(0))
    assert (a, b) == ('Infra', 'Overview'), (n, a, b)
for n in (FIRST - 1, LAST + 1):
    r = by_num[n]
    b = re.search(rf'<c r="B{n}"[^>]*?(?:/>|>.*?</c>)', r, re.S)
    assert not (b and text_of(b.group(0)) == 'Overview' and 'Infra' in r), n
TEMPLATE = by_num[92]


def build_row(src_xml, src_n, n, vals):
    xml = re.sub(r'<row r="\d+"', f'<row r="{n}"', src_xml, count=1)
    xml = re.sub(rf'<c r="([A-Z]+){src_n}"', lambda m: f'<c r="{m.group(1)}{n}"', xml)
    for col, text in vals.items():
        pat = re.compile(rf'<c r="{col}{n}"(?: [^>]*?)?(?:/>|>.*?</c>)', re.S)
        m = pat.search(xml)
        assert m, (n, col)
        st = re.search(r' s="(\d+)"', m.group(0))
        s_attr = f' s="{st.group(1)}"' if st else ''
        new = (f'<c r="{col}{n}"{s_attr} t="inlineStr"><is><t xml:space="preserve">{escape(text)}</t></is></c>'
               if text else f'<c r="{col}{n}"{s_attr}/>')
        xml = xml[:m.start()] + new + xml[m.end():]
    return xml


block = []
for i, (keep, c, d, e, f, g, h, q, j, k, n_rag, o, p, s) in enumerate(ROWS):
    n = FIRST + i
    src_n = keep or 92
    vals = {'A': 'Infra', 'B': 'Overview', 'C': c, 'D': d, 'E': e, 'F': f, 'G': g, 'H': h, 'I': q, 'J': j, 'K': k,
            'L': '', 'M': '', 'N': n_rag, 'O': o, 'P': p, 'Q': '', 'R': '', 'S': NOW + s}
    block.append(build_row(by_num[src_n], src_n, n, vals))

out, prev, done = [], 0, False
for m in rows:
    n = int(m.group(1))
    out.append(sheet[prev:m.start()])
    prev = m.end()
    if FIRST <= n <= LAST:
        if not done:
            out.extend(block)
            done = True
        continue
    xml = m.group(0)
    if n > LAST:
        xml = re.sub(r'(<row r=")(\d+)', lambda mm: mm.group(1) + str(shift_row(int(mm.group(2)))), xml, count=1)
        xml = re.sub(r'(<c r="[A-Z]+)(\d+)"', lambda mm: f'{mm.group(1)}{shift_row(int(mm.group(2)))}"', xml)
    out.append(xml)
out.append(sheet[prev:])
sheet = ''.join(out)

sheet = re.sub(r'<dimension ref="([^"]+)"/>', lambda m: f'<dimension ref="{shift_range(m.group(1))}"/>', sheet)
sheet = re.sub(r'(<autoFilter ref=")([^"]+)"', lambda m: m.group(1) + shift_range(m.group(2)) + '"', sheet)
sheet = re.sub(r'(<selection [^>]*activeCell=")([^"]+)(" sqref=")([^"]+)"',
               lambda m: m.group(1) + shift_ref(m.group(2)) + m.group(3) + shift_sqref(m.group(4)) + '"', sheet)


def fix_cf(m):
    sq, body = m.group(1), m.group(2)
    first_old = sq.split()[0].split(':')[0]
    first_new = shift_sqref(sq).split()[0].split(':')[0]
    if first_old != first_new:
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
print(f'Infra / Overview: {LAST - FIRST + 1} rows -> {len(ROWS)} rows (rows below moved by {K})')
