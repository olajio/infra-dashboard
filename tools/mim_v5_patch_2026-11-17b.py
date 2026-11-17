"""MIM V5 patch 17b (17 Nov 2026), on top of 17a: P1 / P2 Time to Resolve vs Target as a rolling 7-day median.

Usage: mim_v5_patch_2026-11-17b.py "MIM V5.ndjson" "MIM V5.ndjson"

Before (13c): each point = the median of the incidents resolved that one day, so a single slow day made the line jump
(team review, mttr_trend.png). Now each point = the median time to resolve of the incidents resolved in the 7 days up
to and including that day, for the last 7 days. Each incident counts in the 7 daily windows that contain its
resolution day. The panel reads 14 days of incidents (7 shown + 6 before the first one).
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
TTR = 'P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)'
day_k = ', '.join(f'k == {k}, d0 + {k} days' for k in range(1, 7))
Q = f"""FROM servicenow-incidents-*
| WHERE TO_STRING(number) LIKE "INC*" AND resolved_at >= NOW() - 14 days AND TO_INTEGER(priority) IN (1, 2)
| STATS resolved = MAX(TO_DATETIME(resolved_at)), opened = MIN(TO_DATETIME(opened_at)), pri_n = MIN(TO_INTEGER(priority)) BY number
| WHERE opened IS NOT NULL AND resolved >= opened
| EVAL hours = DATE_DIFF("minutes", opened, resolved) / 60.0, d0 = DATE_TRUNC(1 day, resolved), k = [0, 1, 2, 3, 4, 5, 6]
| MV_EXPAND k
| EVAL day = CASE(k == 0, d0, {day_k})
| WHERE day >= DATE_TRUNC(1 day, NOW()) - 6 days AND day <= NOW()
| EVAL h1 = CASE(pri_n == 1, hours), h2 = CASE(pri_n == 2, hours)
| STATS p1_hours = ROUND(MEDIAN(h1), 1), p2_hours = ROUND(MEDIAN(h2), 1),
        incidents = COUNT_DISTINCT(number), open_now = COUNT_DISTINCT(number)
  BY day
| SORT day ASC
| KEEP day, p1_hours, p2_hours, incidents, open_now"""

dash = json.loads([l for l in open(SRC) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
p = next(p for p in panels if p['embeddableConfig'].get('title') == TTR)
ec = p['embeddableConfig']
st = ec['attributes']['state']
old = st['query']['esql']
assert 'MV_EXPAND k' not in old and 'MEDIAN(h1)' in old, 'patch 17a first, or already rolling'
for layer in st['datasourceStates']['textBased']['layers'].values():
    if layer['query']['esql'] == old:
        layer['query'] = {'esql': Q}
        for c in layer['columns']:
            if c['columnId'] == 'incidents':
                c['label'] = 'Resolved in the 7 days'
            if c['columnId'] == 'open_now':
                c['label'] = 'Resolved in the 7 days (P1–P2)'
st['query'] = {'esql': Q}
st['visualization']['yTitle'] = 'Hours to resolve (rolling 7-day median)'
ec['time_range'] = {'from': 'now-14d', 'to': 'now'}
ec['description'] = ('Time to resolve, rolling 7-day median (since 17 Nov): each point is the median hours from opened to '
                     'resolved of the P1 or P2 incidents resolved in the 7 days up to and including that day, for each of '
                     'the last 7 days, against the targets P1 4 h (red dashed line) and P2 8 h (amber). A rising line = '
                     'resolving more slowly. The rolling window smooths out single slow days; a P1 point stays on the '
                     'chart for 7 days after the P1 is resolved. No P1 resolved in a window = no P1 point. Reads 14 days '
                     'of incidents (badge): the 7 days shown and the 6 before the first. Not narrowed by the Incident or '
                     'CI controls.')
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: {TTR} is a rolling 7-day median')
