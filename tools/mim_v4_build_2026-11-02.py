"""Build MIM V4 (2 Nov 2026): our last MIM V3 (through patch 29u, incl. the Telemetry control) plus the
"New collapsible section" a colleague added to an older copy (mim v3 updated.ndjson), kept at the bottom.

Usage: mim_v4_build_2026-11-02.py "MIM V3.ndjson" "mim v3 updated.ndjson" "MIM V4.ndjson"

Taken from the colleague's copy: that section, its 4 panels (CI and Assignment Group option-list controls,
"Total Incident Count by CI", "P1/P2 Incidents by Assignment Group"), the dashboard references of its controls,
the servicenow-incidents-* data view they point to, and the default time range (last 7 days: only the new
section's charts follow the time picker). Everything else is ours: the colleague's copy predates 29u, which
added the Telemetry control and the Application Health telemetry rows. MIM V4 gets its own id, so importing it
leaves MIM V3 in place.
"""
import json
import sys
import uuid

OURS, THEIRS, OUT = sys.argv[1:4]
V4_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, 'mim-dashboard/v4'))

ours = json.loads(open(OURS).readline())
theirs_lines = [json.loads(l) for l in open(THEIRS) if l.strip()]
theirs = next(o for o in theirs_lines if o.get('type') == 'dashboard')
data_views = [o for o in theirs_lines if o.get('type') == 'index-pattern']

OA, TA = ours['attributes'], theirs['attributes']
our_sections = {s['gridData']['i'] for s in OA['sections']}
new_sections = [s for s in TA['sections'] if s['gridData']['i'] not in our_sections]
assert [s['title'] for s in new_sections] == ['New collapsible section'], new_sections
new_ids = {s['gridData']['i'] for s in new_sections}

our_panels = json.loads(OA['panelsJSON'])
assert any(p['embeddableConfig'].get('title') == 'Telemetry' for p in our_panels), 'our copy lacks 29u'
add = [p for p in json.loads(TA['panelsJSON']) if p['gridData'].get('sectionId') in new_ids]
assert len(add) == 4, len(add)
assert not {p['panelIndex'] for p in add} & {p['panelIndex'] for p in our_panels}

sections = list(OA['sections'])
bottom = max(s['gridData']['y'] for s in sections) + 1
for s in new_sections:
    s = json.loads(json.dumps(s))
    s['gridData']['y'] = bottom
    sections.append(s)

add_ids = {p['panelIndex'] for p in add}
refs = [r for r in theirs.get('references', []) if r['name'].split(':')[0] in add_ids]
assert len(refs) == 2, refs
ref_ids = {r['id'] for r in refs}
data_views = [d for d in data_views if d['id'] in ref_ids]
assert len(data_views) == len(ref_ids)

v4 = json.loads(json.dumps(ours))
v4['id'] = V4_ID
A = v4['attributes']
A['title'] = 'MIM V4'
A['panelsJSON'] = json.dumps(our_panels + add, ensure_ascii=False)
A['sections'] = sections
A['timeFrom'], A['timeTo'] = TA['timeFrom'], TA['timeTo']
v4['references'] = list(ours.get('references', [])) + refs
for k in ('created_at', 'created_by', 'updated_at', 'updated_by', 'version'):
    v4.pop(k, None)

with open(OUT, 'w') as f:
    for o in data_views + [v4]:
        f.write(json.dumps(o, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: id {V4_ID}, {len(our_panels)} + {len(add)} panels, sections '
      + ' | '.join(s['title'] for s in sections))
