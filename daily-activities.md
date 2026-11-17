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

**MIM SLA / MTTR (email thread with James Patock and Dan Tautges)**
1. Reviewed the thread (`MIM SLA update.docx`). James proposed using **MTTR for P1s** (from the ServiceNow Outage
   record's Duration, from when the incident became P1 until resolved) and **Duration for all other priorities**
   (Opened to Resolved), instead of the ServiceNow SLAs.
2. Mapped it to the data: P2 duration can be built from what is already in Elastic; the P1 Outage Duration needs a
   check that Outage records reach Elastic (queries O1–O3 in `queries_to_run.md`).

**Capability Tracker**
1. Reviewed `Capability Tracker.xlsx`: 85 Elastic observability capabilities (CAP-001 to CAP-085) with category, AI
   type, description, metric, target, version status, priority, owner and notes.
2. Added 20 capabilities (CAP-086 to CAP-105) from the dashboard work: ServiceNow ITSM sync, MIM command view, P1
   MTTR from Outage records, incident duration trend, SLA tracking, change-to-incident correlation, Netcool bridge,
   alert noise reduction, unattended alerts, data feed freshness, domain status landing page, impact mapping, F5,
   Palo Alto, storage and backup, certificate expiry, Windows services, mainframe, executive reporting, and AI incident
   summaries.

**Open from today**
- Run O1–O3 (`queries_to_run.md`) to see whether the ServiceNow Outage records, or the time an incident became P1,
  are available in Elastic.
- Agree with James and Dan on the approach (P1 MTTR from Outage records, Duration for P2), then build it on MIM V5.
