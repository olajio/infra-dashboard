"""Check the tenth 16 Oct round: Application Health follows the selected CI; production only in the related-CI
tables, Blast radius, Applications on this CI and Open Alerts with No Incident (blank environment kept); Short
description back in Active Incidents; Changes right after Escalate.

Usage: test_mim_v3_2026-10-16j.py MIM_V3_NDJSON
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
TX, INT, REL = 'metrics-apm.service_transaction.1m-t16j', 'metrics-apm.internal-t16j', 'cmdb-ci-relations-t16j'
NC, INC = '.ds-bridge-alerts-netcool-default-t16j', 'servicenow-incidents-t16j'


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
    for i in (REL, NC, INC):
        call('DELETE', f'/{i}')
    for t in ('t16j-tx', 't16j-int'):
        call('DELETE', f'/_index_template/{t}')


cleanup()
for old in ('servicenow-incidents-t', 'servicenow-incidents-t16', 'servicenow-incidents-t16d', 'servicenow-incidents-t16e',
            'servicenow-incidents-t16f', 'cmdb-ci-relations-t16i'):
    call('DELETE', f'/{old}')
call('PUT', '/_index_template/t16j-tx', {'index_patterns': [TX + '*'], 'data_stream': {}, 'priority': 600, 'template': {
    'mappings': {'properties': {'@timestamp': D, 'service': obj(name=K, environment=K), 'host': obj(name=K),
                                'ci': obj(name=K, number=K, support_group=obj(l2=obj(name=K))),
                                'transaction': obj(duration=obj(summary=AMD)), 'event': obj(success_count=AMD)}}}})
call('PUT', '/_index_template/t16j-int', {'index_patterns': [INT + '*'], 'data_stream': {}, 'priority': 600, 'template': {
    'mappings': {'properties': {'@timestamp': D, 'service': obj(name=K, environment=K), 'host': obj(name=K), 'ci': obj(name=K)}}}})
tx = lambda svc, app, env='prd1', n=100, ok=100: {
    '@timestamp': ago(minutes=5), 'service': {'name': svc, 'environment': env}, 'ci': {'name': app},
    'transaction': {'duration': {'summary': {'sum': 1e6, 'value_count': n}}}, 'event': {'success_count': {'sum': ok, 'value_count': n}}}
bulk(TX, [tx('claim-api', 'Claim Center', ok=80), tx('other-api', 'Other App'), tx('server-svc', 'Server App'),
          tx('claim-dev', 'Claim Dev App', env='ete')], op='create')
bulk(INT, [{'@timestamp': ago(minutes=5), 'service': {'name': 'server-svc', 'environment': 'prd1'}, 'host': {'name': 'vslrau1p276'}},
           {'@timestamp': ago(minutes=5), 'service': {'name': 'dev-svc', 'environment': 'ete'}, 'host': {'name': 'vslrau1p276'}}],
     op='create')
side = obj(name=K, **{'class': K}, environment=K, install_status=K)
call('PUT', f'/{REL}', {'mappings': {'properties': {'@timestamp': D, 'parent': side, 'child': side,
                                                    'type': obj(name=K), 'is_marked_for_deletion': {'type': 'boolean'}}}})
rel = lambda p, pc, c, cc, t, penv='Production', cenv='Production': {
    '@timestamp': '2025-01-01T00:00:00Z', 'type': {'name': t},
    'parent': {'name': p, 'class': pc, 'environment': penv, 'install_status': 'Installed'},
    'child': {'name': c, 'class': cc, 'environment': cenv, 'install_status': 'Installed'}}
CI, SVC, BIZ = 'Claim Center PROD', 'cmdb_ci_service_discovered', 'cmdb_ci_business_app'
bulk(REL, [rel('Claim Center', BIZ, CI, SVC, 'Consumes::Consumed by'),
           rel('Claim Center QA', BIZ, CI, SVC, 'Consumes::Consumed by', penv='QA'),           # not production: out
           rel(CI, SVC, 'vslrau1p276', 'cmdb_ci_linux_server', 'Runs on::Runs'),
           rel(CI, SVC, 'vslqau1q001', 'cmdb_ci_linux_server', 'Runs on::Runs', cenv='Development'),  # out
           rel(CI, SVC, 'lbpool-claim', 'cmdb_ci_lb_pool', 'Depends on::Used by', cenv=None)])        # blank: kept
call('PUT', f'/{NC}', {'mappings': {'properties': {
    '@timestamp': D, 'severity': {'type': 'integer'}, 'message': K, 'node': K, 'first_occurrence': D, 'last_occurrence': D,
    'netcool': obj(type_name=K, acknowledged_name=K, tally={'type': 'integer'}, identifier=K),
    'ci': obj(name=K, class_name=K, environment=K, support_group=obj(l2=obj(name=K)))}}})
al = lambda n, ci, env: {'@timestamp': ago(minutes=10), 'severity': 5, 'message': 'down', 'node': ci or 'unknown-node',
                         'first_occurrence': ago(minutes=30), 'last_occurrence': ago(minutes=10),
                         'netcool': {'type_name': 'problem', 'acknowledged_name': 'no', 'tally': 3, 'identifier': n},
                         'ci': {'name': ci, 'environment': env, 'class_name': 'Linux Server'}}
bulk(NC, [al('a1', 'prodhost', 'Production'), al('a2', 'devhost', 'Development'), al('a3', None, None)])
call('PUT', f'/{INC}', {'mappings': {'properties': {'@timestamp': D, 'number': K, 'priority': {'type': 'integer'},
                                                    'state_name': K, 'opened_at': D, 'short_description': K, 'ci': obj(name=K)}}})
bulk(INC, [{'@timestamp': ago(minutes=1), 'number': 'INC1', 'priority': 2, 'state_name': 'New', 'opened_at': ago(hours=1),
            'short_description': 'Claim Center login fails', 'ci': {'name': 'elsewhere'}}])

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


def run(t, ci='(no CI selected)', incident='(all incidents)'):
    ec = P[t]['embeddableConfig']
    q = ec['attributes']['state']['query']['esql']
    params = [x for x in ({'ci': ci}, {'incident': incident}) if '?' + list(x)[0] in q]
    rng = ec.get('time_range', {}).get('from', 'now-24h')
    r = call('POST', '/_query?format=json', {'query': q, 'params': params,
                                              'filter': {'range': {'@timestamp': {'gte': rng, 'lte': 'now'}}}})
    assert 'error' not in r, (t, json.dumps(r)[:900])
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']]


try:
    apps = lambda ci: sorted(r['ci.name'] for r in run('Application Health', ci=ci))
    allp = apps('(no CI selected)')   # other tests' applications may be present too
    check('Application Health, no CI: every production application, non-production left out',
          ({'Claim Center', 'Other App', 'Server App'} <= set(allp), 'Claim Dev App' in allp), (True, False))
    check('Application Health, application-service CI: its CMDB business application', apps(CI), ['Claim Center'])
    check('Application Health, server CI: applications whose APM services run on it', apps('vslrau1p276'), ['Server App'])
    check('Application Health, business-application CI: itself', apps('Other App'), ['Other App'])
    check('Application Health follows the incident too', sorted(r['ci.name'] for r in run('Application Health', incident=f'INC9 · {CI}')),
          ['Claim Center'])
    rows = lambda t, ci=CI: [r['related_ci'] for r in run(t, ci=ci)]
    check('Applications related to this CI: production only', rows('Applications related to this CI'), ['Claim Center'])
    check('Server View: production only', rows('Server View'), ['vslrau1p276'])
    check('Other related CIs: blank environment kept', rows('Other related CIs'), ['lbpool-claim'])
    check('Blast radius: production applications', [r['value'] for r in run('Blast radius', ci=CI)], [1.0])
    check('Applications on this CI: production services only', [r['application'] for r in run('Applications on this CI', ci='vslrau1p276')],
          ['server-svc'])
    check('Open Alerts with No Incident: production CIs and unmatched nodes', sorted(str(r['ci.name']) for r in run('Open Alerts with No Incident')),
          ['None', 'prodhost'])
    check('Active Incidents: Short description back, last column',
          [c['label'] for c in next(iter(P['Active Incidents (P1 / P2 / P3)']['embeddableConfig']['attributes']['state']
                                         ['datasourceStates']['textBased']['layers'].values()))['columns']][-1], 'Short description')
    sec2 = A['sections'][1]['gridData']['i']
    order = [title(p) for p in sorted(panels, key=lambda p: (p['gridData']['y'], p['gridData']['x'])) if p['gridData']['sectionId'] == sec2]
    check('Changes right after Escalate', order[:3], ['Escalate', 'Changes in the Last 7 Days on this CI', 'Alerts on this CI'])
finally:
    cleanup()
print('\n' + ('ALL CHECKS PASSED' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
