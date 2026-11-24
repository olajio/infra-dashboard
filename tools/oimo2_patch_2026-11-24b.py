"""Observability Incident Management Operations 2, patch 24b: the Vega tiles and banners fit their panel at any browser
zoom.

Usage: oimo2_patch_2026-11-24b.py "Observability Incident Management Operations 2.ndjson" (in place)

Why: when Kibana (re)draws a Vega panel it sizes the drawing from the panel's size at that moment, and it ignores any
resize that happens while the drawing is being made. If the page layout is still changing then (page load, a zoom step,
the controls re-running the panels), the drawing keeps a wrong size until the next resize: taller or wider than the
panel (scrollbar, text outside the visible part: the banners of sections 1 and 3 lost all their text) or narrower
(the tile's text out of line with the other tiles). Vega's "fit" sizing also squeezed narrow tiles (at 200 % zoom the
Needs attention tile was laid out on 29 of its 113 px).

Fix, in the 8 Vega specs (the 6 tiles of the first row and the 2 banners); nothing else changes:
- the drawing takes its size from its own panel, not from Kibana: Vega's containerSize(), checked every half second
  and on window resize. Width w = the panel's width - 1 px; height h = the panel's height, at most the layout height of
  the tile (138 px for Active P1 / P2 / P3, 140 px for the other tiles, 60 px for the banners: what they used before,
  constant in CSS pixels at any zoom);
- the marks are laid out on w and h (instead of width and height) inside one group clipped to w by h - 4 px, and
  autosize "pad" (instead of "fit") with a padding that takes off what Kibana's size has in excess: the drawing is
  exactly w by h - 4 px, as before, whatever size Kibana gave it.
At a normal size the drawing is the same as before (checked pixel for pixel).
"""
import json
import re
import sys

SRC = OUT = sys.argv[1]
LAYOUT_H = {'Needs attention now': 140, 'Active P1': 138, 'Active P2': 138, 'Active P3': 138, 'User base · ServiceNow': 140,
            'Real users · RUM': 140, 'Start here': 60, 'Then pick a server, application and service': 60}
GRID_H = {140: 7, 138: 7, 60: 3}
EVENTS = [{'type': 'timer', 'throttle': 500}, {'source': 'window', 'type': 'resize'}]


def swap(expr):
    return re.sub(r'(?<![\w.])height\b', 'h', re.sub(r'(?<![\w.])width\b', 'w', expr))


def sub(x):
    if isinstance(x, dict):
        return {k: (swap(v) if k in ('signal', 'update') and isinstance(v, str) else sub(v)) for k, v in x.items()}
    return [sub(v) for v in x] if isinstance(x, list) else x


lines = [json.loads(l) for l in open(SRC) if l.strip()]
(dash,) = [o for o in lines if o.get('type') == 'dashboard']
panels = json.loads(dash['attributes']['panelsJSON'])
done = []
for p in panels:
    sv = p['embeddableConfig'].get('savedVis')
    if not sv or sv.get('type') != 'vega':
        continue
    t = sv['title']
    D = LAYOUT_H[t]
    assert p['gridData']['h'] == GRID_H[D], (t, p['gridData']['h'])
    spec = json.loads(sv['params']['spec'])
    assert spec['autosize'] == {'type': 'fit', 'contains': 'content'}, t
    assert spec['padding'] == {'top': 0, 'left': 0, 'right': 0, 'bottom': -4}, t
    assert not {'cw', 'ch', 'w', 'h'} & {s['name'] for s in spec.get('signals', [])}, t
    own = sub(spec.get('signals', []))
    spec['autosize'] = {'type': 'pad', 'contains': 'content'}
    spec['padding'] = {'signal': '{top: 0, left: 0, right: min(0, w - width), bottom: min(0, h - 4 - height)}'}
    spec['signals'] = [
        {'name': 'cw', 'init': 'containerSize()[0]', 'on': [{'events': EVENTS, 'update': 'containerSize()[0]'}]},
        {'name': 'ch', 'init': 'containerSize()[1]', 'on': [{'events': EVENTS, 'update': 'containerSize()[1]'}]},
        {'name': 'w', 'update': 'cw > 1 ? cw - 1 : width'},
        {'name': 'h', 'update': 'min(%d, ch > 4 ? ch : height)' % D}] + own
    spec['marks'] = [{'type': 'group', 'clip': True,
                      'encode': {'update': {'x': {'value': 0}, 'y': {'value': 0},
                                            'width': {'signal': 'w'}, 'height': {'signal': 'h - 4'}}},
                      'marks': sub(spec['marks'])}]
    left = re.findall(r'"(?:signal|update)": "[^"]*(?<![\w.])(?:height|width)\b', json.dumps([spec['marks'], own]))
    assert not left, (t, left)
    sv['params']['spec'] = json.dumps(spec, ensure_ascii=False, indent=2)
    done.append(f'{t} ({D} px)')
assert len(done) == len(LAYOUT_H), done
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
with open(OUT, 'w') as f:
    for o in lines:
        f.write(json.dumps(o, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: ' + '; '.join(done))
