"""Observability Incident Management Operations 2 (24 Nov 2026): a copy of "Observability Incident Management
Operations" (the uploaded export) with the Application Health query made light on the cluster.

Usage: oimo2_patch_2026-11-24a.py "Observability Incident Management Operations.ndjson" \
           "Observability Incident Management Operations 2.ndjson"

Why Application Health was heavy: the query only narrowed its data (APM: last hour / 15 minutes; CMDB relations: the
picked CI) in a WHERE that came after EVALs, so Elasticsearch could not apply it while reading. It read every document
of metrics-apm.service_transaction.1m-*, metrics-apm.internal-*, cmdb-ci-relations* and cmdb_with_apm_flag in the
panel's time range, and did so several times (once per INLINE STATS). The uploaded copy cut the range to 24 hours,
which made it lighter but also dropped the CMDB records loaded more than 24 hours ago, so related applications went
missing.

Fix (Application Health only, nothing else changes):
- a WHERE right after FROM that Elasticsearch applies while reading: cmdb_with_apm_flag (all of it), anything from the
  last 15 minutes, service_transaction from the last hour, and the cmdb-ci-relations records of the picked CI (a KQL
  query on parent.name / child.name: KQL is resolved per index, so the text / keyword mapping differences of
  cmdb_with_apm_flag cannot break it; quotes and backslashes in CI names are escaped). The original query follows
  unchanged, so the rows are the same as before.
- time range back to the last 5 years, so all CMDB records are read again (the APM data is limited by the query).
The new dashboard gets its own id and the title "Observability Incident Management Operations 2"; the tags are kept.
"""
import json
import sys
import uuid

SRC, OUT = sys.argv[1:3]
TITLE = 'Observability Incident Management Operations 2'
NEW_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, 'kibana/dashboard/' + TITLE))
APP_HEALTH = '066a72ec-21c0-5ed4-8920-c524d3422463'
FROM = 'FROM metrics-apm.service_transaction.1m-*, metrics-apm.internal-*, cmdb-ci-relations*, cmdb_with_apm_flag METADATA _index\n'

SEL = '(CASE(?incident == "(all incidents)", ?ci, SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)))'
esc = lambda x: f'REPLACE({x}, "([\\\\\\\\\\"])", "\\\\\\\\$1")'   # KQL: \ -> \\, " -> \"
variants = [esc(SEL), esc(f'TO_UPPER({SEL})'), esc(f'TO_LOWER({SEL})')]
kql_field = lambda f: f'"{f}:(\\"", ' + ', "\\" or \\"", '.join(variants) + ', "\\")"'
KQL = 'KQL(CONCAT(' + kql_field('parent.name') + ', " or ", ' + kql_field('child.name') + '))'
PREFILTER = ('| WHERE _index LIKE "*cmdb_with_apm_flag*" OR @timestamp >= NOW() - 15 minutes\n'
             '     OR (@timestamp >= NOW() - 1 hour AND _index LIKE "*service_transaction*")\n'
             '     OR (_index LIKE "*relations*" AND ' + KQL + ')\n')

lines = [json.loads(l) for l in open(SRC) if l.strip()]
(dash,) = [o for o in lines if o.get('type') == 'dashboard']
dash['id'] = NEW_ID
dash['attributes']['title'] = TITLE
panels = json.loads(dash['attributes']['panelsJSON'])
(p,) = [p for p in panels if p['gridData']['i'] == APP_HEALTH]
ec = p['embeddableConfig']
assert ec['attributes']['title'] == 'Application Health'
st = ec['attributes']['state']
old = st['query']['esql']
assert old.startswith(FROM) and old.count(FROM) == 1 and 'KQL(' not in old
new = FROM + PREFILTER + old[len(FROM):]
n = 0
for layer in st['datasourceStates']['textBased']['layers'].values():
    if layer['query']['esql'] == old:
        layer['query'] = {'esql': new}
        n += 1
assert n == 1
st['query'] = {'esql': new}
ec['time_range'] = {'from': 'now-5y', 'to': 'now'}
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
for o in lines:   # keep the export's last line (counts) as it is
    pass
with open(OUT, 'w') as f:
    for o in lines:
        f.write(json.dumps(o, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: {TITLE} ({NEW_ID}); Application Health filtered while reading, time range last 5 years')
