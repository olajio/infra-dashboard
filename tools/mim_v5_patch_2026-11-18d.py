"""MIM V5 patch 18d (18 Nov 2026): Time to Resolve back to the rolling 7-day median (team decision), undoing 18b.

Usage: mim_v5_patch_2026-11-18d.py "MIM V5.ndjson" "<MIM V5 at 18a>.ndjson" "MIM V5.ndjson"
(the second file: MIM V5 as committed with patch 18a, before 18b; git show 6ba8f6b:"MIM V5.ndjson")

The Time to Resolve panel is copied unchanged from the 18a version: each point = the median of the P1 / P2 / P3
incidents resolved in the 7 days up to that day (a resolved incident counts on 7 consecutive days), points joined,
day labels, P3 line, Priorities control. Everything else (18c Future Releases, etc.) is kept.
"""
import json
import sys

SRC, OLD, OUT = sys.argv[1:4]
TTR = 'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)'
dash = json.loads([l for l in open(SRC) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
old = {p['embeddableConfig'].get('title'): p for p in
       json.loads(json.loads([l for l in open(OLD) if l.strip()][0])['attributes']['panelsJSON'])}[TTR]
assert 'MV_EXPAND k' in old['embeddableConfig']['attributes']['state']['query']['esql'], 'second file is not the 18a version'
i = next(n for n, p in enumerate(panels) if p['embeddableConfig'].get('title') == TTR)
assert 'MV_EXPAND k' not in panels[i]['embeddableConfig']['attributes']['state']['query']['esql'], 'already reverted'
assert panels[i]['panelIndex'] == old['panelIndex']
old['gridData'] = panels[i]['gridData']
panels[i] = old
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: Time to Resolve = rolling 7-day median again (as in 18a)')
