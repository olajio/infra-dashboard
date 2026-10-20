"""MIM V3: the section 3 controls move into section 3; Users impacted splits into two "in progress" tiles
(20 Oct 2026).

Usage: mim_v3_patch_2026-10-20o.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-18n.py)

- Server, Health window, Service and Application only drive section 3 panels, so they leave the pinned bar at the top
  and become the first row of section 3 (Kibana >= 9.4 stores a control in the grid as an `esql_control` panel; its
  variable still applies to the whole dashboard). Incident and CI stay pinned: they drive sections 2 and 3.
- Users impacted (a demo number) becomes two tiles, stacked in the same place: "User base · ServiceNow" and
  "Real users · RUM", both "In progress". The 2,500 demo number is gone.
"""
import copy
import json
import sys
import uuid

SRC, OUT = sys.argv[1:3]
NS = uuid.UUID('5b1c7a8e-29a4-4a52-9d5e-6f1f3f0f0d18')
uid = lambda name: str(uuid.uuid5(NS, name))

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = lambda t: next(p for p in panels if title(p) == t)
sec = {s['title']: s['gridData']['i'] for s in A['sections']}
S1, S3 = sec['1 · Major Incident Overview'], sec['3 · Application & Service Health, Dependencies']

# ------------------------------------------------------------------ controls: pinned bar -> first row of section 3
pinned = A['pinned_panels']['panels']
by = {c['config']['title']: k for k, c in pinned.items()}
ROW_H = 3
row = [('Server', 0, 12), ('Health window', 12, 8), ('Service', 20, 14), ('Application', 34, 14)]
for p in panels:                               # make room at the top of section 3
    if p['gridData'].get('sectionId') == S3:
        p['gridData']['y'] += ROW_H
for t, x, w in row:
    k = by[t]
    c = pinned.pop(k)
    assert c['type'] == 'esql_control', t
    panels.append({'type': 'esql_control', 'embeddableConfig': copy.deepcopy(c['config']), 'panelIndex': k,
                   'gridData': {'x': x, 'y': 0, 'w': w, 'h': ROW_H, 'i': k, 'sectionId': S3}})
for i, k in enumerate(sorted(pinned, key=lambda k: pinned[k]['order'])):
    pinned[k]['order'] = i
assert [c['config']['title'] for c in sorted(pinned.values(), key=lambda c: c['order'])] == ['Incident', 'CI']

# ------------------------------------------------------------------ Users impacted -> two "in progress" tiles
old = P('Users impacted')
g = old['gridData']
assert (g['sectionId'], g['w'], g['h']) == (S1, 10, 10)
TILES = [('User base · ServiceNow', 'Users affected, from', 'the ServiceNow user base',
          'Users affected by the active P1 / P2 / P3 incidents, from the ServiceNow user base. The integration is in '
          'progress; no number is shown until it is ready.'),
         ('Real users · RUM', 'Real users affected, from', 'real-user monitoring (RUM)',
          'Real users affected by the active P1 / P2 / P3 incidents, from real-user monitoring (RUM). The integration is '
          'in progress; no number is shown until it is ready.')]
new = []
for n, (t, line1, line2, desc) in enumerate(TILES):
    p = copy.deepcopy(old)
    spec = json.loads(p['embeddableConfig']['savedVis']['params']['spec'])
    tile = spec['data'][0]['values'][0]
    tile.update(value='In progress', detail=f'{line1}|{line2}', more='', names_txt='')
    for m in spec['marks'][0]['marks']:
        if m['encode']['update']['text'].get('signal') == 'parent.value':
            m['encode']['update']['fontSize'] = {'value': 22}
    p['embeddableConfig']['savedVis']['params']['spec'] = json.dumps(spec, indent=2, ensure_ascii=False)
    p['embeddableConfig']['savedVis']['title'] = p['embeddableConfig']['title'] = t
    p['embeddableConfig']['description'] = desc
    if n:
        p['panelIndex'] = uid('panel:users-rum')
    p['gridData'] = dict(g, y=g['y'] + 5 * n, h=5, i=p['panelIndex'])
    new.append(p)
panels[panels.index(old)] = new[0]
panels.insert(panels.index(new[0]) + 1, new[1])

# ------------------------------------------------------------------ checks
s3 = sorted((p['gridData']['y'], p['gridData']['x'], title(p) or p['embeddableConfig'].get('title'))
            for p in panels if p['gridData'].get('sectionId') == S3)
assert [t for *_, t in s3][:4] == ['Server', 'Health window', 'Service', 'Application'], s3[:5]
assert 'Users impacted' not in [title(p) for p in panels]
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print('pinned:', [c['config']['title'] for c in sorted(pinned.values(), key=lambda c: c['order'])],
      '| section 3 starts:', [t for *_, t in s3][:6])
