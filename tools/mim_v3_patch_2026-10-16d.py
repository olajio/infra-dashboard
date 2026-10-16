"""MIM V3: include P3 incidents (16 Oct 2026, fourth round).

Usage: mim_v3_patch_2026-10-16d.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-16b.py)

- Incident and CI controls, Active Incidents, Escalate and the Active donut cover priority 1, 2 and 3
- P3 has its own colour (blue) in the donut and the priority badges
- SLA column: a P3 with no ServiceNow SLA record shows "No SLA record" (there is no agreed P3 target to compare its
  age with; P1 4 h / P2 8 h stay as they were)
- P1 / P2 Time to Resolve vs Target stays P1 / P2 until a P3 target is agreed
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
P1, P2, P3 = '#d6453d', '#c98a0b', '#3f6fb5'

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = lambda t: next(p for p in panels if title(p) == t)
st = lambda p: p['embeddableConfig']['attributes']['state']
layer = lambda p: next(iter(st(p)['datasourceStates']['textBased']['layers'].values()))


def cut(s, old, new):
    assert s.count(old) == 1, (old, s.count(old))
    return s.replace(old, new)


def edit_query(p, *pairs):
    q = layer(p)['query']['esql']
    for old, new in pairs:
        q = cut(q, old, new)
    layer(p)['query']['esql'] = q
    st(p)['query'] = {'esql': q}


def rename(old, new):
    p = P(old)
    p['embeddableConfig']['title'] = new
    if 'attributes' in p['embeddableConfig']:
        p['embeddableConfig']['attributes']['title'] = new
    else:
        p['embeddableConfig']['savedVis']['title'] = new
    return p


def priority_badges(col):
    """Badge colours by priority: 1 red, 2 amber, 3 blue."""
    prm = col['palette']['params']
    prm.update(steps=3, rangeMax=4,
               stops=[{'color': P1, 'stop': 2}, {'color': P2, 'stop': 3}, {'color': P3, 'stop': 4}],
               colorStops=[{'color': P1, 'stop': 1}, {'color': P2, 'stop': 2}, {'color': P3, 'stop': 3}])


# ------------------------------------------------------------------ controls
for c in A['pinned_panels']['panels'].values():
    if c['config']['title'] in ('Incident', 'CI'):
        c['config']['esql_query'] = cut(c['config']['esql_query'], 'WHERE priority IN (1, 2) AND',
                                        'WHERE priority IN (1, 2, 3) AND')

# ------------------------------------------------------------------ Active Incidents
p = rename('Active Incidents (P1 / P2)', 'Active Incidents (P1 / P2 / P3)')
edit_query(p,
           ('TO_INTEGER(priority) IN (1, 2) AND', 'TO_INTEGER(priority) IN (1, 2, 3) AND'),
           ('target = CASE(priority == 1, 240, 480)', 'target = CASE(priority == 1, 240, priority == 2, 480)'),
           ('worst == 5, "Met",\n', 'worst == 5, "Met",\n      target IS NULL, "No SLA record",\n'))
priority_badges(next(c for c in st(p)['visualization']['columns'] if c['columnId'] == 'priority'))
ec = p['embeddableConfig']
ec['description'] = cut(ec['description'], 'Every active P1 / P2 incident', 'Every active P1, P2 and P3 incident')
ec['description'] = cut(ec['description'], '"(age)" = no SLA record, so age is compared with P1 4 h / P2 8 h',
                        '"(age)" = no SLA record, so age is compared with P1 4 h / P2 8 h; a P3 with no SLA record shows '
                        '"No SLA record" (no P3 target agreed yet)')
ec['description'] = cut(ec['description'], 'Active = priority 1 or 2 and', 'Active = priority 1, 2 or 3 and')

# ------------------------------------------------------------------ Escalate
p = P('Escalate')
edit_query(p, ('TO_INTEGER(priority) IN (1, 2) AND', 'TO_INTEGER(priority) IN (1, 2, 3) AND'))
priority_badges(next(c for c in st(p)['visualization']['columns'] if c['columnId'] == 'esc_priority'))
ec = p['embeddableConfig']
ec['description'] = cut(ec['description'], 'one row per active P1 / P2 incident', 'one row per active P1, P2 or P3 incident')

# ------------------------------------------------------------------ Active donut
p = rename('Active P1 / P2', 'Active P1 / P2 / P3')
spec = json.loads(p['embeddableConfig']['savedVis']['params']['spec'])
q = spec['data'][0]['url']['query']
q = cut(q, 'priority IN (1, 2) AND', 'priority IN (1, 2, 3) AND')
q = cut(q, 'EVAL label = CASE(pri == 1, "P1", "P2")', 'EVAL label = CASE(pri == 1, "P1", pri == 2, "P2", "P3")')
spec['data'][0]['url']['query'] = q
spec['scales'][0].update(domain=['P1', 'P2', 'P3'], range=[P1, P2, P3])
legend = next(m for m in spec['marks'] if m['type'] == 'text' and m.get('from', {}).get('data') == 'raw')
legend['encode']['update']['y'] = {'signal': "height / 2 + (datum.label == 'P1' ? -34 : datum.label == 'P2' ? 0 : 34)"}
p['embeddableConfig']['savedVis']['params']['spec'] = json.dumps(spec, ensure_ascii=False, indent=2)
ec = p['embeddableConfig']
ec['description'] = cut(ec['description'], 'How many P1 (red) and P2 (amber) incidents are active now (priority 1 or 2,',
                        'How many P1 (red), P2 (amber) and P3 (blue) incidents are active now (priority 1, 2 or 3,')

# ------------------------------------------------------------------ Users impacted (placeholder text only)
ec = P('Users impacted')['embeddableConfig']
ec['description'] = cut(ec['description'], 'the active P1 / P2 incidents', 'the active P1 / P2 / P3 incidents')

# ------------------------------------------------------------------ Time to Resolve: stays P1 / P2, say why
ec = P('P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)')['embeddableConfig']
ec['description'] += ' P3 incidents are not plotted until a P3 target is agreed.'
ec['description'] = ec['description'].replace('"Active Incidents (P1 / P2)"', '"Active Incidents (P1 / P2 / P3)"')

# ------------------------------------------------------------------ checks
still_p1_p2 = [title(p) for p in panels if 'IN (1, 2)' in json.dumps(p)]
assert still_p1_p2 == ['P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)'], still_p1_p2
assert 'IN (1, 2)' not in json.dumps(A['pinned_panels'])
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{len(panels)} panels')
