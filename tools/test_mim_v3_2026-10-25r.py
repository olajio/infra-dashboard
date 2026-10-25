"""Check the 25 Oct round: Active P1 / P2 over 8 h / P3 over 24 h tiles, the overdue-only Active Incidents table,
the 7-day look-back, and the section 1 layout.

Usage: test_mim_v3_2026-10-25r.py MIM_V3_NDJSON   (local Elasticsearch on port 9200; cleans up its own data)
"""
import json
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

ES = 'http://localhost:9200'
NOW = datetime.now(timezone.utc)
iso = lambda t: t.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
IDX, SLA = 'servicenow-incidents-t25r', 'servicenow-task-sla-t25r'


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request(ES + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return {'error': json.loads(e.read())}


for old in (IDX, SLA):
    call('DELETE', f'/{old}')
call('PUT', f'/{IDX}', {'mappings': {'properties': {
    '@timestamp': {'type': 'date'}, 'number': {'type': 'keyword'}, 'priority': {'type': 'integer'},
    'state_name': {'type': 'keyword'}, 'opened_at': {'type': 'date'}, 'resolved_at': {'type': 'date'},
    'resolution_time': {'type': 'long'}, 'short_description': {'type': 'keyword'},
    'ci': {'properties': {'name': {'type': 'keyword'}}},
    'assigned_to': {'properties': {'name': {'type': 'keyword'}, 'email': {'type': 'keyword'}}},
    'assignment_group': {'properties': {'name': {'type': 'keyword'}, 'manager': {'properties': {
        'name': {'type': 'keyword'}, 'email': {'type': 'keyword'}}}}}}}})
call('PUT', f'/{SLA}', {'mappings': {'properties': {
    '@timestamp': {'type': 'date'}, 'task_number': {'type': 'keyword'}, 'stage': {'type': 'keyword'},
    'task_has_breached': {'type': 'boolean'}, 'percentage': {'type': 'float'}, 'planned_end_time': {'type': 'date'},
    'contract_name': {'type': 'keyword'}}}})


def inc(n, p, s, opened_h, seen_h=0.02):
    return {'@timestamp': iso(NOW - timedelta(hours=seen_h)), 'number': n, 'priority': p, 'state_name': s,
            'opened_at': iso(NOW - timedelta(hours=opened_h)), 'ci': {'name': 'ci-' + n}}


docs = [
    inc('INC101', 1, 'New', 1),                 # P1, young: in
    inc('INC102', 1, 'In Progress', 30),        # P1, old: in
    inc('INC201', 2, 'In Progress', 9),         # P2 past 8 h: in
    inc('INC201', 2, 'In Progress', 9),         # synced twice: still one row
    inc('INC202', 2, 'New', 7),                 # P2 under 8 h: out
    inc('INC203', 2, 'Resolved', 30),           # resolved: out
    inc('INC301', 3, 'New', 25),                # P3 past 24 h: in
    inc('INC302', 3, 'On Hold', 23),            # P3 under 24 h: out
    inc('INC303', 3, 'In Progress', 72),        # P3, 3 days: in
    inc('INC304', 3, 'New', 240, seen_h=240),   # last synced 10 days ago: outside the 7-day look-back
    inc('INC401', 4, 'New', 50),                # P4: out
    inc('CHG001', 2, 'New', 50),                # not an incident: out
]
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
    if rng:   # what Kibana adds for the panel's time range
        body['filter'] = {'range': {'@timestamp': {'gte': rng, 'lte': 'now'}}}
    r = call('POST', '/_query?format=json', body)
    assert 'error' not in r, json.dumps(r)[:900]
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']]


WEEK = {'from': 'now-7d', 'to': 'now'}
TABLE = 'Active Incidents (P1 · P2 over 8 h · P3 over 24 h)'
try:
    print('Panels')
    check('donut removed', 'Active P1 / P2 / P3' in P, False)
    check('old table title gone', 'Active Incidents (P1 / P2 / P3)' in P, False)
    for t in ('Active P1', 'P2 over 8 h', 'P3 over 24 h', TABLE, 'Escalate',
              'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)'):
        check(f'{t}: time range', P[t]['embeddableConfig'].get('time_range'), WEEK)

    print('Tiles')
    tiles = {}
    for t in ('Active P1', 'P2 over 8 h', 'P3 over 24 h'):
        spec = json.loads(P[t]['embeddableConfig']['savedVis']['params']['spec'])
        rows = esql(spec['data'][0]['url']['query'], 'now-7d')
        tiles[t] = rows[0]['incidents']
    check('tile counts', tiles, {'Active P1': 2, 'P2 over 8 h': 1, 'P3 over 24 h': 2})

    print('Active Incidents')
    rows = esql(P[TABLE]['embeddableConfig']['attributes']['state']['query']['esql'], 'now-7d')
    check('rows', [r['number'] for r in rows], ['INC102', 'INC101', 'INC201', 'INC303', 'INC301'])
    by_pri = Counter(r['priority'] for r in rows)
    check('table matches tiles', [by_pri[1], by_pri[2], by_pri[3]],
          [tiles['Active P1'], tiles['P2 over 8 h'], tiles['P3 over 24 h']])
    check('SLA column (age)', {r['number']: r['sla'] for r in rows if r['priority'] != 1},
          {'INC201': 'Breached (age)', 'INC303': 'Breached (age)', 'INC301': 'Breached (age)'})

    print('Time to Resolve vs Target')
    ttr = P['P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)']['embeddableConfig']['attributes']
    rows = esql(ttr['state']['query']['esql'], 'now-7d')
    days = [r['day'] for r in rows]
    oldest = min(datetime.fromisoformat(d.replace('Z', '+00:00')) for d in days)
    check('only incidents opened in the last 7 days', oldest >= NOW - timedelta(days=8), True)

    print('Layout (section 1)')
    sec = P['Active P1']['gridData']['sectionId']
    boxes = [(title(p), p['gridData']) for p in panels if p['gridData'].get('sectionId') == sec]
    cells = Counter((x, y) for _, g in boxes for x in range(g['x'], g['x'] + g['w']) for y in range(g['y'], g['y'] + g['h']))
    check('no overlaps', [c for c, n in cells.items() if n > 1], [])
    check('first row filled', all((x, y) in cells for x in range(48) for y in range(10)), True)
finally:
    for old in (IDX, SLA):
        call('DELETE', f'/{old}')

print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
