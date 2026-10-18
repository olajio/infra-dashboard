"""MIM V3: a Servers column in Application Health and Services of the Application (18 Oct 2026).

Usage: mim_v3_patch_2026-10-18m.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-18l.py)

Servers = the hosts the services' APM agents reported from (metrics-apm.internal-*, host.name, production) in the last
15 minutes: per service in Services of the Application, per application (all its services) in Application Health.
Up to 3 are shown, sorted, then "+N more"; "—" when no APM agent host data. The 15 minutes are applied by
Elasticsearch before reading (`_index LIKE "*service_transaction*" OR @timestamp >= NOW() - 15 minutes`), so the
host data adds little to the queries. Also removes a stale sentence from Application Health's description.
"""
import copy
import json
import sys

SRC, OUT = sys.argv[1:3]

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = lambda t: next(p for p in panels if title(p) == t)
st = lambda p: p['embeddableConfig']['attributes']['state']
layer = lambda p: next(iter(st(p)['datasourceStates']['textBased']['layers'].values()))

PROD = 'TO_LOWER(TO_STRING(service.environment)) IN ("prd1", "prd2", "prd", "prod", "production")'
HOST = 'TO_LOWER(TO_STRING(host.name))'
FMT = ('CASE(hosts IS NULL, "—", MV_COUNT(hosts) > 3, CONCAT(MV_CONCAT(MV_SLICE(MV_SORT(hosts), 0, 2), ", "), " +", '
       'TO_STRING(MV_COUNT(hosts) - 3), " more"), MV_CONCAT(MV_SORT(hosts), ", "))')
SERVERS_NOTE = ('Servers: the hosts its services\' APM agents reported from in the last 15 minutes (up to 3, then '
                '"+N more"; "—" = no APM agent host data). Type one into the Server control to see its health.')


def replace(q, old, new):
    assert q.count(old) == 1, old[:80]
    return q.replace(old, new)


def add_column(p, after, label, width):
    lay = layer(p)
    i = next(k for k, c in enumerate(lay['columns']) if c['columnId'] == after)
    col = copy.deepcopy(lay['columns'][i])
    col.update(columnId='servers', fieldName='servers', label=label, customLabel=True,
               meta={'type': 'string', 'esType': 'keyword'})
    col.pop('params', None)
    lay['columns'].insert(i + 1, col)
    vis = st(p)['visualization']['columns']
    j = next(k for k, c in enumerate(vis) if c['columnId'] == after)
    vis.insert(j + 1, {'columnId': 'servers', 'isTransposed': False, 'isMetric': True, 'alignment': 'left', 'width': width})


def set_query(p, q):
    st(p)['query']['esql'] = q
    if 'query' in layer(p):
        layer(p)['query']['esql'] = q


def set_indices(p, idx):
    s = st(p)
    for v in s.get('adHocDataViews', {}).values():
        v.update(title=idx, name=idx, timeFieldName='@timestamp')
    for r in s['datasourceStates']['textBased']['indexPatternRefs']:
        r.update(title=idx, timeField='@timestamp')


# ------------------------------------------------------------------ Services of the Application: servers per service
p = P('Services of the Application')
q = st(p)['query']['esql']
q = replace(q, 'FROM metrics-apm.service_transaction.1m-*\n'
               '| WHERE TO_LOWER(TO_STRING(service.environment)) IN ("prd1", "prd2", "prd", "prod", "production") AND ci.name IS NOT NULL\n'
               '| WHERE ?application == "(all applications)" OR ci.name == ?application\n',
            'FROM metrics-apm.service_transaction.1m-*, metrics-apm.internal-* METADATA _index\n'
            '| WHERE (_index LIKE "*service_transaction*" OR @timestamp >= NOW() - 15 minutes) AND ' + PROD + '\n'
            '| EVAL is_tx = _index LIKE "*service_transaction*"\n'
            '| WHERE (is_tx AND ci.name IS NOT NULL AND (?application == "(all applications)" OR ci.name == ?application))\n'
            '     OR (NOT is_tx AND host.name IS NOT NULL)\n'
            '| EVAL host = CASE(NOT is_tx, ' + HOST + '), app = CASE(is_tx, TO_STRING(ci.name))\n')
# one STATS per service (reads the data once); its application becomes a column built by the query
q = replace(q, '        dur = SUM(transaction.duration.summary)\n  BY service.name, ci.name\n',
               '        dur = SUM(transaction.duration.summary), apps = VALUES(app), hosts = VALUES(host)\n'
               '  BY service.name\n'
               '| WHERE apps IS NOT NULL\n'
               '| EVAL ci.name = MV_CONCAT(MV_SORT(apps), ", ")\n')
q = replace(q, '| EVAL minutes =', '| EVAL servers = ' + FMT + '\n| EVAL minutes =')
q = replace(q, '| KEEP service.name, ci.name, health,', '| KEEP service.name, ci.name, servers, health,')
set_query(p, q)
set_indices(p, 'metrics-apm.service_transaction.1m-*,metrics-apm.internal-*')
add_column(p, 'ci.name', 'Servers', 150)
for c in st(p)['visualization']['columns']:
    c['width'] = {'service.name': 150, 'ci.name': 120}.get(c['columnId'], c.get('width'))
ec = p['embeddableConfig']
ec['description'] = ec['description'].replace(
    'Click a service to open its APM Service Map.',
    'Servers: the hosts the service\'s APM agents reported from in the last 15 minutes (up to 3, then "+N more"; '
    '"—" = no APM agent host data); type one into the Server control to see its health. '
    'Click a service to open its APM Service Map.')

# ------------------------------------------------------------------ Application Health: servers per application
p = P('Application Health')
q = st(p)['query']['esql']
q = replace(q, '| WHERE @timestamp >= NOW() - 1 hour OR parent.name IN',
               '| WHERE (@timestamp >= NOW() - 15 minutes OR (@timestamp >= NOW() - 1 hour AND _index LIKE "*service_transaction*"))\n'
               '     OR parent.name IN')
# host rows: every production APM host in the last 15 minutes (was: only the selected CI's)
i = q.index('     OR (src == "host"')
j = q.index('\n', i)
host_clause = q[i:j]
sel = host_clause.split('AND NOT ', 1)[1].split(' == "(no CI selected)"', 1)[0]
q = q[:i] + '     OR (src == "host" AND ' + PROD + ' AND host.name IS NOT NULL)' + q[j:]
q = replace(q, 'is_host = CASE(src == "host", 1, 0)',
               f'is_host = CASE(src == "host" AND NOT {sel} == "(no CI selected)" AND {HOST} == TO_LOWER({sel}), 1, 0),\n'
               f'       host = CASE(src == "host", {HOST})')
q = replace(q, '| INLINE STATS service_on_ci = MAX(is_host) BY service.name',
               '| INLINE STATS service_on_ci = MAX(is_host), svc_hosts = VALUES(host) BY service.name')
q = replace(q, 'groups = VALUES(TO_STRING(ci.support_group.l2.name))\n  BY ci.name, service.name',
               'groups = VALUES(TO_STRING(ci.support_group.l2.name)),\n        hosts = VALUES(svc_hosts)\n  BY ci.name, service.name')
q = replace(q, 'nums = VALUES(nums), groups = VALUES(groups)\n  BY ci.name',
               'nums = VALUES(nums), groups = VALUES(groups), hosts = VALUES(hosts)\n  BY ci.name')
q = replace(q, '       rank = CASE(failing > 0, 1,', '       servers = ' + FMT + ',\n       rank = CASE(failing > 0, 1,')
q = replace(q, '| KEEP ci.name, app_health, failing,', '| KEEP ci.name, app_health, servers, failing,')
set_query(p, q)
add_column(p, 'app_health', 'Servers', 170)
ec = p['embeddableConfig']
ec['description'] = replace(ec['description'], ' Last 1 hour (fixed); not narrowed by the Incident or CI controls.', '')
ec['description'] = replace(
    ec['description'],
    'Health covers the last hour (set in the query); the panel shows "Last 5 years" because the CMDB links it reads are '
    'only re-sent when they change.',
    SERVERS_NOTE + ' Health covers the last hour and Servers the last 15 minutes (both set in the query). The panel '
    'shows "Last 5 years" only for the CMDB links of the selected CI, which ServiceNow re-sends only when they change; '
    'APM data is never read further back than the last hour.')

# ------------------------------------------------------------------ checks
for t in ('Application Health', 'Services of the Application'):
    q = st(P(t))['query']['esql']
    assert q == layer(P(t))['query']['esql'], t
    assert 'servers' in q and 'metrics-apm.internal-*' in q and 'NOW() - 15 minutes' in q, t
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print('Servers column added to Application Health and Services of the Application')
