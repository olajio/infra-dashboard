"""MIM V5 patch 17e (17 Nov 2026), on top of 17d: Application Health / Services of the Application error fixed, and
the Dashboard Links section copied from Infrastructure Overview v2.

Usage: mim_v5_patch_2026-11-17e.py "MIM V5.ndjson" "Infrastructure Overview v2.ndjson" "MIM V5.ndjson"

1. Error "Cannot use field [ci.name] due to ambiguities being mapped as [2] incompatible types: [keyword] in
   [.ds-metrics-apm.internal-…] … [text] in [cmdb_with_apm_flag]" (es_error.png): cmdb_with_apm_flag now has a
   ci.name field mapped as text, while APM maps ci.name as keyword, and ES|QL refuses a field with two types unless it
   is converted where it is read. Each query that reads APM and cmdb_with_apm_flag together (Application Health,
   Services of the Application, and the Application and Service controls) now converts ci.name once, right after
   FROM, and leaves it empty on the cmdb_with_apm_flag rows, as before (those rows use name.keyword).
2. Section 4 "Related dashboards" (Applications Operations and Infra Dashboard links) is replaced by an identical copy
   of Infrastructure Overview v2's "Dashboard Links" section (patch infra_overview_v2_patch_2026-11-17b.py): same
   headings, links, font, order and layout; panel ids are MIM's own.
"""
import json
import sys
import uuid

SRC, IO, OUT = sys.argv[1:4]
FIX = ('\n| EVAL ci.name = CASE(NOT (_index LIKE "*cmdb_with_apm_flag*"), TO_STRING(ci.name))'
       )
FIXED = {'Application Health', 'Services of the Application', 'service', 'application'}

dash = json.loads([l for l in open(SRC) if l.strip()][0])
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')


def fix(q, name):
    assert 'cmdb_with_apm_flag' in q and 'METADATA _index' in q, name
    assert 'EVAL ci.name = CASE(NOT (_index LIKE' not in q, f'{name}: already patched'
    first, rest = q.split('\n', 1)
    assert first.startswith('FROM '), name
    return first + FIX + '\n' + rest


done = set()
for p in panels:
    ec = p['embeddableConfig']
    if p['type'] == 'vis' and title(p) in FIXED:
        st = ec['attributes']['state']
        old = st['query']['esql']
        q = fix(old, title(p))
        for layer in st['datasourceStates']['textBased']['layers'].values():
            if layer['query']['esql'] == old:
                layer['query'] = {'esql': q}
        st['query'] = {'esql': q}
        done.add(title(p))
    elif p['type'] == 'esql_control' and ec.get('variable_name') in FIXED and 'cmdb_with_apm_flag' in ec['esql_query']:
        ec['esql_query'] = fix(ec['esql_query'], ec['variable_name'])
        done.add(ec['variable_name'])
assert done == FIXED, done
# no other query reads APM and cmdb_with_apm_flag together without the fix
for p in panels:
    s = json.dumps(p)
    if 'cmdb_with_apm_flag' in s and 'metrics-apm' in s:
        assert 'EVAL ci.name = CASE(NOT (_index LIKE' in s, title(p)

# ---- section 4: Dashboard Links copied from Infrastructure Overview v2 ----
io = json.loads([l for l in open(IO) if l.strip()][0])['attributes']
io_s2 = next(s for s in io['sections'] if 'Dashboard Links' in s['title'])
io_links = [p for p in json.loads(io['panelsJSON']) if p['gridData'].get('sectionId') == io_s2['gridData']['i']]
assert io_links and all(p['type'] == 'markdown' for p in io_links), 'Infrastructure Overview v2: run its patch 17b first'
assert any('Executive Dashboard (In Progress)](' in p['embeddableConfig']['content'] for p in io_links), 'IO patch 17b first'

s4 = next(s for s in A['sections'] if s['title'] == '🔗 4 · Related dashboards')
S4 = s4['gridData']['i']
s4['title'] = '🔗 4 · Dashboard Links'
old4 = [p for p in panels if p['gridData'].get('sectionId') == S4]
assert {title(p) for p in old4} == {'SRE dashboard', 'Infra dashboard'}, [title(p) for p in old4]
panels = [p for p in panels if p['gridData'].get('sectionId') != S4]
for src in io_links:
    p = json.loads(json.dumps(src))
    pid = str(uuid.uuid5(uuid.NAMESPACE_URL, 'mim-v5/dashboard-links/' + title(p)))
    p['panelIndex'] = pid
    p['gridData'] = dict(src['gridData'], i=pid, sectionId=S4)
    panels.append(p)

A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: ci.name fix in {len(done)} queries; section 4 = Dashboard Links ({len(io_links)} panels) from {IO}')
