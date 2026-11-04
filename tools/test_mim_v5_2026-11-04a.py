"""Check MIM V5 patch 04a: Escalate (State, Opened, no CI support group), Active Incidents (Opened), Open Alerts with
No Incident scoped to the selected CI and its CMDB links, control icons and banners; every query still runs.

Usage: test_mim_v5_2026-11-04a.py "MIM V4.ndjson" "MIM V5.ndjson"
(local Elasticsearch on port 9200; loads the Infrastructure Dashboard test's data, which includes the MIM tests'
data, plus its own Netcool alerts and CMDB links, and removes it all at the end)
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

HERE = __file__.rsplit('/', 1)[0]
V4, V5 = sys.argv[1:3]
sys.argv = ['setup', V5]
src = open(f'{HERE}/test_infra_dashboard_2026-10-28.py').read().split('\ntry:')[0]
g = {'__name__': 'setup', '__file__': f'{HERE}/test_infra_dashboard_2026-10-28.py'}
exec(compile(src, 'test_infra_dashboard_2026-10-28.py (data setup)', 'exec'), g)
call, ago, cleanup_infra = g['call'], g['ago'], g['cleanup']
NC, REL = '.ds-bridge-alerts-netcool-default-t40', 'cmdb-ci-relations-t40'
K, D = {'type': 'keyword'}, {'type': 'date'}
obj = lambda **p: {'properties': p}


def cleanup():
    cleanup_infra()
    for i in (NC, REL):
        call('DELETE', f'/{i}')


call('PUT', f'/{NC}', {'mappings': {'properties': {
    '@timestamp': D, 'severity': {'type': 'integer'}, 'message': K, 'node': K, 'first_occurrence': D, 'last_occurrence': D,
    'netcool': obj(type_name=K, acknowledged_name=K, tally={'type': 'integer'}, identifier=K),
    'ci': obj(name=K, class_name=K, environment=K, support_group=obj(l2=obj(name=K)))}}})
al = lambda ident, ci, node: {'@timestamp': ago(minutes=10), 'severity': 5, 'message': f'{ident} down', 'node': node,
                              'first_occurrence': ago(minutes=40), 'last_occurrence': ago(minutes=10),
                              'netcool': {'type_name': 'problem', 'acknowledged_name': 'no', 'tally': 2, 'identifier': ident},
                              'ci': {'name': ci, 'environment': 'Production', 'class_name': 'IP Switch'}}
alerts = [al('nA', 'netA', 'netA'),                 # linked to srvA (srvA is the parent)
          al('nB', 'netB', 'netB'),                 # not linked
          al('nC', None, 'netC.cna.com')]           # node only, linked to srvA (srvA is the child)
assert not call('POST', '/_bulk?refresh=true', ''.join(json.dumps({'index': {'_index': NC}}) + '\n' + json.dumps(a) + '\n'
                                                        for a in alerts), nd=True).get('errors')
call('PUT', f'/{REL}', {'mappings': {'properties': {'@timestamp': D, 'is_marked_for_deletion': {'type': 'boolean'},
                                                    'parent': obj(name=K), 'child': obj(name=K)}}})
rel = lambda p, c, gone=False: {'@timestamp': '2025-01-01T00:00:00Z', 'is_marked_for_deletion': gone,
                                'parent': {'name': p}, 'child': {'name': c}}
assert not call('POST', '/_bulk?refresh=true', ''.join(json.dumps({'index': {'_index': REL}}) + '\n' + json.dumps(r) + '\n' for r in
                [rel('srvA', 'netA'), rel('netC', 'srvA'), rel('srvA', 'netB', gone=True)]), nd=True).get('errors')

load = lambda f: json.loads([l for l in open(f) if l.strip()][-1])
d4, d5 = load(V4), load(V5)
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P4 = {title(p): p for p in json.loads(d4['attributes']['panelsJSON'])}
panels5 = json.loads(d5['attributes']['panelsJSON'])
P5 = {title(p): p for p in panels5}
fails = []
NOW = datetime.now(timezone.utc)
DEFAULTS = {'incident': '(all incidents)', 'ci': '(no CI selected)', 'server': '(no server selected)',
            'health_window': '24 hours', 'service': '(services on this CI)', 'application': '(all applications)',
            'monitored_app': '(all monitored applications)',
            '_tstart': (NOW - timedelta(hours=1)).isoformat(), '_tend': NOW.isoformat()}


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" + ('' if ok else f'\n          expected {want!r}'))
    if not ok:
        fails.append(name)


def esql(q, rng=None, **vals):
    names = sorted(set(re.findall(r'\?([A-Za-z_][A-Za-z0-9_]*)', q)) - {'sysparm_query'})
    v = dict(DEFAULTS, **vals)
    body = {'query': q, 'params': [{n: v[n]} for n in names]}
    if rng:
        body['filter'] = {'range': {'@timestamp': {'gte': rng['from'], 'lte': rng['to']}}}
    r = call('POST', '/_query?format=json', body)
    if 'error' in r:
        return r
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, x)) for x in r['values']]


def run(P, t, **v):
    ec = P[t]['embeddableConfig']
    r = esql(ec['attributes']['state']['query']['esql'], ec.get('time_range'), **v)
    assert not isinstance(r, dict), json.dumps(r)[:900]
    return r


def cols(P, t):
    st = P[t]['embeddableConfig']['attributes']['state']
    (layer,) = st['datasourceStates']['textBased']['layers'].values()
    return [c['columnId'] for c in st['visualization']['columns']], [c['columnId'] for c in layer['columns']]


try:
    print('Every query runs (nothing picked, CI = srvA, Incident = INC801 · srvA)')
    n = 0
    for p in panels5:
        ec = p['embeddableConfig']
        q = ec.get('esql_query') if p['type'] == 'esql_control' else (
            ec['attributes']['state']['query']['esql'] if p['type'] == 'vis' else None)
        if not q:
            continue
        for v in ({}, {'ci': 'srvA'}, {'incident': 'INC801 · srvA'}):
            r = esql(q, ec.get('time_range'), **v)
            n += 1
            if isinstance(r, dict) and 'Unknown index' not in json.dumps(r) and 'Unknown column' not in json.dumps(r):
                check(f'{title(p)} {v}', json.dumps(r['error'])[:300], 'no error')
    print(f'  ran {n} queries (panels whose source data is not loaded here are skipped)')

    print('Escalate')
    viz, layer = cols(P5, 'Escalate')
    check('columns: State and Opened after Priority, no CI support group', viz,
          ['ci.name', 'number', 'esc_priority', 'esc_state', 'esc_opened', 'esc_class', 'esc_env', 'esc_assignment_group',
           'assignee', 'assignee_email', 'group_manager', 'manager_email'])
    check('layer columns match', sorted(layer), sorted(viz))
    rows = run(P5, 'Escalate', ci='srvA')
    check('State per incident on srvA', sorted((r['number'], r['esc_state']) for r in rows),
          [('INC801', 'New'), ('INC802', 'In Progress')])
    check('Opened filled', all(r['esc_opened'] for r in rows), True)
    check('no CI support group in the result', 'esc_support_group' in rows[0], False)
    ai = {r['number']: r['state_name'] for r in run(P5, 'Active Incidents (P1 · P2 over 8 h · P3 over 24 h)')}
    check('Escalate State = Active Incidents State', all(ai.get(r['number'], r['esc_state']) == r['esc_state'] for r in rows), True)

    print('Active Incidents')
    viz, layer = cols(P5, 'Active Incidents (P1 · P2 over 8 h · P3 over 24 h)')
    check('Opened after State', viz[:6], ['number', 'priority', 'ci.name', 'state_name', 'opened', 'sla'])
    rows = run(P5, 'Active Incidents (P1 · P2 over 8 h · P3 over 24 h)')
    check('Opened filled on every row', bool(rows) and all(r['opened'] for r in rows), True)
    old = run(P4, 'Active Incidents (P1 · P2 over 8 h · P3 over 24 h)')
    check('same incidents as MIM V4', sorted(r['number'] for r in rows), sorted(r['number'] for r in old))

    print('Open Alerts with No Incident')
    OA = 'Open Alerts with No Incident'
    keyf = lambda rows: sorted((r['ci.name'] or '-', r['alert_node']) for r in rows)
    check('nothing picked: same alerts as MIM V4', keyf(run(P5, OA)), keyf(run(P4, OA)))
    check('CI = srvA: only alerts on CIs linked to it (both directions, node match; deleted link ignored)',
          keyf(run(P5, OA, ci='srvA')), [('-', 'netC.cna.com'), ('App PROD', 'App PROD.cna.com'), ('netA', 'netA')])   # App PROD: linked in test -18k's data
    check('Incident = INC801 · srvA: the same', keyf(run(P5, OA, incident='INC801 · srvA')),
          [('-', 'netC.cna.com'), ('App PROD', 'App PROD.cna.com'), ('netA', 'netA')])
    check('CI = srvZ (no links): none', keyf(run(P5, OA, ci='srvZ')), [])

    print('Controls and banners')
    pins = sorted((v['order'], v['config']['title'], v['grow']) for v in d5['attributes']['pinned_panels']['panels'].values())
    check('top bar: icons, full width', pins,
          [(0, '🚨 Incident', True), (1, '🖥️ CI', True), (2, '🧩 Monitored application', True)])
    s3 = sorted((p for p in panels5 if p['type'] == 'esql_control'), key=lambda p: p['gridData']['x'])
    check('section 3 controls: icons', [p['embeddableConfig']['title'] for p in s3],
          ['🖥️ Server', '🧩 Application', '⚙️ Service', '⏱️ Health window'])
    check('banners at the top of sections 1 and 3',
          sorted((title(p), p['gridData']['y']) for p in panels5 if 'Start here' in title(p) or title(p).startswith('Then pick')),
          [('Start here', 0), ('Then pick a server, application and service', 0)])
    s1 = P5['Active P1']['gridData']['sectionId']
    check('no panel overlaps the section 1 banner', min(p['gridData']['y'] for p in panels5
                                                        if p['gridData'].get('sectionId') == s1 and title(p) != 'Start here'), 3)
finally:
    cleanup()

print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
