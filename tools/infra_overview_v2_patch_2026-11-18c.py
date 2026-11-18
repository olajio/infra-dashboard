"""Infrastructure Overview v2, patch 18c (18 Nov 2026): shorter link names in Dashboard Links.

Usage: infra_overview_v2_patch_2026-11-18c.py "Infrastructure Overview v2.ndjson" "Infrastructure Overview v2.ndjson"

Executive Dashboard (In Progress) -> Executive (In Progress) (still text, no link); Cloud Infra Dashboard -> Cloud
Infra; Database Infra Dashboard -> Database Infra; Middleware Dashboard -> Middleware; Server Infra Dashboard ->
Server Infra. Links, font and layout unchanged.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
lines = [l for l in open(SRC) if l.strip()]
dash = json.loads(lines[0])
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
S2 = next(s['gridData']['i'] for s in A['sections'] if 'Dashboard Links' in s['title'])
REN = {'Executive link': ('## 📈 Executive Dashboard (In Progress)', '## 📈 Executive (In Progress)'),
       'Cloud Infra link': ('[Cloud Infra Dashboard ›]', '[Cloud Infra ›]'),
       'Database Infra link': ('[Database Infra Dashboard ›]', '[Database Infra ›]'),
       'Middleware link': ('[Middleware Dashboard ›]', '[Middleware ›]'),
       'Server Infra link': ('[Server Infra Dashboard ›]', '[Server Infra ›]')}
tiles = {p['embeddableConfig']['title']: p for p in panels if p['gridData'].get('sectionId') == S2}
for t, (a, b) in REN.items():
    c = tiles[t]['embeddableConfig']['content']
    assert c.count(a) == 1, (t, c)
    tiles[t]['embeddableConfig']['content'] = c.replace(a, b)
assert '](' not in tiles['Executive link']['embeddableConfig']['content']
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
lines[0] = json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n'
open(OUT, 'w').write(''.join(l if l.endswith('\n') else l + '\n' for l in lines))
print(f'{OUT}: link names shortened')
