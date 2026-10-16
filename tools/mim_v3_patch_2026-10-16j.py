"""MIM V3: Application Health follows the selected CI; production only everywhere; Short description back; Changes
after Escalate (16 Oct, tenth round).

Usage: mim_v3_patch_2026-10-16j.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-16i.py)

- Application Health: with a CI selected (the picked incident's CI, or the CI control), only the applications related
  to it: business applications linked to it in the CMDB (either direction), applications whose APM services run on it
  (a server), or the CI itself when it is a business application. With no CI selected: every production application,
  as before. The CMDB links need the 5-year range, so the panel's range is 5 years and the query itself keeps APM data
  to the last hour (written so Elasticsearch can apply it directly, not after reading everything).
- Production only: the related-CI tables (Applications related to this CI, Middleware / Database / Server View,
  Other related CIs), Blast radius, Applications on this CI and Open Alerts with No Incident keep production items
  only: environment starting "prod" or "prd" in any case (Production, Prod, PROD, prd1, prd2 ...). Items with no
  environment recorded are kept (shown "—"), so nothing related disappears unseen. Section 3 was already production
  only. The selected incident / CI itself is never hidden (Escalate, Alerts on this CI, health panels).
- Active Incidents: Short description back, as the last column.
- Changes in the Last 7 Days on this CI moves to right after Escalate.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
S2 = 'ca3d34a5-1eed-5555-a34b-4ae94ea7d242'
SEL = '(CASE(?incident == "(all incidents)", ?ci, SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)))'
MATCH = f'({SEL}, TO_UPPER({SEL}), TO_LOWER({SEL}))'
PROD = lambda e: f'(TO_LOWER({e}) LIKE "prod*" OR TO_LOWER({e}) LIKE "prd*")'
PROD_OR_BLANK = lambda e: f'({e} IS NULL OR {e} IN ("", "null") OR {PROD(e)})'

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = lambda t: next(p for p in panels if title(p) == t)
st = lambda p: p['embeddableConfig']['attributes']['state']
layer = lambda p: next(iter(st(p)['datasourceStates']['textBased']['layers'].values()))


def cut(s, old, new):
    assert s.count(old) == 1, (old[:80], s.count(old))
    return s.replace(old, new)


def edit(p, *pairs):
    q = layer(p)['query']['esql']
    for old, new in pairs:
        q = cut(q, old, new)
    layer(p)['query']['esql'] = q
    st(p)['query'] = {'esql': q}


def describe(p, old, new):
    ec = p['embeddableConfig']
    ec['description'] = cut(ec['description'], old, new)


PROD_NOTE = (' Production only: items whose environment starts with "prod" or "prd" (any case); items with no '
             'environment recorded are kept, shown "—".')

# ------------------------------------------------------------------ production only: related-CI tables
for t in ('Applications related to this CI', 'Middleware View', 'Database View', 'Server View', 'Other related CIs'):
    p = P(t)
    edit(p, ('| WHERE related IS NOT NULL AND TO_LOWER(related) != TO_LOWER(',
             f'| WHERE {PROD_OR_BLANK("env")} AND related IS NOT NULL AND TO_LOWER(related) != TO_LOWER('))
    p['embeddableConfig']['description'] += PROD_NOTE

p = P('Blast radius')
edit(p, ('    AND COALESCE(TO_LOWER(TO_STRING(parent.install_status)), "") != "retired"',
         '    AND COALESCE(TO_LOWER(TO_STRING(parent.install_status)), "") != "retired"\n'
         f'    AND {PROD_OR_BLANK("TO_STRING(parent.environment)")}'))
p['embeddableConfig']['description'] += PROD_NOTE

p = P('Applications on this CI')
edit(p, ('| STATS last_seen = MAX(@timestamp)',
         f'| WHERE {PROD("TO_STRING(service.environment)")}\n| STATS last_seen = MAX(@timestamp)'))
describe(p, 'in the last 7 days, most recent first, with their environment.',
         'in the last 7 days, most recent first, with their environment. Production services only (environment '
         'starting "prod" or "prd").')

p = P('Open Alerts with No Incident')
edit(p, ('| WHERE src == "alert" AND has_inc == 0\n',
         f'| WHERE src == "alert" AND has_inc == 0 AND {PROD_OR_BLANK("TO_STRING(ci.environment)")}\n'))
p['embeddableConfig']['description'] += (' Production only: alerts on CIs whose environment starts with "prod" or '
                                         '"prd"; alerts whose node is not in the CMDB (no environment) are kept.')

# ------------------------------------------------------------------ Application Health follows the CI
p = P('Application Health')
q = layer(p)['query']['esql']
head = """FROM metrics-apm.service_transaction.1m-*
| WHERE TO_LOWER(TO_STRING(service.environment)) IN ("prd1", "prd2", "prd", "prod", "production") AND ci.name IS NOT NULL
| STATS ok"""
assert q.startswith(head), q[:300]
NO_CI = f'{SEL} == "(no CI selected)"'
new_head = f"""FROM metrics-apm.service_transaction.1m-*, metrics-apm.internal-*, cmdb-ci-relations* METADATA _index
| WHERE @timestamp >= NOW() - 1 hour OR parent.name IN {MATCH} OR child.name IN {MATCH}
| EVAL src = CASE(_index LIKE "*relations*", "rel", _index LIKE "*apm.internal*", "host", "tx")
| WHERE (src == "tx" AND @timestamp >= NOW() - 1 hour AND ci.name IS NOT NULL
         AND TO_LOWER(TO_STRING(service.environment)) IN ("prd1", "prd2", "prd", "prod", "production"))
     OR (src == "host" AND @timestamp >= NOW() - 1 hour AND NOT {NO_CI} AND host.name IN {MATCH})
     OR (src == "rel" AND NOT {NO_CI} AND COALESCE(TO_LOWER(TO_STRING(is_marked_for_deletion)), "false") != "true")
| EVAL down = TO_LOWER(TO_STRING(parent.name)) == TO_LOWER({SEL}),
       rel_app = CASE(src == "rel" AND down AND child.class == "cmdb_ci_business_app", TO_STRING(child.name),
                      src == "rel" AND NOT down AND parent.class == "cmdb_ci_business_app", TO_STRING(parent.name))
| EVAL app_key = TO_LOWER(COALESCE(rel_app, TO_STRING(ci.name))),
       is_rel = CASE(rel_app IS NOT NULL, 1, 0), is_host = CASE(src == "host", 1, 0)
| INLINE STATS linked_app = MAX(is_rel) BY app_key
| INLINE STATS service_on_ci = MAX(is_host) BY service.name
| WHERE src == "tx" AND ({NO_CI} OR linked_app == 1 OR service_on_ci == 1 OR app_key == TO_LOWER({SEL}))
| STATS ok"""
q = new_head + q[len(head):]
layer(p)['query']['esql'] = q
st(p)['query'] = {'esql': q}
idx = 'metrics-apm.service_transaction.1m-*,metrics-apm.internal-*,cmdb-ci-relations*'
for v in st(p)['adHocDataViews'].values():
    v.update(title=idx, name=idx, timeFieldName='@timestamp')
for r in st(p)['datasourceStates']['textBased']['indexPatternRefs']:
    r.update(title=idx, timeField='@timestamp')
layer(p)['timeField'] = '@timestamp'
p['embeddableConfig']['time_range'] = {'from': 'now-5y', 'to': 'now'}
p['embeddableConfig']['description'] = (
    'With a CI selected (the picked incident\'s CI, or the CI control): the production business applications related '
    'to it, so you can start investigating from the CI — applications linked to it in the CMDB (either direction, e.g. '
    '"Claim Center consumes this CI"), applications whose APM services run on it (a server), or the CI itself when it '
    'is a business application. With no CI selected: every production business application with APM data. '
    + p['embeddableConfig']['description'].split('Every production business application with APM data, ', 1)[1]
    + ' Health covers the last hour (set in the query); the panel shows "Last 5 years" because the CMDB links it reads '
      'are only re-sent when they change.')

# ------------------------------------------------------------------ Active Incidents: Short description back
p = P('Active Incidents (P1 / P2 / P3)')
edit(p, ('managers = VALUES(TO_STRING(assignment_group.manager.name)), manager_emails = VALUES(TO_STRING(assignment_group.manager.email))\n  BY number, priority, ci.name, state_name',
         'managers = VALUES(TO_STRING(assignment_group.manager.name)), manager_emails = VALUES(TO_STRING(assignment_group.manager.email)),\n        descr = VALUES(TO_STRING(short_description))\n  BY number, priority, ci.name, state_name'),
     ('group_manager = COALESCE(MV_FIRST(managers), "—"), manager_email = COALESCE(MV_FIRST(manager_emails), "—")',
      'group_manager = COALESCE(MV_FIRST(managers), "—"), manager_email = COALESCE(MV_FIRST(manager_emails), "—"),\n       short_description = COALESCE(MV_FIRST(descr), "—")'),
     ('| KEEP number, priority, ci.name, state_name, sla, assignment_group, assignee, assignee_email, group_manager, manager_email',
      '| KEEP number, priority, ci.name, state_name, sla, assignment_group, assignee, assignee_email, group_manager, manager_email, short_description'))
col = {'columnId': 'short_description', 'fieldName': 'short_description', 'label': 'Short description',
       'customLabel': True, 'meta': {'type': 'string', 'esType': 'keyword'}, 'inMetricDimension': True}
for k in ('columns', 'allColumns'):
    layer(p)[k].append(dict(col))
st(p)['visualization']['columns'].append({'columnId': 'short_description', 'isTransposed': False, 'isMetric': True,
                                          'alignment': 'left', 'width': 420})
p['embeddableConfig']['description'] += ' Short description = the incident\'s short description from ServiceNow.'

# ------------------------------------------------------------------ Changes right after Escalate
esc = P('Escalate')['gridData']
chg = P('Changes in the Last 7 Days on this CI')['gridData']
start, h = esc['y'] + esc['h'], chg['h']
for p in panels:
    g = p['gridData']
    if g['sectionId'] == S2 and g is not chg and g['y'] >= start:
        g['y'] += h
chg.update(y=start, x=0)

# ------------------------------------------------------------------ checks: no overlaps
for sec in {p['gridData']['sectionId'] for p in panels}:
    cells = {}
    for p in panels:
        g = p['gridData']
        if g['sectionId'] != sec:
            continue
        for x in range(g['x'], g['x'] + g['w']):
            for y in range(g['y'], g['y'] + g['h']):
                assert (x, y) not in cells, (title(p), cells[(x, y)])
                cells[(x, y)] = title(p)
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{len(panels)} panels')
