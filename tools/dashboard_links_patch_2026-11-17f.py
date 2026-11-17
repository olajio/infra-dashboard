"""Dashboard Links patch 17f (17 Nov 2026): the Server Infra, Middleware and Applications Operations links use the
short links in links.txt, on Infrastructure Overview v2 and MIM V5 (whose Dashboard Links section is a copy).

Usage: dashboard_links_patch_2026-11-17f.py "Infrastructure Overview v2.ndjson" "MIM V5.ndjson"   (edits both in place)

Before: qJk5u / jwCRg / I3R7D (respective_detailed_dashboards.txt). After: SeAtm / DF70u / b4Jas (links.txt, team
decision 17 Nov). Each old link must appear exactly once in each dashboard (its Dashboard Links tile).
"""
import json
import sys

R = 'https://kibana-prod.gcp.cna.com/app/r/s/'
SWAP = {'Server Infra': (R + 'qJk5u', R + 'SeAtm'), 'Middleware': (R + 'jwCRg', R + 'DF70u'),
        'Applications Operations': (R + 'I3R7D', R + 'b4Jas')}
for path in sys.argv[1:]:
    lines = [l for l in open(path) if l.strip()]
    dash = json.loads(lines[0])
    panels = json.loads(dash['attributes']['panelsJSON'])
    for name, (old, new) in SWAP.items():
        hits = [p for p in panels if old + ')' in p['embeddableConfig'].get('content', '')]
        assert len(hits) == 1 and hits[0]['embeddableConfig']['title'] == f'{name} link', (path, name, len(hits))
        hits[0]['embeddableConfig']['content'] = hits[0]['embeddableConfig']['content'].replace(old + ')', new + ')')
    dash['attributes']['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
    assert not any(old in dash['attributes']['panelsJSON'] for old, _ in SWAP.values()), path
    lines[0] = json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n'
    open(path, 'w').write(''.join(l if l.endswith('\n') else l + '\n' for l in lines))
    print(f'{path}: Server Infra, Middleware and Applications Operations links from links.txt')
