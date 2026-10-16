"""Check the second 16 Oct round: no CMDB status in the four related-CI views, transparent first-row tiles with theme
text colours. Run the 15 Oct test first (it loads the dependency data the views read).

Usage: test_mim_v3_2026-10-16b.py MIM_V3_NDJSON
"""
import json
import sys
import urllib.request

ES = 'http://localhost:9200'
ACT = 'Automated Claim Transaction PROD'   # application service loaded by the 15 Oct test

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


def esql(q, params):
    req = urllib.request.Request(ES + '/_query?format=json', data=json.dumps({'query': q, 'params': params}).encode(),
                                 method='POST', headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as r:
        r = json.loads(r.read())
    cols = [c['name'] for c in r['columns']]
    return [dict(zip(cols, v)) for v in r['values']], cols


for t in ('Middleware View', 'Database View', 'Server View', 'Application View'):
    ec = P[t]['embeddableConfig']
    L = next(iter(ec['attributes']['state']['datasourceStates']['textBased']['layers'].values()))
    rows, cols = esql(L['query']['esql'], [{'ci': ACT}, {'incident': '(all incidents)'}])
    check(f'{t}: query columns', cols, ['related_ci', 'ci_type', 'relation', 'related_env'])
    check(f'{t}: table columns', [c['label'] for c in L['columns']], ['Related CI', 'Type', 'Relationship', 'Env'])
    check(f'{t}: no status anywhere', 'CMDB status' in json.dumps(P[t]) or 'operational status' in ec['description'],
          False)
rows, _ = esql(next(iter(P['Server View']['embeddableConfig']['attributes']['state']['datasourceStates']['textBased']
                         ['layers'].values()))['query']['esql'], [{'ci': ACT}, {'incident': '(all incidents)'}])
check('Server View: non-operational CI still listed, sorted by type then name', [r['related_ci'] for r in rows],
      ['vslrau1p174', 'vslrau1p276', 'CNA1BSYS'])

for t in ('Active P1 / P2', 'Users impacted'):
    spec = json.loads(P[t]['embeddableConfig']['savedVis']['params']['spec'])
    marks = spec['marks'] if t == 'Active P1 / P2' else spec['marks'][0]['marks']
    texts = [m for m in marks if m['type'] == 'text']
    check(f'{t}: no background', ('background' in spec, '#000000' in json.dumps(spec)), (False, False))
    check(f'{t}: text uses theme colours',
          [m.get('style') or m['encode']['update']['fill'].get('scale') for m in texts],
          ['guide-title', 'guide-label', 'colour'] if t == 'Active P1 / P2' else
          ['guide-label', 'guide-label', 'guide-label', 'guide-title'])
spec = json.loads(P['Active P1 / P2']['embeddableConfig']['savedVis']['params']['spec'])
check('donut colours match the priority badges', spec['scales'][0]['range'], ['#d6453d', '#c98a0b'])
check('Users impacted group not filled', 'fill' in json.loads(P['Users impacted']['embeddableConfig']['savedVis']['params']
                                                               ['spec'])['marks'][0]['encode']['update'], False)
print('\n' + ('ALL CHECKS PASSED' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
