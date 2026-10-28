"""Build the CI-driven Infrastructure Dashboard from MIM V3's panels (28 Oct 2026, dashboard_kpis.txt).

Usage: build_infra_dashboard.py "MIM V3.ndjson" "Infrastructure Dashboard.ndjson"

Control input: the CI control (pinned, the same as MIM V3's). Three sections, one per KPI group:
  1 · Incidents, changes and alerts      2 · Infrastructure overview (incl. cloud)      3 · Applications overview
Achieved KPIs reuse MIM V3's tested panels; KPIs not achievable yet are placeholder cards that say why.
MIM V3's panels also read the Incident control, which this dashboard doesn't have: `?incident` is replaced by its
"(all incidents)" default, so every panel follows the CI control (and, for the health panels, the optional Server
control).
"""
import copy
import json
import sys
import uuid

SRC, OUT = sys.argv[1:3]
NS = 'infra-dashboard/ci-driven-v1/'
uid = lambda name: str(uuid.uuid5(uuid.NAMESPACE_URL, NS + name))
DASH_ID = uid('dashboard')
S1, S2, S3 = uid('section-1'), uid('section-2'), uid('section-3')
WINDOW_30D = {'from': 'now-30d', 'to': 'now'}

mim = json.loads(open(SRC).readline())
MA = mim['attributes']
mim_panels = json.loads(MA['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
MP = {title(p): p for p in mim_panels}


def no_incident(o):
    """Replace the Incident control variable with its default everywhere in a panel."""
    if isinstance(o, dict):
        return {k: no_incident(v) for k, v in o.items()}
    if isinstance(o, list):
        return [no_incident(v) for v in o]
    if isinstance(o, str):
        o = o.replace('CASE(?incident == "(all incidents)", ?ci, SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))', '?ci')
        return o.replace('?incident', '"(all incidents)"')
    return o


DESC_FIXES = [
    ('the Incident / CI controls', 'the CI control'), ('the Incident or CI controls', 'the CI control'),
    ('the Incident and CI controls', 'the CI control'), ('Incident / CI controls', 'CI control'),
    ("the incident's CI, else the CI control", 'the CI control'), ("the incident's CI or the CI control", 'the CI control'),
    ("(the picked incident's CI, or the CI control)", '(the CI control)'),
    ("the Incident's CI if it is a server, else the CI control's value if it is a server, else the Server control's value",
     "the CI control's value if it is a server, else the Server control's value"),
    ("(the picked incident's affected CI, else the CI control)", '(the CI control)'),
]


def copy_panel(name, section, x, y, w, h, new_title=None, description=None, time_range=None):
    p = no_incident(copy.deepcopy(MP[name]))
    pid = uid('panel/' + (new_title or name))
    p['panelIndex'] = pid
    p['gridData'] = {'x': x, 'y': y, 'w': w, 'h': h, 'i': pid, 'sectionId': section}
    ec = p['embeddableConfig']
    if new_title:
        ec['title'] = new_title
        for holder in (ec.get('attributes'), ec.get('savedVis')):
            if holder and 'title' in holder:
                holder['title'] = new_title
    if description is not None:
        ec['description'] = description
    elif ec.get('description'):
        for a, b in DESC_FIXES:
            ec['description'] = ec['description'].replace(a, b)
    if time_range:
        ec['time_range'] = dict(time_range)
    return p


def placeholder(name, section, x, y, w, h, body):
    pid = uid('placeholder/' + name)
    return {'type': 'markdown', 'panelIndex': pid,
            'gridData': {'x': x, 'y': y, 'w': w, 'h': h, 'i': pid, 'sectionId': section},
            'embeddableConfig': {'title': name, 'content': f'**Not available yet.** {body}',
                                 'settings': {'open_links_in_new_tab': True}}}


DV_ID = uid('dataview/servicenow-incidents')
ACTIVE = 'TO_STRING(state_name) NOT IN ("Resolved", "Closed", "Canceled", "Cancelled")'


def count_tile(name, pri, colour, section, x, y, w, h):
    q = ('FROM servicenow-incidents-*\n'
         f'| WHERE TO_STRING(number) LIKE "INC*" AND TO_INTEGER(priority) == {pri} AND {ACTIVE}\n'
         '| WHERE ?ci == "(no CI selected)" OR TO_STRING(ci.name) == ?ci\n'
         '| STATS metric_val = COUNT_DISTINCT(number)')
    layer = uid('layer/' + name)
    pid = uid('panel/' + name)
    stops = [{'color': '#1f9e6b', 'stop': 0}, {'color': colour, 'stop': 1}]
    return {
        'type': 'vis', 'panelIndex': pid,
        'gridData': {'x': x, 'y': y, 'w': w, 'h': h, 'i': pid, 'sectionId': section},
        'embeddableConfig': {
            'title': name, 'hide_title': True,
            'description': (f'Open P{pri} incidents (priority {pri}, state not Resolved, Closed, Canceled or Cancelled) '
                            'on the CI picked in the CI control; every CI when none is picked. Green at 0. '
                            'Incidents opened in the last 30 days (fixed): the incident record\'s @timestamp is its '
                            'opened time.'),
            'time_range': dict(WINDOW_30D),
            'attributes': {
                'title': name, 'references': [], 'visualizationType': 'lnsMetric', 'version': 2,
                'state': {
                    'datasourceStates': {'textBased': {
                        'layers': {layer: {
                            'index': DV_ID, 'query': {'esql': q}, 'timeField': '@timestamp',
                            'columns': [{'columnId': 'metric_val', 'fieldName': 'metric_val', 'label': name,
                                         'customLabel': True, 'meta': {'type': 'number', 'esType': 'long'},
                                         'inMetricDimension': True}]}},
                        'indexPatternRefs': [{'id': DV_ID, 'title': 'servicenow-incidents-*',
                                              'timeField': '@timestamp'}]}},
                    'filters': [], 'query': {'esql': q}, 'needsRefresh': False,
                    'visualization': {
                        'layerId': layer, 'layerType': 'data', 'metricAccessor': 'metric_val',
                        'subtitle': 'Open ServiceNow incidents · selected CI (all CIs if none)',
                        'titleWeight': 'bold', 'valueFontMode': 'default', 'applyColorTo': 'value',
                        'palette': {'name': 'custom', 'type': 'palette', 'params': {
                            'name': 'custom', 'reverse': False, 'steps': 2, 'maxSteps': 5, 'rangeType': 'number',
                            'rangeMin': 0, 'rangeMax': 2, 'progression': 'fixed', 'continuity': 'all',
                            'stops': [{'color': '#1f9e6b', 'stop': 1}, {'color': colour, 'stop': 2}],
                            'colorStops': stops}}},
                    'adHocDataViews': {DV_ID: {
                        'id': DV_ID, 'title': 'servicenow-incidents-*', 'timeFieldName': '@timestamp',
                        'sourceFilters': [], 'type': 'esql', 'fieldFormats': {}, 'runtimeFieldMap': {},
                        'allowNoIndex': False, 'name': 'servicenow-incidents-*', 'allowHidden': False,
                        'managed': False}}}}}}


panels = []
# ---------------- 1 · Incidents, changes and alerts ----------------
panels += [
    count_tile('Active P1 incidents', 1, '#d6453d', S1, 0, 0, 8, 6),
    count_tile('Active P2 incidents', 2, '#c98a0b', S1, 8, 0, 8, 6),
    copy_panel('User base · ServiceNow', S1, 16, 0, 8, 6, new_title='User impact · ServiceNow'),
    copy_panel('Real users · RUM', S1, 24, 0, 8, 6, new_title='User impact · RUM'),
    placeholder('Elastic infra alerts', S1, 32, 0, 16, 6,
                'Alerts from Elastic\'s own alerting rules: not confirmed on this cluster yet (IQ3 in '
                '*dashboard_queries.md*). Netcool alerts on the CI are in *Alerts on this CI* below.'),
    copy_panel('Escalate', S1, 0, 6, 48, 8, new_title='Incidents on this CI', time_range=WINDOW_30D,
               description='Active P1, P2 and P3 incidents on the CI picked in the CI control (state not Resolved, '
                           'Closed, Canceled or Cancelled), with the CI\'s CMDB class, environment and support '
                           'group, the assignment group, assignee and group manager (with emails). Click the CI or '
                           'the incident to open it in ServiceNow. Incidents opened in the last 30 days (fixed). '
                           'Empty until a CI is picked.'),
    copy_panel('Changes in the Last 7 Days on this CI', S1, 0, 14, 24, 11, new_title='Changes on this CI (last 7 days)'),
    copy_panel('Alerts on this CI', S1, 24, 14, 24, 11, new_title='Alerts on this CI (Netcool)',
               time_range={'from': 'now-7d', 'to': 'now'},
               description='Netcool alerts on the CI picked in the CI control (matched on the CMDB CI, or on the node '
                           '"<CI>.cna.com"), last 7 days, one row per alert: its state now (Open, or Cleared once its '
                           'latest record is a clear / resolution), severity, text, first and last seen, and how many '
                           'times Netcool has seen it fire (a high number means a recurring or flapping problem).'),
]
# ---------------- 2 · Infrastructure overview ----------------
panels += [
    copy_panel('Server', S2, 0, 0, 24, 3),
    copy_panel('Health window', S2, 24, 0, 24, 3),
    copy_panel('Server Health', S2, 0, 3, 16, 10),
    copy_panel('Database Health', S2, 16, 3, 16, 10),
    copy_panel('Middleware Health', S2, 32, 3, 16, 10),
    copy_panel('Process Health', S2, 0, 13, 16, 10),
    placeholder('VMware health', S2, 16, 13, 16, 10,
                'vSphere metrics are collected (`metrics-vsphere.*`, 7 data streams), but under the collector\'s '
                '`host.name`, so a VM or ESXi host has to be found by its own name field. The field names and how '
                'they match CMDB CIs are being confirmed (query IQ1 in *dashboard_queries.md*).'),
    placeholder('Cloud health', S2, 32, 13, 16, 10,
                'GCP metrics are collected (`metrics-gcp.*`, 4 data streams, including CloudSQL and GKE), but '
                'they are not linked to CMDB CIs. CloudSQL already has its own detail dashboard. The datasets, their '
                'resource fields and the link to CIs are being confirmed (query IQ2 in *dashboard_queries.md*).'),
    placeholder('Custom integration health', S2, 0, 23, 48, 5,
                'To be defined: which custom integrations count (for example the ServiceNow, Netcool bridge and CMDB '
                'relation feeds) and what "healthy" means for each (data arrived within N minutes?). Query IQ4 in '
                '*dashboard_queries.md* shows when each feed last delivered data.'),
]
# ---------------- 3 · Applications overview ----------------
panels += [
    copy_panel('Application', S3, 0, 0, 24, 3),
    copy_panel('Service', S3, 24, 0, 24, 3),
    copy_panel('Applications related to this CI', S3, 0, 3, 22, 12),
    copy_panel('Application Health', S3, 22, 3, 26, 12),
    copy_panel('Services of the Application', S3, 0, 15, 26, 12),
    copy_panel('Service health', S3, 26, 15, 22, 12),
]

s = json.dumps(panels, ensure_ascii=False)
assert '?incident' not in s
ids = [p['panelIndex'] for p in panels]
assert len(ids) == len(set(ids))

ci_ctrl = {k: v for k, v in MA['pinned_panels']['panels'].items() if v['config'].get('variable_name') == 'ci'}
assert len(ci_ctrl) == 1
(ci_key, ci_val), = ci_ctrl.items()
ci_val = copy.deepcopy(ci_val)
ci_val['order'] = 0

dash = {
    'type': 'dashboard', 'id': DASH_ID, 'managed': False, 'references': [],
    'coreMigrationVersion': mim.get('coreMigrationVersion'), 'typeMigrationVersion': mim.get('typeMigrationVersion'),
    'attributes': {
        'title': 'Infrastructure Dashboard',
        'description': ('Infrastructure dashboard driven by the CI control: incidents, changes and alerts on the CI; '
                        'its server, database, middleware and process health; the applications related to it and '
                        'their health. KPIs not available yet are shown as placeholder cards that say why '
                        '(dashboard_kpis.txt, INFRA-DASHBOARD-KPIS.xlsx).'),
        'esqlApproximation': False,
        'kibanaSavedObjectMeta': MA['kibanaSavedObjectMeta'],
        'optionsJSON': MA['optionsJSON'],
        'refreshInterval': MA['refreshInterval'],
        'timeRestore': True, 'timeFrom': 'now-24h', 'timeTo': 'now',
        'pinned_panels': {'panels': {uid('control/ci'): ci_val}},
        'sections': [
            {'collapsed': False, 'gridData': {'i': S1, 'y': 0}, 'title': '1 · Incidents, changes and alerts'},
            {'collapsed': False, 'gridData': {'i': S2, 'y': 1}, 'title': '2 · Infrastructure overview (including cloud)'},
            {'collapsed': False, 'gridData': {'i': S3, 'y': 2}, 'title': '3 · Applications overview'},
        ],
        'panelsJSON': s,
    },
}
for k in ('coreMigrationVersion', 'typeMigrationVersion'):
    if dash[k] is None:
        del dash[k]
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: {len(panels)} panels, id {DASH_ID}')
