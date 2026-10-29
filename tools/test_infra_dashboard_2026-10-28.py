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
    for pat in ('*-t15*', '*-test*', '*-t16j*', '*-t18k*', '*-t27s*', '*-t28*'):
        for ds in (call('GET', f'/_data_stream/{pat}').get('data_streams') or []):
            call('DELETE', f'/_data_stream/{ds["name"]}')
        got = call('GET', f'/_cat/indices/{pat}?format=json&h=index&expand_wildcards=all')
        for i in got if isinstance(got, list) else []:
            call('DELETE', f'/{i["index"]}')
    for t in ('apm-tx-test',):
        call('DELETE', f'/_index_template/{t}')
    call('DELETE', '/cmdb_with_apm_flag')


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
    '@timestamp': D, 'name': TXT, 'number': TXT, 'install_status': TXT, 'is_monitored': {'type': 'boolean'},
    'support_group': obj(l2=obj(name=TXT))}}})


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
                           inc('INC803', 1, 'Resolved', 'srvA'), inc('INC804', 1, 'New', 'srvZ')]),
                    (CHG, [chg('CHG1', 'srvA', 1), chg('CHG2', 'App PROD', 2), chg('CHG3', 'srvZ', 1),
                           chg('CHG4', 'srvA', 20)])):
    lines += ''.join(json.dumps({'index': {'_index': index}}) + '\n' + json.dumps(d) + '\n' for d in docs)
assert not call('POST', '/_bulk?refresh=true', lines, nd=True).get('errors')

dash = json.loads(open(sys.argv[1]).readline())
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


DEFAULTS = {'ci': '(no CI selected)', 'server': '(no server selected)', 'health_window': '24 hours',
            'service': '(services on this CI)', 'application': '(all applications)', 'telemetry': '(all applications)',
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
    check('Incidents on this CI', sorted(r['number'] for r in run('Incidents on this CI', ci='srvA')), ['INC801', 'INC802'])
    # CHG2 is on App PROD, linked to srvA by a CMDB relation recorded in 2025: links older than the panel's 7 days
    # aren't read (documented limit), so only srvA's own recent change shows; CHG4 is 20 days old
    check('Changes on this CI: its own, last 7 days',
          sorted(r['number'] for r in run('Changes on this CI (last 7 days)', ci='srvA')), ['CHG1'])
    check('Alerts on this CI', 'a-srvA' in json.dumps(run('Alerts on this CI (Netcool)', ci='srvA')), True)
    print('Section 2')
    check('Server Health: srvA reporting', [(r.get('server') or r.get('host.name') or r.get('ci.name')) for r in run('Server Health', ci='srvA')][:1], ['srvA'])
    check('Middleware Health: the MQ queue manager', 'QM1' in json.dumps(run('Middleware Health', ci='srvA')), True)
    check('Database Health: the SQL Server service', 'mssqlserver' in json.dumps(run('Database Health', ci='srvA')).lower(), True)
    check('Process Health has rows', len(run('Process Health', ci='srvA')) > 0, True)
    print('Section 3')
    check('Applications related to srvA', 'App PROD' in json.dumps(run('Applications related to this CI', ci='srvA')), True)
    check('Service health: the APM service on srvA', 'app-api' in json.dumps(run('Service health', ci='srvA')), True)
    check('Services of the Application: one application', sorted({r['ci.name'] for r in run('Services of the Application', application='Juno')}), ['Juno'])
    check('Application Health with no CI: every production application', len(run('Application Health')) > 0, True)
finally:
    cleanup()

print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
