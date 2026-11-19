"""MIM V5 patch 19b (19 Nov 2026), on top of 19a: P1 MTTR (90 days) tile, item 4 of the 19 Nov recommendations.

Usage: mim_v5_patch_2026-11-19b.py "MIM V5.ndjson" "MIM V5.ndjson"

There is about one P1 a month, so the P1 line on Time to Resolve is mostly empty or repeats one incident. This tile
gives the fair P1 KPI: the median MTTR of the P1s resolved in the last 90 days (from when each became a P1, from the
ServiceNow incident timeline; the opened time if opened as a P1), with the count, the average and how many were within
the 4 h target. Red above 4 h, green at or under, grey "–" with no P1 resolved. Same look as the other tiles (preview:
previews/mim-v5-p1-mttr-tile-preview.png). It goes 5th in the tile row; both "In progress" placeholders are kept, so
the row is 7 5 5 5 8 8 5 5.
"""
import json
import sys
import uuid

SRC, OUT = sys.argv[1:3]
dash = json.loads([l for l in open(SRC) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = {title(p): p for p in panels}
assert 'P1 MTTR (90 days)' not in P, 'already patched'
Q = """FROM servicenow-incidents-*, servicenow-incident-timelines-* METADATA _index
| EVAL src = CASE(_index LIKE "*incident-timelines*", "tl", "inc"), num = TO_STRING(number), p = TO_INTEGER(priority),
       upd = TO_DATETIME(updated_at), opened_d = TO_DATETIME(opened_at), resolved_d = TO_DATETIME(resolved_at)
| WHERE num LIKE "INC*"
| EVAL is_res = CASE(src == "inc" AND resolved_d >= NOW() - 90 days AND p == 1, 1, 0)
| INLINE STATS in_set = MAX(is_res) BY num
| WHERE in_set == 1 AND (is_res == 1 OR (src == "tl" AND @timestamp == upd))
| EVAL h_p1 = CASE(src == "tl" AND p == 1, @timestamp), h_non = CASE(src == "tl" AND p != 1, @timestamp)
| STATS opened = MIN(CASE(is_res == 1, opened_d)), resolved = MAX(CASE(is_res == 1, resolved_d)),
        first_p1 = MIN(h_p1), first_non_p1 = MIN(h_non) BY num
| WHERE opened IS NOT NULL AND resolved >= opened
| EVAL became_p1 = CASE(first_p1 IS NOT NULL AND first_non_p1 IS NOT NULL AND first_non_p1 < first_p1 AND first_p1 >= opened, first_p1, opened)
| EVAL became_p1 = CASE(became_p1 <= resolved, became_p1, opened)
| EVAL mttr = DATE_DIFF("minutes", became_p1, resolved) / 60.0
| STATS p1s = COUNT(*), median_h = ROUND(MEDIAN(mttr), 1), avg_h = ROUND(AVG(mttr), 1), met = SUM(CASE(mttr <= 4, 1, 0))"""
RED, GREEN, GREY = '#d6453d', '#1f9e6b', '#8a96a8'
T = lambda x, y, size, weight, align, text, **kw: {'type': 'text', 'encode': {'update': dict(
    {'x': x, 'y': y, 'fontSize': {'value': size}, 'fontWeight': {'value': weight}, 'align': {'value': align},
     'baseline': {'value': 'alphabetic'}, 'text': text}, **kw)}}
spec = {'$schema': 'https://vega.github.io/schema/vega/v5.json', 'autosize': {'type': 'fit', 'contains': 'padding'}, 'padding': 0,
        'data': [{'name': 'raw', 'url': {'%type%': 'esql', 'query': Q}}],
        'signals': [{'name': 'n', 'update': "length(data('raw')) ? (data('raw')[0].p1s || 0) : 0"},
                    {'name': 'med', 'update': "length(data('raw')) ? data('raw')[0].median_h : null"},
                    {'name': 'avg', 'update': "length(data('raw')) ? data('raw')[0].avg_h : null"},
                    {'name': 'met', 'update': "length(data('raw')) ? (data('raw')[0].met || 0) : 0"},
                    {'name': 'col', 'update': f"n == 0 ? '{GREY}' : med > 4 ? '{RED}' : '{GREEN}'"}],
        'marks': [
            {'type': 'symbol', 'encode': {'update': {'x': {'value': 30}, 'y': {'value': 32}, 'shape': {'value': 'circle'},
             'size': {'value': 1134.1176}, 'fill': {'value': RED}, 'fillOpacity': {'value': 0.18}, 'stroke': {'value': RED},
             'strokeWidth': {'value': 1.5}}}},
            T({'value': 30}, {'value': 38}, 17, 'bold', 'center', {'value': '⏱'}, fill={'value': RED}),
            dict(T({'value': 58}, {'value': 26}, 14, 'bold', 'left', {'value': 'P1 MTTR'}, limit={'signal': 'width - 70'}), style='guide-label'),
            dict(T({'value': 58}, {'value': 43}, 11, 'normal', 'left', {'value': 'median · last 90 days'}, opacity={'value': 0.7},
                   limit={'signal': 'width - 70'}), style='guide-label'),
            dict(T({'value': 12}, {'signal': 'height - 28'}, 11, 'normal', 'left',
                   {'signal': "n == 0 ? 'No P1 resolved' : n + (n == 1 ? ' P1' : ' P1s') + ' · avg ' + format(avg, '.1f') + ' h'"},
                   opacity={'value': 0.75}), style='guide-label'),
            T({'value': 12}, {'signal': 'height - 10'}, 12, 'bold', 'left',
              {'signal': "n == 0 ? 'Target 4 h' : met + ' of ' + n + ' within 4 h'"}, fill={'signal': 'col'}),
            T({'signal': 'width - 12'}, {'signal': 'height - 6'}, 38, 'bold', 'right',
              {'signal': "n == 0 ? '–' : format(med, '.1f') + ' h'"}, fill={'signal': 'col'})]}
tile = json.loads(json.dumps(P['Active P1']))
pid = str(uuid.uuid5(uuid.NAMESPACE_URL, 'mim-v5/p1-mttr-tile'))
tile['panelIndex'] = pid
tile['gridData'] = dict(tile['gridData'], i=pid)
ec = tile['embeddableConfig']
ec['title'] = ec['savedVis']['title'] = 'P1 MTTR (90 days)'
ec['time_range'] = {'from': 'now-100d', 'to': 'now'}
ec['savedVis']['params']['spec'] = json.dumps(spec, ensure_ascii=False, indent=2)
ec['description'] = ('Median P1 MTTR of the P1s resolved in the last 90 days: hours from when each became a P1 (ServiceNow '
                     'incident timeline; the opened time if opened as a P1) to resolved, with the count, the average and how many '
                     'were within the 4 h target. Red above 4 h, green at or under. Reads 100 days (badge). Not narrowed by the '
                     'controls.')
panels.append(tile)
P['P1 MTTR (90 days)'] = tile
y = P['Active P1']['gridData']['y']
for t, x, w in (('Needs attention now', 0, 7), ('Active P1', 7, 5), ('Active P2', 12, 5), ('Active P3', 17, 5),
                ('P1 MTTR (90 days)', 22, 8), ('Open alerts, no incident', 30, 8), ('User base · ServiceNow', 38, 5), ('Real users · RUM', 43, 5)):
    assert P[t]['gridData']['y'] == y, t
    P[t]['gridData'].update(x=x, w=w)
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: P1 MTTR (90 days) tile added')
