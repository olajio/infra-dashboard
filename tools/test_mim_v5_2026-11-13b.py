"""Check MIM V5 patch 13b: Time to Resolve vs Target averages opened -> resolved per resolution day and priority.
Local Elasticsearch (9200), own data.  Usage: test_mim_v5_2026-11-13b.py "MIM V5.ndjson"
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

NOW = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
if NOW > datetime.now(timezone.utc):
    NOW -= timedelta(days=1)      # noon today if it has passed, else noon yesterday: every test time is in the past
iso = lambda d: d.strftime('%Y-%m-%dT%H:%M:%S.000Z')
IDX = 'servicenow-incidents-t13b'


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request('http://localhost:9200' + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b'{}')


fails = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" + ('' if ok else f'\n          expected {want!r}'))
    if not ok:
        fails.append(name)


K, D = {'type': 'keyword'}, {'type': 'date'}
for i in [r['index'] for r in call('GET', '/_cat/indices?format=json&h=index&expand_wildcards=all') if r['index'].startswith('servicenow-incidents')]:
    call('DELETE', f'/{i}')
call('PUT', f'/{IDX}', {'mappings': {'properties': {'@timestamp': D, 'number': K, 'priority': {'type': 'integer'}, 'state_name': K,
                                                    'opened_at': D, 'resolved_at': D}}})
d0, d1 = NOW - timedelta(days=1), NOW - timedelta(days=3)


def inc(n, p, opened, resolved, state='Resolved'):
    return {'@timestamp': iso(resolved or opened), 'number': n, 'priority': p, 'state_name': state, 'opened_at': iso(opened),
            'resolved_at': iso(resolved) if resolved else None}


docs = [inc('INC1', 2, d0 - timedelta(hours=4), d0), inc('INC2', 2, d0 - timedelta(hours=10), d0),      # P2 day 0: 4 h, 10 h -> 7.0
        inc('INC3', 3, d0 - timedelta(hours=30), d0),                                                  # P3 day 0: 30 h
        inc('INC4', 3, d1 - timedelta(hours=12), d1), inc('INC5', 3, d1 - timedelta(hours=48), d1),     # P3 day -3: 12, 48 -> 30.0
        inc('INC6', 1, d1 - timedelta(hours=2), d1),                                                   # P1 day -3: 2 h
        inc('INC7', 3, NOW - timedelta(hours=5), None, 'New'),                                         # still open: not on the chart
        inc('INC8', 3, NOW - timedelta(days=20), NOW - timedelta(days=10)),                            # resolved 10 days ago: out
        inc('INC9', 4, d0 - timedelta(hours=1), d0)]                                                   # P4: out
assert not call('POST', '/_bulk?refresh=true', ''.join(json.dumps({'index': {'_index': IDX}}) + '\n' + json.dumps(x) + '\n' for x in docs), nd=True).get('errors')

dash = json.loads([l for l in open(sys.argv[1]) if l.strip()][0])
P = {p['embeddableConfig'].get('title'): p for p in json.loads(dash['attributes']['panelsJSON'])}
ec = P['P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)']['embeddableConfig']
q = ec['attributes']['state']['query']['esql']
try:
    r = call('POST', '/_query?format=json', {'query': q})
    assert 'error' not in r, r
    cols = [c['name'] for c in r['columns']]
    rows = [dict(zip(cols, v)) for v in r['values']]
    got = [(row['day'][:10], row['p1_hours'], row['p2_hours'], row['p3_hours'], row['incidents']) for row in rows]
    check('per resolution day: average hours opened -> resolved by priority, oldest day first', got,
          [(iso(d1)[:10], 2.0, None, 30.0, 3), (iso(d0)[:10], None, 7.0, 30.0, 3)])
    check('same columns as the chart expects', cols, ['day', 'p1_hours', 'p2_hours', 'p3_hours', 'incidents', 'open_now'])
    viz = ec['attributes']['state']['visualization']
    check('target lines kept (4 / 8 / 24 h), one axis', sorted({yc['axisMode'] for l in viz['layers'] for yc in l.get('yConfig', [])}), ['left'])
    ref = [l for l in ec['attributes']['state']['datasourceStates']['textBased']['layers'].values() if 'p3_target' in json.dumps(l)][0]
    check('targets', ref['query']['esql'], 'ROW p1_target = 4.0, p2_target = 8.0, p3_target = 24.0')
finally:
    call('DELETE', f'/{IDX}')
print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
