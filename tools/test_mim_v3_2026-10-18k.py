"""Check phase 1 of the server / Health window build (18 Oct): CI and Server controls, Health window, the precedence
(Incident's CI if a server, else CI control if a server, else Server control), Server Health one row per server,
"No data in window", the Health window values, and the panels that follow the chosen server.

Usage: test_mim_v3_2026-10-18k.py MIM_V3_NDJSON
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

ES = 'http://localhost:9200'
NOW = datetime.now(timezone.utc)
ago = lambda **kw: (NOW - timedelta(**kw)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
K, D, F = {'type': 'keyword'}, {'type': 'date'}, {'type': 'double'}
obj = lambda **p: {'properties': p}
T = 't18k'
DS = {  # data streams (index names metrics-*-* / logs-*-* must be data streams)
    f'metrics-system.process-{T}': {'@timestamp': D, 'ci': obj(name=K, environment=K), 'event': obj(module=K),
                                     'paladin': obj(enrichment=obj(computed=obj(proc_type=K, proc_instance=K))),
                                     'enrich_policy': obj(**{'cmdb-cis': obj(proc_assignment=K)})},
    f'metrics-windows.service-{T}': {'@timestamp': D, 'ci': obj(name=K), 'windows': obj(service=obj(name=K, state=K, display_name=K, start_type=K)),
                                      'enrich_policy': obj(**{'cmdb-cis': obj(proc_assignment=K)})},
    f'metrics-apm.internal-{T}': {'@timestamp': D, 'host': obj(name=K), 'service': obj(name=K, environment=K), 'ci': obj(name=K)},
    f'logs-syslog-classic-{T}': {'@timestamp': D, 'ci': obj(name=K), 'message': K, 'syslog_severity_code': {'type': 'integer'},
                                  'log': obj(level=K), 'data_stream': obj(dataset=K)},
}
IDX = {  # plain indices
    f'.ds-metrics-system.cpu-default-{T}': {'@timestamp': D, 'ci': obj(name=K, environment=K), 'system': obj(cpu=obj(total=obj(norm=obj(pct=F))))},
    f'.ds-metrics-system.memory-default-{T}': {'@timestamp': D, 'ci': obj(name=K), 'system': obj(memory=obj(actual=obj(used=obj(pct=F))))},
    f'.ds-metrics-system.filesystem-default-{T}': {'@timestamp': D, 'ci': obj(name=K), 'system': obj(filesystem=obj(used=obj(pct=F)))},
    f'cmdb-ci-relations-{T}': {'@timestamp': D, 'type': obj(name=K), 'is_marked_for_deletion': {'type': 'boolean'},
                               'parent': obj(name=K, **{'class': K}, environment=K, install_status=K),
                               'child': obj(name=K, **{'class': K}, environment=K, install_status=K)},
    f'synthetics-{T}': {'@timestamp': D, 'ci': obj(name=K), 'url': obj(domain=K), 'summary': obj(status=K),
                        'monitor': obj(name=K, type=K), 'observer': obj(geo=obj(name=K))},
    f'.ds-bridge-alerts-netcool-default-{T}': {'@timestamp': D, 'severity': {'type': 'integer'}, 'message': K, 'node': K,
                                               'first_occurrence': D, 'last_occurrence': D,
                                               'netcool': obj(type_name=K, acknowledged_name=K, tally={'type': 'integer'}, identifier=K),
                                               'ci': obj(name=K, class_name=K, environment=K, support_group=obj(l2=obj(name=K)))},
    f'servicenow-incidents-{T}': {'@timestamp': D, 'number': K, 'priority': {'type': 'integer'}, 'state_name': K,
                                  'opened_at': D, 'ci': obj(name=K)},
}


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request(ES + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return {'error': json.loads(e.read())}


def bulk(index, docs):
    op = 'create' if index in DS else 'index'
    lines = ''.join(json.dumps({op: {'_index': index}}) + '\n' + json.dumps(d) + '\n' for d in docs)
    r = call('POST', '/_bulk?refresh=true', lines, nd=True)
    assert not r.get('errors'), json.dumps(r)[:700]


def cleanup():
    for n in DS:
        call('DELETE', f'/_data_stream/{n}')
        call('DELETE', f'/_index_template/{n}')
    for n in IDX:
        call('DELETE', f'/{n}')


cleanup()
for n, m in DS.items():
    assert 'error' not in call('PUT', f'/_index_template/{n}', {'index_patterns': [n], 'data_stream': {}, 'priority': 700,
                                                             'template': {'mappings': {'properties': m}}}), n
for n, m in IDX.items():
    assert 'error' not in call('PUT', f'/{n}', {'mappings': {'properties': m}}), n

cpu = lambda h, m, pct=0.5, env='Production': {'@timestamp': ago(minutes=m), 'ci': {'name': h, 'environment': env},
                                                'system': {'cpu': {'total': {'norm': {'pct': pct}}}}}
bulk(f'.ds-metrics-system.cpu-default-{T}', [cpu('srvA', 1, 0.95), cpu('srvB', 30), cpu('srvD', 2, env='Development')])
bulk(f'.ds-metrics-system.memory-default-{T}', [{'@timestamp': ago(minutes=1), 'ci': {'name': 'srvA'}, 'system': {'memory': {'actual': {'used': {'pct': 0.7}}}}}])
bulk(f'.ds-metrics-system.filesystem-default-{T}', [{'@timestamp': ago(minutes=1), 'ci': {'name': 'srvA'}, 'system': {'filesystem': {'used': {'pct': 0.85}}}}])
rel = lambda p, pc, c, cc: {'@timestamp': '2025-01-01T00:00:00Z', 'type': {'name': 'Runs on::Runs'},
                            'parent': {'name': p, 'class': pc, 'environment': 'Production', 'install_status': 'Installed'},
                            'child': {'name': c, 'class': cc, 'environment': 'Production', 'install_status': 'Installed'}}
SVC, LNX = 'cmdb_ci_service_discovered', 'cmdb_ci_linux_server'
bulk(f'cmdb-ci-relations-{T}', [rel('App PROD', SVC, 'srvA', LNX), rel('App PROD', SVC, 'srvB', LNX), rel('Other PROD', SVC, 'srvC', LNX)])
bulk(f'metrics-system.process-{T}', [{'@timestamp': ago(minutes=1), 'ci': {'name': 'srvA'},
                                      'paladin': {'enrichment': {'computed': {'proc_type': 'ibm_mq', 'proc_instance': 'QM1'}}}},
                                     {'@timestamp': ago(minutes=1), 'ci': {'name': 'srvB'},
                                      'paladin': {'enrichment': {'computed': {'proc_type': 'jboss', 'proc_instance': 'n/a'}}}}])
bulk(f'metrics-windows.service-{T}', [{'@timestamp': ago(minutes=1), 'ci': {'name': 'srvA'},
                                       'windows': {'service': {'name': 'MSSQLSERVER', 'state': 'Stopped', 'display_name': 'SQL', 'start_type': 'Automatic'}}}])
bulk(f'metrics-apm.internal-{T}', [{'@timestamp': ago(minutes=3), 'host': {'name': 'srvA'}, 'service': {'name': 'app-api', 'environment': 'prd1'}}])
bulk(f'logs-syslog-classic-{T}', [{'@timestamp': ago(minutes=4), 'ci': {'name': 'srvA'}, 'message': 'disk error 12',
                                    'syslog_severity_code': 3, 'data_stream': {'dataset': 'syslog'}}])
bulk(f'synthetics-{T}', [{'@timestamp': ago(minutes=2), 'url': {'domain': 'srvA.cna.com'}, 'summary': {'status': 'down'},
                          'monitor': {'name': 'srvA ping', 'type': 'icmp'}, 'observer': {'geo': {'name': 'us-east'}}}])
alert = lambda ident, ci: {'@timestamp': ago(minutes=20), 'severity': 5, 'message': 'problem ' + ident, 'node': ci + '.cna.com',
                           'first_occurrence': ago(minutes=40), 'last_occurrence': ago(minutes=20),
                           'netcool': {'type_name': 'problem', 'acknowledged_name': 'no', 'tally': 2, 'identifier': ident},
                           'ci': {'name': ci, 'class_name': 'x'}}
bulk(f'.ds-bridge-alerts-netcool-default-{T}', [alert('a-srvA', 'srvA'), alert('a-app', 'App PROD'), alert('a-srvC', 'srvC')])
bulk(f'servicenow-incidents-{T}', [{'@timestamp': ago(minutes=1), 'number': 'INC7', 'priority': 2, 'state_name': 'New',
                                    'opened_at': ago(minutes=10), 'ci': {'name': 'App PROD'}}])

dash = json.loads(open(sys.argv[1]).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = {title(p): p for p in panels}
CTL = {c['config']['title']: c['config'] for c in A['pinned_panels']['panels'].values()}
fails = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" + ('' if ok else f'\n          expected {want!r}'))
    if not ok:
        fails.append(name)


def esql(q, params, rng=None):
    body = {'query': q, 'params': params}
    if rng:
        body['filter'] = {'range': {'@timestamp': {'gte': rng, 'lte': 'now'}}}
    r = call('POST', '/_query?format=json', body)
    assert 'error' not in r, json.dumps(r)[:1200]
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']]


def run(t, incident='(all incidents)', ci='(no CI selected)', server='(no server selected)', window='24 hours'):
    ec = P[t]['embeddableConfig']
    q = ec['attributes']['state']['query']['esql']
    vals = {'incident': incident, 'ci': ci, 'server': server, 'health_window': window, 'service': '(services on this CI)'}
    params = [{k: v} for k, v in vals.items() if '?' + k in q]
    return esql(q, params, ec.get('time_range', {}).get('from'))


try:
    sh = lambda **kw: [(r['server'], r['status']) for r in run('Server Health', **kw)]
    check('1. Incident CI is a server: it is shown', sh(incident='INC9 · srvA'), [('srvA', 'Reporting')])
    check('2. Incident CI not a server, CI control is: the CI control server', sh(incident='INC7 · App PROD', ci='srvB'),
          [('srvB', 'Silent')])
    check('3. Neither a server: the Server control', sh(incident='INC7 · App PROD', server='srvA'), [('srvA', 'Reporting')])
    check('   ... a server in the CI control wins over the Server control', sh(ci='srvB', server='srvA'), [('srvB', 'Silent')])
    check('4. Nothing chosen (automatic mode comes next): empty', sh(incident='INC7 · App PROD'), [])
    check('Server known only from the CMDB, no data: "No data in window"', sh(ci='srvC'), [('srvC', 'No data in window')])
    check('Health window 15 minutes: srvB (data 30 min old) has no data in the window', sh(ci='srvB', window='15 minutes'),
          [('srvB', 'No data in window')])
    check('Health window 1 hour: srvB data counted', sh(ci='srvB', window='1 hour'), [('srvB', 'Silent')])
    row = run('Server Health', incident='INC9 · srvA')[0]
    check('Server Health values', (row['cpu_p90'], row['mem_peak'], row['disk_max']), (95.0, 70.0, 85.0))
    for w in ('15 minutes', '30 minutes', '1 hour', '6 hours', '8 hours', '24 hours', '3 days', '7 days'):
        run('Server Health', ci='srvA', window=w)   # every Health window value runs
    check('every Health window value accepted', True, True)
    check('Middleware Health follows the chosen server', [(r['component'], r['ci.name']) for r in run('Middleware Health', server='srvA')],
          [('ibm_mq · QM1', 'srvA')])
    check('Middleware Health for another server', [r['component'] for r in run('Middleware Health', server='srvB')], ['jboss'])
    check('Process Health: the stopped Windows service', [(r['name'], r['status']) for r in run('Process Health', server='srvA')
                                                          if r['kind'] == 'Windows service'], [('SQL (MSSQLSERVER)', 'Stopped')])
    check('Applications on this CI: APM services on the server', [r['application'] for r in run('Applications on this CI', server='srvA')], ['app-api'])
    check('Synthetics: monitor on <server>.cna.com', [(r['monitor.name'], r['status']) for r in run('Synthetics Health', server='srvA')],
          [('srvA ping', 'Down')])
    check('Errors from the Logs: the server\'s errors', [r['text'] for r in run('Errors from the Logs', server='srvA')], ['disk error #'])
    check('Alerts on this CI: the CI\'s own alerts and the chosen server\'s', sorted(r['summary'] for r in run('Alerts on this CI', incident='INC7 · App PROD', server='srvA')),
          ['problem a-app', 'problem a-srvA'])
    check('controls in order', [c['title'] for c in sorted(CTL.values(), key=lambda c: next(x['order'] for x in A['pinned_panels']['panels'].values() if x['config'] is c))],
          ['Incident', 'CI', 'Server', 'Health window', 'Service', 'Application'])
    check('Health window options and default', ([r['health_window'] for r in esql(CTL['Health window']['esql_query'], [])],
                                               CTL['Health window']['selected_options']),
          (['15 minutes', '30 minutes', '1 hour', '6 hours', '8 hours', '24 hours', '3 days', '7 days'], ['24 hours']))
    srv_list = [r['server'] for r in esql(CTL['Server']['esql_query'], [])]
    check('Server control: production servers with metrics, no-server option first', (srv_list[0], 'srvA' in srv_list, 'srvD' in srv_list),
          ('(no server selected)', True, False))
    ci_list = [r['ci'] for r in esql(CTL['CI']['esql_query'], [])]
    check('CI control: incident CIs plus monitored servers', ('App PROD' in ci_list, 'srvA' in ci_list, 'srvB' in ci_list), (True, True, True))
    check('server panels show "Last 5 years" (CMDB) and read the Health window', sorted({
        (P[t]['embeddableConfig']['time_range']['from'], '?health_window' in P[t]['embeddableConfig']['attributes']['state']['query']['esql'])
        for t in ('Server Health', 'Middleware Health', 'Database Health', 'Process Health', 'Synthetics Health',
                  'Errors from the Logs', 'Applications on this CI')}), [('now-5y', True)])
finally:
    cleanup()
print('\n' + ('ALL CHECKS PASSED' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
