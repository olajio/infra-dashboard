"""Check Infrastructure Overview v2 patch 18b and MIM V5 patch 18c (structure only, no Elasticsearch needed).

Usage: test_future_releases_2026-11-18.py "Infrastructure Overview v2.ndjson" "MIM V5.ndjson"
"""
import json
import sys

fails = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" + ('' if ok else f'\n          expected {want!r}'))
    if not ok:
        fails.append(name)


load = lambda f: json.loads([l for l in open(f) if l.strip()][0])['attributes']
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
io, mim = load(sys.argv[1]), load(sys.argv[2])
iop = json.loads(io['panelsJSON'])
check('IO: no panel says "partial"', [title(p) for p in iop if 'partial' in json.dumps(p).lower()], [])
spec = next(p for p in iop if title(p) == 'Domain status')['embeddableConfig']['savedVis']['params']['spec']
check('IO: source tags kept', ("'GKE'" in spec, "'vSphere'" in spec), (True, True))
rm = next(p for p in iop if title(p) == 'Next Release Roadmap')['embeddableConfig']['content']
check('IO roadmap: why Database / Middleware / VMware were partial',
      ('Database: health metrics in the Database tile' in rm, 'Middleware: health metrics in the Middleware tile' in rm,
       '4 of 549 ESX hosts' in rm and 'ballooning' in rm), (True, True, True))

secs = sorted(mim['sections'], key=lambda s: s['gridData']['y'])
check('MIM: Future Releases is the last section', secs[-1]['title'], '🚀 5 · Future Releases')
mp = json.loads(mim['panelsJSON'])
fr = sorted((p['gridData']['x'], title(p)) for p in mp if p['gridData'].get('sectionId') == secs[-1]['gridData']['i'])
check('MIM: the two cards side by side', fr, [(0, 'Next Release Roadmap'), (24, 'Predictive & AI Insights')])
cards = {title(p): p for p in mp if p['gridData'].get('sectionId') == secs[-1]['gridData']['i']}
check('MIM: same look as the Infrastructure Overview cards',
      all(c['type'] == 'markdown' and c['embeddableConfig']['content'].startswith('## 🚀 ') and
          '> **Coming Soon**' in c['embeddableConfig']['content'] and c['gridData']['w'] == 24 for c in cards.values()), True)
ids = [p['panelIndex'] for p in mp]
check('MIM: panel ids unique', len(ids), len(set(ids)))
print('FAILED: ' + ', '.join(fails) if fails else 'all passed')
sys.exit(1 if fails else 0)
