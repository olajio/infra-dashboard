"""MIM V5 patch 13a (13 Nov 2026), on top of patch 11a: remove the SLA column from Active Incidents (team request).

Usage: mim_v5_patch_2026-11-13a.py "MIM V5.ndjson" "MIM V5.ndjson"
The column goes from the table, the layer and the query's KEEP; the description drops the SLA paragraph. The rows,
their order and every other column stay the same.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
dash = json.loads([l for l in open(SRC) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
p = next(p for p in panels if (p['embeddableConfig'].get('title') or '').startswith('Active Incidents'))
ec = p['embeddableConfig']
st = ec['attributes']['state']
q = st['query']['esql']
old_keep = 'KEEP number, priority, ci.name, state_name, opened, sla, assignment_group'
assert q.count(old_keep) == 1, 'already removed?'
q = q.replace(old_keep, 'KEEP number, priority, ci.name, state_name, opened, assignment_group')
st['query']['esql'] = q
st['visualization']['columns'] = [c for c in st['visualization']['columns'] if c['columnId'] != 'sla']
for layer in st['datasourceStates']['textBased']['layers'].values():
    layer['query'] = {'esql': q}
    for k in ('columns', 'allColumns'):
        if k in layer:
            layer[k] = [c for c in layer[k] if c.get('columnId', c.get('name')) != 'sla']
sla_txt = ec['description'][ec['description'].index(' SLA = the worst'):ec['description'].index(' Assignee and Group Manager')]
ec['description'] = ec['description'].replace(sla_txt, '')
assert '"sla"' not in json.dumps(st)
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: SLA column removed from {ec["title"]}')
