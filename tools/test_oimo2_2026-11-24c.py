"""Check patch oimo2 24c: Downstream and Upstream return the same rows as before and read fewer documents (Downstream at
most a third); Services of the Application returns the same rows as its query over 5 years, reads no more, and lists
its services again when cmdb_with_apm_flag was loaded more than 24 hours ago.

Usage: test_oimo2_2026-11-24c.py "<dashboard before 24c>.ndjson" "Observability Incident Management Operations 2.ndjson"
(local Elasticsearch on port 9200; own data with the suffix t24c, removed at the end unless KEEP_T24C=1)
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

OLD_FILE, NEW_FILE = sys.argv[1:3]
ES = 'http://localhost:9200'
TR, DST, INT, TX = ('traces-apm-t24c', 'metrics-apm.service_destination.1m-t24c', 'metrics-apm.internal-t24c',
                    'metrics-apm.service_transaction.1m-t24c')
FLAG = 'cmdb_with_apm_flag'
K, D, L = {'type': 'keyword'}, {'type': 'date'}, {'type': 'long'}
obj = lambda **p: {'properties': p}
AMD = {'type': 'aggregate_metric_double', 'metrics': ['sum', 'value_count'], 'default_metric': 'sum'}
NOW = datetime.now(timezone.utc)
ago = lambda **kw: (NOW - timedelta(**kw)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
fails = []
DEF = {'incident': '(all incidents)', 'ci': '(no CI selected)', 'service': '(services on this CI)',
       'application': '(all applications)', 'monitored_app': '(all monitored applications)'}


def call(method, path, body=None, nd=False):
    data = None if body is None else (body if nd else json.dumps(body)).encode()
    req = urllib.request.Request(ES + path, data=data, method=method,
                                 headers={'Content-Type': 'application/x-ndjson' if nd else 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return {'error': json.loads(e.read())}


def bulk(index, docs, op='create'):
    r = call('POST', '/_bulk?refresh=true', ''.join(json.dumps({op: {'_index': index}}) + '\n' + json.dumps(d) + '\n'
                                                    for d in docs), nd=True)
    assert not r.get('errors'), json.dumps(r)[:600]


def check(name, got, want):
    ok = got == want
    print(('  PASS  ' if ok else '  FAIL  ') + name + ': ' + json.dumps(got, ensure_ascii=False, default=str)[:260]
          + ('' if ok else '\n        want: ' + json.dumps(want, ensure_ascii=False, default=str)[:260]))
    if not ok:
        fails.append(name)


def cleanup():
    for ds in (TR, DST, INT, TX):
        call('DELETE', f'/_data_stream/{ds}')
    for t in ('t24c-tr', 't24c-dst', 't24c-int', 't24c-tx'):
        call('DELETE', f'/_index_template/{t}')
    if 'error' not in call('GET', f'/{FLAG}'):
        call('POST', f'/{FLAG}/_delete_by_query?refresh=true', {'query': {'prefix': {'number.keyword': 'T24C-'}}})


def panel(f, title):
    d = next(o for o in (json.loads(l) for l in open(f) if l.strip()) if o.get('type') == 'dashboard')
    p = next(p for p in json.loads(d['attributes']['panelsJSON'])
             if (p['embeddableConfig'].get('attributes') or {}).get('title') == title)
    return p['embeddableConfig']['attributes']['state']['query']['esql'], p['embeddableConfig']['time_range']


def esql(q, rng, **v):
    v = dict(DEF, **v)
    names = [n for n in ('incident', 'ci', 'service', 'application', 'monitored_app') if '?' + n in q]
    body = {'query': q, 'profile': True, 'filter': {'range': {'@timestamp': {'gte': rng['from'], 'lte': rng['to']}}},
            'params': [{n: v[n]} for n in names]}
    r = call('POST', '/_query', body)
    if 'error' in r:
        return json.dumps(r)[:300], 0
    read = sum((op.get('status') or {}).get('rows_emitted', 0) for drv in r['profile']['drivers']
               for op in drv['operators'] if 'Lucene' in op['operator'])
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, x)) for x in r['values']], read


def template(name, pattern, props):
    call('PUT', f'/_index_template/{name}', {'index_patterns': [pattern + '*'], 'data_stream': {}, 'priority': 600,
                                             'template': {'mappings': {'properties': dict({'@timestamp': D}, **props)}}})


cleanup()
try:
    template('t24c-tr', TR, {'processor': obj(event=K), 'transaction': obj(type=K), 'url': obj(domain=K),
                             'host': obj(name=K), 'service': obj(name=K, environment=K)})
    template('t24c-dst', DST, {'service': obj(name=K, environment=K, target=obj(type=K)), 'event': obj(outcome=K),
                               'span': obj(destination=obj(service=obj(resource=K, response_time=obj(count=L, sum=obj(us=L))))),
                               'ci': obj(name=K, support_group=obj(l2=obj(name=K)))})
    template('t24c-int', INT, {'service': obj(name=K, environment=K), 'host': obj(name=K), 'ci': obj(name=K)})
    template('t24c-tx', TX, {'service': obj(name=K, environment=K), 'host': obj(name=K),
                             'ci': obj(name=K, number=K, support_group=obj(l2=obj(name=K))),
                             'transaction': obj(duration=obj(summary=AMD)), 'event': obj(success_count=AMD)})
    # Upstream: hostU runs svc-a (prd1) and svc-b ("PRD1"); svc-ete runs there too but is not production
    intd = lambda svc, host, env='prd1', **kw: {'@timestamp': ago(minutes=kw.get('m', 5)), 'service': {'name': svc, 'environment': env},
                                                'host': {'name': host}}
    bulk(INT, [intd('svc-a', 'hostU'), intd('svc-b', 'hostU', 'PRD1'), intd('svc-ete', 'hostU', 'ete'), intd('svc-z', 'HOSTZ'),
               intd('svc-q', 'srv"q\\x'), intd('pay-svc', 'hostT24', m=5)] +
         [intd(f'noise-{i}', f'h{i}', m=i % 50 + 1) for i in range(400)] +
         [intd(f'old-{i}', f'h{i}', m=60 * 3 + i) for i in range(200)])          # hours old: outside every window
    dst = lambda svc, res, n, bad=0, env='prd1', ci='App', m=5: [
        {'@timestamp': ago(minutes=m), 'service': {'name': svc, 'environment': env, 'target': {'type': 'db'}},
         'event': {'outcome': 'success'}, 'ci': {'name': ci, 'support_group': {'l2': {'name': 'Team ' + ci}}},
         'span': {'destination': {'service': {'resource': res, 'response_time': {'count': n - bad, 'sum': {'us': (n - bad) * 2000}}}}}},
        {'@timestamp': ago(minutes=m), 'service': {'name': svc, 'environment': env, 'target': {'type': 'db'}},
         'event': {'outcome': 'failure'}, 'ci': {'name': ci, 'support_group': {'l2': {'name': 'Team ' + ci}}},
         'span': {'destination': {'service': {'resource': res, 'response_time': {'count': bad, 'sum': {'us': bad * 9000}}}}}}]
    bulk(DST, dst('svc-a', 'pg.cna.com:5432', 100, 5) + dst('svc-b', 'api.cna.com:443', 50) + dst('svc-ete', 'x.cna.com', 9, env='ete')
         + dst('svc-z', 'z.cna.com:80', 30, 1) + dst('svc-c', 'web1.cna.com:443', 80, 20, ci='Caller App')
         + dst('svc-d', 'web1', 40, ci='Other Caller') + dst('web-svc', 'web1.cna.com:443', 7)        # its own calls: left out
         + [x for i in range(150) for x in dst(f'noise-{i}', f'n{i}.cna.com:443', 10, m=i % 50 + 1)])
    # Downstream: web-svc on hostD serves web1.cna.com
    tr = lambda svc, host, dom, ev='transaction', tt='request', env='prd1', m=5: {
        '@timestamp': ago(minutes=m), 'processor': {'event': ev}, 'transaction': {'type': tt}, 'url': {'domain': dom},
        'host': {'name': host}, 'service': {'name': svc, 'environment': env}}
    bulk(TR, [tr('web-svc', 'hostD', 'web1.cna.com'), tr('web-svc', 'hostD', 'web1'), tr('web-svc', 'hostD', 'web1.cna.com', ev='span'),
              tr('z-web', 'HOSTZ', 'z.cna.com')] +
         [tr(f'noise-{i}', f'h{i}', f'n{i}.cna.com', m=i % 50 + 1) for i in range(600)] +
         [tr(f'noise-{i}', f'h{i}', None, ev='span', m=i % 50 + 1) for i in range(300)])
    # Services of the Application: Pay App, enrolled in cmdb_with_apm_flag 3 days ago
    txd = lambda svc, app, num, m=5: {'@timestamp': ago(minutes=m), 'service': {'name': svc, 'environment': 'prd1'},
                                      'ci': {'name': app, 'number': num}, 'transaction': {'duration': {'summary': {'sum': 1e6, 'value_count': 100}}},
                                      'event': {'success_count': {'sum': 97, 'value_count': 100}}}
    bulk(TX, [txd('pay-svc', 'Pay App', 'T24C-3'), txd('bill-svc', 'Bill App', 'T24C-4')] +
         [txd(f'old-{i}', 'Pay App', 'T24C-3', m=90 + i) for i in range(200)])    # older than an hour
    if 'error' in call('GET', f'/{FLAG}'):
        TXT = {'type': 'text', 'fields': {'keyword': {'type': 'keyword'}}}
        call('PUT', f'/{FLAG}', {'mappings': {'properties': {'@timestamp': D, 'name': TXT, 'number': TXT,
             'install_status': TXT, 'operational_status': TXT, 'is_monitored': {'type': 'boolean'}}}})
    flag = lambda name, num: {'@timestamp': ago(days=3), 'name': name, 'number': num, 'is_monitored': True,
                              'install_status': 'In Production', 'operational_status': 'Operational'}
    bulk(FLAG, [flag('Pay App', 'T24C-3'), flag('Bill App', 'T24C-4')], op='index')

    CASES = {
        '⬅ Upstream — what they depend on': [
            ('CI hostU (svc-a, svc-b)', dict(ci='hostU'), ['api.cna.com:443', 'pg.cna.com:5432']),
            ('incident on hostU', dict(incident='INC1 · hostU'), ['api.cna.com:443', 'pg.cna.com:5432']),
            ('CI typed in lower case, host stored in upper case', dict(ci='hostz'), ['z.cna.com:80']),
            ('service picked', dict(service='svc-a'), ['pg.cna.com:5432']),
            ('nothing picked', {}, []),
            ('CI name with a quote and a backslash', dict(ci='srv"q\\x'), [])],
        'Downstream — who is impacted ➡': [
            ('CI hostD (web-svc)', dict(ci='hostD'), ['svc-c', 'svc-d']),
            ('service picked', dict(service='web-svc'), ['svc-c', 'svc-d']),
            ('CI typed in lower case, host stored in upper case', dict(ci='hostz'), ['svc-z']),
            ('nothing picked', {}, []),
            ('CI name with a quote and a backslash', dict(ci='srv"q\\x'), [])],
        'Services of the Application': [
            ('all applications', {}, None),
            ('one application', dict(application='Pay App'), ['pay-svc']),
            ('one monitored application', dict(monitored_app='Bill App'), ['bill-svc'])]}
    key = {'⬅ Upstream — what they depend on': 'dependency', 'Downstream — who is impacted ➡': 'service.name',
           'Services of the Application': 'service.name'}

    def compare(label, panels):
        for t in panels:
            oq, orng = panel(OLD_FILE, t)
            nq, nrng = panel(NEW_FILE, t)
            ro = rn = 0
            five = {'from': 'now-5y', 'to': 'now'}
            for name, v, want in CASES[t]:
                o, a = esql(oq, five if t.startswith('Services') else orng, **v)
                n, b = esql(nq, nrng, **v)
                ro, rn = ro + a, rn + b
                check(f'{label} {t[:24]} / {name}: same rows as before', n, o)
                if want is not None:
                    got = sorted(r[key[t]] for r in n) if isinstance(n, list) else n
                    check(f'{label} {t[:24]} / {name}: rows', [x for x in got if not str(x).startswith('noise')], want)
            print(f'  INFO  {label} {t}: documents read before {ro}, after {rn}')
            if t.startswith('Downstream'):
                check(f'{label} {t[:24]}: reads at most a third of the documents', rn * 3 <= ro, True)
            elif t.startswith('Services'):
                check(f'{label} {t[:24]}: reads no more documents than before', rn <= ro, True)
            else:
                check(f'{label} {t[:24]}: reads fewer documents', rn < ro, True)

    compare('[keyword]', CASES)
    oq, orng = panel(OLD_FILE, 'Services of the Application')
    nq, nrng = panel(NEW_FILE, 'Services of the Application')
    check('Services of the Application: range 24 h before, 5 years now', (orng['from'], nrng['from']), ('now-24h', 'now-5y'))
    check('root cause: with the 24-hour range the 3-day-old flag records drop out (Pay App lists nothing)',
          esql(oq, orng, application='Pay App')[0], [])
    # production: cmdb_with_apm_flag maps these fields as text
    props = {}
    for f in ['ci.name', 'ci.number', 'service.name', 'service.environment', 'host.name']:
        a, b = f.split('.')
        props.setdefault(a, {'properties': {}})['properties'][b] = {'type': 'text'}
    assert call('PUT', f'/{FLAG}/_mapping', {'properties': props}).get('acknowledged')
    call('POST', f'/{FLAG}/_update_by_query?refresh=true', {'query': {'prefix': {'number.keyword': 'T24C-'}}, 'script': {'source':
         "ctx._source.ci = ['name': ctx._source.name, 'number': 'X1']; ctx._source.service = ['name': 'flag-svc', "
         "'environment': 'production']; ctx._source.host = ['name': 'hostU'];"}})
    compare('[text fields like production]', ['Services of the Application'])
finally:
    if not os.environ.get('KEEP_T24C'):
        cleanup()
print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
