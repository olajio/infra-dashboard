"""MIM V5 patch 17d (17 Nov 2026), on top of 17c: P1 and P2 shown regardless of age on every panel.

Usage: mim_v5_patch_2026-11-17d.py "MIM V5.ndjson" "MIM V5.ndjson"

Team decision: show every active P1 and P2, whatever their age (until now section 1 showed P2s only once they were
open longer than the 8 h target, while the Incident control and Escalation Channel already showed every active P2).
- Needs attention now: every active P1 and P2 (strip "P1 · P2").
- "P2 over 8 h" tile becomes "Active P2" (any age).
- "Active Incidents (P1 · P2 over 8 h)" becomes "Active Incidents (P1 · P2)": every active P1 and P2.
The On Hold rule is unchanged (On Hold P1s shown, On Hold P2s not, in section 1). The 8 h P2 target stays on the
Time to Resolve chart.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
AI_OLD, AI_NEW = 'Active Incidents (P1 · P2 over 8 h)', 'Active Incidents (P1 · P2)'
ON_HOLD = 'On Hold P1s count, On Hold P2s do not.'

dash = json.loads([l for l in open(SRC) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
done = set()


def sub(text, pairs, what):
    for a, b in pairs:
        assert a in text, (what, a)
        text = text.replace(a, b)
    return text


for p in panels:
    ec = p['embeddableConfig']
    t = ec.get('title')
    if t == 'Needs attention now':
        spec = json.loads(ec['savedVis']['params']['spec'])
        url = spec['data'][0]['url']
        url['query'] = sub(url['query'], [('pri == 2 AND age_minutes > 480, "p2"', 'pri == 2, "p2"')], t)
        s = sub(json.dumps(spec, ensure_ascii=False, indent=2),
                [('"P1 · P2 over 8 h"', '"P1 · P2"'), ("'P2 > 8 h'", "'P2'")], t)
        ec['savedVis']['params']['spec'] = s
        ec['description'] = ('Every active P1 and P2 incident, whatever its age, in one number. Green at 0. The strip '
                             'splits it by priority; the same incidents as the Active Incidents table. ' + ON_HOLD)
        done.add(t)
    elif t == 'P2 over 8 h':
        spec = json.loads(ec['savedVis']['params']['spec'])
        url = spec['data'][0]['url']
        url['query'] = sub(url['query'], [('WHERE pri == 2 AND age_minutes > 480', 'WHERE pri == 2')], t)
        s = sub(json.dumps(spec, ensure_ascii=False, indent=2),
                [('"value": "P2 over 8 h"', '"value": "Active P2"'),
                 ('"value": "open longer than the 8 h target"', '"value": "any age"')], t)
        ec['savedVis']['params']['spec'] = s
        ec['title'] = 'Active P2'
        ec['savedVis']['title'] = 'Active P2'
        ec['description'] = ('How many P2 incidents are active now, whatever their age. Same incidents as the matching '
                             'rows of Active Incidents. Active = priority 1 or 2 and the incident\'s latest record not '
                             'Resolved, Closed, Canceled or Cancelled; ' + ON_HOLD + ' Last 7 days (fixed); not narrowed '
                             'by the Incident or CI controls.')
        done.add(t)
    elif t == 'Active P1':
        ec['description'] = ec['description'].replace('Same incidents as the matching rows of Active Incidents.',
                                                      'Same incidents as the P1 rows of Active Incidents.')
        done.add(t)
    elif t == AI_OLD:
        st = ec['attributes']['state']
        q = sub(st['query']['esql'],
                [('| EVAL age_minutes = DATE_DIFF("minutes", opened, NOW()), target = CASE(pri == 1, 240, 480)\n'
                  '| WHERE pri == 1 OR age_minutes > target\n', '')], t)
        (layer,) = st['datasourceStates']['textBased']['layers'].values()
        layer['query'] = {'esql': q}
        st['query'] = {'esql': q}
        ec['title'] = AI_NEW
        ec['attributes']['title'] = AI_NEW
        ec['description'] = sub(ec['description'], [
            ('Every active P1 incident, and the active P2 incidents open longer than their 8 h target, P1 first, longest '
             'first.', 'Every active P1 and P2 incident, whatever its age, P1 first, longest first.')], t)
        done.add(t)
assert done == {'Needs attention now', 'P2 over 8 h', 'Active P1', AI_OLD}, done
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
assert 'over 8 h' not in dash['attributes']['panelsJSON'], 'a panel still says "over 8 h"'
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: P1 and P2 shown regardless of age')
