"""MIM V5 patch 19g (19 Nov 2026): the Vega panels stay aligned after the browser zoom changes.

Usage: mim_v5_patch_2026-11-19g.py "MIM V5.ndjson" "MIM V5.ndjson"

Why: Kibana draws Vega panels on a canvas by default. Vega sets the canvas's CSS width and height only when the
browser's device pixel ratio is not 1. Zooming the browser out (say to 75%) sets them to the larger zoomed-out size.
Back at 100% the ratio is 1, so that old size stays on the canvas. The canvas is then wider than its panel: the text is
stretched and out of line and a scrollbar appears. Zooming in and back happened to overwrite it.

Fix, in each of the 9 Vega specs (nothing else changes):
- `config.kibana.renderer: "svg"`: an SVG has no such fixed CSS size and follows the panel.
- `autosize` `contains: "content"` with `padding` bottom -4 (was `contains: "padding"`, padding 0): an SVG sits on the
  text baseline and leaves a 3 px gap under it, which would overflow the panel and show a scrollbar. The SVG is now
  4 px shorter than the panel; the layout inside is unchanged (the bottom 4 px are cut off, empty in every panel).
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
OLD_AUTO = '"autosize": {\n    "type": "fit",\n    "contains": "padding"\n  }'
NEW_AUTO = '"autosize": {\n    "type": "fit",\n    "contains": "content"\n  }'
OLD_PAD, NEW_PAD = '\n  "padding": 0,\n', '\n  "padding": {"top": 0, "left": 0, "right": 0, "bottom": -4},\n'
CONFIG = {'kibana': {'renderer': 'svg'}}
PADDING = {'top': 0, 'left': 0, 'right': 0, 'bottom': -4}

dash = json.loads([l for l in open(SRC) if l.strip()][0])
panels = json.loads(dash['attributes']['panelsJSON'])
n = 0
for p in panels:
    sv = p['embeddableConfig'].get('savedVis')
    if not sv or sv.get('type') != 'vega':
        continue
    raw, t = sv['params']['spec'], sv.get('title')
    spec = json.loads(raw)
    assert 'config' not in spec and spec['padding'] == 0 and spec['autosize'] == {'type': 'fit', 'contains': 'padding'}, t
    assert raw.startswith('{\n') and raw.count(OLD_AUTO) == 1 and raw.count(OLD_PAD) == 1, t
    # text edits, so the rest of each spec stays byte for byte as it was
    new = '{\n  "config": {"kibana": {"renderer": "svg"}},\n' + raw[2:]
    new = new.replace(OLD_AUTO, NEW_AUTO).replace(OLD_PAD, NEW_PAD)
    want = {**spec, 'config': CONFIG, 'padding': PADDING, 'autosize': {'type': 'fit', 'contains': 'content'}}
    assert json.loads(new) == want, t
    sv['params']['spec'] = new
    n += 1
assert n == 9, n
dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: {n} Vega panels drawn as SVG, 4 px shorter than the panel')
