"""Dashboard Links patch 18e (18 Nov 2026): VMware Infra Dashboard -> VMware Infra (Infrastructure Overview v2), and
Executive Dashboard (In Progress) -> Executive (In Progress) on MIM V5 too, so its Related Dashboards match again.

Usage: dashboard_links_patch_2026-11-18e.py "Infrastructure Overview v2.ndjson" "MIM V5.ndjson"   (edits both in place)
"""
import json
import sys

EDITS = {sys.argv[1]: {'VMware Infra link': ('[VMware Infra Dashboard ›]', '[VMware Infra ›]')},
         sys.argv[2]: {'Executive link': ('## 📈 Executive Dashboard (In Progress)', '## 📈 Executive (In Progress)')}}
for path, edits in EDITS.items():
    lines = [l for l in open(path) if l.strip()]
    dash = json.loads(lines[0])
    panels = json.loads(dash['attributes']['panelsJSON'])
    for p in panels:
        t = p['embeddableConfig'].get('title')
        if t in edits:
            a, b = edits.pop(t)
            c = p['embeddableConfig']['content']
            assert c.count(a) == 1, (path, t, c)
            p['embeddableConfig']['content'] = c.replace(a, b)
    assert not edits, (path, edits)
    dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
    lines[0] = json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n'
    open(path, 'w').write(''.join(l if l.endswith('\n') else l + '\n' for l in lines))
    print(f'{path}: done')
