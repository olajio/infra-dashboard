"""MIM V3: donut counts the same incidents as the table on Kibana 9.5; Time to Resolve axes start at 0 h
(16 Oct, seventh round).

Usage: mim_v3_patch_2026-10-16g.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-16f.py)

- Active P1 / P2 / P3 donut: Kibana 9.5 applies the dashboard's time range to Vega ES|QL queries by itself (it looks
  up @timestamp; 9.4 did not). With the dashboard on "Last 24 hours" the donut only counted incidents whose record
  was updated in the last 24 h, so long-running On Hold P2s showed as 0 while the Active Incidents table (fixed
  "Last 1 month") listed them. Reproduced on Kibana 9.5.3. Fix: the donut gets the same fixed panel time range as the
  table, "Last 1 month", so both count the same incidents whatever the dashboard's time picker says.
- Time to Resolve: the logarithmic axis cut off values under 1 h. Now a normal axis from 0 h. P1 and P2 on the left
  axis with their 4 h / 8 h targets; P3 on its own right axis (also from 0 h) with its 24 h target, so P3 values of a
  day or more do not flatten P1 and P2. Axis titles say which priorities each axis is for.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
P1, P2, P3 = '#d6453d', '#c98a0b', '#3f6fb5'
TTR = 'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)'
CLOSED = '("Resolved", "Closed", "Canceled", "Cancelled")'

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = lambda t: next(p for p in panels if title(p) == t)

# ------------------------------------------------------------------ donut: same fixed range as Active Incidents
ec = P('Active P1 / P2 / P3')['embeddableConfig']
ec['time_range'] = dict(P('Active Incidents (P1 / P2 / P3)')['embeddableConfig']['time_range'])
assert ec['time_range'] == {'from': 'now-1M', 'to': 'now'}, ec['time_range']
ec['description'] = ec['description'].replace(
    'Last 1 month; not narrowed by the Incident or CI controls.',
    'Last 1 month (fixed, the same as Active Incidents, so both count the same incidents whatever the time picker '
    'says); not narrowed by the Incident or CI controls.')
assert 'Last 1 month (fixed' in ec['description']

# ------------------------------------------------------------------ Time to Resolve: from 0 h, P3 on its own axis
p = P(TTR)
st = p['embeddableConfig']['attributes']['state']
vis = st['visualization']
layers = st['datasourceStates']['textBased']['layers']
data = next(l for l in vis['layers'] if l['layerType'] == 'data')
ref = next(l for l in vis['layers'] if l['layerType'] == 'referenceLine')

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
| EVAL h1 = CASE(pri_n == 1, hours), h2 = CASE(pri_n == 2, hours), h3 = CASE(pri_n == 3, hours)
| STATS p1_hours = ROUND(AVG(h1), 1), p2_hours = ROUND(AVG(h2), 1), p3_hours = ROUND(AVG(h3), 1),
        incidents = COUNT(*), open_now = SUM(still_open)
  BY day = DATE_TRUNC(1 day, opened)
| SORT day ASC
| KEEP day, p1_hours, p2_hours, p3_hours, incidents, open_now"""
layer = layers[data['layerId']]
layer['query']['esql'] = Q
st['query'] = {'esql': Q}
hours_col = lambda cid, label: {'columnId': cid, 'fieldName': cid, 'label': label, 'customLabel': True,
                                'meta': {'type': 'number', 'esType': 'double'}, 'inMetricDimension': True,
                                'params': {'format': {'id': 'number', 'params': {'decimals': 1, 'suffix': ' h'}}}}
keep = {c['columnId']: c for c in layer['columns']}
cols = [keep['day'], hours_col('p1_hours', 'P1'), hours_col('p2_hours', 'P2'), hours_col('p3_hours', 'P3 (right axis)'),
        keep['incidents'], keep['open_now']]
layer['columns'] = cols
layer['allColumns'] = json.loads(json.dumps(cols))

data['accessors'] = ['p1_hours', 'p2_hours', 'p3_hours']
data.pop('splitAccessors', None)
data.pop('colorMapping', None)
data['yConfig'] = [{'forAccessor': 'p1_hours', 'color': P1, 'axisMode': 'left'},
                   {'forAccessor': 'p2_hours', 'color': P2, 'axisMode': 'left'},
                   {'forAccessor': 'p3_hours', 'color': P3, 'axisMode': 'right'}]
next(y for y in ref['yConfig'] if y['forAccessor'] == 'p3_target')['axisMode'] = 'right'

vis.pop('yLeftScale', None)
vis.update(yLeftScale='linear', yRightScale='linear',
           yLeftExtent={'mode': 'full'}, yRightExtent={'mode': 'full'},       # both axes start at 0 h
           yTitle='P1 / P2 — hours', yRightTitle='P3 — hours',
           axisTitlesVisibilitySettings={'x': False, 'yLeft': True, 'yRight': True},
           pointVisibility='always')

p['embeddableConfig']['description'] = (
    'Average time to resolve the P1, P2 and P3 incidents opened each day, last 30 days, against the targets: '
    'P1 4 h (red dashed line) and P2 8 h (amber) on the left axis; P3 24 h (blue) on the right axis, which has its own '
    'scale so P3 values of a day or more do not flatten P1 and P2. Both axes start at 0 h. Each incident counts once: '
    'a resolved incident by its resolution time; one still open by its age so far, so a live incident appears on the '
    'day it was opened and its point climbs until it is resolved (a still-open point is a minimum). A point above its '
    'line = that day\'s incidents took, or are taking, longer than target on average. Canceled incidents are left out. '
    'Last 1 month (fixed); not narrowed by the Incident or CI controls.')

# ------------------------------------------------------------------ checks
assert 'GREATEST(hours, 0.1)' not in json.dumps(p)
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{len(panels)} panels')
