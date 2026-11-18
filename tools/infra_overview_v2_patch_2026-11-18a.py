"""Infrastructure Overview v2, patch 18a (18 Nov 2026), on top of 17b / links 17f: Related Dashboards.

Usage: infra_overview_v2_patch_2026-11-18a.py "Infrastructure Overview v2.ndjson" "Infrastructure Overview v2.ndjson"

- Executive Dashboard (In Progress) is text again, not a link (same font).
- Order: Executive, Portfolio, Application Operations, Major Incident Management, Infra Overview (Infrastructure
  Overview and Major Incident Management swapped).
- Renamed: Portfolio Dashboard -> Portfolio, Applications Operations Dashboard -> Application Operations,
  Infrastructure Overview -> Infra Overview.
Detailed Dashboards stays on this dashboard (MIM V5 has Related Dashboards only, patch mim_v5_patch_2026-11-18a.py,
with the same Related tiles).
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
lines = [l for l in open(SRC) if l.strip()]
dash = json.loads(lines[0])
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
S2 = next(s['gridData']['i'] for s in A['sections'] if 'Dashboard Links' in s['title'])
R = 'https://kibana-prod.gcp.cna.com/app/r/s/'
RELATED = [('Executive', '## 📈 Executive Dashboard (In Progress)', 10),
           ('Portfolio', '## 📊 [Portfolio ›](https://kibana-prod.gcp.cna.com/app/dashboards#/view/7511c5d1-3326-4c7e-91f4-6c8fdb686ee0)', 9),
           ('Applications Operations', f'## 🛡️ [Application Operations ›]({R}b4Jas)', 10),
           ('Major Incident Management', f'## 🚨 [Major Incident Management ›]({R}ZSMtk)', 10),
           ('Infrastructure Overview', f'## 🧭 [Infra Overview ›]({R}bUy3F)', 9)]
tiles = {p['embeddableConfig']['title']: p for p in panels if p['gridData'].get('sectionId') == S2}
assert '](' in tiles['Executive link']['embeddableConfig']['content'], 'already patched, or 17b missing'
x = 0
for key, content, w in RELATED:
    t = tiles[f'{key} link']
    t['embeddableConfig']['content'] = content
    t['gridData'].update(x=x, y=2, w=w)
    x += w
assert x == 48
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
lines[0] = json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n'
open(OUT, 'w').write(''.join(l if l.endswith('\n') else l + '\n' for l in lines))
print(f'{OUT}: Related Dashboards renamed and reordered; Executive as text')
