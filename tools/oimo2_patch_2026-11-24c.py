"""Observability Incident Management Operations 2, patch 24c: Downstream and Upstream read only the data they use;
Services of the Application reads the whole CMDB application list again.

Usage: oimo2_patch_2026-11-24c.py "Observability Incident Management Operations 2.ndjson" (in place)

Why:
- Downstream and Upstream narrowed their data only after TO_LOWER(TO_STRING(service.environment)), which Elasticsearch
  cannot apply while reading, so they read every document of their indices in the last hour and filtered afterwards:
  Downstream every APM trace (traces-apm*), even with no CI or service picked; Upstream every metrics-apm.internal-* and
  metrics-apm.service_destination.1m-* document.
- Services of the Application: its range was cut to 24 hours in the uploaded copy, which drops the cmdb_with_apm_flag
  records loaded more than a day ago (the panel then lists no services). Its APM data is already limited to the last
  hour / 15 minutes while reading, so the 5-year range costs nothing.

Fix:
- Downstream and Upstream: a WHERE right after FROM that Elasticsearch applies while reading. It keeps a superset of
  the rows the query used (the query itself follows unchanged, so the rows are the same): Downstream all
  service_destination metrics (as before) and only the traces of the picked host or service (processor.event
  transaction, transaction.type request, url.domain present); Upstream metrics-apm.internal-* only for the picked host,
  service_destination only for the picked service (all of them when no service is picked). Host and service values go
  through KQL (resolved per index, so a field mapped differently in one index cannot break the query), with quotes and
  backslashes escaped.
- Services of the Application: time range back to the last 5 years (as Application Health). Query unchanged.
"""
import json
import sys

SRC = OUT = sys.argv[1]
SEL = '(CASE(?incident == "(all incidents)", ?ci, SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)))'
esc = lambda x: f'REPLACE({x}, "([\\\\\\\\\\"])", "\\\\\\\\$1")'   # KQL: \ -> \\, " -> \"
HOSTS = f'"host.name:(\\"", {esc(SEL)}, "\\" or \\"", {esc("TO_UPPER(" + SEL + ")")}, "\\")"'
SERVICE = f'"service.name:\\"", {esc("?service")}, "\\""'

PRE = {
    'Downstream — who is impacted ➡': (
        'FROM traces-apm*, metrics-apm.service_destination.1m-* METADATA _index\n',
        '| WHERE _index LIKE "*service_destination*"\n'
        '     OR (_index LIKE "*traces-apm*" AND KQL(CONCAT("processor.event:transaction and transaction.type:request '
        'and url.domain:* and (", ' + HOSTS + ', " or ", ' + SERVICE + ', ")")))\n', None),
    '⬅ Upstream — what they depend on': (
        'FROM metrics-apm.internal-*, metrics-apm.service_destination.1m-* METADATA _index\n',
        '| WHERE (_index LIKE "*service_destination*" AND (?service == "(services on this CI)" OR KQL(CONCAT(' + SERVICE + '))))\n'
        '     OR (_index LIKE "*apm.internal*" AND ?service == "(services on this CI)" AND KQL(CONCAT(' + HOSTS + ')))\n', None),
    'Services of the Application': (
        'FROM metrics-apm.service_transaction.1m-*, metrics-apm.internal-*, cmdb_with_apm_flag METADATA _index\n',
        '', {'from': 'now-5y', 'to': 'now'}),
}

lines = [json.loads(l) for l in open(SRC) if l.strip()]
(dash,) = [o for o in lines if o.get('type') == 'dashboard']
panels = json.loads(dash['attributes']['panelsJSON'])
done = []
for p in panels:
    ec = p['embeddableConfig']
    t = (ec.get('attributes') or {}).get('title')
    if t not in PRE:
        continue
    frm, pre, rng = PRE[t]
    st = ec['attributes']['state']
    old = st['query']['esql']
    assert old.startswith(frm) and old.count(frm) == 1 and 'KQL(' not in old, t
    new = frm + pre + old[len(frm):]   # pre == '': query unchanged
    n = 0
    for layer in st['datasourceStates']['textBased']['layers'].values():
        if layer['query']['esql'] == old:
            layer['query'] = {'esql': new}
            n += 1
    assert n == 1, t
    st['query'] = {'esql': new}
    if rng:
        ec['time_range'] = rng
    done.append(t)
assert sorted(done) == sorted(PRE), done
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
with open(OUT, 'w') as f:
    for o in lines:
        f.write(json.dumps(o, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: ' + ', '.join(done))
