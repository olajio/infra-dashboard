"""Patch 03w (3 Nov 2026): a "Monitored application" control in the top bar, scoped to the applications MIM escalates;
the section 3 Telemetry control is removed.

Usage: mim_patch_2026-11-03w.py "MIM V4.ndjson" "MIM V4.ndjson"     (after 02v)

Scope = the applications in `cmdb_with_apm_flag` with install_status "In Production", operational_status
"Operational" and is_monitored true (138 business applications on 2 Nov). APM data is matched to them on the APM
number (`number.keyword` in the index, `ci.number` in APM), as Application Health already did.

- New pinned control **Monitored application** (variable ?monitored_app), after Incident and CI: the scoped
  applications, default "(all monitored applications)".
- **Application Health**: lists only scoped applications (or the one picked); scoped applications with no APM data
  stay listed as "Enrolled — no telemetry yet" when no CI is picked (that used to need Telemetry = "Enrolled ...").
- **Services of the Application**: only services of scoped applications (or the one picked), then the section 3
  Application control as before. It now reads the index too, so its panel range is 5 years and the 1-hour (APM
  transactions) and 15-minute (servers) windows are set in the query; "Per minute" divides by 60.
- Section 3 **Application** and **Service** lists: only scoped applications and their services. Service health,
  Upstream and Downstream follow the Service picked, so they are scoped through it.
- **Telemetry** control removed; Server, Application, Service and Health window share the row (12 columns each).
"""
import json
import sys
import uuid

SRC, OUT = sys.argv[1:3]
ALL = '(all monitored applications)'
SCOPE = ('is_monitored == true AND TO_STRING(`install_status.keyword`) == "In Production" '
         'AND TO_STRING(`operational_status.keyword`) == "Operational"')
PICKED = f'(?monitored_app == "{ALL}" OR TO_STRING(`name.keyword`) == ?monitored_app)'
PROD = 'TO_LOWER(TO_STRING(service.environment)) IN ("prd1", "prd2", "prd", "prod", "production")'

CONTROL_Q = f"""FROM cmdb_with_apm_flag
| WHERE {SCOPE}
| STATS apps = VALUES(TO_STRING(`name.keyword`))
| EVAL monitored_app = CASE(apps IS NULL, "{ALL}", MV_APPEND("{ALL}", apps))
| MV_EXPAND monitored_app
| EVAL ord = CASE(monitored_app == "{ALL}", 0, 1)
| SORT ord ASC, monitored_app ASC
| KEEP monitored_app"""


def scoped_list(value, default, field):
    """Section 3 Application / Service list: values from APM transactions of scoped applications only."""
    return f"""FROM metrics-apm.service_transaction.1m-*, cmdb_with_apm_flag METADATA _index
| WHERE _index LIKE "*cmdb_with_apm_flag*" OR @timestamp >= NOW() - 1 day
| EVAL flag = _index LIKE "*cmdb_with_apm_flag*"
| WHERE (flag AND {SCOPE}) OR (NOT flag AND {PROD} AND ci.name IS NOT NULL)
| EVAL num = CASE(flag, TO_STRING(`number.keyword`), TO_STRING(ci.number)), v = CASE(NOT flag, TO_STRING({field}))
| STATS listed = MAX(CASE(flag, 1, 0)), vals = VALUES(v) BY num
| WHERE listed == 1 AND MV_COUNT(vals) > 0
| MV_EXPAND vals
| STATS s = VALUES(vals)
| EVAL {value} = CASE(s IS NULL, "{default}", MV_APPEND("{default}", s))
| MV_EXPAND {value}
| EVAL ord = CASE({value} == "{default}", 0, 1)
| SORT ord ASC, {value} ASC
| KEEP {value}"""


SERVICES_HEAD_OLD = """FROM metrics-apm.service_transaction.1m-*, metrics-apm.internal-* METADATA _index
| WHERE (_index LIKE "*service_transaction*" OR @timestamp >= NOW() - 15 minutes) AND TO_LOWER(TO_STRING(service.environment)) IN ("prd1", "prd2", "prd", "prod", "production")
| EVAL is_tx = _index LIKE "*service_transaction*"
| WHERE (is_tx AND ci.name IS NOT NULL AND (?application == "(all applications)" OR ci.name == ?application))
     OR (NOT is_tx AND host.name IS NOT NULL)
"""
SERVICES_HEAD_NEW = f"""FROM metrics-apm.service_transaction.1m-*, metrics-apm.internal-*, cmdb_with_apm_flag METADATA _index
| WHERE _index LIKE "*cmdb_with_apm_flag*"
     OR (_index LIKE "*service_transaction*" AND @timestamp >= NOW() - 1 hour)
     OR (_index LIKE "*apm.internal*" AND @timestamp >= NOW() - 15 minutes)
| EVAL src = CASE(_index LIKE "*cmdb_with_apm_flag*", "flag", _index LIKE "*service_transaction*", "tx", "host")
| WHERE (src == "flag" AND {SCOPE} AND {PICKED})
     OR (src == "tx" AND {PROD} AND ci.name IS NOT NULL AND (?application == "(all applications)" OR ci.name == ?application))
     OR (src == "host" AND {PROD} AND host.name IS NOT NULL)
| EVAL num = CASE(src == "flag", TO_STRING(`number.keyword`), src == "tx", TO_STRING(ci.number))
| INLINE STATS in_scope = MAX(CASE(src == "flag", 1, 0)) BY num
| WHERE (src == "tx" AND in_scope == 1) OR src == "host"
| EVAL is_tx = src == "tx"
"""

HEALTH_REPLACE = [
    ('OR (src == "flag" AND is_monitored == true AND COALESCE(TO_LOWER(TO_STRING(install_status)), "") != "retired")',
     f'OR (src == "flag" AND {SCOPE} AND {PICKED})'),
    ('| INLINE STATS has_tx = MAX(CASE(src == "tx", 1, 0)) BY num',
     '| INLINE STATS has_tx = MAX(CASE(src == "tx", 1, 0)), in_scope = MAX(CASE(src == "flag", 1, 0)) BY num'),
    ('(src == "tx" AND ?telemetry == "(all applications)" AND (', '(src == "tx" AND in_scope == 1 AND ('),
]
CI = 'CASE(?incident == "(all incidents)", ?ci, SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))'
HEALTH_FLAG_OLD = f'(src == "flag" AND has_tx == 0 AND (?telemetry == "Enrolled, no telemetry yet" OR ({CI}) == "(no CI selected)"))'
HEALTH_FLAG_NEW = f'(src == "flag" AND has_tx == 0 AND ({CI}) == "(no CI selected)")'

lines = [json.loads(l) for l in open(SRC) if l.strip()]
dash = next(o for o in lines if o.get('type') == 'dashboard')
A = dash['attributes']
assert 'monitored_app' not in json.dumps(A['pinned_panels']), 'already applied'
panels = json.loads(A['panelsJSON'])
P = {p['embeddableConfig'].get('title'): p for p in panels}


def set_lens_query(p, old_q, new_q):
    st = p['embeddableConfig']['attributes']['state']
    assert st['query']['esql'] == old_q
    st['query']['esql'] = new_q
    for layer in st['datasourceStates']['textBased']['layers'].values():
        if layer['query']['esql'] == old_q:
            layer['query']['esql'] = new_q


# Application Health
h = P['Application Health']
q = h['embeddableConfig']['attributes']['state']['query']['esql']
new = q
for a, b in HEALTH_REPLACE + [(HEALTH_FLAG_OLD, HEALTH_FLAG_NEW)]:
    assert new.count(a) == 1, a[:70]
    new = new.replace(a, b)
assert '?telemetry' not in new
set_lens_query(h, q, new)
h['embeddableConfig']['description'] = (
    h['embeddableConfig'].get('description', '').split(' Telemetry control')[0].rstrip()
    + ' Only the applications MIM escalates: cmdb_with_apm_flag with install status "In Production", operational '
      'status "Operational" and monitored = true (the Monitored application control at the top picks one). Of these, '
      'applications with no APM data yet are listed last as "Enrolled — no telemetry yet" when no CI is picked.')

# Services of the Application
s = P['Services of the Application']
q = s['embeddableConfig']['attributes']['state']['query']['esql']
assert q.startswith(SERVICES_HEAD_OLD)
new = SERVICES_HEAD_NEW + q[len(SERVICES_HEAD_OLD):]
old_min = '| EVAL minutes = GREATEST(DATE_DIFF("minutes", ?_tstart, ?_tend), 1)\n'
assert new.count(old_min) == 1
new = new.replace(old_min, '| EVAL minutes = 60\n')
set_lens_query(s, q, new)
s['embeddableConfig']['time_range'] = {'from': 'now-5y', 'to': 'now'}
s['embeddableConfig']['description'] = (
    s['embeddableConfig'].get('description', '').rstrip()
    + ' Only services of the applications MIM escalates (the Monitored application control at the top: all of them, '
      'or the one picked), matched on the APM number. Transactions of the last hour; the panel shows "Last 5 years" '
      'only because it also reads cmdb_with_apm_flag.')

# Section 3 Application and Service lists
P['Application']['embeddableConfig']['esql_query'] = scoped_list('application', '(all applications)', 'ci.name')
P['Service']['embeddableConfig']['esql_query'] = scoped_list('service', '(services on this CI)', 'service.name')

# Telemetry control out; the row re-laid
panels = [p for p in panels if p['embeddableConfig'].get('title') != 'Telemetry']
x = 0
for t in ('Server', 'Application', 'Service', 'Health window'):
    P[t]['gridData'].update(x=x, w=12)
    x += 12
assert '?telemetry' not in json.dumps(panels)
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)

# The new control in the top bar, after Incident and CI
pinned = A['pinned_panels']['panels']
order = max(v['order'] for v in pinned.values()) + 1
pinned[str(uuid.uuid5(uuid.NAMESPACE_URL, 'mim-dashboard/v4/control/monitored_app'))] = {
    'config': {'control_type': 'VALUES_FROM_QUERY', 'esql_query': CONTROL_Q, 'selected_options': [ALL],
               'single_select': True, 'title': 'Monitored application', 'variable_name': 'monitored_app',
               'variable_type': 'values'},
    'grow': False, 'order': order, 'type': 'esql_control', 'width': 'large'}

with open(OUT, 'w') as f:
    for o in lines:
        f.write(json.dumps(o, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: Monitored application control added (order {order}); Telemetry removed; '
      'Application Health, Services of the Application, Application and Service lists scoped')
