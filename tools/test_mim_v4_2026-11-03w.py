"""Check patch 03w: the Monitored application control scopes Application Health, Services of the Application and the
section 3 Application / Service lists to cmdb_with_apm_flag's In Production + Operational + monitored applications;
the Telemetry control is gone; every query still runs.

Usage: test_mim_v4_2026-11-03w.py "MIM V4.ndjson"
(local Elasticsearch on port 9200; loads test -15's APM data and a cmdb_with_apm_flag index, removes them at the end)
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

HERE = __file__.rsplit('/', 1)[0]
ES = 'http://localhost:9200'
FLAG = 'cmdb_with_apm_flag'
ALL = '(all monitored applications)'
LABEL = 'Enrolled — no telemetry yet'


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
    for pat in ('*-test*', '*-t15*'):
        for ds in (call('GET', f'/_data_stream/{pat}').get('data_streams') or []):
            call('DELETE', f'/_data_stream/{ds["name"]}')
        got = call('GET', f'/_cat/indices/{pat}?format=json&h=index&expand_wildcards=all')
        for i in got if isinstance(got, list) else []:
            call('DELETE', f'/{i["index"]}')
    call('DELETE', '/_index_template/apm-tx-test')
    call('DELETE', f'/{FLAG}')


cleanup()
src = open(f'{HERE}/test_mim_v3_2026-10-15.py').read().split('dash = json.loads')[0]   # test -15's APM data
exec(compile(src, 'test_mim_v3_2026-10-15.py', 'exec'), {'__name__': 'setup', '__file__': f'{HERE}/test_mim_v3_2026-10-15.py'})

T = {'type': 'text', 'fields': {'keyword': {'type': 'keyword', 'ignore_above': 256}}}
call('PUT', f'/{FLAG}', {'mappings': {'properties': {   # as in cmdb_with_apm_flag.csv
    '@timestamp': {'type': 'date'}, 'name': T, 'number': T, 'install_status': T, 'operational_status': T,
    'is_monitored': {'type': 'boolean'}, 'support_group': {'properties': {'l2': {'properties': {'name': T}}}}}}})
app = lambda name, number, mon=True, inst='In Production', oper='Operational': {
    '@timestamp': '2026-11-02T20:37:39Z', 'name': name, 'number': number, 'is_monitored': mon,
    'install_status': inst, 'operational_status': oper, 'support_group': {'l2': {'name': 'IT.' + name[:3]}}}
docs = [app('Automated Claim Transaction', 'APM-Aut'),      # in scope, sends APM data
        app('Juno', 'APM-Jun'),                             # in scope, sends APM data
        app('Silent App', 'APM-SIL'),                       # in scope, no APM data yet
        app('Payment Hub', 'APM-Pay', mon=False),           # sends APM data but not monitored: out
        app('Quiet App', 'APM-Qui', oper='Non-Operational'),  # out
        app('Pilot App', 'APM-PIL', inst='Pilot'),          # out
        app('Gone App', 'APM-GON', inst='Retired', oper='Retired')]  # out
assert not call('POST', '/_bulk?refresh=true',
                ''.join(json.dumps({'index': {'_index': FLAG}}) + '\n' + json.dumps(d) + '\n' for d in docs), nd=True).get('errors')

dash = json.loads([l for l in open(sys.argv[1]) if l.strip()][-1])   # the dashboard is the last line
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
P = {(p['embeddableConfig'].get('title') or ''): p for p in panels}
pinned = {v['config']['title']: v for v in A['pinned_panels']['panels'].values()}
fails = []
DEFAULTS = {'incident': '(all incidents)', 'ci': '(no CI selected)', 'server': '(no server selected)',
            'health_window': '24 hours', 'service': '(services on this CI)', 'application': '(all applications)',
            'monitored_app': ALL}


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" + ('' if ok else f'\n          expected {want!r}'))
    if not ok:
        fails.append(name)


def esql(q, rng=None, **vals):
    names = sorted(set(re.findall(r'\?([A-Za-z_][A-Za-z0-9_]*)', q)) - {'sysparm_query'})
    now = datetime.now(timezone.utc)
    v = dict(DEFAULTS, _tstart=(now - timedelta(hours=1)).isoformat(), _tend=now.isoformat(), **vals)   # as Kibana sends them
    body = {'query': q, 'params': [{n: v[n]} for n in names]}
    if rng:
        body['filter'] = {'range': {'@timestamp': {'gte': rng['from'], 'lte': rng['to']}}}
    r = call('POST', '/_query?format=json', body)
    if 'error' in r:
        return r
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, x)) for x in r['values']]


def run(title, **vals):
    ec = P[title]['embeddableConfig']
    r = esql(ec['attributes']['state']['query']['esql'], ec.get('time_range'), **vals)
    assert not isinstance(r, dict), json.dumps(r)[:900]
    return r


def control(q):
    r = esql(q)
    assert not isinstance(r, dict), json.dumps(r)[:900]
    return [list(x.values())[0] for x in r]


try:
    print('Every query runs')
    n = 0
    for p in panels:
        ec = p['embeddableConfig']
        q = ec.get('esql_query') if p['type'] == 'esql_control' else (
            ec.get('attributes', {}).get('state', {}).get('query', {}).get('esql') if p['type'] == 'vis' else None)
        if not q:
            continue
        for mon in (ALL, 'Juno'):
            r = esql(q, ec.get('time_range'), monitored_app=mon)
            n += 1
            if isinstance(r, dict) and 'Unknown index' not in json.dumps(r) and 'Unknown column' not in json.dumps(r):
                check(f'{ec.get("title")} [{mon}]', json.dumps(r['error'])[:300], 'no error')
    print(f'  ran {n} queries (panels whose source indices are not loaded here are skipped)')

    print('Monitored application control (top bar)')
    m = pinned.get('Monitored application')
    check('present, pinned after Incident and CI', (m is not None, m and m['order'],
          sorted(v['order'] for v in A['pinned_panels']['panels'].values())), (True, 2, [0, 1, 2]))
    check('variable and default', (m['config']['variable_name'], m['config']['selected_options']), ('monitored_app', [ALL]))
    check('lists In Production + Operational + monitored applications only', control(m['config']['esql_query']),
          [ALL, 'Automated Claim Transaction', 'Juno', 'Silent App'])

    print('Application Health')
    rows = run('Application Health')
    check('all: scoped applications, the one with no telemetry last',
          [(r['ci.name'], r['app_health'] == LABEL) for r in rows],
          [('Automated Claim Transaction', False), ('Juno', False), ('Silent App', True)])
    check('one picked: Juno', [r['ci.name'] for r in run('Application Health', monitored_app='Juno')], ['Juno'])
    check('one picked with no telemetry: Silent App',
          [(r['ci.name'], r['app_health']) for r in run('Application Health', monitored_app='Silent App')], [('Silent App', LABEL)])

    print('Services of the Application')
    svc = lambda **v: sorted(r['service.name'] for r in run('Services of the Application', **v))
    check('all: services of scoped applications only', svc(),
          ['clmact-db-api', 'clmact-event-gen', 'clmact-pymt-subs', 'juno-api', 'juno-tiny-batch'])
    check('Monitored application = Juno', svc(monitored_app='Juno'), ['juno-api', 'juno-tiny-batch'])
    check('section 3 Application = Juno', svc(application='Juno'), ['juno-api', 'juno-tiny-batch'])
    check('section 3 Application = Payment Hub (out of scope): none', svc(application='Payment Hub'), [])
    j = {r['service.name']: r for r in run('Services of the Application')}['juno-api']
    check('juno-api figures unchanged (Degraded, 2 %, 100 tx)', (j['health'], j['error_pct'], j['tx']), ('Degraded', 2.0, 100))

    print('Section 3 lists and layout')
    check('Application list', control(P['Application']['embeddableConfig']['esql_query']),
          ['(all applications)', 'Automated Claim Transaction', 'Juno'])
    check('Service list', control(P['Service']['embeddableConfig']['esql_query']),
          ['(services on this CI)', 'clmact-db-api', 'clmact-event-gen', 'clmact-pymt-subs', 'juno-api', 'juno-tiny-batch'])
    check('Telemetry control removed', ('Telemetry' in P, '?telemetry' in A['panelsJSON']), (False, False))
    row = sorted((p for p in panels if p['type'] == 'esql_control'), key=lambda p: p['gridData']['x'])
    check('section 3 control row', [(p['embeddableConfig']['title'], p['gridData']['x'], p['gridData']['w']) for p in row],
          [('Server', 0, 12), ('Application', 12, 12), ('Service', 24, 12), ('Health window', 36, 12)])
finally:
    cleanup()

print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
