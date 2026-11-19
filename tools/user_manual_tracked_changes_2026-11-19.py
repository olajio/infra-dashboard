"""Tracked-change edits to the unpacked copy of the MIM user manual (word/document.xml). Author 'Claude'."""
import re
import sys
from xml.sax.saxutils import escape

DOC = sys.argv[1] + '/word/document.xml'
x = open(DOC, encoding='utf-8').read()
AUTH, DATE = 'Claude', '2026-11-19T00:00:00Z'
_id = [9000]


def nid():
    _id[0] += 1
    return _id[0]


def attrs():
    return f'w:id="{nid()}" w:author="{AUTH}" w:date="{DATE}"'


def text_of(xml):
    return ''.join(re.findall(r'<w:t(?: [^>]*)?>([^<]*)</w:t>', xml))


def strip_ids(xml):
    return re.sub(r' w14:(?:paraId|textId)="[^"]*"', '', xml)


def bold_rpr(rpr):
    if '<w:b/>' in rpr:
        return rpr
    m = re.search(r'<w:rFonts[^>]*/>', rpr)
    if m:
        return rpr[:m.end()] + '<w:b/><w:bCs/>' + rpr[m.end():]
    return rpr.replace('<w:rPr>', '<w:rPr><w:b/><w:bCs/>', 1)


def plain_rpr(rpr):
    return rpr.replace('<w:b/>', '').replace('<w:bCs/>', '')


def ins_runs(text, rpr):
    """Inserted runs; **...** = bold."""
    out = []
    for k, seg in enumerate(re.split(r'\*\*', text)):
        if not seg:
            continue
        r = bold_rpr(rpr) if k % 2 else plain_rpr(rpr)
        out.append(f'<w:r>{r}<w:t xml:space="preserve">{escape(seg)}</w:t></w:r>')
    return f'<w:ins {attrs()}>' + ''.join(out) + '</w:ins>'


def first_rpr(p):
    m = re.search(r'<w:r>(<w:rPr>.*?</w:rPr>)', p, re.S)
    return m.group(1) if m else '<w:rPr/>'


def del_runs(p):
    """Wrap every run of paragraph p (outside pPr) in w:del."""
    def one(m):
        r = m.group(0).replace('<w:t>', '<w:delText>').replace('<w:t xml:space="preserve">', '<w:delText xml:space="preserve">')
        r = r.replace('</w:t>', '</w:delText>')
        return f'<w:del {attrs()}>{r}</w:del>'
    head_end = p.find('</w:pPr>') + len('</w:pPr>') if '</w:pPr>' in p else p.find('>') + 1
    return p[:head_end] + re.sub(r'<w:r>.*?</w:r>|<w:r [^>]*>.*?</w:r>', one, p[head_end:], flags=re.S)


def mark_para(p, kind):
    """Mark the paragraph mark as inserted / deleted."""
    mark = f'<w:{kind} {attrs()}/>'
    if '<w:pPr>' not in p:
        p = re.sub(r'(<w:p(?: [^>]*)?>)', r'\1<w:pPr></w:pPr>', p, count=1)
    ppr = re.search(r'<w:pPr>.*?</w:pPr>', p, re.S).group(0)
    if re.search(r'<w:rPr>(?:(?!</w:pPr>).)*</w:rPr>\s*</w:pPr>', ppr, re.S):
        i = ppr.rfind('<w:rPr>')   # the paragraph-mark rPr is the last rPr in pPr
        new = ppr[:i + 7] + mark + ppr[i + 7:]
    else:
        new = ppr.replace('</w:pPr>', f'<w:rPr>{mark}</w:rPr></w:pPr>')
    return p.replace(ppr, new, 1)


def find_para(anchor, start=0):
    """Body text only: an anchor that also appears in the table of contents is searched from its last occurrence."""
    i = x.rfind(anchor) if anchor in LAST else x.find(anchor, start)
    assert i >= 0, anchor
    a = max(x.rfind('<w:p ', 0, i), x.rfind('<w:p>', 0, i))
    b = x.find('</w:p>', i) + 6
    return a, b


def replace_para(anchor, new_text):
    global x
    a, b = find_para(anchor)
    p = x[a:b]
    rpr = first_rpr(p)
    p2 = del_runs(p)
    p2 = p2[:-6] + ins_runs(new_text, rpr) + '</w:p>'
    x = x[:a] + p2 + x[b:]


def append_to_para(anchor, add_text):
    global x
    a, b = find_para(anchor)
    p = x[a:b]
    rpr = first_rpr(p)
    x = x[:a] + p[:-6] + ins_runs(add_text, rpr) + '</w:p>' + x[b:]


def new_para_like(template_p, text):
    p = strip_ids(template_p)
    ppr = re.search(r'<w:pPr>.*?</w:pPr>', p, re.S)
    rpr = first_rpr(p)
    head = re.match(r'<w:p(?: [^>]*)?>', p).group(0)
    np = head + (ppr.group(0) if ppr else '') + ins_runs(text, rpr) + '</w:p>'
    return mark_para(np, 'ins')


def insert_paras_before(anchor, template_anchor, texts):
    global x
    ta, tb = find_para(template_anchor)
    tmpl = x[ta:tb]
    new = ''.join(new_para_like(tmpl, t) if isinstance(t, str) else new_para_like(x[slice(*find_para(t[0]))], t[1]) for t in texts)
    a, _ = find_para(anchor)
    x = x[:a] + new + x[a:]


def row_containing(anchor, start=0):
    i = x.find(anchor, start)
    assert i >= 0, anchor
    a = x.rfind('<w:tr ', 0, i)
    if x.rfind('<w:tr>', 0, i) > a:
        a = x.rfind('<w:tr>', 0, i)
    b = x.find('</w:tr>', i) + 7
    return a, b


def cells(row):
    return list(re.finditer(r'<w:tc>.*?</w:tc>', row, re.S))


def set_cell(anchor_row, col, new_text, start=0):
    global x
    a, b = row_containing(anchor_row, start)
    row = x[a:b]
    c = cells(row)[col]
    cell = c.group(0)
    pm = re.search(r'<w:p[ >].*?</w:p>', cell, re.S)
    p = pm.group(0)
    rpr = first_rpr(p)
    p2 = del_runs(p)[:-6] + ins_runs(new_text, rpr) + '</w:p>'
    cell2 = cell[:pm.start()] + p2 + cell[pm.end():]
    row2 = row[:c.start()] + cell2 + row[c.end():]
    x = x[:a] + row2 + x[b:]


def tr_mark(row, kind):
    mark = f'<w:{kind} {attrs()}/>'
    if '<w:trPr>' in row:
        return row.replace('</w:trPr>', mark + '</w:trPr>', 1)
    return re.sub(r'(<w:tr(?: [^>]*)?>)', r'\1<w:trPr>' + mark + '</w:trPr>', row, count=1)


def delete_row(anchor, start=0):
    global x
    a, b = row_containing(anchor, start)
    row = x[a:b]
    row = re.sub(r'<w:p[ >].*?</w:p>', lambda m: mark_para(del_runs(m.group(0)), 'del'), row, flags=re.S)
    x = x[:a] + tr_mark(row, 'del') + x[b:]


def new_row(template_row, texts):
    row = strip_ids(template_row)
    cs = cells(row)
    assert len(cs) == len(texts), (len(cs), texts)
    out, prev = [], 0
    for c, t in zip(cs, texts):
        cell = c.group(0)
        pm = re.search(r'<w:p[ >].*?</w:p>', cell, re.S)
        p = pm.group(0)
        rpr = first_rpr(p)
        if '<w:b/>' in rpr and not t.startswith('**'):
            rpr = plain_rpr(rpr)
        head = re.match(r'<w:p(?: [^>]*)?>', p).group(0)
        ppr = re.search(r'<w:pPr>.*?</w:pPr>', p, re.S)
        np = mark_para(head + (ppr.group(0) if ppr else '') + ins_runs(t, rpr) + '</w:p>', 'ins')
        # keep only the first paragraph of the cell
        cell2 = cell[:pm.start()] + np + re.sub(r'<w:p[ >].*?</w:p>', '', cell[pm.end():], flags=re.S)
        out.append(row[prev:c.start()] + cell2)
        prev = c.end()
    out.append(row[prev:])
    return tr_mark(''.join(out), 'ins')


def insert_rows_after(anchor_row, template_anchor, rows, start=0):
    global x
    ta, tb = row_containing(template_anchor, start)
    tmpl = x[ta:tb]
    a, b = row_containing(anchor_row, start)
    x = x[:b] + ''.join(new_row(tmpl, r) for r in rows) + x[b:]


LAST = {'5.3.1 Dashboard Links', '6. Troubleshooting Guide', '5.3 MIM Dashboard'}
S53 = x.rfind('5.3 MIM Dashboard')

# ---------- A1 ----------
replace_para('Provides a quick overview of active incidents and alerts',
             'Provides a quick overview of the active P1, P2 and P3 incidents and of the open alerts that have no '
             'incident, so the MIM team sees what needs attention now. Tiles count the active incidents by priority and '
             'show the P1 MTTR of the last 90 days; the table lists every active incident with its age, owners and user '
             'impact; the chart shows how quickly incidents were resolved against their targets (P1 4 h, P2 8 h, P3 24 h).')

# ---------- A2: section 1 table ----------
set_cell('Every P1, every P2 open longer than 8 h', 1,
         'Every active P1, P2 and P3 in one number, with a strip by priority. **Green at 0**')
set_cell('Active P1, P2 over 8 h, P3 over 24 h', 0, 'Active P1, Active P2, Active P3')
set_cell('Active P1, P2 over 8 h, P3 over 24 h', 1,
         'The same incidents, by priority, whatever their age. On Hold P1s count; On Hold P2s and P3s do not. Green and '
         '"All clear" at 0; "Needs action" in the priority colour above 0')
insert_rows_after('Active P1, P2 over 8 h, P3 over 24 h', 'Needs attention now', [[
    'P1 MTTR (90 days)',
    'Median time to resolve of the P1s resolved in the last 90 days, from when each became a P1, with the count, the '
    'average and how many were within the 4 h target. **Red** above 4 h, **green** at or under', 'Always']], start=S53)
set_cell('Open Netcool alerts on production CIs with no open incident, by severity', 1,
         'Open Netcool alerts on production CIs with no open incident, by severity (Critical, Major, other): possible '
         'blind spots. Follows the Incident / CI controls')
set_cell('Active Incidents (P1 · P2 over 8 h · P3 over 24 h)', 0, 'Active Incidents (P1 · P2 · P3)')
set_cell('Active Incidents (P1 · P2 over 8 h · P3 over 24 h)', 1,
         'The incidents behind the tiles (only the priorities picked in **Priorities**): priority, CI, state, opened, '
         '**Age**, **Time as P1 / Duration (h)**, **Linked incidents**, assignment group, assignee, group manager (with '
         'emails), description. Longest first. Click an incident to open it in ServiceNow')
set_cell('Average age so far of the active incidents opened each day', 1,
         'How quickly **resolved** incidents were resolved, for each of the last 30 days: each point is the median of the '
         'incidents resolved in the 7 days up to that day. P1 = MTTR (from when it became a P1); P2 and P3 = Duration '
         '(from opened). Dashed lines: targets P1 4 h, P2 8 h, P3 24 h')
delete_row('Open Netcool alerts on CIs with no open incident, Critical first, last 24 h')

NOTE_TMPL = 'Provides a quick overview of'  # body paragraph style (Segoe UI 10.5)
insert_paras_before('Investigate the CI', NOTE_TMPL, [
    '**Time as P1 / Duration:** for a P1, hours since it became a P1 (MTTR so far); for a P2 or P3, hours since it was '
    'opened. **Linked incidents:** incidents that name this one as their parent: the user impact of a P1.',
    'The SLA column was removed on 13 Nov; MIM reports P1 MTTR and P2 / P3 Duration instead of the ServiceNow SLAs. A '
    'resolved incident stays in the Time to Resolve chart for 7 days, so a P1 line can show while no P1 is open.'])

# ---------- A3: section 2 table ----------
s2 = x.find('Investigate the CI')
set_cell('One row per active incident on the CI', 0, 'Escalation Channel')
set_cell('One row per active incident on the CI', 1,
         '**Who to call.** One row per active P1, P2 or P3 incident on the CI (only the priorities picked in '
         '**Priorities**): priority, **state**, **when opened**, **age**, CI class and environment, assignment group, '
         'assignee and group manager (with emails). With a CI and no incident, one row with the CI\'s owners')
insert_rows_after('One row per active P1, P2 or P3 incident on the CI', 'Changes in the Last 7 Days on this CI', [[
    'Open Alerts with No Incident',
    'Open Netcool alerts (last 24 h) on CIs with no open incident, Critical first. **With an incident or CI picked:** '
    'only alerts on that CI and on CIs linked to it in the CMDB', 'Always']], start=s2)
delete_row('Netcool alerts on the CI, last 7 days: Open or Cleared')

# ---------- A4: Time Selector ----------
append_to_para('Defines the time range used by all dashboard panels',
               ' On the Major Incident Management dashboard, most panels use their own fixed time window, shown as a '
               'badge on the panel (for example "Last 7 days"); changing the time selector does not change those panels.')

# ---------- B1: controls, before the KPI definitions; renumber that heading ----------
replace_para('5.3 Major Incident Management Dashboard - KPI Definitions',
             '5.3.3 Major Incident Management Dashboard - KPI Definitions')
H3 = '5.3.1 Dashboard Links'
insert_paras_before('5.3.3 Major Incident Management', NOTE_TMPL, [
    (H3, '5.3.2 Using the MIM Controls'),
    'Pick an **Incident** or a **CI** in the top bar first: sections 2 and 3 follow that pick and stay mostly empty '
    'until one is made (that is expected). To start again: More (…) → Reset changes.'])
# controls table: a copy of the section 3 table (3 columns), header + rows, all inserted
t3a = x.rfind('<w:tbl>', 0, x.find('Traffic light of the monitored applications'))
t3b = x.find('</w:tbl>', t3a) + 8
tbl = x[t3a:t3b]
rows = list(re.finditer(r'<w:tr[ >].*?</w:tr>', tbl, re.S))
hdr, body = rows[0].group(0), rows[1].group(0)
CTRL = [['**Control**', '**What it does**', '**Default**'],
        ['Priorities (top bar)', 'Multi-select: which priorities Active Incidents, Escalation Channel and the Time to '
         'Resolve chart show', 'P1, P2, P3'],
        ['Incident (top bar)', 'The incident to investigate (INC number · CI); picking one fills sections 2 and 3 with '
         'its CI', '(all incidents)'],
        ['CI (top bar)', 'A CI to investigate without an incident', '(no CI selected)'],
        ['Monitored application (top bar)', 'Limits the application panels to the monitored applications, or one of '
         'them', '(all monitored applications)'],
        ['Server, Application, Service (section 3)', 'The server for the health panels, one application for Services of '
         'the Application, one service for Upstream / Service health / Downstream', '(none)'],
        ['Health window (section 3)', 'How far back the health panels look: 15 minutes to 7 days', '24 hours']]
new_tbl = tbl[:rows[0].start()] + new_row(hdr, CTRL[0]) + ''.join(new_row(body, r) for r in CTRL[1:]) + tbl[rows[-1].end():]
new_tbl = strip_ids(new_tbl)
anchor_i = x.find('5.3.3 Major Incident Management')
pa = max(x.rfind('<w:p ', 0, anchor_i), x.rfind('<w:p>', 0, anchor_i))
x = x[:pa] + new_tbl + x[pa:]

# ---------- B2: Dashboard Links and Future Releases, after the section 3 table ----------
H4 = 'Investigate the CI'
insert_paras_before('For detailed View about each panel', NOTE_TMPL, [
    (H4, 'Dashboard Links'),
    '**Related Dashboards:** Executive (In Progress), Portfolio, Application Operations, Major Incident Management, '
    'Infra Overview. Each link opens in a new tab.',
    (H4, 'Future Releases'),
    '**Next Release Roadmap:** data still to come, such as user impact from the ServiceNow user base and RUM, MTTR with '
    'the MIM team\'s Outage adjustments, clickable alerts, the PBA flag and telemetry for every monitored application. '
    '**Predictive & AI Insights:** AI incident summary, change and alert correlation, breach risk, anomaly detection '
    'and blast radius.'])

# ---------- C4: the personal OneDrive link (two Heading 1 paragraphs) -> one normal paragraph ----------
for anchor in ('For detailed View about each panel', 'Refer to user Manual:'):
    a, b = find_para(anchor)
    x = x[:a] + mark_para(del_runs(x[a:b]), 'del') + x[b:]
insert_paras_before('6. Troubleshooting Guide', NOTE_TMPL, [
    'For more detail about each panel, see the MIM V5 user manual (shared copy on the team SharePoint).'])

# ---------- B3: glossary ----------
insert_rows_after('Kibana index pattern that panels query', 'Kibana index pattern that panels query', [
    ['MIM', 'Major Incident Management'],
    ['P1 / P2 / P3', 'ServiceNow incident priority; targets P1 4 h, P2 8 h, P3 24 h'],
    ['MTTR', 'Mean / median time to resolve; for a P1, from when the incident became a P1 to resolved'],
    ['Duration', 'For a P2 or P3, time from opened to resolved (or to now while open)'],
    ['Linked incidents', 'Incidents that name another incident as their parent'],
    ['Netcool', 'IBM Netcool/OMNIbus, the source of the infrastructure alerts'],
    ['CMDB', 'ServiceNow configuration management database (CIs and their relationships)']])

# ---------- B4: troubleshooting ----------
insert_rows_after('Telemetry ingestion delay, agent issue, or pipeline failure', 'Telemetry ingestion delay, agent issue', [
    ['A control is missing, or panels show "Unknown query parameter" after a dashboard update',
     'Kibana re-applies unsaved control picks from before the update', 'More (…) → Reset changes'],
    ['Application Health / Services of the Application show "Cannot use field … due to ambiguities"',
     'A field in the CMDB application list (cmdb_with_apm_flag) changed type',
     'Report it to the dashboard team (fixed 17–18 Nov for the fields seen so far)'],
    ['A P1 line shows on the Time to Resolve chart while no P1 is open',
     'The chart shows resolved incidents; each stays in the 7-day window for a week',
     'Expected; see the P1 MTTR (90 days) tile for the P1 figure'],
    ['Sections 2 and 3 of MIM are empty', 'No Incident or CI picked', 'Pick one in the top bar']])

# ---------- B5: FAQ ----------
FAQ_ANCHOR = 'Missing data'
fi = x.find('7. Frequently Asked Questions')
insert_rows_after(FAQ_ANCHOR, FAQ_ANCHOR, [
    ['Why does a P1 line show when there is no open P1?',
     'The Time to Resolve chart shows resolved incidents, and each stays in the 7-day window for a week.'],
    ['How is P1 MTTR calculated?',
     'From when the incident became a P1 (ServiceNow incident timeline) to resolved; the opened time if it was opened '
     'as a P1. The MIM team\'s manual Outage adjustments are not included yet.'],
    ['Why does the time picker not change the MIM panels?',
     'Most MIM panels use their own fixed window, shown as a badge on the panel.'],
    ['Why are P3 incidents shown?', 'For the demo; MIM may cover P1 and P2 only later.']], start=fi)

# ---------- B6: catalogue ----------
insert_rows_after('Provides real-time visibility into active incidents', 'Provides real-time visibility into active incidents', [
    ['Infrastructure Overview', 'Infrastructure Teams, NOC',
     'Landing page for infrastructure: domain status, active incidents, alerts and changes, with links to the detailed '
     'infrastructure dashboards.'],
    ['Executive Dashboard', 'Senior Leadership', 'In progress.']])

# ---------- C5: version history ----------
insert_rows_after('Initial baseline for knowledge transfer', 'Initial baseline for knowledge transfer', [
    ['1.1', '19 Nov 2026', 'TCS Observability Team',
     'MIM section updated to MIM V5: P3, Priorities control, Age, P1 MTTR, Dashboard Links, Future Releases; troubleshooting, glossary and FAQ']])

open(DOC, 'w', encoding='utf-8').write(x)
print('ok, tracked ids up to', _id[0])
