"""Load small known data into local Elasticsearch and check the 16 Oct changes: Active Incidents and Escalate columns,
the Active P1 / P2 Vega donut, Users impacted text, Applications that depend on this CI, Open Alerts window, removed
panels.

Usage: test_mim_v3_2026-10-16.py MIM_V3_NDJSON
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

ES = 'http://localhost:9200'
NOW = datetime.now(timezone.utc)
ago = lambda **kw: (NOW - timedelta(**kw)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
ahead = lambda **kw: (NOW + timedelta(**kw)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
CI = 'kau1s054'


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request(ES + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return {'error': json.loads(e.read())}


def load(index, docs, mapping=None):
    if mapping is None:
        call('DELETE', f'/_data_stream/{index}')
    else:
        call('DELETE', f'/{index}')
        r = call('PUT', f'/{index}', {'mappings': {'properties': mapping}})
        assert 'error' not in r, (index, r)
    op = 'create' if mapping is None else 'index'
    lines = ''.join(json.dumps({op: {'_index': index}}) + '\n' + json.dumps(d) + '\n' for d in docs)
    r = call('POST', '/_bulk?refresh=true', lines, nd=True)
    assert not r.get('errors'), (index, json.dumps(r)[:800])


KW, DATE, INT = {'type': 'keyword'}, {'type': 'date'}, {'type': 'integer'}
TEXT = {'type': 'text', 'fields': {'keyword': KW}}
obj = lambda **p: {'properties': p}

for old in ('servicenow-incidents-t', 'servicenow-incidents-v3', 'servicenow-incidents-hot'):
    call('DELETE', f'/{old}')
person = lambda n: {'name': n, 'email': n.lower().replace(' ', '.') + '@cna.com'}
inc = lambda n, p, state, ci, opened_h, who, grp, mgr: {
    '@timestamp': ago(minutes=1), 'number': n, 'priority': p, 'state_name': state, 'opened_at': ago(hours=opened_h),
    'ci': {'name': ci, 'class_name': 'Windows Server', 'environment': 'prod', 'support_group': {'l2': {'name': 'IT.I.Wintel'}}},
    'assigned_to': person(who) if who else {}, 'assignment_group': {'name': grp, 'manager': person(mgr)},
    'short_description': n}
load('servicenow-incidents-t16', [
    inc('INC1', 1, 'In Progress', CI, 2, 'Ann Lee', 'IT.I.Wintel', 'Mark Boss'),
    inc('INC2', 2, 'New', 'otherci', 1, None, 'IT.A.Apps', 'Olga Head'),
    inc('INC3', 2, 'Resolved', CI, 3, 'Ann Lee', 'IT.I.Wintel', 'Mark Boss')],
    {'@timestamp': DATE, 'number': KW, 'priority': INT, 'state_name': KW, 'opened_at': DATE, 'short_description': KW,
     'ci': obj(name=KW, class_name=KW, environment=KW, support_group=obj(l2=obj(name=KW))),
     'assigned_to': obj(name=KW, email=KW), 'assignment_group': obj(name=KW, manager=obj(name=KW, email=KW))})
call('DELETE', '/servicenow-task-sla-v3')
load('servicenow-task-sla-t16', [{'@timestamp': ago(minutes=1), 'task_number': 'INC1', 'stage': 'in_progress',
                                  'task_has_breached': False, 'percentage': 20, 'planned_end_time': ahead(hours=3),
                                  'contract_name': 'P1 Resolution'}],
     {'@timestamp': DATE, 'task_number': KW, 'stage': KW, 'task_has_breached': {'type': 'boolean'},
      'percentage': {'type': 'float'}, 'planned_end_time': DATE, 'contract_name': KW})
load('.ds-metrics-system.cpu-default-t16', [{'@timestamp': ago(minutes=1), 'ci': {'name': CI}}],
     {'@timestamp': DATE, 'ci': obj(name=KW, class_name=KW, environment=KW, support_group=obj(l2=obj(name=KW)))})
SIDE = obj(name=TEXT, **{'class': TEXT}, environment=TEXT, install_status=TEXT, operational_status=TEXT,
           number=obj(servicenow=obj(event=obj(number=obj(value=TEXT)))))
side = lambda n, c: {'name': n, 'class': 'cmdb_ci_' + c, 'environment': 'Production', 'install_status': '1',
                     'operational_status': '1', 'number': {'servicenow': {'event': {'number': {'value': 'APM0001'}}}}}
load('cmdb_app_dependencies_v2', [{'parent_ci': side('Underwriting Tools PROD', 'service_by_tags'), 'child_ci': side(CI, 'win_server'),
                                   'relationship': {'latest': {'servicenow': {'event': {'type': {'value': '60bc4e22c0a8010e01f074cbe6bd73c3'}}}}}}],
     {'parent_ci': SIDE, 'child_ci': SIDE, 'relationship': obj(latest=obj(servicenow=obj(event=obj(type=obj(value=KW)))))})

# ------------------------------------------------------------------ checks
dash = json.loads(open(sys.argv[1]).readline())
panels = json.loads(dash['attributes']['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = {title(p): p for p in panels}
fails = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" + ('' if ok else f'\n          expected {want!r}'))
    if not ok:
        fails.append(name)


def esql(q, params=(), rng=None):
    body = {'query': q, 'params': list(params)}
    if rng:
        body['filter'] = {'range': {'@timestamp': {'gte': rng, 'lte': 'now'}}}
    r = call('POST', '/_query?format=json', body)
    assert 'error' not in r, json.dumps(r)[:900]
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']], cols


def run(t, ci='(no CI selected)', incident='(all incidents)'):
    ec = P[t]['embeddableConfig']
    q = next(iter(ec['attributes']['state']['datasourceStates']['textBased']['layers'].values()))['query']['esql']
    params = [x for x in ({'ci': ci}, {'incident': incident}) if '?' + list(x)[0] in q]
    rng = (ec.get('time_range') or {}).get('from')
    return esql(q, params, None if 'cmdb_app_dependencies' in q else rng)


labels = lambda t: [c['label'] for c in next(iter(P[t]['embeddableConfig']['attributes']['state']['datasourceStates']
                                                   ['textBased']['layers'].values()))['columns']]
R, cols = run('Active Incidents (P1 / P2)')
check('Active Incidents columns', labels('Active Incidents (P1 / P2)'), [
    'Incident', 'Pri', 'Affected CI', 'State', 'SLA', 'Assignment Group', 'Assignee', 'Assignee Email',
    'Group Manager Name', 'Manager Email Id'])
check('Active Incidents rows', [tuple(r.values()) for r in R], [
    ('INC1', 1, CI, 'In Progress', 'Within SLA', 'IT.I.Wintel', 'Ann Lee', 'ann.lee@cna.com', 'Mark Boss', 'mark.boss@cna.com'),
    ('INC2', 2, 'otherci', 'New', 'Within SLA (age)', 'IT.A.Apps', '—', '—', 'Olga Head', 'olga.head@cna.com')])
R, cols = run('Escalate', ci=CI)
check('Escalate columns', labels('Escalate'), [
    'CI', 'Active Incident', 'Priority', 'Class', 'Env', 'CI support group', 'Assignment Group', 'Assignee',
    'Assignee Email', 'Group Manager Name', 'Manager Email Id'])
check('Escalate rows', [tuple(r.values()) for r in R], [
    (CI, 'INC1', 1, 'Windows Server', 'prod', 'IT.I.Wintel', 'IT.I.Wintel', 'Ann Lee', 'ann.lee@cna.com', 'Mark Boss',
     'mark.boss@cna.com')])
check('Escalate follows the incident', run('Escalate', incident=f'INC1 · {CI}')[0], R)
R, cols = run('Applications that depend on this CI', ci=CI)
check('Applications that depend on this CI: no CMDB status', cols,
      ['parent_ci.name.keyword', 'app_kind', 'app_how', 'app_env', 'app_number'])
check('Open Alerts window', P['Open Alerts with No Incident']['embeddableConfig']['time_range']['from'], 'now-24h')
spec = json.loads(P['Active P1 / P2']['embeddableConfig']['savedVis']['params']['spec'])
check('donut query', [(r['label'], r['incidents']) for r in esql(spec['data'][0]['url']['query'])[0]], [('P1', 1), ('P2', 1)])
spec = json.loads(P['Users impacted']['embeddableConfig']['savedVis']['params']['spec'])
check('Users impacted text', spec['data'][0]['values'][0]['detail'],
      'Real count to be incorporated|from ServiceNow and RUM')
check('removed panels', [t for t in ('Applications impacted', 'What this CI runs on') if t in P], [])
check('no MIM left', [t for t, p in P.items() if 'promoted_by' in json.dumps(p) or 'Assigned MIM' in json.dumps(p)], [])
print('\n' + ('ALL CHECKS PASSED' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
