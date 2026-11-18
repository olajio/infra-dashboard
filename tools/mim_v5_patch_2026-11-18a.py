"""MIM V5 patch 18a (18 Nov 2026), on top of 17e / 17f.

Usage: mim_v5_patch_2026-11-18a.py "MIM V5.ndjson" "<MIM V5 before 17a>.ndjson" "MIM V5.ndjson"
(the second file is the version before P3 was removed, from git history, for the P3 tile and the 3-part strip)

1. P3 back, any age, same rules as P2 (active = not Resolved / Closed / Canceled; On Hold P1s shown, On Hold P2s and
   P3s not): Needs attention now (P1 · P2 · P3 strip), a new Active P3 tile, Active Incidents, Escalation Channel, the
   Incident and CI controls, and a P3 line (Duration, opened to resolved; 24 h target) on Time to Resolve.
2. New multi-select control "Priorities" (P1, P2, P3; all selected by default) in the top bar. Active Incidents,
   Escalation Channel and Time to Resolve follow it (the Vega tiles cannot read controls; each tile is one priority).
3. Age column (time since opened, "2 d 5 h" / "3 h 20 m") in Active Incidents and Escalation Channel.
4. Time to Resolve: the x axis was the panel's 30-day reading range while only 7 days have points, so the lines sat
   squeezed at the right edge (trendline.png). The day is now a label ("Nov 12"), so the 7 days fill the chart.
5. cmdb_with_apm_flag now maps more fields as text that APM maps as keyword (17 Nov: ci.name; 18 Nov: service.name).
   The four queries that read both now convert every APM / CMDB-relation text field they use, once, right after
   FROM, and keep them empty on the cmdb_with_apm_flag rows (as before), so any of these fields appearing in
   cmdb_with_apm_flag no longer breaks them.
6. Dashboard Links: only Related Dashboards (Detailed Dashboards removed); Executive Dashboard (In Progress) as text;
   order Executive, Portfolio, Application Operations, Major Incident Management, Infra Overview (same as the
   Infrastructure Overview, infra_overview_v2_patch_2026-11-18a.py).
"""
import json
import re
import sys
import uuid

SRC, OLD, OUT = sys.argv[1:4]
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
dash = json.loads([l for l in open(SRC) if l.strip()][0])
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
P = {title(p): p for p in panels}
old_panels = {title(p): p for p in json.loads(json.loads([l for l in open(OLD) if l.strip()][0])['attributes']['panelsJSON'])}
assert 'P3 over 24 h' in old_panels, 'second file must be MIM V5 before patch 17a'
assert 'Active P3' not in P, 'already patched'

PRI = 'MV_CONTAINS(?priorities, CONCAT("P", TO_STRING({})))'
OLD_ACTIVE = ('TO_INTEGER(priority) IN (1, 2) AND TO_STRING(state_name) NOT IN ("Resolved", "Closed", "Canceled", '
              '"Cancelled") AND (TO_INTEGER(priority) == 1 OR TO_STRING(state_name) != "On Hold")')
NEW_ACTIVE = OLD_ACTIVE.replace('IN (1, 2)', 'IN (1, 2, 3)')
AGE = ('CASE({m} >= 1440, CONCAT(TO_STRING({m} / 1440), " d ", TO_STRING(({m} % 1440) / 60), " h"), '
       'CONCAT(TO_STRING({m} / 60), " h ", TO_STRING({m} % 60), " m"))')
ON_HOLD = 'On Hold P1s count; On Hold P2s and P3s do not.'


def sub(text, pairs, what):
    for a, b in pairs:
        assert text.count(a) == 1, (what, text.count(a), a)
        text = text.replace(a, b)
    return text


def set_query(p, q):
    st = p['embeddableConfig']['attributes']['state']
    old = st['query']['esql']
    for layer in st['datasourceStates']['textBased']['layers'].values():
        if layer['query']['esql'] == old:
            layer['query'] = {'esql': q}
    st['query'] = {'esql': q}


def data_layer(p):
    st = p['embeddableConfig']['attributes']['state']
    q = st['query']['esql']
    return next(l for l in st['datasourceStates']['textBased']['layers'].values() if l['query']['esql'] == q)


# ---- 1. tiles ----
for t in ('Active P1', 'Active P2'):
    ec = P[t]['embeddableConfig']
    spec = json.loads(ec['savedVis']['params']['spec'])
    spec['data'][0]['url']['query'] = sub(spec['data'][0]['url']['query'], [(OLD_ACTIVE, NEW_ACTIVE)], t)
    ec['savedVis']['params']['spec'] = json.dumps(spec, ensure_ascii=False, indent=2)
    ec['description'] = ec['description'].replace('On Hold P1s count, On Hold P2s do not.', ON_HOLD)

# Active P3: the Active P2 tile in P3's colour
p3 = json.loads(json.dumps(P['Active P2']))
pid = old_panels['P3 over 24 h']['panelIndex']
p3['panelIndex'] = pid
p3['gridData'] = dict(p3['gridData'], i=pid)
ec = p3['embeddableConfig']
s = ec['savedVis']['params']['spec']
s = s.replace('#c98a0b', '#3f6fb5').replace('"value": "P2"', '"value": "P3"').replace('Active P2', 'Active P3')
spec = json.loads(s)
spec['data'][0]['url']['query'] = sub(spec['data'][0]['url']['query'], [('WHERE pri == 2', 'WHERE pri == 3')], 'Active P3')
assert '#c98a0b' not in json.dumps(spec) and '"P2"' not in json.dumps(spec)
ec['savedVis']['params']['spec'] = json.dumps(spec, ensure_ascii=False, indent=2)
ec['savedVis']['title'] = ec['title'] = 'Active P3'
ec['description'] = ec['description'].replace('P2 incidents', 'P3 incidents')
panels.append(p3)
P['Active P3'] = p3

# Needs attention now: the 3-part strip from before 17a, with today's rules
na = P['Needs attention now']['embeddableConfig']
spec = json.loads(old_panels['Needs attention now']['embeddableConfig']['savedVis']['params']['spec'])
cur = json.loads(na['savedVis']['params']['spec'])
q = sub(cur['data'][0]['url']['query'], [
    (OLD_ACTIVE, NEW_ACTIVE),
    ('EVAL bucket = CASE(pri == 1, "p1", pri == 2, "p2")', 'EVAL bucket = CASE(pri == 1, "p1", pri == 2, "p2", pri == 3, "p3")'),
    ('p2 = SUM(CASE(bucket == "p2", 1, 0))', 'p2 = SUM(CASE(bucket == "p2", 1, 0)), p3 = SUM(CASE(bucket == "p3", 1, 0))')], 'NA')
spec['data'][0]['url']['query'] = q
s = json.dumps(spec, ensure_ascii=False, indent=2)
s = sub(s, [('"P1 · P2 over 8 h · P3 over 24 h"', '"P1 · P2 · P3"'), ("'P2 > 8 h'", "'P2'"), ("'P3 > 24 h'", "'P3'")], 'NA spec')
na['savedVis']['params']['spec'] = s
na['description'] = ('Every active P1, P2 and P3 incident, whatever its age, in one number. Green at 0. The strip splits '
                     'it by priority; the same incidents as the Active Incidents table with every priority picked. ' + ON_HOLD)

# tile row as before 17a: 7 7 7 7 8 6 6
y = P['Active P1']['gridData']['y']
for t, x, w in (('Needs attention now', 0, 7), ('Active P1', 7, 7), ('Active P2', 14, 7), ('Active P3', 21, 7),
                ('Open alerts, no incident', 28, 8), ('User base · ServiceNow', 36, 6), ('Real users · RUM', 42, 6)):
    assert P[t]['gridData']['y'] == y, t
    P[t]['gridData'].update(x=x, w=w)

# ---- Active Incidents: P3, Priorities, Age ----
AI_OLD, AI = 'Active Incidents (P1 · P2)', 'Active Incidents (P1 · P2 · P3)'
p = P[AI_OLD]
q = sub(p['embeddableConfig']['attributes']['state']['query']['esql'], [
    ('EVAL is_active = CASE(src == "inc" AND pri IN (1, 2) AND',
     'EVAL is_active = CASE(src == "inc" AND pri IN (1, 2, 3) AND ' + PRI.format('pri') + ' AND'),
    ('| EVAL hours_open = ', '| EVAL age_m = DATE_DIFF("minutes", opened, NOW())\n| EVAL age = ' + AGE.format(m='age_m')
     + '\n| EVAL hours_open = '),
    ('KEEP number, priority, ci.name, state_name, opened, hours_open,', 'KEEP number, priority, ci.name, state_name, opened, age, hours_open,')],
    AI)
set_query(p, q)
layer = data_layer(p)
i = next(n for n, c in enumerate(layer['columns']) if c['columnId'] == 'opened') + 1
layer['columns'].insert(i, {'columnId': 'age', 'fieldName': 'age', 'label': 'Age', 'customLabel': True,
                            'meta': {'type': 'string', 'esType': 'keyword'}, 'inMetricDimension': True})
for c in layer['columns']:
    if c['columnId'] == 'hours_open':
        c['label'] = 'Time as P1 / Duration (h)'
vc = p['embeddableConfig']['attributes']['state']['visualization']['columns']
i = next(n for n, c in enumerate(vc) if c['columnId'] == 'opened') + 1
vc.insert(i, {'columnId': 'age', 'isTransposed': False, 'isMetric': True, 'alignment': 'right', 'width': 90})
ec = p['embeddableConfig']
ec['title'] = ec['attributes']['title'] = AI
ec['description'] = sub(ec['description'], [
    ('Every active P1 and P2 incident, whatever its age, P1 first, longest first.',
     'Every active P1, P2 and P3 incident, whatever its age, P1 first, longest first; only the priorities picked in the '
     'Priorities control.'),
    ("On Hold P1s count, On Hold P2s do not.", ON_HOLD),
    ('for a P2, hours since it was opened (Duration).', 'for a P2 or P3, hours since it was opened (Duration). Age = time '
     'since the incident was opened.')], AI)

# ---- Escalation Channel: P3, Priorities, Age ----
p = P['Escalation Channel']
q = sub(p['embeddableConfig']['attributes']['state']['query']['esql'], [
    ('EVAL active = src == "inc" AND TO_INTEGER(priority) IN (1, 2) AND',
     'EVAL active = src == "inc" AND TO_INTEGER(priority) IN (1, 2, 3) AND ' + PRI.format('TO_INTEGER(priority)') + ' AND'),
    ('| SORT esc_priority ASC, number ASC', '| EVAL esc_age_m = DATE_DIFF("minutes", esc_opened, NOW())\n| EVAL esc_age = '
     + AGE.format(m='esc_age_m') + '\n| SORT esc_priority ASC, number ASC'),
    ('KEEP ci.name, number, esc_priority, esc_state, esc_opened,', 'KEEP ci.name, number, esc_priority, esc_state, esc_opened, esc_age,')],
    'Escalation Channel')
set_query(p, q)
layer = data_layer(p)
i = next(n for n, c in enumerate(layer['columns']) if c['columnId'] == 'esc_opened') + 1
layer['columns'].insert(i, {'columnId': 'esc_age', 'fieldName': 'esc_age', 'label': 'Age', 'customLabel': True,
                            'meta': {'type': 'string', 'esType': 'keyword'}, 'inMetricDimension': True})
vc = p['embeddableConfig']['attributes']['state']['visualization']['columns']
i = next(n for n, c in enumerate(vc) if c['columnId'] == 'esc_opened') + 1
vc.insert(i, {'columnId': 'esc_age', 'isTransposed': False, 'isMetric': True, 'alignment': 'right', 'width': 90})
ec = p['embeddableConfig']
ec['description'] = sub(ec['description'], [('one row per active P1 or P2 incident on the selected CI',
                                              'one row per active P1, P2 or P3 incident on the selected CI (only the '
                                              'priorities picked in the Priorities control)'),
                                             ('and when it was opened,', 'when it was opened and its age (time since opened),')],
                        'Escalation Channel')

# ---- Time to Resolve: P3 line, Priorities, day labels ----
TTR_OLD = 'P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)'
TTR = 'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)'
p = P[TTR_OLD]
q = sub(p['embeddableConfig']['attributes']['state']['query']['esql'], [
    ('NOW() - 14 days AND pri IN (1, 2), 1, 0)', 'NOW() - 14 days AND pri IN (1, 2, 3) AND ' + PRI.format('pri') + ', 1, 0)'),
    ('| EVAL h1 = CASE(pri_n == 1, hours), h2 = CASE(pri_n == 2, hours)',
     '| EVAL h1 = CASE(pri_n == 1, hours), h2 = CASE(pri_n == 2, hours), h3 = CASE(pri_n == 3, hours)'),
    ('p2_hours = ROUND(MEDIAN(h2), 1),', 'p2_hours = ROUND(MEDIAN(h2), 1), p3_hours = ROUND(MEDIAN(h3), 1),'),
    ('| SORT day ASC\n| KEEP day, p1_hours, p2_hours, incidents, open_now',
     '| SORT day ASC\n| EVAL day_label = DATE_FORMAT("MMM dd", day)\n| KEEP day_label, p1_hours, p2_hours, p3_hours, incidents, open_now, day')],
    TTR)
set_query(p, q)
st = p['embeddableConfig']['attributes']['state']
layer = data_layer(p)
cols = layer['columns']
day = next(c for c in cols if c['columnId'] == 'day')
cols.insert(0, {'columnId': 'day_label', 'fieldName': 'day_label', 'label': 'Day', 'customLabel': True,
                'meta': {'type': 'string', 'esType': 'keyword'}})
p2c = next(c for c in cols if c['columnId'] == 'p2_hours')
p3c = json.loads(json.dumps(p2c))
p3c.update(columnId='p3_hours', fieldName='p3_hours', label='P3')
cols.insert(cols.index(p2c) + 1, p3c)
for c in cols:
    if c['columnId'] == 'open_now':
        c['label'] = 'Resolved in the 7 days (P1–P3)'
vis = st['visualization']
dl = next(l for l in vis['layers'] if l['layerType'] == 'data')
dl['xAccessor'] = 'day_label'
dl['accessors'] = ['p1_hours', 'p2_hours', 'p3_hours']
dl['yConfig'].append({'forAccessor': 'p3_hours', 'color': '#3f6fb5', 'axisMode': 'left'})
rl = next(l for l in vis['layers'] if l['layerType'] == 'referenceLine')
ref = next(l for l in st['datasourceStates']['textBased']['layers'].values() if l['query']['esql'].startswith('ROW p1_target'))
ref['query'] = {'esql': 'ROW p1_target = 4.0, p2_target = 8.0, p3_target = 24.0'}
p2t = next(c for c in ref['columns'] if c['columnId'] == 'p2_target')
ref['columns'].append(dict(json.loads(json.dumps(p2t)), columnId='p3_target', fieldName='p3_target', label='P3 24h'))
rl['accessors'] = ['p1_target', 'p2_target', 'p3_target']
y2 = next(c for c in rl['yConfig'] if c['forAccessor'] == 'p2_target')
rl['yConfig'].append(dict(y2, forAccessor='p3_target', color='#3f6fb5'))
vis['axisTitlesVisibilitySettings']['x'] = False
ec = p['embeddableConfig']
ec['title'] = ec['attributes']['title'] = TTR
ec['description'] = sub(ec['description'], [
    ('P1 MTTR and P2 Duration, rolling 7-day median', 'P1 MTTR, P2 and P3 Duration, rolling 7-day median'),
    ('P2 line: Duration = hours from opened to resolved.', 'P2 and P3 lines: Duration = hours from opened to resolved.'),
    ('Each point covers the P1 or P2 incidents', 'Each point covers the P1, P2 or P3 incidents'),
    ('P2 8 h (amber).', 'P2 8 h (amber) and P3 24 h (blue). Only the priorities picked in the Priorities control.')], TTR)

# ---- controls: P3 in the Incident and CI lists; new Priorities control ----
pins = A['pinned_panels']['panels']
for v in pins.values():
    c = v['config']
    if c['variable_name'] == 'incident':
        c['esql_query'] = sub(c['esql_query'], [('WHERE priority IN (1, 2) AND', 'WHERE priority IN (1, 2, 3) AND')], 'incident')
    elif c['variable_name'] == 'ci':
        c['esql_query'] = c['esql_query'].replace('priority IN (1, 2)', 'priority IN (1, 2, 3)')
        assert c['esql_query'].count('priority IN (1, 2, 3)') == 2
for v in pins.values():
    v['order'] += 1
pid = str(uuid.uuid5(uuid.NAMESPACE_URL, 'mim-v5/control/priorities'))
pins[pid] = {'config': {'control_type': 'VALUES_FROM_QUERY',
                        'esql_query': 'ROW priorities = ["P1", "P2", "P3"]\n| MV_EXPAND priorities',
                        'selected_options': ['P1', 'P2', 'P3'], 'single_select': False, 'title': '🎚️ Priorities',
                        'variable_name': 'priorities', 'variable_type': 'values'},
             'grow': False, 'order': 0, 'type': 'esql_control', 'width': 'medium'}

# ---- 5. text fields shared by APM / CMDB relations and cmdb_with_apm_flag ----
FIELDS = ['ci.name', 'service.name', 'service.environment', 'host.name', 'ci.number', 'ci.support_group.l2.name',
          'parent.name', 'child.name', 'parent.class', 'child.class', 'is_marked_for_deletion']
OLD_FIX = '| EVAL ci.name = CASE(NOT (_index LIKE "*cmdb_with_apm_flag*"), TO_STRING(ci.name))'


def fix(q, name):
    assert q.count(OLD_FIX) == 1, name
    body = q.replace(OLD_FIX + '\n', '')
    used = [f for f in FIELDS if re.search(r'(?<![\w.`])' + re.escape(f) + r'(?![\w`])', body)]
    assert 'ci.name' in used, name
    conv = ', '.join(f'{f} = CASE(NOT from_flag, TO_STRING({f}))' for f in used)
    return q.replace(OLD_FIX, '| EVAL from_flag = _index LIKE "*cmdb_with_apm_flag*"\n| EVAL ' + conv), used


fixed = {}
for p in panels:
    ec = p['embeddableConfig']
    if p['type'] == 'vis' and title(p) in ('Application Health', 'Services of the Application'):
        q, fixed[title(p)] = fix(ec['attributes']['state']['query']['esql'], title(p))
        set_query(p, q)
    elif p['type'] == 'esql_control' and ec.get('variable_name') in ('service', 'application'):
        ec['esql_query'], fixed[ec['variable_name']] = fix(ec['esql_query'], ec['variable_name'])
assert len(fixed) == 4, fixed
assert not re.search(r'\bfrom_flag\b', json.dumps(old_panels))  # the name is new: no clash with an existing column

# ---- 6. Dashboard Links: Related Dashboards only ----
S4 = next(s for s in A['sections'] if s['title'] == '🔗 4 · Dashboard Links')['gridData']['i']
R = 'https://kibana-prod.gcp.cna.com/app/r/s/'
RELATED = [('Executive', '## 📈 Executive Dashboard (In Progress)', 10),
           ('Portfolio', '## 📊 [Portfolio ›](https://kibana-prod.gcp.cna.com/app/dashboards#/view/7511c5d1-3326-4c7e-91f4-6c8fdb686ee0)', 9),
           ('Applications Operations', f'## 🛡️ [Application Operations ›]({R}b4Jas)', 10),
           ('Major Incident Management', f'## 🚨 [Major Incident Management ›]({R}ZSMtk)', 10),
           ('Infrastructure Overview', f'## 🧭 [Infra Overview ›]({R}bUy3F)', 9)]
s4 = {title(p): p for p in panels if p['gridData'].get('sectionId') == S4}
assert 'Detailed Dashboards heading' in s4, 'section 4 is not the 17e Dashboard Links'
keep = [s4['Related Dashboards heading']]
x = 0
for key, content, w in RELATED:
    t = s4[f'{key} link']
    t['embeddableConfig']['content'] = content
    t['gridData'].update(x=x, y=2, w=w, h=4)
    x += w
    keep.append(t)
assert x == 48
panels = [p for p in panels if p['gridData'].get('sectionId') != S4] + keep

A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: P3 back, Priorities control, Age columns, Time to Resolve day labels, text-field fix ({fixed}), links')
