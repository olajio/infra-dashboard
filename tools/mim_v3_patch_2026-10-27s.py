"""MIM V3: SLA breach read from ServiceNow's task_has_breached; On Hold incidents left out (27 Oct 2026).

Usage: mim_v3_patch_2026-10-27s.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-25r.py)

Agreed with the ServiceNow team (sla_breached.txt): every SLA record in servicenow-task-sla carries task_has_breached.
- Active Incidents, SLA column: Breached = task_has_breached is true on any of the incident's (non-cancelled) SLA
  records. No more breach from the incident's age, from stage "breached" or from a passed planned_end_time. An
  incident with no SLA record shows "No SLA record" (grey) instead of the "(age)" estimates.
- Active Incidents, the three tiles and Time to Resolve vs Target leave out incidents that are On Hold, Resolved,
  Closed, Canceled or Cancelled. Each incident is judged by its latest record (highest @timestamp), so an older
  "In Progress" copy cannot keep an incident that has since gone On Hold or been resolved.
- Time to Resolve vs Target therefore plots the age so far of the still-open incidents only.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]

TILES = ('Active P1', 'P2 over 8 h', 'P3 over 24 h')
TABLE = 'Active Incidents (P1 · P2 over 8 h · P3 over 24 h)'
TTR = 'P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)'
EXCLUDED = '"On Hold", "Resolved", "Closed", "Canceled", "Cancelled"'

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = {title(p): p for p in panels}
for t in TILES + (TABLE, TTR):
    assert t in P, t
assert 'sla_stage == "breached"' in P[TABLE]['embeddableConfig']['attributes']['state']['query']['esql'], 'already applied?'


def set_lens_query(p, q):
    st = p['embeddableConfig']['attributes']['state']
    old = st['query']['esql']
    layers = [L for L in st['datasourceStates']['textBased']['layers'].values() if L.get('query', {}).get('esql') == old]
    assert len(layers) == 1
    st['query']['esql'] = layers[0]['query']['esql'] = q


# ---------------- Active Incidents ----------------
TABLE_Q = f'''FROM servicenow-incidents-*, servicenow-task-sla-* METADATA _index
| EVAL src = CASE(_index LIKE "*task-sla*", "sla", "inc")
| EVAL inc = CASE(src == "sla", TO_STRING(task_number), TO_STRING(number))
| WHERE inc LIKE "INC*"
| INLINE STATS last_seen = MAX(CASE(src == "inc", @timestamp)) BY inc
| WHERE src == "sla" OR @timestamp == last_seen
| EVAL is_active = CASE(src == "inc" AND TO_INTEGER(priority) IN (1, 2, 3) AND TO_STRING(state_name) NOT IN ({EXCLUDED}), 1, 0)
| WHERE src == "sla" OR is_active == 1
| EVAL sla_stage = TO_LOWER(TO_STRING(stage))
| EVAL sla_rank = CASE(
      COALESCE(TO_BOOLEAN(task_has_breached), false), 1,
      sla_stage == "in_progress" AND (TO_DOUBLE(percentage) >= 75 OR TO_DATETIME(planned_end_time) <= NOW() + 30 minutes), 2,
      sla_stage == "paused", 3,
      sla_stage == "in_progress", 4,
      5)
| EVAL sla_rank = CASE(src == "sla" AND sla_stage != "cancelled", sla_rank)
| INLINE STATS worst = MIN(sla_rank) BY inc
| WHERE src == "inc"
| STATS opened = MAX(TO_DATETIME(opened_at)), grp = VALUES(TO_STRING(assignment_group.name)), worst = MIN(worst),
        assignees = VALUES(TO_STRING(assigned_to.name)), assignee_emails = VALUES(TO_STRING(assigned_to.email)),
        managers = VALUES(TO_STRING(assignment_group.manager.name)), manager_emails = VALUES(TO_STRING(assignment_group.manager.email)),
        descr = VALUES(TO_STRING(short_description))
  BY number, priority, ci.name, state_name
| EVAL age_minutes = DATE_DIFF("minutes", opened, NOW()), target = CASE(priority == 1, 240, priority == 2, 480, 1440)
| WHERE priority == 1 OR age_minutes > target
| EVAL sla = CASE(worst == 1, "Breached", worst == 2, "Breaching", worst == 3, "Paused", worst == 4, "Within SLA",
                  worst == 5, "Met", "No SLA record")
| EVAL grp1 = MV_FIRST(grp)
| EVAL assignment_group = CASE(grp1 IS NULL OR grp1 == "", "—", grp1), assignee = COALESCE(MV_FIRST(assignees), "—"), assignee_email = COALESCE(MV_FIRST(assignee_emails), "—"),
       group_manager = COALESCE(MV_FIRST(managers), "—"), manager_email = COALESCE(MV_FIRST(manager_emails), "—"),
       short_description = COALESCE(MV_FIRST(descr), "—")
| SORT priority ASC, age_minutes DESC
| KEEP number, priority, ci.name, state_name, sla, assignment_group, assignee, assignee_email, group_manager, manager_email, short_description'''

t = P[TABLE]
set_lens_query(t, TABLE_Q)
t['embeddableConfig']['description'] = (
    'Every active P1 incident, and the active P2 and P3 incidents open longer than their target (P2 8 h, P3 24 h, the '
    'lines in Time to Resolve vs Target; age = time since opened), P1 first, oldest first. The three tiles above count '
    'these rows. Active = priority 1, 2 or 3 and the incident\'s latest record not On Hold, Resolved, Closed, Canceled '
    'or Cancelled. SLA = the worst of the incident\'s ServiceNow SLA records (servicenow-task-sla): Breached = '
    'task_has_breached is true on any of them; Breaching = 75 % used or due within 30 min; Paused; Within SLA; Met; '
    'No SLA record = none synced in the last 7 days (see MIM-V3-SLA-CALCULATION.md). Assignee and Group Manager (with '
    'their emails) come from the incident\'s assigned_to and assignment group. To investigate, pick the incident in '
    'the Incident control (or its Affected CI in the CI control). Click an Incident or an Affected CI to open it in '
    'ServiceNow. Last 7 days (fixed); not narrowed by the Incident or CI controls. Short description = the '
    'incident\'s short description from ServiceNow.')

cols = t['embeddableConfig']['attributes']['state']['visualization']['columns']
sla_col = next(c for c in cols if c['columnId'] == 'sla')
assigns = sla_col['colorMapping']['assignments']
pattern = lambda a: a['rules'][0].get('pattern')
age = [a for a in assigns if (pattern(a) or '').endswith('(age)')]
assert len(age) == 3
grey = next(a for a in assigns if pattern(a) == 'Paused')['color']
sla_col['colorMapping']['assignments'] = [a for a in assigns if a not in age] + [{
    'rules': [{'type': 'match', 'pattern': 'No SLA record', 'matchEntireWord': True, 'matchCase': True}],
    'color': dict(grey), 'touched': True}]

# ---------------- tiles ----------------
OLD_TILE_ACTIVE = ('| WHERE TO_STRING(number) LIKE "INC*" AND TO_INTEGER(priority) IN (1, 2, 3)'
                   ' AND TO_STRING(state_name) NOT IN ("Resolved", "Closed", "Canceled", "Cancelled")\n')
NEW_TILE_ACTIVE = ('| WHERE TO_STRING(number) LIKE "INC*"\n'
                   '| INLINE STATS last_seen = MAX(@timestamp) BY number\n'
                   '| WHERE @timestamp == last_seen AND TO_INTEGER(priority) IN (1, 2, 3)'
                   f' AND TO_STRING(state_name) NOT IN ({EXCLUDED})\n')
OLD_TILE_DESC = 'Active = priority 1, 2 or 3 and state not Resolved, Closed, Canceled or Cancelled.'
NEW_TILE_DESC = ('Active = priority 1, 2 or 3 and the incident\'s latest record not On Hold, Resolved, Closed, '
                 'Canceled or Cancelled.')
for name in TILES:
    ec = P[name]['embeddableConfig']
    spec = json.loads(ec['savedVis']['params']['spec'])
    q = spec['data'][0]['url']['query']
    assert q.count(OLD_TILE_ACTIVE) == 1, name
    spec['data'][0]['url']['query'] = q.replace(OLD_TILE_ACTIVE, NEW_TILE_ACTIVE)
    ec['savedVis']['params']['spec'] = json.dumps(spec, indent=2, ensure_ascii=False)
    assert ec['description'].count(OLD_TILE_DESC) == 1, name
    ec['description'] = ec['description'].replace(OLD_TILE_DESC, NEW_TILE_DESC)

# ---------------- Time to Resolve vs Target: still-open incidents only ----------------
TTR_Q = f'''FROM servicenow-incidents-*
| WHERE priority IN (1, 2, 3) AND opened_at >= NOW() - 7 days AND number IS NOT NULL
| INLINE STATS last_seen = MAX(@timestamp) BY number
| WHERE @timestamp == last_seen AND TO_STRING(state_name) NOT IN ({EXCLUDED})
| STATS opened = MIN(opened_at), pri_n = MIN(TO_INTEGER(priority)) BY number
| EVAL hours = DATE_DIFF("minutes", opened, NOW()) / 60.0
| EVAL h1 = CASE(pri_n == 1, hours), h2 = CASE(pri_n == 2, hours), h3 = CASE(pri_n == 3, hours)
| STATS p1_hours = ROUND(AVG(h1), 1), p2_hours = ROUND(AVG(h2), 1), p3_hours = ROUND(AVG(h3), 1),
        incidents = COUNT(*), open_now = COUNT(*)
  BY day = DATE_TRUNC(1 day, opened)
| SORT day ASC
| KEEP day, p1_hours, p2_hours, p3_hours, incidents, open_now'''

g = P[TTR]
set_lens_query(g, TTR_Q)
g['embeddableConfig']['description'] = (
    'Average age so far of the active P1, P2 and P3 incidents opened each day, last 7 days, against the targets: '
    'P1 4 h (red dashed line) and P2 8 h (amber) on the left axis; P3 24 h (blue) on the right axis, which has its own '
    'scale so P3 values of a day or more do not flatten P1 and P2. Both axes start at 0 h. Active = priority 1, 2 or 3 '
    'and the incident\'s latest record not On Hold, Resolved, Closed, Canceled or Cancelled: an incident leaves the '
    'chart once it is resolved or put On Hold, and its day\'s point climbs while it stays open. A point above its line '
    '= that day\'s still-open incidents are already older than target on average. Last 7 days (fixed); not narrowed '
    'by the Incident or CI controls.')

s = json.dumps(panels, ensure_ascii=False)
assert '(age)' not in json.dumps([P[TABLE]], ensure_ascii=False)
A['panelsJSON'] = s
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print('SLA from task_has_breached; On Hold / Resolved / Closed / Canceled out of the table, tiles and trend graph')
