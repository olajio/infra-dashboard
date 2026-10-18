"""MIM V3: CI control lists every monitored CI; new Server and Health window controls; section 2 health panels follow
the chosen server and the Health window (18 Oct 2026, phase 1 of MIM-V3-BUILD-PLAN-SERVER-HEALTH-WINDOW.md).

Usage: mim_v3_patch_2026-10-18k.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-16j.py)

Controls, in order: Incident · CI · Server · Health window · Service · Application
- CI: CIs on P1-P3 incidents (last 31 days), plus every production server that sent Metricbeat data in the last day.
- Server (new): "(no server selected)" plus every production server that sent Metricbeat data in the last day.
- Health window (new): 15 minutes · 30 minutes · 1 hour · 6 hours · 8 hours · 24 hours (default) · 3 days · 7 days.

Which server the health panels show:
  1. the Incident's CI, if it is a server;  2. the CI control's value, if it is a server;  3. the Server control's value.
  (4. automatic servers of an application CI: added in the next patch.)
"Is a server" = its CMDB class is a server class (the Server View classes) or it sent CPU metrics in the Health window.

Panels that follow the chosen server and the Health window: Server Health (now one row per server), Middleware
Health, Database Health, Process Health, Synthetics Health, Errors from the Logs, Applications on this CI.
Alerts on this CI follows the chosen server too (plus the CI itself) but keeps its fixed 7 days.
These panels read the CMDB links, so their panel range is "Last 5 years"; the data window is set in the query from the
Health window control, and Elasticsearch applies it directly (an index range query).
"""
import copy
import json
import sys
import uuid

SRC, OUT = sys.argv[1:3]
NS = uuid.UUID('5b1c7a8e-29a4-4a52-9d5e-6f1f3f0f0d18')
uid = lambda name: str(uuid.uuid5(NS, name))

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = lambda t: next(p for p in panels if title(p) == t)
st = lambda p: p['embeddableConfig']['attributes']['state']
layer = lambda p: next(iter(st(p)['datasourceStates']['textBased']['layers'].values()))

# ------------------------------------------------------------------ shared expressions
INC = 'CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))'
CIV = 'CASE(?ci == "(no CI selected)", "", ?ci)'
SRV = 'CASE(?server == "(no server selected)", "", ?server)'
V3 = lambda e: f'{e}, TO_UPPER({e}), TO_LOWER({e})'
CANDS = f'({V3(INC)}, {V3(CIV)}, {V3(SRV)})'
FQDN_CANDS = '(' + ', '.join(f'CONCAT({e}, ".cna.com")' for e in (INC, CIV, SRV)) + ')'   # "<name>.cna.com"
HW = ('NOW() - TO_TIMEDURATION(CASE(?health_window == "3 days", "72 hours", ?health_window == "7 days", "168 hours", '
      '?health_window))')
SEL = '(CASE(?incident == "(all incidents)", ?ci, SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)))'
CPU = '.ds-metrics-system.cpu-default*'
REL = 'cmdb-ci-relations*'
PROD_OR_BLANK = lambda e: f'({e} IS NULL OR {e} IN ("", "null") OR TO_LOWER({e}) LIKE "prod*" OR TO_LOWER({e}) LIKE "prd*")'
q = layer(P('Server View'))['query']['esql']
SERVER_CLASSES = q.split('cls IN (', 1)[1].split(')', 1)[0]
SERVER_KIND = 'CASE(cls == ' + q.split('kind = CASE(cls == ', 1)[1].split(', cls)', 1)[0] + ', cls)'


def resolve(indices, match_fields, data_filter='true', window=HW):
    """FROM ... | the precedence: leaves the panel's own data rows for the chosen server, and `target` (lower case).

    indices       the panel's data indices (the CPU index and the CMDB graph are added for the server checks)
    match_fields  fields of the data rows that hold the server name (pushed down as term filters)
    data_filter   extra condition for a row to count as panel data
    """
    extra = [i for i in (CPU, REL) if i not in indices]
    match = ' OR '.join(f'{f} IN {CANDS}' for f in match_fields + (['ci.name'] if 'ci.name' not in match_fields else []))
    return f"""FROM {', '.join(indices + extra)} METADATA _index
| WHERE (@timestamp >= {window} AND ({match})) OR parent.name IN {CANDS} OR child.name IN {CANDS}
| EVAL is_rel = _index LIKE "*relations*", is_cpu = _index LIKE "*metrics-system.cpu*"
| EVAL inc_l = TO_LOWER({INC}), ci_l = TO_LOWER({CIV}), srv_l = TO_LOWER({SRV}),
       p_l = TO_LOWER(TO_STRING(parent.name)), c_l = TO_LOWER(TO_STRING(child.name)),
       p_srv = TO_STRING(parent.class) IN ({SERVER_CLASSES}), c_srv = TO_STRING(child.class) IN ({SERVER_CLASSES}),
       cpu_l = CASE(is_cpu, TO_LOWER(TO_STRING(ci.name)))
| EVAL inc_hit = CASE(inc_l == "", 0, is_rel AND ((p_l == inc_l AND p_srv) OR (c_l == inc_l AND c_srv)), 1, cpu_l == inc_l, 1, 0),
       ci_hit = CASE(ci_l == "", 0, is_rel AND ((p_l == ci_l AND p_srv) OR (c_l == ci_l AND c_srv)), 1, cpu_l == ci_l, 1, 0)
| INLINE STATS inc_is_server = MAX(inc_hit), ci_is_server = MAX(ci_hit)
| EVAL target = CASE(inc_is_server == 1, inc_l, ci_is_server == 1, ci_l, srv_l != "", srv_l)
| EVAL is_data = NOT is_rel AND ({data_filter})"""


def set_query(p, query, indices, time_range={'from': 'now-5y', 'to': 'now'}):
    L = layer(p)
    L['query'] = {'esql': query}
    st(p)['query'] = {'esql': query}
    idx = ','.join(indices)
    L['timeField'] = '@timestamp'
    for v in st(p)['adHocDataViews'].values():
        v.update(title=idx, name=idx, timeFieldName='@timestamp')
    for r in st(p)['datasourceStates']['textBased']['indexPatternRefs']:
        r.update(title=idx, timeField='@timestamp')
    p['embeddableConfig']['time_range'] = dict(time_range)


def after_first_where(qry):
    """The original query from its second pipe on (drops FROM and the first WHERE that matched the CI)."""
    parts = qry.split('\n| ')
    assert parts[0].startswith('FROM ') and parts[1].startswith('WHERE '), qry[:200]
    return parts[1], '\n| '.join(parts[2:])


WINDOW_NOTE = (' Which server: the Incident\'s CI if it is a server, else the CI control\'s value if it is a server, else '
               'the Server control\'s value. Data window: the Health window control (default 24 hours), not the time '
               'picker; the panel shows "Last 5 years" only because it also reads the CMDB links.')

# ------------------------------------------------------------------ Middleware / Database / Process / Logs (ci.name)
for t in ('Middleware Health', 'Database Health', 'Process Health', 'Errors from the Logs'):
    p = P(t)
    orig = layer(p)['query']['esql']
    from_line = orig.split('\n', 1)[0]
    indices = [i.strip() for i in from_line[5:].split(' METADATA')[0].split(',')]
    first_where, rest = after_first_where(orig)
    extra = ''
    if t == 'Process Health':     # it also kept only Windows services / labelled processes
        extra = first_where.split(') AND ', 1)[1]
    data_filter = (f'NOT is_cpu OR {"true" if CPU in indices else "false"}')
    head = resolve(indices, ['ci.name'], data_filter)
    keep = f'| WHERE is_data AND target IS NOT NULL AND TO_LOWER(TO_STRING(ci.name)) == target' + (f' AND {extra}' if extra else '')
    set_query(p, head + '\n' + keep + '\n| ' + rest, indices + [CPU, REL])
    ec = p['embeddableConfig']
    ec['description'] = ec['description'].replace('Follows the Incident / CI controls and the time picker.', '') \
                                         .replace('Follows the CI control and the time picker.', '').rstrip() + WINDOW_NOTE

# ------------------------------------------------------------------ Applications on this CI (APM host.name)
p = P('Applications on this CI')
orig = layer(p)['query']['esql']
first_where, rest = after_first_where(orig)
apm = ['metrics-apm.internal-*']
head = resolve(apm, ['host.name'], 'NOT is_cpu')
set_query(p, head + '\n| WHERE is_data AND target IS NOT NULL AND TO_LOWER(TO_STRING(host.name)) == target\n| ' + rest,
          apm + [CPU, REL])
ec = p['embeddableConfig']
ec['description'] = ('APM services that sent data from the chosen server in the Health window, most recent first, with '
                     'their environment. Production services only (environment starting "prod" or "prd"). The '
                     'applications linked to the CI in the CMDB are in "Applications related to this CI".' + WINDOW_NOTE)

# ------------------------------------------------------------------ Synthetics Health (ci.name or URL domain)
p = P('Synthetics Health')
orig = layer(p)['query']['esql']
first_where, rest = after_first_where(orig)
syn = ['synthetics-*']
head = resolve(syn, ['ci.name', 'url.domain'], 'NOT is_cpu')
keep = ('| WHERE is_data AND target IS NOT NULL AND summary.status IS NOT NULL AND (TO_LOWER(TO_STRING(ci.name)) == target '
        'OR TO_LOWER(TO_STRING(url.domain)) == target OR TO_LOWER(TO_STRING(url.domain)) == CONCAT(target, ".cna.com"))')
# the URL may be the server's FQDN: match "<server>.cna.com" too
head = head.replace(f'url.domain IN {CANDS}', f'url.domain IN {CANDS} OR url.domain IN {FQDN_CANDS}', 1)
set_query(p, head + '\n' + keep + '\n| ' + rest, syn + [CPU, REL])
ec = p['embeddableConfig']
ec['description'] = ec['description'].replace('Follows the CI control and the time picker.', '').rstrip() + WINDOW_NOTE

# ------------------------------------------------------------------ Server Health: one row per server
p = P('Server Health')
template = copy.deepcopy(P('Middleware Health'))           # a table panel to start from
template['gridData'] = p['gridData']
template['panelIndex'] = p['panelIndex']
template['embeddableConfig']['title'] = template['embeddableConfig']['attributes']['title'] = 'Server Health'
template['embeddableConfig'].pop('drilldowns', None)
srv_idx = ['.ds-metrics-system.cpu-default*', '.ds-metrics-system.memory-default*', '.ds-metrics-system.filesystem-default*']
head = resolve(srv_idx, ['ci.name'], 'true')
Q = head + f"""
| WHERE target IS NOT NULL AND ((is_data AND TO_LOWER(TO_STRING(ci.name)) == target)
     OR (is_rel AND (p_l == target OR c_l == target)))
| EVAL srv = CASE(is_data, TO_STRING(ci.name), p_l == target, TO_STRING(parent.name), TO_STRING(child.name))
| STATS cpu = PERCENTILE(system.cpu.total.norm.pct, 90), mem = MAX(system.memory.actual.used.pct),
        disk = MAX(system.filesystem.used.pct), last_seen = MAX(CASE(is_data, @timestamp)), names = VALUES(srv)
  BY server_key = TO_LOWER(srv)
| EVAL server = MV_FIRST(names), silent_min = DATE_DIFF("minutes", last_seen, NOW())
| EVAL status = CASE(last_seen IS NULL, "No data in window", silent_min > 10, "Silent", "Reporting"),
       cpu_p90 = ROUND(cpu * 100, 1), mem_peak = ROUND(mem * 100, 1), disk_max = ROUND(disk * 100, 1),
       rank = CASE(last_seen IS NULL, 1, silent_min > 10, 2, 3)
| SORT rank ASC, server ASC
| KEEP server, status, silent_min, cpu_p90, mem_peak, disk_max"""
num = lambda cid, label, suffix: {'columnId': cid, 'fieldName': cid, 'label': label, 'customLabel': True,
                                  'meta': {'type': 'number', 'esType': 'double'}, 'inMetricDimension': True,
                                  'params': {'format': {'id': 'number', 'params': {'decimals': 1, 'suffix': suffix}}}}
txt = lambda cid, label: {'columnId': cid, 'fieldName': cid, 'label': label, 'customLabel': True,
                          'meta': {'type': 'string', 'esType': 'keyword'}, 'inMetricDimension': True}
cols = [txt('server', 'Server'), txt('status', 'Status'), num('silent_min', 'Min. ago', ''),
        num('cpu_p90', 'CPU p90', ' %'), num('mem_peak', 'Mem peak', ' %'), num('disk_max', 'Disk max', ' %')]
L = layer(template)
L['columns'] = cols
L['allColumns'] = copy.deepcopy(cols)
RED, AMBER, GREEN, GREY = '#d6453d', '#c98a0b', '#1f9e6b', '#8a96a8'
status_col = next(c for c in st(template)['visualization']['columns'] if c.get('colorMode') == 'badge')
status_col = copy.deepcopy(status_col)
status_col['columnId'] = 'status'
status_col['colorMapping']['assignments'] = [
    {'rules': [{'type': 'match', 'pattern': pat, 'matchEntireWord': True, 'matchCase': True}],
     'color': {'type': 'colorCode', 'colorCode': col}, 'touched': True}
    for pat, col in (('No data in window', RED), ('Silent', RED), ('Reporting', GREEN))]
pct = lambda cid: {'columnId': cid, 'isTransposed': False, 'isMetric': True, 'alignment': 'right', 'width': 58,
                   'colorMode': 'text', 'palette': {'name': 'custom', 'type': 'palette', 'params': {
                       'name': 'custom', 'reverse': False, 'rangeType': 'number', 'rangeMin': 0, 'rangeMax': 101,
                       'progression': 'fixed', 'continuity': 'all', 'steps': 3, 'maxSteps': 5,
                       'stops': [{'color': GREEN, 'stop': 80}, {'color': AMBER, 'stop': 90}, {'color': RED, 'stop': 101}],
                       'colorStops': [{'color': GREEN, 'stop': 0}, {'color': AMBER, 'stop': 80}, {'color': RED, 'stop': 90}]}}}
st(template)['visualization']['columns'] = [
    {'columnId': 'server', 'isTransposed': False, 'isMetric': True, 'alignment': 'left', 'width': 92},
    dict(status_col, width=100),
    {'columnId': 'silent_min', 'isTransposed': False, 'isMetric': True, 'alignment': 'right', 'width': 55},
    pct('cpu_p90'), pct('mem_peak'), pct('disk_max')]
set_query(template, Q, srv_idx + [REL])
template['embeddableConfig']['description'] = (
    'The chosen server\'s own telemetry, one row per server, problems first: Status (Reporting; Silent = no data for '
    '10 minutes; No data in window = a server with no data at all in the Health window), minutes since its last data, '
    'CPU 90th percentile, peak memory and its fullest disk (amber from 80 %, red from 90 %). For the whole estate, open '
    'the Infra Dashboard (section 4).' + WINDOW_NOTE)
panels[panels.index(p)] = template

# ------------------------------------------------------------------ Alerts on this CI: chosen server too, 7 days
p = P('Alerts on this CI')
orig = layer(p)['query']['esql']
first_where, rest = after_first_where(orig)
NC, INCX = '.ds-bridge-alerts-netcool-default-*', 'servicenow-incidents-*'
NUM = 'CASE(?incident == "(all incidents)", "(all incidents)", SUBSTRING(?incident, 1, LOCATE(?incident, " · ") - 1))'
head = resolve([NC, INCX], ['ci.name', 'node'], 'NOT is_cpu', window='NOW() - 7 days')
head = head.replace(f'| WHERE (@timestamp >= NOW() - 7 days AND (',
                    f'| WHERE number == {NUM} OR ci.name == {SEL} OR node == CONCAT({SEL}, ".cna.com")\n     OR (@timestamp >= NOW() - 7 days AND (', 1)
head = head.replace(f'node IN {CANDS}', f'node IN {FQDN_CANDS}', 1)
keep = f"""| WHERE (is_data AND _index LIKE "*servicenow*" AND number == {NUM})
     OR (is_data AND _index LIKE "*netcool*" AND @timestamp >= NOW() - 7 days
         AND (ci.name == {SEL} OR node == CONCAT({SEL}, ".cna.com")
              OR (target IS NOT NULL AND (TO_LOWER(TO_STRING(ci.name)) == target OR TO_LOWER(TO_STRING(node)) == CONCAT(target, ".cna.com")))))"""
set_query(p, head + '\n' + keep + '\n| ' + rest, [NC, INCX, CPU, REL])
ec = p['embeddableConfig']
ec['description'] = ec['description'].replace(
    'Netcool alerts on the selected CI (matched on the CMDB CI, or on the node "<CI>.cna.com")',
    'Netcool alerts on the selected CI and on the chosen server (matched on the CMDB CI, or on the node "<name>.cna.com")') \
    + (' Which server: as in the health panels (the Incident\'s CI if it is a server, else the CI control\'s value if it is '
       'a server, else the Server control\'s value). Last 7 days (set in the query; the panel shows "Last 5 years" because '
       'it also reads the CMDB links), so the alert that triggered the incident stays visible.')

# ------------------------------------------------------------------ controls
ctl = A['pinned_panels']['panels']
by = {c['config']['title']: (k, c) for k, c in ctl.items()}
by['CI'][1]['config']['esql_query'] = f"""FROM servicenow-incidents-*, {CPU} METADATA _index
| WHERE (priority IN (1, 2, 3) AND opened_at >= NOW() - 31 days) OR @timestamp >= NOW() - 1 day
| EVAL from_inc = _index LIKE "*servicenow*"
| WHERE ci.name IS NOT NULL AND ((from_inc AND priority IN (1, 2, 3) AND opened_at >= NOW() - 31 days)
     OR (NOT from_inc AND {PROD_OR_BLANK("TO_STRING(ci.environment)")}))
| STATS cis = VALUES(TO_STRING(ci.name))
| EVAL ci = MV_APPEND("(no CI selected)", cis)
| MV_EXPAND ci
| EVAL ord = CASE(ci == "(no CI selected)", 0, 1)
| SORT ord ASC, ci ASC
| LIMIT 10000
| KEEP ci"""
server_ctl = copy.deepcopy(by['CI'][1])
server_ctl['config'].update(title='Server', variable_name='server', selected_options=['(no server selected)'],
                            esql_query=f"""FROM {CPU}
| WHERE @timestamp >= NOW() - 1 day AND ci.name IS NOT NULL AND {PROD_OR_BLANK("TO_STRING(ci.environment)")}
| STATS servers = VALUES(TO_STRING(ci.name))
| EVAL server = MV_APPEND("(no server selected)", servers)
| MV_EXPAND server
| EVAL ord = CASE(server == "(no server selected)", 0, 1)
| SORT ord ASC, server ASC
| LIMIT 10000
| KEEP server""")
server_ctl['width'] = 'medium'
window_ctl = copy.deepcopy(by['CI'][1])
window_ctl['config'].update(title='Health window', variable_name='health_window', selected_options=['24 hours'],
                            esql_query='ROW health_window = ["15 minutes", "30 minutes", "1 hour", "6 hours", "8 hours", '
                                       '"24 hours", "3 days", "7 days"]\n| MV_EXPAND health_window')
window_ctl['width'] = 'small'
order = ['Incident', 'CI', 'Server', 'Health window', 'Service', 'Application']
ctl[uid('control:server')] = server_ctl
ctl[uid('control:health_window')] = window_ctl
for k, c in ctl.items():
    c['order'] = order.index(c['config']['title'])

# ------------------------------------------------------------------ checks
s = json.dumps(panels)
assert s.count('?health_window') >= 8 and s.count('?server') >= 8
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{len(panels)} panels; controls: {[c["config"]["title"] for c in sorted(ctl.values(), key=lambda c: c["order"])]}')
