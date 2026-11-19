"""MIM V5 patch 19f (19 Nov 2026): Escalation Channel, Changes in the Last 7 Days on this CI and Open Alerts with No
Incident on one row at the top of section 2 (a third of the width each, same height). The CMDB row moves up under it.
Layout only.

Usage: mim_v5_patch_2026-11-19f.py "MIM V5.ndjson" "MIM V5.ndjson"
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
TOP = [('Escalation Channel', 16), ('Changes in the Last 7 Days on this CI', 16), ('Open Alerts with No Incident', 16)]
CMDB = ['Blast radius', 'Applications related to this CI', 'Server View', 'Middleware View', 'Database View',
        'Other related CIs']
dash = json.loads([l for l in open(SRC) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
P = {p['embeddableConfig'].get('title'): p for p in panels}
sec = P['Escalation Channel']['gridData']['sectionId']
assert all(P[t]['gridData']['sectionId'] == sec for t, _ in TOP) and all(P[t]['gridData']['sectionId'] == sec for t in CMDB)
assert {P[t]['gridData']['y'] for t in CMDB} == {22}, 'patch 19e first'
h = P['Escalation Channel']['gridData']['h']
x = 0
for t, w in TOP:
    P[t]['gridData'].update(x=x, y=0, w=w, h=h)
    x += w
assert x == 48
for t in CMDB:
    P[t]['gridData']['y'] = h
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: Escalation Channel, Changes, Open Alerts with No Incident on one row')
