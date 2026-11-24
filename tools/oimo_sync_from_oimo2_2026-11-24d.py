"""Make "Observability Incident Management Operations.ndjson" the same as "Observability Incident Management Operations
2.ndjson" (patches 24a-24c: Application Health, Upstream / Downstream filtered while reading, Services of the Application
5 years, tiles and banners fit their panel at any zoom), keeping the dashboard's own id and title so that importing it
replaces the existing "Observability Incident Management Operations" dashboard.

Usage: oimo_sync_from_oimo2_2026-11-24d.py "Observability Incident Management Operations 2.ndjson" \
           "Observability Incident Management Operations.ndjson"
"""
import json
import sys

SRC, DST = sys.argv[1:3]
src = [json.loads(l) for l in open(SRC) if l.strip()]
dst = [json.loads(l) for l in open(DST) if l.strip()]
(sd,) = [o for o in src if o.get('type') == 'dashboard']
(dd,) = [o for o in dst if o.get('type') == 'dashboard']
keep_id, keep_title = dd['id'], dd['attributes']['title']
out = json.loads(json.dumps(src))
(od,) = [o for o in out if o.get('type') == 'dashboard']
od['id'] = keep_id
od['attributes']['title'] = keep_title
with open(DST, 'w') as f:
    for o in out:
        f.write(json.dumps(o, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{DST}: same as {SRC}, id {keep_id}, title "{keep_title}"')
