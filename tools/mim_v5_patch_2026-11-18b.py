"""MIM V5 patch 18b (18 Nov 2026), on top of 18a: Time to Resolve counts each incident once, on its resolution day.

Usage: mim_v5_patch_2026-11-18b.py "MIM V5.ndjson" "MIM V5.ndjson"

Problem (dash.png, trendline2.png): no P1 open, yet a solid P1 line at 26.8 h across the chart. The chart shows
RESOLVED incidents, and with the rolling 7-day median (17b) each resolved incident was counted on 7 consecutive days.
The only P1 resolved in the period (INC2692216, resolved 13 Nov, MTTR 26.8 h) therefore drew a flat line from 13 to
19 Nov, which looks like a trend but is one incident repeated. The line style also joined points across days with
nothing resolved ("Linear" fitting), so gaps looked like data.

Now: each point = the median hours of the incidents of that priority resolved THAT day (P1 MTTR from becoming a P1;
P2 / P3 Duration from opened), one point per day for the last 7 days. A priority with nothing resolved on a day has
no point that day, and points are not joined across such gaps. INC2692216 is one P1 dot on 13 Nov (until 13 Nov
leaves the 7 days).
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
TTR = 'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)'
dash = json.loads([l for l in open(SRC) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
p = next(p for p in panels if p['embeddableConfig'].get('title') == TTR)
ec = p['embeddableConfig']
st = ec['attributes']['state']
old = st['query']['esql']
day_k = ', '.join(f'k == {k}, d0 + {k} days' for k in range(1, 7))
pairs = [
    ('NOW() - 14 days AND pri IN (1, 2, 3)', 'NOW() - 7 days AND pri IN (1, 2, 3)'),
    ('DATE_DIFF("minutes", opened, resolved) / 60.0),\n       d0 = DATE_TRUNC(1 day, resolved), k = [0, 1, 2, 3, 4, 5, 6]\n'
     '| MV_EXPAND k\n'
     f'| EVAL day = CASE(k == 0, d0, {day_k})\n',
     'DATE_DIFF("minutes", opened, resolved) / 60.0),\n       day = DATE_TRUNC(1 day, resolved)\n'),
]
q = old
for a, b in pairs:
    assert q.count(a) == 1, ('patch 18a first, or already patched', a[:60])
    q = q.replace(a, b)
for layer in st['datasourceStates']['textBased']['layers'].values():
    if layer['query']['esql'] == old:
        layer['query'] = {'esql': q}
        for c in layer['columns']:
            if c['columnId'] == 'incidents':
                c['label'] = 'Resolved that day'
            if c['columnId'] == 'open_now':
                c['label'] = 'Resolved that day (P1–P3)'
st['query'] = {'esql': q}
vis = st['visualization']
vis['fittingFunction'] = 'None'
vis['yTitle'] = 'Hours to resolve (median per day)'
ec['description'] = (
    'Time to resolve of the incidents RESOLVED each day (not the open ones): each point is the median hours of the P1, '
    'P2 or P3 incidents resolved that day, for each of the last 7 days, against the targets P1 4 h (red dashed line), '
    'P2 8 h (amber) and P3 24 h (blue). P1 = MTTR, from when the incident became a P1 (ServiceNow incident timeline; '
    'the opened time if opened as a P1) to resolved; P2 and P3 = Duration, from opened to resolved. Each incident '
    'counts once, on the day it was resolved; a priority with nothing resolved that day has no point, and points are '
    'not joined across such days. Only the priorities picked in the Priorities control. Reads 30 days (badge) so the '
    'time a P1 became a P1 is in range. Not narrowed by the Incident or CI controls.')
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: Time to Resolve = median per resolution day, each incident once, no joined gaps')
