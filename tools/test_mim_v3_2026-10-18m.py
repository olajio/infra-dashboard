"""Check the Servers column (18 Oct): Services of the Application (per service) and Application Health (per
application, all its services): APM agent hosts in the last 15 minutes, production only, sorted, up to 3 then
"+N more", "—" when none; the application filter, the CI selection and the stored queries still work.

Usage: test_mim_v3_2026-10-18m.py MIM_V3_NDJSON
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

ES = 'http://localhost:9200'
NOW = datetime.now(timezone.utc)
ago = lambda **kw: (NOW - timedelta(**kw)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
K, D = {'type': 'keyword'}, {'type': 'date'}
obj = lambda **p: {'properties': p}
AMD = {'type': 'aggregate_metric_double', 'metrics': ['sum', 'value_count'], 'default_metric': 'sum'}
TX, INT, REL = 'metrics-apm.service_transaction.1m-t18m', 'metrics-apm.internal-t18m', 'cmdb-ci-relations-t18m'


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request(ES + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return {'error': json.loads(e.read())}


def bulk(index, docs, op='index'):
    lines = ''.join(json.dumps({op: {'_index': index}}) + '\n' + json.dumps(d) + '\n' for d in docs)
    r = call('POST', '/_bulk?refresh=true', lines, nd=True)
    assert not r.get('errors'), json.dumps(r)[:600]


def cleanup():
    for ds in (TX, INT):
        call('DELETE', f'/_data_stream/{ds}')
    call('DELETE', f'/{REL}')
    for t in ('t18m-tx', 't18m-int'):
        call('DELETE', f'/_index_template/{t}')


cleanup()
call('PUT', '/_index_template/t18m-tx', {'index_patterns': [TX + '*'], 'data_stream': {}, 'priority': 600, 'template': {
    'mappings': {'properties': {'@timestamp': D, 'service': obj(name=K, environment=K), 'host': obj(name=K),
                                'ci': obj(name=K, number=K, support_group=obj(l2=obj(name=K))),
                                'transaction': obj(duration=obj(summary=AMD)), 'event': obj(success_count=AMD)}}}})
call('PUT', '/_index_template/t18m-int', {'index_patterns': [INT + '*'], 'data_stream': {}, 'priority': 600, 'template': {
    'mappings': {'properties': {'@timestamp': D, 'service': obj(name=K, environment=K), 'host': obj(name=K), 'ci': obj(name=K)}}}})
tx = lambda svc, app, env='prd1': {
    '@timestamp': ago(minutes=5), 'service': {'name': svc, 'environment': env}, 'ci': {'name': app},
    'transaction': {'duration': {'summary': {'sum': 1e6, 'value_count': 100}}}, 'event': {'success_count': {'sum': 100, 'value_count': 100}}}
bulk(TX, [tx('m-claim-api', 'M Claim Center'), tx('m-claim-batch', 'M Claim Center'), tx('m-wide-svc', 'M Wide App'),
          tx('m-nohost-svc', 'M Wide App'), tx('m-dev-svc', 'M Dev App', env='ete')], op='create')
host = lambda svc, h, minutes=2, env='prd1': {'@timestamp': ago(minutes=minutes), 'service': {'name': svc, 'environment': env},
                                              'host': {'name': h}}
bulk(INT, [host('m-claim-api', 'SRVB'), host('m-claim-api', 'srva'), host('m-claim-api', 'srva'),
           host('m-claim-batch', 'srvc'),
           host('m-claim-api', 'old-host', minutes=40),             # older than 15 minutes: left out
           host('m-claim-api', 'qa-host', env='ete'),               # not production: left out
           *[host('m-wide-svc', f'w{i}') for i in range(1, 6)]],    # 5 hosts: 3 shown, "+2 more"
     op='create')
side = obj(name=K, **{'class': K}, environment=K, install_status=K)
call('PUT', f'/{REL}', {'mappings': {'properties': {'@timestamp': D, 'parent': side, 'child': side,
                                                    'type': obj(name=K), 'is_marked_for_deletion': {'type': 'boolean'}}}})
bulk(REL, [{'@timestamp': '2025-01-01T00:00:00Z', 'type': {'name': 'Consumes::Consumed by'},
            'parent': {'name': 'M Claim Center', 'class': 'cmdb_ci_business_app', 'environment': 'Production'},
            'child': {'name': 'M Claim Center PROD', 'class': 'cmdb_ci_service_discovered', 'environment': 'Production'}}])

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


def run(t, ci='(no CI selected)', incident='(all incidents)', application='(all applications)'):
    ec = P[t]['embeddableConfig']
    q = ec['attributes']['state']['query']['esql']
    vals = {'ci': ci, 'incident': incident, 'application': application, '_tstart': ago(hours=1), '_tend': ago()}
    params = [{k: v} for k, v in vals.items() if '?' + k in q]
    rng = ec.get('time_range', {}).get('from', 'now-24h')
    r = call('POST', '/_query?format=json', {'query': q, 'params': params,
                                              'filter': {'range': {'@timestamp': {'gte': rng, 'lte': 'now'}}}})
    assert 'error' not in r, (t, json.dumps(r)[:900])
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']], cols


try:
    R, cols = run('Services of the Application')
    svc = {r['service.name']: r for r in R if r['service.name'].startswith('m-')}
    check('Services: columns', cols, ['service.name', 'ci.name', 'servers', 'health', 'error_pct', 'latency_ms', 'per_min', 'tx'])
    check('Services: servers per service (last 15 min, production, lower case, sorted)',
          {s: r['servers'] for s, r in svc.items()},
          {'m-claim-api': 'srva, srvb', 'm-claim-batch': 'srvc', 'm-wide-svc': 'w1, w2, w3 +2 more', 'm-nohost-svc': '—'})
    check('Services: application column and health kept', (svc['m-claim-api']['ci.name'], svc['m-claim-api']['health'],
                                                           svc['m-claim-api']['tx']), ('M Claim Center', 'Healthy', 100))
    check('Services: non-production service left out', 'm-dev-svc' in svc, False)
    check('Services: the Application control still filters', sorted(r['service.name'] for r in
                                                                    run('Services of the Application', application='M Claim Center')[0]),
          ['m-claim-api', 'm-claim-batch'])

    R, cols = run('Application Health')
    app = {r['ci.name']: r for r in R if r['ci.name'].startswith('M ')}
    check('Application Health: Servers after Health', cols[:3], ['ci.name', 'app_health', 'servers'])
    check('Application Health: servers of all the application\'s services',
          {a: r['servers'] for a, r in app.items()}, {'M Claim Center': 'srva, srvb, srvc', 'M Wide App': 'w1, w2, w3 +2 more'})
    check('Application Health: a server CI still lists the applications running on it',
          [r['ci.name'] for r in run('Application Health', ci='srvc')[0]], ['M Claim Center'])
    check('Application Health: a CMDB-linked CI still works', [(r['ci.name'], r['servers']) for r in
                                                              run('Application Health', ci='M Claim Center PROD')[0]],
          [('M Claim Center', 'srva, srvb, srvc')])
    for t in ('Application Health', 'Services of the Application'):
        ec = P[t]['embeddableConfig']
        lay = next(iter(ec['attributes']['state']['datasourceStates']['textBased']['layers'].values()))
        check(f'{t}: layer query matches, Servers column defined', (lay['query']['esql'] == ec['attributes']['state']['query']['esql'],
              [c['label'] for c in lay['columns'] if c['columnId'] == 'servers'],
              [c['columnId'] for c in ec['attributes']['state']['visualization']['columns']].count('servers')), (True, ['Servers'], 1))
    check('Application Health: description explains the 5 years', 'APM data is never read further back than the last hour'
          in P['Application Health']['embeddableConfig']['description'], True)
finally:
    cleanup()
print('\n' + ('ALL CHECKS PASSED' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
