# MIM V3 — test walkthrough: from an incident to its cause and the right person

A step-by-step run through the MIM V3 dashboard for one live P1, P2 or P3 incident. It does two jobs:

- **Teaches the flow** a Major Incident Manager (MIM) follows: pick the incident → find the likely cause → see who and
  what is impacted → escalate to the person assigned to the ticket, or their manager.
- **Tests the dashboard**: each step says what you should see. Tick the box, or write down what was different, in
  the test record at the end.

Time needed: about 20 minutes per incident. Run it on at least two incidents: one on a **server** CI and one on an
**application / service** CI, because different panels fill for each.

---

## Before you start

| Check | Done |
|---|---|
| The current `MIM V3.ndjson` is imported (overwrite), then **More → Reset changes** and reload | ☐ |
| Your Kibana role can read every index the dashboard uses (list in *MIM-V3-CHANGES-2026-10-16.md*); a panel you cannot read shows an error, not "no results" | ☐ |
| There is at least one **active** P1, P2 or P3 in ServiceNow (state not Resolved / Closed / Canceled). The Incident control only lists active incidents | ☐ |
| ServiceNow is open in another tab, so you can compare what the dashboard shows with the ticket | ☐ |

Leave the controls at their defaults: Incident **(all incidents)**, CI **(no CI selected)**, Service
**(services on this CI)**, Application **(all applications)**. Time picker: **Last 24 hours**.

---

## Step 1 — Triage: which incident needs attention? (section 1, *Major Incident Overview*)

| # | Do | You should see | ✓ |
|---|---|---|---|
| 1.1 | Look at **Active P1 / P2 / P3** | A donut with the total in the middle and the P1 (red), P2 (amber) and P3 (blue) counts beside it. The counts match the active P1 / P2 / P3 list in ServiceNow | ☐ |
| 1.2 | Look at **Users impacted** | The demo number **2,500** and "Real count to be incorporated from ServiceNow and RUM". This tile is a placeholder; do not use the number | ☐ |
| 1.3 | Look at **Active Incidents (P1 / P2 / P3)** | One row per active incident, P1 first, oldest first: Incident, Pri, Affected CI, State, SLA, Assignment Group, Assignee, Assignee Email, Group Manager Name, Manager Email Id, Short description | ☐ |
| 1.4 | Choose the incident to work on: a **P1** before a P2 before a P3, then **SLA** Breached → Breaching → Within SLA | Note its **number**, **Affected CI**, **Assignee** and **Group Manager** in the test record | ☐ |
| 1.5 | Click the incident number → *Open incident in ServiceNow* | The ticket opens in ServiceNow. Assignee and assignment group match the row | ☐ |
| 1.6 | Look at **Open Alerts with No Incident** | Open Netcool alerts from the last 24 hours on CIs that have **no** open incident, critical first. Anything critical here is a problem nobody has raised yet. It may be linked to your incident (same application, same time) | ☐ |

> **What "SLA" means.** Breached, Breaching (75 % used or due within 30 min), Paused (On Hold) or Within SLA, from
> ServiceNow's SLA records. "(age)" means the incident has no SLA record, so its age is compared with P1 4 h / P2 8 h / P3 24 h.

---

## Step 2 — Point the dashboard at the incident

| # | Do | You should see | ✓ |
|---|---|---|---|
| 2.1 | In the **Incident** control, pick `<number> · <CI>` | Sections 2 and 3 now show the incident's Affected CI. The CI control can stay at "(no CI selected)": while an incident is picked, its CI wins | ☐ |
| 2.2 | Set the time picker to start **at least 2 hours before the incident was opened** (e.g. *Last 7 days* for an older incident) | Panels that follow the time picker (Server, Middleware, Database, Process, Synthetics, Logs) now cover the start of the problem. Panels marked with a fixed range (e.g. *Last 7 days*) do not change | ☐ |

If the incident has **no CI** (`<number> · (no CI)`), sections 2 and 3 stay empty. Ask the assignment group which CI is
affected, then set the Incident control back to **(all incidents)** and pick the CI in the **CI** control. The CI
control lists only CIs that had a P1 / P2 / P3 in the last 31 days.

---

## Step 3 — Find the likely cause (section 2, *Investigate the CI*)

Work down the panels in this order. The first ones answer "what happened just before the incident?"

| # | Panel | What to look for | You should see | ✓ |
|---|---|---|---|---|
| 3.1 | **Alerts on this CI** | Rows marked **Likely trigger**: Netcool alerts first seen up to 2 h before the incident opened. They are listed first | Alerts on the incident's CI from the last 7 days; *Now* says Open or Cleared; *vs incident* is Likely trigger / Earlier / After | ☐ |
| 3.2 | **Changes in the Last 7 Days on this CI** | A change that ended shortly before the incident opened, on this CI or a CI linked to it. **Emergency** changes are red. Click the change to open it in ServiceNow | Changes on the CI itself first, then on linked CIs; the CI column says which | ☐ |
| 3.3 | **Server Health** | Red tiles: no data for more than 10 minutes (server down or agent stopped), CPU, memory or disk at 90 % or more | Four tiles named after the server. **No tiles** = the CI is not a monitored server (normal for an application CI) | ☐ |
| 3.4 | **Middleware Health** and **Database Health** | Anything **Down** (stopped, or silent for 10 minutes). Down rows come first | Components on this CI with status and minutes since last seen. Click the Server to open it in ServiceNow. Empty = nothing of that kind monitored here | ☐ |
| 3.5 | **Process Health** | Windows services that are **Stopped** (set to Automatic but not running), processes **Not seen** | Problems first, healthy middleware below | ☐ |
| 3.6 | **Errors from the Logs** | Critical / error messages whose **First seen** is close to the incident's opened time | Warning-and-worse lines grouped by message, critical and error first | ☐ |
| 3.7 | **Synthetics Health** | Monitors **Down** now, or with down checks in the time range | Ping / HTTP monitors that target this CI. Empty is normal for many CIs | ☐ |
| 3.8 | **SLO Error Burn Rate** | ★ rows (this CI's own SLOs) burning at **14.4× or more** ("page now") | This CI's SLOs first, then every SLO burning 1× or more | ☐ |
| 3.9 | **Applications on this CI** | Which APM services run on this server, and whether they still send data (*Last data*) | APM services seen on the CI in the last 7 days | ☐ |

**Write down the evidence** in the test record: the alert, change, component or log message that best explains the
incident, and the time it started.

---

## Step 4 — Check the CIs around it (section 2)

The cause is not always on the incident's own CI. A database, middleware server or host it runs on may be the real
problem.

| # | Panel | What to look for | You should see | ✓ |
|---|---|---|---|---|
| 4.1 | **Blast radius** | How many applications depend on this CI. Amber from 1, red from 5 | A count, split into business applications and application services | ☐ |
| 4.2 | **Applications related to this CI** | The applications that will be affected: those whose How reads "it … this CI" (e.g. "it consumes this CI"). Rows reading "this CI … it" are applications the CI itself uses | Every related application, both directions, business applications first. Columns: Application, Kind, How, Env. Compare with the CI's related items in ServiceNow: nothing should be missing | ☐ |
| 4.3 | **Middleware / Database / Server View** and **Other related CIs** (section 2, after *Applications related to this CI*) | The CIs this CI runs on or uses ("this CI runs on it"), and the ones that use it ("it runs on this CI"). Compare their names with the Alerts, Changes and Logs panels: a changed or alerting database or host is a strong lead | Four tables: Related CI, Type, Relationship, Env. Retired CIs last, marked "· retired". Empty view = no relationship of that kind in the CMDB. Every related item in ServiceNow should appear in one of the five tables | ☐ |

These four views come from the CMDB and show **no live health**. To check a related CI's health:

- If it had a P1 / P2 / P3 in the last 31 days, set the Incident control to **(all incidents)** and pick it in the **CI**
  control. Section 2 then shows its alerts, changes, health and logs.
- Otherwise open the **Infra Dashboard** (section 4) for servers, or look it up in ServiceNow.

---

## Step 5 — Check the services and the applications impacted (section 3)

Most useful when the CI runs APM-instrumented services. Leave the Service control at **(services on this CI)**.

| # | Panel | What to look for | You should see | ✓ |
|---|---|---|---|---|
| 5.1 | **Service health** | Red tiles: 10 % or more failed transactions in the last hour. Amber from 1 % | One tile per production service on this CI. Click a tile to open its APM Service Map | ☐ |
| 5.2 | **⬅ Upstream — what they depend on** | A **red bar**: calls to a database, queue or other service that are failing. This points at the cause | Top 15 dependencies, failing first | ☐ |
| 5.3 | **Downstream — who is impacted ➡** | Calling services with failing calls: the impacted side | Top 15 callers, failing first. Click one to open its Service Map | ☐ |
| 5.4 | **Business applications impacted** | The business applications of those callers, worst first, with their support group | Click one to open it in ServiceNow | ☐ |
| 5.5 | **Application Health**, then pick the worst application in the **Application** control | Which of the applications related to the incident's CI are Failing / Degraded right now (last hour); all of production when no CI is selected. **Services of the Application** then lists that application's services, worst first | "Low traffic" services (under 20 transactions in the hour) are listed but not rated | ☐ |

To follow one service, pick it in the **Service** control. The four panels above then show that service instead of
the CI's services.

---

## Step 6 — Decide where the cause is

| Evidence from steps 3–5 | Likely cause | Who should fix it |
|---|---|---|
| Likely-trigger alert, Down component, red Server Health tile or stopped service **on the incident's CI** | The CI itself | The incident's **assignment group** (it should already be working on it) |
| A change on the CI that ended shortly before the incident | The change | The change's **assignment group** (column in *Changes*), together with the incident's group |
| Problem on a **related CI** (the related-CI views, or the CI column in *Changes*), or a red **Upstream** bar | The dependency | That CI's support group in ServiceNow. Make sure the incident's assignment group knows |
| Many **Open Alerts with No Incident** on CIs of the same application | A wider problem | Raise or link an incident for those CIs |
| Nothing found | Not visible in monitoring | The assignment group, asking what they have found so far |

Write the decision in the test record.

---

## Step 7 — Escalate to the right person (section 2, *Escalate*)

| # | Do | You should see | ✓ |
|---|---|---|---|
| 7.1 | Look at **Escalate** with the incident picked | **One row**: CI, Active Incident, Priority, Class, Env, CI support group, Assignment Group, Assignee, Assignee Email, Group Manager Name, Manager Email Id | ☐ |
| 7.2 | Compare **Assignment Group** with **CI support group** | They normally match. If they differ, the incident may be with the wrong team: tell the assignment group and the CI's support group | ☐ |
| 7.3 | **Contact the Assignee** (Assignee Email) with the evidence from steps 3–6 | Assignee and email match the ServiceNow ticket | ☐ |
| 7.4 | Escalate to the **Group Manager** (Manager Email Id) if the Assignee is **"—"** (nobody assigned) or does not respond within your MIM process's response time (P1: ___ min, P2: ___ min) | Manager name and email match the assignment group's manager in ServiceNow | ☐ |
| 7.5 | If the cause is on another team's CI (step 6), contact that CI's support group as well | Its support group is on the CI record in ServiceNow (search for the related CI there; the section 3 views have no click-through) | ☐ |
| 7.6 | Click the **Active Incident** → *Open incident in ServiceNow*, and record the escalation in the work notes | The ticket opens | ☐ |

---

## Step 8 — Reset

Set the Incident control back to **(all incidents)** and the time picker to **Last 24 hours**, so the next person
starts from the overview.

---

## Known limits to keep in mind

- **Users impacted** is a demo number until user counts come from ServiceNow and RUM.
- **Alerts and incidents** are linked by CI and time only; Netcool alerts carry no incident number.
- **Open Alerts with No Incident** looks at the last 24 hours; an open incident not updated in that time is missed,
  so its alerts can show as "no incident".
- **The related-CI views** (section 2) are CMDB data with no live health (the dependency index has no timestamp).
- **Changes** mostly shows changes on the CI itself; changes on linked CIs appear only when the CMDB link was updated
  in the same week.
- **The CI control** lists only CIs that had a P1 / P2 / P3 in the last 31 days.

---

## Test record (one per incident)

| Item | Value |
|---|---|
| Tester / date | |
| Incident number · priority · SLA | |
| Affected CI (server or application?) | |
| Assignee / Group Manager (from the dashboard) | |
| Do they match ServiceNow? | Yes / No |
| Evidence found (panel, row, time) | |
| Likely cause (step 6) | |
| Escalated to (name, email, time) | |
| Steps that did not show what this guide says (step number and what you saw) | |
| Panels that showed an error | |
| Time taken | |
