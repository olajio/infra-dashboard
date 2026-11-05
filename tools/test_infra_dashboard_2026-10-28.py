"""Check the Infrastructure Dashboard (28 Oct 2026): every query runs with the CI control picked or not, and the
panels for a server CI show its incidents, changes, alerts, health and applications.

Usage: test_infra_dashboard_2026-10-28.py "Infrastructure Dashboard.ndjson"
(local Elasticsearch on port 9200; loads the data of the MIM V3 tests -15, -16j, -18k and -27s plus its own, and
removes it all at the end)
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

HERE = __file__.rsplit('/', 1)[0]
SETUPS = ['test_mim_v3_2026-10-15.py', 'test_mim_v3_2026-10-16j.py', 'test_mim_v3_2026-10-18k.py',
          'test_mim_v3_2026-10-27s.py']
ES = 'http://localhost:9200'
NOW = datetime.now(timezone.utc)
ago = lambda **kw: (NOW - timedelta(**kw)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
K, D = {'type': 'keyword'}, {'type': 'date'}
obj = lambda **p: {'properties': p}
INC, CHG = 'servicenow-incidents-t28', 'servicenow-change-requests-t28'
ALERTS = '.alerts-observability.t28'


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request(ES + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return {'error': json.loads(e.read())}


def cleanup():
    for pat in ('*-t15*', '*-test*', '*-t16j*', '*-t18k*', '*-t27s*', '*-t28*', '*-t30*'):
        for ds in (call('GET', f'/_data_stream/{pat}').get('data_streams') or []):
            call('DELETE', f'/_data_stream/{ds["name"]}')
        got = call('GET', f'/_cat/indices/{pat}?format=json&h=index&expand_wildcards=all')
        for i in got if isinstance(got, list) else []:
            call('DELETE', f'/{i["index"]}')
    for t in ('apm-tx-test', 't30-gke'):
        call('DELETE', f'/_index_template/{t}')
    call('DELETE', '/cmdb_with_apm_flag')
    call('DELETE', f'/{ALERTS}')


cleanup()
for name in SETUPS:   # each MIM test's data setup: everything before it reads the dashboard
    src = open(f'{HERE}/{name}').read().split('dash = json.loads')[0]
    exec(compile(src, name, 'exec'), {'__name__': 'setup', '__file__': f'{HERE}/{name}'})

call('PUT', f'/{INC}', {'mappings': {'properties': {
    '@timestamp': D, 'number': K, 'priority': {'type': 'integer'}, 'state_name': K, 'opened_at': D,
    'short_description': K, 'ci': obj(name=K, class_name=K, environment=K, support_group=obj(l2=obj(name=K))),
    'assigned_to': obj(name=K, email=K), 'assignment_group': obj(name=K, manager=obj(name=K, email=K))}}})
call('PUT', f'/{CHG}', {'mappings': {'properties': {
    '@timestamp': D, 'number': K, 'ci': obj(name=K), 'start_date': D, 'end_at': D, 'opened_at': D, 'close_code': K,
    'state_name': K, 'type': obj(normalized=K), 'category': obj(**{'1': K}), 'assignment_group': obj(name=K)}}})
TXT = {'type': 'text', 'fields': {'keyword': {'type': 'keyword'}}}
call('PUT', '/cmdb_with_apm_flag', {'mappings': {'properties': {   # telemetry onboarding list read by Application Health (29 Oct)
    '@timestamp': D, 'name': TXT, 'number': TXT, 'install_status': TXT, 'operational_status': TXT, 'is_monitored': {'type': 'boolean'},
    'support_group': obj(l2=obj(name=TXT))}}})
# the applications MIM escalates (3 Nov, patch 03w): In Production + Operational + monitored; Payment Hub is not monitored
flag = lambda name, mon=True: {'@timestamp': ago(hours=6), 'name': name, 'number': 'APM-' + name[:3], 'is_monitored': mon,
                               'install_status': 'In Production', 'operational_status': 'Operational'}
assert not call('POST', '/_bulk?refresh=true', ''.join(json.dumps({'index': {'_index': 'cmdb_with_apm_flag'}}) + '\n' + json.dumps(d) + '\n'
                for d in (flag('Juno'), flag('Automated Claim Transaction'), flag('Payment Hub', mon=False))), nd=True).get('errors')
# Elastic Observability alerts, shaped like round17b.txt: the server is inside kibana.alert.instance.id
call('PUT', f'/{ALERTS}', {'mappings': {'properties': {'@timestamp': D, 'kibana': obj(alert=obj(
    instance=obj(id=K), status=K, severity=K, reason=K, start=D, rule=obj(name=K)))}}})


def alert(instance, rule, status, sev='critical'):
    return {'@timestamp': ago(minutes=5), 'kibana': {'alert': {'instance': {'id': instance}, 'status': status, 'severity': sev,
            'reason': f'{rule} on {instance[:40]}', 'start': ago(hours=2), 'rule': {'name': rule}}}}


alerts = [alert('07b5c934db72c300643cb96c4e96193e,srva,paladin-host-uptime-c30:5ef1', 'paladin-host-uptime-c30', 'active'),
          alert('d5c8de2adbce8300643cb96c4e961943#srva#78a52700', 'paladin-cpu-usage-high_prio-ml', 'recovered', 'minor'),
          alert('srva', 'paladin-genrocketexception-c3', 'active', 'warning'),
          alert('8f9a97b01b9e0e1806943267cc4bcbbf,srvz,/var/log,paladin-filesystem-usage-w90_c95:c66', 'paladin-filesystem-usage', 'active'),
          alert('srva-other,paladin-host-uptime-c30:1', 'paladin-host-uptime-c30', 'active'),           # another CI's name starts the same
          alert('rst-batch_request_apm-tx-latency-and-errors-prod_0', 'APM Alerts prd1', 'active')]       # not an infrastructure rule
assert not call('POST', '/_bulk?refresh=true', ''.join(json.dumps({'index': {'_index': ALERTS}}) + '\n' + json.dumps(a) + '\n'
                                                        for a in alerts), nd=True).get('errors')

# GKE metrics, shaped like round17c.txt (Cloud health · GKE, 2 Nov), and CMDB links to Kubernetes clusters
GKE, REL30 = 'metrics-gcp.gke-t30', 'cmdb-ci-relations-t30'


# a time-series data stream, as in production: restart.count is a counter (round20.txt, CG6)
DIM = {'type': 'keyword', 'time_series_dimension': True}
call('DELETE', '/_index_template/t30-gke')
assert 'error' not in call('PUT', '/_index_template/t30-gke', {'index_patterns': [GKE], 'data_stream': {}, 'priority': 500,
    'template': {'settings': {'index.mode': 'time_series', 'index.routing_path': [
        'gcp.labels.resource.cluster_name', 'gcp.labels.resource.node_name', 'gcp.labels_fingerprint']},
        'mappings': {'properties': {'@timestamp': D, 'cloud': obj(account=obj(id=K)), 'gcp': obj(
            labels_fingerprint=DIM, labels=obj(resource=obj(cluster_name=DIM, node_name=DIM)),
            gke=obj(container=obj(restart=obj(count={'type': 'long', 'time_series_metric': 'counter'})),
                    node=obj(memory=obj(allocatable_utilization=obj(pct={'type': 'double'})))))}}}})   # mapped, never sent (CG5)


def node(cluster, name, cpu, mem, minutes=5):
    # memory as used / allocatable bytes: the utilisation field isn't collected in production (CG5)
    return {'@timestamp': ago(minutes=minutes), 'cloud': {'account': {'id': 'proj-' + cluster}},
            'gcp': {'labels': {'resource': {'cluster_name': cluster, 'node_name': name}, 'metrics': {'memory_type': 'non-evictable'}},
                    'gke': {'node': {'cpu': {'allocatable_utilization': {'pct': cpu}},
                                     'memory': {'used': {'bytes': int(mem * 64e9)}, 'allocatable': {'bytes': int(64e9)}}}}}}


def evictable(cluster, name, frac, minutes=5):
    # the other memory series (CG7, 5 Nov): reclaimable cache; must not count towards Mem peak
    return {'@timestamp': ago(minutes=minutes, seconds=1), 'cloud': {'account': {'id': 'proj-' + cluster}},
            'gcp': {'labels': {'resource': {'cluster_name': cluster, 'node_name': name}, 'metrics': {'memory_type': 'evictable'}},
                    'gke': {'node': {'memory': {'used': {'bytes': int(frac * 64e9)}}}}}}


def restarts(cluster, pod, count, minutes):
    return {'@timestamp': ago(minutes=minutes), 'cloud': {'account': {'id': 'proj-' + cluster}},
            'gcp': {'labels': {'resource': {'cluster_name': cluster}}, 'labels_fingerprint': 'fp-' + pod,   # one per time series
                    'gke': {'container': {'restart': {'count': count}}}}}


gke = [node('g-prd-gke-2', 'n1', 0.50, 0.60), node('g-prd-gke-2', 'n2', 0.95, 0.70),          # Critical: a node at 95 % CPU
       restarts('g-prd-gke-2', 'p1', 3, 30), restarts('g-prd-gke-2', 'p1', 5, 5),              # 2 restarts in the window
       restarts('g-prd-gke-2', 'p2', 7, 30), restarts('g-prd-gke-2', 'p2', 7, 5),              # none
       node('g-stg-gke-2', 'n3', 0.30, 0.85, 3),                                                 # Warning: memory 85 %
       node('g-pre-gke-4', 'n4', 0.20, 0.30, 40),
       evictable('g-prd-gke-2', 'n1', 0.99)]                                                   # 99 % cache: ignored                                                # Silent: 40 minutes ago
assert not call('POST', '/_bulk?refresh=true', ''.join(json.dumps({'create': {'_index': GKE}}) + '\n' + json.dumps(d) + '\n'
                                                        for d in gke), nd=True).get('errors')
call('PUT', f'/{REL30}', {'mappings': {'properties': {
    '@timestamp': D, 'is_marked_for_deletion': {'type': 'boolean'}, 'type': obj(name=K),
    'parent': obj(name=K, **{'class': K}, environment=K, install_status=K),
    'child': obj(name=K, **{'class': K}, environment=K, install_status=K)}}})
rel30 = lambda p, pc, c, cc, gone=False: {'@timestamp': ago(days=30), 'is_marked_for_deletion': gone,
                                          'type': {'name': 'Runs on::Runs'}, 'parent': {'name': p, 'class': pc},
                                          'child': {'name': c, 'class': cc}}
KC = 'cmdb_ci_kubernetes_cluster'
assert not call('POST', '/_bulk?refresh=true', ''.join(json.dumps({'index': {'_index': REL30}}) + '\n' + json.dumps(d) + '\n' for d in [
    rel30('GKE App PROD', 'cmdb_ci_service_auto', 'g-prd-gke-2', KC),
    rel30('GKE App PROD', 'cmdb_ci_service_auto', 'g-dr-gke-1', KC),                            # in the CMDB, not collected
    rel30('GKE App PROD', 'cmdb_ci_service_auto', 'g-stg-gke-2', KC, gone=True)]), nd=True).get('errors')


def inc(n, p, s, ci):
    return {'@timestamp': ago(hours=3), 'number': n, 'priority': p, 'state_name': s, 'opened_at': ago(hours=3),
            'ci': {'name': ci, 'class_name': 'Linux Server', 'environment': 'Production'},
            'assigned_to': {'name': 'Ann Lee', 'email': 'ann@x'}, 'assignment_group': {'name': 'Unix', 'manager': {'name': 'Bo'}}}


def chg(n, ci, days):
    return {'@timestamp': ago(days=days), 'number': n, 'ci': {'name': ci}, 'start_date': ago(days=days),
            'end_at': ago(days=days, hours=-1), 'opened_at': ago(days=days + 1), 'close_code': 'successful',
            'state_name': 'Closed', 'type': {'normalized': 'normal'}, 'category': {'1': 'Hardware'},
            'assignment_group': {'name': 'Unix'}}


lines = ''
for index, docs in ((INC, [inc('INC801', 1, 'New', 'srvA'), inc('INC802', 2, 'In Progress', 'srvA'),
                           inc('INC803', 1, 'Resolved', 'srvA'), inc('INC804', 1, 'New', 'srvZ'),
                           inc('INC805', 3, 'New', 'srvA'), inc('INC806', 2, 'On Hold', 'srvA')]),   # 5 Nov: P3, On Hold
                    (CHG, [chg('CHG1', 'srvA', 1), chg('CHG2', 'App PROD', 2), chg('CHG3', 'srvZ', 1),
                           chg('CHG4', 'srvA', 20)])):
    lines += ''.join(json.dumps({'index': {'_index': index}}) + '\n' + json.dumps(d) + '\n' for d in docs)
assert not call('POST', '/_bulk?refresh=true', lines, nd=True).get('errors')

dash = json.loads([l for l in open(sys.argv[1]) if l.strip()][-1])
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = {title(p): p for p in panels}
fails = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" + ('' if ok else f'\n          expected {want!r}'))
    if not ok:
        fails.append(name)


DEFAULTS = {'incident': '(all incidents)', 'ci': '(no CI selected)', 'server': '(no server selected)', 'health_window': '24 hours',
            'service': '(services on this CI)', 'application': '(all applications)', 'monitored_app': '(all monitored applications)',
            '_tstart': ago(hours=1), '_tend': ago()}


def esql(q, rng, **vals):
    names = sorted(set(re.findall(r'\?([A-Za-z_][A-Za-z0-9_]*)', q)) - {'sysparm_query'})
    v = dict(DEFAULTS, **vals)
    missing = [n for n in names if n not in v]
    assert not missing, missing
    body = {'query': q, 'params': [{n: v[n]} for n in names]}
    if rng:
        body['filter'] = {'range': {'@timestamp': {'gte': rng['from'], 'lte': rng['to']}}}
    r = call('POST', '/_query?format=json', body)
    if 'error' in r:
        return r
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, x)) for x in r['values']]


def queries(p):
    ec = p['embeddableConfig']
    if p['type'] == 'esql_control':
        yield ec['esql_query'], None
    elif p['type'] == 'vis':
        yield ec['attributes']['state']['query']['esql'], ec.get('time_range')


try:
    print('Every query runs (no CI picked, then CI = srvA)')
    for p in panels:
        for q, rng in queries(p):
            for ci in ('(no CI selected)', 'srvA'):
                r = esql(q, rng, ci=ci)
                if isinstance(r, dict):
                    check(f'{title(p)} [{ci}]', json.dumps(r['error'])[:400], 'no error')
    if not fails:
        print('  PASS  all', sum(1 for p in panels for _ in queries(p)), 'queries, both ways')

    run = lambda t, **v: esql(P[t]['embeddableConfig']['attributes']['state']['query']['esql'],
                              P[t]['embeddableConfig'].get('time_range'), **v)
    print('Section 1')
    check('Active P1 on srvA', run('Active P1 incidents', ci='srvA')[0]['metric_val'], 1)
    check('Active P2 on srvA', run('Active P2 incidents', ci='srvA')[0]['metric_val'], 1)
    check('Active P1 with no CI picked counts every CI', run('Active P1 incidents')[0]['metric_val'] >= 2, True)
    T = 'Active P1 and P2 incidents'
    check(T + ' on srvA (no P3, On Hold or Resolved)', sorted(r['number'] for r in run(T, ci='srvA')), ['INC801', 'INC802'])
    allrows = {r['number'] for r in run(T)}
    check(T + ' with nothing picked: every CI\'s P1 / P2, no P3, On Hold or Resolved',
          ({'INC801', 'INC802', 'INC804'} <= allrows, allrows & {'INC803', 'INC805', 'INC806'}), (True, set()))
    check(T + ': MIM\'s columns', list(run(T, ci='srvA')[0]),
          ['number', 'priority', 'ci.name', 'state_name', 'opened', 'sla', 'assignment_group', 'assignee',
           'assignee_email', 'group_manager', 'manager_email', 'short_description'])
    print('Incident control (MIM logic: the incident selects its CI and wins over the CI control)')
    check('Incident INC804 → its CI srvZ: the table', [r['number'] for r in run(T, incident='INC804 · srvZ', ci='srvA')], ['INC804'])
    check('Incident INC804 → P1 tile counts srvZ', run('Active P1 incidents', incident='INC804 · srvZ', ci='srvA')[0]['metric_val'], 1)
    check('Incident INC801 → P2 tile counts srvA', run('Active P2 incidents', incident='INC801 · srvA')[0]['metric_val'], 1)
    check('Incident INC801 → Elastic infra alerts tile on srvA',
          run('Active Elastic infra alerts', incident='INC801 · srvA')[0]['metric_val'], 2)
    check('Incident INC801 → Changes on srvA', [r['number'] for r in run('Changes on this CI (last 7 days)', incident='INC801 · srvA')], ['CHG1'])
    check('Incident INC801 → Server Health on srvA', [r.get('host.name') or r.get('server') or r.get('ci.name') for r in run('Server Health', incident='INC801 · srvA')][:1] != [], True)
    ctl = sorted(A['pinned_panels']['panels'].values(), key=lambda v: v['order'])
    check('top bar: Incident, CI, Monitored application', [v['config']['title'] for v in ctl],
          ['🚨 Incident', '🖥️ CI', '🧩 Monitored application'])
    # CHG2 is on App PROD, linked to srvA by a CMDB relation recorded in 2025: links older than the panel's 7 days
    # aren't read (documented limit), so only srvA's own recent change shows; CHG4 is 20 days old
    check('Changes on this CI: its own, last 7 days',
          sorted(r['number'] for r in run('Changes on this CI (last 7 days)', ci='srvA')), ['CHG1'])
    check('Alerts on this CI', 'a-srvA' in json.dumps(run('Alerts on this CI (Netcool)', ci='srvA')), True)
    ea = run('Elastic infra alerts', ci='srvA')
    check('Elastic infra alerts on srvA: threshold, ML and host alerts, active first',
          [(r['state'], r['server'], r['rule']) for r in ea],
          [('Active', 'srva', 'paladin-host-uptime-c30'), ('Active', 'srva', 'paladin-genrocketexception-c3'),
           ('Recovered', 'srva', 'paladin-cpu-usage-high_prio-ml')] if ea and ea[0]['rule'] == 'paladin-host-uptime-c30' else
          [('Active', 'srva', 'paladin-genrocketexception-c3'), ('Active', 'srva', 'paladin-host-uptime-c30'),
           ('Recovered', 'srva', 'paladin-cpu-usage-high_prio-ml')])
    check('Elastic infra alerts with no CI: every active paladin alert, with its server',
          sorted((r['server'], r['rule']) for r in run('Elastic infra alerts')),
          [('srva', 'paladin-genrocketexception-c3'), ('srva', 'paladin-host-uptime-c30'),
           ('srva-other', 'paladin-host-uptime-c30'), ('srvz', 'paladin-filesystem-usage')])
    print('Section 2')
    check('Server Health: srvA reporting', [(r.get('server') or r.get('host.name') or r.get('ci.name')) for r in run('Server Health', ci='srvA')][:1], ['srvA'])
    check('Middleware Health: the MQ queue manager', 'QM1' in json.dumps(run('Middleware Health', ci='srvA')), True)
    check('Database Health: the SQL Server service', 'mssqlserver' in json.dumps(run('Database Health', ci='srvA')).lower(), True)
    check('Process Health has rows', len(run('Process Health', ci='srvA')) > 0, True)
    gk = lambda **v: [(r['cluster'], r['status']) for r in run('Cloud health · GKE', **v)]
    check('Cloud health · GKE with no CI: every collected cluster, problems first', gk(),
          [('g-prd-gke-2', 'Critical'), ('g-pre-gke-4', 'Silent'), ('g-stg-gke-2', 'Warning')])
    g = {r['cluster']: r for r in run('Cloud health · GKE')}['g-prd-gke-2']
    check('Cloud health · GKE: nodes, CPU p90 of the busiest node, memory peak, restarts in the window, project',
          (g['nodes'], g['cpu_p90'], g['mem_peak'], g['restarts'], g['project']), (2, 95.0, 70.0, 2, 'proj-g-prd-gke-2'))
    check('Cloud health · GKE for an application service: its linked clusters (deleted links ignored)',
          gk(ci='GKE App PROD'), [('g-prd-gke-2', 'Critical'), ('g-dr-gke-1', 'Not collected')])
    check('Cloud health · GKE for a cluster CI: that cluster', gk(ci='g-stg-gke-2'), [('g-stg-gke-2', 'Warning')])
    check('Cloud health · GKE for a server with no cluster: empty', gk(ci='srvA'), [])
    check('Active Elastic infra alerts tile on srvA: the active alerts', run('Active Elastic infra alerts', ci='srvA')[0]['metric_val'], 2)
    check('Active Elastic infra alerts tile with no CI: every active paladin alert', run('Active Elastic infra alerts')[0]['metric_val'], 4)
    links = sorted(p['embeddableConfig']['content'] for p in panels if p['type'] == 'markdown' and 'detailed dashboard' in title(p))
    check('five detailed-dashboard links', sorted(l.split('](')[1].rstrip(')') for l in links),
          sorted('https://kibana-prod.gcp.cna.com/app/r/s/' + c for c in ['qJk5u', 'w6zL4', 'jwCRg', 't4oxr', 'MDJ9f']))
    check('section titles with icons', [s['title'] for s in A['sections']],
          ['🚨 1 · Incidents, changes and alerts', '🖥️ 2 · Infrastructure overview (including cloud)',
           '🩺 3 · Applications overview', '🔗 4 · Detailed dashboards'])
    print('Section 3')
    check('Applications related to srvA', 'App PROD' in json.dumps(run('Applications related to this CI', ci='srvA')), True)
    check('Service health: the APM service on srvA', 'app-api' in json.dumps(run('Service health', ci='srvA')), True)
    check('Services of the Application: one application', sorted({r['ci.name'] for r in run('Services of the Application', application='Juno')}), ['Juno'])
    check('Application Health with no CI: the monitored applications only',
          sorted(r['ci.name'] for r in run('Application Health')), ['Automated Claim Transaction', 'Juno'])
    check('Application Health, Monitored application = Juno', [r['ci.name'] for r in run('Application Health', monitored_app='Juno')], ['Juno'])
    check('Services of the Application leaves out an unmonitored application',
          [r['service.name'] for r in run('Services of the Application', application='Payment Hub')], [])
    pins = sorted((v['order'], v['config']['title']) for v in A['pinned_panels']['panels'].values())
    check('top bar: Incident, CI, then Monitored application (icon titles)', pins,
          [(0, '🚨 Incident'), (1, '🖥️ CI'), (2, '🧩 Monitored application')])
    row = sorted((p for p in panels if p['type'] == 'esql_control' and p['gridData'].get('sectionId') == P['🧩 Application']['gridData']['sectionId']),
                 key=lambda p: p['gridData']['x'])
    check('section 3 controls: no Telemetry', [(title(p), p['gridData']['x'], p['gridData']['w']) for p in row],
          [('🧩 Application', 0, 24), ('⚙️ Service', 24, 24)])
    check('three Start here banners', sorted(title(p) for p in panels if p['type'] == 'legacy_vis' and 'description' in p['embeddableConfig'] and p['embeddableConfig']['description'].startswith('How to use')),
          ['Pick a server', 'Pick an application and a service', 'Start here'])
finally:
    cleanup()

print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
