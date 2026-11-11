"""Test the Infrastructure Overview against a local Elasticsearch (port 9200) with its own data.

Usage: test_infra_overview_2026-11-10.py "Infrastructure Overview.ndjson"
Removes every index matching the dashboard's sources first (local test cluster only), loads a small estate, runs
every ES|QL query (Lens and Vega) and checks the tiles, tables and domain counts. Removes its data at the end.
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

NOW = datetime.now(timezone.utc)
iso = lambda **kw: (NOW + timedelta(**kw)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
ago = lambda **kw: (NOW - timedelta(**kw)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request('http://localhost:9200' + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b'{}')


PATTERNS = ('servicenow-', '.ds-bridge-alerts-netcool', 'bridge-alerts-netcool', '.alerts-observability', '.ds-metrics-system',
            'metrics-system', 'metrics-gcp.gke', '.ds-metrics-gcp.gke', 'cmdb-ci-relations')


def cleanup():
    for ds in call('GET', '/_data_stream/*?expand_wildcards=all').get('data_streams', []):
        if ds['name'].startswith(PATTERNS):
            call('DELETE', f'/_data_stream/{ds["name"]}')
    for row in call('GET', '/_cat/indices?format=json&h=index&expand_wildcards=all') or []:
        if isinstance(row, dict) and row['index'].startswith(PATTERNS):
            call('DELETE', f'/{row["index"]}')


cleanup()
K, D, I, F, B = {'type': 'keyword'}, {'type': 'date'}, {'type': 'integer'}, {'type': 'double'}, {'type': 'boolean'}
obj = lambda **p: {'properties': p}
CI = obj(name=K, class_name=K, environment=K)
T = 't60'
IDX = {
    f'servicenow-incidents-{T}': {'@timestamp': D, 'number': K, 'priority': I, 'state_name': K, 'opened_at': D, 'ci': CI,
                                  'assignment_group': obj(name=K), 'assigned_to': obj(name=K), 'short_description': K},
    f'servicenow-change-requests-{T}': {'@timestamp': D, 'number': K, 'start_date': D, 'end_at': D, 'state_name': K,
                                        'close_code': K, 'closed_at': D, 'type': obj(normalized=K), 'ci': CI,
                                        'assignment_group': obj(name=K)},
    f'.ds-bridge-alerts-netcool-default-{T}': {'@timestamp': D, 'severity': I, 'message': K, 'node': K, 'first_occurrence': D,
                                                'netcool': obj(identifier=K, type_name=K), 'ci': CI},
    f'.alerts-observability.{T}': {'@timestamp': D, 'kibana': obj(alert=obj(status=K, severity=K, reason=K, start=D,
                                                                             rule=obj(name=K), instance=obj(id=K)))},
    f'.ds-metrics-system.cpu-default-{T}': {'@timestamp': D, 'host': obj(name=K), 'ci': CI, 'system': obj(cpu=obj(total=obj(norm=obj(pct=F))))},
    f'.ds-metrics-system.memory-default-{T}': {'@timestamp': D, 'host': obj(name=K), 'ci': CI, 'system': obj(memory=obj(actual=obj(used=obj(pct=F))))},
    f'.ds-metrics-system.filesystem-default-{T}': {'@timestamp': D, 'host': obj(name=K), 'ci': CI, 'system': obj(filesystem=obj(used=obj(pct=F)))},
    f'metrics-gcp.gke-{T}': {'@timestamp': D, 'cloud': obj(account=obj(id=K)), 'gcp': obj(
        labels_fingerprint=K, labels=obj(resource=obj(cluster_name=K, node_name=K), metrics=obj(memory_type=K)),
        gke=obj(node=obj(cpu=obj(allocatable_utilization=obj(pct=F)),
                         memory=obj(allocatable_utilization=obj(pct=F), used=obj(bytes={'type': 'long'}), allocatable=obj(bytes={'type': 'long'}))),
                container=obj(restart=obj(count={'type': 'long'}))))},
    f'cmdb-ci-relations-{T}': {'@timestamp': D, 'is_marked_for_deletion': B, 'parent': obj(name=K, **{'class': K}),
                               'child': obj(name=K, **{'class': K})},
}
# a plain index under metrics-* needs its own template (the built-in one makes data streams only)
call('PUT', f'/_index_template/{T}-gke', {'index_patterns': [f'metrics-gcp.gke-{T}'], 'priority': 900, 'template': {}})
for name, props in IDX.items():
    r = call('PUT', f'/{name}', {'mappings': {'properties': props}})
    assert r.get('acknowledged'), (name, r)

ci = lambda n, c, env='Production': {'name': n, 'class_name': c, 'environment': env}
inc = lambda n, p, s, c, cls, opened_h=2, ts_h=0.1: {'@timestamp': ago(hours=ts_h), 'number': n, 'priority': p, 'state_name': s,
                                                     'opened_at': ago(hours=opened_h), 'ci': ci(c, cls),
                                                     'assignment_group': {'name': 'Ops'}, 'assigned_to': {'name': 'Ann Lee'},
                                                     'short_description': f'{n} problem'}
docs = {
    f'servicenow-incidents-{T}': [
        inc('INC1', 1, 'New', 'srv1', 'Linux Server'),                          # Server, P1
        inc('INC2', 2, 'In Progress', 'db1', 'MSFT SQL Server Instance', 10),   # Database, P2 past 8 h
        inc('INC3', 2, 'New', 'sw1', 'IP Switch', 2),                           # Network, P2 under 8 h
        inc('INC4', 1, 'New', 'app1', 'Application Service'),                   # application: left out
        inc('INC5', 1, 'Resolved', 'srv2', 'Linux Server'),                     # resolved
        inc('INC6', 2, 'On Hold', 'srv2', 'Linux Server', 20),                  # On Hold
        inc('INC7', 3, 'New', 'srv2', 'Linux Server'),                          # P3
        inc('INC8', 1, 'New', 'srv3', 'Windows Server', 5, 3), inc('INC8', 1, 'Resolved', 'srv3', 'Windows Server', 5, 1),  # latest record resolved
        inc('INC9', 2, 'New', 'esx1', 'ESX Server', 12),                        # VMware, P2 past 8 h
    ],
    f'servicenow-change-requests-{T}': [
        {'@timestamp': ago(minutes=5), 'number': 'CHG1', 'type': {'normalized': 'normal'}, 'start_date': ago(hours=1), 'end_at': iso(hours=2), 'state_name': 'Implement', 'ci': ci('srv1', 'Linux Server'), 'assignment_group': {'name': 'Unix'}},
        {'@timestamp': ago(minutes=5), 'number': 'CHG2', 'type': {'normalized': 'standard'}, 'start_date': iso(hours=5), 'end_at': iso(hours=6), 'state_name': 'Scheduled', 'ci': ci('db1', 'MSFT SQL Server Instance'), 'assignment_group': {'name': 'DBA'}},
        {'@timestamp': ago(minutes=5), 'number': 'CHG3', 'type': {'normalized': 'emergency'}, 'start_date': iso(days=3), 'end_at': iso(days=3, hours=1), 'state_name': 'Scheduled', 'ci': ci('srv1', 'Linux Server'), 'assignment_group': {'name': 'Unix'}},
        {'@timestamp': ago(days=2), 'number': 'CHG4', 'type': {'normalized': 'normal'}, 'start_date': ago(days=2, hours=2), 'end_at': ago(days=2), 'state_name': 'Closed', 'close_code': 'unsuccessful', 'closed_at': ago(days=2), 'ci': ci('sw1', 'IP Switch'), 'assignment_group': {'name': 'Network'}},
        {'@timestamp': ago(days=1), 'number': 'CHG5', 'type': {'normalized': 'normal'}, 'start_date': ago(days=1, hours=2), 'end_at': ago(days=1), 'state_name': 'Closed', 'close_code': 'successful', 'closed_at': ago(days=1), 'ci': ci('srv1', 'Linux Server'), 'assignment_group': {'name': 'Unix'}},
        {'@timestamp': ago(minutes=5), 'number': 'CHG6', 'type': {'normalized': 'normal'}, 'start_date': ago(hours=1), 'end_at': iso(hours=1), 'state_name': 'Implement', 'ci': ci('app1', 'Application Service'), 'assignment_group': {'name': 'Apps'}},
        {'@timestamp': ago(minutes=5), 'number': 'CHG7', 'type': {'normalized': 'normal'}, 'state_name': 'Assess', 'ci': ci('sw1', 'IP Switch'), 'assignment_group': {'name': 'Network'}},     # pending approval
        {'@timestamp': ago(days=1), 'number': 'CHG8', 'type': {'normalized': 'standard'}, 'start_date': ago(days=1, hours=2), 'state_name': 'Closed', 'close_code': 'canceled', 'closed_at': ago(days=1), 'ci': ci('srv1', 'Linux Server'), 'assignment_group': {'name': 'Unix'}},  # canceled: not implemented
        {'@timestamp': ago(days=10), 'number': 'CHG9', 'type': {'normalized': 'normal'}, 'start_date': ago(days=10, hours=2), 'end_at': ago(days=10), 'state_name': 'Closed', 'close_code': 'successful', 'closed_at': ago(days=10), 'ci': ci('srv1', 'Linux Server'), 'assignment_group': {'name': 'Unix'}},  # previous week
    ],
    f'.ds-bridge-alerts-netcool-default-{T}': [
        {'@timestamp': ago(minutes=10), 'severity': 5, 'message': 'Interface down', 'node': 'sw1.cna.com', 'first_occurrence': ago(hours=2),
         'netcool': {'identifier': 'n1', 'type_name': 'problem'}, 'ci': ci('sw1', 'IP Switch')},
        {'@timestamp': ago(minutes=10), 'severity': 4, 'message': 'UPS on battery', 'node': 'ups9.cna.com', 'first_occurrence': ago(hours=1),
         'netcool': {'identifier': 'n2', 'type_name': 'problem'}},
        {'@timestamp': ago(minutes=10), 'severity': 3, 'message': 'DB slow', 'node': 'db1.cna.com', 'first_occurrence': ago(hours=1),
         'netcool': {'identifier': 'n3', 'type_name': 'problem'}, 'ci': ci('db1', 'MSFT SQL Server Instance')},
        {'@timestamp': ago(minutes=30), 'severity': 5, 'message': 'Link down', 'node': 'sw2.cna.com', 'first_occurrence': ago(hours=1),
         'netcool': {'identifier': 'n4', 'type_name': 'problem'}, 'ci': ci('sw2', 'IP Switch')},
        {'@timestamp': ago(minutes=5), 'severity': 0, 'message': 'Link up', 'node': 'sw2.cna.com', 'first_occurrence': ago(hours=1),
         'netcool': {'identifier': 'n4', 'type_name': 'resolution'}, 'ci': ci('sw2', 'IP Switch')},
        {'@timestamp': ago(minutes=10), 'severity': 5, 'message': 'Dev switch down', 'node': 'dsw.cna.com', 'first_occurrence': ago(hours=1),
         'netcool': {'identifier': 'n5', 'type_name': 'problem'}, 'ci': ci('dsw', 'IP Switch', 'Development')},
    ],
    f'.alerts-observability.{T}': [
        {'@timestamp': ago(minutes=2), 'kibana': {'alert': {'status': 'active', 'severity': 'critical', 'reason': 'Host srv1 down',
         'start': ago(minutes=40), 'rule': {'name': 'paladin-host-uptime-c30'}, 'instance': {'id': 'srv1'}}}},
        {'@timestamp': ago(minutes=2), 'kibana': {'alert': {'status': 'active', 'reason': 'Queue manager QM1 stopped',
         'start': ago(minutes=20), 'rule': {'name': 'paladin-ibm-mq-qmgr'}, 'instance': {'id': '8f9a97b01b9e0e1806943267cc4bcbbf,mq1,QM1'}}}},
        {'@timestamp': ago(minutes=2), 'kibana': {'alert': {'status': 'recovered', 'severity': 'critical', 'reason': 'ok',
         'start': ago(hours=3), 'rule': {'name': 'paladin-cpu-usage'}, 'instance': {'id': 'srv2'}}}},
        {'@timestamp': ago(minutes=2), 'kibana': {'alert': {'status': 'active', 'severity': 'critical', 'reason': 'not infra',
         'start': ago(hours=3), 'rule': {'name': 'apm-latency'}, 'instance': {'id': 'svc'}}}},
    ],
}
srv = lambda kind, host, field, val, minutes: {'@timestamp': ago(minutes=minutes), 'host': {'name': host}, 'ci': ci(host, 'Linux Server'),
                                               'system': {kind: field(val)}}
cpu = lambda v: {'total': {'norm': {'pct': v}}}
mem = lambda v: {'actual': {'used': {'pct': v}}}
fs = lambda v: {'used': {'pct': v}}
docs[f'.ds-metrics-system.cpu-default-{T}'] = [srv('cpu', 'srvA', cpu, 0.3, 2), srv('cpu', 'srvB', cpu, 0.2, 30), srv('cpu', 'srvC', cpu, 0.4, 2)]
docs[f'.ds-metrics-system.memory-default-{T}'] = [srv('memory', 'srvA', mem, 0.5, 2), srv('memory', 'srvC', mem, 0.6, 2)]
docs[f'.ds-metrics-system.filesystem-default-{T}'] = [srv('filesystem', 'srvA', fs, 0.95, 2), srv('filesystem', 'srvC', fs, 0.5, 2)]
docs[f'metrics-gcp.gke-{T}'] = [{'@timestamp': ago(minutes=3), 'cloud': {'account': {'id': 'p1'}}, 'gcp': {
    'labels': {'resource': {'cluster_name': 'g-prd-1', 'node_name': f'n{i}'}, 'metrics': {'memory_type': 'non-evictable'}},
    'gke': {'node': {'cpu': {'allocatable_utilization': {'pct': 0.4}},
                     'memory': {'used': {'bytes': 30}, 'allocatable': {'bytes': 100}}}}}} for i in (1, 2)]
docs[f'cmdb-ci-relations-{T}'] = [{'@timestamp': ago(minutes=20), 'is_marked_for_deletion': False,
                                   'parent': {'name': 'app1', 'class': 'cmdb_ci_service_auto'}, 'child': {'name': 'srv1', 'class': 'cmdb_ci_linux_server'}}]
body = ''.join(json.dumps({'index': {'_index': i}}) + '\n' + json.dumps(d) + '\n' for i, ds in docs.items() for d in ds)
r = call('POST', '/_bulk?refresh=true', body, nd=True)
assert not r.get('errors'), json.dumps([x for x in r['items'] if 'error' in list(x.values())[0]])[:800]

dash = json.loads([l for l in open(sys.argv[1]) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title')
P = {title(p): p for p in panels}
fails = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" + ('' if ok else f'\n          expected {want!r}'))
    if not ok:
        fails.append(name)


def esql(q):
    r = call('POST', '/_query?format=json', {'query': q})
    if 'error' in r:
        return r
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']]


def queries(p):
    ec = p['embeddableConfig']
    if p['type'] == 'vis':
        yield 'lens', ec['attributes']['state']['query']['esql']
    elif p['type'] == 'legacy_vis':
        for d in json.loads(ec['savedVis']['params']['spec']).get('data', []):
            if isinstance(d.get('url'), dict) and d['url'].get('%type%') == 'esql':
                yield d['name'], d['url']['query']


run = lambda t: esql(P[t]['embeddableConfig']['attributes']['state']['query']['esql'])
vq = lambda t, name: dict(queries(P[t]))[name]
try:
    print('Every query runs')
    n = 0
    for p in panels:
        for name, q in queries(p):
            n += 1
            r = esql(q)
            if isinstance(r, dict):
                check(f'{title(p)} / {name}', json.dumps(r['error'])[:400], 'no error')
    print(f'  ran {n} queries')
    check('no controls on the page', dash['attributes']['pinned_panels'], {'panels': {}})
    check('no control variables in any query', sorted(set(re.findall(r'\?([a-z_]+)', ''.join(q for p in panels for _, q in queries(p))))), [])

    print('Domain of every CMDB class seen in production (IO1, 11 Nov)')
    src = open(__file__.rsplit('/', 1)[0] + '/build_infra_overview.py').read()
    g = {}
    exec(re.search(r'def DOMAIN\(cls\):.*?\n\n\n', src, re.S).group(0), g)
    WANT = {'Network': ['IP Switch', 'UPS', 'Wireless Access Point', 'Network Appliance Hardware', 'Network Gear', 'IP Firewall',
                        'DNS Name', 'IP Router', 'F5 BIG-IP', 'Palo Alto Firewall Device', 'Storage Switch', 'Communication Device'],
            'Server': ['Linux Server', 'Windows Server', 'AIX Server', 'Mainframe LPAR', 'Hardware', 'Computer', 'IBM LPAR Instance',
                       'Storage Server', 'UNIX Cluster', 'Server', 'Windows Cluster Node', 'UNIX Cluster Node', 'HPUX Server'],
            'Database': ['MSFT SQL Instance', 'Oracle Database', 'Oracle Instance', 'Database', 'Database Instance',
                         'PostgreSQL Instance', 'MSSQL Cluster', 'Cloud DataBase'],
            'VMware': ['VMware Virtual Machine Instance', 'ESX Server'], 'Middleware': ['Tomcat WAR Inclusion'],
            'Application': ['Mapped Application Service', 'Batch Job', 'Tag-Based Application Service', 'Application Service',
                            'Calculated Application Service', 'Business Application', 'Service Instance', 'Business Service'],
            'Other': ['Infrastructure Service', 'Data Center', 'Printer'], 'Unknown': ['null', '']}
    allc = [c for cs in WANT.values() for c in cs]
    got = esql('ROW cls = [' + ', '.join(json.dumps(c) for c in allc) + ']\n| MV_EXPAND cls\n| EVAL domain = ' + g['DOMAIN']('cls'))
    got = {r['cls']: r['domain'] for r in got}
    check(f'{len(allc)} classes in their domain', sorted(c for c in allc if got.get(c) != next(d for d, cs in WANT.items() if c in cs)), [])

    print('Tiles')
    check('Active P1: INC1 only (application, resolved, latest-resolved left out)', run('Active P1 (infrastructure)')[0]['metric_val'], 1)
    check('P2 over 8 h: INC2 and INC9 (INC3 is 2 h old, INC6 On Hold)', run('P2 over 8 h (infrastructure)')[0]['metric_val'], 2)
    r = run('Critical alerts')[0]
    check('Critical alerts: Netcool sw1 + Elastic srv1; Major: UPS + MQ (no severity)', (r['metric_val'], r['major']), (2, 2))
    r = run('Servers not reporting')[0]
    check('Servers not reporting: srvB of 3', (r['metric_val'], r['servers']), (1, 3))
    r = run('Servers under pressure')[0]
    check('Servers under pressure: srvA (disk 95 %)', (r['metric_val'], r['disk']), (1, 1))
    r = run('Failed changes (7 days)')[0]
    check('Failed changes: CHG4 of 2 ended', (r['metric_val'], r['closed']), (1, 2))

    print('Domain status board (its queries)')
    inc_by = {r['domain']: (r['p1'], r['p2']) for r in esql(vq('Domain status', 'inc'))}
    check('incidents by domain', inc_by, {'Server': (1, 0), 'Database': (0, 1), 'Network': (0, 1), 'VMware': (0, 1)})
    al_by = {r['domain']: (r['critical'], r['major'], r['alerts']) for r in esql(vq('Domain status', 'al'))}
    check('alerts by domain (n4 resolved, n5 not production, recovered and non-paladin left out)', al_by,
          {'Network': (1, 1, 2), 'Database': (0, 0, 1), 'Server': (1, 0, 1), 'Middleware': (0, 1, 1)})
    s = esql(vq('Domain status', 'srv'))[0]
    check('servers', (s['servers'], s['silent'], s['pressure'], s['disk']), (3, 1, 1, 1))
    g = esql(vq('Domain status', 'gke'))[0]
    check('GKE clusters', (g['clusters'], g['gke_bad'], g['gke_warn']), (1, 0, 0))

    print('Section 2')
    rows = run('Active P1 · P2 over 8 h on infrastructure')
    check('incidents table: P1 first, then oldest, with domain', [(r['number'], r['domain']) for r in rows],
          [('INC1', 'Server'), ('INC9', 'VMware'), ('INC2', 'Database')])   # P1 first, then oldest first
    check('incident drill-downs: ServiceNow incident, CMDB CI, MIM',
          [d['url'].split('/')[2] + ('/r/s/' + d['url'].rsplit('/', 1)[1] if 'kibana' in d['url'] else '') for d in P['Active P1 · P2 over 8 h on infrastructure']['embeddableConfig']['drilldowns']],
          ['cnaprod.service-now.com', 'cnaprod.service-now.com',
           'kibana-prod.gcp.cna.com/r/s/ZSMtk'])
    rows = run('Top open alerts')
    check('top alerts: Critical first', [(r['severity_label'], r['ci'], r['source']) for r in rows],
          [('Critical', 'sw1', 'Netcool'), ('Critical', 'srv1', 'Elastic'), ('Major', 'ups9.cna.com', 'Netcool'),
           ('Major', 'mq1', 'Elastic'), ('Minor', 'db1', 'Netcool')])
    bar = {(r['domain'], r['severity_label']): r['n'] for r in esql(vq('Open infrastructure alerts by domain', 'raw'))}
    check('alerts bar = Top open alerts rows', sum(bar.values()), len(rows))

    print('Section 3')
    s = esql(vq('Change Request Summary', 'stats'))[0]
    check('Change Request Summary: open (N / S / E), implemented this week vs before, pending, scheduled 7 d',
          {k: s[k] for k in ('open', 'normal', 'standard', 'emergency', 'implemented', 'implemented_prev', 'pending', 'scheduled')},
          {'open': 4, 'normal': 2, 'standard': 1, 'emergency': 1, 'implemented': 2, 'implemented_prev': 1, 'pending': 1, 'scheduled': 2})
    rows = run('Change requests')
    check('Change requests list: in progress, pending, scheduled, implemented; application change and canceled left out',
          [(r['status'], r['number'], r['change_type']) for r in rows],
          [('In progress', 'CHG1', 'Normal'), ('Pending approval', 'CHG7', 'Normal'), ('Scheduled (7 d)', 'CHG2', 'Standard'),
           ('Scheduled (7 d)', 'CHG3', 'Emergency'), ('Implemented this week', 'CHG4', 'Normal'), ('Implemented this week', 'CHG5', 'Normal')])
    check('summary and list side by side', [(P[x]['gridData']['x'], P[x]['gridData']['y'], P[x]['gridData']['w'])
                                           for x in ('Change Request Summary', 'Change requests')], [(0, 0, 18), (18, 0, 30)])
    trend = {}
    for r in esql(vq('Infrastructure incidents per day', 'raw')):   # summed over days: the test incidents can span midnight
        trend[r['domain']] = trend.get(r['domain'], 0) + r['n']
    check('incidents per day (every priority, infrastructure only)', trend, {'Server': 5, 'Database': 1, 'Network': 1, 'VMware': 1})

    print('Section 4')
    links = sorted(re.search(r'\((https://[^)]+)\)', title_p['embeddableConfig']['content']).group(1)
                   for title_p in panels if title_p['type'] == 'markdown' and ' ›](' in title_p['embeddableConfig']['content'])
    check('links: 5 domains under the tiles + 7 in section 4', len(links), 12)
    fr = {r['src']: r['minutes'] for r in esql(vq('Data freshness', 'raw'))}
    check('freshness: every source found', sorted(fr), sorted(['incidents', 'changes', 'netcool', 'elastic', 'metrics', 'gke', 'cmdb']))
    secs = [s['title'] for s in dash['attributes']['sections']]
    check('sections', secs, ['🧭 1 · Infrastructure status', '🚨 2 · What needs attention now', '🔄 3 · Changes and trend',
                             '🔗 4 · Detailed dashboards'])
    check('same id as the Infrastructure Dashboard', dash['id'], '0ed4078f-ae6c-5721-b852-20f0cf4d7a33')
finally:
    if '--keep' not in sys.argv:
        cleanup()
        call('DELETE', f'/_index_template/{T}-gke')

print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
