"""(Superseded by test_mim_v5_2026-11-17c.py.) Check MIM V5 patch 17b: Time to Resolve vs Target = rolling 7-day median per day, P1 / P2 only, last 7 days.
Local Elasticsearch (9200), own data; the expected values are computed here independently of the query.
Usage: test_mim_v5_2026-11-17b.py "MIM V5.ndjson"
"""
import json
import statistics
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

NOW = datetime.now(timezone.utc)
TODAY = NOW.replace(hour=0, minute=0, second=0, microsecond=0)
iso = lambda d: d.strftime('%Y-%m-%dT%H:%M:%S.000Z')
IDX = 'servicenow-incidents-t17b'


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


for i in [r['index'] for r in call('GET', '/_cat/indices?format=json&h=index&expand_wildcards=all') if r['index'].startswith('servicenow-incidents')]:
    call('DELETE', f'/{i}')
D = {'type': 'date'}
call('PUT', f'/{IDX}', {'mappings': {'properties': {'@timestamp': D, 'number': {'type': 'keyword'}, 'priority': {'type': 'integer'},
                                                    'state_name': {'type': 'keyword'}, 'opened_at': D, 'resolved_at': D}}})
# (number, priority, days before today it was resolved (at 01:00 UTC), hours to resolve)
SPEC = [('INC1', 2, 1, 4), ('INC2', 2, 1, 10), ('INC3', 1, 3, 2), ('INC4', 2, 5, 20), ('INC5', 2, 9, 30),
        ('INC6', 1, 12, 6), ('INC7', 3, 1, 50), ('INC8', 2, 20, 99), ('INC9', 4, 2, 1)]
docs = []
for n, p, ago_d, h in SPEC:
    resolved = TODAY - timedelta(days=ago_d) + timedelta(hours=1)
    docs.append({'@timestamp': iso(resolved), 'number': n, 'priority': p, 'state_name': 'Resolved',
                 'opened_at': iso(resolved - timedelta(hours=h)), 'resolved_at': iso(resolved)})
docs.append({'@timestamp': iso(NOW), 'number': 'INC10', 'priority': 1, 'state_name': 'New', 'opened_at': iso(NOW - timedelta(hours=3))})
assert not call('POST', '/_bulk?refresh=true', ''.join(json.dumps({'index': {'_index': IDX}}) + '\n' + json.dumps(x) + '\n' for x in docs), nd=True).get('errors')

# expected: for each of the last 7 days, the incidents resolved in [day - 6, day]
want = []
for back in range(6, -1, -1):
    day = TODAY - timedelta(days=back)
    inw = [(p, h) for n, p, ago_d, h in SPEC if p in (1, 2) and ago_d <= 14 and 0 <= (day - (TODAY - timedelta(days=ago_d))).days <= 6]
    if not inw:
        continue
    med = lambda pr: round(statistics.median([h for p, h in inw if p == pr]), 1) if any(p == pr for p, _ in inw) else None
    want.append((day.strftime('%Y-%m-%d'), med(1), med(2), len(inw)))

dash = json.loads([l for l in open(sys.argv[1]) if l.strip()][0])
P = {p['embeddableConfig'].get('title'): p for p in json.loads(dash['attributes']['panelsJSON'])}
ec = P['P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)']['embeddableConfig']
try:
    r = call('POST', '/_query?format=json', {'query': ec['attributes']['state']['query']['esql'],
                                              'filter': {'range': {'@timestamp': {'gte': 'now-14d', 'lte': 'now'}}}})
    assert 'error' not in r, r
    cols = [c['name'] for c in r['columns']]
    rows = [dict(zip(cols, v)) for v in r['values']]
    check('rolling 7-day median per day, P1 / P2 only (P3, P4, open and > 14-day-old incidents left out)',
          [(x['day'][:10], x['p1_hours'], x['p2_hours'], x['incidents']) for x in rows], want)
    check('only the last 7 days shown', all(x['day'][:10] >= (TODAY - timedelta(days=6)).strftime('%Y-%m-%d') for x in rows), True)
    check('columns', cols, ['day', 'p1_hours', 'p2_hours', 'incidents', 'open_now'])
    check('panel reads 14 days', ec['time_range'], {'from': 'now-14d', 'to': 'now'})
    check('axis title', ec['attributes']['state']['visualization']['yTitle'], 'Hours to resolve (rolling 7-day median)')
    ref = [l for l in ec['attributes']['state']['datasourceStates']['textBased']['layers'].values() if 'p2_target' in json.dumps(l)][0]
    check('targets', ref['query']['esql'], 'ROW p1_target = 4.0, p2_target = 8.0')
finally:
    call('DELETE', f'/{IDX}')
print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
