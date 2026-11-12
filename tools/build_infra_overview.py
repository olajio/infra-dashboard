"""Build the Infrastructure Overview: the landing page of the infrastructure dashboards (10 Nov 2026).

Usage: build_infra_overview.py "MIM V5.ndjson" "Infrastructure Overview.ndjson"

Design: INFRA-OVERVIEW-KPIS.md (KPIs) and previews/INFRA-OVERVIEW-WALKTHROUGH.md (mockup and flow). No controls:
every panel reads correctly when the page opens. It replaces the CI-driven Infrastructure Dashboard and keeps its
id, so links and bookmarks to it keep working. MIM V5 is read only for its table and drill-down formats.

Sections:  1 · Infrastructure status   2 · What needs attention now   3 · Changes and trend   4 · Detailed dashboards

Domains: every incident and alert is put in one of Server, Database, Middleware, VMware, Cloud, Network (or
Application / Other, which the infrastructure panels leave out) by DOMAIN() below, from the CMDB class of its CI. The
team can change the patterns there; the class list to check them against is query IO1 in INFRA-OVERVIEW-KPIS.md.
Status rules (the banner): red = an open P1 or a Critical alert (or, for Server, a server not reporting); amber = an
active P2, a Major alert or a resource at 90 %; grey = not monitored (VMware).
"""
import copy
import json
import sys
import uuid

SRC, OUT = sys.argv[1:3]
NS = 'infra-dashboard/ci-driven-v1/'           # the Infrastructure Dashboard's namespace: same dashboard id
uid = lambda name: str(uuid.uuid5(uuid.NAMESPACE_URL, NS + name))
DASH_ID = uid('dashboard')
OV = lambda name: str(uuid.uuid5(uuid.NAMESPACE_URL, 'infra-overview/v1/' + name))
S1, S2, S3, S4 = (OV(f'section-{i}') for i in range(1, 5))
D7, D30 = {'from': 'now-7d', 'to': 'now'}, {'from': 'now-30d', 'to': 'now'}

mim = next(o for o in (json.loads(l) for l in open(SRC) if l.strip()) if o.get('type') == 'dashboard')
MP = {p['embeddableConfig'].get('title'): p for p in json.loads(mim['attributes']['panelsJSON'])}
SN_DRILLDOWNS = MP['Active Incidents (P1 · P2 over 8 h · P3 over 24 h)']['embeddableConfig']['drilldowns']
LINKS = {   # respective_detailed_dashboards.txt
    'Server': 'https://kibana-prod.gcp.cna.com/app/r/s/qJk5u', 'Database': 'https://kibana-prod.gcp.cna.com/app/r/s/w6zL4',
    'Middleware': 'https://kibana-prod.gcp.cna.com/app/r/s/jwCRg', 'VMware': 'https://kibana-prod.gcp.cna.com/app/r/s/t4oxr',
    'Cloud': 'https://kibana-prod.gcp.cna.com/app/r/s/MDJ9f', 'Applications': 'https://kibana-prod.gcp.cna.com/app/r/s/I3R7D',
    'MIM': 'https://kibana-prod.gcp.cna.com/app/r/s/ZSMtk',
    # no short link given: Portfolio v4's dashboard id from portfolio_v4.ndjson (11 Nov)
    'Portfolio': 'https://kibana-prod.gcp.cna.com/app/dashboards#/view/7511c5d1-3326-4c7e-91f4-6c8fdb686ee0'}
ICON = {'Server': '🖥️', 'Database': '🗄️', 'Middleware': '⚙️', 'VMware': '🧱', 'Cloud': '☁️', 'Network': '🌐'}
DOMAINS = ['Server', 'Database', 'Middleware', 'VMware', 'Cloud', 'Network']
GREEN, AMBER, RED, BLUE, GREY = '#1f9e6b', '#c98a0b', '#d6453d', '#3f6fb5', '#8a96a8'


# ---------------- the domain of a CI, from its CMDB class (both "Linux Server" and "cmdb_ci_linux_server" forms) --------------
def DOMAIN(cls):
    c = f'TO_LOWER(COALESCE({cls}, ""))'
    like = lambda *ps: ' OR '.join(f'{c} LIKE "*{p}*"' for p in ps)
    return (f'CASE({c} == "" OR {c} == "null", "Unknown", '
            f'{like("infrastructure service")}, "Other", '
            f'{like("esx", "vmware", "vcenter", "vsphere", "hyper_v", "hyper-v")}, "VMware", '
            f'{like("sql", "oracle", "db2", "database", "postgres", "mongo", "sybase", "_db", "db_")}, "Database", '
            f'{like("mq", "websphere", "jboss", "tomcat", "weblogic", "iis", "app_server", "application server", "web server", "web_server", "middleware")}, "Middleware", '
            f'{like("kubernetes", "gke", "cloud", "gcp", "container")}, "Cloud", '
            f'{like("switch", "router", "ups", "firewall", "load bal", "lb_", "network", "wireless", "access point", "ip_", "ip ", "netgear", "pdu", "big-ip", "bigip", "f5", "dns", "communication")}, "Network", '
            f'{like("server", "linux", "windows", "win_", "aix", "solaris", "unix", "computer", "mainframe", "lpar", "storage", "hardware")}, "Server", '
            f'{like("application", "service", "business", "app", "batch")}, "Application", '
            '"Other")')


PROD = ('(TO_STRING(ci.environment) IS NULL OR TO_STRING(ci.environment) IN ("", "null") '
        'OR TO_LOWER(TO_STRING(ci.environment)) LIKE "prod*" OR TO_LOWER(TO_STRING(ci.environment)) LIKE "prd*")')
INFRA = 'domain IN ("Server", "Database", "Middleware", "VMware", "Cloud", "Network", "Unknown", "Other")'
NOT_ACTIVE = '("On Hold", "Resolved", "Closed", "Canceled", "Cancelled")'

# active P1 / P2 incidents on infrastructure (the incident's latest record, as in MIM)
INC_BASE = f"""FROM servicenow-incidents-*
| WHERE TO_STRING(number) LIKE "INC*" AND opened_at >= NOW() - 30 days
| INLINE STATS last_seen = MAX(@timestamp) BY number
| WHERE @timestamp == last_seen AND TO_INTEGER(priority) IN (1, 2) AND TO_STRING(state_name) NOT IN {NOT_ACTIVE}
| EVAL domain = {DOMAIN('TO_STRING(ci.class_name)')}, pri = TO_INTEGER(priority),
       age_minutes = DATE_DIFF("minutes", TO_DATETIME(opened_at), NOW())
| WHERE {INFRA}
"""

# open alerts, one row per alert: Netcool (open in the last 24 h, production) and Elastic (active paladin-* rules)
ALERTS_BASE = f"""FROM .ds-bridge-alerts-netcool-default-*, .alerts-observability.* METADATA _index
| EVAL nc = _index LIKE "*netcool*"
| WHERE (nc AND @timestamp >= NOW() - 24 hours AND {PROD})
     OR (NOT nc AND @timestamp >= NOW() - 7 days AND TO_STRING(kibana.alert.status) == "active"
         AND TO_STRING(kibana.alert.rule.name) LIKE "paladin*")
| EVAL rule = TO_LOWER(TO_STRING(kibana.alert.rule.name)),
       ekey = CONCAT(COALESCE(TO_STRING(kibana.alert.rule.name), ""), "|", COALESCE(TO_STRING(kibana.alert.instance.id), "")),
       akey = CASE(nc, CONCAT("n|", COALESCE(TO_STRING(netcool.identifier), "")), CONCAT("e|", ekey)),
       eparts = SPLIT(REPLACE(TO_LOWER(TO_STRING(kibana.alert.instance.id)), "#", ","), ","),
       ehead = MV_FIRST(SPLIT(REPLACE(TO_LOWER(TO_STRING(kibana.alert.instance.id)), "#", ","), ","))
| EVAL ci_e = CASE(MV_COUNT(eparts) > 1 AND LENGTH(ehead) == 32, MV_FIRST(MV_SLICE(eparts, 1, 1)), ehead),
       esev = TO_LOWER(TO_STRING(kibana.alert.severity)),
       rec = CONCAT(TO_STRING(TO_LONG(@timestamp)), "~", COALESCE(TO_STRING(severity), "9"), "~",
                    COALESCE(TO_STRING(netcool.type_name), "problem"), "~",
                    COALESCE(TO_STRING(message), TO_STRING(kibana.alert.reason), TO_STRING(kibana.alert.rule.name), ""))
| EVAL erank = CASE(nc, null, esev == "critical", 3, esev IN ("low", "minor", "warning", "medium"), 1, 2)
| STATS latest = MAX(rec), nsev = MAX(CASE(nc AND severity > 0, severity)), erank = MAX(erank),
        ci_n = VALUES(TO_STRING(ci.name)), node_n = VALUES(TO_STRING(node)), cls = VALUES(TO_STRING(ci.class_name)),
        ci_es = VALUES(ci_e), rules = VALUES(rule), started = MIN(COALESCE(TO_DATETIME(first_occurrence), TO_DATETIME(kibana.alert.start), @timestamp))
  BY akey, nc
| DISSECT latest "%{{ts}}~%{{sev_now}}~%{{type_now}}~%{{summary}}"
| WHERE NOT nc OR (sev_now != "0" AND type_now != "resolution")
| EVAL rule1 = COALESCE(MV_FIRST(rules), ""), cls1 = MV_FIRST(cls),
       severity_label = CASE(nc AND nsev == 5, "Critical", nc AND nsev == 4, "Major", nc, "Minor",
                             erank == 3, "Critical", erank == 1, "Minor", "Major"),
       domain = CASE(nc AND cls1 IS NULL, "Network",
                     nc, {DOMAIN('cls1')},
                     rule1 LIKE "*mq*" OR rule1 LIKE "*websphere*" OR rule1 LIKE "*jboss*" OR rule1 LIKE "*tomcat*" OR rule1 LIKE "*iis*", "Middleware",
                     rule1 LIKE "*sql*" OR rule1 LIKE "*oracle*" OR rule1 LIKE "*db2*" OR rule1 LIKE "*database*", "Database",
                     rule1 LIKE "*gke*" OR rule1 LIKE "*kubernetes*", "Cloud",
                     "Server"),
       source = CASE(nc, "Netcool", "Elastic"),
       ci = COALESCE(MV_FIRST(ci_n), MV_FIRST(node_n), MV_FIRST(ci_es), "—"),
       sev_rank = CASE(severity_label == "Critical", 3, severity_label == "Major", 2, 1)
| WHERE {INFRA}
"""

# servers: CPU p90, memory and fullest disk over the last hour; silent = no data for 10 minutes (seen in the last day)
SRV_BASE = f"""FROM .ds-metrics-system.cpu-default*, .ds-metrics-system.memory-default*, .ds-metrics-system.filesystem-default*
| WHERE @timestamp >= NOW() - 24 hours AND {PROD}
| EVAL recent = @timestamp >= NOW() - 1 hour,
       cpu = CASE(recent, TO_DOUBLE(system.cpu.total.norm.pct)), mem = CASE(recent, TO_DOUBLE(system.memory.actual.used.pct)),
       disk = CASE(recent, TO_DOUBLE(system.filesystem.used.pct)),
       server = TO_LOWER(COALESCE(TO_STRING(ci.name), TO_STRING(host.name)))
| STATS cpu_p90 = PERCENTILE(cpu, 90), mem_max = MAX(mem), disk_max = MAX(disk), last_seen = MAX(@timestamp) BY server
| WHERE server IS NOT NULL
| EVAL silent = CASE(DATE_DIFF("minutes", last_seen, NOW()) > 10, 1, 0),
       hot_cpu = CASE(cpu_p90 >= 0.9, 1, 0), hot_mem = CASE(mem_max >= 0.9, 1, 0), hot_disk = CASE(disk_max >= 0.9, 1, 0)
| EVAL pressure = CASE(silent == 0 AND (hot_cpu == 1 OR hot_mem == 1 OR hot_disk == 1), 1, 0)
"""


# VMware: the vSphere integration (metrics-vsphere.*), the same data as the VMware Infra Dashboard (vmware.ndjson).
# Collected and used (vmware_data.xlsx): host CPU, host memory, host disk latency, datastore capacity, VM status.
# Not collected: CPU ready, ballooning, swapping, packet loss. Thresholds from vmware_data.xlsx.
# ".pct" fields: Elastic's 0-1 fractions (values above 1.5 are taken as already in %).
pct = lambda e: f'CASE({e} > 1.5, {e}, {e} * 100.0)'
VM_BASE = f"""FROM metrics-vsphere.host-*, metrics-vsphere.datastore-*, metrics-vsphere.virtualmachine-* METADATA _index
| WHERE @timestamp >= NOW() - 1 hour
| EVAL kind = CASE(_index LIKE "*vsphere.host*", "host", _index LIKE "*vsphere.datastore*", "datastore", "vm"),
       ent = CASE(_index LIKE "*vsphere.host*", TO_STRING(vsphere.host.name), _index LIKE "*vsphere.datastore*",
                  TO_STRING(vsphere.datastore.name), TO_STRING(vsphere.virtualmachine.name)),
       recent = @timestamp >= NOW() - 15 minutes,
       cpu = TO_DOUBLE(vsphere.host.cpu.used.pct),
       mem = TO_DOUBLE(vsphere.host.memory.used.bytes) / TO_DOUBLE(vsphere.host.memory.total.bytes) * 100.0,
       lat = TO_DOUBLE(vsphere.host.disk.latency.total.ms), dsu = TO_DOUBLE(vsphere.datastore.capacity.used.pct),
       vst = TO_LOWER(TO_STRING(vsphere.virtualmachine.status))
| STATS cpu = MAX(cpu), mem = MAX(mem), lat = MAX(lat), dsu = MAX(dsu), last_seen = MAX(@timestamp),
        red = MAX(CASE(recent AND vst == "red", 1, 0)), yellow = MAX(CASE(recent AND vst == "yellow", 1, 0))
  BY kind, ent
| WHERE ent IS NOT NULL
| EVAL cpu = {pct('cpu')}, dsu = {pct('dsu')}, silent = CASE(DATE_DIFF("minutes", last_seen, NOW()) > 15, 1, 0)
"""
VM_SUM_Q = VM_BASE + """| STATS hosts = COUNT(CASE(kind == "host", 1)), vms = COUNT(CASE(kind == "vm", 1)),
        datastores = COUNT(CASE(kind == "datastore", 1)),
        hosts_silent = SUM(CASE(kind == "host", silent, 0)), vms_red = SUM(CASE(kind == "vm", red, 0)),
        vms_yellow = SUM(CASE(kind == "vm", yellow, 0)),
        cpu_max = MAX(CASE(kind == "host", cpu)), mem_max = MAX(CASE(kind == "host", mem)), lat_max = MAX(CASE(kind == "host", lat)),
        hosts_crit = SUM(CASE(kind == "host" AND (cpu >= 90 OR mem >= 95 OR lat >= 25), 1, 0)),
        hosts_warn = SUM(CASE(kind == "host" AND (cpu >= 75 OR mem >= 85 OR lat >= 10), 1, 0)),
        ds_crit = SUM(CASE(kind == "datastore" AND dsu >= 90, 1, 0)), ds_warn = SUM(CASE(kind == "datastore" AND dsu >= 80, 1, 0))
| EVAL cpu_max = ROUND(cpu_max, 0), mem_max = ROUND(mem_max, 0), lat_max = ROUND(lat_max, 0)"""


def gke_q():
    """Infrastructure Dashboard's Cloud health · GKE query, for every cluster, last hour."""
    import re
    src = open(__file__.rsplit('/', 1)[0] + '/build_infra_dashboard.py').read()
    m = re.search(r'GKE_HEALTH_Q = f"""(.*?)"""', src, re.S)
    q = m.group(1)
    q = q.replace('{WINDOW}', '1 hour').replace('{K8S}', '"cmdb_ci_kubernetes_cluster"')
    q = q.replace('?ci', '"(no CI selected)"')
    return q


GKE_Q = gke_q()


# ---------------- panel helpers ----------------
def grid(pid, section, x, y, w, h):
    return {'x': x, 'y': y, 'w': w, 'h': h, 'i': pid, 'sectionId': section}


def adhoc(title):
    dv = OV('dataview/' + title)
    return dv, {dv: {'id': dv, 'title': title, 'timeFieldName': '@timestamp', 'sourceFilters': [], 'type': 'esql',
                     'fieldFormats': {}, 'runtimeFieldMap': {}, 'allowNoIndex': False, 'name': title,
                     'allowHidden': True, 'managed': False}}


def metric_tile(name, q, colour, section, x, y, w, h, icon, subtitle, description, time_range, index_title,
                secondary=None, secondary_prefix=None):
    pid, layer = OV('panel/' + name), OV('layer/' + name)
    dv, views = adhoc(index_title)
    num = lambda cid, label: {'columnId': cid, 'fieldName': cid, 'label': label, 'customLabel': True,
                              'meta': {'type': 'number', 'esType': 'long'}, 'inMetricDimension': True}
    cols = [num('metric_val', name)] + ([num(secondary, secondary_prefix)] if secondary else [])
    vis = {'layerId': layer, 'layerType': 'data', 'metricAccessor': 'metric_val', 'subtitle': subtitle,
           'icon': icon, 'iconAlign': 'left', 'titleWeight': 'bold', 'valueFontMode': 'default', 'applyColorTo': 'value',
           'palette': {'name': 'custom', 'type': 'palette', 'params': {
               'name': 'custom', 'reverse': False, 'steps': 2, 'maxSteps': 5, 'rangeType': 'number', 'rangeMin': 0,
               'rangeMax': 2, 'progression': 'fixed', 'continuity': 'all',
               'stops': [{'color': GREEN, 'stop': 1}, {'color': colour, 'stop': 2}],
               'colorStops': [{'color': GREEN, 'stop': 0}, {'color': colour, 'stop': 1}]}}}
    if secondary:
        vis.update({'secondaryMetricAccessor': secondary, 'secondaryPrefix': secondary_prefix})
    return {'type': 'vis', 'panelIndex': pid, 'gridData': grid(pid, section, x, y, w, h),
            'embeddableConfig': {
                'title': name, 'hide_title': True, 'description': description, 'time_range': dict(time_range),
                'attributes': {'title': name, 'references': [], 'visualizationType': 'lnsMetric', 'version': 2,
                               'state': {'datasourceStates': {'textBased': {
                                   'layers': {layer: {'index': dv, 'query': {'esql': q}, 'timeField': '@timestamp', 'columns': cols}},
                                   'indexPatternRefs': [{'id': dv, 'title': index_title, 'timeField': '@timestamp'}]}},
                                   'filters': [], 'query': {'esql': q}, 'needsRefresh': False, 'visualization': vis,
                                   'adHocDataViews': views}}}}


TEMPLATE_TABLE = MP['Open Alerts with No Incident']
S, N, D = {'type': 'string', 'esType': 'keyword'}, {'type': 'number', 'esType': 'long'}, {'type': 'date', 'esType': 'date'}


def badge(pairs):
    return {'colorMode': 'badge', 'palette': {'type': 'palette', 'name': 'default'}, 'colorMapping': {
        'paletteId': 'default', 'colorMode': {'type': 'categorical'},
        'assignments': [{'rules': [{'type': 'match', 'pattern': k, 'matchEntireWord': True, 'matchCase': True}],
                         'color': {'type': 'colorCode', 'colorCode': v}, 'touched': True} for k, v in pairs],
        'specialAssignments': [{'rules': [{'type': 'other'}], 'color': {'type': 'colorCode', 'colorCode': GREY}, 'touched': True}]}}


SEV_BADGE = badge([('Critical', RED), ('Major', '#d95926'), ('Minor', AMBER)])
PRI_BADGE = {'colorMode': 'badge', 'palette': {'name': 'custom', 'type': 'palette', 'params': {
    'name': 'custom', 'reverse': False, 'steps': 3, 'maxSteps': 5, 'rangeType': 'number', 'rangeMin': 1, 'rangeMax': 3,
    'progression': 'fixed', 'continuity': 'all', 'stops': [{'color': RED, 'stop': 2}, {'color': AMBER, 'stop': 3}],
    'colorStops': [{'color': RED, 'stop': 1}, {'color': AMBER, 'stop': 2}]}}}


def table(name, q, cols, section, x, y, w, h, description, time_range, index_title, drilldowns=None):
    """cols: (id, label, meta, width, extra visualization settings)."""
    p = copy.deepcopy(TEMPLATE_TABLE)
    pid = OV('panel/' + name)
    p['panelIndex'] = pid
    p['gridData'] = grid(pid, section, x, y, w, h)
    ec = p['embeddableConfig']
    ec['title'] = name
    ec['description'] = description
    ec['time_range'] = dict(time_range)
    if drilldowns:
        ec['drilldowns'] = drilldowns
    else:
        ec.pop('drilldowns', None)
    at = ec['attributes']
    at['title'] = name
    st = at['state']
    (lid, layer), = st['datasourceStates']['textBased']['layers'].items()
    dv, views = adhoc(index_title)
    layer['index'] = dv
    layer['query'] = {'esql': q}
    layer.pop('allColumns', None)
    layer['columns'] = [{'columnId': c, 'fieldName': c, 'label': l, 'customLabel': True, 'meta': m, 'inMetricDimension': True}
                        for c, l, m, _, _ in cols]
    st['query'] = {'esql': q}
    st['datasourceStates']['textBased']['indexPatternRefs'] = [{'id': dv, 'title': index_title, 'timeField': '@timestamp'}]
    st['adHocDataViews'] = views
    st['visualization']['columns'] = [dict({'columnId': c, 'isTransposed': False, 'isMetric': False, 'alignment': 'left',
                                            'width': wd}, **(extra or {})) for c, _, _, wd, extra in cols]
    st['visualization']['showRowNumbers'] = True
    return p


def vega(name, spec, section, x, y, w, h, description, time_range=None):
    pid = OV('panel/' + name)
    ec = {'title': name, 'hide_title': True, 'description': description,
          'savedVis': {'title': name, 'description': '', 'type': 'vega', 'params': {'spec': json.dumps(spec, indent=1, ensure_ascii=False)},
                       'uiState': {}, 'data': {'aggs': [], 'searchSource': {}}}}
    if time_range:
        ec['time_range'] = dict(time_range)
    return {'type': 'legacy_vis', 'panelIndex': pid, 'gridData': grid(pid, section, x, y, w, h), 'embeddableConfig': ec}


def markdown(name, content, section, x, y, w, h):
    pid = OV('panel/' + name)
    return {'type': 'markdown', 'panelIndex': pid, 'gridData': grid(pid, section, x, y, w, h),
            'embeddableConfig': {'title': name, 'hide_title': True, 'content': content,
                                 'settings': {'open_links_in_new_tab': True}}}


VEGA = {'$schema': 'https://vega.github.io/schema/vega/v5.json', 'autosize': {'type': 'fit', 'contains': 'padding'}, 'padding': 4}
esql = lambda name, q: {'name': name, 'url': {'%type%': 'esql', 'query': q}}
txt = lambda x, y, text, size=12, weight='normal', fill=None, align='left', style=None, extra=None: dict(
    {'type': 'text', 'encode': {'update': dict({
        'x': x, 'y': y, 'text': text, 'fontSize': {'value': size}, 'fontWeight': {'value': weight},
        'align': {'value': align}, 'baseline': {'value': 'middle'}}, **({'fill': fill} if fill else {}), **(extra or {}))}},
    **({'style': style} if style else {}))


def banner(name, step, headline, detail, section):
    spec = dict(VEGA, padding=0, marks=[
        {'type': 'rect', 'encode': {'update': {'x': {'value': 0}, 'y': {'value': 0}, 'width': {'signal': 'width'},
                                               'height': {'signal': 'height'}, 'fill': {'value': '#0b64dd'},
                                               'fillOpacity': {'value': 0.16}, 'cornerRadius': {'value': 6}}}},
        {'type': 'rect', 'encode': {'update': {'x': {'value': 0}, 'y': {'value': 0}, 'width': {'value': 6},
                                               'height': {'signal': 'height'}, 'fill': {'value': '#0b64dd'}}}},
        {'type': 'symbol', 'encode': {'update': {'x': {'value': 30}, 'y': {'signal': 'height / 2'}, 'shape': {'value': 'circle'},
                                                 'size': {'value': 700}, 'fill': {'value': '#0b64dd'}}}},
        txt({'value': 30}, {'signal': 'height / 2 + 1'}, {'value': step}, 15, 'bold', {'value': 'white'}, 'center'),
        txt({'value': 54}, {'signal': 'height / 2 - 8'}, {'value': headline}, 15, 'bold', {'value': '#0b64dd'},
            extra={'limit': {'signal': 'width - 70'}}),
        txt({'value': 54}, {'signal': 'height / 2 + 11'}, {'value': detail}, 12, style='guide-label',
            extra={'limit': {'signal': 'width - 70'}})])
    return vega(name, spec, section, 0, 0, 48, 3, 'How to read the page. Not data.')


# ---------------- 1 · Infrastructure status ----------------
def domain_board():
    """One status tile per domain, from active P1 / P2 incidents, open alerts, server and GKE health."""
    inc_q = INC_BASE + ('| STATS p1 = COUNT_DISTINCT(CASE(pri == 1, number)), p2 = COUNT_DISTINCT(CASE(pri == 2, number)) BY domain')
    al_q = ALERTS_BASE + ('| STATS critical = SUM(CASE(severity_label == "Critical", 1, 0)), '
                          'major = SUM(CASE(severity_label == "Major", 1, 0)), alerts = COUNT(*) BY domain')
    srv_q = SRV_BASE + ('| STATS servers = COUNT(*), silent = SUM(silent), pressure = SUM(pressure), '
                        'disk = SUM(CASE(silent == 0, hot_disk, 0)), cpu = SUM(CASE(silent == 0, hot_cpu, 0)), '
                        'mem = SUM(CASE(silent == 0, hot_mem, 0))')
    gke_q2 = GKE_Q.rsplit('| KEEP', 1)[0] + ('| STATS clusters = COUNT(*), gke_bad = SUM(CASE(status IN ("Critical", "Silent"), 1, 0)), '
                                            'gke_warn = SUM(CASE(status == "Warning", 1, 0)), restarts = SUM(restarts)')
    dom_vals = [{'d': d, 'i': i, 'icon': ICON[d]} for i, d in enumerate(DOMAINS)]
    look = lambda src, fields: {'type': 'lookup', 'from': src, 'key': 'domain', 'fields': ['d'], 'values': fields,
                                'default': 0}
    s1 = "data('srv')[0] || {}"
    g1 = "data('gke')[0] || {}"
    v1 = "data('vm')[0] || {}"
    spec = dict(VEGA, padding=0, data=[
        esql('inc', inc_q), esql('al', al_q), esql('srv', srv_q), esql('gke', gke_q2), esql('vm', VM_SUM_Q),
        {'name': 'dom', 'values': dom_vals, 'transform': [
            look('inc', ['p1', 'p2']), look('al', ['critical', 'major', 'alerts']),
            {'type': 'formula', 'as': 'silent', 'expr': f"datum.d == 'Server' ? (({s1}).silent || 0) : 0"},
            {'type': 'formula', 'as': 'pressure', 'expr': f"datum.d == 'Server' ? (({s1}).pressure || 0) : 0"},
            {'type': 'formula', 'as': 'gbad', 'expr': f"datum.d == 'Cloud' ? (({g1}).gke_bad || 0) : 0"},
            {'type': 'formula', 'as': 'gwarn', 'expr': f"datum.d == 'Cloud' ? (({g1}).gke_warn || 0) : 0"},
            {'type': 'formula', 'as': 'vhave', 'expr': f"datum.d == 'VMware' ? ((({v1}).hosts || 0) + (({v1}).vms || 0)) : 1"},
            {'type': 'formula', 'as': 'vbad', 'expr':
                f"datum.d == 'VMware' ? ((({v1}).hosts_silent || 0) + (({v1}).hosts_crit || 0) + (({v1}).ds_crit || 0) + (({v1}).vms_red || 0)) : 0"},
            {'type': 'formula', 'as': 'vwarn', 'expr':
                f"datum.d == 'VMware' ? ((({v1}).hosts_warn || 0) + (({v1}).ds_warn || 0) + (({v1}).vms_yellow || 0)) : 0"},
            {'type': 'formula', 'as': 'level', 'expr':
                "(datum.p1 > 0 || datum.critical > 0 || datum.silent > 0 || datum.gbad > 0 || datum.vbad > 0) ? 2 : "
                "(datum.p2 > 0 || datum.major > 0 || datum.pressure > 0 || datum.gwarn > 0 || datum.vwarn > 0) ? 1 : "
                "(datum.vhave == 0 ? -1 : 0)"},
            {'type': 'formula', 'as': 'word', 'expr':
                "datum.level == 2 ? 'Action' : datum.level == 1 ? 'Attention' : datum.level == -1 ? 'Not monitored' : 'Healthy'"},
            {'type': 'formula', 'as': 'colour', 'expr':
                f"datum.level == 2 ? '{RED}' : datum.level == 1 ? '{AMBER}' : datum.level == -1 ? '{GREY}' : '{GREEN}'"},
            {'type': 'formula', 'as': 'tag', 'expr':
                "datum.d == 'Database' ? 'partial' : datum.d == 'Middleware' ? 'partial' : "
                "datum.d == 'Cloud' ? 'GKE' : datum.d == 'Network' ? 'Netcool' : datum.d == 'VMware' ? 'vSphere · partial' : ''"},
            {'type': 'formula', 'as': 'l1', 'expr': "'Open P1: ' + datum.p1 + ' · P2: ' + datum.p2"},
            {'type': 'formula', 'as': 'l2', 'expr': "'Alerts: ' + datum.critical + ' Critical · ' + datum.major + ' Major'"},
            {'type': 'formula', 'as': 'l3', 'expr':
                f"datum.d == 'Server' ? (datum.silent + ' not reporting · ' + datum.pressure + ' under pressure (of ' + ((({s1}).servers) || 0) + ')') : "
                f"datum.d == 'Cloud' ? ((({g1}).clusters || 0) + ' GKE clusters · ' + datum.gbad + ' critical / silent · ' + datum.gwarn + ' warning') : "
                f"datum.d == 'VMware' ? ((({v1}).hosts || 0) + ' hosts · ' + (({v1}).vms || 0) + ' VMs (' + (({v1}).vms_red || 0) + ' red) · ' + (({v1}).ds_warn || 0) + ' datastores ≥ 80 %') : "
                "datum.d == 'Network' ? 'devices and UPSs · no network dashboard yet' : "
                "datum.d == 'Database' ? 'down / slow: see the Database dashboard' : 'see the Middleware dashboard'"},
            {'type': 'formula', 'as': 'l4', 'expr':
                f"datum.d == 'VMware' && datum.vhave > 0 ? ('Peak: CPU ' + (({v1}).cpu_max || 0) + ' % · mem ' + (({v1}).mem_max || 0) + ' % · ' + (({v1}).lat_max || 0) + ' ms') : "
                "datum.d == 'VMware' ? 'no vSphere data in the last hour' : ''"}]}],
        signals=[{'name': 'tw', 'update': 'width / 6'}],
        marks=[{'type': 'group', 'from': {'data': 'dom'}, 'encode': {'update': {
            'x': {'signal': 'datum.i * tw + 3'}, 'y': {'value': 2}, 'width': {'signal': 'tw - 6'}, 'height': {'signal': 'height - 4'},
            'fill': {'value': '#88a0c0'}, 'fillOpacity': {'value': 0.06}, 'cornerRadius': {'value': 6},
            'stroke': {'value': '#88a0c0'}, 'strokeOpacity': {'value': 0.25}}},
            'marks': [
                {'type': 'rect', 'encode': {'update': {'x': {'value': 0}, 'y': {'value': 0}, 'width': {'signal': 'tw - 6'},
                                                       'height': {'value': 5}, 'fill': {'signal': 'parent.colour'},
                                                       'cornerRadius': {'value': 2}}}},
                txt({'value': 12}, {'value': 24}, {'signal': "parent.icon + '  ' + parent.d"}, 15, 'bold', style='guide-title'),
                txt({'signal': 'tw - 18'}, {'value': 24}, {'signal': 'parent.tag'}, 10, 'bold', {'value': '#c99a2e'}, 'right'),
                txt({'value': 12}, {'value': 54}, {'signal': 'parent.word'}, 22, 'bold', {'signal': 'parent.colour'}),
                txt({'value': 12}, {'value': 82}, {'signal': 'parent.l1'}, 11.5, style='guide-label', extra={'limit': {'signal': 'tw - 30'}}),
                txt({'value': 12}, {'value': 99}, {'signal': 'parent.l2'}, 11.5, style='guide-label', extra={'limit': {'signal': 'tw - 30'}}),
                txt({'value': 12}, {'value': 116}, {'signal': 'parent.l3'}, 11.5, style='guide-label', extra={'limit': {'signal': 'tw - 30'}}),
                txt({'value': 12}, {'value': 133}, {'signal': 'parent.l4'}, 11.5, style='guide-label', extra={'limit': {'signal': 'tw - 30'}})]}])
    return vega('Domain status', spec, S1, 0, 3, 48, 8,
                'One tile per infrastructure domain. Red (Action): an open P1, a Critical alert, a server not reporting '
                'or a GKE cluster critical or silent. Amber (Attention): an active P2, a Major alert, a server at 90 % '
                'CPU, memory or disk, or a GKE cluster warning. VMware (vSphere, last hour): red = a host silent 15 min, '
                'host CPU ≥ 90 %, memory ≥ 95 % or disk latency ≥ 25 ms, a datastore ≥ 90 % or a red VM; amber = host '
                'CPU ≥ 75 %, memory ≥ 85 % or latency ≥ 10 ms, a datastore ≥ 80 % or a yellow VM (vmware_data.xlsx). '
                'Green: none. Grey: no vSphere data. Domain = from the CMDB class of the incident or alert CI. Incidents: active P1 / P2 '
                '(latest record not On Hold, Resolved, Closed, Canceled), opened in the last 30 days. Alerts: open '
                'Netcool alerts (24 h, production) and active Elastic paladin-* alerts. Servers: last hour. Click the '
                'link under a tile to open its dashboard.', D30)


panels = [banner('Start here', '1', '▲  Start here: a red or amber tile shows where to look. Open its dashboard from the link under it.',
                 'No control to pick. Red = an open P1, a Critical alert or a server not reporting · Amber = a P2, a Major alert or a resource at 90 % · Grey = not monitored.', S1),
          domain_board()]
for i, d in enumerate(DOMAINS):
    content = (f'**{ICON[d]} [{d} dashboard ›]({LINKS[d]})**' if d in LINKS else
               f'{ICON[d]} No network dashboard')
    panels.append(markdown(f'{d} link', content, S1, i * 8, 11, 8, 2))

SN_IDX = 'servicenow-incidents-*'
AL_IDX = '.ds-bridge-alerts-netcool-default-*,.alerts-observability.*'
SRV_IDX = '.ds-metrics-system.cpu-default*,.ds-metrics-system.memory-default*,.ds-metrics-system.filesystem-default*'
CHG_IDX = 'servicenow-change-requests-*'
FAILED = ('(TO_LOWER(TO_STRING(close_code)) LIKE "*unsuccess*" OR TO_LOWER(TO_STRING(close_code)) LIKE "*fail*" '
          'OR TO_LOWER(TO_STRING(close_code)) LIKE "*back*")')
CHG_LATEST = """FROM servicenow-change-requests-*
| WHERE TO_STRING(number) LIKE "CHG*" AND @timestamp >= NOW() - 30 days
| INLINE STATS last_seen = MAX(@timestamp) BY number
| WHERE @timestamp == last_seen
"""
panels += [
    metric_tile('Active P1 (infrastructure)', INC_BASE + '| WHERE pri == 1\n| STATS metric_val = COUNT_DISTINCT(number)',
                RED, S1, 0, 13, 8, 6, 'alert', 'Open P1 incidents on infrastructure CIs',
                'Active P1 incidents (latest record not On Hold, Resolved, Closed or Canceled; opened in the last 30 days) '
                'whose CI is infrastructure (not an application service). Green at 0. The rows are in section 2.', D30, SN_IDX),
    metric_tile('P2 over 8 h (infrastructure)', INC_BASE + '| WHERE pri == 2 AND age_minutes > 480\n| STATS metric_val = COUNT_DISTINCT(number)',
                AMBER, S1, 8, 13, 8, 6, 'clock', 'Active P2 open longer than 8 h (MIM\'s target)',
                'Active P2 incidents on infrastructure CIs open longer than 8 h, MIM\'s P2 target. Green at 0.', D30, SN_IDX),
    metric_tile('Critical alerts', ALERTS_BASE + '| STATS metric_val = SUM(CASE(severity_label == "Critical", 1, 0)), '
                'major = SUM(CASE(severity_label == "Major", 1, 0))',
                RED, S1, 16, 13, 8, 6, 'bell', 'Open now · Netcool and Elastic',
                'Open Critical alerts on infrastructure: Netcool alerts still open in the last 24 h on production CIs, '
                'and active Elastic paladin-* alerts. Major count under the number. Green at 0.', D7, AL_IDX,
                'major', 'Major'),
    metric_tile('Servers not reporting', SRV_BASE + '| STATS metric_val = SUM(silent), servers = COUNT(*)',
                RED, S1, 24, 13, 8, 6, 'offline', 'No data for 10 min (seen in the last day)',
                'Production servers that sent system metrics in the last 24 h but none in the last 10 minutes: down, or '
                'their agent stopped. Under the number: servers reporting in the last day. Green at 0.', D7, SRV_IDX,
                'servers', 'of'),
    metric_tile('Servers under pressure', SRV_BASE + '| STATS metric_val = SUM(pressure), disk = SUM(CASE(silent == 0, hot_disk, 0))',
                AMBER, S1, 32, 13, 8, 6, 'warning', 'CPU p90, memory or a disk ≥ 90 %, last hour',
                'Reporting production servers with CPU p90, memory or their fullest disk at 90 % or more in the last hour. '
                'Under the number: how many because of a disk. Green at 0.', D7, SRV_IDX, 'disk', 'Disk'),
    metric_tile('Failed changes (7 days)', CHG_LATEST + f'| WHERE TO_DATETIME(end_at) >= NOW() - 7 days AND TO_DATETIME(end_at) <= NOW()\n'
                f'| STATS metric_val = COUNT_DISTINCT(CASE({FAILED}, number)), closed = COUNT_DISTINCT(number)',
                AMBER, S1, 40, 13, 8, 6, 'refresh', 'Failed or backed out, last 7 days',
                'Change requests that ended in the last 7 days with a close code saying unsuccessful, failed or backed out. '
                'Under the number: all changes that ended. Green at 0.', D30, CHG_IDX, 'closed', 'of'),
]

# ---------------- 2 · What needs attention now ----------------
inc_table_q = INC_BASE + """| WHERE pri == 1 OR age_minutes > 480
| STATS opened = MAX(TO_DATETIME(opened_at)), grp = VALUES(TO_STRING(assignment_group.name)),
        assignees = VALUES(TO_STRING(assigned_to.name)), descr = VALUES(TO_STRING(short_description))
  BY domain, number, priority, ci.name, state_name
| EVAL assignment_group = COALESCE(MV_FIRST(grp), "—"), assignee = COALESCE(MV_FIRST(assignees), "—"),
       short_description = COALESCE(MV_FIRST(descr), "—"), d_rank = CASE(domain IN ("Unknown", "Other"), 2, 1)
| SORT priority ASC, d_rank ASC, opened ASC
| KEEP domain, number, priority, ci.name, state_name, opened, assignment_group, assignee, short_description"""
mim_dd = {'label': 'Open the MIM dashboard (pick this CI there) — use on the CI column', 'encode_url': False,
          'open_in_new_tab': True, 'trigger': 'on_click_value', 'type': 'url_drilldown', 'url': LINKS['MIM']}
panels.append(table(
    'Active P1 · P2 over 8 h on infrastructure', inc_table_q,
    [('domain', 'Domain', S, 95, None), ('number', 'Incident', S, 105, None), ('priority', 'Pri', N, 45, dict(PRI_BADGE, alignment='center')),
     ('ci.name', 'CI', S, 140, None), ('state_name', 'State', S, 90, None), ('opened', 'Opened', D, 140, None),
     ('assignment_group', 'Assignment group', S, 160, None), ('assignee', 'Assignee', S, 120, None),
     ('short_description', 'Description', S, 300, None)],
    S2, 0, 0, 26, 11,
    'Active P1 incidents, and P2 incidents open longer than 8 h (MIM\'s rule), whose CI is infrastructure, with the '
    'domain from its CMDB class. Unknown = the CI has no class; Other = a class not mapped to a domain yet. Click the '
    'incident or the CI to open it in ServiceNow, or open MIM to investigate it.', D30, SN_IDX,
    drilldowns=SN_DRILLDOWNS + [mim_dd]))

bar_q = ALERTS_BASE + '| STATS n = COUNT(*) BY domain, severity_label, sev_rank'
bar_spec = dict(VEGA, data=[
    esql('raw', bar_q),
    {'name': 'doms', 'values': [{'domain': d, 'label': f'{ICON[d]} {d}', 'o': i} for i, d in enumerate(DOMAINS)]},
    {'name': 'stack', 'source': 'raw', 'transform': [
        {'type': 'filter', 'expr': "indexof(['Server','Database','Middleware','VMware','Cloud','Network'], datum.domain) >= 0"},
        {'type': 'lookup', 'from': 'doms', 'key': 'domain', 'fields': ['domain'], 'values': ['label', 'o']},
        {'type': 'stack', 'groupby': ['domain'], 'field': 'n', 'sort': {'field': 'sev_rank', 'order': 'descending'}}]}],
    scales=[{'name': 'y', 'type': 'band', 'domain': {'data': 'doms', 'field': 'label', 'sort': {'field': 'o', 'op': 'min'}},
             'range': 'height', 'padding': 0.3},
            {'name': 'x', 'type': 'linear', 'domain': {'data': 'stack', 'field': 'y1'}, 'range': 'width', 'nice': True, 'zero': True},
            {'name': 'c', 'type': 'ordinal', 'domain': ['Critical', 'Major', 'Minor'], 'range': [RED, AMBER, BLUE]}],
    axes=[{'orient': 'left', 'scale': 'y', 'ticks': False, 'domain': False, 'labelFontSize': 12, 'labelPadding': 6},
          {'orient': 'bottom', 'scale': 'x', 'grid': True, 'tickCount': 5, 'labelFontSize': 10, 'domain': False}],
    legends=[{'fill': 'c', 'orient': 'top', 'direction': 'horizontal', 'labelFontSize': 11, 'symbolType': 'square'}],
    marks=[{'type': 'rect', 'from': {'data': 'stack'}, 'encode': {'update': {
        'y': {'scale': 'y', 'field': 'label'}, 'height': {'scale': 'y', 'band': 1},
        'x': {'scale': 'x', 'field': 'y0'}, 'x2': {'scale': 'x', 'field': 'y1'}, 'fill': {'scale': 'c', 'field': 'severity_label'},
        'tooltip': {'signal': "datum.label + ': ' + datum.n + ' ' + datum.severity_label"}}}},
        {'type': 'text', 'from': {'data': 'doms'}, 'encode': {'update': {
            'y': {'scale': 'y', 'field': 'label', 'band': 0.5}, 'x': {'value': 6}, 'baseline': {'value': 'middle'},
            'text': {'value': ''}, 'fontSize': {'value': 11}}},
         'style': 'guide-label'}])
panels.append(vega('Open infrastructure alerts by domain', bar_spec, S2, 26, 0, 22, 11,
                   'Open alerts by domain and severity: Netcool alerts open in the last 24 h on production CIs, and active '
                   'Elastic paladin-* alerts. Critical = Netcool 5 or Elastic critical; Major = Netcool 4 or Elastic '
                   'major / high (or no severity); Minor = the rest. Domain from the CI\'s CMDB class (Netcool alerts on a '
                   'node with no CMDB CI count as Network) or, for Elastic, from the rule.', D7))

top_q = ALERTS_BASE + """| EVAL open_minutes = DATE_DIFF("minutes", started, NOW())
| EVAL _d = open_minutes / 1440, _h = (open_minutes % 1440) / 60, _m = open_minutes % 60
| EVAL open_for = CASE(_d > 0, CONCAT(TO_STRING(_d), " d ", TO_STRING(_h), " h"),
                       _h > 0, CONCAT(TO_STRING(_h), " h ", TO_STRING(_m), " min"), CONCAT(TO_STRING(_m), " min"))
| SORT sev_rank DESC, started ASC
| LIMIT 200
| KEEP domain, severity_label, ci, summary, source, open_for, started"""
panels.append(table(
    'Top open alerts', top_q,
    [('domain', 'Domain', S, 95, None), ('severity_label', 'Severity', S, 85, dict(SEV_BADGE, alignment='center')),
     ('ci', 'CI', S, 160, None), ('summary', 'Alert', S, 520, None), ('source', 'Source', S, 80, None),
     ('open_for', 'Open for', S, 100, {'alignment': 'right'}), ('started', 'Started', D, 150, None)],
    S2, 0, 11, 48, 11,
    'Every open infrastructure alert, Critical first, oldest first: Netcool (open in the last 24 h, production) and '
    'Elastic (active paladin-* rules). The CI column opens the CI in the ServiceNow CMDB. Investigate a CI in MIM.',
    D7, AL_IDX, drilldowns=[SN_DRILLDOWNS[1]] if len(SN_DRILLDOWNS) > 1 else None))

# ---------------- 3 · Changes and trend ----------------
# Change Request Summary: the Portfolio v4 panel (four cards), rebuilt on ES|QL so each change counts once (its latest
# record), on infrastructure CIs (and changes with no CI class), with a list of those changes beside it.
CHG_SCOPED = CHG_LATEST + f"""| EVAL domain = {DOMAIN('TO_STRING(ci.class_name)')},
       st = TO_STRING(state_name), ty = TO_LOWER(COALESCE(TO_STRING(type.normalized), "")),
       cl = TO_DATETIME(closed_at), sd = TO_DATETIME(start_date), ed = TO_DATETIME(end_at),
       cc = TO_LOWER(COALESCE(TO_STRING(close_code), ""))
| WHERE {INFRA}
| EVAL is_open = st NOT IN ("Closed", "Canceled", "Cancelled"),
       is_pending = st IN ("Assess", "Authorize"),
       is_sched = st == "Scheduled" AND sd >= NOW() AND sd < NOW() + 7 days,
       is_impl = st == "Closed" AND cc != "canceled" AND cl >= NOW() - 7 days AND cl <= NOW(),
       is_impl_prev = st == "Closed" AND cc != "canceled" AND cl >= NOW() - 14 days AND cl < NOW() - 7 days,
       is_running = st NOT IN ("Closed", "Canceled", "Cancelled") AND sd <= NOW() AND (ed IS NULL OR ed >= NOW())
"""
sum_q = CHG_SCOPED + """| STATS open = COUNT_DISTINCT(CASE(is_open, number)),
        normal = COUNT_DISTINCT(CASE(is_open AND ty LIKE "*normal*", number)),
        standard = COUNT_DISTINCT(CASE(is_open AND ty LIKE "*standard*", number)),
        emergency = COUNT_DISTINCT(CASE(is_open AND ty LIKE "*emergency*", number)),
        implemented = COUNT_DISTINCT(CASE(is_impl, number)), implemented_prev = COUNT_DISTINCT(CASE(is_impl_prev, number)),
        pending = COUNT_DISTINCT(CASE(is_pending, number)), scheduled = COUNT_DISTINCT(CASE(is_sched, number))"""


def card(i, icon, value, label, sub, sub_colour, stroke):
    """One of the four cards, in a 2 x 2 grid that fills the panel (Portfolio's layout, sized to the panel)."""
    x = 'cw * ' + str(i % 2) + ' + 4'
    y = 'ch * ' + str(i // 2) + ' + 4'
    return {'type': 'group', 'encode': {'update': {
        'x': {'signal': x}, 'y': {'signal': y}, 'width': {'signal': 'cw - 8'}, 'height': {'signal': 'ch - 8'},
        'cornerRadius': {'value': 8}, 'stroke': {'value': stroke}, 'strokeWidth': {'value': 1.5},
        'fill': {'value': stroke}, 'fillOpacity': {'value': 0.06}}},
        'marks': [
            txt({'value': 14}, {'signal': '(ch - 8) / 2'}, {'value': icon}, 34),
            txt({'value': 64}, {'signal': '(ch - 8) / 2 - 18'}, {'signal': value}, 24, 'bold', style='guide-title'),
            txt({'value': 64}, {'signal': '(ch - 8) / 2 + 4'}, {'value': label}, 12, style='guide-label'),
            dict(txt({'value': 64}, {'signal': '(ch - 8) / 2 + 22'}, sub, 11, 'bold', sub_colour),
                 **{})]}


sum_spec = dict(VEGA, padding=2, data=[esql('stats', sum_q)],
    signals=[{'name': 's', 'update': "data('stats')[0] || {}"},
             {'name': 'cw', 'update': 'width / 2'}, {'name': 'ch', 'update': 'height / 2'},
             {'name': 'pct', 'update': "s.implemented_prev > 0 ? round((s.implemented - s.implemented_prev) / s.implemented_prev * 100) : 0"},
             {'name': 'arrow', 'update': "pct > 0 ? '▲' : pct < 0 ? '▼' : '■'"},
             {'name': 'pctColour', 'update': f"pct > 0 ? '{GREEN}' : pct < 0 ? '{RED}' : '{GREY}'"}],
    marks=[
        card(0, '📂', 's.open || 0', 'Open changes', {'signal': "'N: ' + (s.normal || 0) + '   S: ' + (s.standard || 0) + '   E: ' + (s.emergency || 0)"},
             {'signal': "(s.emergency || 0) > 0 ? '" + RED + "' : '#3b82f6'"}, '#244a78'),
        card(1, '✅', 's.implemented || 0', 'Implemented this week',
             {'signal': "arrow + ' ' + abs(pct) + '% vs previous week (' + (s.implemented_prev || 0) + ')'"}, {'signal': 'pctColour'}, '#1d5c3d'),
        card(2, '⏳', 's.pending || 0', 'Pending approval', {'signal': "(s.pending || 0) > 0 ? 'Action required (Assess, Authorize)' : 'Nothing waiting'"},
             {'value': AMBER}, '#7a5515'),
        card(3, '📅', 's.scheduled || 0', 'Scheduled next 7 days', {'value': 'Forward looking'}, {'value': '#8b5cf6'}, '#5840a5')])
panels.append(vega('Change Request Summary', sum_spec, S3, 0, 0, 18, 12,
                   'Like Portfolio v4\'s Change Request Summary, for infrastructure: each change counted once (its latest '
                   'record, updated in the last 30 days), on infrastructure CIs or with no CI class (most changes have none). '
                   'Open = not Closed or Canceled, by type (N normal, S standard, E emergency). Implemented this week = '
                   'Closed (not canceled) in the last 7 days, against the 7 days before. Pending approval = Assess or '
                   'Authorize. Scheduled next 7 days = Scheduled and starting within 7 days. The list beside it shows the '
                   'changes.', D30))

list_q = CHG_SCOPED + """| WHERE is_open OR is_impl
| EVAL status = CASE(is_running, "In progress", is_pending, "Pending approval", is_sched, "Scheduled (7 d)",
                     is_impl, "Implemented this week", "Open"),
       s_rank = CASE(status == "In progress", 1, status == "Pending approval", 2, status == "Scheduled (7 d)", 3,
                     status == "Open", 4, 5),
       change_type = CASE(ty LIKE "*emergency*", "Emergency", ty LIKE "*standard*", "Standard", ty LIKE "*normal*", "Normal", "—")
| SORT s_rank ASC, sd ASC
| LIMIT 500
| KEEP status, number, change_type, state_name, domain, ci.name, start_date, end_at, assignment_group.name"""
panels.append(table(
    'Change requests', list_q,
    [('status', 'Status', S, 175, badge([('In progress', AMBER), ('Pending approval', '#d95926'), ('Scheduled (7 d)', '#8b5cf6'),
                                         ('Open', '#3b82f6'), ('Implemented this week', GREEN)])),
     ('number', 'Change', S, 105, None), ('change_type', 'Type', S, 105, badge([('Emergency', RED), ('Standard', GREEN), ('Normal', '#3b82f6')])),
     ('state_name', 'State', S, 85, None), ('domain', 'Domain', S, 85, None), ('ci.name', 'CI', S, 150, None),
     ('start_date', 'Planned start', D, 140, None), ('end_at', 'Planned end', D, 140, None),
     ('assignment_group.name', 'Assignment group', S, 160, None)],
    S3, 18, 0, 30, 12,
    'The changes behind the Change Request Summary: open changes (in progress first, then pending approval, scheduled '
    'within 7 days, other open) and those implemented this week. Same scope as the summary.', D30, CHG_IDX))

trend_q = f"""FROM servicenow-incidents-*
| WHERE TO_STRING(number) LIKE "INC*" AND opened_at >= NOW() - 30 days
| EVAL domain = {DOMAIN('TO_STRING(ci.class_name)')}
| WHERE domain IN ("Server", "Database", "Middleware", "VMware", "Cloud", "Network")
| STATS n = COUNT_DISTINCT(number) BY day = DATE_TRUNC(1 day, TO_DATETIME(opened_at)), domain"""
DCOL = {'Server': '#6092c0', 'Database': '#9170b8', 'Middleware': '#b9a888', 'VMware': '#ca8eae', 'Cloud': '#54b399',
        'Network': '#d6bf57'}
trend_spec = dict(VEGA, data=[
    esql('raw', trend_q),
    {'name': 'stack', 'source': 'raw', 'transform': [
        {'type': 'formula', 'as': 't', 'expr': 'toDate(datum.day)'},
        {'type': 'stack', 'groupby': ['day'], 'field': 'n', 'sort': {'field': 'domain'}}]}],
    scales=[{'name': 'x', 'type': 'band', 'domain': {'data': 'stack', 'field': 't', 'sort': True}, 'range': 'width', 'padding': 0.2},
            {'name': 'xt', 'type': 'time', 'domain': {'data': 'stack', 'field': 't'}, 'range': 'width'},
            {'name': 'y', 'type': 'linear', 'domain': {'data': 'stack', 'field': 'y1'}, 'range': 'height', 'nice': True, 'zero': True},
            {'name': 'c', 'type': 'ordinal', 'domain': list(DCOL), 'range': list(DCOL.values())}],
    axes=[{'orient': 'bottom', 'scale': 'xt', 'tickCount': 5, 'format': '%d %b', 'labelFontSize': 10, 'domain': False},
          {'orient': 'left', 'scale': 'y', 'grid': True, 'tickCount': 4, 'labelFontSize': 10, 'domain': False}],
    legends=[{'fill': 'c', 'orient': 'top', 'direction': 'horizontal', 'labelFontSize': 11, 'symbolType': 'square'}],
    marks=[{'type': 'rect', 'from': {'data': 'stack'}, 'encode': {'update': {
        'x': {'scale': 'x', 'field': 't'}, 'width': {'scale': 'x', 'band': 1},
        'y': {'scale': 'y', 'field': 'y1'}, 'y2': {'scale': 'y', 'field': 'y0'}, 'fill': {'scale': 'c', 'field': 'domain'},
        'tooltip': {'signal': "timeFormat(datum.t, '%d %b') + ' · ' + datum.domain + ': ' + datum.n"}}}}])
panels.append(vega('Infrastructure incidents per day', trend_spec, S3, 0, 12, 48, 9,
                   'Incidents (every priority) opened per day in the last 30 days on infrastructure CIs, by domain from the '
                   'CI\'s CMDB class. Shows whether a domain is getting better or worse.', D30))

# ---------------- 4 · Detailed dashboards ----------------
# two lists side by side (team layout, 11 Nov): the technology dashboards on the left, the related ones on the right
LEFT = [('Server Infra Dashboard', 'Server', '🖥️'), ('Database Infra Dashboard', 'Database', '🗄️'),
        ('Middleware Dashboard', 'Middleware', '⚙️'), ('Cloud Infra Dashboard', 'Cloud', '☁️')]
RIGHT = [('Applications Operations Dashboard', 'Applications', '🩺'), ('VMware Infra Dashboard', 'VMware', '🧱'),
         ('Portfolio Dashboard', 'Portfolio', '💼'), ('MIM Dashboard', 'MIM', '🚨')]
for x, items in ((0, LEFT), (24, RIGHT)):
    for k, (name, key, icon) in enumerate(items):
        panels.append(markdown(f'{key} detailed dashboard', f'## {icon} [{name} ›]({LINKS[key]})', S4, x, k * 2, 24, 2))

SOURCES = [('incidents', 'ServiceNow incidents', 'servicenow-incidents'), ('changes', 'ServiceNow changes', 'servicenow-change-requests'),
           ('netcool', 'Netcool alerts', 'netcool'), ('elastic', 'Elastic alerts', 'alerts-observability'),
           ('metrics', 'Server metrics', 'metrics-system'), ('gke', 'GKE metrics', 'metrics-gcp'),
           ('cmdb', 'CMDB relations', 'cmdb-ci-relations')]
fresh_q = ('FROM servicenow-incidents-*, servicenow-change-requests-*, .ds-bridge-alerts-netcool-default-*, .alerts-observability.*, '
           '.ds-metrics-system.cpu-default*, metrics-gcp.gke-*, cmdb-ci-relations* METADATA _index\n'
           '| WHERE @timestamp >= NOW() - 2 days AND @timestamp <= NOW() + 5 minutes\n'
           '| EVAL src = CASE(' + ', '.join(f'_index LIKE "*{pat}*", "{k}"' for k, _, pat in SOURCES) + ', "other")\n'
           '| STATS last_data = MAX(@timestamp) BY src\n| EVAL minutes = DATE_DIFF("minutes", last_data, NOW())')
fresh_spec = dict(VEGA, padding=0, data=[
    esql('raw', fresh_q),
    {'name': 'src', 'values': [{'src': k, 'label': l, 'i': i} for i, (k, l, _) in enumerate(SOURCES)], 'transform': [
        {'type': 'lookup', 'from': 'raw', 'key': 'src', 'fields': ['src'], 'values': ['minutes'], 'default': None},
        {'type': 'formula', 'as': 'colour', 'expr':
            f"datum.minutes == null ? '{RED}' : datum.minutes <= 30 ? '{GREEN}' : datum.minutes <= 120 ? '{AMBER}' : '{RED}'"},
        {'type': 'formula', 'as': 'ago', 'expr':
            "datum.minutes == null ? 'no data in 2 days' : datum.minutes < 60 ? (datum.minutes + ' min ago') : "
            "datum.minutes < 2880 ? (floor(datum.minutes / 60) + ' h ago') : (floor(datum.minutes / 1440) + ' d ago')"}]}],
    signals=[{'name': 'cw', 'update': f'width / {len(SOURCES)}'}],
    marks=[txt({'value': 4}, {'value': 12}, {'value': 'Data freshness: when each source last delivered (green ≤ 30 min, amber ≤ 2 h)'},
               13, 'bold', style='guide-title'),
           {'type': 'symbol', 'from': {'data': 'src'}, 'encode': {'update': {
               'x': {'signal': 'datum.i * cw + 10'}, 'y': {'value': 40}, 'size': {'value': 90}, 'shape': {'value': 'circle'},
               'fill': {'field': 'colour'}}}},
           {'type': 'text', 'from': {'data': 'src'}, 'style': 'guide-label', 'encode': {'update': {
               'x': {'signal': 'datum.i * cw + 20'}, 'y': {'value': 34}, 'text': {'field': 'label'}, 'fontSize': {'value': 12},
               'fontWeight': {'value': 'bold'}, 'baseline': {'value': 'middle'}, 'limit': {'signal': 'cw - 24'}}}},
           {'type': 'text', 'from': {'data': 'src'}, 'style': 'guide-label', 'encode': {'update': {
               'x': {'signal': 'datum.i * cw + 20'}, 'y': {'value': 50}, 'text': {'field': 'ago'}, 'fontSize': {'value': 11},
               'baseline': {'value': 'middle'}, 'fill': {'field': 'colour'}}}}])
panels.append(vega('Data freshness', fresh_spec, S4, 0, 8, 48, 5,
                   'When each source last delivered data. If a feed stops, the tiles that read it are wrong: green ≤ 30 min, '
                   'amber ≤ 2 h, red older or nothing in 2 days.', {'from': 'now-2d', 'to': 'now'}))

ids = [p['panelIndex'] for p in panels]
assert len(ids) == len(set(ids))

dash = {
    'type': 'dashboard', 'id': DASH_ID, 'managed': False, 'references': [],
    'coreMigrationVersion': mim.get('coreMigrationVersion'), 'typeMigrationVersion': mim.get('typeMigrationVersion'),
    'attributes': {
        'title': 'Infrastructure Overview',
        'description': ('Landing page for the infrastructure dashboards: the status of each domain (Server, Database, '
                        'Middleware, VMware, Cloud, Network) from its incidents, alerts and health, what needs attention '
                        'now, changes and trend, and links to each domain\'s detailed dashboard. No control to pick. '
                        '(INFRA-OVERVIEW-KPIS.md)'),
        'esqlApproximation': False,
        'kibanaSavedObjectMeta': mim['attributes']['kibanaSavedObjectMeta'],
        'optionsJSON': mim['attributes']['optionsJSON'],
        'refreshInterval': {'pause': False, 'value': 300000},
        'timeRestore': True, 'timeFrom': 'now-24h', 'timeTo': 'now',
        'pinned_panels': {'panels': {}},
        'sections': [
            {'collapsed': False, 'gridData': {'i': S1, 'y': 0}, 'title': '🧭 1 · Infrastructure status'},
            {'collapsed': False, 'gridData': {'i': S2, 'y': 1}, 'title': '🚨 2 · What needs attention now'},
            {'collapsed': False, 'gridData': {'i': S3, 'y': 2}, 'title': '🔄 3 · Changes and trend'},
            {'collapsed': False, 'gridData': {'i': S4, 'y': 3}, 'title': '🔗 4 · Detailed dashboards'},
        ],
        'panelsJSON': json.dumps(panels, ensure_ascii=False),
    },
}
for k in ('coreMigrationVersion', 'typeMigrationVersion'):
    if dash[k] is None:
        del dash[k]
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: {len(panels)} panels, id {DASH_ID}')
