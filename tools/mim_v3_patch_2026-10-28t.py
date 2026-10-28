"""MIM V3: Applications Operations Dashboard link updated (28 Oct 2026).

Usage: mim_v3_patch_2026-10-28t.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-27s.py)

The "Applications Operations Dashboard ›" link (section 4, SRE dashboard card) now opens
https://kibana-prod.gcp.cna.com/app/r/s/uolFV (application_sre_link.txt) instead of .../b4Jas.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
OLD, NEW = 'https://kibana-prod.gcp.cna.com/app/r/s/b4Jas', 'https://kibana-prod.gcp.cna.com/app/r/s/uolFV'

dash = json.loads(open(SRC).readline())
panels = json.loads(dash['attributes']['panelsJSON'])
card = next(p for p in panels if p['embeddableConfig'].get('title') == 'SRE dashboard')
assert card['embeddableConfig']['content'].count(OLD) == 1, 'already applied?'
card['embeddableConfig']['content'] = card['embeddableConfig']['content'].replace(OLD, NEW)
s = json.dumps(panels, ensure_ascii=False)
assert OLD not in s and s.count(NEW) == 1
dash['attributes']['panelsJSON'] = s
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print('Applications Operations Dashboard link ->', NEW)
