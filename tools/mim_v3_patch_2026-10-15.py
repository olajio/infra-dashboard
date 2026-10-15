"""Fix the colleague's "related CIs by type" section and add application health (15 Oct 2026).

Starts from the colleague's export ("updated mim dashboard.ndjson": MIM V3 + four CMDB views in a new section) and
writes the dashboard object only.

Usage: mim_v3_patch_2026-10-15.py "updated mim dashboard.ndjson" "MIM V3.ndjson"

What it does (see MIM-V3-REVIEW-UPDATED-DASHBOARD.md for the bugs):
- the four views (Middleware, Database, Server, Application) follow the Incident / CI controls, cover both
  directions of a relationship, match the exact ServiceNow classes from round 10 (AU / AV) and show the relationship
  and CMDB status; the extra filter control and its data view are removed;
- the default time range goes back to the last 24 hours, every section opens expanded, and the new section is named
  and placed after section 2 (sections renumbered 1-5);
- a new Application control and two panels rate each business application by the health of its APM services and
  list the services of the picked application (round 10: AX, AY, AZ).
"""
import copy
import json
import sys
import uuid

SRC, OUT = sys.argv[1:3]
RED, AMBER, GREEN, GREY = '#d6453d', '#c98a0b', '#1f9e6b', '#8a96a8'
NS = uuid.UUID('6f1c1d1e-2b1c-4c1a-9a51-6d1f0c1e1a15')
uid = lambda name: str(uuid.uuid5(NS, name))
SEL_CI = '(CASE(?incident == "(all incidents)", ?ci, SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)))'
PROD = '("prd1", "prd2", "prd", "prod", "production")'
ALL_APPS = '(all applications)'
MIN_TX = 20      # a service needs this many transactions in the hour before its error rate can make it Failing / Degraded

objs = [json.loads(l) for l in open(SRC) if l.strip()]
dash = next(o for o in objs if o.get('type') == 'dashboard')
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = lambda t: next(p for p in panels if title(p) == t)
st = lambda p: p['embeddableConfig']['attributes']['state']
layer = lambda p: next(iter(st(p)['datasourceStates']['textBased']['layers'].values()))
query = lambda p: layer(p)['query']['esql']
SECTIONS = {s['title']: s for s in A['sections']}
NEWSEC = SECTIONS['New collapsible section']['gridData']['i']


def col(cid, label, typ='string', es='keyword', fmt=None):
    c = {'columnId': cid, 'fieldName': cid, 'label': label, 'customLabel': True, 'meta': {'type': typ, 'esType': es},
         'inMetricDimension': True}
    if fmt:
        c['params'] = {'format': fmt}
    return c


def exact(pairs, other=GREY):
    rule = lambda v: {'type': 'match', 'pattern': v, 'matchEntireWord': True, 'matchCase': True}
    return {'paletteId': 'default', 'colorMode': {'type': 'categorical'},
            'assignments': [{'rules': [rule(v)], 'color': {'type': 'colorCode', 'colorCode': c}, 'touched': True}
                            for v, c in pairs],
            'specialAssignments': [{'rules': [{'type': 'other'}], 'color': {'type': 'colorCode', 'colorCode': other},
                                    'touched': True}]}


def tcol(cid, width, link=False, align='left', badge=None):
    c = {'columnId': cid, 'isTransposed': False, 'isMetric': not link, 'alignment': align, 'width': width}
    if badge:
        c.update(colorMode='badge', palette={'type': 'palette', 'name': 'default'}, colorMapping=exact(badge))
    return c


def table_panel(template, name, ttl, desc, q, cols, vcols, page=8, index_title=None):
    """A copy of a known-good ES|QL table panel with its own ids, query and columns."""
    p = copy.deepcopy(template)
    ec = p['embeddableConfig']
    ec['title'] = ec['attributes']['title'] = ttl
    ec['description'] = desc
    ec.pop('drilldowns', None)
    ec.pop('time_range', None)
    s = ec['attributes']['state']
    (old_id, L), = s['datasourceStates']['textBased']['layers'].items()
    new_id = uid(name + ':layer')
    s['datasourceStates']['textBased']['layers'] = {new_id: L}
    L['query'] = {'esql': q}
    s['query'] = {'esql': q}
    L['columns'] = cols
    L['allColumns'] = copy.deepcopy(cols)
    if index_title:
        for v in s.get('adHocDataViews', {}).values():
            v['title'] = v['name'] = index_title
    vis = s['visualization']
    vis['layerId'] = new_id
    vis['columns'] = vcols
    vis['paging'] = {'enabled': True, 'size': page}
    vis.pop('sorting', None)
    p['panelIndex'] = uid(name)
    return p


# ------------------------------------------------------------------ the four views: exact classes, both directions
# Classes from round 10 (AU / AV) for the lists in relationships1.png and relatiosnhips2.png, with readable names.
GROUPS = {
    'Middleware': {
        'cmdb_ci_app_server': 'Application Server', 'cmdb_ci_app_server_jboss': 'JBoss',
        'cmdb_ci_app_server_jb_module': 'JBoss module', 'cmdb_ci_app_server_tomcat': 'Tomcat',
        'cmdb_ci_app_server_tomcat_war': 'Tomcat WAR', 'cmdb_ci_app_server_weblogic': 'WebLogic',
        'cmdb_ci_app_server_websphere': 'IBM WebSphere', 'cmdb_ci_app_server_ws_ear': 'WebSphere EAR'},
    'Database': {
        'cmdb_ci_cassandra_instance': 'Cassandra Instance', 'cmdb_ci_cloud_database': 'Cloud DataBase',
        'cmdb_ci_db_db2_instance': 'DB2 Instance', 'cmdb_ci_db_hbase_instance': 'HBase Instance',
        'cmdb_ci_db_instance': 'Database Instance', 'cmdb_ci_db_instance_size': 'DB Instance Size',
        'cmdb_ci_db_mongodb_instance': 'MongoDB Instance', 'cmdb_ci_db_mssql_analysis': 'SQL Server Analysis Services',
        'cmdb_ci_db_mssql_database': 'MS SQL DataBase', 'cmdb_ci_db_mssql_instance': 'MSFT SQL Instance',
        'cmdb_ci_db_mssql_integration': 'SQL Server Integration Services',
        'cmdb_ci_db_mssql_reporting': 'SQL Server Reporting Services', 'cmdb_ci_db_mysql_instance': 'MySQL Instance',
        'cmdb_ci_db_ora_instance': 'Oracle Instance', 'cmdb_ci_db_ora_service': 'Oracle DB Service',
        'cmdb_ci_db_postgresql_instance': 'PostgreSQL Instance', 'cmdb_ci_db_syb_instance': 'Sybase Instance'},
    'Server': {
        'cmdb_ci_aix_server': 'AIX Server', 'cmdb_ci_esx_server': 'ESX Server', 'cmdb_ci_hpux_server': 'HPUX Server',
        'cmdb_ci_hyper_v_server': 'Hyper-V Server', 'cmdb_ci_ibm_frame': 'IBM Frame', 'cmdb_ci_isam_server': 'ISAM Server',
        'cmdb_ci_lb_bigip': 'Load Balancer (F5 BIG-IP)', 'cmdb_ci_lb_netscaler': 'Citrix Netscaler',
        'cmdb_ci_linux_server': 'Linux Server', 'cmdb_ci_mainframe': 'IBM Mainframe',
        'cmdb_ci_mainframe_lpar': 'Mainframe LPAR', 'cmdb_ci_net_app_server': 'Network Appliance Hardware',
        'cmdb_ci_server': 'Server', 'cmdb_ci_solaris_server': 'Solaris Server', 'cmdb_ci_storage_server': 'Storage Server',
        'cmdb_ci_win_server': 'Windows Server'},
    'Application': {'cmdb_ci_business_app': 'Business Application'},
}
template_runs_on = P('What this CI runs on')
q0 = query(template_runs_on)
REL_CASE = q0[q0.index('CASE(r == "60bc4e22'):q0.index(', oper = CASE(')]
OPER_CASE = q0[q0.index('oper = CASE(') + len('oper = '):q0.index('\n', q0.index('oper = CASE('))]
assert REL_CASE.endswith('r)') and OPER_CASE.endswith('"—")')
NOT_RETIRED = lambda side: f'({side}_ci.install_status.keyword IS NULL OR {side}_ci.install_status.keyword != "7")'
DESCRIPTIONS = {
    'Middleware': 'Application servers related to the selected CI in the CMDB: Application Server, JBoss, JBoss module, '
                  'Tomcat, Tomcat WAR, WebLogic, IBM WebSphere, WebSphere EAR.',
    'Database': 'Databases related to the selected CI in the CMDB: Oracle, MS SQL (instances, databases, Analysis / '
                'Integration / Reporting Services), DB2, MySQL, PostgreSQL, Sybase, MongoDB, Cassandra, HBase, cloud '
                'databases.',
    'Server': 'Servers related to the selected CI in the CMDB: Windows, Linux, AIX, HP-UX, Solaris, ESX, Hyper-V, '
              'mainframe and LPARs, IBM frames, storage servers, network appliances, F5 / Netscaler load balancers.',
    'Application': 'Business applications related to the selected CI in the CMDB (application-to-application '
                   'relationships). For their live health see "Application Health" in section 4.',
}
STATUS = [('Non-operational', RED), ('Repair in progress', AMBER), ('Operational', GREEN), ('Ready', GREEN)]
VIEW_LAYOUT = {'Middleware': (0, 0), 'Database': (24, 0), 'Server': (0, 11), 'Application': (24, 11)}


def view_query(classes):
    in_list = '(' + ', '.join(f'"{c}"' for c in classes) + ')'
    names = 'CASE(' + ', '.join(f'cls == "{c}", "{n}"' for c, n in classes.items()) + ', cls)'
    return f'''FROM cmdb_app_dependencies_v2
| WHERE (parent_ci.name.keyword == {SEL_CI} AND child_ci.class.keyword IN {in_list} AND {NOT_RETIRED("child")})
     OR (child_ci.name.keyword == {SEL_CI} AND parent_ci.class.keyword IN {in_list} AND {NOT_RETIRED("parent")})
| EVAL down = parent_ci.name.keyword == {SEL_CI}
| EVAL related = CASE(down, TO_STRING(child_ci.name.keyword), TO_STRING(parent_ci.name.keyword)),
       cls = CASE(down, TO_STRING(child_ci.class.keyword), TO_STRING(parent_ci.class.keyword)),
       o = CASE(down, TO_STRING(child_ci.operational_status.keyword), TO_STRING(parent_ci.operational_status.keyword)),
       env = CASE(down, TO_STRING(child_ci.environment.keyword), TO_STRING(parent_ci.environment.keyword)),
       r = TO_STRING(relationship.latest.servicenow.event.type.value)
| WHERE related IS NOT NULL AND related != {SEL_CI}
| EVAL rel = TO_LOWER({REL_CASE}), oper = {OPER_CASE}
| EVAL how = CASE(down, CONCAT("this CI ", rel, " it"), CONCAT("it ", rel, " this CI")), kind = {names}
| STATS kinds = VALUES(kind), hows = VALUES(how), opers = VALUES(oper), envs = VALUES(env) BY related_ci = related
| EVAL ci_type = MV_FIRST(kinds), relation = MV_CONCAT(hows, "; "), cmdb_status = MV_FIRST(opers), env1 = MV_FIRST(envs)
| EVAL related_env = CASE(env1 IS NULL OR env1 == "null", "—", env1),
       rank = CASE(cmdb_status IN ("Non-operational", "Repair in progress"), 1, 2)
| SORT rank ASC, ci_type ASC, related_ci ASC
| LIMIT 300
| KEEP related_ci, ci_type, relation, cmdb_status, related_env'''


new_views = []
for group, classes in GROUPS.items():
    old = P(f'{group} View')
    q = view_query(classes)
    p = table_panel(template_runs_on, f'mim-v3:view:{group}', f'{group} View',
                    DESCRIPTIONS[group] + ' Both directions: "this CI runs on it" (the CI uses it) and "it runs on this '
                    'CI" (it uses the CI), with the relationship from ServiceNow and the CMDB operational status '
                    '(non-operational and in-repair first); retired CIs are left out. CMDB data only, no live health '
                    '(the dependency index has no timestamp); for live health pick the CI in the CI control. Follows '
                    'the Incident / CI controls; not affected by the time picker.',
                    q,
                    [col('related_ci', 'Related CI'), col('ci_type', 'Type'), col('relation', 'Relationship'),
                     col('cmdb_status', 'CMDB status'), col('related_env', 'Env')],
                    [tcol('related_ci', 220), tcol('ci_type', 150), tcol('relation', 220),
                     tcol('cmdb_status', 120, align='center', badge=STATUS), tcol('related_env', 90)])
    x, y = VIEW_LAYOUT[group]
    p['panelIndex'] = old['panelIndex']
    p['gridData'] = {'x': x, 'y': y, 'w': 24, 'h': 11, 'i': old['panelIndex'], 'sectionId': NEWSEC}
    panels[panels.index(old)] = p
    new_views.append(p)

# drop the extra filter control (the views follow the Incident / CI controls now) and its data view
panels[:] = [p for p in panels if p['type'] != 'options_list_control']
dash['references'] = [r for r in dash.get('references', []) if not r['name'].endswith(':optionsListDataView')]

# ------------------------------------------------------------------ Application health (section 4, top row)
APP_CTRL_Q = f'''FROM metrics-apm.service_transaction.1m-*
| WHERE TO_LOWER(TO_STRING(service.environment)) IN {PROD} AND ci.name IS NOT NULL AND @timestamp >= NOW() - 1 day
| STATS apps = VALUES(TO_STRING(ci.name))
| EVAL application = MV_APPEND("{ALL_APPS}", apps)
| MV_EXPAND application
| EVAL ord = CASE(application == "{ALL_APPS}", 0, 1)
| SORT ord ASC, application ASC
| KEEP application'''
_TX = f'''FROM metrics-apm.service_transaction.1m-*
| WHERE TO_LOWER(TO_STRING(service.environment)) IN {PROD} AND ci.name IS NOT NULL'''
_SERVICE_HEALTH = f'''| EVAL error_pct = CASE(okn > 0, ROUND((okn - ok) * 100.0 / okn, 1))
| EVAL health = CASE(okn IS NULL OR okn == 0, "No traffic", okn < {MIN_TX}, "Low traffic", error_pct >= 10, "Failing",
                     error_pct >= 1, "Degraded", "Healthy")'''
APP_HEALTH = _TX + f'''
| STATS ok = SUM(event.success_count), okn = COUNT(event.success_count), tx = COUNT(transaction.duration.summary),
        nums = VALUES(TO_STRING(ci.number)), groups = VALUES(TO_STRING(ci.support_group.l2.name))
  BY ci.name, service.name
{_SERVICE_HEALTH}
| EVAL is_failing = CASE(health == "Failing", 1, 0), is_degraded = CASE(health == "Degraded", 1, 0),
       is_rated = CASE(health IN ("Failing", "Degraded", "Healthy"), 1, 0), rated_error_pct = CASE(is_rated == 1, error_pct)
| STATS services = COUNT(*), failing = SUM(is_failing), degraded = SUM(is_degraded), rated = SUM(is_rated),
        worst_error_pct = MAX(rated_error_pct),
        bad = SUM(okn - ok), calls = SUM(okn), tx = SUM(tx), nums = VALUES(nums), groups = VALUES(groups)
  BY ci.name
| EVAL app_health = CASE(failing > 0, "Failing", degraded > 0, "Degraded", rated > 0, "Healthy", calls > 0, "Low traffic",
                        "No traffic"),
       app_error_pct = CASE(calls > 0, ROUND(bad * 100.0 / calls, 1)),
       app_number = COALESCE(MV_FIRST(nums), "—"), app_support = COALESCE(MV_FIRST(groups), "—"),
       rank = CASE(failing > 0, 1, degraded > 0, 2, rated > 0, 3, 4)
| SORT rank ASC, failing DESC, degraded DESC, worst_error_pct DESC, ci.name ASC
| LIMIT 200
| KEEP ci.name, app_health, failing, degraded, services, worst_error_pct, app_error_pct, tx, app_number, app_support'''
APP_SERVICES = _TX + f'''
| WHERE ?application == "{ALL_APPS}" OR ci.name == ?application
| STATS ok = SUM(event.success_count), okn = COUNT(event.success_count), tx = COUNT(transaction.duration.summary),
        dur = SUM(transaction.duration.summary)
  BY service.name, ci.name
{_SERVICE_HEALTH}
| EVAL minutes = GREATEST(DATE_DIFF("minutes", ?_tstart, ?_tend), 1)
| EVAL latency_ms = CASE(tx > 0, ROUND(dur / tx / 1000.0, 0)), per_min = ROUND(tx * 1.0 / minutes, 1),
       rank = CASE(health == "Failing", 1, health == "Degraded", 2, health == "Healthy", 3, health == "Low traffic", 4, 5)
| SORT rank ASC, error_pct DESC, service.name ASC
| LIMIT 300
| KEEP service.name, ci.name, health, error_pct, latency_ms, per_min, tx'''

HEALTH = [('Failing', RED), ('Degraded', AMBER), ('Healthy', GREEN), ('Low traffic', '#6f87a6'), ('No traffic', GREY)]
num = lambda cid, label, es='long', dec=0, suffix=None: col(cid, label, 'number', es, {
    'id': 'number', 'params': dict({'decimals': dec}, **({'suffix': suffix} if suffix else {}))})
apps_tpl = P('Business applications impacted')
SEC4 = apps_tpl['gridData']['sectionId']
HOUR = {'from': 'now-1h', 'to': 'now'}
cmdb_dd = copy.deepcopy(apps_tpl['embeddableConfig']['drilldowns'][0])
cmdb_dd['label'] = 'Open the application in ServiceNow CMDB — use on the Application column'
map_dd = copy.deepcopy(P('Service health')['embeddableConfig']['drilldowns'][0])

app_health = table_panel(
    apps_tpl, 'mim-v3:app-health', 'Application Health',
    'Every production business application with APM data, rated by the health of its services in the last hour: '
    'Failing = at least one service with 10 % or more failed transactions, Degraded = at least one with 1 % or more, '
    f'Healthy otherwise; worst first. A service needs at least {MIN_TX} transactions in the hour to be rated (fewer = '
    '"Low traffic", shown in the services list but not counted here, so one failed call out of two does not make an '
    'application Failing). Failing / Degraded = how many of its services; Worst = the worst service\'s '
    'error rate; App = the application\'s overall error rate. To see which services, pick the application in the '
    'Application control: "Services of the Application" lists them. Click an application to open it in the '
    'ServiceNow CMDB. From the APM CMDB enrichment on each service (398 of 400 production services carry their '
    'application, round 10). Last 1 hour (fixed); not narrowed by the Incident or CI controls.',
    APP_HEALTH,
    [col('ci.name', 'Application'), col('app_health', 'Health'), num('failing', 'Failing'), num('degraded', 'Degraded'),
     num('services', 'Services'), num('worst_error_pct', 'Worst service', 'double', 1, ' %'),
     num('app_error_pct', 'App error rate', 'double', 1, ' %'), num('tx', 'Transactions'),
     col('app_number', 'APM number'), col('app_support', 'Support group')],
    [tcol('ci.name', 200, link=True), tcol('app_health', 90, align='center', badge=HEALTH),
     tcol('failing', 70, align='right'), tcol('degraded', 75, align='right'), tcol('services', 70, align='right'),
     tcol('worst_error_pct', 95, align='right'), tcol('app_error_pct', 100, align='right'),
     tcol('tx', 100, align='right'), tcol('app_number', 105), tcol('app_support', 200)],
    page=10, index_title='metrics-apm.service_transaction.1m-*')
app_health['embeddableConfig']['drilldowns'] = [cmdb_dd]
app_health['embeddableConfig']['time_range'] = HOUR

app_services = table_panel(
    apps_tpl, 'mim-v3:app-services', 'Services of the Application',
    'The services of the application picked in the Application control (all applications when none is picked), '
    f'worst first: health (Failing ≥ 10 % failed transactions, Degraded ≥ 1 %; Low traffic = under {MIN_TX} '
    'transactions in the hour, error rate shown but not rated), error rate, average latency, '
    'throughput. Click a service to open its APM Service Map. Last 1 hour (fixed).',
    APP_SERVICES,
    [col('service.name', 'Service'), col('ci.name', 'Application'), col('health', 'Health'),
     num('error_pct', 'Error rate', 'double', 1, ' %'), num('latency_ms', 'Latency', 'double', 0, ' ms'),
     num('per_min', 'Per minute', 'double', 1), num('tx', 'Transactions')],
    [tcol('service.name', 170, link=True), tcol('ci.name', 150), tcol('health', 85, align='center', badge=HEALTH),
     tcol('error_pct', 75, align='right'), tcol('latency_ms', 70, align='right'), tcol('per_min', 80, align='right'),
     tcol('tx', 90, align='right')],
    page=10, index_title='metrics-apm.service_transaction.1m-*')
app_services['embeddableConfig']['drilldowns'] = [map_dd]
app_services['embeddableConfig']['time_range'] = HOUR

for p in panels:
    if p['gridData'].get('sectionId') == SEC4:
        p['gridData']['y'] += 12
app_health['gridData'] = {'x': 0, 'y': 0, 'w': 26, 'h': 12, 'i': app_health['panelIndex'], 'sectionId': SEC4}
app_services['gridData'] = {'x': 26, 'y': 0, 'w': 22, 'h': 12, 'i': app_services['panelIndex'], 'sectionId': SEC4}
panels.extend([app_health, app_services])

ctrls = A['pinned_panels']['panels']
inc_ctrl = next(c for c in ctrls.values() if c['config']['variable_name'] == 'incident')
app_ctrl = copy.deepcopy(inc_ctrl)
app_ctrl['order'] = 3
app_ctrl['width'] = 'medium'
app_ctrl['config'].update(esql_query=APP_CTRL_Q, selected_options=[ALL_APPS], title='Application',
                          variable_name='application')
ctrls[uid('mim-v3:control:application')] = app_ctrl

# ------------------------------------------------------------------ sections: names, order, all expanded; 24 h default
ORDER = [('1 · Major Incident Overview', '1 · Major Incident Overview'),
         ('2 · Investigate the CI', '2 · Investigate the CI'),
         ('New collapsible section', '3 · Related CIs by Type (CMDB)'),
         ('3 · Service Dependency & Blast Radius', '4 · Application & Service Health, Dependencies'),
         ('4 · Related dashboards', '5 · Related dashboards')]
A['sections'] = [dict(SECTIONS[old], title=new, collapsed=False, gridData=dict(SECTIONS[old]['gridData'], y=i))
                 for i, (old, new) in enumerate(ORDER)]
A['timeFrom'], A['timeTo'] = 'now-24h', 'now'

# fix descriptions that name sections by number
for p in panels:
    ec = p['embeddableConfig']
    for k in ('description',):
        if ec.get(k):
            ec[k] = ec[k].replace('section 3', 'section 4').replace('Section 3', 'Section 4')

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
assert len({p['panelIndex'] for p in panels}) == len(panels)
assert not any(p['type'] == 'options_list_control' for p in panels)

A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
A['description'] = ('MIM V3 — major incident overview; one-CI investigation driven by the Incident / CI controls; the '
                    'CI\'s related middleware, databases, servers and applications from the CMDB; application and '
                    'service health (Application and Service controls) with dependencies and blast radius; related '
                    'dashboards.')
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{len(panels)} panels, sections: {[s["title"] for s in A["sections"]]}')
