"""Check the eighth 16 Oct round: the four related-CI views sit in "Investigate the CI" right after Blast radius and
Applications that depend on this CI; the old section 3 is gone and the sections are renumbered.

Usage: test_mim_v3_2026-10-16h.py MIM_V3_NDJSON
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


check('sections', [s['title'] for s in A['sections']],
      ['1 · Major Incident Overview', '2 · Investigate the CI', '3 · Application & Service Health, Dependencies',
       '4 · Related dashboards'])
order = [title(p) for p in sorted(panels, key=lambda p: (p['gridData']['y'], p['gridData']['x']))
         if sec[p['gridData']['sectionId']] == '2 · Investigate the CI']
check('section 2 reading order', order[:9], [
    'Escalate', 'Alerts on this CI', 'Blast radius', 'Applications related to this CI',   # names since round i
    'Middleware View', 'Database View', 'Server View', 'Other related CIs', 'Middleware Health'])
check('no panel left in a removed section', [title(p) for p in panels if p['gridData']['sectionId'] not in sec], [])
check('no description names an old section number',
      [title(p) for p in panels if any(f'section {n}' in (p['embeddableConfig'].get('description') or '')
                                       for n in ('5',)) or 'views in section 3' in (p['embeddableConfig'].get('description') or '')], [])
print('\n' + ('ALL CHECKS PASSED' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
