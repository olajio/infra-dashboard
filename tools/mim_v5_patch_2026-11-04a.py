"""MIM V5 patch 04a (4 Nov 2026), applied to the team's manual layout export (`updated mim v5.ndjson`).

Usage: mim_v5_patch_2026-11-04a.py "updated mim v5.ndjson" "MIM V5.ndjson"

From new_suggestions2.txt:
- **Escalate:** the "CI support group" column is removed; "State" (the incident's state from its latest record,
  as in Active Incidents) and "Opened" are added after Priority.
- **Active Incidents:** an "Opened" column (when the incident was opened) after State.
- **Open Alerts with No Incident:** with an incident or a CI picked, only alerts on that CI and on CIs linked to it in
  the CMDB (both directions), still only those with no open incident; with nothing picked, every alert as before. It
  now reads the CMDB links, so its panel range is 5 years and the 24 h window is in the query (same alerts as before).
Controls made harder to miss:
- Icons in the control titles (top bar and section 3); the top-bar controls grow to the full width.
- A "Start here" banner at the top of section 1 (pick an Incident or a CI) and of section 3 (pick a Server,
  Application, Service).
"""
import json
import sys
import uuid

SRC, OUT = sys.argv[1:3]
uid = lambda name: str(uuid.uuid5(uuid.NAMESPACE_URL, 'mim-dashboard/v5/' + name))
TGT = 'CASE(?incident == "(all incidents)", ?ci, SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))'

lines = [json.loads(l) for l in open(SRC) if l.strip()]
dash = next(o for o in lines if o.get('type') == 'dashboard')
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = {title(p): p for p in panels}
assert 'Start here' not in A['panelsJSON'], 'already applied'


def lens(t):
    st = P[t]['embeddableConfig']['attributes']['state']
    (lid, layer), = st['datasourceStates']['textBased']['layers'].items()
    return st, layer


def set_query(t, old, new):
    st, layer = lens(t)
    assert st['query']['esql'] == old and layer['query']['esql'] == old
    st['query']['esql'] = new
    layer['query']['esql'] = new


def set_columns(t, order, add_layer, add_viz, drop=()):
    """Reorder the table's columns to `order`, adding the new ones and dropping `drop`."""
    st, layer = lens(t)
    for key in ('columns', 'allColumns'):
        if key in layer:
            cols = {c['columnId']: c for c in layer[key] if c['columnId'] not in drop}
            cols.update({k: v for k, v in add_layer.items()})
            layer[key] = [cols[c] for c in order if c in cols] + [c for k, c in cols.items() if k not in order]
    viz = {c['columnId']: c for c in st['visualization']['columns'] if c['columnId'] not in drop}
    viz.update(add_viz)
    st['visualization']['columns'] = [viz[c] for c in order]


S = lambda cid, label: {'columnId': cid, 'fieldName': cid, 'label': label, 'customLabel': True,
                        'meta': {'type': 'string', 'esType': 'keyword'}, 'inMetricDimension': True}
D = lambda cid, label: {'columnId': cid, 'fieldName': cid, 'label': label, 'customLabel': True,
                        'meta': {'type': 'date', 'esType': 'date'}, 'inMetricDimension': True}
V = lambda cid, w: {'columnId': cid, 'isTransposed': False, 'isMetric': True, 'alignment': 'left', 'width': w}

# ------------------------------------------------------------------ Escalate: State + Opened in, CI support group out
E = 'Escalate'
q = lens(E)[0]['query']['esql']
n = q
for a, b in [
    ('managers = VALUES(TO_STRING(assignment_group.manager.name)), manager_emails = VALUES(TO_STRING(assignment_group.manager.email))\n  BY',
     'managers = VALUES(TO_STRING(assignment_group.manager.name)), manager_emails = VALUES(TO_STRING(assignment_group.manager.email)),\n'
     '        latest_state = MAX(CONCAT(TO_STRING(TO_LONG(@timestamp)), "~", TO_STRING(state_name))), esc_opened = MAX(TO_DATETIME(opened_at))\n  BY'),
    ('| EVAL esc_priority = TO_INTEGER(priority),',
     '| DISSECT latest_state "%{_state_ts}~%{state_now}"\n| EVAL esc_priority = TO_INTEGER(priority), esc_state = COALESCE(state_now, "—"),'),
    ('       esc_support_group = COALESCE(MV_FIRST(groups), "—"),\n', ''),
    ('| KEEP ci.name, number, esc_priority, esc_class, esc_env, esc_support_group, esc_assignment_group,',
     '| KEEP ci.name, number, esc_priority, esc_state, esc_opened, esc_class, esc_env, esc_assignment_group,'),
]:
    assert n.count(a) == 1, a[:60]
    n = n.replace(a, b)
set_query(E, q, n)
set_columns(E, ['ci.name', 'number', 'esc_priority', 'esc_state', 'esc_opened', 'esc_class', 'esc_env', 'esc_assignment_group',
                'assignee', 'assignee_email', 'group_manager', 'manager_email'],
            {'esc_state': S('esc_state', 'State'), 'esc_opened': D('esc_opened', 'Opened')},
            {'esc_state': V('esc_state', 100), 'esc_opened': V('esc_opened', 160)}, drop=('esc_support_group',))
ec = P[E]['embeddableConfig']
ec['description'] = ec['description'].replace(
    "with the CI's CMDB class, environment and support group (from the CMDB enrichment on the server metrics)",
    "its state (from its latest record, as in Active Incidents) and when it was opened, with the CI's CMDB class and "
    "environment (from the CMDB enrichment on the server metrics)")

# ------------------------------------------------------------------ Active Incidents: Opened
AI = 'Active Incidents (P1 · P2 over 8 h · P3 over 24 h)'
q = lens(AI)[0]['query']['esql']
a = '| KEEP number, priority, ci.name, state_name, sla,'
assert q.count(a) == 1
set_query(AI, q, q.replace(a, '| KEEP number, priority, ci.name, state_name, opened, sla,'))
set_columns(AI, ['number', 'priority', 'ci.name', 'state_name', 'opened', 'sla', 'assignment_group', 'assignee',
                 'assignee_email', 'group_manager', 'manager_email', 'short_description'],
            {'opened': D('opened', 'Opened')}, {'opened': V('opened', 160)})
P[AI]['embeddableConfig']['description'] = (P[AI]['embeddableConfig'].get('description', '').rstrip()
                                             + ' Opened = when the incident was opened in ServiceNow.')

# ------------------------------------------------------------------ Open Alerts with No Incident: the selected CI's
OA = 'Open Alerts with No Incident'
q = lens(OA)[0]['query']['esql']
NAMES = f'({TGT}, TO_UPPER({TGT}), TO_LOWER({TGT}))'
head_old = ('FROM .ds-bridge-alerts-netcool-default-*, servicenow-incidents-* METADATA _index\n'
            '| WHERE _index LIKE "*netcool*" OR (state_name NOT IN ("Resolved", "Closed", "Canceled", "Cancelled") AND opened_at >= NOW() - 31 days)\n'
            '| EVAL src = CASE(_index LIKE "*servicenow*", "inc", "alert")\n')
head_new = ('FROM .ds-bridge-alerts-netcool-default-*, servicenow-incidents-*, cmdb-ci-relations* METADATA _index\n'
            '| WHERE (_index LIKE "*netcool*" AND @timestamp >= NOW() - 24 hours)\n'
            '     OR (_index LIKE "*servicenow*" AND @timestamp >= NOW() - 24 hours AND state_name NOT IN ("Resolved", "Closed", "Canceled", "Cancelled") AND opened_at >= NOW() - 31 days)\n'
            f'     OR (_index LIKE "*relations*" AND {TGT} != "(no CI selected)" AND (parent.name IN {NAMES} OR child.name IN {NAMES})\n'
            '         AND COALESCE(TO_LOWER(TO_STRING(is_marked_for_deletion)), "false") != "true")\n'
            '| EVAL src = CASE(_index LIKE "*servicenow*", "inc", _index LIKE "*relations*", "rel", "alert")\n')
where_old = '| WHERE src == "alert" AND has_inc == 0 AND ('
where_new = (f'| EVAL tgt = TO_LOWER({TGT}), p_l = TO_LOWER(TO_STRING(parent.name)), c_l = TO_LOWER(TO_STRING(child.name))\n'
             '| EVAL lkey = CASE(src == "rel", CASE(p_l == tgt, c_l, p_l),\n'
             '                   TO_LOWER(COALESCE(TO_STRING(ci.name), REPLACE(TO_STRING(node), "[.][Cc][Nn][Aa][.][Cc][Oo][Mm]$", "")))),\n'
             '       is_rel = CASE(src == "rel", 1, 0)\n'
             '| INLINE STATS linked = MAX(is_rel) BY lkey\n'
             f'| WHERE src == "alert" AND has_inc == 0 AND ({TGT} == "(no CI selected)" OR lkey == tgt OR linked == 1) AND (')
assert q.startswith(head_old) and q.count(where_old) == 1
set_query(OA, q, head_new + q[len(head_old):].replace(where_old, where_new))
oa = P[OA]['embeddableConfig']
oa['time_range'] = {'from': 'now-5y', 'to': 'now'}
oa['description'] = (oa.get('description', '').rstrip() + ' With an incident or a CI picked: only alerts on that CI and '
                     'on CIs linked to it in the CMDB (its server, ESX host, switch, applications …). Last 24 hours; the '
                     'panel shows "Last 5 years" only because it also reads the CMDB links.')

# ------------------------------------------------------------------ controls: icons, full width, "Start here" banners
ICONS = {'incident': '🚨 Incident', 'ci': '🖥️ CI', 'monitored_app': '🧩 Monitored application',
         'server': '🖥️ Server', 'application': '🧩 Application', 'service': '⚙️ Service', 'health_window': '⏱️ Health window'}
for v in A['pinned_panels']['panels'].values():
    v['config']['title'] = ICONS[v['config']['variable_name']]
    v['grow'] = True
for p in panels:
    if p['type'] == 'esql_control':
        p['embeddableConfig']['title'] = ICONS[p['embeddableConfig']['variable_name']]


def banner(name, step, headline, detail, section, colour='#0b64dd'):
    spec = {
        '$schema': 'https://vega.github.io/schema/vega/v5.json', 'autosize': {'type': 'fit', 'contains': 'padding'},
        'padding': 0,
        'marks': [
            {'type': 'rect', 'encode': {'update': {'x': {'value': 0}, 'y': {'value': 0}, 'width': {'signal': 'width'},
                                                   'height': {'signal': 'height'}, 'fill': {'value': colour},
                                                   'fillOpacity': {'value': 0.16}, 'cornerRadius': {'value': 6}}}},
            {'type': 'rect', 'encode': {'update': {'x': {'value': 0}, 'y': {'value': 0}, 'width': {'value': 6},
                                                   'height': {'signal': 'height'}, 'fill': {'value': colour}}}},
            {'type': 'symbol', 'encode': {'update': {'x': {'value': 30}, 'y': {'signal': 'height / 2'},
                                                     'shape': {'value': 'circle'}, 'size': {'value': 700},
                                                     'fill': {'value': colour}}}},
            {'type': 'text', 'encode': {'update': {'x': {'value': 30}, 'y': {'signal': 'height / 2 + 1'},
                                                   'text': {'value': step}, 'align': {'value': 'center'},
                                                   'baseline': {'value': 'middle'}, 'fontSize': {'value': 15},
                                                   'fontWeight': {'value': 'bold'}, 'fill': {'value': 'white'}}}},
            {'type': 'text', 'encode': {'update': {'x': {'value': 54}, 'y': {'signal': 'height / 2 - 8'},
                                                   'text': {'value': headline}, 'baseline': {'value': 'middle'},
                                                   'fontSize': {'value': 15}, 'fontWeight': {'value': 'bold'},
                                                   'fill': {'value': colour}, 'limit': {'signal': 'width - 70'}}}},
            {'type': 'text', 'style': 'guide-label',
             'encode': {'update': {'x': {'value': 54}, 'y': {'signal': 'height / 2 + 11'}, 'text': {'value': detail},
                                   'baseline': {'value': 'middle'}, 'fontSize': {'value': 12},
                                   'limit': {'signal': 'width - 70'}}}},
        ]}
    pid = uid('banner/' + name)
    return {'type': 'legacy_vis', 'panelIndex': pid,
            'gridData': {'x': 0, 'y': 0, 'w': 48, 'h': 3, 'i': pid, 'sectionId': section},
            'embeddableConfig': {'title': name, 'hide_title': True,
                                 'description': 'How to use the controls. Not data.',
                                 'savedVis': {'title': name, 'description': '', 'type': 'vega',
                                              'params': {'spec': json.dumps(spec, indent=2)}, 'uiState': {},
                                              'data': {'aggs': [], 'searchSource': {}}}}}


# Needs attention now: at the team's 7-column width the legend labels collided; P2 / P3 are enough (subtitle says the rest)
hv = P['Needs attention now']['embeddableConfig']['savedVis']['params']
for o, n2 in (("'P2 > 8 h  ' + p2", "'P2  ' + p2"), ("'P3 > 24 h  ' + p3", "'P3  ' + p3")):
    assert hv['spec'].count(o) == 1, o
    hv['spec'] = hv['spec'].replace(o, n2)

S1 = P['Active P1']['gridData']['sectionId']
S3 = P['Application Health']['gridData']['sectionId']
for p in panels:
    if p['gridData'].get('sectionId') in (S1, S3):
        p['gridData']['y'] += 3
panels.append(banner('Start here', '1', '▲  Start here: pick an Incident, or a CI, in the controls at the top',
                     'Sections 2 and 3 follow it. More (⋯) → Reset changes clears every pick.', S1))
panels.append(banner('Then pick a server, application and service', '2',
                     '▼  For an application service, pick one of its servers, then an Application and a Service',
                     'Server: the health panels (a server CI fills them by itself) · Application: Services of the Application · '
                     'Service: Upstream, Service health, Downstream', S3))

A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
with open(OUT, 'w') as f:
    for o in lines:
        if o.get('type') or 'exportedCount' not in o:   # drop Kibana's export summary line
            f.write(json.dumps(o, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: Escalate (State, Opened; no CI support group), Active Incidents (Opened), Open Alerts scoped to the CI, '
      f'control icons, 2 banners; {len(panels)} panels')
