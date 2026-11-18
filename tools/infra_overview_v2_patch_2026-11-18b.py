"""Infrastructure Overview v2, patch 18b (18 Nov 2026): no "partial" tags; their reasons go to Future Releases.

Usage: infra_overview_v2_patch_2026-11-18b.py "Infrastructure Overview v2.ndjson" "Infrastructure Overview v2.ndjson"

The Domain status tiles tagged Database and Middleware "partial" and VMware "vSphere · partial". The tags are removed
(VMware keeps "vSphere" and Cloud "GKE", which name the source). Why they were partial now reads in the Next Release
Roadmap card (wider coverage, not AI, so not Predictive & AI Insights):
- Database: status from incidents and alerts only; Oracle and Db2 health per server and Cloud SQL matched to the CMDB
  to come.
- Middleware: status from incidents and alerts only; middleware health metrics to come.
- VMware: vSphere covers 4 of 549 ESX hosts; CPU ready time, ballooning, swapping and packet loss not collected.
"""
import json
import sys

SRC, OUT = sys.argv[1:3]
lines = [l for l in open(SRC) if l.strip()]
dash = json.loads(lines[0])
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
title = lambda p: p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')
P = {title(p): p for p in panels}

OLD_TAG = ("datum.d == 'Database' ? 'partial' : datum.d == 'Middleware' ? 'partial' : datum.d == 'Cloud' ? 'GKE' : "
           "datum.d == 'VMware' ? 'vSphere · partial' : ''")
NEW_TAG = "datum.d == 'Cloud' ? 'GKE' : datum.d == 'VMware' ? 'vSphere' : ''"
ec = P['Domain status']['embeddableConfig']
spec = ec['savedVis']['params']['spec']
assert spec.count(OLD_TAG) == 1, 'already patched?'
ec['savedVis']['params']['spec'] = spec.replace(OLD_TAG, NEW_TAG)
assert 'partial' not in ec['savedVis']['params']['spec'].lower()

OLD_ITEMS = """✅ VMware: every vCenter in vSphere (4 of 549 ESX hosts collected today)
✅ Network dashboard: switches, routers, firewalls and UPSs
✅ Database: Oracle and Db2 health per server; Cloud SQL matched to the CMDB
"""
NEW_ITEMS = """✅ VMware: every vCenter in vSphere (4 of 549 ESX hosts collected today), plus CPU ready time, ballooning, swapping and packet loss
✅ Database: health metrics in the Database tile (today it reflects incidents and alerts only): Oracle and Db2 per server, Cloud SQL matched to the CMDB
✅ Middleware: health metrics in the Middleware tile (today it reflects incidents and alerts only)
✅ Network dashboard: switches, routers, firewalls and UPSs
"""
rm = P['Next Release Roadmap']['embeddableConfig']
assert rm['content'].count(OLD_ITEMS) == 1
rm['content'] = rm['content'].replace(OLD_ITEMS, NEW_ITEMS)
for t in ('Next Release Roadmap', 'Predictive & AI Insights'):
    P[t]['gridData']['h'] = 18
assert not any('partial' in json.dumps(p).lower() for p in panels), [title(p) for p in panels if 'partial' in json.dumps(p).lower()]
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
lines[0] = json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n'
open(OUT, 'w').write(''.join(l if l.endswith('\n') else l + '\n' for l in lines))
print(f'{OUT}: "partial" tags removed; reasons in Next Release Roadmap')
