"""MIM V5 patch 20a (20 Nov 2026): the Linked incidents column is removed from Active Incidents, and the P1 MTTR
(90 days) tile is removed.

Usage: mim_v5_patch_2026-11-20a.py "MIM V5.ndjson" "MIM V5.ndjson"

- Active Incidents: `linked_incidents` is no longer computed or kept, and its column and its sentence in the panel
  description are gone. Everything else in the query (rows, sort order, drill-down columns) is unchanged.
- P1 MTTR (90 days): the tile is deleted and the tile row goes back to the widths it had before the tile was added
  (patch 19b): 7 7 7 7 8 6 6, so no gap is left.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
dash = json.loads([l for l in open(SRC) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = {title(p): p for p in panels}


def sub(text, pairs, what):
    for a, b in pairs:
        assert text.count(a) == 1, (what, text.count(a), a)
        text = text.replace(a, b)
    return text


# ---- Active Incidents: no Linked incidents ----
AI = 'Active Incidents (P1 · P2 · P3)'
st = P[AI]['embeddableConfig']['attributes']['state']
old = st['query']['esql']
q = sub(old, [('        linked_incidents = MAX(linked), grp = VALUES(grp_s),', '        grp = VALUES(grp_s),'),
              ('KEEP number, priority, ci.name, state_name, opened, age, linked_incidents, assignment_group,',
               'KEEP number, priority, ci.name, state_name, opened, age, assignment_group,')], AI)
n = 0
for layer in st['datasourceStates']['textBased']['layers'].values():
    if layer['query']['esql'] == old:
        layer['query'] = {'esql': q}
        before = len(layer['columns'])
        layer['columns'] = [c for c in layer['columns'] if c['columnId'] != 'linked_incidents']
        assert len(layer['columns']) == before - 1
        n += 1
assert n == 1
st['query'] = {'esql': q}
vc = st['visualization']['columns']
st['visualization']['columns'] = [c for c in vc if c['columnId'] != 'linked_incidents']
assert len(st['visualization']['columns']) == len(vc) - 1
ec = P[AI]['embeddableConfig']
ec['description'] = sub(ec['description'], [(' Linked incidents = incidents whose parent incident is this one, updated in '
                                             'the last 7 days (the user impact of a P1).', '')], AI)

# ---- P1 MTTR (90 days) tile removed; row widths as before patch 19b ----
tile = P.pop('P1 MTTR (90 days)')
panels.remove(tile)
y, sec = P['Active P1']['gridData']['y'], P['Active P1']['gridData']['sectionId']
row = [('Needs attention now', 0, 7), ('Active P1', 7, 7), ('Active P2', 14, 7), ('Active P3', 21, 7),
       ('Open alerts, no incident', 28, 8), ('User base · ServiceNow', 36, 6), ('Real users · RUM', 42, 6)]
assert sorted(title(p) for p in panels if p['gridData'].get('sectionId') == sec and p['gridData']['y'] == y) == sorted(t for t, _, _ in row)
for t, x, w in row:
    P[t]['gridData'].update(x=x, w=w)

dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: Linked incidents column and P1 MTTR tile removed')
