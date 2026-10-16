"""MIM V3: Active P1 / P2 / P3 donut shows every priority that has active incidents (16 Oct, sixth round).

Usage: mim_v3_patch_2026-10-16f.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-16e.py)

Seen live: active P2 and P3 in the Active Incidents table, but only P3 in the donut. With many P3s, a P2 slice is
thinner than the gap between slices (padAngle) and is not drawn at all (reproduced: 1 P2 next to 300 P3s gives a
solid blue ring).
- Each priority with at least one active incident gets a slice of at least 6 % of the ring; the legend and the
  tooltip keep the real counts.
- The legend always lists P1, P2 and P3, with 0 shown faded, so a priority never silently disappears.
- The query uses the same active-incident rule as the Active Incidents table (number starting "INC",
  TO_INTEGER(priority), TO_STRING(state_name)), so the two panels count the same incidents.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
MIN_SHARE = 0.06

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
p = next(p for p in panels if title(p) == 'Active P1 / P2 / P3')
spec = json.loads(p['embeddableConfig']['savedVis']['params']['spec'])

Q = """FROM servicenow-incidents-*
| WHERE @timestamp >= NOW() - 1 month
| EVAL inc = TO_STRING(number), pri_n = TO_INTEGER(priority), state = TO_STRING(state_name)
| WHERE inc LIKE "INC*" AND pri_n IN (1, 2, 3) AND state NOT IN ("Resolved", "Closed", "Canceled", "Cancelled")
| STATS pri = MIN(pri_n) BY inc
| EVAL label = CASE(pri == 1, "P1", pri == 2, "P2", "P3")
| STATS incidents = COUNT(*) BY label
| SORT label ASC"""

spec['data'] = [
    {'name': 'raw', 'url': {'%type%': 'esql', 'query': Q}},
    # always P1, P2, P3 (0 when none), so the legend never drops a priority
    {'name': 'prios', 'values': [{'label': 'P1'}, {'label': 'P2'}, {'label': 'P3'}],
     'transform': [{'type': 'lookup', 'from': 'raw', 'key': 'label', 'fields': ['label'], 'values': ['incidents'],
                    'as': ['incidents'], 'default': 0}]},
    # slices: every non-zero priority at least MIN_SHARE of the ring, so a small one stays visible
    {'name': 'slices', 'source': 'prios',
     'transform': [{'type': 'filter', 'expr': 'datum.incidents > 0'},
                   {'type': 'joinaggregate', 'fields': ['incidents'], 'ops': ['sum'], 'as': ['all']},
                   {'type': 'formula', 'as': 'weight', 'expr': f'max(datum.incidents, datum.all * {MIN_SHARE})'},
                   {'type': 'pie', 'field': 'weight', 'sort': False}]},
    {'name': 'total', 'source': 'prios',
     'transform': [{'type': 'aggregate', 'fields': ['incidents'], 'ops': ['sum'], 'as': ['n']}]},
]
legend = next(m for m in spec['marks'] if m['type'] == 'text' and m.get('from', {}).get('data') == 'raw')
legend['from'] = {'data': 'prios'}
legend['encode']['update']['opacity'] = {'signal': 'datum.incidents > 0 ? 1 : 0.4'}
p['embeddableConfig']['savedVis']['params']['spec'] = json.dumps(spec, ensure_ascii=False, indent=2)
ec = p['embeddableConfig']
ec['description'] += (' Every priority with an active incident gets a visible slice (at least 6 % of the ring, so a '
                      'single P2 next to hundreds of P3s still shows); the numbers beside the ring are the real counts.')

# ------------------------------------------------------------------ checks
assert all(d['name'] != 'raw' or '%type%' in d['url'] for d in spec['data'])
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{len(panels)} panels')
