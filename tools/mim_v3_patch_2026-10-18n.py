"""MIM V3: the seven health panels move from section 2 to section 3, right after the Upstream / Service health /
Downstream row; "Applications on this CI" is renamed "APM Services Health" (18 Oct 2026).

Usage: mim_v3_patch_2026-10-18n.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-18m.py)

Section 3, after the dependency row (y 12-23), three columns of 16:
  Middleware Health · Database Health · Server Health
  APM Services Health · Process Health · Synthetics Health
  Errors from the Logs (full width)
then Business applications impacted. SLO Error Burn Rate, now alone at the end of section 2, takes the full width.
The panels' queries are unchanged: they still follow the chosen server and the Health window.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
OLD, NEW = 'Applications on this CI', 'APM Services Health'

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = lambda t: next(p for p in panels if title(p) == t)
sec = {s['title']: s['gridData']['i'] for s in A['sections']}
S2, S3 = sec['2 · Investigate the CI'], sec['3 · Application & Service Health, Dependencies']

# ------------------------------------------------------------------ rename
p = P(OLD)
p['embeddableConfig']['title'] = NEW
if p['embeddableConfig'].get('attributes', {}).get('title') == OLD:
    p['embeddableConfig']['attributes']['title'] = NEW
for q in panels:
    d = q['embeddableConfig'].get('description')
    if d and OLD in d:
        q['embeddableConfig']['description'] = d.replace(f'"{OLD}"', f'"{NEW}"').replace(OLD, NEW)

# ------------------------------------------------------------------ move into section 3
dep_row = [P(t)['gridData'] for t in ('⬅ Upstream — what they depend on', 'Service health', 'Downstream — who is impacted ➡')]
assert all(g['sectionId'] == S3 for g in dep_row)
y0 = max(g['y'] + g['h'] for g in dep_row)
layout = [('Middleware Health', 0, 0, 16), ('Database Health', 16, 0, 16), ('Server Health', 32, 0, 16),
          (NEW, 0, 10, 16), ('Process Health', 16, 10, 16), ('Synthetics Health', 32, 10, 16),
          ('Errors from the Logs', 0, 20, 48)]
for t, x, dy, w in layout:
    g = P(t)['gridData']
    assert g['sectionId'] == S2, t
    g.update(sectionId=S3, x=x, y=y0 + dy, w=w, h=10)
moved_end = y0 + 30
for q in panels:   # anything below the dependency row in section 3 goes after the moved panels
    g = q['gridData']
    if g.get('sectionId') == S3 and title(q) not in [t for t, *_ in layout] and g['y'] >= y0:
        g['y'] += moved_end - y0

# ------------------------------------------------------------------ SLO Error Burn Rate: full width in section 2
g = P('SLO Error Burn Rate')['gridData']
assert g['sectionId'] == S2
g.update(x=0, w=48, h=12)

# ------------------------------------------------------------------ checks
s3 = sorted((q['gridData']['y'], q['gridData']['x'], title(q)) for q in panels if q['gridData'].get('sectionId') == S3)
assert [t for *_, t in s3][-1] == 'Business applications impacted', s3
assert OLD not in json.dumps(panels)
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print('section 3:', [t for *_, t in s3])
