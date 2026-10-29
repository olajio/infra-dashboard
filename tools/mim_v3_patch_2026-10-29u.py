"""MIM V3: telemetry onboarding in Application Health, and a Telemetry control (29 Oct 2026).

Usage: mim_v3_patch_2026-10-29u.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-28t.py)

`cmdb_with_apm_flag` (Round 18) lists every CMDB business application with `is_monitored` = enrolled for Elastic
telemetry onboarding. Every application that sends APM data is enrolled, so the list adds the enrolled applications
that send nothing yet:
- Application Health also reads `cmdb_with_apm_flag`. An enrolled, non-retired application with no APM data in the
  last hour (matched on the application number) is listed as "Enrolled — no telemetry yet", after every other row.
  With "(all applications)" in the new Telemetry control this happens only when no CI is picked (those applications
  have no APM data or CMDB relation that could tie them to a CI); otherwise the panel is unchanged.
- New Telemetry control in section 3: "(all applications)" (default) or "Enrolled, no telemetry yet", which lists only
  those applications, whatever the CI: the onboarding worklist.
"""
import copy
import json
import sys
import uuid

SRC, OUT = sys.argv[1:3]
FLAG = 'cmdb_with_apm_flag'
ALL, SILENT = '(all applications)', 'Enrolled, no telemetry yet'
LABEL = 'Enrolled — no telemetry yet'
CI = 'CASE(?incident == "(all incidents)", ?ci, SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))'

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = {title(p): p for p in panels}
assert 'Telemetry' not in P, 'already applied?'
app = P['Application Health']['embeddableConfig']
st = app['attributes']['state']
q = st['query']['esql']


def sub(s, old, new):
    assert s.count(old) == 1, old[:90]
    return s.replace(old, new)


q = sub(q, 'FROM metrics-apm.service_transaction.1m-*, metrics-apm.internal-*, cmdb-ci-relations* METADATA _index',
        f'FROM metrics-apm.service_transaction.1m-*, metrics-apm.internal-*, cmdb-ci-relations*, {FLAG} METADATA _index')
q = sub(q, '| WHERE (@timestamp >= NOW() - 15 minutes OR',
        f'| WHERE _index LIKE "*{FLAG}*" OR (@timestamp >= NOW() - 15 minutes OR')
q = sub(q, '| EVAL src = CASE(_index LIKE "*relations*", "rel",',
        f'| EVAL src = CASE(_index LIKE "*{FLAG}*", "flag", _index LIKE "*relations*", "rel",')
q = sub(q, '\n| EVAL down = ',
        '\n     OR (src == "flag" AND is_monitored == true AND COALESCE(TO_LOWER(TO_STRING(install_status)), "") != "retired")'
        '\n| EVAL down = ')
q = sub(q, '\n| INLINE STATS linked_app = MAX(is_rel) BY app_key',
        '\n| EVAL num = CASE(src == "flag", TO_STRING(`number.keyword`), src == "tx", TO_STRING(ci.number))'
        '\n| INLINE STATS has_tx = MAX(CASE(src == "tx", 1, 0)) BY num'
        '\n| INLINE STATS linked_app = MAX(is_rel) BY app_key')
start = q.index('| WHERE src == "tx" AND (')
end = q.index('\n| STATS ok = ', start)
cond = q[start + len('| WHERE src == "tx" AND '):end]
q = (q[:start]
     + f'| WHERE (src == "tx" AND ?telemetry == "{ALL}" AND {cond})\n'
     + f'     OR (src == "flag" AND has_tx == 0 AND (?telemetry == "{SILENT}" OR ({CI}) == "(no CI selected)"))\n'
     + '| EVAL ci.name = CASE(src == "flag", TO_STRING(`name.keyword`), ci.name), is_flag = CASE(src == "flag", 1, 0),\n'
     + '       grp = COALESCE(TO_STRING(ci.support_group.l2.name), TO_STRING(support_group.l2.name))'
     + q[end:])
q = sub(q, 'nums = VALUES(TO_STRING(ci.number)), groups = VALUES(TO_STRING(ci.support_group.l2.name)),',
        'nums = VALUES(num), groups = VALUES(grp), flag_row = MAX(is_flag),')
q = sub(q, 'hosts = VALUES(hosts)\n  BY ci.name\n', 'hosts = VALUES(hosts), flag_row = MAX(flag_row)\n  BY ci.name\n')
q = sub(q, '| EVAL app_health = CASE(failing > 0,', f'| EVAL app_health = CASE(flag_row == 1, "{LABEL}", failing > 0,')
q = sub(q, '       rank = CASE(failing > 0, 1,',
        '       services = CASE(flag_row == 1, TO_LONG(0), services), rank = CASE(flag_row == 1, 5, failing > 0, 1,')

old = st['query']['esql']
layers = [L for L in st['datasourceStates']['textBased']['layers'].values() if L.get('query', {}).get('esql') == old]
assert len(layers) == 1
st['query']['esql'] = layers[0]['query']['esql'] = q

col = next(c for c in st['visualization']['columns'] if c['columnId'] == 'app_health')
col['colorMapping']['assignments'].append({
    'rules': [{'type': 'match', 'pattern': LABEL, 'matchEntireWord': True, 'matchCase': True}],
    'color': {'type': 'colorCode', 'colorCode': '#7b61a8'}, 'touched': True})
col['width'] = 215
app['description'] = sub(
    app['description'], 'With no CI selected: every production business application with APM data.',
    'With no CI selected: every production business application with APM data, then the business applications '
    f'enrolled for Elastic telemetry onboarding that sent no APM data in the last hour ("{LABEL}", from '
    f'{FLAG}, matched on the application number; retired applications left out). The Telemetry control set to '
    f'"{SILENT}" lists only those, whatever the CI: the onboarding worklist.')

# ---- Telemetry control, in the section 3 control row ----
ctl_row = sorted((p for p in panels if p['type'] == 'esql_control'), key=lambda p: p['gridData']['x'])
assert [title(p) for p in ctl_row] == ['Server', 'Health window', 'Service', 'Application']
service = P['Service']
pid = str(uuid.uuid5(uuid.NAMESPACE_URL, 'mim-v3/section3/control-telemetry'))
tel = copy.deepcopy(service)
tel['panelIndex'] = pid
tel['embeddableConfig'] = {
    'control_type': 'VALUES_FROM_QUERY',
    'esql_query': f'ROW telemetry = ["{ALL}", "{SILENT}"]\n| MV_EXPAND telemetry',
    'selected_options': [ALL], 'single_select': True, 'title': 'Telemetry', 'variable_name': 'telemetry',
    'variable_type': 'values'}
for p, (x, w) in zip(ctl_row + [tel], [(0, 10), (10, 8), (18, 10), (28, 10), (38, 10)]):
    p['gridData'].update({'x': x, 'w': w, 'i': p['panelIndex']})
panels.insert(panels.index(P['Application']) + 1, tel)

A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print('Application Health reads cmdb_with_apm_flag; Telemetry control added')
