"""Patch MIM V3.ndjson in place for the suggestions2.txt round (14 Oct 2026).

Usage: patch_v3.py IN_NDJSON OUT_NDJSON
"""
import copy
import json
import re
import sys

SRC, OUT = sys.argv[1:3]
RED, AMBER, GREEN, GREY, BLUE = '#d6453d', '#c98a0b', '#1f9e6b', '#8a96a8', '#3987e5'
DEMO_USERS = 2500           # Users impacted: demo number until ATOS sends user counts
INFRA_URL = 'https://kibana-prod.gcp.cna.com/app/r/s/3A7f1'
CLOSED = '("Resolved", "Closed", "Canceled", "Cancelled")'
SEL_CI = '(CASE(?incident == "(all incidents)", ?ci, SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)))'

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = lambda t: next(p for p in panels if title(p) == t)
st = lambda p: p['embeddableConfig']['attributes']['state']
layer = lambda p: next(iter(st(p)['datasourceStates']['textBased']['layers'].values()))
SEC1, SEC2 = P('Active Incidents (P1 / P2)')['gridData']['sectionId'], P('Escalate')['gridData']['sectionId']


def set_query(p, q):
    layer(p)['query']['esql'] = q
    st(p)['query'] = {'esql': q}


def col(cid, label, typ='string', es='keyword', fmt=None):
    c = {'columnId': cid, 'fieldName': cid, 'label': label, 'customLabel': True, 'meta': {'type': typ, 'esType': es},
         'inMetricDimension': True}
    if fmt:
        c['params'] = {'format': fmt}
    return c


def set_columns(p, cols):
    layer(p)['columns'] = cols
    layer(p)['allColumns'] = copy.deepcopy(cols)


def exact(pairs, other=GREY):
    rule = lambda v: {'type': 'match', 'pattern': v, 'matchEntireWord': True, 'matchCase': True}
    return {'paletteId': 'default', 'colorMode': {'type': 'categorical'},
            'assignments': [{'rules': [rule(v)], 'color': {'type': 'colorCode', 'colorCode': c}, 'touched': True}
                            for v, c in pairs],
            'specialAssignments': [{'rules': [{'type': 'other'}], 'color': {'type': 'colorCode', 'colorCode': other},
                                    'touched': True}]}


CMDB_DD = copy.deepcopy(P('What this CI runs on')['embeddableConfig']['drilldowns'][0])

# ------------------------------------------------------------------ 1. Section 1: one Active P1 / P2 donut
ACTIVE_PRI = f'''FROM servicenow-incidents-*
| WHERE priority IN (1, 2) AND state_name NOT IN {CLOSED} AND number IS NOT NULL
| STATS pri = MIN(TO_INTEGER(priority)) BY number
| EVAL priority_label = CASE(pri == 1, "P1", "P2")
| STATS incidents = COUNT(*) BY priority_label
| SORT priority_label ASC'''
glance, mw = P('Active P1 / P2 at a Glance'), P('Middleware Health')
donut_attrs = copy.deepcopy(mw['embeddableConfig']['attributes'])
donut_attrs['title'] = 'Active P1 / P2'
donut_attrs['state']['adHocDataViews'] = copy.deepcopy(st(glance)['adHocDataViews'])
L = next(iter(donut_attrs['state']['datasourceStates']['textBased']['layers'].values()))
L['index'] = layer(glance)['index']
donut_attrs['state']['datasourceStates']['textBased'].pop('indexPatternRefs', None)
if 'indexPatternRefs' in st(glance)['datasourceStates']['textBased']:
    donut_attrs['state']['datasourceStates']['textBased']['indexPatternRefs'] = copy.deepcopy(
        st(glance)['datasourceStates']['textBased']['indexPatternRefs'])
glance['embeddableConfig']['attributes'] = donut_attrs
glance['embeddableConfig']['title'] = 'Active P1 / P2'
glance['embeddableConfig']['description'] = (
    'How many P1 and P2 incidents are active now (priority 1 or 2, state not Resolved, Closed, Canceled or Cancelled): '
    'P1 red, P2 amber, with the count on each slice and in the legend. Last 1 month (fixed); not narrowed by the '
    'Incident or CI controls.')
set_query(glance, ACTIVE_PRI)
set_columns(glance, [col('priority_label', 'Priority'),
                     col('incidents', 'Active incidents', 'number', 'long', {'id': 'number', 'params': {'decimals': 0}})])
v = st(glance)['visualization']['layers'][0]
v.update(primaryGroups=['priority_label'], metrics=['incidents'], numberDisplay='value', categoryDisplay='default',
         legendDisplay='show', legendPosition='right', legendStats=['value'], emptySizeRatio=0.5,
         colorMapping=exact([('P1', RED), ('P2', AMBER)]))

# ------------------------------------------------------------------ 2. Users impacted: a demo number
users = P('Users impacted')
spec = json.loads(users['embeddableConfig']['savedVis']['params']['spec'])
spec['data'][0]['values'] = [{'value': f'{DEMO_USERS:,}', 'detail': 'Demo value|real counts to come from ATOS',
                              'more': '', 'names_txt': 'Users of the impacted applications|(placeholder for the demo)',
                              'colour': BLUE}]
users['embeddableConfig']['savedVis']['params']['spec'] = json.dumps(spec, indent=2, ensure_ascii=False)
users['embeddableConfig']['description'] = (
    f'DEMO VALUE ({DEMO_USERS:,}) for presentations only. Will show how many users the active P1 / P2 incidents '
    'affect (the user base of the impacted applications) once ATOS ingests user counts into Elastic; there is no '
    'user-count field today on incidents, the CMDB enrichment or the CMDB dependency index.')

# section 1 row: donut, Applications impacted, Users impacted, trend
for t, (x, w) in {'Active P1 / P2': (0, 12), 'Applications impacted': (12, 8), 'Users impacted': (20, 8),
                  'P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)': (28, 20)}.items():
    P(t)['gridData'].update(x=x, w=w)

# ------------------------------------------------------------------ 3. remove the section 2 banner
panels.remove(P('How to use this section'))

# ------------------------------------------------------------------ 4. Middleware / Database Health: tables of components
proc = P('Process Health')


def components_table(p, tier, what):
    q = layer(p)['query']['esql']
    head = q[:q.index('| WHERE tier ==')]
    head = head.replace(' BY tier, component', ' BY ci.name, tier, component')
    set_query(p, head + f'''| WHERE tier == "{tier}"
| EVAL minutes_since = DATE_DIFF("minutes", last_ts, NOW()), rank = CASE(health == "Down", 1, 2)
| SORT rank ASC, component ASC
| LIMIT 100
| KEEP component, health, minutes_since, ci.name''')
    attrs = p['embeddableConfig']['attributes']
    lid = next(iter(attrs['state']['datasourceStates']['textBased']['layers']))
    vis = copy.deepcopy(st(proc)['visualization'])
    vis['layerId'] = lid
    vis['paging']['size'] = 6
    vis['columns'] = [
        {'columnId': 'component', 'isTransposed': False, 'isMetric': True, 'alignment': 'left', 'width': 150},
        {'columnId': 'health', 'isTransposed': False, 'isMetric': True, 'alignment': 'center', 'colorMode': 'badge',
         'palette': {'type': 'palette', 'name': 'default'}, 'colorMapping': exact([('Down', RED), ('Healthy', GREEN)]),
         'width': 76},
        {'columnId': 'minutes_since', 'isTransposed': False, 'isMetric': True, 'alignment': 'right', 'width': 62},
        {'columnId': 'ci.name', 'isTransposed': False, 'isMetric': False, 'alignment': 'left', 'width': 100}]
    attrs['state']['visualization'] = vis
    attrs['visualizationType'] = 'lnsDatatable'
    set_columns(p, [col('component', what), col('health', 'Status'),
                    col('minutes_since', 'Min. ago', 'number', 'long', {'id': 'number', 'params': {'decimals': 0}}),
                    col('ci.name', 'Server')])
    dd = copy.deepcopy(CMDB_DD)
    dd['label'] = 'Open the server in ServiceNow CMDB — use on the Server column'
    p['embeddableConfig']['drilldowns'] = [dd]


components_table(mw, 'mw', 'Middleware component')
mw['embeddableConfig']['description'] = (
    'Every middleware component on the selected CI with its status, Down first: processes labelled by the monitoring '
    'enrichment (IBM MQ queue managers, IBM HTTP Server, JBoss, WebSphere …) and Windows middleware services (IIS, MQ, '
    'Tomcat …). Down = stopped, or not reported for 10 minutes; Min. since seen = minutes since its last report. '
    'Server = the CI it runs on; click it to open the server in ServiceNow. Empty = no middleware monitored on this '
    'CI. Follows the Incident / CI controls and the time picker.')
db = P('Database Health')
components_table(db, 'db', 'Database')
db['embeddableConfig']['description'] = (
    'Every database on the selected CI with its status, Down first: SQL Server (from the SQL Server metrics), and '
    'database processes and Windows services (SQL Server, Oracle, Db2, PostgreSQL, MySQL …). Down = stopped, or not '
    'reported for 10 minutes; Min. since seen = minutes since its last report. Server = the CI it runs on; click it '
    'to open the server in ServiceNow. Empty = no database monitored on this CI. Follows the Incident / CI controls '
    'and the time picker.')

# ------------------------------------------------------------------ 5. Server Health: name the server on each tile
sh = P('Server Health')
q = layer(sh)['query']['esql']
q = q.replace('disk = MAX(system.filesystem.used.pct), last_seen = MAX(@timestamp)',
              'disk = MAX(system.filesystem.used.pct), last_seen = MAX(@timestamp), servers = VALUES(ci.name)')
q = q.replace('| KEEP label, value, rag_max', '| EVAL detail = CONCAT("server ", MV_FIRST(servers))\n| KEEP label, value, rag_max, detail')
assert 'servers = VALUES(ci.name)' in q and 'KEEP label, value, rag_max, detail' in q
set_query(sh, q)
layer(sh)['columns'].append(col('detail', ' '))
layer(sh)['allColumns'] = copy.deepcopy(layer(sh)['columns'])
st(sh)['visualization'].update(secondaryMetricAccessor='detail', secondaryLabel='')
sh['embeddableConfig'].pop('drilldowns', None)   # its click value (label) is computed: Kibana 9.5 blocks links on it
sh['embeddableConfig']['description'] = (
    'The selected CI\'s own server telemetry, with the server named on each tile: minutes since it last sent data (red '
    'after 10), CPU 90th percentile, peak memory and its fullest disk (amber from 80 %, red from 90 %). No tiles = the '
    'CI is not a monitored server. For the whole estate, open the Infra Dashboard (section 4). Follows the '
    'Incident / CI controls and the time picker.')

# ------------------------------------------------------------------ 6. Applications on this CI: APM services, last 7 days
apps = P('Applications on this CI')
set_query(apps, f'''FROM metrics-apm.internal-*
| WHERE host.name == {SEL_CI} OR host.name == TO_UPPER({SEL_CI})
| STATS last_seen = MAX(@timestamp), envs = VALUES(TO_STRING(service.environment)) BY application = TO_STRING(service.name)
| WHERE application IS NOT NULL
| EVAL mins = DATE_DIFF("minutes", last_seen, NOW())
| EVAL health = CASE(mins >= 1440, CONCAT(TO_STRING(mins / 1440), " d ago"), mins >= 60, CONCAT(TO_STRING(mins / 60), " h ago"),
                     CONCAT(TO_STRING(mins), " min ago")),
       source = "APM · runs on this server", type = COALESCE(MV_CONCAT(envs, ", "), "—")
| SORT last_seen DESC, application ASC
| KEEP application, health, source, type
| LIMIT 200''')
for c in layer(apps)['columns'] + layer(apps)['allColumns']:
    c['label'] = {'application': 'Application / service', 'health': 'Last data', 'source': 'Source',
                  'type': 'Environment'}.get(c['columnId'], c['label'])
st(apps)['adHocDataViews'] = {k: v for k, v in st(apps)['adHocDataViews'].items()}
for v_ in st(apps)['adHocDataViews'].values():
    v_['title'] = v_['name'] = 'metrics-apm.internal-*'
apps['embeddableConfig']['time_range'] = {'from': 'now-7d', 'to': 'now'}
apps['embeddableConfig']['description'] = (
    'APM services that sent data from the selected CI (the server they run on) in the last 7 days, most recent first, '
    'with their environment. The applications linked to the CI in the CMDB are in "Applications that depend on this '
    'CI" and "What this CI runs on". Last 7 days (fixed). Follows the Incident / CI controls.')

# ------------------------------------------------------------------ 7. Changes: last 7 days
chg = P('Changes in the Last 7 Days on this CI and Linked CIs')
chg['embeddableConfig']['title'] = chg['embeddableConfig']['attributes']['title'] = 'Changes in the Last 7 Days on this CI'
chg['embeddableConfig']['time_range'] = {'from': 'now-7d', 'to': 'now'}
d = chg['embeddableConfig']['description']
d = d[:d.index('Follows the Incident / CI controls.')] + (
    'Follows the Incident / CI controls. Last 7 days (fixed). Changes on linked CIs (its ESX host, cluster, switch '
    '…) appear only when their CMDB link was recorded in the same 7 days: ServiceNow stores a relation record only '
    'when it changes, so most links are older and not seen here.')
chg['embeddableConfig']['description'] = d

# ------------------------------------------------------------------ 8. Section 4: the links only
for t, md in {'SRE dashboard': '## 🛡️ [Applications Operations Dashboard ›](https://kibana-prod.gcp.cna.com/app/r/s/b4Jas)',
              'Infra dashboard': f'## 🖥️ [Infra Dashboard ›]({INFRA_URL})'}.items():
    p = P(t)
    old = p['embeddableConfig']['content']
    url = re.search(r'\]\((https://[^)]+)\)', old).group(1)
    p['embeddableConfig']['content'] = md.split('](')[0] + f']({url})'
    p['gridData']['h'] = 3

# ------------------------------------------------------------------ section 2 layout (banner removed)
LAYOUT2 = {'Escalate': (0, 0, 48, 6), 'Alerts on this CI': (0, 6, 48, 9),
           'Blast radius': (0, 15, 7, 11), 'Applications that depend on this CI': (7, 15, 21, 11),
           'What this CI runs on': (28, 15, 20, 11),
           'Middleware Health': (0, 26, 12, 10), 'Database Health': (12, 26, 11, 10), 'Server Health': (23, 26, 12, 10),
           'SLO Error Burn Rate': (35, 26, 13, 20),
           'Applications on this CI': (0, 36, 12, 10), 'Process Health': (12, 36, 11, 10),
           'Synthetics Health': (23, 36, 12, 10),
           'Errors from the Logs': (0, 46, 48, 10), 'Changes in the Last 7 Days on this CI': (0, 56, 48, 11)}
for t, (x, y, w, h) in LAYOUT2.items():
    P(t)['gridData'].update(x=x, y=y, w=w, h=h)
assert {title(p) for p in panels if p['gridData']['sectionId'] == SEC2} == set(LAYOUT2)

# no overlaps within a section
for s in {p['gridData']['sectionId'] for p in panels}:
    cells = {}
    for p in panels:
        g = p['gridData']
        if g['sectionId'] != s:
            continue
        for x in range(g['x'], g['x'] + g['w']):
            for y in range(g['y'], g['y'] + g['h']):
                assert (x, y) not in cells, (title(p), cells[(x, y)])
                cells[(x, y)] = title(p)

A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
A['description'] = ('MIM V3 — major incident overview (active P1 / P2, applications and users impacted, time to '
                     'resolve, active incidents with their MIM, open alerts with no incident) and a one-CI investigation '
                     'section driven by the Incident / CI controls: alerts, CMDB dependencies, middleware, databases, '
                     'server health, applications, SLO burn, synthetics, logs, processes, changes; a service dependency '
                     'and blast-radius section driven by the Service control.')
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{len(panels)} panels written to {OUT}')
