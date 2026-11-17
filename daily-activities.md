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

3. Ran O1–O3 (`outage_results.txt`):
   - **No ServiceNow Outage records in Elastic** (no outage index; the outage-like fields belong to change requests).
     Using the Outage Duration needs the ServiceNow team to add the Outage table to the integration.
   - **The open-incident snapshots give the became-P1 time** to within a few minutes (the whole open-incident list is
     captured about every 5 minutes, kept back to 11 Aug). Last P1, INC2692216: opened 12 Nov 18:29, became P1 at
     20:12 (P3 → P2 → P1), resolved 13 Nov about 23:00: MTTR about 26.8 h from becoming P1, against a duration of
     28.5 h from opening.
   - Found an unexplored index, `servicenow-incident-timelines` (10.3 M records), that may log priority changes with
     exact times: check O4 added.
4. Ran O4 (`timeline_results.txt`): the timeline index holds incident records with priority, state, `updated_at`,
   a major-incident flag, the parent incident and `resolution_time` (seconds from opened to resolved, checked against
   the dates). The search matched about 2,500 child incidents linked to the P1 INC2692216 rather than the P1 itself,
   so check O5 was added to look at the P1's own records and whether each priority change is kept.
5. Ran O5 (`timeline_results2.txt`): **the timeline keeps every update with its priority and state**, so it gives the
   exact time an incident became a P1. INC2692216: opened 18:29:32 as P3, P2 at 18:48, **P1 at 20:10:13**, resolved
   13 Nov 22:59:10: **MTTR 26.8 h** from becoming P1, duration 28.5 h from opening. The snapshot estimate (20:12) was
   2 minutes out. `resolution_time` (opened to resolved, in seconds) is also on the incident records the dashboard
   already reads. About 8–9 timeline records per incident (32,518 for 3,740 incidents in 7 days).
6. Restated the recommendations; approved, with Linked incidents and On Hold P1s added. Built them on MIM V5:
   - **P1 MTTR** from the time the incident became a P1 (from the incident timeline), to resolved or now.
   - **P2 Duration** from opened to resolved (`resolution_time`) or now.
   - *Active Incidents*: new columns **Time as P1 / Duration (h)** and **Linked incidents** (incidents whose parent is
     this one); **On Hold P1s now shown**, and counted by the tiles. The table no longer reads the SLA records.
   - *Time to Resolve vs Target*: the P1 line is now MTTR from becoming a P1; the panel reads 30 days.
   - Test with hand-worked cases (escalated P3 → P2 → P1, opened as P1, On Hold P1, child incidents, mismatched field
     types between the two indices). Updated the user manual and seven KPI sheet rows (122, 123, 126–128, 130, 132).

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
