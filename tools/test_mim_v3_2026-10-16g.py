"""Check the seventh 16 Oct round: the Active P1 / P2 / P3 donut has the same fixed time range as the Active
Incidents table (Kibana 9.5 applies a panel's time range to Vega ES|QL queries; without a fixed range the donut
followed the dashboard's time picker and missed incidents the table showed).

Usage: test_mim_v3_2026-10-16g.py MIM_V3_NDJSON
"""
import json
import sys

dash = json.loads(open(sys.argv[1]).readline())
panels = json.loads(dash['attributes']['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = {title(p): p for p in panels}
fails = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" + ('' if ok else f'\n          expected {want!r}'))
    if not ok:
        fails.append(name)


donut = P['Active P1 / P2 / P3']['embeddableConfig']
table = P['Active Incidents (P1 / P2 / P3)']['embeddableConfig']
check('donut and table have the same fixed time range', (donut.get('time_range'), table.get('time_range')),
      ({'from': 'now-1M', 'to': 'now'}, {'from': 'now-1M', 'to': 'now'}))
spec = json.loads(donut['savedVis']['params']['spec'])
check('donut query has no %timefield% override (Kibana 9.5 finds @timestamp itself)',
      '%timefield%' in json.dumps(spec), False)
check('no other Vega panel queries data without a fixed range',
      [title(p) for p in panels if p['type'] == 'legacy_vis' and '"%type%": "esql"' in
       p['embeddableConfig']['savedVis']['params']['spec'] and not p['embeddableConfig'].get('time_range')], [])
print('\n' + ('ALL CHECKS PASSED' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
