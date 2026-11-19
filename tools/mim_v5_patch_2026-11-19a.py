"""MIM V5 patch 19a (19 Nov 2026), on top of 18d / 18e: time windows, items 3 and 6 of the 19 Nov recommendations.

Usage: mim_v5_patch_2026-11-19a.py "MIM V5.ndjson" "MIM V5.ndjson"

3. Time to Resolve: 30 days of points (was 7), still the rolling 7-day median. It reads the incidents resolved in the
   last 36 days (30 points + the 6 days before the first) and the panel reads 40 days, so the time a P1 became a P1 is
   in range. With about 43 P2s and 414 P3s resolved a day, 30 points show a trend; 7 were too few.
6. Section 3 health panels (Server, Middleware, Database, Process, APM Services and Synthetics Health, Errors from the
   Logs): panel window 5 years -> 30 days. They still show only the Health window (at most 7 days); the shorter window
   lets Elasticsearch skip years of old metrics and logs, with a margin if the daily CMDB relationship load lapses.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
TTR = 'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)'
HEALTH = ['Server Health', 'Middleware Health', 'Database Health', 'Process Health', 'APM Services Health',
          'Synthetics Health', 'Errors from the Logs']
dash = json.loads([l for l in open(SRC) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
P = {p['embeddableConfig'].get('title'): p for p in panels}

ec = P[TTR]['embeddableConfig']
st = ec['attributes']['state']
old = st['query']['esql']
q = old
for a, b in (('resolved_d >= NOW() - 14 days AND', 'resolved_d >= NOW() - 36 days AND'),
             ('WHERE day >= DATE_TRUNC(1 day, NOW()) - 6 days AND', 'WHERE day >= DATE_TRUNC(1 day, NOW()) - 29 days AND')):
    assert q.count(a) == 1, ('patch 18d first, or already patched', a)
    q = q.replace(a, b)
for layer in st['datasourceStates']['textBased']['layers'].values():
    if layer['query']['esql'] == old:
        layer['query'] = {'esql': q}
st['query'] = {'esql': q}
assert ec['time_range'] == {'from': 'now-30d', 'to': 'now'}
ec['time_range'] = {'from': 'now-40d', 'to': 'now'}
d = ec['description']
for a, b in (('for each of the last 7 days', 'for each of the last 30 days'), ('Reads 30 days', 'Reads 40 days')):
    if a in d:
        d = d.replace(a, b)
ec['description'] = d

for t in HEALTH:
    e = P[t]['embeddableConfig']
    assert e['time_range'] == {'from': 'now-5y', 'to': 'now'}, t
    e['time_range'] = {'from': 'now-30d', 'to': 'now'}
    if e.get('description'):
        e['description'] = e['description'].replace('Last 5 years', 'Last 30 days')

dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: Time to Resolve 30 points (reads 40 days); 7 health panels read 30 days')
