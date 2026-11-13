"""MIM V5 patch 13b (13 Nov 2026), on top of 13a: P1 / P2 / P3 Time to Resolve vs Target shows real time to resolve.

Usage: mim_v5_patch_2026-11-13b.py "MIM V5.ndjson" "MIM V5.ndjson"
Before: the average age so far of the incidents still open, by the day they were opened. That line always fell from
left to right (an incident opened 6 days ago is about 6 days old, one opened today a few hours), and resolved
incidents left the chart, so it never showed a time to resolve.
Now (option A, checked with TTR1 / TTR2 on 13 Nov, ttr.txt): for the P1 / P2 / P3 incidents resolved each day, the
average hours from opened to resolved, against the same 4 h / 8 h / 24 h target lines. A rising line = resolving more
slowly. resolved_at is on 545 of 547 P2 and 3,344 of 3,987 P3 incidents (TTR1).
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
TTR = 'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)'
Q = """FROM servicenow-incidents-*
| WHERE TO_STRING(number) LIKE "INC*" AND resolved_at >= NOW() - 7 days AND TO_INTEGER(priority) IN (1, 2, 3)
| STATS resolved = MAX(TO_DATETIME(resolved_at)), opened = MIN(TO_DATETIME(opened_at)), pri_n = MIN(TO_INTEGER(priority)) BY number
| WHERE opened IS NOT NULL AND resolved >= opened
| EVAL hours = DATE_DIFF("minutes", opened, resolved) / 60.0
| EVAL h1 = CASE(pri_n == 1, hours), h2 = CASE(pri_n == 2, hours), h3 = CASE(pri_n == 3, hours)
| STATS p1_hours = ROUND(AVG(h1), 1), p2_hours = ROUND(AVG(h2), 1), p3_hours = ROUND(AVG(h3), 1),
        incidents = COUNT(*), open_now = COUNT(*)
  BY day = DATE_TRUNC(1 day, resolved)
| SORT day ASC
| KEEP day, p1_hours, p2_hours, p3_hours, incidents, open_now"""

dash = json.loads([l for l in open(SRC) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
p = next(p for p in panels if p['embeddableConfig'].get('title') == TTR)
ec = p['embeddableConfig']
st = ec['attributes']['state']
old = st['query']['esql']
assert 'age_minutes' not in Q and 'resolved_at' not in old, 'already patched?'
data_layer = next(l for l in st['datasourceStates']['textBased']['layers'].values() if l['query']['esql'] == old)
data_layer['query'] = {'esql': Q}
st['query'] = {'esql': Q}
for c in data_layer['columns']:
    if c['columnId'] == 'incidents':
        c['label'] = 'Resolved'
    if c['columnId'] == 'open_now':
        c['label'] = 'Resolved (P1–P3)'
data_layer.pop('allColumns', None)
st['visualization']['yTitle'] = 'Hours to resolve (average)'
ec['description'] = ('Time to resolve: for the P1, P2 and P3 incidents resolved each day (last 7 days), the average hours '
                     'from opened to resolved, against the targets: P1 4 h (red dashed line), P2 8 h (amber) and P3 24 h '
                     '(blue), on one axis in hours. A point above its line = that day\'s resolved incidents took longer '
                     'than target on average; a rising line = resolving more slowly. Each incident counts once, on the '
                     'day it was resolved (resolved_at). A day with no resolved incident of a priority has no point. '
                     'Averages are pulled up by the odd very long incident (TTR2 on 13 Nov: some P3 over 900 h). '
                     'Last 7 days (fixed); not narrowed by the Incident or CI controls. Since 13 Nov; it showed the age '
                     'so far of open incidents before.')
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: {TTR} now shows time to resolve')
