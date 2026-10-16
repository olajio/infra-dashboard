"""MIM V3: P3 target 24 h; Time to Resolve covers P3 and shows incidents that are still open (16 Oct, fifth round).

Usage: mim_v3_patch_2026-10-16e.py "MIM V3.ndjson" "MIM V3.ndjson" [linear|log]   (run once, after ..._16d.py)

- Time to Resolve vs Target: P1, P2 and P3, with dashed targets P1 4 h, P2 8 h, P3 24 h.
  Fixes the live P1 not showing: only resolved incidents were plotted, so an open P1 had no point until it was
  resolved. Now each incident counts once — resolved: its resolution time; still open: its age so far (a lower
  bound that grows until it is resolved) — so a live P1 appears on the day it was opened and climbs towards and past
  its target. Canceled incidents are left out. Points are always drawn (a priority with incidents on one day only was a
  single point, which Kibana's "auto" setting can hide). Incidents re-synced several times are counted once (they
  used to weigh once per copy in the average).
- Hours floored at 0.1 h, so an incident opened moments ago (0 h) can still be drawn on the log axis.
- Rows sorted by priority first, so the legend reads P1, P2, P3.
- Active Incidents: a P3 with no SLA record is compared with 24 h, like P1 4 h / P2 8 h, and marked "(age)".
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
SCALE = sys.argv[3] if len(sys.argv) > 3 else 'log'
P1, P2, P3 = '#d6453d', '#c98a0b', '#3f6fb5'
OLD_TITLE = 'P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)'
NEW_TITLE = 'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)'
CLOSED = '("Resolved", "Closed", "Canceled", "Cancelled")'

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = lambda t: next(p for p in panels if title(p) == t)
st = lambda p: p['embeddableConfig']['attributes']['state']


def cut(s, old, new):
    assert s.count(old) == 1, (old, s.count(old))
    return s.replace(old, new)


# ------------------------------------------------------------------ Time to Resolve
p = P(OLD_TITLE)
ec = p['embeddableConfig']
ec['title'] = ec['attributes']['title'] = NEW_TITLE
layers = st(p)['datasourceStates']['textBased']['layers']
vis = st(p)['visualization']
data_id = next(l['layerId'] for l in vis['layers'] if l['layerType'] == 'data')
ref_id = next(l['layerId'] for l in vis['layers'] if l['layerType'] == 'referenceLine')

Q = f"""FROM servicenow-incidents-*
| WHERE priority IN (1, 2, 3) AND opened_at >= NOW() - 30 days AND number IS NOT NULL
| STATS opened = MIN(opened_at), pri_n = MIN(TO_INTEGER(priority)), res_s = MAX(resolution_time),
        resolved = MAX(resolved_at), canceled = MAX(CASE(state_name IN ("Canceled", "Cancelled"), 1, 0)),
        closed = MAX(CASE(state_name IN {CLOSED}, 1, 0))
  BY number
| WHERE canceled == 0
| EVAL still_open = CASE(res_s IS NULL AND resolved IS NULL AND closed == 0, 1, 0)
| EVAL hours = CASE(res_s IS NOT NULL, res_s / 3600.0,
                    resolved IS NOT NULL, DATE_DIFF("minutes", opened, resolved) / 60.0,
                    still_open == 1, DATE_DIFF("minutes", opened, NOW()) / 60.0)
| WHERE hours IS NOT NULL
| EVAL hours = GREATEST(hours, 0.1)
| EVAL pri = CASE(pri_n == 1, "P1", pri_n == 2, "P2", "P3")
| STATS avg_hours = ROUND(AVG(hours), 1), incidents = COUNT(*), open_now = SUM(still_open)
  BY day = DATE_TRUNC(1 day, opened), pri
| SORT pri ASC, day ASC
| KEEP day, pri, avg_hours, incidents, open_now"""
layers[data_id]['query']['esql'] = Q
st(p)['query'] = {'esql': Q}
num_col = lambda cid, label, fmt: {'columnId': cid, 'fieldName': cid, 'label': label, 'customLabel': True,
                                   'meta': {'type': 'number', 'esType': 'long'}, 'inMetricDimension': True,
                                   'params': {'format': {'id': 'number', 'params': fmt}}}
for k in ('columns', 'allColumns'):
    cols = [c for c in layers[data_id][k] if c['columnId'] != 'open_now']
    cols.append(num_col('open_now', 'Still open', {'decimals': 0}))
    layers[data_id][k] = cols

layers[ref_id]['query']['esql'] = 'ROW p1_target = 4.0, p2_target = 8.0, p3_target = 24.0'
layers[ref_id]['columns'].append({'columnId': 'p3_target', 'fieldName': 'p3_target', 'label': 'P3 24h', 'customLabel': True,
                                  'meta': {'type': 'number', 'esType': 'double'}, 'inMetricDimension': True})
ref = next(l for l in vis['layers'] if l['layerId'] == ref_id)
ref['accessors'] = ['p1_target', 'p2_target', 'p3_target']
ref['yConfig'].append({'forAccessor': 'p3_target', 'axisMode': 'left', 'color': P3, 'lineStyle': 'dashed',
                       'lineWidth': 2, 'textVisibility': False, 'fill': 'none'})
data = next(l for l in vis['layers'] if l['layerId'] == data_id)
data['colorMapping']['assignments'].append({
    'rules': [{'type': 'match', 'pattern': 'P3', 'matchEntireWord': True, 'matchCase': True}],
    'color': {'type': 'colorCode', 'colorCode': P3}, 'touched': True})
vis['pointVisibility'] = 'always'
vis['yLeftScale'] = SCALE
ec['description'] = (
    'Average time to resolve the P1, P2 and P3 incidents opened each day, last 30 days, against the targets: '
    'P1 4 h (red dashed line), P2 8 h (amber), P3 24 h (blue). Each incident counts once: a resolved incident by its '
    'resolution time; one still open by its age so far, so a live incident appears on the day it was opened and its '
    'point climbs until it is resolved (a still-open point is a minimum). A point above its line = that day\'s '
    'incidents took, or are taking, longer than target on average. Canceled incidents are left out.'
    + (' The time axis is logarithmic, so 4 h, 8 h and 24 h stay readable next to incidents that took days.'
       if SCALE == 'log' else '')
    + ' Last 1 month (fixed); not narrowed by the Incident or CI controls.')

# ------------------------------------------------------------------ Active Incidents: P3 compared with 24 h
p = P('Active Incidents (P1 / P2 / P3)')
L = next(iter(st(p)['datasourceStates']['textBased']['layers'].values()))
q = L['query']['esql']
q = cut(q, 'target = CASE(priority == 1, 240, priority == 2, 480)', 'target = CASE(priority == 1, 240, priority == 2, 480, 1440)')
q = cut(q, '      target IS NULL, "No SLA record",\n', '')
L['query']['esql'] = q
st(p)['query'] = {'esql': q}
ec = p['embeddableConfig']
ec['description'] = cut(ec['description'], 'so age is compared with P1 4 h / P2 8 h; a P3 with no SLA record shows '
                                           '"No SLA record" (no P3 target agreed yet)',
                        'so age is compared with P1 4 h / P2 8 h / P3 24 h')

# ------------------------------------------------------------------ checks
s = json.dumps(panels)
assert 'No SLA record' not in s and OLD_TITLE not in s
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{len(panels)} panels, y axis {SCALE}')
