"""MIM V5 patch 17a (17 Nov 2026), on top of 16a: P3 removed entirely; Active Incidents narrower, Time to Resolve wider.

Usage: mim_v5_patch_2026-11-17a.py "MIM V5.ndjson" "MIM V5.ndjson"

Team request: keep only P1s and P2s (P2s past their 8 h target, as before).
- Tiles: "P3 over 24 h" removed; "Needs attention now" counts P1 + P2 over 8 h (its strip: P1, P2); the other tiles
  spread over the row it leaves.
- Active Incidents, Escalation Channel, the Incident and CI control lists: priority 1 or 2 only.
- Time to Resolve vs Target: P1 and P2 only (no P3 line or 24 h target); retitled.
- Layout: Active Incidents about 25 % narrower (w 38 -> 29), Time to Resolve takes the space (w 10 -> 19).
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
dash = json.loads([l for l in open(SRC) if l.strip()][0])
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = {title(p): p for p in panels}
OLD_AI = 'Active Incidents (P1 · P2 over 8 h · P3 over 24 h)'
NEW_AI = 'Active Incidents (P1 · P2 over 8 h)'
OLD_TTR = 'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)'
NEW_TTR = 'P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)'
assert 'P3 over 24 h' in P and OLD_AI in P and OLD_TTR in P, 'already patched?'
P123 = 'IN (1, 2, 3)'


def sub(s, a, b, n=None):
    assert a in s, a[:60]
    if n is not None:
        assert s.count(a) == n, (a[:60], s.count(a))
    return s.replace(a, b)


def lens_query(p, fn):
    """Apply fn to the panel's ES|QL, in the state and in every layer that holds the same query."""
    st = p['embeddableConfig']['attributes']['state']
    old = st['query']['esql']
    new = fn(old)
    st['query']['esql'] = new
    for layer in st['datasourceStates']['textBased']['layers'].values():
        if layer.get('query', {}).get('esql') == old:
            layer['query']['esql'] = new
    return st


# ---- 1. tiles ----
panels.remove(P['P3 over 24 h'])
spec_holder = P['Needs attention now']['embeddableConfig']
spec = json.loads(spec_holder['savedVis']['params']['spec'])
q = spec['data'][0]['url']['query']
q = sub(q, P123, 'IN (1, 2)')
q = sub(q, ', pri == 3 AND age_minutes > 1440, "p3")', ')')
q = sub(q, ', p3 = SUM(CASE(bucket == "p3", 1, 0))', '')
spec['data'][0]['url']['query'] = q
spec['signals'] = [s for s in spec['signals'] if s['name'] != 'p3']
for s in spec['signals']:
    if s['name'] == 'total':
        s['update'] = 'p1 + p2'
    if s['name'] == 'worst':
        s['update'] = "p1 > 0 ? '#d6453d' : p2 > 0 ? '#c98a0b' : '#1f9e6b'"
marks = []
for m in spec['marks']:
    s = json.dumps(m)
    if 'p3' in s:          # the P3 segment and its label
        continue
    if '"P1 \\u00b7 P2 over 8 h \\u00b7 P3 over 24 h"' in s or 'P3 over 24 h' in s:
        m = json.loads(s.replace('P1 \\u00b7 P2 over 8 h \\u00b7 P3 over 24 h', 'P1 \\u00b7 P2 over 8 h'))
    if json.dumps(m).count('barX + 1 * barW / 3'):
        m = json.loads(json.dumps(m).replace('barX + 1 * barW / 3', 'barX + barW / 2'))
    marks.append(m)
assert len(marks) == len(spec['marks']) - 2
spec['marks'] = marks
spec_holder['savedVis']['params']['spec'] = json.dumps(spec, indent=2)
spec_holder['description'] = ('Active incidents past their target, in one number: every P1 and the P2s open longer '
                              'than 8 h. Green at 0. The strip splits it by priority; the same incidents as the Active '
                              'Incidents table.')
for t in ('Active P1', 'P2 over 8 h'):
    sv = P[t]['embeddableConfig']['savedVis']['params']
    sv['spec'] = sub(sv['spec'], P123, 'IN (1, 2)')
for t in ('User base · ServiceNow', 'Real users · RUM'):
    ec = P[t]['embeddableConfig']
    ec['description'] = ec['description'].replace('P1 / P2 / P3', 'P1 / P2')
ROW = {'Needs attention now': (0, 8), 'Active P1': (8, 8), 'P2 over 8 h': (16, 8),
       'Open alerts, no incident': (24, 8), 'User base · ServiceNow': (32, 8), 'Real users · RUM': (40, 8)}
for t, (x, w) in ROW.items():
    P[t]['gridData'].update({'x': x, 'w': w})

# ---- 2. Active Incidents ----
ai = P[OLD_AI]
ec = ai['embeddableConfig']
lens_query(ai, lambda s: sub(s, P123, 'IN (1, 2)'))
ec['title'] = ec['attributes']['title'] = NEW_AI
ec['description'] = ec['description'].replace(
    'Every active P1 incident, and the active P2 and P3 incidents open longer than their target (P2 8 h, P3 24 h, the '
    'lines in Time to Resolve vs Target; age = time since opened)',
    'Every active P1 incident, and the active P2 incidents open longer than their 8 h target (age = time since opened)')
ec['description'] = ec['description'].replace('The three tiles above count these rows.', 'The P1 and P2 tiles above count these rows.')
ec['description'] = ec['description'].replace('Active = priority 1, 2 or 3', 'Active = priority 1 or 2')
ai['gridData'].update({'x': 0, 'w': 29})

# ---- 3. Escalation Channel, controls ----
esc = P['Escalation Channel']
lens_query(esc, lambda s: sub(s, P123, 'IN (1, 2)'))
esc['embeddableConfig']['description'] = esc['embeddableConfig']['description'].replace('active P1, P2 or P3 incident', 'active P1 or P2 incident')
for v in A['pinned_panels']['panels'].values():
    c = v['config']
    if c.get('variable_name') in ('incident', 'ci') and P123 in c.get('esql_query', ''):
        c['esql_query'] = c['esql_query'].replace('priority IN (1, 2, 3)', 'priority IN (1, 2)')
        assert P123 not in c['esql_query'], c['variable_name']

# ---- 4. Time to Resolve: P1 / P2 only, wider ----
ttr = P[OLD_TTR]
ec = ttr['embeddableConfig']
st = lens_query(ttr, lambda s: sub(sub(sub(sub(s, P123, 'IN (1, 2)'),
                                         ', h3 = CASE(pri_n == 3, hours)', ''),
                                     ', p3_hours = ROUND(MEDIAN(h3), 1)', ''),
                                 'KEEP day, p1_hours, p2_hours, p3_hours,', 'KEEP day, p1_hours, p2_hours,'))
for layer in st['datasourceStates']['textBased']['layers'].values():
    if 'p3_target' in layer['query']['esql']:
        layer['query']['esql'] = 'ROW p1_target = 4.0, p2_target = 8.0'
    layer['columns'] = [c for c in layer['columns'] if c['columnId'] not in ('p3_hours', 'p3_target')]
    layer.pop('allColumns', None)
for lay in st['visualization']['layers']:
    lay['accessors'] = [a for a in lay['accessors'] if a not in ('p3_hours', 'p3_target')]
    lay['yConfig'] = [y for y in lay.get('yConfig', []) if y['forAccessor'] not in ('p3_hours', 'p3_target')]
ec['title'] = ec['attributes']['title'] = NEW_TTR
d = ec['description']
d = d.replace('for the P1, P2 and P3 incidents resolved each day', 'for the P1 and P2 incidents resolved each day')
d = d.replace('P1 4 h (red dashed line), P2 8 h (amber) and P3 24 h (blue)', 'P1 4 h (red dashed line) and P2 8 h (amber)')
d = d.replace('The median is not pulled up by the odd very long incident (TTR2 on 13 Nov: some P3 over 900 h). ',
              'The median is not pulled up by the odd very long incident. ')
ec['description'] = d + ' P3 removed on 17 Nov.'
ttr['gridData'].update({'x': 29, 'w': 19})

s = json.dumps(panels) + json.dumps(A['pinned_panels'])
for bad in ('p3_hours', 'p3_target', 'P3 over 24 h', P123):
    assert bad not in s, bad
ids = [p['panelIndex'] for p in panels]
assert len(ids) == len(set(ids))
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: P3 removed; {len(panels)} panels')
