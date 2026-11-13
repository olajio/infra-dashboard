"""MIM V5 patch 13c (13 Nov 2026), on top of 13b: Time to Resolve vs Target uses the median, not the average.

Usage: mim_v5_patch_2026-11-13c.py "MIM V5.ndjson" "MIM V5.ndjson"
A few very long incidents (TTR2: some P3 over 900 h) pulled the daily averages up; the median shows the typical
incident, and is what the MIM KPI list asks for (MTTR trend: median per day). Everything else stays as in 13b.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
TTR = 'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)'
dash = json.loads([l for l in open(SRC) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
ec = next(p for p in panels if p['embeddableConfig'].get('title') == TTR)['embeddableConfig']
st = ec['attributes']['state']
q = st['query']['esql']
old = 'p1_hours = ROUND(AVG(h1), 1), p2_hours = ROUND(AVG(h2), 1), p3_hours = ROUND(AVG(h3), 1)'
assert q.count(old) == 1, 'patch 13b first, or already median'
new_q = q.replace(old, 'p1_hours = ROUND(MEDIAN(h1), 1), p2_hours = ROUND(MEDIAN(h2), 1), p3_hours = ROUND(MEDIAN(h3), 1)')
for layer in st['datasourceStates']['textBased']['layers'].values():
    if layer['query']['esql'] == q:
        layer['query'] = {'esql': new_q}
st['query'] = {'esql': new_q}
st['visualization']['yTitle'] = 'Hours to resolve (median)'
d = ec['description']
d = d.replace('the average hours from opened to resolved', 'the median hours from opened to resolved (the typical incident)')
d = d.replace("took longer than target on average", "typically took longer than target")
d = d.replace('Averages are pulled up by the odd very long incident (TTR2 on 13 Nov: some P3 over 900 h). ',
              'The median is not pulled up by the odd very long incident (TTR2 on 13 Nov: some P3 over 900 h). ')
assert 'median hours' in d and 'Averages are pulled' not in d
ec['description'] = d
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: {TTR} uses the median')
