# Suggested updates: "CNA Observability Dashboard - User Manual - Major Incident Management.docx"

Reviewed 19 Nov 2026 against MIM V5 as it is now. Grouped by priority: **A** = wrong today (fix before the hypercare
start on 23 Nov), **B** = missing, **C** = tidy-up. Replacement text is ready to paste.

## A. Content that is wrong today (section 5.3)

### A1. Section 5.3 intro, "Major Incident Overview" paragraph

Today: "Highlights of incidents that have exceeded their target resolution time (TRT) require immediate attention."
Since 17–18 Nov the overview shows **every** active P1, P2 and P3, whatever its age. Replace with:

> Provides a quick overview of the active P1, P2 and P3 incidents and of the open alerts that have no incident, so the
> MIM team sees what needs attention now. Tiles count the active incidents by priority and show the P1 MTTR of the last
> 90 days; the table lists every active incident with its age, owners and user impact; the chart shows how quickly
> incidents were resolved against their targets (P1 4 h, P2 8 h, P3 24 h).

### A2. Section 5.3, Major Incident Overview panel table: replace the whole table

| Panel | Shows | Fills when |
|---|---|---|
| Needs attention now | Every active P1, P2 and P3 in one number, with a strip by priority. **Green at 0** | Always |
| Active P1, Active P2, Active P3 | The same incidents, by priority, whatever their age. On Hold P1s count; On Hold P2s and P3s do not. Green and "All clear" at 0; "Needs action" in the priority colour above 0 | Always |
| P1 MTTR (90 days) | Median time to resolve of the P1s resolved in the last 90 days, from when each became a P1, with the count, the average and how many were within the 4 h target. Red above 4 h, green at or under | Always |
| Open alerts, no incident | Open Netcool alerts on production CIs with no open incident, by severity (Critical, Major, other): possible blind spots. Follows the Incident / CI controls | Always |
| User base · ServiceNow, Real users · RUM | Placeholders: the integrations are in progress | Not yet |
| Active Incidents (P1 · P2 · P3) | The incidents behind the tiles (only the priorities picked in **Priorities**): priority, CI, state, opened, **Age**, **Time as P1 / Duration (h)**, **Linked incidents**, assignment group, assignee, group manager (with emails), description. Longest first. Click an incident to open it in ServiceNow | Always |
| P1 / P2 / P3 Time to Resolve vs Target | How quickly **resolved** incidents were resolved, for each of the last 30 days: each point is the median of the incidents resolved in the 7 days up to that day. P1 = MTTR (from when it became a P1); P2 and P3 = Duration (from opened). Dashed lines: targets P1 4 h, P2 8 h, P3 24 h | Always |

Notes for the table (add under it):
- *Time as P1 / Duration*: for a P1, hours since it became a P1 (MTTR so far); for a P2 or P3, hours since it was opened.
- *Linked incidents*: incidents that name this one as their parent: the user impact of a P1.
- The SLA column was removed on 13 Nov; MIM reports P1 MTTR and P2 / P3 Duration instead of the ServiceNow SLAs.
- A resolved incident stays in the chart for 7 days, so a P1 line can show while no P1 is open.

Remove the row **Open Alerts with No Incident** from this table: the panel is in section 2 (see A3).

### A3. Section 5.3, Investigate the CI panel table

- Rename **Escalate** → **Escalation Channel** (renamed 6 Nov). New text: "**Who to call.** One row per active P1, P2 or
  P3 incident on the CI (only the priorities picked in **Priorities**): priority, state, when opened, **age**, CI class
  and environment, assignment group, assignee and group manager (with emails). With a CI and no incident, one row with
  the CI's owners."
- **Delete the row "Alerts on this CI"**: the panel was removed on 11 Nov.
- **Add the row** *Open Alerts with No Incident* | "Open Netcool alerts (last 24 h) on CIs with no open incident,
  Critical first. With an incident or CI picked: only alerts on that CI and on CIs linked to it in the CMDB" | Always.

### A4. Section 4.2, "Time Selector"

Today: "Defines the time range used by all dashboard panels". On MIM almost every panel has its own fixed window (the
badge on the panel, e.g. "Last 7 days"), so the time picker does not change them. Add:

> On the Major Incident Management dashboard, most panels use their own fixed time window, shown as a badge on the
> panel (for example "Last 7 days" or "Last 30 days"); changing the time picker does not change those panels.

## B. Missing from the manual

### B1. The controls (add as 5.3.2 "Using the MIM controls", before the panel tables)

| Control | Where | What it does | Default |
|---|---|---|---|
| Priorities | Top bar | Multi-select: which priorities Active Incidents, Escalation Channel and the Time to Resolve chart show | P1, P2, P3 |
| Incident | Top bar | The incident to investigate (`INC number · CI`); picking one fills sections 2 and 3 with its CI | (all incidents) |
| CI | Top bar | A CI to investigate without an incident | (no CI selected) |
| Monitored application | Top bar | Limits the application panels to the monitored applications, or one of them | (all monitored applications) |
| Server, Application, Service | Section 3 | The server for the health panels, one application for Services of the Application, one service for Upstream / Service health / Downstream | (none) |
| Health window | Section 3 | How far back the health panels look: 15 minutes to 7 days | 24 hours |

Plus: "Sections 2 and 3 stay mostly empty until an Incident or CI is picked: that is expected. To start again: More
(…) → Reset changes."

### B2. Section 4 "Dashboard Links" and section 5 "Future Releases" of the dashboard

> **Dashboard Links**: Related Dashboards: Executive (In Progress), Portfolio, Application Operations, Major Incident
> Management, Infra Overview. Each opens in a new tab.
>
> **Future Releases**: *Next Release Roadmap* (data still to come: user impact from the ServiceNow user base and RUM,
> MTTR with the MIM team's Outage adjustments, clickable alerts, the PBA flag, telemetry for every monitored
> application) and *Predictive & AI Insights* (AI incident summary, change and alert correlation, breach risk, anomaly
> detection, blast radius).

### B3. Glossary (1.5): add

| Term | Meaning |
|---|---|
| MIM | Major Incident Management |
| P1 / P2 / P3 | ServiceNow incident priority; targets P1 4 h, P2 8 h, P3 24 h |
| MTTR | Mean / median time to resolve; for a P1, from when the incident became a P1 to resolved |
| Duration | For a P2 or P3, time from opened to resolved (or to now while open) |
| Linked incidents | Incidents that name another incident as their parent |
| Netcool | IBM Netcool/OMNIbus, the source of the infrastructure alerts |
| CMDB | ServiceNow configuration management database (CIs and their relationships) |

### B4. Troubleshooting (6.1): add MIM rows

| Symptom | Likely cause | Resolution |
|---|---|---|
| A control is missing, or panels show "Unknown query parameter" after a dashboard update | Kibana re-applies unsaved control picks from before the update | More (…) → **Reset changes** |
| Application Health / Services of the Application show "Cannot use field … due to ambiguities" | A field in the CMDB application list (`cmdb_with_apm_flag`) changed type | Report it to the dashboard team (fixed 17–18 Nov for the fields seen so far) |
| A P1 line shows on the chart while no P1 is open | The chart shows resolved incidents; each stays in the 7-day window for a week | Expected; see the P1 MTTR tile for the 90-day figure |
| Sections 2 and 3 are empty | No Incident or CI picked | Pick one in the top bar |

### B5. FAQ (7): replace the placeholders with MIM answers

- *Why does a P1 line show when there is no open P1?* — see B4.
- *How is P1 MTTR calculated?* — from when the incident became a P1 (ServiceNow incident timeline) to resolved; the
  opened time if it was opened as a P1. The MIM team's manual Outage adjustments are not included yet.
- *Why does the time picker not change the panels?* — see A4.
- *Why are P3 incidents shown?* — for the demo; MIM may cover P1 and P2 only later.
- Keep "Dashboard modification" and "Missing data" once the process is agreed.

### B6. Section 5.1 catalogue: add the dashboards now linked from MIM

Infrastructure Overview (landing page for infrastructure, links to the detailed dashboards), Portfolio, Applications
Operations, and Executive (in progress).

## C. Tidy-up

1. Two headings are numbered **5.3** ("MIM Dashboard" and "Major Incident Management Dashboard - KPI Definitions"):
   make the second **5.3.2** (or 5.3.3 if B1 is added as 5.3.2), and refresh the table of contents.
2. Numbered lists restart wrongly: 2.2 (1, then 1–3), 3.2 ("2 ." with a space), 4.1 (1, 4, 3).
3. Empty headings in 1.4, 3.1, 4.1 and after 5.3 (blank lines formatted as headings) show up in the table of
   contents; remove them.
4. The link "MIM dashboard User manual.docx" points to a personal OneDrive and carries a colleague's email address
   in the URL (`email=…`, `ovuser=…`). Replace it with a clean link to the shared copy (SharePoint), or point to the
   maintained MIM V5 user manual.
5. Version history (1.3): date "TBD"; add **1.1, 19 Nov 2026**: "MIM section updated to MIM V5 (P3, Priorities, Age,
   P1 MTTR, Dashboard Links, Future Releases)".
6. Support email `TCSobservbilityprojectteam@cna.com` — check the spelling ("observbility") is the real address.
7. Screenshots: after re-importing the latest MIM V5, retake the section 1 screenshot (it does not yet show the
   Priorities control or the P1 MTTR tile) and the section 2 screenshot if it still shows *Alerts on this CI*.
8. "Highlights of incidents that have exceeded … require immediate attention" (grammar) — replaced by A1.
