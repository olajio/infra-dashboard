"""Infrastructure Overview v2, patch 17a (17 Nov 2026): Dashboard Links as in related_links.png, and Future Releases.

Usage: infra_overview_v2_patch_2026-11-17a.py infra_overview_2.ndjson "Infrastructure Overview v2.ndjson"

Basis: the team's infra_overview_2.ndjson (id 00dde42d-…, "Infrastructure Overview v2"); everything outside section 2
is kept as the team left it.
- "🔗 2 · Dashboard Links": two subsections, each a heading over one row of link tiles (the look of related_links.png):
  Related Dashboards: Executive (in progress, no link yet), Portfolio, Applications Operations, Major Incident
  Management. Detailed Dashboards: Cloud Infra, Database Infra, Middleware, Server Infra, VMware Infra. Then Data
  freshness, as before.
- New "🚀 3 · Future Releases" at the bottom: Next Release Roadmap and Predictive & AI Insights cards (the look of
  next_release.png), with the items that apply to this dashboard.
"""
import json
import sys
import uuid

SRC, OUT = sys.argv[1:3]
lines = [l for l in open(SRC) if l.strip()]
dash = json.loads(lines[0])
assert dash.get('type') == 'dashboard'
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
sections = A['sections']
S2 = next(s['gridData']['i'] for s in sections if 'Dashboard Links' in s['title'])
OV = lambda name: str(uuid.uuid5(uuid.NAMESPACE_URL, 'infra-overview/v2/' + name))
S3 = OV('section-future-releases')
assert all(s['gridData']['i'] != S3 for s in sections), 'already patched?'

URL = {
    'Portfolio': 'https://kibana-prod.gcp.cna.com/app/dashboards#/view/7511c5d1-3326-4c7e-91f4-6c8fdb686ee0',
    'Applications': 'https://kibana-prod.gcp.cna.com/app/r/s/I3R7D', 'MIM': 'https://kibana-prod.gcp.cna.com/app/r/s/ZSMtk',
    'Cloud': 'https://kibana-prod.gcp.cna.com/app/r/s/MDJ9f', 'Database': 'https://kibana-prod.gcp.cna.com/app/r/s/w6zL4',
    'Middleware': 'https://kibana-prod.gcp.cna.com/app/r/s/jwCRg', 'Server': 'https://kibana-prod.gcp.cna.com/app/r/s/qJk5u',
    'VMware': 'https://kibana-prod.gcp.cna.com/app/r/s/t4oxr'}


def md(name, content, section, x, y, w, h):
    pid = OV('panel/' + name)
    return {'type': 'markdown', 'panelIndex': pid, 'gridData': {'x': x, 'y': y, 'w': w, 'h': h, 'i': pid, 'sectionId': section},
            'embeddableConfig': {'title': name, 'hide_title': True, 'content': content,
                                 'settings': {'open_links_in_new_tab': True}}}


# ---- section 2: drop the old headings and link tiles, keep Data freshness ----
fresh = next(p for p in panels if p['gridData'].get('sectionId') == S2 and
             (p['embeddableConfig'].get('title') or (p['embeddableConfig'].get('savedVis') or {}).get('title')) == 'Data freshness')
removed = [p for p in panels if p['gridData'].get('sectionId') == S2 and p is not fresh]
assert all(p['type'] == 'markdown' for p in removed), [p['type'] for p in removed]
panels = [p for p in panels if p not in removed]

RELATED = [('Executive', None, 'Executive Dashboard (In Progress)', None),
           ('Portfolio', '📊', 'Portfolio Dashboard', URL['Portfolio']),
           ('Applications Operations', '🛡️', 'Applications Operations Dashboard', URL['Applications']),
           ('Major Incident Management', '🚨', 'Major Incident Management', URL['MIM'])]
DETAILED = [('Cloud Infra', '☁️', 'Cloud Infra Dashboard', URL['Cloud'], 10),
            ('Database Infra', '🗄️', 'Database Infra Dashboard', URL['Database'], 10),
            ('Middleware', '⚙️', 'Middleware Dashboard', URL['Middleware'], 9),
            ('Server Infra', '🖥️', 'Server Infra Dashboard', URL['Server'], 10),
            ('VMware Infra', '🧱', 'VMware Infra Dashboard', URL['VMware'], 9)]
new = [md('Related Dashboards heading', '**↗ Related Dashboards**', S2, 0, 0, 48, 2)]
for k, (key, icon, label, url) in enumerate(RELATED):
    content = f'#### {icon} [{label} ›]({url})' if url else f'**{label}**'
    new.append(md(f'{key} link', content, S2, k * 12, 2, 12, 2))
new.append(md('Detailed Dashboards heading', '**↗ Detailed Dashboards**', S2, 0, 4, 48, 2))
x = 0
for key, icon, label, url, w in DETAILED:
    new.append(md(f'{key} link', f'#### {icon} [{label} ›]({url})', S2, x, 6, w, 2))
    x += w
assert x == 48
fresh['gridData'].update({'x': 0, 'y': 8, 'w': 48})

# ---- section 3: Future Releases ----
ROADMAP = """## 🚀 Next Release Roadmap

> **Coming Soon**

Wider infrastructure coverage on this page, so every domain tile shows full health.

#### What's on the way?

✅ VMware: every vCenter in vSphere (4 of 549 ESX hosts collected today)
✅ Network dashboard: switches, routers, firewalls and UPSs
✅ Database: Oracle and Db2 health per server; Cloud SQL matched to the CMDB
✅ ServiceNow: CI class on every change, for change counts by domain
✅ User impact (ServiceNow user base, RUM) and custom integration health

---

📢 **Stay tuned! These infrastructure features will be available in upcoming dashboard releases.**"""
AI = """## 🚀 Predictive & AI Insights

> **Coming Soon**

Unlock the next generation of infrastructure analytics with **Predictive Intelligence** and **AI-Powered Insights**.

#### What's on the way?

✅ Disk-full forecasting for servers and VMware datastores
✅ Anomaly detection on server CPU and memory, and VMware host latency
✅ Alert noise reduction: noisiest CIs and correlated alerts
✅ Change-risk insights: failed changes linked to the incidents that follow
✅ Capacity trends for GKE clusters and VMware datastores

---

📢 **Stay tuned! These advanced KPIs and insights will be available shortly.**"""
new.append(md('Next Release Roadmap', ROADMAP, S3, 0, 0, 24, 16))
new.append(md('Predictive & AI Insights', AI, S3, 24, 0, 24, 16))
panels += new
sections.append({'collapsed': False, 'gridData': {'i': S3, 'y': max(s['gridData']['y'] for s in sections) + 1},
                 'title': '🚀 3 · Future Releases'})

ids = [p['panelIndex'] for p in panels]
assert len(ids) == len(set(ids))
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: {len(removed)} old link panels replaced by {len(new) - 2} links and headings, Future Releases added; '
      f'{len(panels)} panels, id {dash["id"]}')
