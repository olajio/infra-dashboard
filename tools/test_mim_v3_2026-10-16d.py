"""Check that P3 incidents are included (16 Oct, fourth round): controls, Active donut, Active Incidents (SLA for a
P3 with and without an SLA record), Escalate; P4 and resolved incidents stay out; Time to Resolve stays P1 / P2.

Usage: test_mim_v3_2026-10-16d.py MIM_V3_NDJSON
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

ES = 'http://localhost:9200'
NOW = datetime.now(timezone.utc)
ago = lambda **kw: (NOW - timedelta(**kw)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
ahead = lambda **kw: (NOW + timedelta(**kw)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request(ES + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return {'error': json.loads(e.read())}


def load(index, docs, mapping):
    call('DELETE', f'/{index}')
    assert 'error' not in call('PUT', f'/{index}', {'mappings': {'properties': mapping}}), index
    lines = ''.join(json.dumps({'index': {'_index': index}}) + '\n' + json.dumps(d) + '\n' for d in docs)
    assert not call('POST', '/_bulk?refresh=true', lines, nd=True).get('errors'), index


KW, DATE, INT = {'type': 'keyword'}, {'type': 'date'}, {'type': 'integer'}
obj = lambda **p: {'properties': p}
for old in ('servicenow-incidents-t', 'servicenow-incidents-t16', 'servicenow-task-sla-t16'):
    call('DELETE', f'/{old}')
person = lambda n: {'name': n, 'email': n.lower().replace(' ', '.') + '@cna.com'}
inc = lambda n, p, state, ci, who: {
    '@timestamp': ago(minutes=1), 'number': n, 'priority': p, 'state_name': state, 'opened_at': ago(hours=30),
    'ci': {'name': ci}, 'assigned_to': person(who), 'assignment_group': {'name': 'IT.I.Wintel', 'manager': person('Mark Boss')}}
load('servicenow-incidents-t16d', [
    inc('INC1', 1, 'In Progress', 'p1host', 'Ann Lee'), inc('INC2', 2, 'New', 'p2host', 'Bo Chan'),
    inc('INC3', 3, 'In Progress', 'p3host', 'Cy Dee'), inc('INC4', 3, 'New', 'p3other', 'Di Eck'),
    inc('INC5', 4, 'New', 'p4host', 'Ed Fox'), inc('INC6', 3, 'Resolved', 'p3done', 'Fi Gee')],
    {'@timestamp': DATE, 'number': KW, 'priority': INT, 'state_name': KW, 'opened_at': DATE,
     'ci': obj(name=KW), 'assigned_to': obj(name=KW, email=KW), 'assignment_group': obj(name=KW, manager=obj(name=KW, email=KW))})
load('servicenow-task-sla-t16d', [{'@timestamp': ago(minutes=1), 'task_number': 'INC3', 'stage': 'in_progress',
                                   'task_has_breached': False, 'percentage': 20, 'planned_end_time': ahead(days=2),
                                   'contract_name': 'P3 Resolution'}],
     {'@timestamp': DATE, 'task_number': KW, 'stage': KW, 'task_has_breached': {'type': 'boolean'},
      'percentage': {'type': 'float'}, 'planned_end_time': DATE, 'contract_name': KW})

dash = json.loads(open(sys.argv[1]).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
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
    return [dict(zip(cols, v)) for v in r['values']]


def run(t, ci='(no CI selected)', incident='(all incidents)'):
    ec = P[t]['embeddableConfig']
    q = ec['attributes']['state']['query']['esql']
    params = [x for x in ({'ci': ci}, {'incident': incident}) if '?' + list(x)[0] in q]
    return esql(q, params, (ec.get('time_range') or {}).get('from'))


ctl = {c['config']['title']: c['config']['esql_query'] for c in A['pinned_panels']['panels'].values()}
check('Incident control lists P1-P3, not P4 or resolved', [r['incident'] for r in esql(ctl['Incident'])],
      ['(all incidents)', 'INC4 · p3other', 'INC3 · p3host', 'INC2 · p2host', 'INC1 · p1host'])
check('CI control lists P1-P3 CIs (resolved too), not P4', [r['ci'] for r in esql(ctl['CI'])],
      ['(no CI selected)', 'p1host', 'p2host', 'p3done', 'p3host', 'p3other'])
spec = json.loads(P['Active P1 / P2 / P3']['embeddableConfig']['savedVis']['params']['spec'])
check('donut counts', [(r['label'], r['incidents']) for r in esql(spec['data'][0]['url']['query'])],
      [('P1', 1), ('P2', 1), ('P3', 2)])
check('donut colours', (spec['scales'][0]['domain'], spec['scales'][0]['range']),
      (['P1', 'P2', 'P3'], ['#d6453d', '#c98a0b', '#3f6fb5']))
check('Active Incidents: P1-P3, P3 SLA from its record or "No SLA record"',
      sorted((r['number'], r['priority'], r['sla'], r['assignee']) for r in run('Active Incidents (P1 / P2 / P3)')), [
          ('INC1', 1, 'Breached (age)', 'Ann Lee'), ('INC2', 2, 'Breached (age)', 'Bo Chan'),
          ('INC3', 3, 'Within SLA', 'Cy Dee'), ('INC4', 3, 'No SLA record', 'Di Eck')])
check('Escalate shows a P3', [(r['number'], r['esc_priority'], r['assignee'], r['group_manager'])
                              for r in run('Escalate', incident='INC4 · p3other')], [('INC4', 3, 'Di Eck', 'Mark Boss')])
badges = [c for p in ('Active Incidents (P1 / P2 / P3)', 'Escalate') for c in
          P[p]['embeddableConfig']['attributes']['state']['visualization']['columns'] if c['columnId'] in ('priority', 'esc_priority')]
check('priority badges have a P3 colour', [[s['color'] for s in c['palette']['params']['colorStops']] for c in badges],
      [['#d6453d', '#c98a0b', '#3f6fb5']] * 2)
tq = P['P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)']['embeddableConfig']['attributes']['state']['query']['esql']
check('Time to Resolve stays P1 / P2', 'priority IN (1, 2) AND' in tq, True)
for idx in ('servicenow-incidents-t16d', 'servicenow-task-sla-t16d'):   # do not leak into the other tests
    call('DELETE', f'/{idx}')
print('\n' + ('ALL CHECKS PASSED' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
