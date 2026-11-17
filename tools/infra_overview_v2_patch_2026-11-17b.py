"""Infrastructure Overview v2, patch 17b (17 Nov 2026), on top of 17a: Dashboard Links in Portfolio v4's font.

Usage: infra_overview_v2_patch_2026-11-17b.py "Infrastructure Overview v2.ndjson" "Infrastructure Overview v2.ndjson"

- Related Dashboards: Executive Dashboard (In Progress) is now a link (links.txt), still reading "Executive Dashboard
  (In Progress)"; Infrastructure Overview added before Major Incident Management. Order: Executive, Portfolio,
  Applications Operations, Infrastructure Overview, Major Incident Management.
- Every link uses Portfolio v4's link font (a level-2 Markdown heading, `## icon [label](url)`; pfv4.ndjson, section
  Related Dashboards), and Portfolio's tile widths 10 / 9 / 10 / 9 / 10. The tiles are 4 rows high (Portfolio: 2) so a
  label that wraps to two lines at this size is not cut off.
- The Data freshness panel (shown only as a "Last 2 days" badge above Future Releases) is removed.
The same section is copied into MIM V5 by mim_v5_patch_2026-11-17e.py.
"""
import json
import sys
import uuid

SRC, OUT = sys.argv[1:3]
lines = [l for l in open(SRC) if l.strip()]
dash = json.loads(lines[0])
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
S2 = next(s['gridData']['i'] for s in A['sections'] if 'Dashboard Links' in s['title'])
OV = lambda name: str(uuid.uuid5(uuid.NAMESPACE_URL, 'infra-overview/v2/' + name))
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')

R = 'https://kibana-prod.gcp.cna.com/app/r/s/'
RELATED = [('Executive', '📈', 'Executive Dashboard (In Progress)', R + 'cPJ71', 10),
           ('Portfolio', '📊', 'Portfolio Dashboard ›',
            'https://kibana-prod.gcp.cna.com/app/dashboards#/view/7511c5d1-3326-4c7e-91f4-6c8fdb686ee0', 9),
           ('Applications Operations', '🛡️', 'Applications Operations Dashboard ›', R + 'I3R7D', 10),
           ('Infrastructure Overview', '🧭', 'Infrastructure Overview ›', R + 'bUy3F', 9),
           ('Major Incident Management', '🚨', 'Major Incident Management ›', R + 'ZSMtk', 10)]
DETAILED = [('Cloud Infra', '☁️', 'Cloud Infra Dashboard ›', R + 'MDJ9f', 10),
            ('Database Infra', '🗄️', 'Database Infra Dashboard ›', R + 'w6zL4', 10),
            ('Middleware', '⚙️', 'Middleware Dashboard ›', R + 'jwCRg', 9),
            ('Server Infra', '🖥️', 'Server Infra Dashboard ›', R + 'qJk5u', 10),
            ('VMware Infra', '🧱', 'VMware Infra Dashboard ›', R + 't4oxr', 9)]

old = {title(p): p for p in panels if p['gridData'].get('sectionId') == S2}
assert 'Data freshness' in old and 'Executive link' in old, 'patch 17a first, or already patched'
assert '](' not in old['Executive link']['embeddableConfig']['content'], 'already patched'
# the URLs of the existing tiles are kept as they are (only Executive and Infrastructure Overview are new)
for key, _, _, url, _ in RELATED[1:3] + [RELATED[4]] + DETAILED:
    assert url in old[f'{key} link']['embeddableConfig']['content'], key


def md(name, content, x, y, w, h):
    pid = OV('panel/' + name)
    return {'type': 'markdown', 'panelIndex': pid, 'gridData': {'x': x, 'y': y, 'w': w, 'h': h, 'i': pid, 'sectionId': S2},
            'embeddableConfig': {'title': name, 'hide_title': True, 'content': content,
                                 'settings': {'open_links_in_new_tab': True}}}


old['Detailed Dashboards heading']['gridData']['y'] = 6
new = [old['Related Dashboards heading'], old['Detailed Dashboards heading']]
for row_y, links in ((2, RELATED), (8, DETAILED)):
    x = 0
    for key, icon, label, url, w in links:
        new.append(md(f'{key} link', f'## {icon} [{label}]({url})', x, row_y, w, 4))
        x += w
    assert x == 48
panels = [p for p in panels if p['gridData'].get('sectionId') != S2] + new
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
lines[0] = json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n'
open(OUT, 'w').write(''.join(l if l.endswith('\n') else l + '\n' for l in lines))
print(f'{OUT}: Dashboard Links in Portfolio font, Executive linked, Infrastructure Overview added, Data freshness removed')
