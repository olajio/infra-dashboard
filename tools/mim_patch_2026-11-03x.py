"""Patch 03x (3 Nov 2026): remove the "New collapsible section" (a colleague's addition, carried into MIM V4 on 2 Nov).

Usage: mim_patch_2026-11-03x.py "MIM V4.ndjson" "MIM V4.ndjson"     (after 03w)

Removes the section, its 4 panels (the CI and Assignment Group option lists, Total Incident Count by CI, P1/P2
Incidents by Assignment Group), the dashboard references of its option lists, and the servicenow-incidents-* data
view line that only those option lists used. The default time range (last 7 days) stays: the control lists in the top
bar read it.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
TITLE = 'New collapsible section'

lines = [json.loads(l) for l in open(SRC) if l.strip()]
dash = next(o for o in lines if o.get('type') == 'dashboard')
A = dash['attributes']
gone = [s for s in A['sections'] if s['title'] == TITLE]
assert len(gone) == 1, 'already applied?'
sid = gone[0]['gridData']['i']
A['sections'] = [s for s in A['sections'] if s['title'] != TITLE]

panels = json.loads(A['panelsJSON'])
removed = {p['panelIndex'] for p in panels if p['gridData'].get('sectionId') == sid}
assert len(removed) == 4, removed
A['panelsJSON'] = json.dumps([p for p in panels if p['panelIndex'] not in removed], ensure_ascii=False)

refs = dash.get('references', [])
dropped_refs = [r for r in refs if r['name'].split(':')[0] in removed]
dash['references'] = [r for r in refs if r not in dropped_refs]
still_used = {r['id'] for r in dash['references']}
dropped_views = {r['id'] for r in dropped_refs} - still_used
lines = [o for o in lines if not (o.get('type') == 'index-pattern' and o.get('id') in dropped_views)]

assert 'optionsListDataView' not in json.dumps(dash)
with open(OUT, 'w') as f:
    for o in lines:
        f.write(json.dumps(o, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: removed "{TITLE}" ({len(removed)} panels, {len(dropped_refs)} references, '
      f'{len(dropped_views)} data view); sections now: ' + ' | '.join(s['title'] for s in A['sections']))
