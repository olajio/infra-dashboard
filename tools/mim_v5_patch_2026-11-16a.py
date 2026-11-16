"""MIM V5 patch 16a (16 Nov 2026), on top of 13c: the alert panels' time range from 5 years to 7 days.

Usage: mim_v5_patch_2026-11-16a.py "MIM V5.ndjson" "MIM V5.ndjson"
"Open Alerts with No Incident" and its tile "Open alerts, no incident" showed "Last 5 years" only because they also
read the CMDB links (cmdb-ci-relations) and a panel's range filters every index it reads. R2 (16 Nov, r2.csv): every
link is re-sent daily (62,533 records, 51,115 links, all in the last 24 h), so 7 days keeps every link. The alerts
themselves stay limited to the last 24 h by the query, as before.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
dash = json.loads([l for l in open(SRC) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
done = []
for p in panels:
    ec = p['embeddableConfig']
    t = ec.get('title') or (ec.get('savedVis') or {}).get('title')
    if t in ('Open Alerts with No Incident', 'Open alerts, no incident'):
        assert ec.get('time_range', {}).get('from') == 'now-5y', (t, ec.get('time_range'))
        ec['time_range'] = {'from': 'now-7d', 'to': 'now'}
        done.append(t)
assert sorted(done) == ['Open Alerts with No Incident', 'Open alerts, no incident'], done
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: {", ".join(done)} now Last 7 days')
