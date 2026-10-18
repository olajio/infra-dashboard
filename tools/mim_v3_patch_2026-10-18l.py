"""MIM V3: note in Errors from the Logs that a 3- or 7-day Health window can load slowly the first time (18 Oct 2026,
after Round 11d: 4 s once the data is warm; a first read of 7 days of logs from disk can take over 30 s).

Usage: mim_v3_patch_2026-10-18l.py "MIM V3.ndjson" "MIM V3.ndjson"   (run once, after mim_v3_patch_2026-10-18k.py)
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
NOTE = (' At 3 or 7 days the first load can take up to a minute, while older logs are read from disk; later loads take '
        'a few seconds.')

dash = json.loads(open(SRC).readline())
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
p = next(p for p in panels if title(p) == 'Errors from the Logs')
ec = p['embeddableConfig']
assert NOTE not in ec['description'], 'already applied'
ec['description'] = ec['description'].rstrip() + NOTE

A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print('Errors from the Logs description:', ec['description'][-160:])
