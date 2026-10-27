# MIM V3 — how a Major Incident Manager uses the dashboard

**File:** `MIM V3.ndjson` · **Dashboard:** MIM V3 · **Built from:** Naveen's MIM sketch (`naveen-mim suggestion.png`)
**Default time range:** last 24 hours, refreshing every 5 minutes

MIM V3 answers four questions, in order:

1. **What is going on?** Every active P1, P2 and P3 incident across the estate, how old it is, where it sits and what
   state it is in.
2. **Why, and how bad?** Everything Elastic knows about the one CI behind the incident: its own health, the
   middleware and processes on it, the applications that depend on it, whether customers are feeling it, what the
   logs say and what changed on it recently.
3. **Who do we call?** The CI's support group and the group each incident is with, with one-click links into
   ServiceNow.
4. **What else is hit?** The services behind the CI, what they depend on, which services call them and which
   business applications those belong to.

The dashboard has five sections and six controls. Incident and CI are pinned at the top; Server, Health window,
Service and Application are the first row of section 3, the only section they affect:

| | What it covers | Time window |
|---|---|---|
| **Incident control** (top, first) | Picks the incident to work on. Each option is "number · affected CI" (e.g. *INC100 · kau1s054*); sections 2 and 3 then show that CI, and *Escalate* shows that incident. Lists the active P1 / P2 / P3; type to search. *(all incidents)* clears it. | — |
| **CI control** (top, second) | Picks a CI directly, when no incident is picked (an incident overrides it). Lists the CIs with P1 / P2 / P3 incidents in the last month, plus every production server that sent server metrics in the last day; type to search. *(no CI selected)* clears it. | — |
| **Server control** (section 3, first) | Picks the server the health panels show when neither the incident's CI nor the CI control holds a server (e.g. the CI is an application: read a server name in *Server View* and pick it here). Lists every production server that sent server metrics in the last day; type to search. *(no server selected)* clears it. | — |
| **Health window** (section 3, second) | The data window of the health panels in section 3: 15 minutes · 30 minutes · 1 hour · 6 hours · 8 hours · **24 hours** (default) · 3 days · 7 days. | — |
| **Service control** (section 3, third) | Picks the service section 3 shows. *(services on this CI)* (the default) uses the production APM services running on the selected CI (the incident's affected CI, else the CI control); or type to pick any production service. | — |
| **1 · Major Incident Overview** | All active P1 / P2 / P3 incidents, all CIs | Fixed last month |
| **2 · Investigate the CI** | The picked incident's affected CI (or the CI picked in the CI control) only, including every CI and application related to it in the CMDB (*Applications related to this CI* and the four related-CI views) | Fixed per panel (shown on the panel); the CMDB panels read the last 5 years |
| **Application control** (section 3, fourth) | Picks the business application whose services *Services of the Application* lists. *(all applications)* (the default) lists every service, worst first. | — |
| **3 · Application & Service Health, Dependencies** | Every application's health from its services; the services of the picked application; the service(s) from the Service control with their dependencies; then the chosen server's health panels (Middleware, Database, Server, APM Services, Process, Synthetics, Logs) | Fixed last hour; the health panels follow the **Health window** control |
| **4 · Related dashboards** | Links to the Applications Operations and Infra dashboards | — |

---

## The walkthrough — telling the story

*Example used below: it is 09:00, the bridge line is quiet, and a P1 has just come in.*

### Step 1 — Spot the incident (section 1, top row)

The MIM lead opens MIM V3 and reads the top row from left to right.

- **Active P1**, **P2 over 8 h** and **P3 over 24 h** — three count tiles: every active P1 (red), whatever its age;
  the active P2s open longer than 8 h (amber); the active P3s open longer than 24 h (blue). 8 h and 24 h are the P2
  and P3 targets in the Time to Resolve graph; age = time since the incident was opened. A zero is shown faded.
  Last 7 days.
- **User base · ServiceNow** and **Real users · RUM** — how many users are affected, from the ServiceNow user base and
  from real-user monitoring. Both integrations are in progress, so both tiles show *In progress*.
- **P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)** — are the open incidents already past
  target? The average age so far of the still-open P1, P2 and P3 incidents opened each day, against the dashed target
  lines (red P1 4 h, amber P2 8 h, blue P3 24 h). An incident leaves the chart once it is resolved, closed, canceled
  or put On Hold; while it stays open its day's point climbs. A point above a line means that day's open incidents
  are, on average, older than target. Both axes start at 0 h: P1 and P2 use the left axis, P3 its own right axis, so
  P3 values of a day or more do not flatten the P1 and P2 lines. Incidents opened in the last 7 days.

### Step 2 — Pick the incident (section 1, table)

**Active Incidents (P1 · P2 over 8 h · P3 over 24 h)** lists the incidents the three tiles count: every active P1,
and the active P2s and P3s past their 8 h / 24 h target, P1 first and oldest first (last 7 days). Younger P2s and P3s,
and On Hold incidents, are left out; they can still be picked in the Incident control. For each one the lead sees:

- the **SLA**: Breached (ServiceNow's `task_has_breached` flag on one of its SLA records), Breaching, Paused, Within
  SLA, Met, or *No SLA record*. It is never worked out from the incident's age. Full rules in
  *MIM-V3-SLA-CALCULATION.md*;
- the people: the **Assignment Group**, the **Assignee** and the **Group Manager**, each with an email address
  (`assigned_to.name` / `.email`, `assignment_group.manager.name` / `.email`).

*In the example, the P1 on `kau1s054` shows SLA Breached.* The lead clicks the incident to open it in ServiceNow if
needed, then **selects it in the Incident control** (*INC100 · kau1s054*): sections 2 and 3 now show its affected
CI, `kau1s054`. (Picking `kau1s054` in the CI control does the same; when an incident is picked, it wins.)

**Open Alerts with No Incident**, under the table, answers "is anything else broken that nobody has raised yet?":
Netcool alerts still open (latest record not a clear) on CIs with no open incident of any priority, critical first.
*A UPS battery fault on `lonely01` has been open 20 hours with no incident.* Pick its CI in the CI control to
investigate it, or raise the incident in ServiceNow.

### Step 3 — Measure the impact (section 2)

Section 2 now shows `kau1s054` only.

- **Blast radius** and **Applications related to this CI** — who is hurt if this CI is down. The count tile
  (amber from 1, red from 5) counts the applications that depend on the CI. The table lists every application related
  to the CI in the CMDB, in both directions: business applications, application services and application instances,
  with the relationship spelled out (*Claim Center — it consumes this CI*; *this CI depends on it* for the ones the CI
  itself uses) and their environment.
- **APM Services Health** (section 3) — the APM services that sent data from the chosen server in the Health window, most
  recent first. *policy-admin reported 3 minutes ago.* (The CMDB applications are in the dependency panels
  above.)
- **Synthetics Health** — does the CI answer from outside? *The ping monitor for the server is down.*

At this point the lead knows the incident is real, customer-facing and tied to one server.

### Step 4 — Confirm it is this CI (section 2, then the health panels in section 3)

- **Alerts on this CI** — the Netcool alerts on the CI, open ones and cleared ones, with when each started compared
  with the picked incident. **Likely trigger** = first seen up to 2 h before the incident opened (listed first);
  *Earlier* = longer before; *After* = once the incident was open. *A Major "CPU utilisation above 95 %" alert started
  28 minutes before INC100: the likely trigger.* Netcool does not record which incident an alert raised, so this is a
  match by CI and time.

- **Server Health** — the server's own telemetry, one row per server: Status (*Reporting*, *Silent* after 10 minutes
  without data, *No data in window*), minutes since it last reported, CPU p90, memory peak, fullest disk, the
  percentages green / amber / red. *CPU is at 92 % and the disk is 88 % full.*
- **Middleware Health** — every middleware component on the CI (IBM MQ, IBM HTTP Server, JBoss, WebSphere, Windows
  middleware services such as IIS) with a red *Down* / green *Healthy* badge, Down first, minutes since it last
  reported and the server it runs on. *The IBM HTTP Server has not reported for 25 minutes.* Click the server to
  open it in ServiceNow.
- **Database Health** — the same for databases (SQL Server metrics, and SQL Server, Oracle, Db2 … processes and
  Windows services). *The MSSQLSERVER service is stopped.*
- **Which server?** The health panels show the incident's CI if it is a server, else the CI control's value if it
  is a server, else the server picked in the **Server** control. For an application CI, pick one of its servers
  (from *Server View*) in the Server control.

### Step 5 — Find the cause (health panels, section 3)

- **Process Health** — which process or service actually stopped. *The SQL Server Windows service is Stopped and an
  IBM HTTP Server instance has not been seen for 25 minutes.*
- **Errors from the Logs** — the warning-and-worse lines from the CI's server and application logs, grouped by
  message. *"MSSQLSERVER terminated unexpectedly", followed by SQL timeouts in policy-admin.*
- **Changes in the Last 7 Days on this CI** — was there a change just before? Changes on the CI itself, plus changes
  on CIs linked to it in the CMDB (its ESX host, cluster, switch …) when that link was recorded in the same 7 days. *An emergency change on `kau1s054` ended unsuccessful
  two hours before the incident opened.*

The story is now complete: an unsuccessful emergency change stopped SQL Server on `kau1s054`, which took down
policy-admin and the applications that depend on it.

### Step 6 — Escalate

**Escalate** gives the lead the people to call without leaving the dashboard. It has one row per active P1, P2 or P3
incident on the CI, showing the incident and its priority, the CI's class, environment and CMDB support group, and
the incident's Assignment Group, Assignee and Group Manager with their email addresses. With several incidents on the CI, pick one in the **Incident control** to show
only that one. Only the CI and the Active Incident are links; clicking either opens it in ServiceNow.

The lead now:

- declares a major incident if several applications or many callers are affected;
- opens the bridge and engages the CI support group, the incident's assignment group and the team that made the
  change (the Changes panel shows its group);
- shares the evidence: the burn-rate chart, the stopped service, the first error and the change.

### Step 6b — See what the CI is built from (section 2, the four CMDB views)

The four **related-CI views**, right after *Applications related to this CI*, list everything else the selected CI is
related to in the CMDB: **Middleware** (Tomcat, JBoss, WebLogic, WebSphere …), **Database** (Oracle, MS SQL, DB2, MySQL,
PostgreSQL …), **Server** (Windows, Linux, AIX, mainframe LPAR, ESX …) and **Other related CIs** (every other class:
load balancer pools, clusters, VMs, network gear, storage, IP addresses …), so no relationship is left out. Both
directions are shown: "this CI runs on it" (the CI uses it) and "it runs on this CI" (it uses the CI), sorted by type,
then name; retired CIs last, marked "· retired". *For the
application service Automated Claim Transaction PROD: Tomcat on vslrau1p276, an Oracle instance, two Linux servers
and the mainframe LPAR.* These are CMDB records, not live health: pick a server in the CI
control to see its health in the health panels (section 3).

### Step 6c — Which application to look at (section 3, top row)

**Application Health** follows the selected CI (the picked incident's CI, or the CI control): it lists the production
business applications related to it — linked to it in the CMDB in either direction, running APM services on it (a
server), or the CI itself when it is a business application. With no CI selected it lists every production business
application. Each is rated by the health of its services in the last hour, worst first: Failing (a service with 10 % or more failed transactions), Degraded (1 % or more) or Healthy, with how
many services are failing or degraded, and the **Servers** its services run on. Pick an application in the
**Application control**: **Services of the Application** then lists its services, worst first, with the servers each
runs on, error rate, latency and throughput; click a service to open its APM Service Map. Type a server from either
table into the **Server** control to see its health in the health panels below.

- **Servers** are the hosts the services' APM agents reported from in the last 15 minutes, lower case, sorted. Up
  to 3 are shown, then "+N more"; "—" means no APM agent host data (e.g. a service measured only from outside).
- **Why Application Health shows "Last 5 years".** The badge is only for the CMDB links of the selected CI in
  `cmdb-ci-relations*`, which ServiceNow re-sends only when a link changes (records go back to 2023). A Kibana panel
  applies its time range to every index it reads, so the range must reach those records. Health is still the last
  hour and Servers the last 15 minutes, both set in the query: APM data is never read further back.

### Step 7 — Size the blast radius (section 3)

Section 3 reads left to right, like a dependency map: what the service depends on → the service → who depends on it.
With the CI selected it shows the APM services running on the CI. If the CI is not a monitored server (an AIX box, a
network device, an application service), pick the affected service in the **Service** control instead.

- **⬅ Upstream — what they depend on**: a bar per database, queue or service they call; length = calls in the last
  hour, colour = health, and the label shows the share that failed. A red bar points at the cause. *The Oracle
  database the service calls: 38 % of calls failing.*
- **Service health**: a tile per service, green / amber / red by the share of its own transactions that failed, with
  its business application.
- **Downstream — who is impacted ➡**: a bar per production service that calls them, coloured by how many of those
  calls fail, with each caller's business application and support group: the teams to warn. This is the impact.

Click a service (a tile or a downstream bar) and choose *Open service in APM Service Map* for the drawn dependency
diagram.

During the bridge the dashboard keeps refreshing every five minutes, so the lead can watch the failed-transaction rates
fall, the service return to Running and the ping monitor go green.

### Step 8 — Look wider (section 4)

If the problem is bigger than one CI or one service, the two links at the bottom open the **Applications Operations Dashboard**
(applications, services, SLOs) and the **Infra Dashboard** (servers and platforms across the estate) in a new tab,
so MIM V3 stays open on the bridge.

---

## Things to know

### Controls and selections

- **Use the controls, not cell clicks, to choose what to look at.** Clicking a value and choosing *Apply filter*
  (or *Filter for*) adds a dashboard filter that applies to **every** panel. For example, a filter on an incident
  number also hides the SLA records, so *Active Incidents* shows "No SLA record". Remove such filters with
  the **×** on the filter pill under the search bar.
- **The CI control only lists CIs with a P1 / P2 / P3 opened in the last 31 days.** A CI outside that list cannot be
  picked. Type in the control to search the list.
- **An incident overrides the CI control.** With an incident picked, sections 2 and 3 follow its affected CI whatever
  the CI control says. Set the Incident control back to *(all incidents)* to use the CI control again.
- **A ⚠ next to the picked incident means it is no longer active.** The Incident control lists active P1 / P2 / P3 only;
  once the picked incident is resolved, *Escalate* shows no rows for it, while sections 2 and 3 keep showing its CI.
  Pick another incident or *(all incidents)*.
- **The controls cannot be left empty.** Each has a "nothing selected" option instead: *(no CI selected)*,
  *(all incidents)*, *(services on this CI)*.
- **Each control drives specific panels.** CI → section 2 and, through *(services on this CI)*, section 3.
  Incident → *Escalate* only. Service → section 3 only. Section 1 ignores all three.
- **For most incident CIs, you'll need to pick the service yourself.** Round 5 showed most P1 / P2s are raised
  against Linux / AIX servers, network devices or application services. Only servers with APM agents have services
  on them, so for the rest section 3 stays empty until you choose a service in the Service control.
- **Selections are unsaved changes.** Picking a CI or an incident does not change the saved dashboard. Do not click
  *Save* with a CI picked unless you want every viewer to open MIM V3 on that CI. Use **More (⋯) → Reset changes**
  to go back to the saved state.

### Time windows

- **A badge on a panel means a fixed window.** "Last 1 month", "Last 7 days", "Last 30 days" and "Last 1 hour"
  panels ignore the time picker. The health panels (section 3) show "Last 5 years" only because they also read the CMDB
  links; their data window is the **Health window** control.
- **Section 1** is fixed to the last month (*Open Alerts with No Incident*: last 24 hours). **Section 2**: *Escalate*
  is last month, *Alerts on this CI* and *Changes* last 7 days. **Section 3** is fixed to the last hour, except its
  health panels (Middleware, Database, Server, APM Services, Process, Synthetics, Logs), which follow the **Health
  window** control (24 hours by default). The time picker changes neither section.
- **Changes shows few linked CIs.** ServiceNow stores a CMDB relationship record only when the relationship changes
  (129k of 34M in a week, round 7 AN), so within 7 days *Changes* mostly finds changes on the CI itself. The CMDB panels (*Blast radius*,
  *Applications related to this CI* and the four related-CI views) read the same relationship graph with a fixed range of the last 5 years
  (records go back to 2023), so they show every relationship.
- **Set the Health window to suit the question.** Use 15 minutes to see the server's state *now*:
  *Server Health* shows CPU p90 and peak memory over the whole window, so 24 hours can show yesterday's peak. Use a
  window starting before the incident opened (3 days or 7 days for an older incident) to see the first errors in
  the logs.
- **Long Health windows load slowly the first time.** At 3 or 7 days, *Errors from the Logs* can take up to a
  minute on its first load, while older logs are read from disk; later loads take a few seconds (Round 11d: 4 s at
  7 days).
- **The dashboard refreshes every 5 minutes.** Click **Refresh** for an immediate update.

### Reading the numbers

- **"Breached" in the SLA column is ServiceNow's own verdict** (`task_has_breached` on the incident's SLA records),
  not the dashboard's. "No SLA record" means no SLA record for the incident was synced in the last 7 days. Full
  rules: *MIM-V3-SLA-CALCULATION.md*.
- **Active** means priority 1, 2 or 3 and state not Resolved, Closed, Canceled or Cancelled. In section 1 (the three
  tiles, Active Incidents and the trend) On Hold incidents are left out too, judged on each incident's latest record;
  Escalate and the Incident control still list them.
- **The trend's target lines** are P1 4 h, P2 8 h and P3 24 h, the same targets as the P2 / P3 tiles. Each still-open
  incident counts once, on the day it was opened, by its age so far (a minimum that grows until it is resolved or put
  On Hold, when it leaves the chart).
- **One slow incident moves a day's average.** On days with one or two P1s, a single long incident can put the point
  far above the line.
- **Health thresholds.** Server Health: amber from 80 %, red from 90 %, red if the server has been silent more than
  10 minutes. Middleware, Database and Process Health: *Down* / *Not seen* after 10 minutes without data. Section 3: *Failing*
  = 10 % or more of calls failed in the last hour, *Degraded* = 1 % or more.
- **Check the call count before trusting an error %.** In section 3, a service with 20 calls in the hour and 2
  failures shows 10 % *Failing*; the *Calls* / *Per min* columns show how much traffic is behind the figure.
- **Section 3 is production only** (`prd1`, `prd2`, `prd`, `prod`, `production`). Test environments (cut, ete, stg,
  drt …) are left out.
- **Upstream shows dependencies as APM records them.** Databases appear by type or schema (e.g. `oracle`), other
  services by host:port (e.g. `abp-data-api.gcp.cna.com:443`).
- **Shared host names can list callers twice.** When several services sit behind one host name (e.g.
  `ecs-data-api.gcp.cna.com`), the callers of that host appear for each of those services.
- **Section 3 charts show the top 15** dependencies and callers, failing first. The APM Service Map shows them all.
- **Callers are found only for services reached over HTTP on a CNA host name.** *Downstream* matches the host names a
  service answers on (its incoming requests); services reached only through queues (JMS), batch jobs, or services
  behind external host names show no callers.
- **Picking demo values:** see *MIM-V3-DEMO-VALUES.md* for queries that find the CIs and services that fill the most
  panels.
- **No user counts or criticality.** Neither APM nor the CMDB data has them, so *Downstream* ranks callers by the
  errors they see.
- **Empty health panels usually mean "no data for this CI", not "healthy".** *Server Health*, *Middleware
  Health*, *Database Health* and *Process Health* are empty when no server is chosen: the CI is not a server (e.g. a
  network device or an application service) and the Server control is empty. A chosen server with no data at all in
  the Health window still gets a *Server Health* row, "No data in window".
- **Changes show the planned start.** The data has no actual start or maintenance windows; an unsuccessful or
  emergency change shortly before the incident opened is the strongest lead.

### Clicks and links

- **Only some columns are clickable**, the ones with a link: Incident, Affected CI and Pri in *Active Incidents*;
  CI and Active Incident in *Escalate*; Change and CI in *Changes*; the Service health tiles and Downstream bars in section 3.
- **The click menu lists every link of that panel.** Kibana cannot attach a link to one column, so each link is
  labelled with the column it belongs to (e.g. "Open incident in ServiceNow — use on the Incident column"). Pick
  the one for the column you clicked. *Apply filter to current view* adds a filter instead (see above).
- **On Kibana 9.5, links only work on real fields.** Kibana 9.5 greys out ⊕ (*"…relies on a field created at query
  time"*) on any column the query creates or renames. MIM V3's link columns are built to stay real fields; if you
  edit a query, do not EVAL / RENAME / DISSECT into a link column (see *MIM-V3-LINKS-INVESTIGATION.md*).
- **Service names open the APM Service Map** (last hour, all environments), which draws the dependency diagram that a
  Kibana dashboard cannot.
- **The Applications Operations and Infra links in section 4** open those dashboards in a new tab.

### Speed and access

- **Speed is untested on real data.** The *Downstream* panel reads an hour of
  trace and dependency data each time it refreshes. If it is slow, collapse section 3 when you do not need it
  (Kibana does not load panels in a collapsed section) and report it so the queries can be narrowed.
- **Viewers need read access to every index the panels use**: `servicenow-*`, `cmdb-ci-relations*`,
  `metrics-*`, `metricbeat-*`, `logs-*`, `synthetics-*`, `traces-apm*` and the hidden
  `.ds-bridge-alerts-netcool-default-*`, `.ds-metrics-system.*` and `.slo-observability.*`. A panel the viewer cannot
  read shows an error, not "no results". The full list is in *MIM-V3-CHANGES-2026-10-16.md*.

---

## Panel reference

**Status:** ✅ ready on the confirmed data · ⚠️ ready, with the limit noted.

| Section | Panel | Status | What it shows | How it works |
|---|---|---|---|---|
| Control | **Incident** (first) | ✅ | The incident to work on; sections 2 and 3 follow its affected CI | Lists every active P1 / P2 / P3 as "number · affected CI", plus *(all incidents)*. A query variable (`?incident`); every section 2 and 3 query takes the CI from the part after " · " (and the number from the part before, for *Escalate*), so no extra lookup is needed. |
| Control | **CI** (second) | ✅ | The CI to investigate when no incident is picked | Lists every CI with a P1 / P2 / P3 opened in the last 31 days and every production (or blank-environment) server that sent CPU metrics in the last day (at most 10,000), plus *(no CI selected)*. A query variable (`?ci`), used by section 2 and 3 only while the Incident control is on *(all incidents)*. |
| Control | **Server** (third, new 18 Oct) | ✅ | The server for the health panels when neither the incident's CI nor the CI control is a server | Every production (or blank-environment) server that sent CPU metrics in the last day, plus *(no server selected)*. A query variable (`?server`). "Is a server" = a server class in the CMDB (the *Server View* classes) or CPU metrics in the Health window. |
| Control | **Health window** (fourth, new 18 Oct) | ✅ | The data window of the health panels (section 3) | Fixed list 15 minutes … 7 days, default 24 hours. A query variable (`?health_window`) applied inside each health query (`@timestamp >= NOW() - window`), so Elasticsearch filters on it. |
| 1 | **Active P1**, **P2 over 8 h**, **P3 over 24 h** | ✅ | Three count tiles: every active P1 (red); active P2s open longer than 8 h (amber); active P3s open longer than 24 h (blue) | Vega tiles, transparent, theme text colours. `servicenow-incidents-*`, same active rule and grouping as Active Incidents, so each tile equals that priority's rows in the table. Age = now − `opened_at`; 8 h / 24 h are the P2 / P3 targets of Time to Resolve vs Target. Fixed panel range Last 7 days (Kibana 9.5 applies a Vega panel's time range to its ES|QL query, so without it the tiles would follow the time picker). Replaced the Active P1 / P2 / P3 donut on 25 Oct. |
| 1 | **User base · ServiceNow** / **Real users · RUM** | ⚠️ | Two tiles, both "In progress" (replaced *Users impacted* and its demo number on 20 Oct) | The ServiceNow user base and RUM integrations are in progress; no user-count data in Elastic yet. |
| 1 | **P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)** | ✅ | Average age so far of the still-open incidents per opened day, P1 (red), P2 (amber) and P3 (blue), with dashed target lines; P1 / P2 on the left axis, P3 on the right, both from 0 h | P1 / P2 / P3 opened in the last 7 days (panel range Last 7 days) whose latest record is not On Hold, Resolved, Closed, Canceled or Cancelled; one value per incident, its age so far (now − `opened_at`). Points always drawn. Target lines are a reference-line layer. |
| 1 | **Open Alerts with No Incident** | ⚠️ | Netcool alerts still open on CIs with no open incident: CI, severity, alert, open for, last seen, times fired, ack, node, class, support group | `.ds-bridge-alerts-netcool-*` (CMDB-enriched `ci.name`) + `servicenow-incidents-*` (any priority, not closed). Open = the alert's latest record is not severity 0 or a resolution. Last 24 hours (alerts and open incidents seen in that window). CI links to the CMDB. **Limit:** alerts carry no incident number, so "no incident" means no open incident on the same CI; an alert whose node is not in the CMDB shows an empty CI and is listed. |
| 1 | **Active Incidents (P1 · P2 over 8 h · P3 over 24 h)** | ✅ | Every active P1, and the active P2s / P3s open longer than 8 h / 24 h (the rows the three tiles count), last 7 days: Incident, Pri, Affected CI, State, SLA, Assignment Group, Assignee, Assignee Email, Group Manager Name, Manager Email Id, Short description | Incidents joined to `servicenow-task-sla-*` on incident number. Breached = `task_has_breached` true on any non-cancelled SLA record; then breaching ≥ 75 % or due in 30 min, paused, within, met; none → "No SLA record". On Hold incidents left out (latest record). Full rules: *MIM-V3-SLA-CALCULATION.md*. Incident and CI link to ServiceNow. |
| 2 | **Alerts on this CI** | ⚠️ | The CI's Netcool alerts: Open / Cleared, severity, text, timing against the picked incident, first / last seen, times fired, ack | `.ds-bridge-alerts-netcool-*` on `ci.name` (or node "<CI>.cna.com"), one row per `netcool.identifier`; the picked incident's `opened_at` for the timing. Likely trigger = first seen ≤ 2 h before the incident opened. Last 7 days (panel range Last 1 month, for the incident record). Follows the Incident / CI controls only: the Server control belongs to section 3. **Limit:** a match by CI and time, not a recorded link (round 7: no incident or ticket field on the alerts). |
| 2 | **Escalate** | ✅ | One row per active P1 / P2 / P3 on the CI: CI, Active Incident, Priority, Class, Env, CI support group, Assignment Group, Assignee, Assignee Email, Group Manager Name, Manager Email Id | Incidents on the CI (or the one in the Incident control) plus the CMDB enrichment on its server metrics; last month. CI and Active Incident link to ServiceNow; no other column is clickable. A CI with no active P1 / P2 / P3 still shows one row with its owners. If an incident is picked whose CI is not the one in the CI control, Class / Env / support group come from the incident record and may show "—". |
| 2 | **Blast radius** | ✅ | Count of applications that depend on the CI, split into business applications, application services and (when any) application instances | `cmdb-ci-relations*` (the full ServiceNow relationship graph): links whose child is the CI and whose parent is an application class, not retired, not marked for deletion. Amber from 1, red from 5. Last 5 years (fixed). |
| 2 | **Applications related to this CI** | ✅ | Every application related to the CI, both directions: Application, Kind (business application / application service / application), How ("it consumes this CI", "this CI depends on it" …), Env | `cmdb-ci-relations*`; relationship from `type.name`. Merged from *Applications that depend on this CI* and *Application View* on 16 Oct. Business applications first, retired last. CI name matched exactly, in upper or in lower case. Last 5 years (fixed). The Application column no longer opens ServiceNow: the name comes from either side of the link, which Kibana 9.5 counts as created by the query. |
| 3 | **Server Health** | ✅ | One row per chosen server: Server, Status (Reporting / Silent / No data in window), Min. ago, CPU p90, Mem peak, Disk max — percentages green / amber / red | System CPU / memory / filesystem metrics matched on `ci.name` (equal to the host name), in the Health window. Amber ≥ 80 %, red ≥ 90 %; Silent = no data for 10 minutes. A chosen server with no data in the window gets a "No data in window" row (anchored by its CMDB links). Panel range Last 5 years for the CMDB links. Empty when no server is chosen. |
| 3 | **Middleware Health** | ✅ | Table: each middleware component on the CI, Down / Healthy badge (Down first), minutes since seen, server (links to the CMDB) | Middleware processes labelled by the Paladin monitoring enrichment (IBM MQ, IHS, JBoss, WebSphere) and Windows middleware services (IIS, MQ, Tomcat …). Down = stopped or silent > 10 min. The chosen server (see the Server control), in the Health window. |
| 3 | **Database Health** | ✅ | Table: each database on the CI, Down / Healthy badge (Down first), minutes since seen, server (links to the CMDB) | SQL Server metrics (`metricbeat-*` sql / mssql), plus processes and Windows services whose name is a database engine (SQL Server, Oracle, Db2, PostgreSQL, MySQL, MongoDB, Sybase, Informix). Down = stopped or silent > 10 min. Split from the former *Middleware / DB Health* (12 Oct). The chosen server (see the Server control), in the Health window. |
| 3 | **APM Services Health** | ✅ | APM services that sent data from the chosen server in the Health window: last data, environment | `metrics-apm.internal-*` matched on the APM host name (the server, upper or lower case). Health window (was a fixed 7 days). Production only. |
| 3 | **Synthetics Health** | ✅ | Monitors that target the CI: status now, down checks | `synthetics-*`, ping monitors enriched with the CI, or monitors whose URL is the CI's host name. Browser journeys are tagged with the application, so they do not appear here. The chosen server (see the Server control), in the Health window. |
| 3 | **Errors from the Logs** | ✅ | Warning-and-worse log lines from the CI, grouped by message | Syslog (server, WebSphere, JBoss, Red Hat, AIX, system), generic file logs, APM error and application logs, matched on `ci.name`; syslog severity code ≤ 4 or log level warning or worse; numbers replaced by # so repeats group together The chosen server (see the Server control), in the Health window. |
| 3 | **Process Health** | ✅ | Stopped / not-seen processes and services first, then healthy middleware | Windows services (Stopped = Automatic service not running) and Paladin-labelled middleware processes; Not seen = silent > 10 min The chosen server (see the Server control), in the Health window. |
| 2 | **Changes in the Last 7 Days on this CI** | ⚠️ | Changes active in the last 7 days on the CI, and on CMDB-linked CIs when the link was recorded in the same 7 days; the CI column shows which | `servicenow-change-requests` + `cmdb-ci-relations`. The selected CI's own changes first. Type (Emergency in red), category, state, outcome (close code), planned start, end, group. **Limit:** no actual start and no maintenance windows in the data; "application" category is the nearest thing to a release. Change and CI link to ServiceNow. |
| 2 | **Middleware View / Database View / Server View / Other related CIs** | ⚠️ | The CIs related to the selected CI in the CMDB, by class: related CI, type, relationship (both directions), env | `cmdb-ci-relations*` (the full relationship graph, since 16 Oct; before that `cmdb_app_dependencies_v2`, which missed many relationships). Exact ServiceNow classes from round 10 for Middleware / Database / Server; *Other related CIs* takes every remaining class. Retired CIs last, marked "· retired"; links marked for deletion left out. Last 5 years (fixed). **Limit:** CMDB data only, no live health; the name is not a link (it comes from either side of the relationship). |
| 3 | **Application Health** | ✅ | The production business applications related to the selected CI (all of them when no CI is selected): health from its services (Failing / Degraded / Healthy), servers (APM agent hosts of its services, last 15 minutes), failing and degraded service counts, worst service error rate, application error rate, transactions, APM number, support group | `metrics-apm.service_transaction.1m-*`, business application from the APM CMDB enrichment (`ci.name`, on 398 of 400 production services, round 10), matched to the CI through `cmdb-ci-relations*` (business applications linked to it) and `metrics-apm.internal-*` (services running on it). Health over the last hour, servers over the last 15 minutes (both in the query); panel range Last 5 years only for the CMDB links. Application links to the CMDB. |
| 4 | **Services of the Application** | ✅ | The services of the application in the Application control (all when none is picked), worst first, with the servers each runs on, error rate, latency, throughput | Same data, plus `metrics-apm.internal-*` (`host.name`, last 15 minutes) for the servers; click a service for its APM Service Map. Last hour. |
| 4 | **⬅ Upstream — what they depend on** | ✅ | Horizontal bars: calls per dependency, coloured Failing / Degraded / Healthy, label with % failed; top 15 | `metrics-apm.service_destination.1m-*`, production only. Failing ≥ 10 % failed calls, Degraded ≥ 1 %. Other services appear by host:port, as APM records them. |
| 4 | **Service health** | ✅ | One tile per service in scope: % of its transactions that failed, RAG background, business application | `metrics-apm.service_transaction.1m-*`; "(services on this CI)" = services whose APM host is the CI (`metrics-apm.internal-*`). Click a tile to open the APM Service Map. |
| 4 | **Downstream — who is impacted ➡** | ⚠️ | Horizontal bars: calls per calling service, coloured by the health of those calls; top 15 | Hosts the services in scope answer on (URL host of their incoming-request transactions, CNA host names only) matched to every production service's dependency addresses. Batch / messaging transactions and external hosts (Google storage, Okta …) are ignored. **Limit:** when several services share a host (an API gateway), callers of that host are listed for each of them. Click a bar to open that service's APM Service Map. |
| Control | **Service** | ✅ | The service(s) for section 3 | Production APM services seen in the last day, plus *(services on this CI)*. A query variable (`?service`) used only by section 3. |
| Control | **Application** | ✅ | The application for *Services of the Application* | Production business applications with APM data in the last day, plus *(all applications)*. A query variable (`?application`) used only by that panel. |
| 5 | **Applications Operations Dashboard** / **Infra Dashboard** | ✅ | Cards linking to the two dashboards | Text panels; the title of each card is the link (opens in a new tab). Addresses from `links.txt`. |

---

## Known limits and the enrichment they point to

| Limit | Why | What would fix it |
|---|---|---|
| No acknowledgement time (time to acknowledge) | Incidents carry no assigned / acknowledged timestamps; the response SLA says *whether* it was met, not *when* | ServiceNow: send assigned / acknowledged timestamps |
| No maintenance windows or releases | No outage-window or actual-start values on 148k change requests; no release or maintenance index | ServiceNow: export maintenance schedules and releases (or Caused-by-change on incidents) to Elastic |
| Alert → incident link is inferred | Netcool alerts carry no incident or ticket number (round 7, AI / AL); the ServiceNow event index holds ServiceNow table records (incidents, changes, CIs), not alerts | Netcool / ServiceNow integration: write the incident number back to the alert (e.g. Netcool's TTNumber), or send ServiceNow `em_alert` records with their incident |
| Change → incident link is inferred | Incidents have no "Caused by change"; matched on the same CI within 7 days | ServiceNow: send Caused-by-change |
| Major-incident and bridge flags unused | `is_major_incident` and `has_been_handled_by_bridge` are empty on all P1 / P2 for a year | ServiceNow integration mapping |
| Containerised services not linked to servers | APM reports pod names | Expected; use the application panels |
| Section 3 has no drawn node-and-arrow diagram | Kibana's Vega charts could draw one, but they cannot read the ES\|QL Service control (only the time range and filters), so the map could not follow the selected service | Section 3 is laid out left to right instead; click a service for the APM Service Map |
| Section 3 is empty for most incident CIs unless a service is picked | P1 / P2 are raised mostly against servers (Linux, AIX), network devices and application services; only servers with APM agents have services on them, and no incident CI is an APM business application (round 5, X and Y) | Pick the service in the Service control; longer term, record the affected business application / service on the incident |
| Estimated user base | Not in Elastic | Add the ServiceNow user-base field to the CI enrichment |
| The related-CI views and *Applications related to this CI* show CMDB data only, not live health | Kibana cannot combine the relationship records (5-year window) with live metrics (minutes) in one Lens panel | Option (b) in *MIM-V3-CI-VS-CMDB-RELATIONSHIPS.md*: a lookup copy of the relationship graph and an ES\|QL `LOOKUP JOIN` |

## Related dashboards (section 4): the links

The two links (link text only, 14 Oct) go to:

| Link | Address |
|---|---|
| Applications Operations Dashboard | https://kibana-prod.gcp.cna.com/app/r/s/b4Jas |
| Infra Dashboard | https://kibana-prod.gcp.cna.com/app/r/s/3A7f1 |

The addresses come from `links.txt` and are stored in `MIM V3.ndjson`. To change one, update both (the link text in
the two section-5 panels of `MIM V3.ndjson`), so a re-import keeps it. A quick fix in Kibana (**Edit** → panel **⋯** → **Edit**, change the address in
the round brackets of the title, **Save**) is lost at the next re-import.

## Importing

Import `MIM V3.ndjson` in **Stack Management → Saved objects → Import**, with *overwrite*. It contains only the
dashboard: every panel is ES|QL, so no data views are needed. MIM V1 and MIM V2 are untouched. A re-import replaces
any change made to MIM V3 in Kibana (layout, text, saved selections).

**Re-importing a new version over an older one.** If you had the old version open and changed anything (picked a
CI, changed the time range, entered edit mode), Kibana keeps those unsaved changes in the browser and lays them over
the imported version, including the old set of controls. New controls then go missing and the panels that use
them fail with *Unknown query parameter [incident]* (or *[service]*). To fix it:

1. Open MIM V3 and click **More (⋯) → Reset changes → Reset dashboard**. In edit mode, click **Exit edit** and
   discard first.
2. **Reload the page.** The CI, Incident and Service controls are all back.

Do **not** click Save while the dashboard is in that state: it would save the dashboard without the new controls.
If that has happened, import `MIM V3.ndjson` again (overwrite), then do steps 1 and 2.
