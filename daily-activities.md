# Daily activities

## 19 Nov 2026

**MIM: time windows**
1. Recommended time windows for every MIM panel group from the 90-day resolution figures (A1): keep the dashboard
   picker at 7 days; active-incident panels longer than 7 days; Time to Resolve with 30 days of points and a 90-day
   P1 MTTR tile; CMDB and health panels down from 5 years to 7 days.
2. Ran D1 (`open_age.txt`): of the open incidents, **1 of 7 P2s and 193 of 648 P3s (30 %)** had no new record in the
   last 7 days, so today's 7-day window leaves them off the active panels (17 P3s last updated 30–90 days ago, 26
   90–180 days ago). ServiceNow does not re-send an open incident unless it changes.
3. Discussed with the team: P3 is only on MIM for the demo, so a 1-year window for the active panels is not needed (90
   days suggested for P1 / P2); confirmed CMDB relationships are re-sent daily, so the 6 CMDB panels stay at 5 years.
4. Applied item 3: *Time to Resolve* shows **30 days** of points (rolling 7-day median, reads 40 days); checked the day
   labels stay in date order across the month change.
5. Applied item 6: the 7 section 3 health panels read **30 days** instead of 5 years (what they show is unchanged:
   the Health window).
6. Made a preview of the proposed **P1 MTTR (90 days)** tile (`previews/mim-v5-p1-mttr-tile-preview.png`): median MTTR,
   count, average, how many within 4 h; to fit the row, the two user-impact placeholders become one tile. Not on the
   dashboard yet.
7. Added the **P1 MTTR (90 days)** tile to MIM, 5th in the tile row, keeping both "In progress" placeholders (row 7 5 5
   5 8 8 5 5). Tested (count, median, average and within-4 h against hand-worked values), checked in Kibana, updated
   the user manual and KPI sheet rows 123 and 132. On today's data it would read 6.4 h (3 P1s, avg 11.9 h, 1 within
   4 h).
8. Health panels: kept at 30 days (team decision), not 24 hours (24 hours would cut off the Health window's 3- and
   7-day options and could miss a late daily CMDB load).

**Infrastructure Overview KPIs** (`Dashboard Testing and Verification Template-updated.xlsx`, sheet *Persona KPI
Metrics Coverage*, Persona Infra / Template Overview)
1. The 11 Infra / Overview rows described an earlier overview. Removed the 7 that are not on the current dashboard
   (Servers Up, Fleet Availability, P3 Incident count, Windows / Linux servers with high CPU / memory).
2. Updated the 4 still on it (Total Servers Monitored, Servers Down, P1 and P2 incident counts) and added the 8
   missing KPIs (Domain status, Critical alerts, Servers under pressure, Failed changes (7 days), Active P1 · P2
   table, Open alerts by domain, Change Request Summary, Infrastructure incidents per domain), all Pass.
3. Rows below moved down by one with their pictures, filter and colour rules intact; the old evidence pictures of
   the block were removed (new evidence screenshots to be added). Noted that the Servers tile's subtitle describes
   the servers-down number, not the main number.

**MIM KPI sheet and user manual**
1. Brought the MIM KPI sheet fully up to date: 12 rows updated (Active P1, Open Alerts with No Incident, Escalation
   Channel, Application Health, Services of the Application, the 7 health panels) and 5 KPIs added (Active P2, Active
   P3, Priority filter, Incident age, Linked incidents); evidence pictures kept.
2. Reviewed "CNA Observability Dashboard - User Manual - Major Incident Management.docx" and wrote suggested updates
   (`MIM-USER-MANUAL-SUGGESTED-UPDATES.md`): section 5.3 still describes early-November MIM (P2 over 8 h, SLA column,
   Escalate, Alerts on this CI, an average-age chart); missing the controls, P1 MTTR tile, Dashboard Links and Future
   Releases; plus tidy-up (duplicate 5.3, list numbering, a personal OneDrive link with an email address in it).
3. Made the updated copy "CNA Observability Dashboard - User Manual - Major Incident Management - updated.docx" (the
   original untouched), with every change as a tracked change (author "Claude") to accept or reject: section 5.3
   brought up to MIM V5 (intro, the three panel tables, new 5.3.2 controls table, notes, Dashboard Links, Future
   Releases), the personal OneDrive link replaced, Time Selector note, glossary (7 terms), troubleshooting (4 rows),
   FAQ (4 answers), catalogue (Infrastructure Overview, Executive), version 1.1. Validated and rendered.
4. Listed the follow-ups to do by hand in Word in `MIM-USER-MANUAL-TODO.md` (update the table of contents, retake two
   screenshots, list numbering and empty headings, support email spelling, the SharePoint link).

**Other**
1. PBA: not a standard ServiceNow term or field, and no PBA field reaches Elastic (check R1); asked the team what it
   stands for and which field holds it. It is on MIM's Future Releases roadmap.

**Open from today**
- Re-import MIM V5 (P1 MTTR tile, 30-day Time to Resolve, health panels at 30 days) and check it on real data.
- Accept or reject the tracked changes in the updated MIM user manual, then do the items in `MIM-USER-MANUAL-TODO.md`.
- Add new evidence screenshots for the 12 Infra / Overview rows of the KPI sheet.
- Relabel the Infrastructure Overview Servers tile (its subtitle describes the servers-down number).
- Item 2 (90 days for MIM's active-incident panels) left as it is for now; F1 (`cmdb_with_apm_flag`) still to run.
- Find out what PBA is and which ServiceNow field holds it.

## 18 Nov 2026

**MIM V5**
1. **P3 back**, any age, with the same rules as P2 (On Hold P2s and P3s left out; On Hold P1s shown): a new *Active
   P3* tile, P3 in the *Needs attention now* strip, *Active Incidents (P1 · P2 · P3)*, *Escalation Channel*, the
   Incident and CI dropdowns, and a P3 line (Duration, 24 h target) on the time-to-resolve chart.
2. **Priorities control** (multi-select: P1, P2, P3, all picked by default) in the top bar. *Active Incidents*,
   *Escalation Channel* and the time-to-resolve chart follow it; the tiles show every priority, one tile each.
3. **Age column** (time since opened, e.g. "1 d 16 h") in *Active Incidents* and *Escalation Channel*.
4. **Time-to-resolve chart** (`trendline.png`): the axis covered the 30 days the panel reads while the line covers 7,
   so the lines sat squeezed at the right edge. The days are now labels ("Nov 18"), so the 7 days fill the chart.
   Added check T1 to confirm the P2 values (about 0.3 h). (The flat lines were corrected later today, see below.)
5. **Application Health / Services of the Application errors again** (now on `service.name`): compared the production
   dashboard (`mim_error.ndjson`) with the last version built: identical, so nobody else changed it. The cause is the
   data: `cmdb_with_apm_flag` keeps gaining text fields with the same names as APM fields (17 Nov `ci.name`, 18 Nov
   `service.name`). All four queries that read it now convert every shared text field they use, so further fields
   like these no longer break them. Added check F1 to see when the index was reloaded and what is in it.
6. **Dashboard Links**: only *Related Dashboards* (Detailed Dashboards removed); Executive Dashboard (In Progress) as
   text, not a link; same names and order as the Infrastructure Overview.
7. Tested (P3 rows, tiles, Priorities with one and several values, Age, chart points and labels, the production error
   reproduced and fixed, links), checked in Kibana, updated the user manual and seven KPI sheet rows (122, 125,
   130–132, 142, 163).

**MIM: time-to-resolve chart corrected** (`dash.png`, `trendline2.png`)
1. Found why a solid P1 line showed while no P1 was open: the chart shows **resolved** incidents, and the rolling
   7-day median counted each resolved incident on 7 days in a row. The only P1 resolved in the period (INC2692216,
   resolved 13 Nov, MTTR 26.8 h) was repeated from 13 to 19 Nov as a flat line. The line style also joined points
   across days with nothing resolved, so gaps looked like data.
2. Changed the chart: each point is now the median of the incidents resolved **that day**, each incident counted
   once; no point on a day with nothing resolved for that priority, and points are not joined across such days.
   INC2692216 is now a single P1 point on 13 Nov.
3. Tested (each P1 appears only on its resolution day; gaps not joined), checked in Kibana, updated the user manual
   and KPI sheet row 132.

**MIM: time-to-resolve chart reverted** (team decision)
1. Put the chart back to the **rolling 7-day median** (as built this morning with P3 and the Priorities control),
   undoing the one-point-per-resolution-day change. The P1 line again shows INC2692216 (26.8 h) until 20 Nov, although
   no P1 is open; the user manual says so. Everything else from today is kept.

**Future Releases**
1. Infrastructure Overview: removed the *partial* tags from the Database, Middleware and VMware domain tiles; why they
   were partial is now in the *Next Release Roadmap* card (Database and Middleware status from incidents and alerts
   only; VMware: 4 of 549 ESX hosts, some vSphere metrics not collected).
2. MIM: new section **5 · Future Releases** with *Next Release Roadmap* (user impact, MTTR with the MIM team's Outage
   adjustments, clickable alerts, PBA flag, telemetry for every monitored application, a stable CMDB application list,
   Linked incidents over a P1's whole life) and *Predictive & AI Insights* (AI incident summary, change and alert
   correlation, breach risk, anomaly detection, blast radius), from the gaps found while building it.
3. Tested, checked in Kibana, updated both user manuals.

**Average time to resolve by priority** (A1, `ttr_averages.txt`, incidents resolved in the last 90 days)

| Priority | Resolved | Average | Median | 90 % within | Longest |
|---|---|---|---|---|---|
| P1 (duration) | 3 | 12.6 h | 6.4 h | 24.1 h | 28.5 h |
| P1 (MTTR from becoming P1) | 3 | 11.9 h | 6.4 h | – | 26.8 h |
| P2 | 3,915 | 7.4 h | 0.3 h | 8.1 h | 2,519 h |
| P3 | 37,263 | 32.1 h | 1.0 h | 97.3 h | 3,490 h |

- ServiceNow's `resolution_time` matches the dates exactly, so the P2 median of 0.3 h on the chart is real (this
  answers check T1): half of P2s are resolved within about 18 minutes; the average is pulled up by a few very long
  ones.
- Against the targets: P1 4 h met by 1 of 3 (INC2674345, 2.4 h); P2 8 h met by about 90 %; P3 24 h: median 1 h, but
  more than 10 % take over 4 days.

**Infrastructure Overview v2**
1. Related Dashboards: Executive Dashboard (In Progress) as text, not a link; renamed Portfolio, Application Operations
   and Infra Overview; Infra Overview and Major Incident Management swapped. Detailed Dashboards kept here.
2. Shorter link names: Executive (In Progress) (still text), Cloud Infra, Database Infra, Middleware, Server Infra,
   VMware Infra. MIM's Executive tile renamed too, so its Related Dashboards still match.
3. Updated the user manual.

**Reporting**
1. Updated the action tracker (`ACTION-TRACKER-2026-11-03-04.md`, now 3–18 Nov) twice: P3 back, Priorities, Age, the
   field fix and the links; then the chart correction, MIM Future Releases and the Infrastructure Overview *partial*
   change. Both spreadsheet summaries updated.

**Open from today**
- Import the updated MIM V5 and Infrastructure Overview v2 (then More → Reset changes) and check them on real data.
- Run F1 (`cmdb_with_apm_flag`: when it was reloaded, which fields it has). (T1 answered by A1.)
- Decide on the MIM V5 previews (*CI at a glance*, *health distribution* bar).
- Decide whether the Infrastructure Overview should show every active P2 (it still shows P2 over 8 h).
- Decide whether On Hold P2s and P3s should be shown on MIM (the Incident control and Escalation Channel show them).
- Review the Future Releases items on both dashboards with the team (wording and priority).
- Tell the owner of `cmdb_with_apm_flag` that new fields in it affect MIM.

## 17 Nov 2026

**MIM V5**
1. Removed P3 incidents from the dashboard entirely, leaving P1 and P2. P2s still appeared once they were past their
   8 h target (changed later today: every P1 and P2 is now shown whatever its age, see below). This covered the tiles, *Needs attention now*, *Active Incidents*, *Escalation Channel*, the Incident and CI
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

**MIM: P1 and P2 regardless of age**
1. Checked which MIM panels showed P2s only once open longer than 8 h: the *Needs attention now* and *P2 over 8 h*
   tiles and the *Active Incidents* table did; the Incident control and *Escalation Channel* already showed every
   active P2.
2. Team decision: show every active P1 and P2 whatever its age, on every panel. Built it:
   - *P2 over 8 h* tile renamed **Active P2** (any age); *Needs attention now* counts every active P1 and P2.
   - *Active Incidents (P1 · P2 over 8 h)* renamed **Active Incidents (P1 · P2)**, showing every active P1 and P2.
   - The On Hold rule is unchanged (On Hold P1s shown, On Hold P2s not, in section 1); the 8 h P2 target stays on
     the Time to Resolve chart.
3. Tested (a 3-hour-old P2 now shows; an On Hold P2 still does not). Updated the user manual and five KPI sheet rows
   (122, 125, 130, 141, 163).

**MIM: Application Health and Services of the Application errors**
1. Diagnosed the errors (`es_error.png`, `application_health_error.txt`, `service_health_error.txt`): the
   `cmdb_with_apm_flag` index now has a `ci.name` field stored as text, while APM stores `ci.name` as keyword, and
   ES|QL refuses a field with two types. The Application and Service dropdowns had the same problem.
2. Fixed all four queries: `ci.name` is converted once, straight after the data is read. Reproduced the production
   error locally first, then checked that the fixed panels run and return the same rows as before.

**Dashboard Links (Infrastructure Overview v2 and MIM V5)**
1. Infrastructure Overview v2:
   - **Executive Dashboard (In Progress)** is now a link (`links.txt`), still reading "Executive Dashboard (In
     Progress)".
   - Added **Infrastructure Overview** before Major Incident Management.
   - Every link now uses the Portfolio dashboard's link font (`pfv4.ndjson`); the tiles are taller so the labels
     are not cut off.
   - Removed the panel that only showed "Last 2 days" (Data freshness) above Future Releases.
2. MIM V5: replaced section 4 *Related dashboards* (Applications Operations and Infra Dashboard links) with an
   identical copy of the Infrastructure Overview's **Dashboard Links** section.
3. Tested (links identical on both dashboards, order, font, link addresses) and updated both user manuals.
4. Switched the Server Infra, Middleware and Applications Operations links on both dashboards to the short links in
   `links.txt` (they differed from `respective_detailed_dashboards.txt`; team decision to use `links.txt`).

**Reporting**
1. Updated the action tracker (`ACTION-TRACKER-2026-11-03-04.md`) with MIM and Infrastructure Dashboard progress from
   5 to 17 Nov, each with a summary ready to paste into the action tracker spreadsheet.
2. Wrote the status reply on P1 MTTR and P2 Duration (`response.md`): built on MIM V5, being checked on live data.

**Capability Tracker**
1. Reviewed `Capability Tracker.xlsx`: 85 Elastic observability capabilities (CAP-001 to CAP-085) with category, AI
   type, description, metric, target, version status, priority, owner and notes.
2. Added 20 capabilities (CAP-086 to CAP-105) from the dashboard work: ServiceNow ITSM sync, MIM command view, P1
   MTTR from Outage records, incident duration trend, SLA tracking, change-to-incident correlation, Netcool bridge,
   alert noise reduction, unattended alerts, data feed freshness, domain status landing page, impact mapping, F5,
   Palo Alto, storage and backup, certificate expiry, Windows services, mainframe, executive reporting, and AI incident
   summaries.
3. Updated CAP-088 (P1 MTTR) to match what was built: the became-P1 time comes from the ServiceNow incident timeline,
   not the Outage records. Noted on CAP-090 (SLA tracking) that MIM now reports P1 MTTR / P2 Duration instead.

**Open from today**
- Import the updated **MIM V5** and **Infrastructure Overview v2** (then More → Reset changes) and check them on real
  data:
  - MIM: Application Health and Services of the Application load without the error; the new Active Incidents columns;
    the P1 line on Time to Resolve (INC2692216, resolved 13 Nov, counts as 26.8 h until the window passes it on 20 Nov).
  - Both: the Dashboard Links open the right dashboards.
- Decide whether section 1 of MIM should also show On Hold P2s (the Incident control and Escalation Channel do).
- Decide whether the Infrastructure Overview should also drop "P2 over 8 h" and show every active P2.
- Decide on the MIM V5 previews (*CI at a glance*, *health distribution* bar); reminder set for 18 Nov.
- `respective_detailed_dashboards.txt` still has the old Server Infra, Middleware and Applications Operations links.
- Only if James needs the MIM team's manual adjustments: ask the ServiceNow team to add the Outage table to the
  integration.
