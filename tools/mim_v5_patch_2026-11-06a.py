"""MIM V5 patch 06a (6 Nov 2026), on top of patch 04a.

Usage: mim_v5_patch_2026-11-06a.py "MIM V5.ndjson" "MIM V5.ndjson"

1. The "Open alerts, no incident" tile follows the Incident / CI controls, like the "Open Alerts with No Incident"
   table: the CI's alerts and its CMDB-linked CIs' alerts; every CI's when nothing is picked. The tile was a Vega
   panel, and Vega cannot read control values, so it becomes a Lens ES|QL metric on the table's own query
   (count of open alerts, with the Critical count under it). Same place, same size.
2. "Escalate" is renamed "Escalation Channel".
3. Section 2 layout: Escalation Channel and Open Alerts with No Incident side by side (the table moves from
   section 1 to the top of section 2, next to Escalation Channel: both follow the picked CI); Changes in the Last
   7 Days on this CI and Alerts on this CI side by side under them. The panels below move up.
4. P1 / P2 / P3 Time to Resolve vs Target: the P3 line and its 24 h target were on the right-hand axis, with its
   own scale, so the dashed 24 h line looked like about 1 h against the left axis. Everything is now on one axis
   (hours), so each target line sits at its real value.
"""
import copy
import json
import sys

SRC, OUT = sys.argv[1:3]
lines = [l for l in open(SRC) if l.strip()]
dash = json.loads(lines[0])
assert dash.get('type') == 'dashboard'
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = {title(p): p for p in panels}
S1 = P['Active P1']['gridData']['sectionId']
S2 = P['Escalate']['gridData']['sectionId']
OA = 'Open Alerts with No Incident'
TTR = 'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)'

# ---- 1. the tile: Lens metric on the table's query ----
table = P[OA]
tq = table['embeddableConfig']['attributes']['state']['query']['esql']
cut = tq.index('| EVAL alert_node')
q = tq[:cut] + ('| STATS metric_val = COUNT(*), critical = SUM(CASE(alert_severity == "Critical", 1, 0)), '
                'major = SUM(CASE(alert_severity == "Major", 1, 0))')
old = P['Open alerts, no incident']
tile = copy.deepcopy(table)
tile['panelIndex'] = old['panelIndex']
tile['gridData'] = dict(old['gridData'])
ec = tile['embeddableConfig']
ec.pop('drilldowns', None)
name = 'Open alerts, no incident'
ec['title'] = name
ec['hide_title'] = True
ec['description'] = ('Open Netcool alerts, last 24 h, on production CIs with no open incident: the rows of the Open '
                     'Alerts with No Incident table. With an incident or CI picked: only that CI\'s alerts and its '
                     'CMDB-linked CIs\'; with nothing picked, every CI\'s. Green at 0; red above 0. Under the number: '
                     'how many are Critical.')
at = ec['attributes']
at['title'] = name
at['visualizationType'] = 'lnsMetric'
st = at['state']
st['query'] = {'esql': q}
(layer_id, layer), = st['datasourceStates']['textBased']['layers'].items()
layer['query'] = {'esql': q}
num = lambda cid, label: {'columnId': cid, 'fieldName': cid, 'label': label, 'customLabel': True,
                          'meta': {'type': 'number', 'esType': 'long'}, 'inMetricDimension': True}
layer['columns'] = [num('metric_val', name), num('critical', 'Critical'), num('major', 'Major')]
layer.pop('allColumns', None)
st['visualization'] = {
    'layerId': layer_id, 'layerType': 'data', 'metricAccessor': 'metric_val',
    'secondaryMetricAccessor': 'critical', 'secondaryPrefix': 'Critical',
    'subtitle': 'Netcool, no open incident · picked CI and its links (all if none)',
    'icon': 'bell', 'iconAlign': 'left', 'titleWeight': 'bold', 'valueFontMode': 'default', 'applyColorTo': 'value',
    'palette': {'name': 'custom', 'type': 'palette', 'params': {
        'name': 'custom', 'reverse': False, 'steps': 2, 'maxSteps': 5, 'rangeType': 'number', 'rangeMin': 0,
        'rangeMax': 2, 'progression': 'fixed', 'continuity': 'all',
        'stops': [{'color': '#1f9e6b', 'stop': 1}, {'color': '#d6453d', 'stop': 2}],
        'colorStops': [{'color': '#1f9e6b', 'stop': 0}, {'color': '#d6453d', 'stop': 1}]}}}
panels[panels.index(old)] = tile

# ---- 2. Escalate -> Escalation Channel ----
esc = P['Escalate']
esc['embeddableConfig']['title'] = 'Escalation Channel'
esc['embeddableConfig']['attributes']['title'] = 'Escalation Channel'
for p in panels:
    e = p['embeddableConfig']
    if e.get('description'):
        e['description'] = e['description'].replace('Escalate', 'Escalation Channel')

# ---- 3. section 2 layout ----
LAYOUT = {   # title: (x, y, w, h), section 2
    'Escalate': (0, 0, 24, 11), OA: (24, 0, 24, 11),
    'Changes in the Last 7 Days on this CI': (0, 11, 24, 11), 'Alerts on this CI': (24, 11, 24, 11),
    'Blast radius': (0, 22, 7, 11), 'Applications related to this CI': (7, 22, 41, 11),
    'Middleware View': (0, 33, 24, 11), 'Database View': (24, 33, 24, 11),
    'Server View': (0, 44, 24, 11), 'Other related CIs': (24, 44, 24, 11),
}
for t, (x, y, w, h) in LAYOUT.items():
    g = P[t]['gridData']
    g.update({'x': x, 'y': y, 'w': w, 'h': h, 'sectionId': S2})
assert not [title(p) for p in panels if p['gridData'].get('sectionId') == S2 and title(p) not in LAYOUT
            and title(p) != 'Escalation Channel']

# ---- 4. Time to Resolve: one axis ----
viz = P[TTR]['embeddableConfig']['attributes']['state']['visualization']
for lay in viz['layers']:
    for yc in lay.get('yConfig', []):
        yc['axisMode'] = 'left'
viz['yTitle'] = 'Hours since opened (average)'
viz.pop('yRightTitle', None)
viz['axisTitlesVisibilitySettings']['yRight'] = False
P[TTR]['embeddableConfig']['attributes'] = json.loads(json.dumps(P[TTR]['embeddableConfig']['attributes'], ensure_ascii=False)
                                                     .replace('"P3 (right axis)"', '"P3"'))
d = P[TTR]['embeddableConfig']
old_txt = ('P1 4 h (red dashed line) and P2 8 h (amber) on the left axis; P3 24 h (blue) on the right axis, which has its '
           'own scale so P3 values of a day or more do not flatten P1 and P2. Both axes start at 0 h.')
assert old_txt in d['description']
d['description'] = d['description'].replace(old_txt, 'P1 4 h (red dashed line), P2 8 h (amber) and P3 24 h (blue), all on '
                                            'one axis in hours (since 6 Nov; P3 had its own right-hand axis), from 0 h.')

ids = [p['panelIndex'] for p in panels]
assert len(ids) == len(set(ids))
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: {len(panels)} panels')
