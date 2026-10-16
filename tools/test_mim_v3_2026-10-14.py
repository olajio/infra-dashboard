"""Load small known data into local Elasticsearch and check the MIM V3 panels changed in the 14 Oct round.

Usage: test_patch.py MIM_V3_NDJSON
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

ES = 'http://localhost:9200'
NOW = datetime.now(timezone.utc)
CI = 'kau1s054'
ALL = '(all incidents)'


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request(ES + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return {'error': json.loads(e.read())}


ago = lambda **kw: (NOW - timedelta(**kw)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
KW, DATE, INT = {'type': 'keyword'}, {'type': 'date'}, {'type': 'integer'}
obj = lambda **p: {'properties': p}


def load(index, docs, mapping=None):
    """mapping None = a data stream (names like metrics-*-* match the built-in data-stream templates)"""
    if mapping is None:
        call('DELETE', f'/_data_stream/{index}')
    else:
        call('DELETE', f'/{index}')
        r = call('PUT', f'/{index}', {'mappings': {'properties': mapping}})
        assert 'error' not in r, (index, r)
    op = 'create' if mapping is None else 'index'
    lines = ''.join(json.dumps({op: {'_index': index}}) + '\n' + json.dumps(d) + '\n' for d in docs)
    r = call('POST', '/_bulk?refresh=true', lines, nd=True)
    assert not r.get('errors'), (index, r)


inc = lambda n, p, state, ci: {'@timestamp': ago(minutes=1), 'number': n, 'priority': p, 'state_name': state,
                               'opened_at': ago(hours=1), 'ci': {'name': ci}}
call('DELETE', '/servicenow-incidents-t16')  # left by the 16 Oct test
load('servicenow-incidents-t', [inc('INC1', 1, 'In Progress', CI), inc('INC1', 1, 'In Progress', CI),  # two syncs
                                inc('INC2', 1, 'New', 'x2'), inc('INC3', 2, 'In Progress', 'x3'),
                                inc('INC4', 2, 'On Hold', 'x4'), inc('INC5', 2, 'In Progress', 'x5'),
                                inc('INC6', 2, 'Resolved', 'x6'), inc('INC7', 3, 'New', 'x7')],
     {'@timestamp': DATE, 'number': KW, 'priority': INT, 'state_name': KW, 'opened_at': DATE, 'ci': obj(name=KW)})

win = lambda m, name, state, ci=CI: {'@timestamp': ago(minutes=m), 'ci': {'name': ci}, 'event': {'module': 'windows'},
                                     'windows': {'service': {'name': name, 'state': state}}}
proc = lambda m, ptype, inst: {'@timestamp': ago(minutes=m), 'ci': {'name': CI}, 'event': {'module': 'system'},
                               'paladin': {'enrichment': {'computed': {'proc_type': ptype, 'proc_instance': inst}}}}
COMP = {'@timestamp': DATE, 'ci': obj(name=KW), 'event': obj(module=KW),
        'windows': obj(service=obj(name=KW, state=KW)),
        'paladin': obj(enrichment=obj(computed=obj(proc_type=KW, proc_instance=KW)))}
load('metrics-windows.service-t', [win(30, 'mssqlserver', 'Running'), win(2, 'mssqlserver', 'Stopped'),
                                   win(2, 'w3svc', 'Running'), win(2, 'oracleservice', 'Running'),
                                   win(2, 'w3svc', 'Stopped', ci='otherci')])
load('metrics-system.process-t', [proc(1, 'ibm_mq_amqzmgr0_positional', 'QM1'), proc(25, 'ibm_ihs', 'HTTPServer01')])
load('metricbeat-t', [{'@timestamp': ago(minutes=2), 'ci': {'name': CI}, 'event': {'module': 'mssql'}}], COMP)

SYS = {'@timestamp': DATE, 'ci': obj(name=KW), 'system': obj(cpu=obj(total=obj(norm=obj(pct={'type': 'double'}))),
                                                               memory=obj(actual=obj(used=obj(pct={'type': 'double'}))),
                                                               filesystem=obj(used=obj(pct={'type': 'double'})))}
load('.ds-metrics-system.cpu-default-t', [{'@timestamp': ago(minutes=1), 'ci': {'name': CI},
                                           'system': {'cpu': {'total': {'norm': {'pct': 0.5}}}}}], SYS)
load('.ds-metrics-system.memory-default-t', [{'@timestamp': ago(minutes=1), 'ci': {'name': CI},
                                              'system': {'memory': {'actual': {'used': {'pct': 0.7}}}}}], SYS)
load('.ds-metrics-system.filesystem-default-t', [{'@timestamp': ago(minutes=1), 'ci': {'name': CI},
                                                  'system': {'filesystem': {'used': {'pct': 0.85}}}}], SYS)

apm = lambda m, svc, host, env: {'@timestamp': ago(**m), 'service': {'name': svc, 'environment': env}, 'host': {'name': host}}
load('metrics-apm.internal-t', [apm({'minutes': 3}, 'policy-admin', CI.upper(), 'prd1'),
                                apm({'days': 3}, 'nightly-batch', CI, 'prd1'),
                                apm({'days': 10}, 'old-service', CI, 'prd1'),
                                apm({'minutes': 3}, 'dmf-api', 'OTHERHOST', 'prd1')])

# ------------------------------------------------------------------ run the queries stored in the dashboard
dash = json.loads(open(sys.argv[1]).readline())
panels = json.loads(dash['attributes']['panelsJSON'])
P = {(p['embeddableConfig'].get('title') or ''): p for p in panels}
fails = []


def run(t, ci=CI, incident=ALL, frm=None):
    ec = P[t]['embeddableConfig']
    q = next(iter(ec['attributes']['state']['datasourceStates']['textBased']['layers'].values()))['query']['esql']
    assert q == ec['attributes']['state']['query']['esql'], t
    params = [x for x in ({'ci': ci}, {'incident': incident}) if '?' + list(x)[0] in q]
    rng = (ec.get('time_range') or {}).get('from', frm or 'now-24h')
    r = call('POST', '/_query?format=json', {'query': q, 'params': params,
                                             'filter': {'range': {'@timestamp': {'gte': rng, 'lte': 'now'}}}})
    assert 'error' not in r, (t, json.dumps(r)[:900])
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']], cols


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" + ('' if ok else f'\n          expected {want!r}'))
    if not ok:
        fails.append(name)


# Active P1 / P2 is a Vega donut since 16 Oct: run its ES|QL, which carries its own one-month window
donut_q = json.loads(P['Active P1 / P2']['embeddableConfig']['savedVis']['params']['spec'])['data'][0]['url']['query']
r = call('POST', '/_query?format=json', {'query': donut_q})
assert 'error' not in r, json.dumps(r)[:900]
check('Active P1 / P2 donut', [tuple(v) for v in r['values']], [(2, 'P1'), (3, 'P2')])
check('Active P1 / P2 window', 'NOW() - 1 month' in donut_q, True)

R, cols = run('Middleware Health')
check('Middleware columns', cols, ['component', 'health', 'minutes_since', 'ci.name'])
check('Middleware rows, Down first', [(r['component'], r['health'], r['ci.name']) for r in R], [
    ('ibm_ihs · HTTPServer01', 'Down', CI), ('ibm_mq_amqzmgr0_positional · QM1', 'Healthy', CI),
    ('w3svc (Windows service)', 'Healthy', CI)])
R, cols = run('Database Health')
check('Database rows, Down first', [(r['component'], r['health']) for r in R], [
    ('mssqlserver (Windows service)', 'Down'), ('SQL Server (mssql metrics)', 'Healthy'),
    ('oracleservice (Windows service)', 'Healthy')])
check('Database follows the incident', run('Database Health', ci='(no CI selected)', incident=f'INC1 · {CI}')[0], R)
check('Middleware with no CI', run('Middleware Health', ci='(no CI selected)')[0], [])

R, cols = run('Server Health')
check('Server Health tiles name the server', [(r['label'], r['value'], r['detail']) for r in R], [
    ('Minutes since last data', 1.0, f'server {CI}'), ('CPU p90 %', 50.0, f'server {CI}'),
    ('Memory peak %', 70.0, f'server {CI}'), ('Fullest disk %', 85.0, f'server {CI}')])

R, cols = run('Applications on this CI')
check('Applications: APM on this server, last 7 days', [(r['application'], r['health'], r['type']) for r in R], [
    ('policy-admin', '3 min ago', 'prd1'), ('nightly-batch', '3 d ago', 'prd1')])

check('banner removed', 'How to use this section' in P, False)
ctrls = sorted(dash['attributes']['pinned_panels']['panels'].values(), key=lambda c: c['order'])
check('controls: Incident, CI, Service first', [c['config']['title'] for c in ctrls][:3], ['Incident', 'CI', 'Service'])
check('time windows', {t: P[t]['embeddableConfig'].get('time_range', {}).get('from') for t in
                       ('Applications on this CI', 'Changes in the Last 7 Days on this CI')},
      {'Applications on this CI': 'now-7d', 'Changes in the Last 7 Days on this CI': 'now-7d'})
check('link cards are links only', [P[t]['embeddableConfig']['content'] for t in ('SRE dashboard', 'Infra dashboard')], [
    '## 🛡️ [Applications Operations Dashboard ›](https://kibana-prod.gcp.cna.com/app/r/s/b4Jas)',
    '## 🖥️ [Infra Dashboard ›](https://kibana-prod.gcp.cna.com/app/r/s/3A7f1)'])
spec = json.loads(P['Users impacted']['embeddableConfig']['savedVis']['params']['spec'])
check('Users impacted demo number', spec['data'][0]['values'][0]['value'], '2,500')

print('\n' + ('ALL CHECKS PASSED' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
