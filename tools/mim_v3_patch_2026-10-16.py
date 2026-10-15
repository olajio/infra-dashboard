"""MIM V3 changes from suggestions2.txt (16 Oct 2026 update).

Usage: mim_v3_patch_2026-10-16.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, on the 15 Oct version)

- Users impacted: text "Real count to be incorporated from ServiceNow and RUM", black background
- Applications impacted removed
- Active P1 / P2: a Vega donut on a black background (Lens charts cannot take a background colour)
- Active Incidents: Incident, Pri, Affected CI, State, SLA, Assignment Group, Assignee, Assignee Email, Group Manager
  Name, Manager Email Id (Assigned MIM, Opened, Age and Short description removed)
- Escalate: CI, Active Incident, Priority, Class, Env, CI support group, Assignment Group, Assignee, Assignee Email,
  Group Manager Name, Manager Email Id (Assigned MIM removed)
- Open Alerts with No Incident: last 24 hours
- Applications that depend on this CI: CMDB status column removed
- What this CI runs on: removed
"""
import copy
import json
import sys

SRC, OUT = sys.argv[1:3]
RED, AMBER, WHITE, LIGHT = '#e7664c', '#f1c40f', '#ffffff', '#c9ced6'
CLOSED = '("Resolved", "Closed", "Canceled", "Cancelled")'

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = lambda t: next(p for p in panels if title(p) == t)
st = lambda p: p['embeddableConfig']['attributes']['state']
layer = lambda p: next(iter(st(p)['datasourceStates']['textBased']['layers'].values()))


def set_query(p, q):
    layer(p)['query']['esql'] = q
    st(p)['query'] = {'esql': q}


def col(cid, label):
    return {'columnId': cid, 'fieldName': cid, 'label': label, 'customLabel': True,
            'meta': {'type': 'string', 'esType': 'keyword'}, 'inMetricDimension': True}


def tcol(cid, width):
    return {'columnId': cid, 'isTransposed': False, 'isMetric': True, 'alignment': 'left', 'width': width}


def set_table(p, order, extra_cols, widths):
    """Keep the existing column definitions (badges, links) for known columns, add new ones, in this order."""
    L, vis = layer(p), st(p)['visualization']
    known = {c['columnId']: c for c in L['columns']}
    known_vis = {c['columnId']: c for c in vis['columns']}
    known.update({c['columnId']: c for c in extra_cols})
    L['columns'] = [known[c] for c in order]
    L['allColumns'] = copy.deepcopy(L['columns'])
    vis['columns'] = [dict(known_vis.get(c) or tcol(c, 150), **({'width': widths[c]} if c in widths else {}))
                      for c in order]


PEOPLE = [col('assignee', 'Assignee'), col('assignee_email', 'Assignee Email'),
          col('group_manager', 'Group Manager Name'), col('manager_email', 'Manager Email Id')]
PEOPLE_VALUES = '''assignees = VALUES(TO_STRING(assigned_to.name)), assignee_emails = VALUES(TO_STRING(assigned_to.email)),
        managers = VALUES(TO_STRING(assignment_group.manager.name)), manager_emails = VALUES(TO_STRING(assignment_group.manager.email))'''
PEOPLE_EVAL = '''assignee = COALESCE(MV_FIRST(assignees), "—"), assignee_email = COALESCE(MV_FIRST(assignee_emails), "—"),
       group_manager = COALESCE(MV_FIRST(managers), "—"), manager_email = COALESCE(MV_FIRST(manager_emails), "—")'''
PEOPLE_WIDTHS = {'assignee': 160, 'assignee_email': 220, 'group_manager': 160, 'manager_email': 230}

# ------------------------------------------------------------------ Active Incidents: the people columns, no MIM
inc = P('Active Incidents (P1 / P2)')
q = layer(inc)['query']['esql']
head = q[:q.index('| INLINE STATS')]
head = head.replace('FROM servicenow-incidents-*, servicenow-task-sla-*, .ds-logs-servicenow.event-default-* METADATA _index\n'
                    '| WHERE servicenow.event.table_name IS NULL OR (servicenow.event.table_name == "incident" AND '
                    'servicenow.event.promoted_by.display_value IS NOT NULL AND servicenow.event.promoted_by.display_value != "")\n',
                    'FROM servicenow-incidents-*, servicenow-task-sla-* METADATA _index\n')
head = head.replace('| EVAL src = CASE(_index LIKE "*task-sla*", "sla", _index LIKE "*servicenow.event*", "sn", "inc")',
                    '| EVAL src = CASE(_index LIKE "*task-sla*", "sla", "inc")')
head = head.replace('src == "sn", TO_STRING(servicenow.event.number.value), ', '')
head = head.replace('| WHERE src IN ("sla", "sn") OR is_active == 1', '| WHERE src == "sla" OR is_active == 1')
assert 'servicenow.event' not in head and '"sn"' not in head
set_query(inc, head + f'''| INLINE STATS worst = MIN(sla_rank) BY inc
| WHERE src == "inc"
| STATS opened = MAX(TO_DATETIME(opened_at)), grp = VALUES(TO_STRING(assignment_group.name)), worst = MIN(worst),
        {PEOPLE_VALUES}
  BY number, priority, ci.name, state_name
| EVAL age_minutes = DATE_DIFF("minutes", opened, NOW()), target = CASE(priority == 1, 240, 480)
| EVAL sla = CASE(
      worst == 1, "Breached", worst == 2, "Breaching", worst == 3, "Paused", worst == 4, "Within SLA", worst == 5, "Met",
      age_minutes >= target, "Breached (age)", age_minutes >= target * 0.8, "At risk (age)", "Within SLA (age)")
| EVAL grp1 = MV_FIRST(grp)
| EVAL assignment_group = CASE(grp1 IS NULL OR grp1 == "", "—", grp1), {PEOPLE_EVAL}
| SORT priority ASC, age_minutes DESC
| KEEP number, priority, ci.name, state_name, sla, assignment_group, assignee, assignee_email, group_manager, manager_email''')
set_table(inc, ['number', 'priority', 'ci.name', 'state_name', 'sla', 'assignment_group', 'assignee', 'assignee_email',
                'group_manager', 'manager_email'], PEOPLE, dict(PEOPLE_WIDTHS, assignment_group=220))
for c in layer(inc)['columns'] + layer(inc)['allColumns']:
    if c['columnId'] == 'assignment_group':
        c['label'] = 'Assignment Group'
d = inc['embeddableConfig']['description']
d = d[:d.index(' Assigned MIM =')] + d[d.index('".') + 2:] if ' Assigned MIM =' in d else d
inc['embeddableConfig']['description'] = d.replace('To investigate, pick', 'Assignee and Group Manager (with their emails) '
                                                   'come from the incident\'s assigned_to and assignment group. To investigate, pick')

# ------------------------------------------------------------------ Escalate: the people columns, no MIM
esc = P('Escalate')
q = layer(esc)['query']['esql']
q = q.replace('FROM servicenow-incidents-*, .ds-metrics-system.cpu-default*, .ds-logs-servicenow.event-default-* METADATA _index',
              'FROM servicenow-incidents-*, .ds-metrics-system.cpu-default* METADATA _index')
q = q.replace(' OR (servicenow.event.table_name == "incident" AND servicenow.event.promoted_by.display_value IS NOT NULL AND '
              'servicenow.event.promoted_by.display_value != "")', '')
q = q.replace('''| EVAL src = CASE(_index LIKE "*servicenow.event*", "sn", _index LIKE "*servicenow*", "inc", "met")
| EVAL key = CASE(src == "sn", TO_STRING(servicenow.event.number.value), TO_STRING(number)),
       mim = CASE(src == "sn", TO_STRING(servicenow.event.promoted_by.display_value))
| INLINE STATS mims = VALUES(mim) BY key
| WHERE src != "sn"
''', '''| EVAL src = CASE(_index LIKE "*servicenow*", "inc", "met")
''')
q = q.replace('''| STATS classes = VALUES(classes), envs = VALUES(envs), groups = VALUES(groups), mims = VALUES(mims),
        mgrs = VALUES(TO_STRING(assignment_group.manager.name))''', f'''| STATS classes = VALUES(classes), envs = VALUES(envs), groups = VALUES(groups),
        {PEOPLE_VALUES}''')
q = q.replace(''',
       esc_mim = CASE(number IS NULL, "—", CASE(mims IS NOT NULL, MV_FIRST(mims), mgrs IS NOT NULL, CONCAT(MV_FIRST(mgrs), " (group manager)"), "—"))''',
              f''',
       {PEOPLE_EVAL}''')
q = q.replace('| KEEP ci.name, number, esc_priority, esc_mim, esc_class, esc_env, esc_support_group, esc_assignment_group',
              '| KEEP ci.name, number, esc_priority, esc_class, esc_env, esc_support_group, esc_assignment_group, assignee, '
              'assignee_email, group_manager, manager_email')
assert 'servicenow.event' not in q and 'mim' not in q and 'assignee_email' in q, q
set_query(esc, q)
set_table(esc, ['ci.name', 'number', 'esc_priority', 'esc_class', 'esc_env', 'esc_support_group', 'esc_assignment_group',
                'assignee', 'assignee_email', 'group_manager', 'manager_email'], PEOPLE,
          dict(PEOPLE_WIDTHS, esc_support_group=220, esc_assignment_group=220))
d = esc['embeddableConfig']['description']
esc['embeddableConfig']['description'] = (d[:d.index(' Assigned MIM =')] if ' Assigned MIM =' in d else d) + (
    ' Assignee and Group Manager (with their emails) come from the incident\'s assigned_to and assignment group.')

# ------------------------------------------------------------------ Applications that depend on this CI: no CMDB status
dep = P('Applications that depend on this CI')
q = layer(dep)['query']['esql']
q = q.replace('| KEEP parent_ci.name.keyword, app_kind, app_how, app_status, app_env, app_number',
              '| KEEP parent_ci.name.keyword, app_kind, app_how, app_env, app_number')
assert 'KEEP parent_ci.name.keyword, app_kind, app_how, app_env, app_number' in q
set_query(dep, q)
set_table(dep, ['parent_ci.name.keyword', 'app_kind', 'app_how', 'app_env', 'app_number'], [],
          {'parent_ci.name.keyword': 300, 'app_kind': 200, 'app_how': 260, 'app_env': 120, 'app_number': 140})
dep['embeddableConfig']['description'] = dep['embeddableConfig']['description'].replace(
    ', with their CMDB operational status', '')

# ------------------------------------------------------------------ Open Alerts with No Incident: last 24 hours
oa = P('Open Alerts with No Incident')
oa['embeddableConfig']['time_range'] = {'from': 'now-24h', 'to': 'now'}
oa['embeddableConfig']['description'] = oa['embeddableConfig']['description'].replace(
    'Last 30 days (fixed)', 'Last 24 hours (fixed): alerts and open incidents seen in the last 24 hours')

# ------------------------------------------------------------------ removed panels
panels.remove(P('Applications impacted'))
panels.remove(P('What this CI runs on'))
P('Applications that depend on this CI')['gridData'].update(w=41)

# ------------------------------------------------------------------ black first two panels: Active P1 / P2 (Vega donut), Users impacted
users = P('Users impacted')
spec = json.loads(users['embeddableConfig']['savedVis']['params']['spec'])
spec['data'][0]['values'][0].update(detail='Real count to be incorporated|from ServiceNow and RUM', names_txt='',
                                    colour='#000000')
for m in spec['marks'][0]['marks']:
    m['encode']['update']['fill'] = {'value': LIGHT}
spec['marks'][0]['marks'][3]['encode']['update']['fill'] = {'value': WHITE}
spec['background'] = '#000000'
users['embeddableConfig']['savedVis']['params']['spec'] = json.dumps(spec, indent=2, ensure_ascii=False)
users['embeddableConfig']['description'] = (
    'Placeholder (demo number). The real count of users affected by the active P1 / P2 incidents is to be '
    'incorporated from ServiceNow and RUM (real-user monitoring).')

DONUT_Q = f'''FROM servicenow-incidents-*
| WHERE @timestamp >= NOW() - 1 month AND priority IN (1, 2) AND state_name NOT IN {CLOSED} AND number IS NOT NULL
| STATS pri = MIN(TO_INTEGER(priority)) BY number
| EVAL label = CASE(pri == 1, "P1", "P2")
| STATS incidents = COUNT(*) BY label
| SORT label ASC'''
DONUT = {
    '$schema': 'https://vega.github.io/schema/vega/v5.json', 'autosize': {'type': 'fit', 'contains': 'padding'},
    'padding': 8, 'background': '#000000',
    'data': [
        {'name': 'raw', 'url': {'%type%': 'esql', 'query': DONUT_Q}},
        {'name': 'slices', 'source': 'raw', 'transform': [{'type': 'pie', 'field': 'incidents', 'sort': False}]},
        {'name': 'total', 'source': 'raw', 'transform': [{'type': 'aggregate', 'fields': ['incidents'], 'ops': ['sum'],
                                                          'as': ['n']}]}],
    'signals': [{'name': 'r', 'update': 'min(width * 0.6, height) / 2'}],
    'scales': [{'name': 'colour', 'type': 'ordinal', 'domain': ['P1', 'P2'], 'range': [RED, AMBER]}],
    'marks': [
        {'type': 'arc', 'from': {'data': 'slices'}, 'encode': {'update': {
            'x': {'signal': 'r + 4'}, 'y': {'signal': 'height / 2'}, 'startAngle': {'field': 'startAngle'},
            'endAngle': {'field': 'endAngle'}, 'innerRadius': {'signal': 'r * 0.58'}, 'outerRadius': {'signal': 'r'},
            'padAngle': {'value': 0.02}, 'fill': {'scale': 'colour', 'field': 'label'},
            'tooltip': {'signal': "{'Priority': datum.label, 'Active incidents': datum.incidents}"}}}},
        {'type': 'text', 'from': {'data': 'total'}, 'encode': {'update': {
            'x': {'signal': 'r + 4'}, 'y': {'signal': 'height / 2 - 4'}, 'align': {'value': 'center'},
            'baseline': {'value': 'middle'}, 'text': {'signal': 'datum.n'}, 'fontSize': {'signal': 'max(r * 0.42, 14)'},
            'fontWeight': {'value': 'bold'}, 'fill': {'value': WHITE}}}},
        {'type': 'text', 'encode': {'update': {
            'x': {'signal': 'r + 4'}, 'y': {'signal': 'height / 2 + r * 0.28'}, 'align': {'value': 'center'},
            'baseline': {'value': 'middle'}, 'text': {'value': 'active'}, 'fontSize': {'value': 12},
            'fill': {'value': LIGHT}}}},
        {'type': 'text', 'from': {'data': 'raw'}, 'encode': {'update': {
            'x': {'signal': '2 * r + 24'}, 'y': {'signal': "height / 2 + (datum.label == 'P1' ? -22 : 22)"},
            'baseline': {'value': 'middle'}, 'text': {'signal': "datum.label + '  ' + datum.incidents"},
            'fontSize': {'value': 24}, 'fontWeight': {'value': 'bold'}, 'fill': {'scale': 'colour', 'field': 'label'}}}}]}
donut = P('Active P1 / P2')
donut['type'] = 'legacy_vis'
donut['embeddableConfig'] = {
    'savedVis': {'title': 'Active P1 / P2', 'description': '', 'type': 'vega',
                 'params': {'spec': json.dumps(DONUT, indent=2, ensure_ascii=False)}, 'uiState': {},
                 'data': {'aggs': [], 'searchSource': {'query': {'query': '', 'language': 'kuery'}, 'filter': []}}},
    'title': 'Active P1 / P2',
    'description': 'How many P1 (red) and P2 (amber) incidents are active now (priority 1 or 2, state not Resolved, '
                   'Closed, Canceled or Cancelled), with the total in the middle. Last 1 month; not narrowed by the '
                   'Incident or CI controls.'}

# section 1 first row: donut, Users impacted, trend
for t, (x, w) in {'Active P1 / P2': (0, 14), 'Users impacted': (14, 10),
                  'P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)': (24, 24)}.items():
    P(t)['gridData'].update(x=x, w=w)

# ------------------------------------------------------------------ checks
for s in {p['gridData']['sectionId'] for p in panels}:
    cells = {}
    for p in panels:
        g = p['gridData']
        if g['sectionId'] != s:
            continue
        for x in range(g['x'], g['x'] + g['w']):
            for y in range(g['y'], g['y'] + g['h']):
                assert (x, y) not in cells, (title(p), cells[(x, y)])
                cells[(x, y)] = title(p)
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{len(panels)} panels')
