"""MIM V5 patch 19d (19 Nov 2026): three fixes asked for by the team.

Usage: mim_v5_patch_2026-11-19d.py "MIM V5.ndjson" "MIM V5.ndjson"

1. Drill-downs to ServiceNow on the Incident and Affected CI columns of Active Incidents did not work outside edit
   mode. Since patch 17c the query renamed its own working columns back to `number` and `ci.name`, so Kibana treated
   them as "created at query time" and disabled filters and drill-downs on them. The table now groups by the original
   `number` and `ci.name` fields again. (Other tables: see the test; only those whose drill-down column is built in the
   query are changed here.)
2. The "Time as P1 / Duration (h)" column is removed from Active Incidents (the sort order is unchanged).
3. Active incident = state New, In Progress or On Hold, for every priority (On Hold P2s and P3s were left out): the
   Needs attention now and Active P1 / P2 / P3 tiles, Active Incidents, Escalation Channel and the Incident control.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
ACTIVE = '("New", "In Progress", "On Hold")'
dash = json.loads([l for l in open(SRC) if l.strip()][0])
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = {title(p): p for p in panels}


def sub(text, pairs, what):
    for a, b in pairs:
        assert text.count(a) == 1, (what, text.count(a), a)
        text = text.replace(a, b)
    return text


def set_query(p, q):
    st = p['embeddableConfig']['attributes']['state']
    old = st['query']['esql']
    for layer in st['datasourceStates']['textBased']['layers'].values():
        if layer['query']['esql'] == old:
            layer['query'] = {'esql': q}
    st['query'] = {'esql': q}


DESC_OLD = 'On Hold P1s count; On Hold P2s and P3s do not.'
DESC_NEW = 'Active = state New, In Progress or On Hold.'
LONG_OLD = ("Active = priority 1 or 2 and the incident's latest record not Resolved, Closed, Canceled or Cancelled; " + DESC_OLD)


def fix_desc(d):
    d = d.replace(LONG_OLD, "Active = the incident's latest record is New, In Progress or On Hold.")
    return d.replace(DESC_OLD, DESC_NEW)


# ---- tiles ----
TILE_OLD = ('TO_STRING(state_name) NOT IN ("Resolved", "Closed", "Canceled", "Cancelled") '
            'AND (TO_INTEGER(priority) == 1 OR TO_STRING(state_name) != "On Hold")')
for t in ('Needs attention now', 'Active P1', 'Active P2', 'Active P3'):
    ec = P[t]['embeddableConfig']
    spec = json.loads(ec['savedVis']['params']['spec'])
    spec['data'][0]['url']['query'] = sub(spec['data'][0]['url']['query'], [(TILE_OLD, f'TO_STRING(state_name) IN {ACTIVE}')], t)
    ec['savedVis']['params']['spec'] = json.dumps(spec, ensure_ascii=False, indent=2)
    ec['description'] = fix_desc(ec.get('description') or '')

# ---- Active Incidents ----
AI = 'Active Incidents (P1 · P2 · P3)'
p = P[AI]
q = sub(p['embeddableConfig']['attributes']['state']['query']['esql'], [
    ('st NOT IN ("Resolved", "Closed", "Canceled", "Cancelled")\n                        AND (pri == 1 OR st != "On Hold"), 1, 0)',
     f'st IN {ACTIVE}, 1, 0)'),
    ('  BY num, pri, ci_s, st\n', '  BY number, pri, ci.name, st\n'),
    ('| RENAME num AS number, pri AS priority, ci_s AS ci.name, st AS state_name\n', '| RENAME pri AS priority, st AS state_name\n'),
    ('KEEP number, priority, ci.name, state_name, opened, age, hours_open, linked_incidents,',
     'KEEP number, priority, ci.name, state_name, opened, age, linked_incidents,')], AI)
set_query(p, q)
st = p['embeddableConfig']['attributes']['state']
(layer,) = [l for l in st['datasourceStates']['textBased']['layers'].values() if l['query']['esql'] == q]
layer['columns'] = [c for c in layer['columns'] if c['columnId'] != 'hours_open']
st['visualization']['columns'] = [c for c in st['visualization']['columns'] if c['columnId'] != 'hours_open']
ec = p['embeddableConfig']
ec['description'] = sub(fix_desc(ec['description']), [
    (' Time as P1 / Duration (h): for a P1, hours since it became a P1 (MTTR so far; the time it became a P1 comes from the '
     'ServiceNow incident timeline, or the opened time if it was opened as a P1); for a P2 or P3, hours since it was '
     'opened (Duration).', '')], AI)

# ---- Escalation Channel ----
p = P['Escalation Channel']
set_query(p, sub(p['embeddableConfig']['attributes']['state']['query']['esql'], [
    ('AND TO_STRING(state_name) NOT IN ("Resolved", "Closed", "Canceled", "Cancelled")',
     f'AND TO_STRING(state_name) IN {ACTIVE}')], 'Escalation Channel'))

# ---- Incident control ----
c = next(v['config'] for v in A['pinned_panels']['panels'].values() if v['config']['variable_name'] == 'incident')
c['esql_query'] = sub(c['esql_query'], [('state_name NOT IN ("Resolved", "Closed", "Canceled", "Cancelled")',
                                         f'state_name IN {ACTIVE}')], 'incident control')

A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: drill-down columns from the original fields, Time as P1 / Duration removed, active = New / In Progress / On Hold')
