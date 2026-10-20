"""MIM V3: remove SLO Error Burn Rate and Business applications impacted (20 Oct 2026).

Usage: mim_v3_patch_2026-10-20q.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-20p.py)

- SLO Error Burn Rate (end of section 2): removed at the user's request.
- Business applications impacted (end of section 3): empty for almost every incident (it needs APM services on the CI
  that other instrumented services call over HTTP in the last hour), and Downstream already lists each calling
  service with its business application and support group.
Both were the last panel of their section, so nothing else moves.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
GONE = ('SLO Error Burn Rate', 'Business applications impacted')

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
assert all(sum(title(p) == t for p in panels) == 1 for t in GONE)
for t in GONE:                                   # each is the last panel of its section
    g = next(p for p in panels if title(p) == t)['gridData']
    assert all(q['gridData']['y'] < g['y'] + g['h'] or q['gridData'].get('sectionId') != g['sectionId']
               for q in panels if title(q) != t and q['gridData']['y'] >= g['y']), t
panels = [p for p in panels if title(p) not in GONE]
assert not any(t in json.dumps(panels, ensure_ascii=False) for t in GONE)
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'removed {GONE}; {len(panels)} panels left')
