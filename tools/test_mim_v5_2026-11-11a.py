"""Check MIM V5 patch 11a: "Alerts on this CI" removed, Changes full width, section 2 without gaps or overlaps, and
every query still runs (data of the 06a test).  Usage: test_mim_v5_2026-11-11a.py "MIM V4.ndjson" "MIM V5.ndjson"
"""
import json
import sys

HERE = __file__.rsplit('/', 1)[0]
V4, V5 = sys.argv[1:3]
src = open(f'{HERE}/test_mim_v5_2026-11-06a.py').read().split('\ntry:')[0]
g = {'__name__': 'setup', '__file__': f'{HERE}/test_mim_v5_2026-11-06a.py'}
sys.argv = ['setup', V4, V5]
exec(compile(src, 'test_mim_v5_2026-11-06a.py (data setup)', 'exec'), g)
check, esql, panels5, P5, title, fails, cleanup = (g[k] for k in ('check', 'esql', 'panels5', 'P5', 'title', 'fails', 'cleanup'))
try:
    check('no "Alerts on this CI" panel', 'Alerts on this CI' in P5, False)
    s2 = P5['Escalation Channel']['gridData']['sectionId']
    sec = [p for p in panels5 if p['gridData'].get('sectionId') == s2]
    gd = lambda t: {k: P5[t]['gridData'][k] for k in ('x', 'y', 'w', 'h')}
    check('Changes takes the full row', gd('Changes in the Last 7 Days on this CI'), {'x': 0, 'y': 11, 'w': 48, 'h': 11})
    cells = {}
    for p in sec:
        q = p['gridData']
        for x in range(q['x'], q['x'] + q['w']):
            for y in range(q['y'], q['y'] + q['h']):
                cells.setdefault((x, y), []).append(title(p))
    check('section 2: no overlaps', [c for c, ts in cells.items() if len(ts) > 1][:3], [])
    bottom = max(q['gridData']['y'] + q['gridData']['h'] for q in sec)
    check('section 2: no gaps', sorted((x, y) for x in range(48) for y in range(bottom) if (x, y) not in cells)[:3], [])
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
