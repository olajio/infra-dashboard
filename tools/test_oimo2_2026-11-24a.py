"""Check "Observability Incident Management Operations 2" (patch oimo2 24a): Application Health returns the same rows as
the uploaded version's query over the last 5 years, reads far fewer documents, and fills again for an incident whose CMDB
records are older than 24 hours (with the uploaded 24-hour range they were dropped).

Usage: test_oimo2_2026-11-24a.py "Observability Incident Management Operations.ndjson" \
           "Observability Incident Management Operations 2.ndjson"
(local Elasticsearch on port 9200; own data with the suffix t24a, removed at the end unless KEEP_T24A=1)

The three ways Application Health links an application to the picked CI:
  A. the CI is the application itself ("eFile PROD")
  B. a CMDB relation between the CI and a business application (srvT24 -> Billing App), loaded 30 days ago
  C. an APM service of the application runs on the CI as a host (hostT24 runs pay-svc of Pay App)
Every application is in cmdb_with_apm_flag (loaded 3 days ago); APM data older than an hour must not count.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

OLD_FILE, NEW_FILE = sys.argv[1:3]
ES = 'http://localhost:9200'
APP_HEALTH = '066a72ec-21c0-5ed4-8920-c524d3422463'
TX, INT, REL = 'metrics-apm.service_transaction.1m-t24a', 'metrics-apm.internal-t24a', 'cmdb-ci-relations-t24a'
FLAG = 'cmdb_with_apm_flag'
K, D = {'type': 'keyword'}, {'type': 'date'}
obj = lambda **p: {'properties': p}
AMD = {'type': 'aggregate_metric_double', 'metrics': ['sum', 'value_count'], 'default_metric': 'sum'}
NOW = datetime.now(timezone.utc)
ago = lambda **kw: (NOW - timedelta(**kw)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
fails = []


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
    r = call('POST', '/_bulk?refresh=true', ''.join(json.dumps({op: {'_index': index}}) + '\n' + json.dumps(d) + '\n'
                                                    for d in docs), nd=True)
    assert not r.get('errors'), json.dumps(r)[:600]


def check(name, got, want):
    ok = got == want
    print(('  PASS  ' if ok else '  FAIL  ') + name + ': ' + json.dumps(got, ensure_ascii=False, default=str)[:300]
          + ('' if ok else '\n        want: ' + json.dumps(want, ensure_ascii=False, default=str)[:300]))
    if not ok:
        fails.append(name)


def cleanup():
    for ds in (TX, INT):
        call('DELETE', f'/_data_stream/{ds}')
    call('DELETE', f'/{REL}')
    for t in ('t24a-tx', 't24a-int'):
        call('DELETE', f'/_index_template/{t}')
    if 'error' not in call('GET', f'/{FLAG}'):
        call('POST', f'/{FLAG}/_delete_by_query?refresh=true', {'query': {'prefix': {'number.keyword': 'T24A-'}}})


def app_health(f):
    d = next(o for o in (json.loads(l) for l in open(f) if l.strip()) if o.get('type') == 'dashboard')
    p = next(p for p in json.loads(d['attributes']['panelsJSON']) if p['gridData']['i'] == APP_HEALTH)
    return p['embeddableConfig']['attributes']['state']['query']['esql'], p['embeddableConfig']['time_range']


def esql(q, rng, incident='(all incidents)', ci='(no CI selected)', monitored_app='(all monitored applications)'):
    body = {'query': q, 'profile': True, 'filter': {'range': {'@timestamp': {'gte': rng['from'], 'lte': rng['to']}}},
            'params': [{'incident': incident}, {'ci': ci}, {'monitored_app': monitored_app}]}
    r = call('POST', '/_query', body)
    if 'error' in r:
        return json.dumps(r)[:300], 0
    read = sum((op.get('status') or {}).get('rows_emitted', 0) for drv in r['profile']['drivers']
               for op in drv['operators'] if 'Lucene' in op['operator'])
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']], read


cleanup()
try:
    call('PUT', '/_index_template/t24a-tx', {'index_patterns': [TX + '*'], 'data_stream': {}, 'priority': 600, 'template': {
        'mappings': {'properties': {'@timestamp': D, 'service': obj(name=K, environment=K), 'host': obj(name=K),
                                    'ci': obj(name=K, number=K, support_group=obj(l2=obj(name=K))),
                                    'transaction': obj(duration=obj(summary=AMD)), 'event': obj(success_count=AMD)}}}})
    call('PUT', '/_index_template/t24a-int', {'index_patterns': [INT + '*'], 'data_stream': {}, 'priority': 600, 'template': {
        'mappings': {'properties': {'@timestamp': D, 'service': obj(name=K, environment=K), 'host': obj(name=K), 'ci': obj(name=K)}}}})
    tx = lambda svc, app, num, when, n=100, ok=100: {
        '@timestamp': when, 'service': {'name': svc, 'environment': 'prd1'}, 'ci': {'name': app, 'number': num},
        'transaction': {'duration': {'summary': {'sum': 1e6, 'value_count': n}}},
        'event': {'success_count': {'sum': ok, 'value_count': n}}}
    bulk(TX, [tx('efile-api', 'eFile PROD', 'T24A-1', ago(minutes=5)),
              tx('billing-api', 'Billing App', 'T24A-2', ago(minutes=5), ok=85),
              tx('pay-svc', 'Pay App', 'T24A-3', ago(minutes=5)),
              tx('billing-api', 'Billing App', 'T24A-2', ago(hours=3), ok=0)] +          # older than an hour: ignored
         [tx(f'bulk-{i}', 'Old App', 'T24A-9', ago(days=2, minutes=i)) for i in range(300)],  # old APM volume
         op='create')
    bulk(INT, [{'@timestamp': ago(minutes=5), 'service': {'name': 'pay-svc', 'environment': 'prd1'}, 'host': {'name': 'hostT24'}}] +
         [{'@timestamp': ago(days=1, minutes=i), 'service': {'name': f'old-{i}', 'environment': 'prd1'}, 'host': {'name': 'h'}}
          for i in range(300)], op='create')
    side = obj(name=K, **{'class': K})
    call('PUT', f'/{REL}', {'mappings': {'properties': {'@timestamp': D, 'parent': side, 'child': side,
                                                        'is_marked_for_deletion': {'type': 'boolean'}}}})
    rel = lambda p, pc, c, cc: {'@timestamp': ago(days=30), 'parent': {'name': p, 'class': pc}, 'child': {'name': c, 'class': cc}}
    bulk(REL, [rel('Billing App', 'cmdb_ci_business_app', 'srvT24', 'cmdb_ci_server'),
               rel('Billing App', 'cmdb_ci_business_app', 'srvlow24', 'cmdb_ci_server'),
               rel('Q"App', 'cmdb_ci_business_app', 'srv"q\\x', 'cmdb_ci_server')] +
         [rel(f'Other {i}', 'cmdb_ci_business_app', f'srv{i}', 'cmdb_ci_server') for i in range(200)])
    if 'error' in call('GET', f'/{FLAG}'):
        TXT = {'type': 'text', 'fields': {'keyword': {'type': 'keyword'}}}
        call('PUT', f'/{FLAG}', {'mappings': {'properties': {'@timestamp': D, 'name': TXT, 'number': TXT,
             'install_status': TXT, 'operational_status': TXT, 'is_monitored': {'type': 'boolean'}}}})
    flag = lambda name, num: {'@timestamp': ago(days=3), 'name': name, 'number': num, 'is_monitored': True,
                              'install_status': 'In Production', 'operational_status': 'Operational'}
    bulk(FLAG, [flag('eFile PROD', 'T24A-1'), flag('Billing App', 'T24A-2'), flag('Pay App', 'T24A-3'), flag('Old App', 'T24A-9')])

    old_q, old_rng = app_health(OLD_FILE)
    new_q, new_rng = app_health(NEW_FILE)
    check('uploaded version reads 24 hours; new version 5 years', (old_rng['from'], new_rng['from']), ('now-24h', 'now-5y'))
    five = {'from': 'now-5y', 'to': 'now'}
    apps = lambda rows: sorted(r['ci.name'] for r in rows) if isinstance(rows, list) else rows
    CASES = [('A: CI is the application', dict(ci='eFile PROD'), ['eFile PROD']),
             ('A: incident on the application', dict(incident='INC9 · eFile PROD'), ['eFile PROD']),
             ('B: CMDB relation (30 days old)', dict(ci='srvT24'), ['Billing App']),
             ('B: CI stored in lower case, typed in upper case', dict(ci='SRVLOW24'), ['Billing App']),
             ('B: incident on the server', dict(incident='INC9 · srvT24'), ['Billing App']),
             ('C: service runs on the host', dict(ci='hostT24'), ['Pay App']),
             ('CI name with a quote and a backslash', dict(ci='srv"q\\x'), []),
             ('unknown CI', dict(ci='nothing-here'), [])]

    def compare(label):
        tot_old = tot_new = 0
        for name, params, want in CASES + [('no CI: every monitored application', {}, None),
                                           ('no CI, one monitored application', dict(monitored_app='Billing App'), None)]:
            o, ro = esql(old_q, five, **params)
            n, rn = esql(new_q, new_rng, **params)
            tot_old += ro
            tot_new += rn
            check(f'{label} {name}: same rows as the uploaded query over 5 years', n, o)
            if want is not None:
                check(f'{label} {name}: applications', apps(n), want)
        return tot_old, tot_new

    ro, rn = compare('[keyword fields]')
    no_ci = apps(esql(new_q, new_rng)[0])
    check('no CI: the four T24A applications listed', [a for a in no_ci if a in ('eFile PROD', 'Billing App', 'Pay App', 'Old App')],
          ['Billing App', 'Old App', 'Pay App', 'eFile PROD'])
    check('Billing App counts only the last hour (85 % success, not the 3-hour-old failures)',
          [r['app_error_pct'] for r in esql(new_q, new_rng, ci='srvT24')[0]], [15.0])
    print(f'  INFO  documents read over the cases: uploaded query (5 years) {ro}, new query {rn}')
    check('new query reads at most a quarter of the documents', rn * 4 <= ro, True)
    check('root cause: the uploaded 24-hour range loses the relation and flag records (srvT24 -> nothing)',
          apps(esql(old_q, old_rng, ci='srvT24')[0]), [])

    # production: cmdb_with_apm_flag maps these fields as text (APM and the relations as keyword)
    TEXTF = ['ci.name', 'ci.number', 'service.name', 'service.environment', 'host.name', 'parent.name', 'child.name']
    props = {}
    for f in TEXTF:
        a, b = f.split('.')
        props.setdefault(a, {'properties': {}})['properties'][b] = {'type': 'text'}
    r = call('PUT', f'/{FLAG}/_mapping', {'properties': props})
    assert r.get('acknowledged'), r
    call('POST', f'/{FLAG}/_update_by_query?refresh=true', {'query': {'prefix': {'number.keyword': 'T24A-'}}, 'script': {'source':
         "ctx._source.ci = ['name': ctx._source.name, 'number': 'X1']; ctx._source.service = ['name': 'flag-svc', "
         "'environment': 'production']; ctx._source.host = ['name': 'hostT24']; ctx._source.parent = ['name': 'srvT24']; "
         "ctx._source.child = ['name': 'srvT24'];"}})
    compare('[text fields like production]')
finally:
    if not os.environ.get('KEEP_T24A'):
        cleanup()
print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
