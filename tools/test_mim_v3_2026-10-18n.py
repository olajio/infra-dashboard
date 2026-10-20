"""Check the 18 Oct rearrangement: the seven health panels sit in section 3 right after the Upstream / Service health /
Downstream row (Middleware, Database, Server / APM Services, Process, Synthetics / Logs), then Business applications
impacted; "Applications on this CI" is now "APM Services Health"; SLO Error Burn Rate ends section 2 at full width.
Layout only, so no Elasticsearch is needed.

Usage: test_mim_v3_2026-10-18n.py MIM_V3_NDJSON
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


def section(n):
    return [(title(p), p['gridData']['x'], p['gridData']['w']) for p in
            sorted(panels, key=lambda p: (p['gridData']['y'], p['gridData']['x'])) if sec[p['gridData']['sectionId']].startswith(n)
            and p['type'] != 'esql_control']   # the section 3 control row (20 Oct) is checked by -20o


check('section 3 order and widths', section('3 ·'), [
    ('Application Health', 0, 26), ('Services of the Application', 26, 22),
    ('⬅ Upstream — what they depend on', 0, 16), ('Service health', 16, 14), ('Downstream — who is impacted ➡', 30, 18),
    ('Middleware Health', 0, 16), ('Database Health', 16, 16), ('Server Health', 32, 16),
    ('APM Services Health', 0, 16), ('Process Health', 16, 16), ('Synthetics Health', 32, 16),
    ('Errors from the Logs', 0, 48)])   # Business applications impacted removed on 20 Oct
s2 = section('2 ·')
check('section 2 keeps none of the moved panels', [t for t, *_ in s2 if t in (
    'Middleware Health', 'Database Health', 'Server Health', 'APM Services Health', 'Process Health', 'Synthetics Health',
    'Errors from the Logs')], [])
check('section 2 ends with the related-CI views (SLO Error Burn Rate removed on 20 Oct)', [t for t, *_ in s2[-2:]],
      ['Server View', 'Other related CIs'])
check('old name gone everywhere', 'Applications on this CI' in json.dumps(panels), False)
check('no two panels overlap', [
    (title(a), title(b)) for i, a in enumerate(panels) for b in panels[i + 1:]
    if a['gridData']['sectionId'] == b['gridData']['sectionId']
    and a['gridData']['x'] < b['gridData']['x'] + b['gridData']['w'] and b['gridData']['x'] < a['gridData']['x'] + a['gridData']['w']
    and a['gridData']['y'] < b['gridData']['y'] + b['gridData']['h'] and b['gridData']['y'] < a['gridData']['y'] + a['gridData']['h']], [])

print('\n' + ('ALL CHECKS PASSED' if not fails else f'FAILED: {fails}'))
sys.exit(1 if fails else 0)
