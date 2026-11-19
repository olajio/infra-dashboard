"""MIM V5 patch 19e (19 Nov 2026): section 2's CMDB panels in one row, as in new_row.png. Layout only.

Usage: mim_v5_patch_2026-11-19e.py "MIM V5.ndjson" "MIM V5.ndjson"

Blast radius, Applications related to this CI, Server View, Middleware View, Database View, Other related CIs, left
to right, in the row under Changes (widths 4 9 9 9 9 8, same height as before). Nothing else changes.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
ROW = [('Blast radius', 4), ('Applications related to this CI', 9), ('Server View', 9), ('Middleware View', 9),
       ('Database View', 9), ('Other related CIs', 8)]
dash = json.loads([l for l in open(SRC) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
P = {p['embeddableConfig'].get('title'): p for p in panels}
y, h = P['Blast radius']['gridData']['y'], P['Blast radius']['gridData']['h']
assert all(P[t]['gridData']['sectionId'] == P['Blast radius']['gridData']['sectionId'] for t, _ in ROW)
x = 0
for t, w in ROW:
    P[t]['gridData'].update(x=x, y=y, w=w, h=h)
    x += w
assert x == 48
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: CMDB panels in one row')
