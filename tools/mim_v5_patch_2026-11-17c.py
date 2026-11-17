"""MIM V5 patch 17c (17 Nov 2026), on top of 17b: P1 MTTR from the time the incident became a P1, P2 Duration,
Linked incidents, On Hold P1s shown.

Usage: mim_v5_patch_2026-11-17c.py "MIM V5.ndjson" "MIM V5.ndjson"

Agreed approach (James Patock's proposal in `MIM SLA update.docx`, checks O1-O5):
- P1: MTTR = from the time the incident became a P1 to resolved (open: to now). The became-P1 time comes from
  servicenow-incident-timelines, which keeps a record of every update with the priority at that time. The first
  record at priority 1 is when it became a P1; if there is no earlier lower-priority record, it was opened as a P1 and
  the opened time is used (also the fallback when the timeline has no record yet).
- P2: Duration = opened to resolved (resolution_time, in seconds; the dates when missing), open: opened to now.
- Active Incidents: new columns "Time as P1 / Duration (h)" and "Linked incidents" (incidents whose parent incident
  is this one); On Hold P1s are now shown (On Hold P2s still are not). The tiles follow the same rule.
- Time to Resolve vs Target: the P1 line is MTTR from becoming a P1; the panel reads 30 days so the became-P1 record
  of a P1 resolved in the last 14 days is in range.
The Active Incidents query no longer reads the SLA records (the SLA column was removed on 13 Nov).
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
AI = 'Active Incidents (P1 · P2 over 8 h)'
TTR = 'P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)'
TL = 'servicenow-incident-timelines-*'
OLD_ACTIVE = 'TO_STRING(state_name) NOT IN ("On Hold", "Resolved", "Closed", "Canceled", "Cancelled")'
NEW_ACTIVE = ('TO_STRING(state_name) NOT IN ("Resolved", "Closed", "Canceled", "Cancelled") '
              'AND (TO_INTEGER(priority) == 1 OR TO_STRING(state_name) != "On Hold")')

# became P1: first timeline record at priority 1, unless no lower-priority record came before it (opened as a P1)
BECAME = ('CASE(first_p1 IS NOT NULL AND first_non_p1 IS NOT NULL AND first_non_p1 < first_p1 AND first_p1 >= opened, '
          'first_p1, opened)')

# Every field is converted once, straight after FROM: the incident and timeline indices map some fields to different
# types (for example priority: byte on the timeline), and ES|QL only accepts such fields through a conversion there.
HEAD = f"""FROM servicenow-incidents-*, {TL} METADATA _index
| EVAL src = CASE(_index LIKE "*incident-timelines*", "tl", "inc"), num = TO_STRING(number), pri = TO_INTEGER(priority),
       st = TO_STRING(state_name), upd = TO_DATETIME(updated_at), opened_d = TO_DATETIME(opened_at),
       resolved_d = TO_DATETIME(resolved_at)"""

AI_Q = HEAD + f""", parent = TO_STRING(parent_incident.number), ci_s = TO_STRING(ci.name),
       grp_s = TO_STRING(assignment_group.name), asg_s = TO_STRING(assigned_to.name), asg_e = TO_STRING(assigned_to.email),
       mgr_s = TO_STRING(assignment_group.manager.name), mgr_e = TO_STRING(assignment_group.manager.email),
       descr_s = TO_STRING(short_description)
| WHERE num LIKE "INC*"
| INLINE STATS last_seen = MAX(CASE(src == "inc", @timestamp)) BY num
| WHERE (src == "inc" AND @timestamp == last_seen) OR (src == "tl" AND @timestamp == upd)
| EVAL is_active = CASE(src == "inc" AND pri IN (1, 2) AND st NOT IN ("Resolved", "Closed", "Canceled", "Cancelled")
                        AND (pri == 1 OR st != "On Hold"), 1, 0)
| INLINE STATS active = MAX(is_active) BY num
| EVAL role = CASE(src == "tl" AND active == 1, "tl",
                   src == "inc" AND active == 1 AND parent IS NOT NULL AND parent != "", "self,child",
                   src == "inc" AND active == 1, "self",
                   src == "inc" AND parent IS NOT NULL AND parent != "", "child")
| WHERE role IS NOT NULL
| EVAL role = SPLIT(role, ",")
| MV_EXPAND role
| EVAL key = CASE(role == "child", parent, num),
       h_p1 = CASE(role == "tl" AND pri == 1, @timestamp), h_non = CASE(role == "tl" AND pri != 1, @timestamp),
       child = CASE(role == "child", num)
| INLINE STATS first_p1 = MIN(h_p1), first_non_p1 = MIN(h_non), linked = COUNT_DISTINCT(child) BY key
| WHERE role == "self"
| STATS opened = MAX(opened_d), first_p1 = MIN(first_p1), first_non_p1 = MIN(first_non_p1),
        linked_incidents = MAX(linked), grp = VALUES(grp_s), assignees = VALUES(asg_s), assignee_emails = VALUES(asg_e),
        managers = VALUES(mgr_s), manager_emails = VALUES(mgr_e), descr = VALUES(descr_s)
  BY num, pri, ci_s, st
| EVAL age_minutes = DATE_DIFF("minutes", opened, NOW()), target = CASE(pri == 1, 240, 480)
| WHERE pri == 1 OR age_minutes > target
| EVAL became_p1 = {BECAME}
| EVAL hours_open = ROUND(DATE_DIFF("minutes", CASE(pri == 1, became_p1, opened), NOW()) / 60.0, 1)
| EVAL grp1 = MV_FIRST(grp)
| EVAL assignment_group = CASE(grp1 IS NULL OR grp1 == "", "—", grp1), assignee = COALESCE(MV_FIRST(assignees), "—"), assignee_email = COALESCE(MV_FIRST(assignee_emails), "—"),
       group_manager = COALESCE(MV_FIRST(managers), "—"), manager_email = COALESCE(MV_FIRST(manager_emails), "—"),
       short_description = COALESCE(MV_FIRST(descr), "—")
| SORT pri ASC, hours_open DESC
| RENAME num AS number, pri AS priority, ci_s AS ci.name, st AS state_name
| KEEP number, priority, ci.name, state_name, opened, hours_open, linked_incidents, assignment_group, assignee, assignee_email, group_manager, manager_email, short_description"""

day_k = ', '.join(f'k == {k}, d0 + {k} days' for k in range(1, 7))
TTR_Q = HEAD + f""", rt0 = TO_INTEGER(resolution_time)
| WHERE num LIKE "INC*"
| EVAL is_res = CASE(src == "inc" AND resolved_d >= NOW() - 14 days AND pri IN (1, 2), 1, 0)
| INLINE STATS in_set = MAX(is_res) BY num
| WHERE in_set == 1 AND (is_res == 1 OR (src == "tl" AND @timestamp == upd))
| EVAL h_p1 = CASE(src == "tl" AND pri == 1, @timestamp), h_non = CASE(src == "tl" AND pri != 1, @timestamp)
| STATS resolved = MAX(CASE(is_res == 1, resolved_d)), opened = MIN(CASE(is_res == 1, opened_d)),
        pri_n = MIN(CASE(is_res == 1, pri)), rt = MAX(CASE(is_res == 1, rt0)),
        first_p1 = MIN(h_p1), first_non_p1 = MIN(h_non)
  BY num
| WHERE opened IS NOT NULL AND resolved >= opened
| EVAL became_p1 = {BECAME}
| EVAL became_p1 = CASE(became_p1 <= resolved, became_p1, opened)
| EVAL hours = CASE(pri_n == 1, DATE_DIFF("minutes", became_p1, resolved) / 60.0,
                    rt IS NOT NULL AND rt >= 0, rt / 3600.0,
                    DATE_DIFF("minutes", opened, resolved) / 60.0),
       d0 = DATE_TRUNC(1 day, resolved), k = [0, 1, 2, 3, 4, 5, 6]
| MV_EXPAND k
| EVAL day = CASE(k == 0, d0, {day_k})
| WHERE day >= DATE_TRUNC(1 day, NOW()) - 6 days AND day <= NOW()
| EVAL h1 = CASE(pri_n == 1, hours), h2 = CASE(pri_n == 2, hours)
| STATS p1_hours = ROUND(MEDIAN(h1), 1), p2_hours = ROUND(MEDIAN(h2), 1),
        incidents = COUNT_DISTINCT(num), open_now = COUNT_DISTINCT(num)
  BY day
| SORT day ASC
| KEEP day, p1_hours, p2_hours, incidents, open_now"""

ACTIVE_DESC = ('Active = priority 1 or 2 and the incident\'s latest record not Resolved, Closed, Canceled or Cancelled; '
               'On Hold P1s count, On Hold P2s do not.')

lines = [l for l in open(SRC) if l.strip()]
dash = json.loads(lines[0])
panels = json.loads(dash['attributes']['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title')
done = set()
for p in panels:
    ec = p['embeddableConfig']
    t = title(p)
    if t in ('Needs attention now', 'Active P1', 'P2 over 8 h'):
        spec = json.loads(ec['savedVis']['params']['spec'])
        url = spec['data'][0]['url']
        assert OLD_ACTIVE in url['query'], t
        url['query'] = url['query'].replace(OLD_ACTIVE, NEW_ACTIVE)
        ec['savedVis']['params']['spec'] = json.dumps(spec, ensure_ascii=False, indent=2)
        if 'description' in ec:
            ec['description'] = (ec['description']
                                 .replace("Active = priority 1, 2 or 3 and the incident's latest record not On Hold, "
                                          "Resolved, Closed, Canceled or Cancelled.", ACTIVE_DESC))
        done.add(t)
    elif t == AI:
        st = ec['attributes']['state']
        old = st['query']['esql']
        assert 'hours_open' not in old, 'already patched'
        (layer,) = st['datasourceStates']['textBased']['layers'].values()
        layer['query'] = {'esql': AI_Q}
        st['query'] = {'esql': AI_Q}
        cols = layer['columns']
        i = next(n for n, c in enumerate(cols) if c['columnId'] == 'opened') + 1
        cols[i:i] = [
            {'columnId': 'hours_open', 'fieldName': 'hours_open', 'label': 'Time as P1 / Duration (h)', 'customLabel': True,
             'meta': {'type': 'number', 'esType': 'double'}, 'inMetricDimension': True,
             'params': {'format': {'id': 'number', 'params': {'decimals': 1}}}},
            {'columnId': 'linked_incidents', 'fieldName': 'linked_incidents', 'label': 'Linked incidents', 'customLabel': True,
             'meta': {'type': 'number', 'esType': 'long'}, 'inMetricDimension': True,
             'params': {'format': {'id': 'number', 'params': {'decimals': 0}}}}]
        vcols = st['visualization']['columns']
        i = next(n for n, c in enumerate(vcols) if c['columnId'] == 'opened') + 1
        vcols[i:i] = [{'columnId': 'hours_open', 'isTransposed': False, 'isMetric': True, 'alignment': 'right', 'width': 120},
                      {'columnId': 'linked_incidents', 'isTransposed': False, 'isMetric': True, 'alignment': 'right', 'width': 100}]
        ec['description'] = (
            'Every active P1 incident, and the active P2 incidents open longer than their 8 h target, P1 first, longest '
            'first. The P1 and P2 tiles above count these rows. ' + ACTIVE_DESC + ' Time as P1 / Duration (h): for a P1, '
            'hours since it became a P1 (MTTR so far; the time it became a P1 comes from the ServiceNow incident timeline, '
            'or the opened time if it was opened as a P1); for a P2, hours since it was opened (Duration). Linked incidents '
            '= incidents whose parent incident is this one, updated in the last 7 days (the user impact of a P1). Assignee '
            'and Group Manager (with their emails) come from the incident\'s assigned_to and assignment group. To '
            'investigate, pick the incident in the Incident control (or its Affected CI in the CI control). Click an '
            'Incident or an Affected CI to open it in ServiceNow. Last 7 days (fixed); not narrowed by the Incident or CI '
            'controls. Short description = the incident\'s short description from ServiceNow. Opened = when the incident '
            'was opened in ServiceNow.')
        done.add(t)
    elif t == TTR:
        st = ec['attributes']['state']
        old = st['query']['esql']
        assert 'MV_EXPAND k' in old and 'became_p1' not in old, 'patch 17b first, or already patched'
        for layer in st['datasourceStates']['textBased']['layers'].values():
            if layer['query']['esql'] == old:
                layer['query'] = {'esql': TTR_Q}
        st['query'] = {'esql': TTR_Q}
        st['visualization']['yTitle'] = 'Hours (rolling 7-day median)'
        ec['time_range'] = {'from': 'now-30d', 'to': 'now'}
        ec['description'] = (
            'P1 MTTR and P2 Duration, rolling 7-day median (since 17 Nov). P1 line: MTTR = hours from the time the '
            'incident became a P1 (from the ServiceNow incident timeline; the opened time if it was opened as a P1) to '
            'resolved. P2 line: Duration = hours from opened to resolved. Each point covers the P1 or P2 incidents resolved '
            'in the 7 days up to and including that day, for each of the last 7 days, against the targets P1 4 h (red '
            'dashed line) and P2 8 h (amber). A rising line = resolving more slowly. A P1 point stays on the chart for 7 '
            'days after the P1 is resolved; no P1 resolved in a window = no P1 point. Reads 30 days (badge) so the time '
            'a recently resolved P1 became a P1 is in range. Not narrowed by the Incident or CI controls.')
        done.add(t)
assert done == {'Needs attention now', 'Active P1', 'P2 over 8 h', AI, TTR}, done
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: P1 MTTR from became-P1, P2 Duration, Linked incidents, On Hold P1s shown')
