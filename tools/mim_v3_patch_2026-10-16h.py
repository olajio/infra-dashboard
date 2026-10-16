"""MIM V3: the Related CIs by Type views move into "Investigate the CI" (16 Oct, eighth round).

Usage: mim_v3_patch_2026-10-16h.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-16g.py)

- Middleware View, Database View, Server View and Application View move into section 2, right after Blast radius and
  Applications that depend on this CI; the panels below them move down.
- The empty "3 · Related CIs by Type (CMDB)" section is removed; sections 4 and 5 become 3 and 4.
- Descriptions that named a section by number are updated.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
S2, S3 = 'ca3d34a5-1eed-5555-a34b-4ae94ea7d242', '78b7cc72-3d3a-45a4-bdd2-669192f1b75f'
VIEWS = ('Middleware View', 'Database View', 'Server View', 'Application View')

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = lambda t: next(p for p in panels if title(p) == t)


def cut(s, old, new):
    assert s.count(old) == 1, (old, s.count(old))
    return s.replace(old, new)


# ------------------------------------------------------------------ views into section 2, after the dependents row
dep = P('Applications that depend on this CI')['gridData']
start = dep['y'] + dep['h']                                   # first row below Blast radius / dependents
height = max(P(t)['gridData']['y'] + P(t)['gridData']['h'] for t in VIEWS)   # the views' block, 22 rows
for p in panels:
    g = p['gridData']
    if g['sectionId'] == S2 and g['y'] >= start:
        g['y'] += height
for t in VIEWS:
    g = P(t)['gridData']
    g.update(sectionId=S2, y=start + g['y'])
assert not [p for p in panels if p['gridData']['sectionId'] == S3]

# ------------------------------------------------------------------ sections: drop 3, renumber 4 and 5
A['sections'] = [s for s in A['sections'] if s['gridData']['i'] != S3]
for i, s in enumerate(A['sections']):
    s['gridData']['y'] = i
    s['title'] = f'{i + 1} · ' + s['title'].split(' · ', 1)[1]

# ------------------------------------------------------------------ descriptions that named a section number
for t, old, new in (('Server Health', 'open the Infra Dashboard (section 5)', 'open the Infra Dashboard (section 4)'),
                    ('Applications on this CI', 'and the views in section 3', 'and the Middleware / Database / Server '
                                                                              'views in this section'),
                    ('Application View', '"Application Health" in section 4', '"Application Health" in section 3')):
    ec = P(t)['embeddableConfig']
    ec['description'] = cut(ec['description'], old, new)

# ------------------------------------------------------------------ checks: no overlaps in any section
for sec in {p['gridData']['sectionId'] for p in panels}:
    cells = {}
    for p in panels:
        g = p['gridData']
        if g['sectionId'] != sec:
            continue
        for x in range(g['x'], g['x'] + g['w']):
            for y in range(g['y'], g['y'] + g['h']):
                assert (x, y) not in cells, (title(p), cells[(x, y)])
                cells[(x, y)] = title(p)
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print([s['title'] for s in A['sections']])
