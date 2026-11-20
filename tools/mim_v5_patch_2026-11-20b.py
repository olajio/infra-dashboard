"""MIM V5 patch 20b (20 Nov 2026): six data-ingestion items added to the Next Release Roadmap panel (Future Releases
section). Only that panel changes: its text, and one grid row taller (22 -> 23) so the added lines fit with no scrollbar.

Usage: mim_v5_patch_2026-11-20b.py "MIM V5.ndjson" "MIM V5.ndjson"
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
LAST = '✅ Linked incidents over the whole life of a P1 (today: those updated in the last 7 days)\n'
NEW = ['Ingest Critical outage record data into Elasticsearch',
       'Ingest Critical start time field into Elasticsearch',
       'Ingest Critical Impact Mitigated field into Elasticsearch',
       'Ingest P1 Duration field into Elasticsearch',
       'Ingest PBA related field to Elastic',
       'Ingest Managed-P2 (mp2) incident documents into Elasticsearch']
dash = json.loads([l for l in open(SRC) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
(p,) = [p for p in panels if p['embeddableConfig'].get('title') == 'Next Release Roadmap']
c = p['embeddableConfig']['content']
assert c.count(LAST) == 1 and not any(n in c for n in NEW)
p['embeddableConfig']['content'] = c.replace(LAST, LAST + ''.join(f'✅ {n}\n' for n in NEW))
assert p['gridData']['h'] == 22
p['gridData']['h'] = 23
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: {len(NEW)} items added to the Next Release Roadmap')
