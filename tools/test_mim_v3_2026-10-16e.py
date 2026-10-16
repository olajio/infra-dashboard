"""Check the fifth 16 Oct round: Time to Resolve covers P1-P3 with targets 4 h / 8 h / 24 h, counts each incident once,
plots open incidents by their age so far (the live P1 that did not show), leaves canceled ones out, always draws
points, uses a log axis; Active Incidents compares a P3 without an SLA record with 24 h.

Usage: test_mim_v3_2026-10-16e.py MIM_V3_NDJSON
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

ES = 'http://localhost:9200'
NOW = datetime.now(timezone.utc)
iso = lambda t: t.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
TITLE = 'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)'
IDX = 'servicenow-incidents-t16e'


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request(ES + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return {'error': json.loads(e.read())}


for old in ('servicenow-incidents-t', 'servicenow-incidents-t16', 'servicenow-incidents-t16d', IDX):
    call('DELETE', f'/{old}')
call('PUT', f'/{IDX}', {'mappings': {'properties': {
    '@timestamp': {'type': 'date'}, 'number': {'type': 'keyword'}, 'priority': {'type': 'integer'},
    'state_name': {'type': 'keyword'}, 'opened_at': {'type': 'date'}, 'resolved_at': {'type': 'date'},
    'resolution_time': {'type': 'long'}}}})
day = (NOW - timedelta(days=3)).replace(hour=8, minute=0, second=0, microsecond=0)   # one fixed opened day
docs = []


def inc(n, pri, state, opened, hours=None, copies=1):
    for _ in range(copies):
        d = {'@timestamp': iso(NOW - timedelta(minutes=1)), 'number': n, 'priority': pri, 'state_name': state,
             'opened_at': iso(opened)}
        if hours is not None:
            d.update(resolution_time=int(hours * 3600), resolved_at=iso(opened + timedelta(hours=hours)))
        docs.append(d)


inc('INC1', 1, 'Resolved', day, 2.0, copies=3)        # synced three times: must count once
inc('INC2', 1, 'Resolved', day + timedelta(hours=1), 6.0)
inc('INC3', 3, 'Closed', day, 30.0)
inc('INC4', 3, 'Canceled', day, 1.0)                 # canceled: left out
inc('INC5', 2, 'Resolved', day, 9.0)
inc('INC6', 1, 'In Progress', NOW - timedelta(hours=5))   # the live P1
inc('INC7', 4, 'Resolved', day, 1.0)                 # P4: left out
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


def esql(q):
    r = call('POST', '/_query?format=json', {'query': q, 'filter': {'range': {'@timestamp': {'gte': 'now-1M'}}}})
    assert 'error' not in r, json.dumps(r)[:900]
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']]


st = P[TITLE]['embeddableConfig']['attributes']['state']
vis = st['visualization']
layers = st['datasourceStates']['textBased']['layers']
data_id = next(l['layerId'] for l in vis['layers'] if l['layerType'] == 'data')
ref = next(l for l in vis['layers'] if l['layerType'] == 'referenceLine')
rows = esql(layers[data_id]['query']['esql'])
got = [(r['pri'], r['day'][:10], r['avg_hours'], r['incidents'], r['open_now']) for r in rows]
check('per incident, open by age so far, canceled and P4 out', got, [
    ('P1', iso(day)[:10], 4.0, 2, 0),                     # INC1 once (2 h) + INC2 (6 h)
    ('P1', iso(NOW - timedelta(hours=5))[:10], 5.0, 1, 1),  # the live P1, 5 h so far
    ('P2', iso(day)[:10], 9.0, 1, 0),
    ('P3', iso(day)[:10], 30.0, 1, 0)])
check('target lines', (esql(layers[ref['layerId']]['query']['esql']),
                       [(y['forAccessor'], y['color'], y['lineStyle']) for y in ref['yConfig']]),
      ([{'p1_target': 4.0, 'p2_target': 8.0, 'p3_target': 24.0}],
       [('p1_target', '#d6453d', 'dashed'), ('p2_target', '#c98a0b', 'dashed'), ('p3_target', '#3f6fb5', 'dashed')]))
check('P3 colour', [a['color']['colorCode'] for a in next(l for l in vis['layers'] if l['layerType'] == 'data')
                    ['colorMapping']['assignments']], ['#d6453d', '#c98a0b', '#3f6fb5'])
check('points always drawn, log axis', (vis.get('pointVisibility'), vis.get('yLeftScale')), ('always', 'log'))
check('both query copies agree', st['query']['esql'] == layers[data_id]['query']['esql'], True)
q = P['Active Incidents (P1 / P2 / P3)']['embeddableConfig']['attributes']['state']['query']['esql']
check('Active Incidents: P3 compared with 24 h', 'target = CASE(priority == 1, 240, priority == 2, 480, 1440)' in q, True)
call('DELETE', f'/{IDX}')
print('\n' + ('ALL CHECKS PASSED' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
