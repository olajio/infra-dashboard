"""Check the 27 Oct round: SLA breach from task_has_breached only; On Hold / Resolved / Closed / Canceled incidents
out of Active Incidents, the three tiles and Time to Resolve vs Target, judged on each incident's latest record.

Usage: test_mim_v3_2026-10-27s.py MIM_V3_NDJSON   (local Elasticsearch on port 9200; cleans up its own data)
"""
import json
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

ES = 'http://localhost:9200'
NOW = datetime.now(timezone.utc)
iso = lambda t: t.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
IDX, SLA = 'servicenow-incidents-t27s', 'servicenow-task-sla-t27s'


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request(ES + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return {'error': json.loads(e.read())}


# other rounds' test indices reuse the same incident numbers, so any left over would change the counts
leftover = call('GET', '/_cat/indices/servicenow-incidents-t*,servicenow-task-sla-t*?format=json&h=index')
for old in {i['index'] for i in leftover if isinstance(leftover, list)} | {IDX, SLA}:
    call('DELETE', f'/{old}')
call('PUT', f'/{IDX}', {'mappings': {'properties': {
    '@timestamp': {'type': 'date'}, 'number': {'type': 'keyword'}, 'priority': {'type': 'integer'},
    'state_name': {'type': 'keyword'}, 'opened_at': {'type': 'date'}, 'resolved_at': {'type': 'date'},
    'resolution_time': {'type': 'long'}, 'short_description': {'type': 'keyword'},
    'ci': {'properties': {'name': {'type': 'keyword'}}},
    'assigned_to': {'properties': {'name': {'type': 'keyword'}, 'email': {'type': 'keyword'}}},
    'assignment_group': {'properties': {'name': {'type': 'keyword'}, 'manager': {'properties': {
        'name': {'type': 'keyword'}, 'email': {'type': 'keyword'}}}}}}}})
call('PUT', f'/{SLA}', {'mappings': {'properties': {   # as in sla_breached.txt: percentage is a string
    '@timestamp': {'type': 'date'}, 'task_number': {'type': 'keyword'}, 'stage': {'type': 'keyword'},
    'task_has_breached': {'type': 'boolean'}, 'percentage': {'type': 'keyword'}, 'planned_end_time': {'type': 'date'},
    'contract_name': {'type': 'keyword'}}}})


def inc(n, p, s, opened_h, seen_h=0.02):
    return {'@timestamp': iso(NOW - timedelta(hours=seen_h)), 'number': n, 'priority': p, 'state_name': s,
            'opened_at': iso(NOW - timedelta(hours=opened_h)), 'ci': {'name': 'ci-' + n}}


def sla(n, stage, breached, pct, end_h):
    return {'@timestamp': iso(NOW - timedelta(minutes=3)), 'task_number': n, 'stage': stage,
            'task_has_breached': breached, 'percentage': str(pct), 'planned_end_time': iso(NOW + timedelta(hours=end_h)),
            'contract_name': 'Resolution SLA'}


incidents = [
    inc('INC101', 1, 'New', 1),
    inc('INC102', 1, 'In Progress', 30),
    inc('INC103', 1, 'New', 2),
    inc('INC104', 1, 'On Hold', 5),                               # On Hold: out
    inc('INC201', 2, 'In Progress', 9),
    inc('INC202', 2, 'New', 30),
    inc('INC203', 2, 'In Progress', 20, seen_h=3),                # older copy ...
    inc('INC203', 2, 'On Hold', 20),                              # ... latest record On Hold: out
    inc('INC204', 2, 'Resolved', 30),                             # out
    inc('INC301', 3, 'New', 30),
    inc('INC302', 3, 'On Hold', 48),                              # out
    inc('INC303', 3, 'Closed', 48),                               # out
    inc('INC304', 3, 'Canceled', 48),                             # out
    inc('INC305', 3, 'In Progress', 50),
]
slas = [
    sla('INC101', 'in_progress', True, 50, 3),       # flag true -> Breached
    sla('INC102', 'in_progress', False, 60, -1),     # past planned end, flag false -> Breaching, not Breached
    sla('INC201', 'in_progress', False, 40, 5),      # -> Within SLA
    sla('INC202', 'cancelled', True, 99, -5),        # cancelled record ignored even though breached ...
    sla('INC202', 'in_progress', False, 10, 40),     # ... -> Within SLA
    sla('INC203', 'in_progress', True, 90, -1),      # incident On Hold: not listed at all
    sla('INC305', 'completed', False, 70, 10),       # -> Met
]                                                   # INC103, INC301: no SLA record
lines = ''.join(json.dumps({'index': {'_index': IDX}}) + '\n' + json.dumps(d) + '\n' for d in incidents)
lines += ''.join(json.dumps({'index': {'_index': SLA}}) + '\n' + json.dumps(d) + '\n' for d in slas)
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


def esql(q, rng='now-7d'):   # rng = what Kibana adds for the panel's fixed time range
    r = call('POST', '/_query?format=json', {'query': q, 'filter': {'range': {'@timestamp': {'gte': rng, 'lte': 'now'}}}})
    assert 'error' not in r, json.dumps(r)[:900]
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']]


TABLE = 'Active Incidents (P1 · P2 over 8 h · P3 over 24 h)'
TTR = 'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)'
try:
    print('Active Incidents')
    t = P[TABLE]['embeddableConfig']
    rows = esql(t['attributes']['state']['query']['esql'])
    check('rows', [r['number'] for r in rows], ['INC102', 'INC103', 'INC101', 'INC202', 'INC201', 'INC305', 'INC301'])
    check('SLA column', {r['number']: r['sla'] for r in rows}, {
        'INC101': 'Breached', 'INC102': 'Breaching', 'INC103': 'No SLA record', 'INC201': 'Within SLA',
        'INC202': 'Within SLA', 'INC305': 'Met', 'INC301': 'No SLA record'})
    q = t['attributes']['state']['query']['esql']
    layer_q = [L['query']['esql'] for L in t['attributes']['state']['datasourceStates']['textBased']['layers'].values()]
    check('layer query = panel query', layer_q, [q])
    check('no age-based SLA left', '(age)' in json.dumps(t, ensure_ascii=False), False)
    sla_col = next(c for c in t['attributes']['state']['visualization']['columns'] if c['columnId'] == 'sla')
    colours = {a['rules'][0]['pattern']: a['color']['colorCode'] for a in sla_col['colorMapping']['assignments']}
    check('SLA colours', colours, {'Breached': '#d6453d', 'Breaching': '#c98a0b', 'Paused': '#8a96a8',
                                   'Within SLA': '#1f9e6b', 'Met': '#1f9e6b', 'No SLA record': '#8a96a8'})

    print('Tiles')
    tiles = {}
    for name in ('Active P1', 'P2 over 8 h', 'P3 over 24 h'):
        spec = json.loads(P[name]['embeddableConfig']['savedVis']['params']['spec'])
        tiles[name] = esql(spec['data'][0]['url']['query'])[0]['incidents']
    check('tile counts', tiles, {'Active P1': 3, 'P2 over 8 h': 2, 'P3 over 24 h': 2})
    by_pri = Counter(r['priority'] for r in rows)
    check('tiles match table', [by_pri[1], by_pri[2], by_pri[3]], list(tiles.values()))

    print('Time to Resolve vs Target')
    g = P[TTR]['embeddableConfig']
    rows = esql(g['attributes']['state']['query']['esql'])
    check('only the 7 still-open incidents', sum(r['incidents'] for r in rows), 7)
    check('columns kept for the chart', sorted(rows[0]), sorted(['day', 'p1_hours', 'p2_hours', 'p3_hours', 'incidents', 'open_now']))
    p1 = [r['p1_hours'] for r in rows if r['p1_hours'] is not None]
    # INC101 (1 h) and INC103 (2 h) share a day unless midnight UTC falls between them; INC102 is 30 h old
    check('P1 point = average age so far', sorted(round(h, 1) for h in p1) in ([1.5, 30.0], [1.0, 2.0, 30.0]), True)
    layer_q = [L['query']['esql'] for L in g['attributes']['state']['datasourceStates']['textBased']['layers'].values() if 'query' in L]
    check('data layer query = panel query', g['attributes']['state']['query']['esql'] in layer_q, True)
finally:
    for old in (IDX, SLA):
        call('DELETE', f'/{old}')

print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
