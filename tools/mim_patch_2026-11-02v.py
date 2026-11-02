"""Patch 02v (2 Nov 2026): section 3 controls in the order Server, Application, Telemetry, Service, Health window.

Usage: mim_patch_2026-11-02v.py "MIM V4.ndjson" "MIM V4.ndjson"
Only the five controls' x positions change (same row, same widths); every other line of the file is kept as is.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
ORDER = [('Server', 10), ('Application', 10), ('Telemetry', 10), ('Service', 10), ('Health window', 8)]

lines = [json.loads(l) for l in open(SRC) if l.strip()]
dash = next(o for o in lines if o.get('type') == 'dashboard')
panels = json.loads(dash['attributes']['panelsJSON'])
ctrls = {p['embeddableConfig'].get('title'): p for p in panels if p['type'] == 'esql_control'}
missing = [t for t, _ in ORDER if t not in ctrls]
assert not missing, missing
assert len({ctrls[t]['gridData']['sectionId'] for t, _ in ORDER}) == 1
assert len({ctrls[t]['gridData']['y'] for t, _ in ORDER}) == 1
x = 0
for t, w in ORDER:
    ctrls[t]['gridData'].update(x=x, w=w)
    x += w
assert x <= 48
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
with open(OUT, 'w') as f:
    for o in lines:
        f.write(json.dumps(o, ensure_ascii=False, separators=(',', ':')) + '\n')
print(OUT + ': ' + ' | '.join(f"{t} x{ctrls[t]['gridData']['x']} w{ctrls[t]['gridData']['w']}" for t, _ in ORDER))
