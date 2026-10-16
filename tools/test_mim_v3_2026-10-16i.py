"""Check the ninth 16 Oct round: related CIs and applications come from the full CMDB relationship graph with no blind
spots (both directions, every class, retired marked, other name case, old records, deleted links left out), one
applications table, Blast radius from the same graph, and "Times fired".

Usage: test_mim_v3_2026-10-16i.py MIM_V3_NDJSON
"""
import json
import sys
import urllib.request

ES = 'http://localhost:9200'
IDX = 'cmdb-ci-relations-t16i'
CI = 'Claim Center PROD'


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request(ES + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return {'error': json.loads(e.read())}


K = {'type': 'keyword'}
side = {'properties': {f: K for f in ('name', 'class', 'environment', 'install_status', 'operational_status', 'sys_id')}}
call('DELETE', f'/{IDX}')
assert 'error' not in call('PUT', f'/{IDX}', {'mappings': {'properties': {
    '@timestamp': {'type': 'date'}, 'parent': side, 'child': side, 'type': {'properties': {'name': K}},
    'is_marked_for_deletion': {'type': 'boolean'}}}})
rel = lambda p, pc, c, cc, t, ts='2026-10-10T00:00:00Z', ps='Installed', cs='Installed', deleted=False: {
    '@timestamp': ts, 'type': {'name': t}, 'is_marked_for_deletion': deleted,
    'parent': {'name': p, 'class': pc, 'install_status': ps, 'environment': 'Production'},
    'child': {'name': c, 'class': cc, 'install_status': cs, 'environment': 'Production'}}
SVC, BIZ = 'cmdb_ci_service_discovered', 'cmdb_ci_business_app'
docs = [
    rel('Claim Center', BIZ, CI, SVC, 'Consumes::Consumed by'),                           # app above (the example)
    rel(CI, SVC, 'Claim Center Billing', BIZ, 'Depends on::Used by'),                      # business app below
    rel('Claim Center API PROD', 'cmdb_ci_service_by_tags', CI, SVC, 'Depends on::Used by'),
    rel(CI, SVC, 'vslrau1p276', 'cmdb_ci_linux_server', 'Runs on::Runs'),
    rel(CI, SVC, 'vslrau1p174', 'cmdb_ci_linux_server', 'Runs on::Runs', cs='Retired'),    # retired: shown, marked
    rel(CI, SVC, 'Tomcat@vslrau1p276:8081', 'cmdb_ci_app_server_tomcat', 'Depends on::Used by'),
    rel(CI, SVC, 'oradb01', 'cmdb_ci_db_ora_instance', 'Depends on::Used by', ts='2024-02-01T00:00:00Z'),  # old record
    rel(CI, SVC, 'lbpool-claim', 'cmdb_ci_lb_pool', 'Depends on::Used by'),                # class in no list
    rel('claim center prod', SVC, 'vm-claim-01', 'cmdb_ci_vmware_instance', 'Runs on::Runs'),  # lower-case name
    rel(CI, SVC, 'old-db', 'cmdb_ci_db_ora_instance', 'Depends on::Used by', deleted=True),    # marked for deletion
    rel('Other App', BIZ, 'unrelated', SVC, 'Consumes::Consumed by')]
lines = ''.join(json.dumps({'index': {'_index': IDX}}) + '\n' + json.dumps(d) + '\n' for d in docs)
assert not call('POST', '/_bulk?refresh=true', lines, nd=True).get('errors')

dash = json.loads(open(sys.argv[1]).readline())
panels = json.loads(dash['attributes']['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = {title(p): p for p in panels}
fails = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" + ('' if ok else f'\n          expected {want!r}'))
    if not ok:
        fails.append(name)


def run(t, ci=CI, incident='(all incidents)'):
    ec = P[t]['embeddableConfig']
    q = ec['attributes']['state']['query']['esql']
    rng = ec['time_range']['from']
    r = call('POST', '/_query?format=json', {'query': q, 'params': [{'ci': ci}, {'incident': incident}],
                                              'filter': {'range': {'@timestamp': {'gte': rng, 'lte': 'now'}}}})
    assert 'error' not in r, (t, json.dumps(r)[:900])
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']]


row = lambda r: (r['related_ci'], r['ci_type'], r['relation'])
try:
    check('Applications related to this CI: both directions, all kinds', [row(r) for r in run('Applications related to this CI')], [
        ('Claim Center', 'Business application', 'it consumes this CI'),
        ('Claim Center Billing', 'Business application', 'this CI depends on it'),
        ('Claim Center API PROD', 'Application service', 'it depends on this CI')])
    check('Server View: retired shown last and marked', [row(r) for r in run('Server View')], [
        ('vslrau1p276', 'Linux Server', 'this CI runs on it'), ('vslrau1p174', 'Linux Server · retired', 'this CI runs on it')])
    check('Middleware View', [row(r) for r in run('Middleware View')], [('Tomcat@vslrau1p276:8081', 'Tomcat', 'this CI depends on it')])
    check('Database View: 2024 record shown, deleted link left out', [row(r) for r in run('Database View')],
          [('oradb01', 'Oracle Instance', 'this CI depends on it')])
    check('Other related CIs: classes in no list, lower-case name matched', [row(r) for r in run('Other related CIs')], [
        ('lbpool-claim', 'lb pool', 'this CI depends on it'), ('vm-claim-01', 'vmware instance', 'this CI runs on it')])
    check('views follow the incident', run('Server View', ci='(no CI selected)', incident=f'INC1 · {CI}'), run('Server View'))
    check('empty with no CI', [len(run(t, ci='(no CI selected)')) for t in ('Applications related to this CI', 'Server View', 'Other related CIs')], [0, 0, 0])
    br = run('Blast radius')
    check('Blast radius: applications above the CI', [(r['value'], r['detail']) for r in br],
          [(2.0, 'business apps 1 · app services 1')])  # instances shown only when > 0
    check('every related-CI panel has the 5-year range and reads the full graph',
          sorted({(json.dumps(P[t]['embeddableConfig']['time_range']), 'cmdb-ci-relations*' in P[t]['embeddableConfig']['attributes']['state']['query']['esql'])
                  for t in ('Applications related to this CI', 'Middleware View', 'Database View', 'Server View', 'Other related CIs', 'Blast radius')}),
          [('{"from": "now-5y", "to": "now"}', True)])
    check('Application View removed, merged table has no ServiceNow link',
          ('Application View' in P, 'drilldowns' in P['Applications related to this CI']['embeddableConfig']), (False, False))
    labels = lambda t: [c['label'] for c in next(iter(P[t]['embeddableConfig']['attributes']['state']['datasourceStates']['textBased']['layers'].values()))['columns']]
    check('"Times fired" instead of "Count"', ['Times fired' in labels(t) and 'Count' not in labels(t)
                                              for t in ('Open Alerts with No Incident', 'Alerts on this CI')], [True, True])
finally:
    call('DELETE', f'/{IDX}')
print('\n' + ('ALL CHECKS PASSED' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
