"""List, for every panel with drilldowns, the query and the link columns (dimension columns a click comes from)."""
import json, sys
o = json.loads(open(sys.argv[1]).readline())
out = []
for p in json.loads(o['attributes']['panelsJSON']):
    ec = p['embeddableConfig']
    if not ec.get('drilldowns') or 'attributes' not in ec:
        continue
    st = ec['attributes']['state']
    L = next(iter(st['datasourceStates']['textBased']['layers'].values()))
    vis = st['visualization']
    if 'columns' in vis:
        cols = [c['columnId'] for c in vis['columns'] if c.get('isMetric') is False]
    elif 'breakdownByAccessor' in vis:
        cols = [vis['breakdownByAccessor']]
    else:
        cols = [vis['layers'][0].get('xAccessor')]
    out.append({'title': ec.get('title'), 'query': L['query']['esql'], 'cols': cols})
json.dump(out, open(sys.argv[2], 'w'))
print(len(out), 'linked panels')
