"""Check the sixth 16 Oct round: the Active P1 / P2 / P3 donut counts the same active incidents as the Active
Incidents table, lists P1, P2 and P3 always, and gives every non-zero priority a visible slice.

Usage: test_mim_v3_2026-10-16f.py MIM_V3_NDJSON
"""
import json
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

ES = 'http://localhost:9200'
NOW = datetime.now(timezone.utc)
iso = lambda t: t.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
IDX, SLA = 'servicenow-incidents-t16f', 'servicenow-task-sla-t16f'


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request(ES + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return {'error': json.loads(e.read())}


for old in ('servicenow-incidents-t', 'servicenow-incidents-t16', 'servicenow-incidents-t16d', 'servicenow-incidents-t16e', IDX, SLA):
    call('DELETE', f'/{old}')
call('PUT', f'/{IDX}', {'mappings': {'properties': {
    '@timestamp': {'type': 'date'}, 'number': {'type': 'keyword'}, 'priority': {'type': 'integer'},
    'state_name': {'type': 'keyword'}, 'opened_at': {'type': 'date'}, 'ci': {'properties': {'name': {'type': 'keyword'}}},
    'assigned_to': {'properties': {'name': {'type': 'keyword'}, 'email': {'type': 'keyword'}}},
    'assignment_group': {'properties': {'name': {'type': 'keyword'}, 'manager': {'properties': {
        'name': {'type': 'keyword'}, 'email': {'type': 'keyword'}}}}}}}})
inc = lambda n, p, s: {'@timestamp': iso(NOW - timedelta(minutes=1)), 'number': n, 'priority': p, 'state_name': s,
                       'opened_at': iso(NOW - timedelta(hours=2)), 'ci': {'name': 'ci-' + n}}
docs = [inc(f'INC{300 + i}', 3, 'New') for i in range(40)] + [
    inc('INC201', 2, 'In Progress'), inc('INC201', 2, 'In Progress'),   # synced twice: one P2
    inc('INC202', 2, 'Resolved'),                                       # resolved: out
    inc('INC401', 4, 'New'),                                            # P4: out
    inc('CHG001', 2, 'New')]                                            # not an incident number: out
call('PUT', f'/{SLA}', {'mappings': {'properties': {   # the table also reads SLA records (none here)
    '@timestamp': {'type': 'date'}, 'task_number': {'type': 'keyword'}, 'stage': {'type': 'keyword'},
    'task_has_breached': {'type': 'boolean'}, 'percentage': {'type': 'float'}, 'planned_end_time': {'type': 'date'},
    'contract_name': {'type': 'keyword'}}}})
lines = ''.join(json.dumps({'index': {'_index': IDX}}) + '\n' + json.dumps(d) + '\n' for d in docs)
assert not call('POST', '/_bulk?refresh=true', lines, nd=True).get('errors')

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


def esql(q, rng=None):
    body = {'query': q}
    if rng:
        body['filter'] = {'range': {'@timestamp': {'gte': rng}}}
    r = call('POST', '/_query?format=json', body)
    assert 'error' not in r, json.dumps(r)[:900]
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']]


try:
    spec = json.loads(P['Active P1 / P2 / P3']['embeddableConfig']['savedVis']['params']['spec'])
    D = {d['name']: d for d in spec['data']}
    donut = {r['label']: r['incidents'] for r in esql(D['raw']['url']['query'])}
    table = Counter(f"P{r['priority']}" for r in esql(P['Active Incidents (P1 / P2 / P3)']['embeddableConfig']['attributes']
                                                       ['state']['query']['esql'], 'now-1M'))
    check('donut counts', donut, {'P2': 1, 'P3': 40})
    check('donut and Active Incidents table count the same', donut, dict(table))
    check('legend always lists P1, P2, P3', ([v['label'] for v in D['prios']['values']],
                                            D['prios']['transform'][0]['default'],
                                            next(m for m in spec['marks'] if m['type'] == 'text' and m.get('from', {}).get('data') == 'prios') is not None),
          (['P1', 'P2', 'P3'], 0, True))
    t = D['slices']['transform']
    check('every non-zero priority gets at least 6 % of the ring', (t[0]['expr'], t[2]['expr'], t[3]['field']),
          ('datum.incidents > 0', 'max(datum.incidents, datum.all * 0.06)', 'weight'))
    share = max(1, 41 * 0.06) / (max(1, 41 * 0.06) + 40)
    check('so 1 P2 next to 40 P3s gets a visible slice (over 5 % of the ring)', share > 0.05, True)
finally:
    for idx in (IDX, SLA):
        call('DELETE', f'/{idx}')
print('\n' + ('ALL CHECKS PASSED' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
