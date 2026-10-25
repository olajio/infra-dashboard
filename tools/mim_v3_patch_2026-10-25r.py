"""MIM V3: Active P1 / P2 / P3 donut split into three tiles; overdue-only Active Incidents; 7-day look-back (25 Oct 2026).

Usage: mim_v3_patch_2026-10-25r.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-20q.py)

- The Active P1 / P2 / P3 donut becomes three count tiles: every active P1; active P2s open longer than 8 h; active
  P3s open longer than 24 h (the P2 / P3 targets of Time to Resolve vs Target). Age = now - opened_at.
- Active Incidents lists the same incidents: all active P1s, and only the P2s / P3s past those targets. Each tile
  counts exactly the rows of its priority in the table (same grouping).
- The tiles, Time to Resolve vs Target, Active Incidents and Escalate look back 7 days instead of 1 month.
- Layout: the tiles take the top half of the donut's old space (plus the tiles' old width), User base and Real users
  move below them; Time to Resolve stays where it was. Nothing below the first row moves.
"""
import copy
import json
import sys
import uuid

SRC, OUT = sys.argv[1:3]

DONUT = '51da697e-ae2f-57b0-93a9-2f3ce02b3837'
USERBASE = 'fd93960b-0df5-54fe-be41-c92285a0ff2d'
RUM = '6aa61130-16c9-587e-98ff-b4725868ffca'
TTR = 'ee7c706a-7bd9-5a61-9347-ea8b97286278'
ACTIVE = 'cb971d69-d438-51c9-b38a-57277a4966e6'
ESCALATE = '4e4ea543-c199-5398-b124-bb305174e40f'

P2_TARGET_MIN, P3_TARGET_MIN = 480, 1440
WEEK = {'from': 'now-7d', 'to': 'now'}

OLD_TABLE_TITLE = 'Active Incidents (P1 / P2 / P3)'
NEW_TABLE_TITLE = 'Active Incidents (P1 · P2 over 8 h · P3 over 24 h)'

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
byid = {p['panelIndex']: p for p in panels}
assert DONUT in byid, 'already applied?'
for pid in (USERBASE, RUM, TTR, ACTIVE, ESCALATE):
    assert pid in byid, pid


def replace_once(s, old, new):
    assert s.count(old) >= 1, old
    return s.replace(old, new)


def edit_panel(pid, pairs):
    """Apply string replacements to the panel's JSON (queries are stored twice in Lens ES|QL panels)."""
    s = json.dumps(byid[pid], ensure_ascii=False)
    for old, new in pairs:
        s = replace_once(s, json.dumps(old, ensure_ascii=False)[1:-1], json.dumps(new, ensure_ascii=False)[1:-1])
    byid[pid].clear()
    byid[pid].update(json.loads(s))


# ---- tile query: the same rows as Active Incidents (same active rule and grouping), counted for one priority ----
def tile_query(cond):
    return (
        'FROM servicenow-incidents-*\n'
        '| WHERE @timestamp >= NOW() - 7 days\n'
        '| WHERE TO_STRING(number) LIKE "INC*" AND TO_INTEGER(priority) IN (1, 2, 3)'
        ' AND TO_STRING(state_name) NOT IN ("Resolved", "Closed", "Canceled", "Cancelled")\n'
        '| STATS opened = MAX(TO_DATETIME(opened_at)) BY number, priority, ci.name, state_name\n'
        '| EVAL pri = TO_INTEGER(priority), age_minutes = DATE_DIFF("minutes", opened, NOW())\n'
        f'| WHERE {cond}\n'
        '| STATS incidents = COUNT(*)'
    )


def tile_spec(query, label, colour):
    return json.dumps({
        '$schema': 'https://vega.github.io/schema/vega/v5.json',
        'autosize': {'type': 'fit', 'contains': 'padding'},
        'padding': 0,
        'data': [{'name': 'raw', 'url': {'%type%': 'esql', 'query': query}}],
        'marks': [{
            'type': 'group',
            'from': {'data': 'raw'},
            'encode': {'update': {'x': {'value': 0}, 'y': {'value': 0},
                                  'width': {'signal': 'width'}, 'height': {'signal': 'height'}}},
            'marks': [
                {'type': 'text', 'style': 'guide-label',
                 'encode': {'update': {
                     'x': {'value': 10}, 'y': {'value': 10}, 'baseline': {'value': 'top'},
                     'lineHeight': {'value': 17}, 'text': {'value': label.split('|')},
                     'fontSize': {'value': 13}, 'fontWeight': {'value': 'bold'},
                     'limit': {'signal': 'width - 20'}}}},
                {'type': 'text', 'style': 'guide-title',
                 'encode': {'update': {
                     'x': {'signal': 'width - 10'}, 'y': {'signal': 'height - 2'},
                     'align': {'value': 'right'}, 'baseline': {'value': 'bottom'},
                     'text': {'signal': 'parent.incidents'},
                     'fontSize': {'value': 34}, 'fontWeight': {'value': 'bold'},
                     'fill': {'value': colour},
                     'opacity': {'signal': 'parent.incidents > 0 ? 1 : 0.4'},
                     'tooltip': {'signal': "{'Incidents': parent.incidents}"}}}},
            ],
        }],
    }, indent=2, ensure_ascii=False)


TILE_COMMON = (' Same incidents as the matching rows of Active Incidents. Active = priority 1, 2 or 3 and state not '
               'Resolved, Closed, Canceled or Cancelled. Last 7 days (fixed); not narrowed by the Incident or CI '
               'controls.')
TILES = [
    ('p1', 'Active P1', 'Active P1|any age', 'pri == 1', '#d6453d',
     'How many P1 incidents are active now, whatever their age.'),
    ('p2', 'P2 over 8 h', 'Active P2|open longer than 8 h', f'pri == 2 AND age_minutes > {P2_TARGET_MIN}', '#c98a0b',
     'How many active P2 incidents have been open longer than the P2 target of 8 h (the amber line in Time to '
     'Resolve vs Target). Age = time since the incident was opened.'),
    ('p3', 'P3 over 24 h', 'Active P3|open longer than 24 h', f'pri == 3 AND age_minutes > {P3_TARGET_MIN}', '#3f6fb5',
     'How many active P3 incidents have been open longer than the P3 target of 24 h (the blue line in Time to '
     'Resolve vs Target). Age = time since the incident was opened.'),
]

donut = byid[DONUT]
section = donut['gridData']['sectionId']
assert donut['gridData'] == {'y': 0, 'x': 0, 'w': 14, 'h': 10, 'i': DONUT, 'sectionId': section}
assert byid[USERBASE]['gridData']['x'] == 14 and byid[RUM]['gridData']['x'] == 14
assert byid[TTR]['gridData']['x'] == 24 and byid[TTR]['gridData']['h'] == 10

template = byid[USERBASE]
tiles = []
for i, (key, title, label, cond, colour, desc) in enumerate(TILES):
    pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'mim-v3/section1/tile-{key}'))
    t = copy.deepcopy(template)
    t['panelIndex'] = pid
    t['gridData'] = {'y': 0, 'x': 8 * i, 'w': 8, 'h': 5, 'i': pid, 'sectionId': section}
    ec = t['embeddableConfig']
    ec['title'] = ec['savedVis']['title'] = title
    ec['description'] = desc + TILE_COMMON
    ec['savedVis']['params'] = {'spec': tile_spec(tile_query(cond), label, colour)}
    ec['time_range'] = dict(WEEK)
    tiles.append(t)

byid[USERBASE]['gridData'].update({'y': 5, 'x': 0, 'w': 12, 'h': 5})
byid[RUM]['gridData'].update({'y': 5, 'x': 12, 'w': 12, 'h': 5})

# ---- Active Incidents: all P1, P2 / P3 only past their target; 7 days ----
edit_panel(ACTIVE, [
    ('| EVAL age_minutes = DATE_DIFF("minutes", opened, NOW()), target = CASE(priority == 1, 240, priority == 2, 480, 1440)\n',
     '| EVAL age_minutes = DATE_DIFF("minutes", opened, NOW()), target = CASE(priority == 1, 240, priority == 2, 480, 1440)\n'
     '| WHERE priority == 1 OR age_minutes > target\n'),
    (OLD_TABLE_TITLE, NEW_TABLE_TITLE),
    ('Every active P1, P2 and P3 incident, P1 first, oldest first.',
     'Every active P1 incident, and the active P2 and P3 incidents open longer than their target (P2 8 h, P3 24 h, '
     'the lines in Time to Resolve vs Target; age = time since opened), P1 first, oldest first. The three tiles '
     'above count these rows.'),
    ('Last 1 month (fixed)', 'Last 7 days (fixed)'),
])
byid[ACTIVE]['embeddableConfig']['time_range'] = dict(WEEK)

# ---- Time to Resolve vs Target: 7 days ----
edit_panel(TTR, [
    ('opened_at >= NOW() - 30 days', 'opened_at >= NOW() - 7 days'),
    ('opened each day, last 30 days,', 'opened each day, last 7 days,'),
    ('Last 1 month (fixed)', 'Last 7 days (fixed)'),
])
byid[TTR]['embeddableConfig']['time_range'] = dict(WEEK)

# ---- Escalate: 7 days ----
edit_panel(ESCALATE, [('Last 1 month (fixed)', 'Last 7 days (fixed)')])
byid[ESCALATE]['embeddableConfig']['time_range'] = dict(WEEK)

# ---- assemble: tiles where the donut was ----
out = []
for p in panels:
    if p['panelIndex'] == DONUT:
        out.extend(tiles)
    else:
        out.append(byid[p['panelIndex']])
s = json.dumps(out, ensure_ascii=False)
assert OLD_TABLE_TITLE not in s and DONUT not in s
A['panelsJSON'] = s
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'donut -> 3 tiles; Active Incidents filtered; 4 panels on 7 days; {len(out)} panels')
