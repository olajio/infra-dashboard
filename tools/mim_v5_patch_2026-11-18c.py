"""MIM V5 patch 18c (18 Nov 2026), on top of 18b: a "Future Releases" section, as on the Infrastructure Overview.

Usage: mim_v5_patch_2026-11-18c.py "MIM V5.ndjson" "MIM V5.ndjson"

New last section "🚀 5 · Future Releases" with the Next Release Roadmap and Predictive & AI Insights cards (the same
look as the Infrastructure Overview's). The items are the gaps found while building MIM:
- Next Release Roadmap (data and integrations): user impact (ServiceNow user base, RUM: the two "In progress"
  tiles), MTTR with the MIM team's Outage record adjustments (Outage table not synced), clickable alerts (Netcool Web
  GUI needs the ObjectServer name), PBA / business-critical flag (no such field in ServiceNow data), telemetry for
  the enrolled applications with none yet, a stable cmdb_with_apm_flag schema (its new text fields broke the
  application panels on 17-18 Nov), Linked incidents beyond 7 days.
- Predictive & AI Insights: AI incident summary, change-to-incident correlation, alert correlation and noise
  reduction, MTTR / breach risk forecasting, anomaly detection on the CI before the incident, blast radius.
"""
import json
import sys
import uuid

SRC, OUT = sys.argv[1:3]
dash = json.loads([l for l in open(SRC) if l.strip()][0])
A = dash['attributes']
panels = json.loads(A['panelsJSON'])
ID = lambda name: str(uuid.uuid5(uuid.NAMESPACE_URL, 'mim-v5/future-releases/' + name))
S5 = ID('section')
assert all(s['gridData']['i'] != S5 for s in A['sections']), 'already patched'
A['sections'].append({'collapsed': False, 'gridData': {'i': S5, 'y': max(s['gridData']['y'] for s in A['sections']) + 1},
                      'title': '🚀 5 · Future Releases'})

ROADMAP = """## 🚀 Next Release Roadmap

> **Coming Soon**

More complete incident data on this page, from the integrations MIM depends on.

#### What's on the way?

✅ User impact: users affected from the ServiceNow user base, and real users from RUM (the two *In progress* tiles)
✅ P1 MTTR with the MIM team's adjustments, from the ServiceNow Outage record (needs the Outage table in the integration)
✅ Clickable alerts: open an alert in Discover or the Netcool Web GUI (waiting for the Netcool server name)
✅ Business-critical (PBA) flag on incidents, once ServiceNow sends it
✅ Application health for every monitored application (some are enrolled with no APM data yet)
✅ A stable schema for the CMDB application list (`cmdb_with_apm_flag`), so new fields do not break the application panels
✅ Linked incidents over the whole life of a P1 (today: those updated in the last 7 days)

---

📢 **Stay tuned! These features will be available in upcoming dashboard releases.**"""

AI = """## 🚀 Predictive & AI Insights

> **Coming Soon**

Unlock the next generation of incident analytics with **Predictive Intelligence** and **AI-Powered Insights**.

#### What's on the way?

✅ AI incident summary: timeline, affected CIs and likely cause, ready for the bridge call
✅ Change-to-incident correlation: changes on the CI just before the incident, flagged as a likely cause
✅ Alert correlation: related alerts grouped under one incident, less noise for the MIM team
✅ Breach risk: P1s and P2s likely to miss their target, from their age and similar past incidents
✅ Anomaly detection on the CI's metrics in the hours before an incident
✅ Blast radius: services and users likely to be affected, from the CMDB and APM dependencies

---

📢 **Stay tuned! These advanced KPIs and insights will be available shortly.**"""

for name, content, x in (('Next Release Roadmap', ROADMAP, 0), ('Predictive & AI Insights', AI, 24)):
    pid = ID(name)
    panels.append({'type': 'markdown', 'panelIndex': pid,
                   'gridData': {'x': x, 'y': 0, 'w': 24, 'h': 22, 'i': pid, 'sectionId': S5},
                   'embeddableConfig': {'title': name, 'hide_title': True, 'content': content,
                                        'settings': {'open_links_in_new_tab': True}}})
A['panelsJSON'] = json.dumps(panels, ensure_ascii=False)
open(OUT, 'w').write(json.dumps(dash, ensure_ascii=False, separators=(',', ':')) + '\n')
print(f'{OUT}: section 5 Future Releases added')
