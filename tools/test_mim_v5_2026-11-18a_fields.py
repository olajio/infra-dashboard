"""Check MIM V5 patch 18a, part 5: cmdb_with_apm_flag mapping more fields as text than APM / CMDB relations do.

Production on 18 Nov: "Cannot use field [service.name] due to ambiguities … [keyword] in [.ds-metrics-apm.internal-…]
… [text] in [cmdb_with_apm_flag]" (after ci.name on 17 Nov). Here cmdb_with_apm_flag gets ci.name, service.name,
service.environment, host.name, ci.number, parent.name and child.name as text. Before 18a (the 17e version) Application
Health, Services of the Application and the Application / Service controls fail like production; after 18a they run
and return the same rows as before those fields existed.

Usage: test_mim_v5_2026-11-18a_fields.py "<MIM V4>.ndjson" "<MIM V5 17e>.ndjson" "MIM V5.ndjson"
(local Elasticsearch on port 9200; uses the data setup of test_mim_v5_2026-11-06a.py and removes it at the end)
"""
import json
import sys

HERE = __file__.rsplit('/', 1)[0]
V4, BEFORE, V5 = sys.argv[1:4]
src = open(f'{HERE}/test_mim_v5_2026-11-06a.py').read().split('\ntry:')[0]
g = {'__name__': 'setup', '__file__': f'{HERE}/test_mim_v5_2026-11-06a.py'}
sys.argv = ['setup', V4, V5]
exec(compile(src, 'test_mim_v5_2026-11-06a.py (data setup)', 'exec'), g)
check, esql, call, cleanup, title, d5 = (g[k] for k in ('check', 'esql', 'call', 'cleanup', 'title', 'd5'))
g['DEFAULTS']['priorities'] = ['P1', 'P2', 'P3']
d_before = next(json.loads(l) for l in open(BEFORE) if l.strip())
FIXED = ('Application Health', 'Services of the Application', 'service', 'application')
TEXT = ['service.name', 'service.environment', 'host.name', 'ci.number', 'parent.name', 'child.name']


def queries(d):
    out = {}
    for p in json.loads(d['attributes']['panelsJSON']):
        ec = p['embeddableConfig']
        if p['type'] == 'vis' and title(p) in FIXED:
            out[title(p)] = (ec['attributes']['state']['query']['esql'], ec.get('time_range'))
        elif p['type'] == 'esql_control' and ec.get('variable_name') in FIXED:
            out[ec['variable_name']] = (ec['esql_query'], ec.get('time_range'))
    assert set(out) == set(FIXED), out.keys()
    return out


def rows(d, **v):
    return {k: esql(q, rng, **v) for k, (q, rng) in queries(d).items()}


try:
    base = rows(d_before)
    for k in FIXED:
        check(f'{k}: 17e version runs on the old mapping', isinstance(base[k], list), True)
    check('Application Health has rows to compare', len(base['Application Health']) > 0, True)
    base_app = rows(d_before, ci='srvA')
    props = {}
    for f in ['ci.name'] + TEXT:
        node = props
        parts = f.split('.')
        for part in parts[:-1]:
            node = node.setdefault(part, {'properties': {}})['properties']
        node[parts[-1]] = {'type': 'text'}
    r = call('PUT', '/cmdb_with_apm_flag/_mapping', {'properties': props})
    assert r.get('acknowledged'), r
    call('POST', '/cmdb_with_apm_flag/_update_by_query?refresh=true', {'script': {'source':
         "ctx._source.ci = ['name': ctx._source.name, 'number': 'X1']; ctx._source.service = ['name': 'flag-svc', "
         "'environment': 'production']; ctx._source.host = ['name': 'flag-host']; ctx._source.parent = ['name': 'p']; "
         "ctx._source.child = ['name': 'c'];"}})
    broken = rows(d_before)
    # the two controls already convert these fields where they use them; the two panels fail, as in production
    check('before 18a: Application Health and Services of the Application fail like production',
          sorted(k for k in FIXED if 'due to ambiguities' in json.dumps(broken[k])), ['Application Health', 'Services of the Application'])
    after = rows(d5)
    for k in FIXED:
        check(f'{k}: after 18a, runs and returns the same rows as before', after[k], base[k])
    after_app = rows(d5, ci='srvA')
    for k in FIXED:
        check(f'{k} (CI srvA picked): same rows as before', after_app[k], base_app[k])
finally:
    cleanup()
fails = g['fails']
print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
