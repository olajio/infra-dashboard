"""Check the 20 Oct changes: Server, Health window, Service and Application are the first row of section 3 (grid
esql_control panels, same variables and defaults); Incident and CI stay pinned; Users impacted is two "In progress"
tiles (User base · ServiceNow, Real users · RUM) in its old place, without the demo number. Layout only, so no
Elasticsearch is needed.

Usage: test_mim_v3_2026-10-20o.py MIM_V3_NDJSON
"""
import json
import sys

dash = json.loads(open(sys.argv[1]).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
sec = {s['gridData']['i']: s['title'] for s in A['sections']}
fails = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" + ('' if ok else f'\n          expected {want!r}'))
    if not ok:
        fails.append(name)


pinned = sorted(A['pinned_panels']['panels'].values(), key=lambda c: c['order'])
check('pinned controls', [(c['config']['title'], c['config']['variable_name']) for c in pinned],
      [('Incident', 'incident'), ('CI', 'ci')])
s3 = sorted((p for p in panels if sec[p['gridData']['sectionId']].startswith('3 ·')),
            key=lambda p: (p['gridData']['y'], p['gridData']['x']))
row = [(p['type'], p['embeddableConfig']['title'], p['embeddableConfig']['variable_name'], p['gridData']['y'],
        p['gridData']['x'], p['gridData']['w']) for p in s3[:4]]
check('section 3 starts with the four controls', row, [
    ('esql_control', 'Server', 'server', 0, 0, 12), ('esql_control', 'Health window', 'health_window', 0, 12, 8),
    ('esql_control', 'Service', 'service', 0, 20, 14), ('esql_control', 'Application', 'application', 0, 34, 14)])
check('control defaults kept', [p['embeddableConfig']['selected_options'] for p in s3[:4]],
      [['(no server selected)'], ['24 hours'], ['(services on this CI)'], ['(all applications)']])
check('section 3 panels start below the controls', min(p['gridData']['y'] for p in s3[4:]), 3)
check('no control left anywhere else', [title(p) for p in panels if p['type'] == 'esql_control'
                                        and not sec[p['gridData']['sectionId']].startswith('3 ·')], [])

tiles = {title(p): p for p in panels if title(p) in ('User base · ServiceNow', 'Real users · RUM')}
check('Users impacted replaced by two tiles', ('Users impacted' in [title(p) for p in panels], sorted(tiles)),
      (False, ['Real users · RUM', 'User base · ServiceNow']))
check('tiles stacked in the old place', sorted((p['gridData']['x'], p['gridData']['y'], p['gridData']['w'], p['gridData']['h'])
                                               for p in tiles.values()), [(14, 0, 10, 5), (14, 5, 10, 5)])
vals = [json.loads(p['embeddableConfig']['savedVis']['params']['spec'])['data'][0]['values'][0] for p in tiles.values()]
check('both say In progress, no demo number', ([v['value'] for v in vals], '2,500' in json.dumps(vals)),
      (['In progress', 'In progress'], False))
check('distinct panel ids', len({p['panelIndex'] for p in panels}), len(panels))
S3_VARS = ('?server', '?health_window', '?service', '?application')
check('no panel outside section 3 uses a section 3 control (they load only when section 3 comes into view)',
      [title(p) for p in panels if p['type'] != 'esql_control' and not sec[p['gridData']['sectionId']].startswith('3 ·')
       and any(v in json.dumps(p['embeddableConfig']) for v in S3_VARS)], [])

check('SLO Error Burn Rate and Business applications impacted removed (20q)',
      [t for t in ('SLO Error Burn Rate', 'Business applications impacted') if t in [title(p) for p in panels]], [])

print('\n' + ('ALL CHECKS PASSED' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
