"""MIM V3: Alerts on this CI follows the selected CI only (20 Oct 2026).

Usage: mim_v3_patch_2026-10-20p.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-20o.py)

Since -20o the Server control sits in section 3. Kibana creates section 3's panels, the controls included, only when
they come into view, so the section 2 panel "Alerts on this CI" failed with "Unknown query parameter [server]". It
now uses only the Incident / CI controls, as before 18 Oct: Netcool alerts on the selected CI (any letter case, or
node "<CI>.cna.com"), last 7 days in the query. It no longer reads the CMDB links or CPU data, so the panel range is
Last 1 month, like Escalate (it still reads the picked incident's record for "vs incident").
"""
import json
import sys

SRC, OUT = sys.argv[1:3]

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = lambda t: next(p for p in panels if title(p) == t)
st = lambda p: p['embeddableConfig']['attributes']['state']
layer = lambda p: next(iter(st(p)['datasourceStates']['textBased']['layers'].values()))

SEL = '(CASE(?incident == "(all incidents)", ?ci, SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)))'
NUM = 'CASE(?incident == "(all incidents)", "(all incidents)", SUBSTRING(?incident, 1, LOCATE(?incident, " · ") - 1))'
NC, INC = '.ds-bridge-alerts-netcool-default-*', 'servicenow-incidents-*'

p = P('Alerts on this CI')
q = st(p)['query']['esql']
rest = q[q.index('| EVAL src = CASE(_index LIKE "*servicenow*", "inc", "alert"), g = 1'):]
names = f'({SEL}, TO_UPPER({SEL}), TO_LOWER({SEL}))'
nodes = f'(CONCAT({SEL}, ".cna.com"), CONCAT(TO_LOWER({SEL}), ".cna.com"), CONCAT(TO_UPPER({SEL}), ".cna.com"))'
head = f"""FROM {NC}, {INC} METADATA _index
| WHERE number == {NUM} OR ci.name IN {names} OR node IN {nodes}
| WHERE (_index LIKE "*servicenow*" AND number == {NUM})
     OR (_index LIKE "*netcool*" AND @timestamp >= NOW() - 7 days)
"""
q = head + rest
assert '?server' not in q and '?health_window' not in q
st(p)['query']['esql'] = q
if 'query' in layer(p):
    layer(p)['query']['esql'] = q
idx = f'{NC},{INC}'
for v in st(p).get('adHocDataViews', {}).values():
    v.update(title=idx, name=idx, timeFieldName='@timestamp')
for r in st(p)['datasourceStates']['textBased']['indexPatternRefs']:
    r.update(title=idx, timeField='@timestamp')
ec = p['embeddableConfig']
ec['time_range'] = {'from': 'now-1M', 'to': 'now'}
d = ec['description']
d = d.replace('Netcool alerts on the selected CI and on the chosen server (matched on the CMDB CI, or on the node "<name>.cna.com")',
              'Netcool alerts on the selected CI (matched on the CMDB CI, or on the node "<CI>.cna.com")')
i = d.index(' Which server: as in the health panels')
d = d[:i] + (' Alerts: last 7 days (set in the query), so the alert that triggered the incident stays visible; the panel '
             'shows "Last 1 month" because it also reads the picked incident\'s record, like Escalate. The Server control '
             'does not apply here: it belongs to section 3.')
d = d.replace(' Last 7 days (fixed). Follows the Incident / CI controls.', ' Follows the Incident / CI controls.')
ec['description'] = d

A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print('Alerts on this CI: Incident / CI only;', len(q), 'chars')
