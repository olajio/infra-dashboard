"""(Superseded by test_mim_v5_2026-11-17d.py.) Check MIM V5 patch 17c: P1 MTTR from the time the incident became a P1 (incident timeline), P2 Duration, Linked
incidents, On Hold P1s shown (table and tiles), Time to Resolve P1 line = MTTR.
Local Elasticsearch (9200), own data; expected values are worked out by hand here, independently of the queries.
Usage: test_mim_v5_2026-11-17c.py "MIM V5.ndjson"
"""
import json
import statistics
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

NOW = datetime.now(timezone.utc).replace(microsecond=0)
TODAY = NOW.replace(hour=0, minute=0, second=0)
iso = lambda d: d.strftime('%Y-%m-%dT%H:%M:%S.000Z')
INC, TL = 'servicenow-incidents-t17c', 'servicenow-incident-timelines-t17c'
H = lambda h: timedelta(hours=h)


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


def esql(q, rng):
    r = call('POST', '/_query?format=json', {'query': q, 'filter': {'range': {'@timestamp': {'gte': rng['from'], 'lte': rng['to']}}}})
    assert 'error' not in r, json.dumps(r)[:1500]
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']]


for i in [r['index'] for r in call('GET', '/_cat/indices?format=json&h=index&expand_wildcards=all')
          if r['index'].startswith(('servicenow-incidents', 'servicenow-incident-timelines'))]:
    call('DELETE', f'/{i}')
K, D = {'type': 'keyword'}, {'type': 'date'}
obj = lambda **p: {'properties': p}
common = {'@timestamp': D, 'number': K, 'priority': {'type': 'integer'}, 'state_name': K, 'opened_at': D, 'resolved_at': D,
          'updated_at': D, 'resolution_time': {'type': 'integer'}, 'parent_incident': obj(number=K), 'ci': obj(name=K),
          'short_description': K, 'assigned_to': obj(name=K, email=K),
          'assignment_group': obj(name=K, manager=obj(name=K, email=K))}
# the timeline maps some fields to other types than the incidents (as in production: priority is a byte there), and
# resolution_time is a long on the incidents here, to check the queries cope with the mismatch
call('PUT', f'/{INC}', {'mappings': {'properties': dict(common, resolution_time={'type': 'long'})}})
call('PUT', f'/{TL}', {'mappings': {'properties': dict(common, priority={'type': 'byte'})}})

inc_docs, tl_docs = [], []


def inc(n, pri, state, opened, resolved=None, rt=None, parent=None, ts=None):
    d = {'@timestamp': iso(ts or resolved or NOW - timedelta(minutes=5)), 'number': n, 'priority': pri, 'state_name': state,
         'opened_at': iso(opened), 'ci': {'name': f'ci-{n}'}, 'short_description': f'{n} broken',
         'assignment_group': {'name': 'Grp'}, 'updated_at': iso(ts or resolved or NOW - timedelta(minutes=5))}
    if resolved:
        d['resolved_at'] = iso(resolved)
    if rt is not None:
        d['resolution_time'] = rt
    if parent:
        d['parent_incident'] = {'number': parent}
    inc_docs.append(d)


def tl(n, opened, history, current_pri, last_update):
    """history = [(time, priority)]; plus the timeline's current record (@timestamp = opened, updated_at = last update)."""
    for t, p in history:
        tl_docs.append({'@timestamp': iso(t), 'updated_at': iso(t), 'number': n, 'priority': p, 'opened_at': iso(opened)})
    tl_docs.append({'@timestamp': iso(opened), 'updated_at': iso(last_update), 'number': n, 'priority': current_pri,
                    'opened_at': iso(opened)})


# --- active incidents ---
oA = NOW - H(10)
inc('INCA', 1, 'In Progress', oA)                                          # P3 -> P2 -> P1 six hours ago
tl('INCA', oA, [(oA + timedelta(minutes=1), 3), (NOW - H(9), 2), (NOW - H(6), 1), (NOW - H(1), 1)], 1, NOW - H(1))
for k in ('INCK1', 'INCK2', 'INCK3'):
    inc(k, 3, 'In Progress', NOW - H(5), parent='INCA')                    # child incidents of INCA
inc('INCK4', 2, 'In Progress', NOW - H(12), parent='INCA')                 # child of INCA, and itself a P2 over 8 h
oB = NOW - H(4)
inc('INCB', 1, 'In Progress', oB)                                          # opened as a P1
tl('INCB', oB, [(oB + timedelta(minutes=2), 1)], 1, oB + timedelta(minutes=2))
inc('INCC', 1, 'On Hold', NOW - H(2))                                      # On Hold P1, no timeline record yet
inc('INCD', 2, 'On Hold', NOW - H(20))                                     # On Hold P2: not shown
inc('INCE', 2, 'In Progress', NOW - H(10))                                 # P2 over 8 h
inc('INCF', 2, 'In Progress', NOW - H(3))                                  # P2 under 8 h: not shown
inc('INCG', 1, 'Resolved', NOW - H(30), resolved=NOW - H(3))               # resolved P1: not in the table

# --- resolved incidents for the chart ---
r1 = TODAY - timedelta(days=1) + H(1); o1 = r1 - H(20)                     # P1: P3 at open, P1 8 h later -> MTTR 12 h
inc('INCR1', 1, 'Resolved', o1, resolved=r1, rt=20 * 3600)
tl('INCR1', o1, [(o1 + timedelta(minutes=5), 3), (o1 + H(8), 1)], 1, r1)
r2 = TODAY - timedelta(days=2) + H(1); o2 = r2 - H(5)                      # P1 opened as a P1 -> 5 h
inc('INCR2', 1, 'Resolved', o2, resolved=r2, rt=5 * 3600)
tl('INCR2', o2, [(o2 + timedelta(minutes=10), 1)], 1, r2)
r3 = TODAY - timedelta(days=1) + H(1)                                      # P2 with resolution_time 11 h (dates say 10 h)
inc('INCR3', 2, 'Resolved', r3 - H(10), resolved=r3, rt=11 * 3600)
r4 = TODAY - timedelta(days=3) + H(1)                                      # P2 without resolution_time -> dates, 6 h
inc('INCR4', 2, 'Resolved', r4 - H(6), resolved=r4)
r5 = TODAY - timedelta(days=20) + H(1)                                     # resolved 20 days ago: left out
inc('INCR5', 1, 'Resolved', r5 - H(2), resolved=r5, rt=7200)
# INCG resolved 3 h ago, P1, no timeline -> from opened, 27 h
CHART = [('INCR1', 1, r1, 12.0), ('INCR2', 1, r2, 5.0), ('INCR3', 2, r3, 11.0), ('INCR4', 2, r4, 6.0),
         ('INCG', 1, NOW - H(3), 27.0)]

for idx, docs in ((INC, inc_docs), (TL, tl_docs)):
    r = call('POST', '/_bulk?refresh=true', ''.join(json.dumps({'index': {'_index': idx}}) + '\n' + json.dumps(x) + '\n'
                                                    for x in docs), nd=True)
    assert not r.get('errors'), json.dumps(r)[:800]

dash = json.loads([l for l in open(sys.argv[1]) if l.strip()][0])
P = {(p['embeddableConfig'].get('title')): p for p in json.loads(dash['attributes']['panelsJSON'])}
try:
    ec = P['Active Incidents (P1 · P2 over 8 h)']['embeddableConfig']
    rows = esql(ec['attributes']['state']['query']['esql'], ec['time_range'])
    check('Active Incidents rows: P1s (On Hold included) then P2s over 8 h, longest first',
          [(r['number'], r['priority'], r['state_name'], r['hours_open'], r['linked_incidents']) for r in rows],
          [('INCA', 1, 'In Progress', 6.0, 4), ('INCB', 1, 'In Progress', 4.0, 0), ('INCC', 1, 'On Hold', 2.0, 0),
           ('INCK4', 2, 'In Progress', 12.0, 0), ('INCE', 2, 'In Progress', 10.0, 0)])
    st = ec['attributes']['state']
    (layer,) = st['datasourceStates']['textBased']['layers'].values()
    labels = {c['columnId']: c['label'] for c in layer['columns']}
    check('new columns and labels', (labels.get('hours_open'), labels.get('linked_incidents')),
          ('Time as P1 / Duration (h)', 'Linked incidents'))
    check('table columns = query columns', [c['columnId'] for c in st['visualization']['columns']], list(rows[0].keys()))
    check('no SLA records read any more', 'task-sla' in st['query']['esql'], False)

    tiles = {}
    for t in ('Needs attention now', 'Active P1', 'P2 over 8 h'):
        tec = P[t]['embeddableConfig']
        q = json.loads(tec['savedVis']['params']['spec'])['data'][0]['url']['query']
        tiles[t] = esql(q, tec.get('time_range') or {'from': 'now-7d', 'to': 'now'})[0]
    check('Active P1 tile counts the On Hold P1', tiles['Active P1']['incidents'], 3)
    check('P2 over 8 h tile (On Hold P2 left out)', tiles['P2 over 8 h']['incidents'], 2)
    check('Needs attention now = Active Incidents rows', (tiles['Needs attention now']['p1'], tiles['Needs attention now']['p2']), (3, 2))
    check('tile descriptions: no "1, 2 or 3" left', [t for t in tiles if '2 or 3' in (P[t]['embeddableConfig'].get('description') or '')], [])

    want = []
    for back in range(6, -1, -1):
        day = TODAY - timedelta(days=back)
        inw = [(p, h, n) for n, p, r, h in CHART if 0 <= (day - r.replace(hour=0, minute=0, second=0)).days <= 6]
        if not inw:
            continue
        med = lambda pr: round(statistics.median([h for p, h, _ in inw if p == pr]), 1) if any(p == pr for p, _, _ in inw) else None
        want.append((day.strftime('%Y-%m-%d'), med(1), med(2), len(inw)))
    tec = P['P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)']['embeddableConfig']
    rows = esql(tec['attributes']['state']['query']['esql'], tec['time_range'])
    check('Time to Resolve: P1 = MTTR from became-P1, P2 = Duration (resolution_time, else dates), rolling 7-day median',
          [(x['day'][:10], x['p1_hours'], x['p2_hours'], x['incidents']) for x in rows], want)
    check('Time to Resolve reads 30 days', tec['time_range'], {'from': 'now-30d', 'to': 'now'})
finally:
    for i in (INC, TL):
        call('DELETE', f'/{i}')
print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
