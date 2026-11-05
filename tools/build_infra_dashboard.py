"""Build the CI-driven Infrastructure Dashboard from MIM V3's panels (28 Oct 2026, dashboard_kpis.txt).

Usage: build_infra_dashboard.py "MIM V4.ndjson" "Infrastructure Dashboard.ndjson" ["MIM V5.ndjson"]   (MIM V3 until 3 Nov)

Control inputs: the Incident, CI and Monitored application controls (pinned, the same as MIM's). Sections:
  1 · Incidents, changes and alerts      2 · Infrastructure overview (incl. cloud)      3 · Applications overview
Achieved KPIs reuse MIM V3's tested panels; KPIs not achievable yet are placeholder cards that say why.
Since 5 Nov the dashboard has MIM's Incident control too, with MIM's logic: a picked incident selects its CI and
wins over the CI control. The panels copied from MIM keep their incident logic; the panels written here read the CI
through CI_EXPR. Until 5 Nov `?incident` was replaced by its "(all incidents)" default (no_incident, now unused).
"""
import copy
import json
import re
import sys
import uuid

SRC, OUT = sys.argv[1:3]
SRC5 = sys.argv[3] if len(sys.argv) > 3 else 'MIM V5.ndjson'
# MIM's rule (5 Nov): the incident's CI if an incident is picked, otherwise the CI control
CI_EXPR = '(CASE(?incident == "(all incidents)", ?ci, SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)))'
NS = 'infra-dashboard/ci-driven-v1/'
uid = lambda name: str(uuid.uuid5(uuid.NAMESPACE_URL, NS + name))
DASH_ID = uid('dashboard')
S1, S2, S3, S4 = uid('section-1'), uid('section-2'), uid('section-3'), uid('section-4')
WINDOW_30D = {'from': 'now-30d', 'to': 'now'}

mim = next(o for o in (json.loads(l) for l in open(SRC) if l.strip()) if o.get('type') == 'dashboard')
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


FROM_MIM = set()


def active_incidents_panel(section, x, y, w, h):
    """5 Nov: MIM V5's Active Incidents table, for active P1 and P2 incidents, following the Incident / CI controls."""
    mim5 = next(o for o in (json.loads(l) for l in open(SRC5) if l.strip()) if o.get('type') == 'dashboard')
    src = next(p for p in json.loads(mim5['attributes']['panelsJSON'])
               if (p['embeddableConfig'].get('title') or '').startswith('Active Incidents'))
    p = copy.deepcopy(src)
    name = 'Active P1 and P2 incidents'
    pid = uid('panel/' + name)
    p['panelIndex'] = pid
    p['gridData'] = {'x': x, 'y': y, 'w': w, 'h': h, 'i': pid, 'sectionId': section}
    ec = p['embeddableConfig']
    ec['title'] = name
    ec['time_range'] = dict(WINDOW_30D)
    st = ec['attributes']['state']
    q = st['query']['esql']
    for a, b in (('TO_INTEGER(priority) IN (1, 2, 3)', 'TO_INTEGER(priority) IN (1, 2)'),
                 ('| WHERE src == "inc"\n', '| WHERE src == "inc"\n| WHERE ?ci == "(no CI selected)" OR TO_STRING(ci.name) == ?ci\n'),
                 ('| WHERE priority == 1 OR age_minutes > target\n', '')):
        assert q.count(a) == 1, a
        q = q.replace(a, b)
    st['query']['esql'] = q
    for layer in st.get('datasourceStates', {}).get('textBased', {}).get('layers', {}).values():
        if 'query' in layer:
            layer['query']['esql'] = q
    ec['attributes']['title'] = name
    ec['description'] = ('Every active P1 and P2 incident (priority 1 or 2, state not On Hold, Resolved, Closed, Canceled '
                         'or Cancelled), the same table as MIM\'s Active Incidents: CI, state, when opened, SLA, '
                         'assignment group, assignee and group manager (with emails), description. With an incident '
                         'picked: the incidents on that incident\'s CI; with a CI picked: that CI\'s. Click the incident '
                         'or the CI to open it in ServiceNow. Incidents updated in the last 30 days, like the P1 and P2 '
                         'tiles above.')
    return p


def copy_panel(name, section, x, y, w, h, new_title=None, description=None, time_range=None):
    p = copy.deepcopy(MP[name])   # keeps MIM's incident logic (5 Nov)
    FROM_MIM.add(uid('panel/' + (new_title or name)))
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
ACTIVE = 'TO_STRING(state_name) NOT IN ("On Hold", "Resolved", "Closed", "Canceled", "Cancelled")'   # On Hold out since 5 Nov, as in MIM


def count_tile(name, pri, colour, section, x, y, w, h, icon='alert', q=None, subtitle=None, description=None):
    q = q or ('FROM servicenow-incidents-*\n'
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
            'description': description or (f'Open P{pri} incidents (priority {pri}, state not Resolved, Closed, Canceled or Cancelled) '
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
                        'subtitle': subtitle or 'Open ServiceNow incidents · selected CI (all CIs if none)',
                        'icon': icon, 'iconAlign': 'left',
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


ELASTIC_ALERTS_Q = """FROM .alerts-observability.*
| WHERE @timestamp >= NOW() - 7 days
| EVAL parts = SPLIT(REPLACE(TO_LOWER(TO_STRING(kibana.alert.instance.id)), "#", ","), ",")
| EVAL inst = CONCAT(",", MV_CONCAT(parts, ","), ",")
| WHERE (?ci == "(no CI selected)" AND TO_STRING(kibana.alert.status) == "active" AND TO_STRING(kibana.alert.rule.name) LIKE "paladin*")
     OR (?ci != "(no CI selected)" AND LOCATE(inst, CONCAT(",", TO_LOWER(?ci), ",")) > 0)
| EVAL head = MV_FIRST(parts)
| EVAL server = CASE(MV_COUNT(parts) > 1 AND LENGTH(head) == 32, MV_FIRST(MV_SLICE(parts, 1, 1)), head),
       state = CASE(TO_STRING(kibana.alert.status) == "active", "Active", "Recovered"),
       severity = COALESCE(TO_STRING(kibana.alert.severity), "—"), rule = TO_STRING(kibana.alert.rule.name),
       reason = TO_STRING(kibana.alert.reason), started = TO_DATETIME(kibana.alert.start), last_seen = @timestamp
| SORT state ASC, started DESC
| LIMIT 200
| KEEP state, severity, server, rule, reason, started, last_seen"""


def elastic_alerts_panel(section, x, y, w, h):
    """Elastic Observability alerts (the paladin-* infrastructure rules and any other rule) on the selected CI."""
    name = 'Elastic infra alerts'
    p = copy_panel('Alerts on this CI', section, x, y, w, h, new_title=name, time_range={'from': 'now-7d', 'to': 'now'},
                   description=('Alerts raised by Elastic\'s own alerting rules (Observability: the paladin-* '
                                'infrastructure rules for host uptime and availability, filesystem, CPU and memory, '
                                'processes, Windows services, IBM MQ, plus any other rule) on the CI picked in the CI '
                                'control, last 7 days, active first. Matched on the CI name inside the alert\'s instance '
                                'id (the rules group by CMDB CI). With no CI picked: every active paladin-* alert. '
                                'Netcool alerts are in Alerts on this CI (Netcool). Reads .alerts-observability.*, '
                                'which needs read access to the alert indices.'))
    st = p['embeddableConfig']['attributes']['state']
    (lid, layer), = st['datasourceStates']['textBased']['layers'].items()
    dv = uid('dataview/alerts-observability')
    S, D = {'type': 'string', 'esType': 'keyword'}, {'type': 'date', 'esType': 'date'}
    cols = [('state', 'Now', S), ('severity', 'Severity', S), ('server', 'Server', S), ('rule', 'Rule', S),
            ('reason', 'Reason', S), ('started', 'Started', D), ('last_seen', 'Last seen', D)]
    layer['columns'] = [{'columnId': c, 'fieldName': c, 'label': l, 'customLabel': True, 'meta': m, 'inMetricDimension': True}
                        for c, l, m in cols]
    layer.pop('allColumns', None)
    layer['index'] = dv
    layer['query'] = {'esql': ELASTIC_ALERTS_Q}
    st['query'] = {'esql': ELASTIC_ALERTS_Q}
    title = '.alerts-observability.*'
    st['datasourceStates']['textBased']['indexPatternRefs'] = [{'id': dv, 'title': title, 'timeField': '@timestamp'}]
    st['adHocDataViews'] = {dv: {'id': dv, 'title': title, 'timeFieldName': '@timestamp', 'sourceFilters': [], 'type': 'esql',
                                 'fieldFormats': {}, 'runtimeFieldMap': {}, 'allowNoIndex': False, 'name': title,
                                 'allowHidden': True, 'managed': False}}
    badge = lambda pairs: {'colorMode': 'badge', 'palette': {'type': 'palette', 'name': 'default'}, 'colorMapping': {
        'paletteId': 'default', 'colorMode': {'type': 'categorical'},
        'assignments': [{'rules': [{'type': 'match', 'pattern': k, 'matchEntireWord': True, 'matchCase': True}],
                         'color': {'type': 'colorCode', 'colorCode': v}, 'touched': True} for k, v in pairs],
        'specialAssignments': [{'rules': [{'type': 'other'}], 'color': {'type': 'colorCode', 'colorCode': '#8a96a8'}, 'touched': True}]}}
    vis = {'state': dict(badge([('Active', '#d6453d'), ('Recovered', '#1f9e6b')]), width=95, alignment='center'),
           'severity': dict(badge([('critical', '#d6453d'), ('major', '#d95926'), ('high', '#d95926'), ('medium', '#c98a0b'),
                                   ('warning', '#c98a0b'), ('minor', '#c98a0b'), ('low', '#6f87a6')]), width=85, alignment='center'),
           'server': {'width': 130}, 'rule': {'width': 230}, 'reason': {'width': 520}, 'started': {'width': 150},
           'last_seen': {'width': 150}}
    st['visualization']['columns'] = [dict({'columnId': c, 'isTransposed': False, 'isMetric': c not in ('server', 'rule')}, **vis[c])
                                      for c, _, _ in cols]
    return p


K8S = '"cmdb_ci_kubernetes_cluster"'
WINDOW = ('TO_TIMEDURATION(CASE(?health_window == "3 days", "72 hours", ?health_window == "7 days", "168 hours", '
          '?health_window))')
GKE_HEALTH_Q = f"""FROM metrics-gcp.gke-*, cmdb-ci-relations* METADATA _index
| WHERE (NOT _index LIKE "*cmdb-ci-relations*" AND @timestamp >= NOW() - {WINDOW}
         AND (gcp.gke.node.cpu.allocatable_utilization.pct IS NOT NULL OR gcp.gke.node.memory.allocatable_utilization.pct IS NOT NULL
              OR gcp.gke.node.memory.used.bytes IS NOT NULL OR gcp.gke.container.restart.count IS NOT NULL))
     OR (_index LIKE "*cmdb-ci-relations*" AND ?ci != "(no CI selected)"
         AND (parent.name IN (?ci, TO_UPPER(?ci), TO_LOWER(?ci)) OR child.name IN (?ci, TO_UPPER(?ci), TO_LOWER(?ci)))
         AND (TO_STRING(parent.class) == {K8S} OR TO_STRING(child.class) == {K8S})
         AND COALESCE(TO_LOWER(TO_STRING(is_marked_for_deletion)), "false") != "true")
| EVAL is_rel = _index LIKE "*cmdb-ci-relations*", ci_l = TO_LOWER(?ci),
       p_l = TO_LOWER(TO_STRING(parent.name)), c_l = TO_LOWER(TO_STRING(child.name)),
       cpu = TO_DOUBLE(gcp.gke.node.cpu.allocatable_utilization.pct), mem = TO_DOUBLE(gcp.gke.node.memory.allocatable_utilization.pct),
       mu = CASE(TO_STRING(gcp.labels.metrics.memory_type) == "evictable", null, TO_DOUBLE(gcp.gke.node.memory.used.bytes)),
       ma = TO_DOUBLE(gcp.gke.node.memory.allocatable.bytes),
       rc = TO_DOUBLE(gcp.gke.container.restart.count)
| EVAL cluster = CASE(is_rel, CASE(TO_STRING(child.class) == {K8S} AND (c_l != ci_l OR TO_STRING(parent.class) != {K8S}), c_l, p_l),
                      TO_LOWER(TO_STRING(gcp.labels.resource.cluster_name))),
       ent = CASE(is_rel, "", rc IS NOT NULL, CONCAT("c:", COALESCE(TO_STRING(gcp.labels_fingerprint), "")), COALESCE(TO_STRING(gcp.labels.resource.node_name), "")),
       project = CASE(is_rel, "", COALESCE(TO_STRING(cloud.account.id), ""))
| STATS rel = MAX(CASE(is_rel, 1, 0)), cpu_avg_e = AVG(cpu), cpu_p90_e = PERCENTILE(cpu, 90), mem_u = MAX(mem), mem_used = MAX(mu), mem_alloc = MAX(ma),
        r_max = MAX(rc), r_min = MIN(rc), last_e = MAX(CASE(NOT is_rel, @timestamp))
  BY cluster, ent, project
| EVAL restarts_e = r_max - r_min, mem_e = COALESCE(mem_u, mem_used / mem_alloc), project = CASE(project == "", null, project)
| STATS related = MAX(rel), nodes = COUNT(cpu_p90_e), cpu_a = AVG(cpu_avg_e), cpu_p = MAX(cpu_p90_e), mem_p = MAX(mem_e),
        restarts = SUM(restarts_e), last_seen = MAX(last_e), projects = VALUES(project)
  BY cluster
| WHERE COALESCE(cluster, "") != "" AND (?ci == "(no CI selected)" OR related == 1 OR cluster == TO_LOWER(?ci))
| EVAL scale = CASE(COALESCE(cpu_p, 0) <= 2 AND COALESCE(mem_p, 0) <= 2, 100.0, 1.0)
| EVAL cpu_avg = ROUND(cpu_a * scale, 1), cpu_p90 = ROUND(cpu_p * scale, 1), mem_peak = ROUND(mem_p * scale, 1),
       restarts = CASE(last_seen IS NULL, null, COALESCE(TO_LONG(restarts), TO_LONG(0))), silent_min = DATE_DIFF("minutes", last_seen, NOW()),
       project = COALESCE(MV_FIRST(projects), "—")
| EVAL status = CASE(last_seen IS NULL, "Not collected", silent_min > 20, "Silent",
                     cpu_p90 >= 90 OR mem_peak >= 90, "Critical",
                     cpu_p90 >= 80 OR mem_peak >= 80 OR restarts >= 10, "Warning", "Healthy"),
       rank = CASE(status == "Critical", 1, status == "Silent", 2, status == "Warning", 3, status == "Not collected", 4, 5)
| SORT rank ASC, cluster ASC
| LIMIT 100
| KEEP cluster, status, project, nodes, cpu_avg, cpu_p90, mem_peak, restarts, silent_min"""


def gke_health_panel(section, x, y, w, h):
    """Cloud health, GKE part: one row per GKE cluster, matched to the CI control by the CMDB cluster name (Round 17d)."""
    name = 'Cloud health · GKE'
    p = copy_panel('Server Health', section, x, y, w, h, new_title=name, description=(
        'GKE (Google Kubernetes Engine) clusters, one row per cluster, problems first. Status: Critical (CPU or memory '
        'from 90 %), Warning (from 80 %, or 10+ container restarts), Silent (no data for 20 minutes; GCP metrics arrive '
        'every 5 minutes with about 5 minutes\' lag), Healthy; Not collected = a cluster in the CMDB that the GCP '
        'integration does not collect. Nodes = nodes reporting; CPU avg / p90 = node CPU use of allocatable cores '
        '(p90 of the busiest node); Mem peak = the fullest node\'s memory use of allocatable memory (non-evictable used bytes / allocatable bytes: memory in use that Kubernetes cannot reclaim; evictable cache is left out, CG7); Restarts = container '
        'restarts in the window. Which clusters: the CI control\'s value if it is a cluster, plus every Kubernetes '
        'cluster linked to it in the CMDB; with no CI picked, every collected cluster. GCP metrics carry no CMDB fields, '
        'so clusters are matched on name (4 of the 5 collected clusters are CMDB CIs). CloudSQL and Storage are not '
        'shown: their names do not match the CMDB, and Storage has no health signal. Data window: the Health window '
        'control. Reads metrics-gcp.gke-* and cmdb-ci-relations*.'))
    st = p['embeddableConfig']['attributes']['state']
    (lid, layer), = st['datasourceStates']['textBased']['layers'].items()
    dv = uid('dataview/gcp-gke')
    S, N = {'type': 'string', 'esType': 'keyword'}, {'type': 'number', 'esType': 'double'}
    L = {'type': 'number', 'esType': 'long'}
    cols = [('cluster', 'Cluster', S), ('status', 'Status', S), ('project', 'GCP project', S), ('nodes', 'Nodes', L),
            ('cpu_avg', 'CPU avg %', N), ('cpu_p90', 'CPU p90 %', N), ('mem_peak', 'Mem peak %', N),
            ('restarts', 'Restarts', L), ('silent_min', 'Min. ago', L)]
    layer['columns'] = [{'columnId': c, 'fieldName': c, 'label': l, 'customLabel': True, 'meta': m, 'inMetricDimension': True}
                        for c, l, m in cols]
    layer.pop('allColumns', None)
    layer['index'] = dv
    layer['query'] = {'esql': GKE_HEALTH_Q}
    st['query'] = {'esql': GKE_HEALTH_Q}
    title = 'metrics-gcp.gke-*,cmdb-ci-relations*'
    st['datasourceStates']['textBased']['indexPatternRefs'] = [{'id': dv, 'title': title, 'timeField': '@timestamp'}]
    st['adHocDataViews'] = {dv: {'id': dv, 'title': title, 'timeFieldName': '@timestamp', 'sourceFilters': [], 'type': 'esql',
                                 'fieldFormats': {}, 'runtimeFieldMap': {}, 'allowNoIndex': False, 'name': title,
                                 'allowHidden': False, 'managed': False}}
    old = {c['columnId']: c for c in st['visualization']['columns']}
    pct = old['cpu_p90']   # Server Health's amber-80 / red-90 text colouring
    status = copy.deepcopy(old['status'])
    status['colorMapping']['assignments'] = [
        {'rules': [{'type': 'match', 'pattern': k, 'matchEntireWord': True, 'matchCase': True}],
         'color': {'type': 'colorCode', 'colorCode': v}, 'touched': True}
        for k, v in (('Critical', '#d6453d'), ('Silent', '#d6453d'), ('Warning', '#c98a0b'), ('Healthy', '#1f9e6b'),
                     ('Not collected', '#8a96a8'))]
    status['width'] = 100
    vis = {'cluster': {'alignment': 'left', 'width': 190}, 'status': status, 'project': {'alignment': 'left', 'width': 250},
           'nodes': {'alignment': 'right', 'width': 55}, 'cpu_avg': dict(copy.deepcopy(pct), width=65),
           'cpu_p90': dict(copy.deepcopy(pct), width=65), 'mem_peak': dict(copy.deepcopy(pct), width=70),
           'restarts': {'alignment': 'right', 'width': 65}, 'silent_min': {'alignment': 'right', 'width': 60}}
    st['visualization']['columns'] = [dict(vis[c], columnId=c, isTransposed=False, isMetric=c not in ('cluster', 'project'))
                                      for c, _, _ in cols]
    return p


panels = []
# ---------------- 1 · Incidents, changes and alerts ----------------
panels += [
    count_tile('Active P1 incidents', 1, '#d6453d', S1, 0, 0, 10, 6),
    count_tile('Active P2 incidents', 2, '#c98a0b', S1, 10, 0, 10, 6),
    count_tile('Active Elastic infra alerts', 0, '#d6453d', S1, 20, 0, 10, 6, icon='bell',
               q=ELASTIC_ALERTS_Q[:ELASTIC_ALERTS_Q.index('| EVAL head')]
               + '| STATS metric_val = COUNT_DISTINCT(CASE(TO_STRING(kibana.alert.status) == "active", TO_STRING(kibana.alert.instance.id)))',
               subtitle='Elastic alerts active now · selected CI (every paladin alert if none)',
               description='Active alerts from Elastic\'s alerting rules on the CI picked in the CI control, last 7 days; '
                           'with no CI, every active paladin-* infrastructure alert. Green at 0. The same alerts as the '
                           'Elastic infra alerts table (state Active).'),
    copy_panel('User base · ServiceNow', S1, 30, 0, 9, 6, new_title='User impact · ServiceNow'),
    copy_panel('Real users · RUM', S1, 39, 0, 9, 6, new_title='User impact · RUM'),
    active_incidents_panel(S1, 0, 6, 48, 8),
    copy_panel('Changes in the Last 7 Days on this CI', S1, 0, 14, 24, 11, new_title='Changes on this CI (last 7 days)'),
    copy_panel('Alerts on this CI', S1, 24, 14, 24, 11, new_title='Alerts on this CI (Netcool)',
               time_range={'from': 'now-7d', 'to': 'now'},
               description='Netcool alerts on the CI picked in the CI control (matched on the CMDB CI, or on the node '
                           '"<CI>.cna.com"), last 7 days, one row per alert: its state now (Open, or Cleared once its '
                           'latest record is a clear / resolution), severity, text, first and last seen, and how many '
                           'times Netcool has seen it fire (a high number means a recurring or flapping problem).'),
    elastic_alerts_panel(S1, 0, 25, 48, 10),
]
# ---------------- 2 · Infrastructure overview ----------------
panels += [
    copy_panel('Server', S2, 0, 0, 24, 3),
    copy_panel('Health window', S2, 24, 0, 24, 3),
    copy_panel('Server Health', S2, 0, 3, 16, 10),
    copy_panel('Database Health', S2, 16, 3, 16, 10),
    copy_panel('Middleware Health', S2, 32, 3, 16, 10),
    copy_panel('Process Health', S2, 0, 13, 16, 10),
    gke_health_panel(S2, 16, 13, 32, 10),
    placeholder('VMware health', S2, 0, 23, 24, 6,
                'vSphere collects one VMware Cloud Foundation cluster only (4 ESXi hosts, 46 VMs, against 549 ESX '
                'hosts in the CMDB), with no CMDB fields; only one of its VMs matches a monitored server (Round 17). '
                'It needs the vSphere integration extended to the main vCenters. Meanwhile: the VMware Infra Dashboard (section 4).'),
    placeholder('Custom integration health', S2, 24, 23, 24, 6,
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

# ---------------- controls made hard to miss (4 Nov): icons in their titles, "Start here" banners ----------------
ICONS = {'incident': '🚨 Incident', 'ci': '🖥️ CI', 'monitored_app': '🧩 Monitored application', 'server': '🖥️ Server',
         'health_window': '⏱️ Health window', 'application': '🧩 Application', 'service': '⚙️ Service'}


def banner(name, step, headline, detail, section, colour='#0b64dd'):
    """A coloured how-to strip (Vega, so it can have colour and bold text; no data)."""
    def txt(y, value, size, weight, fill=None, style=None):
        enc = {'x': {'value': 54}, 'y': {'signal': y}, 'text': {'value': value}, 'baseline': {'value': 'middle'},
               'fontSize': {'value': size}, 'fontWeight': {'value': weight}, 'limit': {'signal': 'width - 70'}}
        if fill:
            enc['fill'] = {'value': fill}
        m = {'type': 'text', 'encode': {'update': enc}}
        if style:
            m['style'] = style
        return m
    spec = {'$schema': 'https://vega.github.io/schema/vega/v5.json', 'autosize': {'type': 'fit', 'contains': 'padding'},
            'padding': 0, 'marks': [
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
                txt('height / 2 - 8', headline, 15, 'bold', fill=colour),
                txt('height / 2 + 11', detail, 12, 'normal', style='guide-label')]}
    pid = uid('banner/' + name)
    return {'type': 'legacy_vis', 'panelIndex': pid, 'gridData': {'x': 0, 'y': 0, 'w': 48, 'h': 3, 'i': pid, 'sectionId': section},
            'embeddableConfig': {'title': name, 'hide_title': True, 'description': 'How to use the controls. Not data.',
                                 'savedVis': {'title': name, 'description': '', 'type': 'vega',
                                              'params': {'spec': json.dumps(spec, indent=2)}, 'uiState': {},
                                              'data': {'aggs': [], 'searchSource': {}}}}}


for p in panels:
    if p['type'] == 'esql_control':
        p['embeddableConfig']['title'] = ICONS[p['embeddableConfig']['variable_name']]
    p['gridData']['y'] += 3
panels += [
    banner('Start here', '1', '▲  Start here: pick an incident or a CI in the controls at the top',
           'An incident selects its CI. Every section follows it; with neither, the whole estate. More (⋯) → Reset changes clears every pick.', S1),
    banner('Pick a server', '2', '▼  If the CI is not a server, pick one of its servers',
           'A server CI fills these panels by itself. Health window: how far back they look.', S2),
    banner('Pick an application and a service', '3', '▼  Pick an Application, then a Service',
           'Application: Services of the Application · Service: Service health', S3),
]

# ---------------- the new look (5 Nov), as in MIM V5: row numbers, section icons, detailed-dashboard links ----------------
for p in panels:
    if p['type'] == 'vis' and p['embeddableConfig'].get('attributes', {}).get('visualizationType') == 'lnsDatatable' \
            and p['embeddableConfig'].get('title') in ('Active P1 and P2 incidents', 'Changes on this CI (last 7 days)',
                                                       'Alerts on this CI (Netcool)', 'Elastic infra alerts',
                                                       'Applications related to this CI', 'Application Health',
                                                       'Services of the Application'):
        p['embeddableConfig']['attributes']['state']['visualization']['showRowNumbers'] = True

DETAILED = [   # respective_detailed_dashboards.txt (5 Nov)
    ('Server', '🖥️', 'Server Infra Dashboard', 'https://kibana-prod.gcp.cna.com/app/r/s/qJk5u'),
    ('Database', '🗄️', 'Database Infra Dashboard', 'https://kibana-prod.gcp.cna.com/app/r/s/w6zL4'),
    ('Middleware', '⚙️', 'Middleware Dashboard', 'https://kibana-prod.gcp.cna.com/app/r/s/jwCRg'),
    ('VMware', '🧱', 'VMware Infra Dashboard', 'https://kibana-prod.gcp.cna.com/app/r/s/t4oxr'),
    ('Cloud', '☁️', 'Cloud Infra Dashboard', 'https://kibana-prod.gcp.cna.com/app/r/s/MDJ9f'),
]
for i, (domain, icon, name, url) in enumerate(DETAILED):
    pid = uid('link/' + domain)
    # one row, as the team arranged it in infra2.ndjson (5 Nov): Server, Database, Cloud, Middleware, VMware
    x, w = {'Server': (0, 9), 'Database': (9, 9), 'Cloud': (18, 9), 'Middleware': (27, 9), 'VMware': (36, 10)}[domain]
    y = 0
    panels.append({'type': 'markdown', 'panelIndex': pid,
                   'gridData': {'x': x, 'y': y, 'w': w, 'h': 2, 'i': pid, 'sectionId': S4},
                   'embeddableConfig': {'title': f'{domain} detailed dashboard', 'hide_title': True,
                                        'content': f'## {icon} [{name} ›]({url})',
                                        'settings': {'open_links_in_new_tab': True}}})

# panels written here read the CI through MIM's incident rule (copied MIM panels already do)
for p in panels:
    if p['panelIndex'] not in FROM_MIM and p['type'] != 'esql_control':
        p['embeddableConfig'] = json.loads(re.sub(r'\?ci\b', lambda m: CI_EXPR.replace('"', '\\"'),
                                                  json.dumps(p['embeddableConfig'], ensure_ascii=False)))
s = json.dumps(panels, ensure_ascii=False)
assert '?telemetry' not in s
ids = [p['panelIndex'] for p in panels]
assert len(ids) == len(set(ids))

ci_ctrl = {k: v for k, v in MA['pinned_panels']['panels'].items() if v['config'].get('variable_name') == 'ci'}
assert len(ci_ctrl) == 1
(ci_key, ci_val), = ci_ctrl.items()
ci_val = copy.deepcopy(ci_val)
ci_val['order'] = 1
inc = [v for v in MA['pinned_panels']['panels'].values() if v['config'].get('variable_name') == 'incident']
assert len(inc) == 1
inc_val = copy.deepcopy(inc[0])
inc_val['order'] = 0
mon = [v for v in MA['pinned_panels']['panels'].values() if v['config'].get('variable_name') == 'monitored_app']
assert len(mon) == 1, 'build from MIM V4 (patch 03w)'
mon_val = copy.deepcopy(mon[0])
mon_val['order'] = 2
for v, var in ((inc_val, 'incident'), (ci_val, 'ci'), (mon_val, 'monitored_app')):   # 4 Nov: icon titles, full width
    v['config']['title'] = ICONS[var]
    v['grow'] = True

dash = {
    'type': 'dashboard', 'id': DASH_ID, 'managed': False, 'references': [],
    'coreMigrationVersion': mim.get('coreMigrationVersion'), 'typeMigrationVersion': mim.get('typeMigrationVersion'),
    'attributes': {
        'title': 'Infrastructure Dashboard',
        'description': ('Infrastructure dashboard driven by the Incident and CI controls (an incident selects its CI): incidents, changes and alerts on the CI; '
                        'its server, database, middleware and process health; the applications related to it and '
                        'their health. KPIs not available yet are shown as placeholder cards that say why '
                        '(dashboard_kpis.txt, INFRA-DASHBOARD-KPIS.xlsx).'),
        'esqlApproximation': False,
        'kibanaSavedObjectMeta': MA['kibanaSavedObjectMeta'],
        'optionsJSON': MA['optionsJSON'],
        'refreshInterval': MA['refreshInterval'],
        'timeRestore': True, 'timeFrom': 'now-24h', 'timeTo': 'now',
        'pinned_panels': {'panels': {uid('control/incident'): inc_val, uid('control/ci'): ci_val, uid('control/monitored_app'): mon_val}},
        'sections': [
            {'collapsed': True, 'gridData': {'i': S1, 'y': 0}, 'title': '🚨 1 · Incidents, changes and alerts'},
            {'collapsed': True, 'gridData': {'i': S2, 'y': 1}, 'title': '🖥️ 2 · Infrastructure overview (including cloud)'},
            {'collapsed': True, 'gridData': {'i': S3, 'y': 2}, 'title': '🩺 3 · Applications overview'},
            {'collapsed': False, 'gridData': {'i': S4, 'y': 3}, 'title': '🔗 4 · Detailed dashboards'},
        ],
        'panelsJSON': s,
    },
}
for k in ('coreMigrationVersion', 'typeMigrationVersion'):
    if dash[k] is None:
        del dash[k]
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: {len(panels)} panels, id {DASH_ID}')
