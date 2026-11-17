# Daily activities

## 17 Nov 2026

**MIM V5**
1. Removed P3 incidents from the dashboard entirely, leaving P1 and P2. P2s still appear once they're past their 8 h
   target. This covered the tiles, *Needs attention now*, *Active Incidents*, *Escalation Channel*, the Incident and CI
   dropdowns, and the time-to-resolve chart.
2. Narrowed the *Active Incidents* table by about 25 % and widened the *P1 / P2 Time to Resolve vs Target* chart to fill
   the space.
3. Reviewed the zigzag in the P3 line on the time-to-resolve chart. Each point was the median of only the incidents
   resolved that day, so values jumped from day to day. Switched the chart to a **rolling 7-day median**: each point now
   covers the incidents resolved in the 7 days up to that day, so a single slow day no longer makes the line jump.
4. Ran the follow-up ServiceNow checks:
   - **PBA:** no PBA field exists in the data.
   - **Duration fields:** not on the incident records. R4e/R4f found them in the ServiceNow SLA records
     (`servicenow-task-sla`): `duration` and `business_duration` are how long each SLA has been running, per SLA
     contract, for incidents and service requests alike. So the "duration calculated in ServiceNow" is the SLA clock,
     not a field on the incident.
5. Updated the MIM V5 user manual and the MIM KPI spreadsheet (seven rows for the P3 removal, two for the rolling
   median).

**Infrastructure Overview**
1. Adopted the team's updated version (*Infrastructure Overview v2*) as the new basis.
2. Rebuilt the Dashboard Links section into two subsections:
   - **Related Dashboards:** Executive (in progress), Portfolio, Applications Operations, Major Incident Management.
   - **Detailed Dashboards:** Cloud Infra, Database Infra, Middleware, Server Infra, VMware Infra.
3. Added a Future Releases section with *Next Release Roadmap* and *Predictive & AI Insights* cards, listing the planned
   infrastructure items.
4. Updated the user manual.

**MIM P1 MTTR and P2 Duration (email thread with James Patock and Dan Tautges)**
1. Reviewed the thread (`MIM SLA update.docx`). James proposed reporting **MTTR for P1s** (from when the incident
   became a P1 until resolved, as in the ServiceNow Outage record) and **Duration for other priorities** (opened to
   resolved), instead of the ServiceNow SLAs.
2. Ran data checks O1–O5 to find where that information is in Elastic (results in `outage_results.txt`,
   `timeline_results.txt` and `timeline_results2.txt`):
   - **Outage records are not in Elastic.** Using them would need the ServiceNow team to add the Outage table to the
     integration.
   - **The incident timeline (`servicenow-incident-timelines`) keeps every update with its priority,** so it gives the
     exact time an incident became a P1. The open-incident snapshots give the same time to within a few minutes, as a
     fallback.
   - **`resolution_time`** (opened to resolved, in seconds) is on the incident records, ready to use for Duration.
   - Example, the last P1 (INC2692216, Email/Exchange): opened 12 Nov 18:29 as a P3, P2 at 18:48, **P1 at 20:10**,
     resolved 13 Nov 22:59. **MTTR 26.8 h**, Duration 28.5 h. About 2,500 child incidents were linked to it.
3. Recommended the approach; it was approved, with *Linked incidents* and On Hold P1s added.
4. Built it on MIM V5:
   - **P1 MTTR:** from when the incident became a P1 to resolved, or to now while open.
   - **P2 Duration:** from opened to resolved, or to now while open.
   - *Active Incidents*: new columns **Time as P1 / Duration (h)** and **Linked incidents** (incidents whose parent is
     this one); **On Hold P1s are now shown** and counted by the tiles; sorted longest first.
   - *Time to Resolve vs Target*: the P1 line is MTTR from becoming a P1, the P2 line is Duration; reads 30 days.
   - Fixed two tile descriptions that still mentioned P3.
5. Tested with hand-worked cases (an incident escalated P3 → P2 → P1, one opened as a P1, an On Hold P1, child
   incidents, and fields stored as different types in the two indices). Updated the MIM V5 user manual and seven rows
   of the KPI sheet (122, 123, 126–128, 130, 132).

**Capability Tracker**
1. Reviewed `Capability Tracker.xlsx`: 85 Elastic observability capabilities (CAP-001 to CAP-085) with category, AI
   type, description, metric, target, version status, priority, owner and notes.
2. Added 20 capabilities (CAP-086 to CAP-105) from the dashboard work: ServiceNow ITSM sync, MIM command view, P1
   MTTR from Outage records, incident duration trend, SLA tracking, change-to-incident correlation, Netcool bridge,
   alert noise reduction, unattended alerts, data feed freshness, domain status landing page, impact mapping, F5,
   Palo Alto, storage and backup, certificate expiry, Windows services, mainframe, executive reporting, and AI incident
   summaries.

**Open from today**
- Only if James needs the MIM team's manual adjustments: ask the ServiceNow team to add the Outage table to the integration.
- Import the updated MIM V5 and check it on real data: the new Active Incidents columns, and the P1 line on Time to
  Resolve (INC2692216, resolved 13 Nov, counts as 26.8 h until the window passes it on 20 Nov).
