"""Load small known data into local Elasticsearch and check the panels changed on 15 Oct (the four related-CI views,
Application Health, Services of the Application, the Application control) and the dashboard settings.

Usage: test_mim_v3_2026-10-15.py MIM_V3_NDJSON
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

ES = 'http://localhost:9200'
NOW = datetime.now(timezone.utc)
iso = lambda dt: dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
ago = lambda **kw: iso(NOW - timedelta(**kw))
ALL_INC, NO_CI, ALL_APPS = '(all incidents)', '(no CI selected)', '(all applications)'


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request(ES + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return {'error': json.loads(e.read())}


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
    assert not r.get('errors'), (index, json.dumps(r)[:800])


KW = {'type': 'keyword'}
TEXT = {'type': 'text', 'fields': {'keyword': KW}}
obj = lambda **p: {'properties': p}

# ------------------------------------------------------------------ CMDB dependency index (no @timestamp)
SIDE = obj(name=TEXT, **{'class': TEXT}, environment=TEXT, install_status=TEXT, operational_status=TEXT)
RUNS, DEPENDS, CONSUMES = '60bc4e22c0a8010e01f074cbe6bd73c3', '1a9cb166f1571100a92eb60da2bce5c5', '41008aa6ef32010098d5925495c0fb94'
side = lambda n, c, oper='1', inst='1': {'name': n, 'class': 'cmdb_ci_' + c, 'environment': 'Production',
                                         'install_status': inst, 'operational_status': oper}
link = lambda p, pc, c, cc, r=RUNS, **kw: {'parent_ci': side(p, pc), 'child_ci': side(c, cc, **kw),
                                           'relationship': {'latest': {'servicenow': {'event': {'type': {'value': r}}}}}}
ACT, SRV = 'Automated Claim Transaction PROD', 'vslrau1p276'
load('cmdb_app_dependencies_v2', [
    link(ACT, 'service_by_tags', SRV, 'linux_server'),                                    # server it runs on
    link(ACT, 'service_by_tags', 'vslrau1p174', 'linux_server', oper='2'),                # non-operational: listed first
    link(ACT, 'service_by_tags', 'CNA1BSYS', 'mainframe_lpar'),
    link(ACT, 'service_by_tags', 'Tomcat@vslrau1p276:8081', 'app_server_tomcat', DEPENDS),  # middleware it uses
    link(ACT, 'service_by_tags', 'oradb01', 'db_ora_instance', DEPENDS),                   # database it uses
    link(ACT, 'service_by_tags', 'P59302', 'batch_job', DEPENDS),                           # not in any group
    link(ACT, 'service_by_tags', 'oldsrv', 'linux_server', inst='7'),                      # retired: left out
    link('Automated Claim Transaction', 'business_app', ACT, 'service_by_tags', CONSUMES),  # application using it
    link('WebSphere@vslrau1p276', 'app_server_websphere', SRV, 'linux_server'),            # seen from the server
    link('mssql@vslrau1p276', 'db_mssql_instance', SRV, 'linux_server'),
    link('cmdb_ci noise', 'storage_volume', SRV, 'linux_server'),                          # not in any group
], {'parent_ci': SIDE, 'child_ci': SIDE,
    'relationship': obj(latest=obj(servicenow=obj(event=obj(type=obj(value=KW)))))})

# ------------------------------------------------------------------ APM transaction metrics with the business application
AMD = {'type': 'aggregate_metric_double', 'metrics': ['sum', 'value_count'], 'default_metric': 'sum'}
tx = lambda m, svc, app, n, ok, env='prd1', us=1e6: {
    '@timestamp': ago(minutes=m), 'service': {'name': svc, 'environment': env}, 'ci': {'name': app, 'number': 'APM-' + app[:3], 'support_group': {'l2': {'name': 'IT.A.' + app[:3]}}},
    'transaction': {'duration': {'summary': {'sum': us, 'value_count': n}}}, 'event': {'success_count': {'sum': ok, 'value_count': n}}}
call('DELETE', '/_index_template/apm-tx-test')
call('PUT', '/_index_template/apm-tx-test', {'index_patterns': ['metrics-apm.service_transaction.1m-test*'],
     'data_stream': {}, 'priority': 500, 'template': {'mappings': {'properties': {
         '@timestamp': {'type': 'date'}, 'service': obj(name=KW, environment=KW), 'ci': obj(name=KW, number=KW, support_group=obj(l2=obj(name=KW))),
         'transaction': obj(duration=obj(summary=AMD)), 'event': obj(success_count=AMD)}}}})
load('metrics-apm.service_transaction.1m-test', [
    tx(5, 'clmact-pymt-subs', 'Automated Claim Transaction', 100, 80),   # 20 % failed -> Failing
    tx(5, 'clmact-db-api', 'Automated Claim Transaction', 100, 97),      # 3 % -> Degraded
    tx(5, 'clmact-event-gen', 'Automated Claim Transaction', 100, 100),  # Healthy
    tx(5, 'juno-api', 'Juno', 100, 98),                                  # Degraded
    tx(5, 'juno-tiny-batch', 'Juno', 4, 2),                              # 50 % failed but 4 calls: Low traffic
    tx(5, 'lonely-svc', 'Quiet App', 3, 0),                              # the app's only service: Low traffic
    tx(5, 'phub-payment', 'Payment Hub', 100, 100),                      # Healthy
    tx(5, 'phub-batch', 'Payment Hub', 50, 50),
    tx(5, 'stage-svc', 'Payment Hub', 100, 0, env='stg1'),               # not production: ignored
    tx(90, 'old-svc', 'Old App', 100, 0),                                # older than the last hour
])

# Application Health also reads the CMDB relationship graph since round j: make sure the index exists (empty)
call('DELETE', '/cmdb-ci-relations-t15')
call('PUT', '/cmdb-ci-relations-t15', {'mappings': {'properties': {
    '@timestamp': {'type': 'date'}, 'is_marked_for_deletion': {'type': 'boolean'}, 'type': obj(name=KW),
    'parent': obj(name=KW, **{'class': KW}, environment=KW, install_status=KW),
    'child': obj(name=KW, **{'class': KW}, environment=KW, install_status=KW)}}})

# ------------------------------------------------------------------ run the stored queries
dash = json.loads(open(sys.argv[1]).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
P = {(p['embeddableConfig'].get('title') or ''): p for p in panels}
fails = []


def esql(q, params, rng=None):
    body = {'query': q, 'params': params}
    if rng:
        body['filter'] = {'range': {'@timestamp': {'gte': rng, 'lte': 'now'}}}
    r = call('POST', '/_query?format=json', body)
    assert 'error' not in r, json.dumps(r)[:900]
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']], cols


def run(t, ci=NO_CI, incident=ALL_INC, application=ALL_APPS):
    ec = P[t]['embeddableConfig']
    q = next(iter(ec['attributes']['state']['datasourceStates']['textBased']['layers'].values()))['query']['esql']
    assert q == ec['attributes']['state']['query']['esql'], t
    vals = {'ci': ci, 'incident': incident, 'application': application, '_tstart': ago(hours=1), '_tend': iso(NOW)}
    params = [{k: v} for k, v in vals.items() if '?' + k in q]
    rng = (ec.get('time_range') or {}).get('from')
    return esql(q, params, None if 'cmdb_app_dependencies' in q else rng)


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" + ('' if ok else f'\n          expected {want!r}'))
    if not ok:
        fails.append(name)


# The related-CI views and the applications table read the full relationship graph since round i (16 Oct):
# their rows are checked by test_mim_v3_2026-10-16i.py.

R, cols = run('Application Health')
check('Application Health: worst first', [(r['ci.name'], r['app_health'], r['failing'], r['degraded'], r['services'],
                                           r['worst_error_pct'], r['app_error_pct']) for r in R], [
    ('Automated Claim Transaction', 'Failing', 1, 1, 3, 20.0, 7.7),
    ('Juno', 'Degraded', 0, 1, 2, 2.0, 3.8),
    ('Payment Hub', 'Healthy', 0, 0, 2, 0.0, 0.0),
    ('Quiet App', 'Low traffic', 0, 0, 1, None, 100.0)])
R, cols = run('Services of the Application', application='Automated Claim Transaction')
check('Services of the picked application, worst first', [(r['service.name'], r['health'], r['error_pct']) for r in R], [
    ('clmact-pymt-subs', 'Failing', 20.0), ('clmact-db-api', 'Degraded', 3.0), ('clmact-event-gen', 'Healthy', 0.0)])
check('Services with no application picked', len(run('Services of the Application')[0]), 8)
check('low-traffic services are listed, not rated', [(r['service.name'], r['health'], r['error_pct']) for r in
      run('Services of the Application', application='Juno')[0]], [('juno-api', 'Degraded', 2.0),
                                                                    ('juno-tiny-batch', 'Low traffic', 50.0)])

ctrl = next(c for c in A['pinned_panels']['panels'].values() if c['config']['variable_name'] == 'application')
check('Application control options', [r['application'] for r in esql(ctrl['config']['esql_query'], [])[0]],
      [ALL_APPS, 'Automated Claim Transaction', 'Juno', 'Old App', 'Payment Hub', 'Quiet App'])
check('controls in order', [c['config']['title'] for c in sorted(A['pinned_panels']['panels'].values(),
                                                                 key=lambda c: c['order'])],
      ['Incident', 'CI', 'Service', 'Application'])
check('sections', [(s['title'], s['collapsed']) for s in A['sections']], [
    ('1 · Major Incident Overview', False), ('2 · Investigate the CI', False),   # views moved into 2 in round h
    ('3 · Application & Service Health, Dependencies', False), ('4 · Related dashboards', False)])
check('default time', (A['timeFrom'], A['timeTo']), ('now-24h', 'now'))
check('no extra filter control', [p['type'] for p in panels if p['type'] == 'options_list_control'], [])

print('\n' + ('ALL CHECKS PASSED' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
