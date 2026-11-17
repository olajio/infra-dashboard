"""Check MIM V5 patch 17e and Infrastructure Overview v2 patch 17b.

1. The production error (es_error.png): cmdb_with_apm_flag gets a ci.name field mapped as text (APM: keyword). Before
   17e, Application Health, Services of the Application and the Application / Service controls fail with "Cannot use
   field [ci.name] due to ambiguities"; after 17e they run, and return the same rows as before the text field existed.
2. MIM section 4 = an identical copy of Infrastructure Overview v2's Dashboard Links section; Infrastructure Overview
   v2: Executive linked (label kept), Infrastructure Overview before Major Incident Management, Portfolio v4's link
   font (## heading), Data freshness gone.

Usage: test_mim_v5_2026-11-17e.py "<MIM V4>.ndjson" "<MIM V5 before 17e>.ndjson" "MIM V5.ndjson"
       "Infrastructure Overview v2.ndjson" pfv4.ndjson
(local Elasticsearch on port 9200; uses the data setup of test_mim_v5_2026-11-06a.py and removes it at the end)
"""
import json
import sys

HERE = __file__.rsplit('/', 1)[0]
V4, BEFORE, V5, IO, PF = sys.argv[1:6]
src = open(f'{HERE}/test_mim_v5_2026-11-06a.py').read().split('\ntry:')[0]
g = {'__name__': 'setup', '__file__': f'{HERE}/test_mim_v5_2026-11-06a.py'}
sys.argv = ['setup', V4, V5]
exec(compile(src, 'test_mim_v5_2026-11-06a.py (data setup)', 'exec'), g)
check, esql, call, cleanup, title, d5 = (g[k] for k in ('check', 'esql', 'call', 'cleanup', 'title', 'd5'))
load = lambda f, i=None: next(json.loads(l) for l in open(f) if l.strip() and (i is None or json.loads(l).get('id') == i))
d_before = load(BEFORE)
FIXED = ('Application Health', 'Services of the Application', 'service', 'application')


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
    before_rows = rows(d_before)
    for k, r in before_rows.items():
        check(f'{k}: runs before the text ci.name exists', isinstance(r, list), True)
    after_rows = rows(d5)
    for k in FIXED:
        check(f'{k}: same rows as before the fix (no text ci.name yet)', after_rows[k], before_rows[k])
    check('Application Health has rows to compare', len(after_rows['Application Health']) > 0, True)

    # production: cmdb_with_apm_flag gets ci.name as text
    r = call('PUT', '/cmdb_with_apm_flag/_mapping', {'properties': {'ci': {'properties': {'name': {'type': 'text'}}}}})
    assert r.get('acknowledged'), r
    call('POST', '/cmdb_with_apm_flag/_update_by_query?refresh=true',
         {'script': {'source': "ctx._source.ci = ['name': ctx._source.name]"}})
    broken = rows(d_before)
    for k in FIXED:
        check(f'{k}: before 17e, fails like production', 'due to ambiguities' in json.dumps(broken[k]), True)
    fixed = rows(d5)
    for k in FIXED:
        check(f'{k}: after 17e, runs and returns the same rows', fixed[k], before_rows[k])
    fixed_app = rows(d5, application='Juno')
    check('Services of the Application with an Application picked: runs',
          isinstance(fixed_app['Services of the Application'], list), True)

    # ---- links ----
    io = load(IO)['attributes']
    io_s2 = next(s for s in io['sections'] if 'Dashboard Links' in s['title'])['gridData']['i']
    io_links = sorted(((p['gridData']['x'], p['gridData']['y'], p['gridData']['w'], p['gridData']['h'], p['type'],
                        p['embeddableConfig']['content'], p['embeddableConfig'].get('hide_title'),
                        json.dumps(p['embeddableConfig'].get('settings')))
                       for p in json.loads(io['panelsJSON']) if p['gridData'].get('sectionId') == io_s2))
    contents = [c for *_, c, _, _ in io_links]
    check('IO: Data freshness removed', any('Data freshness' in json.dumps(p) for p in json.loads(io['panelsJSON'])
                                            if p['gridData'].get('sectionId') == io_s2), False)
    related = [c for x, y, w, h, t, c, *_ in io_links if y == 2]
    check('IO: link tiles 4 rows high (labels not cut off)', {h for x, y, w, h, t, c, *_ in io_links if '](' in c}, {4})
    check('IO: Related Dashboards order', [c.split('[')[1].split(']')[0] for c in related],
          ['Executive Dashboard (In Progress)', 'Portfolio Dashboard ›', 'Applications Operations Dashboard ›',
           'Infrastructure Overview ›', 'Major Incident Management ›'])
    check('IO: Executive and Infrastructure Overview links from links.txt',
          ('(https://kibana-prod.gcp.cna.com/app/r/s/cPJ71)' in related[0], '(https://kibana-prod.gcp.cna.com/app/r/s/bUy3F)' in related[3]),
          (True, True))
    pf = load(PF, '7511c5d1-3326-4c7e-91f4-6c8fdb686ee0')['attributes']
    pf_rel = next(s for s in pf['sections'] if s['title'] == 'Related Dashboards')['gridData']['i']
    pf_links = [p['embeddableConfig']['content'] for p in json.loads(pf['panelsJSON'])
                if p['gridData'].get('sectionId') == pf_rel and '](' in p['embeddableConfig']['content']]
    check("Portfolio v4's link font is a level-2 heading", all(c.startswith('## ') for c in pf_links), True)
    check('IO: every link uses it', [c for c in contents if '](' in c and not c.startswith('## ')], [])
    check('IO: each link row fills the width', [sum(w for x, y, w, *_ in io_links if y == row) for row in (2, 8)], [48, 48])

    a5 = d5['attributes']
    s4 = next(s for s in a5['sections'] if s['gridData']['y'] == 3)
    check('MIM section 4 title', s4['title'], '🔗 4 · Dashboard Links')
    mim_links = sorted(((p['gridData']['x'], p['gridData']['y'], p['gridData']['w'], p['gridData']['h'], p['type'],
                         p['embeddableConfig']['content'], p['embeddableConfig'].get('hide_title'),
                         json.dumps(p['embeddableConfig'].get('settings')))
                        for p in json.loads(a5['panelsJSON']) if p['gridData'].get('sectionId') == s4['gridData']['i']))
    check('MIM section 4 is identical to Infrastructure Overview v2 Dashboard Links', mim_links, io_links)
    check('MIM: old Related dashboards links gone', ('3A7f1' in a5['panelsJSON'], 'uolFV' in a5['panelsJSON']), (False, False))
    ids = [p['panelIndex'] for p in json.loads(a5['panelsJSON'])]
    check('MIM: panel ids unique', len(ids), len(set(ids)))
finally:
    cleanup()
fails = g['fails']
print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
