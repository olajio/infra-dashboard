"""Check MIM V5 patch 17a: no P3 anywhere (tiles, tables, controls), the same P1 / P2 rows as before, Needs attention
now = Active Incidents rows, Active Incidents w 29 and Time to Resolve w 19, no overlaps, every query runs.
Usage: test_mim_v5_2026-11-17a.py "MIM V4.ndjson" "MIM V5 before.ndjson" "MIM V5.ndjson"
(time to resolve itself: test_mim_v5_2026-11-13b.py)
"""
import json
import sys

HERE = __file__.rsplit('/', 1)[0]
V4, BEFORE, V5 = sys.argv[1:4]
src = open(f'{HERE}/test_mim_v5_2026-11-06a.py').read().split('\ntry:')[0]
g = {'__name__': 'setup', '__file__': f'{HERE}/test_mim_v5_2026-11-06a.py'}
sys.argv = ['setup', V4, V5]
exec(compile(src, 'test_mim_v5_2026-11-06a.py (data setup)', 'exec'), g)
check, esql, run, panels5, P5, title, fails, cleanup, d5 = (g[k] for k in ('check', 'esql', 'run', 'panels5', 'P5', 'title', 'fails', 'cleanup', 'd5'))
B = {title(p): p for p in json.loads(json.loads([l for l in open(BEFORE) if l.strip()][0])['attributes']['panelsJSON'])}
AI, TTR = 'Active Incidents (P1 · P2 over 8 h)', 'P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)'
try:
    check('no P3 tile; renamed panels present', ('P3 over 24 h' in P5, AI in P5, TTR in P5), (False, True, True))
    rows = run(P5, AI)
    old = run(B, 'Active Incidents (P1 · P2 over 8 h · P3 over 24 h)')
    check('Active Incidents: P1 / P2 only', sorted({r['priority'] for r in rows}), [1, 2])
    check('Active Incidents: the same P1 / P2 rows as before', sorted(r['number'] for r in rows),
          sorted(r['number'] for r in old if r['priority'] in (1, 2)))
    spec = json.loads(P5['Needs attention now']['embeddableConfig']['savedVis']['params']['spec'])
    na = esql(spec['data'][0]['url']['query'])[0]
    check('Needs attention now = Active Incidents rows (P1 + P2 over 8 h)', na['p1'] + na['p2'], len(rows))
    check('Needs attention now: no p3', 'p3' in json.dumps(spec), False)
    for v in d5['attributes']['pinned_panels']['panels'].values():
        c = v['config']
        if c.get('variable_name') == 'incident':
            opts = [r['incident'] for r in esql(c['esql_query'])]
            check('Incident control: no P3 incident (INC805)', any(o.startswith('INC805') for o in opts), False)
            check('Incident control: P1 / P2 still listed', any(o.startswith('INC801') for o in opts), True)
    esc = run(P5, 'Escalation Channel', ci='srvA')
    check('Escalation Channel on srvA: P1 / P2 only', sorted({r['esc_priority'] for r in esc}), [1, 2])
    s1 = P5['Active P1']['gridData']['sectionId']
    sec = [p for p in panels5 if p['gridData'].get('sectionId') == s1]
    gd = lambda t: (P5[t]['gridData']['x'], P5[t]['gridData']['w'])
    check('Active Incidents 25 % narrower, Time to Resolve takes the space', (gd(AI), gd(TTR)), ((0, 29), (29, 19)))
    row = sorted((p['gridData']['x'], p['gridData']['w']) for p in sec if p['gridData']['y'] == P5['Active P1']['gridData']['y'])
    check('tile row: six tiles across the full width', (len(row), sum(w for _, w in row)), (6, 48))
    cells = {}
    for p in sec:
        q = p['gridData']
        for x in range(q['x'], q['x'] + q['w']):
            for y in range(q['y'], q['y'] + q['h']):
                cells.setdefault((x, y), []).append(title(p))
    check('section 1: no overlaps', [c for c, ts in cells.items() if len(ts) > 1][:3], [])
    n = 0
    for p in panels5:
        ec = p['embeddableConfig']
        q = ec.get('esql_query') if p['type'] == 'esql_control' else (
            ec['attributes']['state']['query']['esql'] if p['type'] == 'vis' else None)
        if not q:
            continue
        for v in ({}, {'ci': 'srvA'}, {'incident': 'INC801 · srvA'}):
            r = esql(q, ec.get('time_range'), **v)
            n += 1
            if isinstance(r, dict) and 'Unknown index' not in json.dumps(r) and 'Unknown column' not in json.dumps(r):
                check(f'{title(p)} {v}', json.dumps(r['error'])[:300], 'no error')
    print(f'  ran {n} queries')
finally:
    cleanup()
print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
