"""Check MIM V5 patch 16a: the two alert panels read the last 7 days, and still find the picked CI's linked CIs when
the CMDB links are recent (as in production: re-sent daily, R2 16 Nov).
Usage: test_mim_v5_2026-11-16a.py "MIM V4.ndjson" "MIM V5.ndjson"
"""
import json
import sys

HERE = __file__.rsplit('/', 1)[0]
V4, V5 = sys.argv[1:3]
src = open(f'{HERE}/test_mim_v5_2026-11-06a.py').read().split('\ntry:')[0]
g = {'__name__': 'setup', '__file__': f'{HERE}/test_mim_v5_2026-11-06a.py'}
sys.argv = ['setup', V4, V5]
exec(compile(src, 'test_mim_v5_2026-11-06a.py (data setup)', 'exec'), g)
check, run, P5, fails, cleanup, call, REL, ago = (g[k] for k in ('check', 'run', 'P5', 'fails', 'cleanup', 'call', 'REL', 'ago'))
OA, T = 'Open Alerts with No Incident', 'Open alerts, no incident'
try:
    for t in (OA, T):
        check(f'{t}: Last 7 days', P5[t]['embeddableConfig']['time_range'], {'from': 'now-7d', 'to': 'now'})
    # production links are re-sent daily: give the test links today's date
    call('POST', '/cmdb-ci-relations*/_update_by_query?refresh=true&conflicts=proceed', {'script': {'source': f"ctx._source['@timestamp'] = '{ago(hours=2)}'"}})
    keyf = lambda rows: sorted((r['ci.name'] or '-', r['alert_node']) for r in rows)
    check('CI = srvA: its linked CIs\' alerts still found', keyf(run(P5, OA, ci='srvA')),
          [('-', 'netC.cna.com'), ('App PROD', 'App PROD.cna.com'), ('netA', 'netA')])
    for v in ({}, {'ci': 'srvA'}, {'incident': 'INC801 · srvA'}):
        check(f'tile = table rows {v}', run(P5, T, **v)[0]['metric_val'], len(run(P5, OA, **v)))
finally:
    cleanup()
print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
