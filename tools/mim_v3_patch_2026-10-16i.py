"""MIM V3: related CIs from the full CMDB relationship graph, no blind spots; one applications table; "Times fired"
(16 Oct, ninth round).

Usage: mim_v3_patch_2026-10-16i.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-16h.py)

Seen: relationships in ServiceNow missing from the related-CI views and from "Applications that depend on this CI".
Causes and fixes:
- The panels read cmdb_app_dependencies_v2, an application-dependency extract. They now read cmdb-ci-relations*, the
  full ServiceNow relationship graph (34.2M links, every class, both directions).
- Only the classes in the Middleware / Database / Server / Application lists were shown. "Application View" becomes
  "Other related CIs": every related CI whose class is in none of the lists (load balancer pools, clusters, VMs,
  network gear, storage, IP addresses ...), so every relationship shows somewhere.
- Retired CIs were left out. They are now shown, marked "· retired" in the Type column and listed last. Links marked
  for deletion are left out.
- The CI name had to match exactly; it now also matches in upper and lower case.
- Relationship records are only re-sent when they change (oldest 2023), so these panels get a fixed range of
  "Last 5 years"; the dashboard's time picker would otherwise hide most of them.
Also:
- "Applications that depend on this CI" and "Application View" are one table, "Applications related to this CI":
  business applications, application services and application instances, in both directions, the relationship
  spelled out (e.g. "it consumes this CI", "this CI depends on it"). Its Application column can no longer open
  ServiceNow: the name comes from either side of the link, which Kibana 9.5 treats as created by the query.
- Blast radius counts, from the same graph, the applications that depend on the CI (above it), retired ones left out.
- "Count" in Open Alerts with No Incident and Alerts on this CI is renamed "Times fired".
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
IDX = 'cmdb-ci-relations*'
RANGE = {'from': 'now-5y', 'to': 'now'}
SEL = '(CASE(?incident == "(all incidents)", ?ci, SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)))'
MATCH = f'({SEL}, TO_UPPER({SEL}), TO_LOWER({SEL}))'
NOT_DELETED = 'COALESCE(TO_LOWER(TO_STRING(is_marked_for_deletion)), "false") != "true"'
APP_CLASS = lambda f: (f'({f} == "cmdb_ci_business_app" OR {f} LIKE "cmdb_ci_service*" OR {f} == "cmdb_ci_appl" '
                       f'OR {f} LIKE "cmdb_ci_appl_*")')

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = lambda t: next(p for p in panels if title(p) == t)
st = lambda p: p['embeddableConfig']['attributes']['state']
layer = lambda p: next(iter(st(p)['datasourceStates']['textBased']['layers'].values()))


def cut(s, old, new):
    assert s.count(old) == 1, (old, s.count(old))
    return s.replace(old, new)


def classes_and_kind(t):
    """The class list and the class -> label CASE of one of the existing views."""
    q = layer(P(t))['query']['esql']
    cls = q.split('child_ci.class.keyword IN (', 1)[1].split(')', 1)[0]
    kind = 'CASE(cls == ' + q.split('kind = CASE(cls == ', 1)[1].split(', cls)', 1)[0] + ', cls)'
    return cls, kind


def use_relations(p, q, rename=None):
    """Point a Lens ES|QL panel at the relationship graph, with a fixed 5-year range."""
    ec = p['embeddableConfig']
    s = st(p)
    L = layer(p)
    L['query'] = {'esql': q}
    s['query'] = {'esql': q}
    L['timeField'] = '@timestamp'
    for v in s['adHocDataViews'].values():
        v.update(title=IDX, name=IDX, timeFieldName='@timestamp')
    for r in s['datasourceStates']['textBased']['indexPatternRefs']:
        r.update(title=IDX, timeField='@timestamp')
    ec['time_range'] = dict(RANGE)
    if rename:
        ec['title'] = ec['attributes']['title'] = rename


def related_query(where_cls, kind_case, limit, rank='0'):
    return f"""FROM {IDX}
| WHERE (parent.name IN {MATCH} OR child.name IN {MATCH}) AND {NOT_DELETED}
| EVAL down = TO_LOWER(TO_STRING(parent.name)) == TO_LOWER({SEL})
| EVAL related = CASE(down, TO_STRING(child.name), TO_STRING(parent.name)),
       cls = COALESCE(CASE(down, TO_STRING(child.class), TO_STRING(parent.class)), "unknown"),
       env = CASE(down, TO_STRING(child.environment), TO_STRING(parent.environment)),
       inst = TO_LOWER(CASE(down, TO_STRING(child.install_status), TO_STRING(parent.install_status))),
       t = COALESCE(TO_STRING(type.name), "Linked to::Linked to")
| WHERE related IS NOT NULL AND TO_LOWER(related) != TO_LOWER({SEL}) AND {where_cls}
| EVAL verb = TO_LOWER(CASE(LOCATE(t, "::") > 0, SUBSTRING(t, 1, LOCATE(t, "::") - 1), t)),
       how = CASE(down, CONCAT("this CI ", verb, " it"), CONCAT("it ", verb, " this CI")),
       kind = {kind_case}, is_retired = CASE(inst == "retired", 1, 0), rank = {rank}
| STATS kinds = VALUES(kind), hows = VALUES(how), envs = VALUES(env), retired = MIN(is_retired), r = MIN(rank)
  BY related_ci = related
| EVAL ci_type = CONCAT(MV_FIRST(kinds), CASE(retired == 1, " · retired", "")), relation = MV_CONCAT(hows, "; "),
       env1 = MV_FIRST(envs)
| EVAL related_env = CASE(env1 IS NULL OR env1 == "null" OR env1 == "", "—", env1)
| SORT retired ASC, r ASC, ci_type ASC, related_ci ASC
| LIMIT {limit}
| KEEP related_ci, ci_type, relation, related_env"""


# ------------------------------------------------------------------ the three typed views
groups = {t: classes_and_kind(t) for t in ('Middleware View', 'Database View', 'Server View')}
for t, (cls, kind) in groups.items():
    p = P(t)
    use_relations(p, related_query(f'cls IN ({cls})', kind, 300))
    ec = p['embeddableConfig']
    ec['description'] = (ec['description'].split(' Both directions:', 1)[0] +
                         ' Both directions: "this CI runs on it" (the CI uses it) and "it runs on this CI" (it uses the '
                         'CI), with the relationship from ServiceNow. From the full CMDB relationship graph '
                         '(cmdb-ci-relations); retired CIs are listed last, marked "· retired"; links marked for '
                         'deletion are left out. CMDB data only, no live health; for live health pick the CI in the CI '
                         'control. Follows the Incident / CI controls. Last 5 years (fixed): relationship records are '
                         'only re-sent when they change, so a shorter window would hide most of them.')

# ------------------------------------------------------------------ Application View -> Other related CIs
all_cls = ', '.join(c for c, _ in groups.values())
p = P('Application View')
use_relations(p, related_query(f'NOT cls IN ({all_cls}) AND NOT {APP_CLASS("cls")}',
                               'REPLACE(REPLACE(cls, "^cmdb_ci_", ""), "_", " ")', 500), rename='Other related CIs')
p['embeddableConfig']['description'] = (
    'Every CI related to the selected CI in the CMDB whose class is not middleware, database, server or application '
    '(those have their own tables): load balancer pools, clusters, virtual machines, network gear, storage, disks, IP '
    'addresses and so on, so no relationship is left out. Type = the ServiceNow class. Both directions, with the '
    'relationship from ServiceNow. Retired CIs listed last, marked "· retired". From the full CMDB relationship graph '
    '(cmdb-ci-relations). Follows the Incident / CI controls. Last 5 years (fixed), as for the other related-CI views.')
for k in ('columns', 'allColumns'):
    for c in layer(p)[k]:
        c['label'] = {'related_ci': 'Related CI', 'ci_type': 'Type', 'relation': 'Relationship', 'related_env': 'Env'}[c['columnId']]

# ------------------------------------------------------------------ one applications table
p = P('Applications that depend on this CI')
app_kind = ('CASE(cls == "cmdb_ci_business_app", "Business application", cls LIKE "cmdb_ci_service*", '
            '"Application service", "Application")')
app_rank = 'CASE(cls == "cmdb_ci_business_app", 1, cls LIKE "cmdb_ci_service*", 2, 3)'
use_relations(p, related_query(APP_CLASS('cls'), app_kind, 500, rank=app_rank),
              rename='Applications related to this CI')
cols = {c['columnId']: c for c in layer(P('Middleware View'))['columns']}
labels = {'related_ci': 'Application', 'ci_type': 'Kind', 'relation': 'How', 'related_env': 'Env'}
new_cols = [dict(cols[c], label=labels[c]) for c in ('related_ci', 'ci_type', 'relation', 'related_env')]
layer(p)['columns'] = new_cols
layer(p)['allColumns'] = json.loads(json.dumps(new_cols))
vis = st(p)['visualization']
widths = {'related_ci': 300, 'ci_type': 170, 'relation': 330, 'related_env': 110}
vis['columns'] = [{'columnId': c, 'isTransposed': False, 'isMetric': True, 'alignment': 'left', 'width': widths[c]}
                  for c in ('related_ci', 'ci_type', 'relation', 'related_env')]
p['embeddableConfig'].pop('drilldowns', None)    # the name comes from either side of the link: Kibana 9.5 blocks it
p['embeddableConfig']['description'] = (
    'Every application related to the selected CI in the CMDB, in both directions: business applications, application '
    'services (by tags, calculated, discovered) and application instances. How = the relationship from ServiceNow, '
    'e.g. "it consumes this CI" (the application uses the CI: it is impacted if the CI fails) or "this CI depends on '
    'it". Business applications first. Retired ones listed last, marked "· retired". From the full CMDB relationship '
    'graph (cmdb-ci-relations). Follows the Incident / CI controls. Last 5 years (fixed): relationship records are '
    'only re-sent when they change.')

# ------------------------------------------------------------------ Blast radius from the same graph
p = P('Blast radius')
q = f"""FROM {IDX}
| WHERE child.name IN {MATCH} AND {APP_CLASS("parent.class")} AND {NOT_DELETED}
    AND COALESCE(TO_LOWER(TO_STRING(parent.install_status)), "") != "retired"
| EVAL app = TO_STRING(parent.name), cls = TO_STRING(parent.class)
| EVAL biz = CASE(cls == "cmdb_ci_business_app", app), svc = CASE(cls LIKE "cmdb_ci_service*", app),
       inst = CASE(cls == "cmdb_ci_appl" OR cls LIKE "cmdb_ci_appl_*", app)
| STATS apps = COUNT_DISTINCT(app), biz_n = COUNT_DISTINCT(biz), svc_n = COUNT_DISTINCT(svc), inst_n = COUNT_DISTINCT(inst)
| WHERE {SEL} != "(no CI selected)"
| EVAL label = "Applications", value = TO_DOUBLE(apps),
       detail = CONCAT("business apps ", TO_STRING(biz_n), " · app services ", TO_STRING(svc_n),
                       CASE(inst_n > 0, CONCAT(" · instances ", TO_STRING(inst_n)), ""))
| EVAL band = CASE(value >= 5, 0.9, value >= 1, 0.55, 0.1)
| EVAL rag_max = CASE(value <= 0, 1.0, value / band)
| KEEP label, value, detail, rag_max"""
use_relations(p, q)
p['embeddableConfig']['description'] = (
    'How many applications depend directly on the selected CI (they sit above it in the CMDB, e.g. "Claim Center '
    'consumes this CI"): business applications, application services and application instances; its blast radius. '
    'Amber from 1, red from 5. Retired applications are left out. From the full CMDB relationship graph '
    '(cmdb-ci-relations). Follows the Incident / CI controls. Last 5 years (fixed).')

# ------------------------------------------------------------------ "Count" -> "Times fired"
for t in ('Open Alerts with No Incident', 'Alerts on this CI'):
    p = P(t)
    n = 0
    for k in ('columns', 'allColumns'):
        for c in layer(p)[k]:
            if c.get('label') == 'Count':
                c['label'] = 'Times fired'
                n += 1
    assert n == 2, (t, n)
    ec = p['embeddableConfig']
    old, new = {
        'Open Alerts with No Incident': (
            'Count = how many times Netcool has seen it',
            'Times fired = how many times Netcool has seen the alert fire since it first appeared (its tally): a high '
            'number means a recurring or flapping problem, 1 or 2 a new one'),
        'Alerts on this CI': (
            'and how many times Netcool has seen it',
            'and how many times Netcool has seen it fire (Times fired: a high number means a recurring or flapping '
            'problem)')}[t]
    ec['description'] = cut(ec['description'], old, new)

# ------------------------------------------------------------------ other descriptions that named the old table
ec = P('Applications on this CI')['embeddableConfig']
ec['description'] = cut(ec['description'], '"Applications that depend on this CI"', '"Applications related to this CI"')

# ------------------------------------------------------------------ checks
s = json.dumps(panels, ensure_ascii=False)
assert 'cmdb_app_dependencies_v2' not in s, 'a panel still reads the old extract'
assert 'Application View' not in s and '"Applications that depend on this CI"' not in s
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{len(panels)} panels')
