"""MIM V3 changes, 16 Oct 2026 (second round).

Usage: mim_v3_patch_2026-10-16b.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-16.py)

- Middleware / Database / Server / Application View: CMDB status column removed (and the hidden "non-operational
  first" sort that went with it); the Relationship column takes the freed width
- Active P1 / P2 and Users impacted: transparent background instead of black. Text takes Kibana's theme colours
  (the Vega "guide-title" / "guide-label" styles), so it reads in light and dark mode. The donut uses the same P1 / P2
  colours as the priority badges in Active Incidents (the old yellow did not read on a white page).
- Descriptions that still named removed panels (Active P1 / P2 at a Glance, What this CI runs on) or the old section
  number of the Infra Dashboard card corrected
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
P1, P2 = '#d6453d', '#c98a0b'   # priority badges in Active Incidents
VIEWS = ('Middleware View', 'Database View', 'Server View', 'Application View')

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = lambda t: next(p for p in panels if title(p) == t)
st = lambda p: p['embeddableConfig']['attributes']['state']
layer = lambda p: next(iter(st(p)['datasourceStates']['textBased']['layers'].values()))


def cut(s, old, new=''):
    assert s.count(old) == 1, (old, s.count(old))
    return s.replace(old, new)


# ------------------------------------------------------------------ CMDB status out of the four views
for t in VIEWS:
    p = P(t)
    q = layer(p)['query']['esql']
    q = cut(q, ',\n       o = CASE(down, TO_STRING(child_ci.operational_status.keyword), '
               'TO_STRING(parent_ci.operational_status.keyword))')
    q = cut(q, ', oper = CASE(o == "1", "Operational", o == "2", "Non-operational", o == "3", "Repair in progress", '
               'o == "4", "DR standby", o == "5", "Ready", o == "6", "Retired", o == "7", "Pipeline", o == "8", '
               '"Catalog", "—")')
    q = cut(q, ', opers = VALUES(oper)')
    q = cut(q, ', cmdb_status = MV_FIRST(opers)')
    q = cut(q, ',\n       rank = CASE(cmdb_status IN ("Non-operational", "Repair in progress"), 1, 2)')
    q = cut(q, '| SORT rank ASC, ci_type ASC, related_ci ASC', '| SORT ci_type ASC, related_ci ASC')
    q = cut(q, '| KEEP related_ci, ci_type, relation, cmdb_status, related_env', '| KEEP related_ci, ci_type, relation, related_env')
    assert 'oper' not in q and 'cmdb_status' not in q, t
    layer(p)['query']['esql'] = q
    st(p)['query'] = {'esql': q}
    for k in ('columns', 'allColumns'):
        layer(p)[k] = [c for c in layer(p)[k] if c['columnId'] != 'cmdb_status']
    vis = st(p)['visualization']
    vis['columns'] = [c for c in vis['columns'] if c['columnId'] != 'cmdb_status']
    next(c for c in vis['columns'] if c['columnId'] == 'relation')['width'] = 340
    ec = p['embeddableConfig']
    ec['description'] = cut(ec['description'], ', with the relationship from ServiceNow and the CMDB operational status '
                                               '(non-operational and in-repair first)', ', with the relationship from ServiceNow')

# ------------------------------------------------------------------ transparent first row
def set_spec(p, spec):
    p['embeddableConfig']['savedVis']['params']['spec'] = json.dumps(spec, ensure_ascii=False, indent=2)


def themed(enc, style):
    """Drop the fixed fill so the text takes Kibana's theme colour from the named style."""
    enc.pop('fill', None)
    return style


p = P('Active P1 / P2')
spec = json.loads(p['embeddableConfig']['savedVis']['params']['spec'])
spec.pop('background')
spec['scales'][0]['range'] = [P1, P2]
for m in spec['marks']:
    if m['type'] == 'text' and m['encode']['update'].get('fill', {}).get('scale') is None:
        upd = m['encode']['update']
        m['style'] = themed(upd, 'guide-title' if upd.get('fontWeight') else 'guide-label')
set_spec(p, spec)

p = P('Users impacted')
spec = json.loads(p['embeddableConfig']['savedVis']['params']['spec'])
spec.pop('background')
group = spec['marks'][0]
group['encode']['update'].pop('fill')
spec['data'][0]['values'][0].pop('colour')
for m in group['marks']:
    upd = m['encode']['update']
    m['style'] = themed(upd, 'guide-title' if upd.get('fontSize', {}).get('value') == 46 else 'guide-label')
set_spec(p, spec)

# ------------------------------------------------------------------ descriptions that named removed panels
for t, old, new in (
        ('P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)',
         'those past target are counted in "Active P1 / P2 at a Glance"', 'those past target show in the SLA column of '
                                                                         '"Active Incidents (P1 / P2)"'),
        ('Applications on this CI', 'are in "Applications that depend on this CI" and "What this CI runs on"',
         'are in "Applications that depend on this CI" and the views in section 3'),
        ('Server Health', 'open the Infra Dashboard (section 4)', 'open the Infra Dashboard (section 5)')):
    ec = P(t)['embeddableConfig']
    ec['description'] = cut(ec['description'], old, new)

# ------------------------------------------------------------------ checks
s = json.dumps(panels)
assert '#000000' not in s and 'cmdb_status' not in s and 'CMDB status' not in s
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{len(panels)} panels')
