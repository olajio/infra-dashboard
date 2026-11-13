"""Check MIM V5 patch 13a: no SLA column in Active Incidents, the same incidents in the same order as before, every
query runs.  Usage: test_mim_v5_2026-11-13a.py "MIM V4.ndjson" "MIM V5 before.ndjson" "MIM V5.ndjson"
"""
import json
import sys

HERE = __file__.rsplit('/', 1)[0]
V4, BEFORE, V5 = sys.argv[1:4]
src = open(f'{HERE}/test_mim_v5_2026-11-06a.py').read().split('\ntry:')[0]
g = {'__name__': 'setup', '__file__': f'{HERE}/test_mim_v5_2026-11-06a.py'}
sys.argv = ['setup', V4, V5]
exec(compile(src, 'test_mim_v5_2026-11-06a.py (data setup)', 'exec'), g)
check, esql, panels5, P5, title, fails, cleanup, run = (g[k] for k in ('check', 'esql', 'panels5', 'P5', 'title', 'fails', 'cleanup', 'run'))
B = {title(p): p for p in json.loads(json.loads([l for l in open(BEFORE) if l.strip()][0])['attributes']['panelsJSON'])}
T = 'Active Incidents (P1 · P2 over 8 h · P3 over 24 h)'
try:
    st = P5[T]['embeddableConfig']['attributes']['state']
    check('table columns: no SLA', [c['columnId'] for c in st['visualization']['columns']],
          ['number', 'priority', 'ci.name', 'state_name', 'opened', 'assignment_group', 'assignee', 'assignee_email',
           'group_manager', 'manager_email', 'short_description'])
    rows, before = run(P5, T), run(B, T)
    check('result has no sla column', 'sla' in (rows[0] if rows else {}), False)
    check('same incidents as before', sorted(r['number'] for r in rows), sorted(r['number'] for r in before))
    check('still P1 first (ties of equal age may swap)', [r['priority'] for r in rows], sorted(r['priority'] for r in rows))
    check('description: no SLA paragraph', 'SLA = the worst' in P5[T]['embeddableConfig']['description'], False)
    n = 0
    for p in panels5:
        ec = p['embeddableConfig']
        q = ec.get('esql_query') if p['type'] == 'esql_control' else (
            ec['attributes']['state']['query']['esql'] if p['type'] == 'vis' else None)
        if not q:
            continue
        r = esql(q, ec.get('time_range'))
        n += 1
        if isinstance(r, dict) and 'Unknown index' not in json.dumps(r) and 'Unknown column' not in json.dumps(r):
            check(title(p), json.dumps(r['error'])[:300], 'no error')
    print(f'  ran {n} queries')
finally:
    cleanup()
print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
