"""Check MIM V5 patch 19a (Time to Resolve: 30 days of points, rolling 7-day median; health panels read 30 days) on top
of 18a / 18d (supersedes the 18a test). Earlier: MIM V5 patch 18a (P3 back, Priorities control, Age columns, Time to Resolve day labels and P3 line, Dashboard
Links) on top of 17c / 17d (supersedes the 17d test). 17c: P1 MTTR from the time the incident became a P1 (incident timeline), P2 Duration, Linked
incidents, On Hold P1s shown (table and tiles), Time to Resolve P1 line = MTTR.
Local Elasticsearch (9200), own data; expected values are worked out by hand here, independently of the queries.
Usage: test_mim_v5_2026-11-19a.py "MIM V5.ndjson" "Infrastructure Overview v2.ndjson"
"""
import json
import re
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


def esql(q, rng, **params):
    body = {'query': q, 'filter': {'range': {'@timestamp': {'gte': rng['from'], 'lte': rng['to']}}}}
    names = sorted(set(re.findall(r'\?([A-Za-z_]+)', q)))
    vals = dict({'priorities': ['P1', 'P2', 'P3'], 'incident': '(all incidents)', 'ci': '(no CI selected)'}, **params)
    if names:
        body['params'] = [{n: vals[n]} for n in names]
    r = call('POST', '/_query?format=json', body)
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
          'short_description': K, 'assigned_to': obj(name=K, email=K), 'ci': obj(name=K, class_name=K, environment=K, support_group=obj(l2=obj(name=K))),
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
for k, h in (('INCK1', 5), ('INCK2', 4), ('INCK3', 3)):
    inc(k, 3, 'In Progress', NOW - H(h), parent='INCA')                    # P3 child incidents of INCA (shown since 18a)
inc('INCK4', 2, 'In Progress', NOW - H(12), parent='INCA')                 # child of INCA, and itself a P2 over 8 h
oB = NOW - H(4)
inc('INCB', 1, 'In Progress', oB)                                          # opened as a P1
tl('INCB', oB, [(oB + timedelta(minutes=2), 1)], 1, oB + timedelta(minutes=2))
inc('INCC', 1, 'On Hold', NOW - H(2))                                      # On Hold P1, no timeline record yet
inc('INCD', 2, 'On Hold', NOW - H(20))                                     # On Hold P2: not shown
inc('INCE', 2, 'In Progress', NOW - H(10))                                 # P2 over 8 h
inc('INCF', 2, 'In Progress', NOW - H(3))                                  # P2 under 8 h: shown since 17d
inc('INCG', 1, 'Resolved', NOW - H(30), resolved=NOW - H(3))               # resolved P1: not in the table

inc('INCP3O', 3, 'In Progress', NOW - H(40))                               # P3 open 40 h: shown, age 1 d 16 h
inc('INCP3H', 3, 'On Hold', NOW - H(50))                                   # On Hold P3: not shown

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
r5 = TODAY - timedelta(days=20) + H(1)                                     # resolved 20 days ago: in the 30 days since 19a
inc('INCR5', 1, 'Resolved', r5 - H(2), resolved=r5, rt=7200)
r7 = TODAY - timedelta(days=25) + H(1)                                     # P2 25 days ago (previous month, usually)
inc('INCR7', 2, 'Resolved', r7 - H(4), resolved=r7, rt=4 * 3600)
r8 = TODAY - timedelta(days=33) + H(1)                                     # P3 33 days ago: in the first 3 windows only
inc('INCR8', 3, 'Resolved', r8 - H(9), resolved=r8, rt=9 * 3600)
r9 = TODAY - timedelta(days=45) + H(1)                                     # 45 days ago: left out
inc('INCR9', 2, 'Resolved', r9 - H(50), resolved=r9, rt=50 * 3600)
r6 = TODAY - timedelta(days=1) + H(1)                                      # P3 with resolution_time 30 h
inc('INCR6', 3, 'Resolved', r6 - H(30), resolved=r6, rt=30 * 3600)
# INCG resolved 3 h ago, P1, no timeline -> from opened, 27 h
CHART = [('INCR1', 1, r1, 12.0), ('INCR2', 1, r2, 5.0), ('INCR3', 2, r3, 11.0), ('INCR4', 2, r4, 6.0),
         ('INCG', 1, NOW - H(3), 27.0), ('INCR6', 3, r6, 30.0),
         ('INCR5', 1, r5, 2.0), ('INCR7', 2, r7, 4.0), ('INCR8', 3, r8, 9.0)]

for idx, docs in ((INC, inc_docs), (TL, tl_docs)):
    r = call('POST', '/_bulk?refresh=true', ''.join(json.dumps({'index': {'_index': idx}}) + '\n' + json.dumps(x) + '\n'
                                                    for x in docs), nd=True)
    assert not r.get('errors'), json.dumps(r)[:800]

dash = json.loads([l for l in open(sys.argv[1]) if l.strip()][0])
P = {(p['embeddableConfig'].get('title')): p for p in json.loads(dash['attributes']['panelsJSON'])}
AI = 'Active Incidents (P1 · P2 · P3)'
TTR = 'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)'
ALL = [('INCA', 1, 'In Progress', '10 h 0 m', 6.0, 4), ('INCB', 1, 'In Progress', '4 h 0 m', 4.0, 0),
       ('INCC', 1, 'On Hold', '2 h 0 m', 2.0, 0),
       ('INCK4', 2, 'In Progress', '12 h 0 m', 12.0, 0), ('INCE', 2, 'In Progress', '10 h 0 m', 10.0, 0),
       ('INCF', 2, 'In Progress', '3 h 0 m', 3.0, 0),
       ('INCP3O', 3, 'In Progress', '1 d 16 h', 40.0, 0), ('INCK1', 3, 'In Progress', '5 h 0 m', 5.0, 0),
       ('INCK2', 3, 'In Progress', '4 h 0 m', 4.0, 0), ('INCK3', 3, 'In Progress', '3 h 0 m', 3.0, 0)]
try:
    ec = P[AI]['embeddableConfig']
    q = ec['attributes']['state']['query']['esql']
    pick = lambda rows: [(r['number'], r['priority'], r['state_name'], r['age'], r['hours_open'], r['linked_incidents']) for r in rows]
    rows = esql(q, ec['time_range'])
    check('Active Incidents, every priority: P1 (On Hold included), P2, P3 (On Hold left out), longest first; Age',
          pick(rows), ALL)
    check('Priorities = P1 only', pick(esql(q, ec['time_range'], priorities=['P1'])), [r for r in ALL if r[1] == 1])
    check('Priorities = P2, P3', pick(esql(q, ec['time_range'], priorities=['P2', 'P3'])), [r for r in ALL if r[1] != 1])
    check('Priorities = P3 (one value, sent as a string)', pick(esql(q, ec['time_range'], priorities='P3')), [r for r in ALL if r[1] == 3])
    st = ec['attributes']['state']
    (layer,) = st['datasourceStates']['textBased']['layers'].values()
    check('table columns = query columns', [c['columnId'] for c in st['visualization']['columns']], list(rows[0].keys()))
    check('Age column label', {c['columnId']: c['label'] for c in layer['columns']}['age'], 'Age')

    tiles = {}
    for t in ('Needs attention now', 'Active P1', 'Active P2', 'Active P3'):
        tec = P[t]['embeddableConfig']
        tq = json.loads(tec['savedVis']['params']['spec'])['data'][0]['url']['query']
        tiles[t] = esql(tq, tec.get('time_range') or {'from': 'now-7d', 'to': 'now'})[0]
    check('tiles P1 / P2 / P3', [tiles[f'Active P{k}']['incidents'] for k in (1, 2, 3)], [3, 3, 4])
    na = tiles['Needs attention now']
    check('Needs attention now = Active Incidents rows, by priority', (na['p1'], na['p2'], na['p3']), (3, 3, 4))
    spec = P['Active P3']['embeddableConfig']['savedVis']['params']['spec']
    check('Active P3 tile in P3 blue', ('#3f6fb5' in spec, '#c98a0b' in spec), (True, False))
    na_spec = P['Needs attention now']['embeddableConfig']['savedVis']['params']['spec']
    check('Needs attention now strip has P3', ("'P3  ' + p3" in na_spec, '"P1 · P2 · P3"' in na_spec), (True, True))
    row = sorted((P[t]['gridData']['x'], P[t]['gridData']['w']) for t in P if P[t]['gridData'].get('y') == P['Active P1']['gridData']['y']
                 and P[t]['gridData'].get('sectionId') == P['Active P1']['gridData']['sectionId'])
    check('tile row: 7 tiles across the full width, no overlap', (len(row), sum(w for _, w in row),
                                                                   all(a + w <= b for (a, w), (b, _) in zip(row, row[1:]))), (7, 48, True))

    ec = P['Escalation Channel']['embeddableConfig']
    eq = ec['attributes']['state']['query']['esql']
    esc = esql(eq, ec['time_range'], ci='ci-INCP3O')
    check('Escalation Channel: P3 row with Age', [(r['number'], r['esc_priority'], r['esc_age']) for r in esc], [('INCP3O', 3, '1 d 16 h')])
    check('Escalation Channel: Priorities = P1 hides it', esql(eq, ec['time_range'], ci='ci-INCP3O', priorities=['P1']), [])

    want = []
    for back in range(29, -1, -1):
        day = TODAY - timedelta(days=back)
        inw = [(p, h, n) for n, p, r, h in CHART if 0 <= (day - r.replace(hour=0, minute=0, second=0)).days <= 6]
        if not inw:
            continue
        med = lambda pr: round(statistics.median([h for p, h, _ in inw if p == pr]), 1) if any(p == pr for p, _, _ in inw) else None
        want.append((day.strftime('%b %d'), med(1), med(2), med(3), len(inw)))
    tec = P[TTR]['embeddableConfig']
    tq = tec['attributes']['state']['query']['esql']
    rows = esql(tq, tec['time_range'])
    check('Time to Resolve reads 40 days; health panels 30 days', (tec['time_range'], sorted({P[t]['embeddableConfig']['time_range']['from'] for t in
          ('Server Health', 'Middleware Health', 'Database Health', 'Process Health', 'APM Services Health', 'Synthetics Health', 'Errors from the Logs')})),
          ({'from': 'now-40d', 'to': 'now'}, ['now-30d']))
    check('Time to Resolve: P1 MTTR, P2 / P3 Duration, rolling 7-day median, 30 days, day labels in order',
          [(x['day_label'], x['p1_hours'], x['p2_hours'], x['p3_hours'], x['incidents']) for x in rows], want)
    rows1 = esql(tq, tec['time_range'], priorities=['P1'])
    check('Time to Resolve with Priorities = P1: no P2 / P3 points',
          {(x['p2_hours'], x['p3_hours']) for x in rows1}, {(None, None)})
    vis = tec['attributes']['state']['visualization']
    dl = next(l for l in vis['layers'] if l['layerType'] == 'data')
    check('chart x axis = day label; three lines', (dl['xAccessor'], dl['accessors']), ('day_label', ['p1_hours', 'p2_hours', 'p3_hours']))
    ref = [l for l in tec['attributes']['state']['datasourceStates']['textBased']['layers'].values() if 'p3_target' in json.dumps(l)][0]
    check('targets', ref['query']['esql'], 'ROW p1_target = 4.0, p2_target = 8.0, p3_target = 24.0')

    pins = dash['attributes']['pinned_panels']['panels'].values()
    pr = next(v for v in pins if v['config']['variable_name'] == 'priorities')
    check('Priorities control: first, multi-select, P1-P3 selected',
          (pr['order'], pr['config']['single_select'], pr['config']['selected_options'], pr['config']['title']),
          (0, False, ['P1', 'P2', 'P3'], '🎚️ Priorities'))
    inc_ctl = next(v for v in pins if v['config']['variable_name'] == 'incident')['config']['esql_query']
    opts = [r['incident'] for r in esql(inc_ctl, {'from': 'now-7d', 'to': 'now'})]
    check('Incident control lists P3s', any(o.startswith('INCP3O') for o in opts), True)

    a = dash['attributes']
    s4 = next(s for s in a['sections'] if s['title'] == '🔗 4 · Dashboard Links')['gridData']['i']
    links = sorted((p['gridData']['y'], p['gridData']['x'], p['embeddableConfig']['content'])
                   for p in json.loads(a['panelsJSON']) if p['gridData'].get('sectionId') == s4)
    check('MIM Dashboard Links: Related Dashboards only', [c for *_, c in links], [
        '**↗ Related Dashboards**', '## 📈 Executive (In Progress)',
        '## 📊 [Portfolio ›](https://kibana-prod.gcp.cna.com/app/dashboards#/view/7511c5d1-3326-4c7e-91f4-6c8fdb686ee0)',
        '## 🛡️ [Application Operations ›](https://kibana-prod.gcp.cna.com/app/r/s/b4Jas)',
        '## 🚨 [Major Incident Management ›](https://kibana-prod.gcp.cna.com/app/r/s/ZSMtk)',
        '## 🧭 [Infra Overview ›](https://kibana-prod.gcp.cna.com/app/r/s/bUy3F)'])
    io = json.loads([l for l in open(sys.argv[2]) if l.strip()][0])['attributes']
    s2 = next(s for s in io['sections'] if 'Dashboard Links' in s['title'])['gridData']['i']
    io_rel = sorted((p['gridData']['x'], p['gridData']['w'], p['gridData']['h'], p['embeddableConfig']['content'])
                    for p in json.loads(io['panelsJSON']) if p['gridData'].get('sectionId') == s2 and p['gridData']['y'] in (0, 2))
    mim_rel = sorted((p['gridData']['x'], p['gridData']['w'], p['gridData']['h'], p['embeddableConfig']['content'])
                     for p in json.loads(a['panelsJSON']) if p['gridData'].get('sectionId') == s4)
    check('Related Dashboards identical on MIM and the Infrastructure Overview', mim_rel, io_rel)
    check('Infrastructure Overview keeps Detailed Dashboards', sum('Detailed Dashboards' in p['embeddableConfig'].get('content', '')
                                                                   for p in json.loads(io['panelsJSON'])), 1)
finally:
    for i in (INC, TL):
        call('DELETE', f'/{i}')
print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
