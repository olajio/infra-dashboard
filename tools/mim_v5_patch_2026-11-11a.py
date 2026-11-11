"""MIM V5 patch 11a (11 Nov 2026), on top of patch 06a: remove the "Alerts on this CI" panel (team request).

Usage: mim_v5_patch_2026-11-11a.py "MIM V5.ndjson" "MIM V5.ndjson"
"Changes in the Last 7 Days on this CI", which sat beside it, takes the full width of the row. Nothing else moves.
Netcool alerts stay on the dashboard in "Open Alerts with No Incident" (section 2) and its tile (section 1).
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
dash = json.loads([l for l in open(SRC) if l.strip()][0])
assert dash.get('type') == 'dashboard'
panels = json.loads(dash['attributes']['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
gone = [p for p in panels if title(p) == 'Alerts on this CI']
assert len(gone) == 1, 'already removed?'
panels.remove(gone[0])
chg = next(p for p in panels if title(p) == 'Changes in the Last 7 Days on this CI')
chg['gridData'].update({'x': 0, 'w': 48})
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: {len(panels)} panels')
