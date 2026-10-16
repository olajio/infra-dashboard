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

The dashboard has five sections and four controls:

| | What it covers | Time window |
|---|---|---|
| **Incident control** (top, first) | Picks the incident to work on. Each option is "number · affected CI" (e.g. *INC100 · kau1s054*); sections 2 to 4 then show that CI, and *Escalate* shows that incident. Lists the active P1 / P2 / P3; type to search. *(all incidents)* clears it. | — |
| **CI control** (top, second) | Picks a CI directly, when no incident is picked (an incident overrides it). Lists the CIs with P1 / P2 / P3 incidents in the last month; type to search. *(no CI selected)* clears it. | — |
| **Service control** (top) | Picks the service section 4 shows. *(services on this CI)* (the default) uses the production APM services running on the selected CI (the incident's affected CI, else the CI control); or type to pick any production service. | — |
| **1 · Major Incident Overview** | All active P1 / P2 / P3 incidents, all CIs | Fixed last month |
| **2 · Investigate the CI** | The picked incident's affected CI (or the CI picked in the CI control) only | Time picker (last 24 h by default), except where a panel says otherwise |
| **Application control** (top, fourth) | Picks the business application whose services *Services of the Application* lists. *(all applications)* (the default) lists every service, worst first. | — |
| **3 · Related CIs by Type (CMDB)** | The middleware, databases, servers and business applications related to the selected CI in the CMDB | None (CMDB data, no timestamp) |
| **4 · Application & Service Health, Dependencies** | Every application's health from its services; the services of the picked application; the service(s) from the Service control with their dependencies | Fixed last hour |
| **5 · Related dashboards** | Links to the Applications Operations and Infra dashboards | — |

---

## The walkthrough — telling the story

*Example used below: it is 09:00, the bridge line is quiet, and a P1 has just come in.*

### Step 1 — Spot the incident (section 1, top row)

The MIM lead opens MIM V3 and reads the top row from left to right.

- **Active P1 / P2 / P3** — a donut (transparent background): P1 (red), P2 (amber) and P3 (blue) incidents active now, with the total in
  the middle and each count beside it. P1, P2 and P3 are always listed (0 shown faded), and every priority with an
  active incident gets a visible slice, even one P2 next to hundreds of P3s; the numbers are the real counts.
- **Users impacted** — a placeholder number (2,500, demo only): *"Real count to be incorporated from
  ServiceNow and RUM"*.
- **P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)** — are we resolving within target? The
  average time to resolve the P1, P2 and P3 incidents opened each day, against the dashed target lines (red P1 4 h,
  amber P2 8 h, blue P3 24 h). Incidents still open count with their age so far, so a live P1 shows up on the day it
  was opened and its point climbs until it is resolved. A run of points above a line means incidents are taking
  longer than target. Both axes start at 0 h: P1 and P2 use the left axis, P3 its own right axis, so P3 values of a
  day or more do not flatten the P1 and P2 lines.

### Step 2 — Pick the incident (section 1, table)

**Active Incidents (P1 / P2 / P3)** lists every active P1, P2 and P3, P1 first and oldest first. For each one the lead sees:

- the **SLA**: Breached, Breaching, Paused or Within SLA, taken from ServiceNow's SLA records. How this is worked
  out is explained in *MIM-V3-SLA-CALCULATION.md*;
- the people: the **Assignment Group**, the **Assignee** and the **Group Manager**, each with an email address
  (`assigned_to.name` / `.email`, `assignment_group.manager.name` / `.email`).

*In the example, the P1 on `kau1s054` shows SLA Breached.* The lead clicks the incident to open it in ServiceNow if
needed, then **selects it in the Incident control** (*INC100 · kau1s054*): sections 2 to 4 now show its affected
CI, `kau1s054`. (Picking `kau1s054` in the CI control does the same; when an incident is picked, it wins.)

**Open Alerts with No Incident**, under the table, answers "is anything else broken that nobody has raised yet?":
Netcool alerts still open (latest record not a clear) on CIs with no open incident of any priority, critical first.
*A UPS battery fault on `lonely01` has been open 20 hours with no incident.* Pick its CI in the CI control to
investigate it, or raise the incident in ServiceNow.

### Step 3 — Measure the impact (section 2)

Section 2 now shows `kau1s054` only.

- **Blast radius** and **Applications that depend on this CI** — who is hurt if this CI is down. The count tile
  (amber from 1, red from 5) and the list of business applications and application services that depend on the CI
  in the CMDB, read as "<application> <how> this CI" (*Underwriting Tools PROD Runs on this CI*), with their
  environment and APM number. Pick one of them in the CI control to follow the chain upwards.
- **Applications on this CI** — the APM services that sent data from the CI (the server they run on) in the last 7
  days, most recent first. *policy-admin reported 3 minutes ago.* (The CMDB applications are in the dependency panels
  above.)
- **SLO Error Burn Rate** — are customers feeling it? The CI's own SLOs (marked ★) first, then every SLO burning its
  error budget right now. *policy-admin is burning at 38× — well past the 14.4× "page now" level.*
- **Synthetics Health** — does the CI answer from outside? *The ping monitor for the server is down.*

At this point the lead knows the incident is real, customer-facing and tied to one server.

### Step 4 — Confirm it is this CI (section 2)

- **Alerts on this CI** — the Netcool alerts on the CI, open ones and cleared ones, with when each started compared
  with the picked incident. **Likely trigger** = first seen up to 2 h before the incident opened (listed first);
  *Earlier* = longer before; *After* = once the incident was open. *A Major "CPU utilisation above 95 %" alert started
  28 minutes before INC100: the likely trigger.* Netcool does not record which incident an alert raised, so this is a
  match by CI and time.

- **Server Health** — the server's own telemetry: minutes since it last reported, CPU, memory, fullest disk, each
  green / amber / red. *CPU is at 92 % and the disk is 88 % full.*
- **Middleware Health** — every middleware component on the CI (IBM MQ, IBM HTTP Server, JBoss, WebSphere, Windows
  middleware services such as IIS) with a red *Down* / green *Healthy* badge, Down first, minutes since it last
  reported and the server it runs on. *The IBM HTTP Server has not reported for 25 minutes.* Click the server to
  open it in ServiceNow.
- **Database Health** — the same for databases (SQL Server metrics, and SQL Server, Oracle, Db2 … processes and
  Windows services). *The MSSQLSERVER service is stopped.*
- **Server Health** names the server on every tile, so it is clear which machine the numbers are for.

### Step 5 — Find the cause (section 2)

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

- declares a major incident if several applications are affected or an SLO is past the page-now level;
- opens the bridge and engages the CI support group, the incident's assignment group and the team that made the
  change (the Changes panel shows its group);
- shares the evidence: the burn-rate chart, the stopped service, the first error and the change.

### Step 6b — See what the CI is built from (section 3)

**Related CIs by Type** lists what the selected CI is related to in the CMDB, in four views: **Middleware** (Tomcat,
JBoss, WebLogic, WebSphere …), **Database** (Oracle, MS SQL, DB2, MySQL, PostgreSQL …), **Server** (Windows, Linux,
AIX, mainframe LPAR, ESX …) and **Application** (business applications). Both directions are shown: "this CI runs on
it" (the CI uses it) and "it runs on this CI" (it uses the CI), sorted by type, then name. *For the
application service Automated Claim Transaction PROD: Tomcat on vslrau1p276, an Oracle instance, two Linux servers
and the mainframe LPAR.* These are CMDB records, not live health: pick a server in the CI
control to see its health in section 2.

### Step 6c — Which application to look at (section 4, top row)

**Application Health** rates every production business application by the health of its services in the last hour,
worst first: Failing (a service with 10 % or more failed transactions), Degraded (1 % or more) or Healthy, with how
many services are failing or degraded. Pick an application in the **Application control**: **Services of the
Application** then lists its services, worst first, with error rate, latency and throughput; click a service to open
its APM Service Map.

### Step 7 — Size the blast radius (section 4)

Section 4 reads left to right, like a dependency map: what the service depends on → the service → who depends on it.
With the CI selected it shows the APM services running on the CI. If the CI is not a monitored server (an AIX box, a
network device, an application service), pick the affected service in the **Service** control instead.

- **⬅ Upstream — what they depend on**: a bar per database, queue or service they call; length = calls in the last
  hour, colour = health, and the label shows the share that failed. A red bar points at the cause. *The Oracle
  database the service calls: 38 % of calls failing.*
- **Service health**: a tile per service, green / amber / red by the share of its own transactions that failed, with
  its business application.
- **Downstream — who is impacted ➡**: a bar per production service that calls them, coloured by how many of those
  calls fail. This is the impact.
- **Business applications impacted**: the CMDB business applications of those callers, worst first, with their
  portfolio and support groups: the teams to warn.

Click a service (a tile or a downstream bar) and choose *Open service in APM Service Map* for the drawn dependency
diagram.

During the bridge the dashboard keeps refreshing every five minutes, so the lead can watch the SLO burn fall back
below 1×, the service return to Running and the ping monitor go green.

### Step 8 — Look wider (section 5)

If the problem is bigger than one CI or one service, the two links at the bottom open the **Applications Operations Dashboard**
(applications, services, SLOs) and the **Infra Dashboard** (servers and platforms across the estate) in a new tab,
so MIM V3 stays open on the bridge.

---

## Things to know

### Controls and selections

- **Use the controls, not cell clicks, to choose what to look at.** Clicking a value and choosing *Apply filter*
  (or *Filter for*) adds a dashboard filter that applies to **every** panel. For example, a filter on an incident
  number also hides the SLA records, so *Active Incidents* drops to the "(age)" estimate. Remove such filters with
  the **×** on the filter pill under the search bar.
- **The CI control only lists CIs with a P1 / P2 / P3 opened in the last 31 days.** A CI outside that list cannot be
  picked. Type in the control to search the list.
- **An incident overrides the CI control.** With an incident picked, sections 2 to 4 follow its affected CI whatever
  the CI control says. Set the Incident control back to *(all incidents)* to use the CI control again.
- **A ⚠ next to the picked incident means it is no longer active.** The Incident control lists active P1 / P2 / P3 only;
  once the picked incident is resolved, *Escalate* shows no rows for it, while sections 2 to 4 keep showing its CI.
  Pick another incident or *(all incidents)*.
- **The controls cannot be left empty.** Each has a "nothing selected" option instead: *(no CI selected)*,
  *(all incidents)*, *(services on this CI)*.
- **Each control drives specific panels.** CI → section 2 and, through *(services on this CI)*, section 4.
  Incident → *Escalate* only. Service → section 4 only. Section 1 ignores all three.
- **For most incident CIs, you'll need to pick the service yourself.** Round 5 showed most P1 / P2s are raised
  against Linux / AIX servers, network devices or application services. Only servers with APM agents have services
  on them, so for the rest section 4 stays empty until you choose a service in the Service control.
- **Selections are unsaved changes.** Picking a CI or an incident does not change the saved dashboard. Do not click
  *Save* with a CI picked unless you want every viewer to open MIM V3 on that CI. Use **More (⋯) → Reset changes**
  to go back to the saved state.

### Time windows

- **A badge on a panel means a fixed window.** "Last 1 month", "Last 7 days", "Last 30 days" and "Last 1 hour"
  panels ignore the time picker. Panels without a badge follow the time picker.
- **Section 1** is fixed to the last month (*Open Alerts with No Incident*: last 24 hours). **Section 4** is fixed to
  the last hour. **Section 2** follows the time picker (last 24 h by default), except *Escalate* (last month),
  *Alerts on this CI*, *Applications on this CI* and *Changes* (last 7 days).
- **Changes shows few linked CIs.** ServiceNow stores a CMDB relationship record only when the relationship changes
  (129k of 34M in a week, round 7 AN), so within 7 days *Changes* mostly finds changes on the CI itself. The CMDB dependency panels (*Blast radius*,
  *Applications that depend on this CI* and the four views in section 3) have no time window at all: the dependency index has no timestamp.
- **Set the time picker to suit the question in section 2.** Use the last 15 minutes to see the CI's state *now*:
  *Server Health* shows CPU p90 and peak memory over the whole range, so a 24-hour range can show yesterday's peak.
  Use a range starting before the incident opened to see the first errors in the logs.
- **The dashboard refreshes every 5 minutes.** Click **Refresh** for an immediate update.

### Reading the numbers

- **"(age)" in the SLA column is an estimate.** It appears when the incident has no ServiceNow SLA record: its age
  is compared with P1 4 h / P2 8 h / P3 24 h. Full rules: *MIM-V3-SLA-CALCULATION.md*.
- **Active** everywhere means priority 1, 2 or 3 and state not Resolved, Closed, Canceled or Cancelled.
- **The trend's target lines** are P1 4 h, P2 8 h and P3 24 h, the same targets as the SLA age rule. Each incident
  counts once, on the day it was opened: resolved ones by ServiceNow's `resolution_time`, open ones by their age so
  far (a minimum that grows until they are resolved). Canceled incidents are left out.
- **One slow incident moves a day's average.** On days with one or two P1s, a single long incident can put the point
  far above the line.
- **Health thresholds.** Server Health: amber from 80 %, red from 90 %, red if the server has been silent more than
  10 minutes. Middleware, Database and Process Health: *Down* / *Not seen* after 10 minutes without data. Section 4: *Failing*
  = 10 % or more of calls failed in the last hour, *Degraded* = 1 % or more.
- **Check the call count before trusting an error %.** In section 4, a service with 20 calls in the hour and 2
  failures shows 10 % *Failing*; the *Calls* / *Per min* columns show how much traffic is behind the figure.
- **Section 4 is production only** (`prd1`, `prd2`, `prd`, `prod`, `production`). Test environments (cut, ete, stg,
  drt …) are left out.
- **Upstream shows dependencies as APM records them.** Databases appear by type or schema (e.g. `oracle`), other
  services by host:port (e.g. `abp-data-api.gcp.cna.com:443`).
- **Shared host names can list callers twice.** When several services sit behind one host name (e.g.
  `ecs-data-api.gcp.cna.com`), the callers of that host appear for each of those services.
- **Section 4 charts show the top 15** dependencies and callers, failing first. The APM Service Map shows them all.
- **Callers are found only for services reached over HTTP on a CNA host name.** *Downstream* matches the host names a
  service answers on (its incoming requests); services reached only through queues (JMS), batch jobs, or services
  behind external host names show no callers.
- **Picking demo values:** see *MIM-V3-DEMO-VALUES.md* for queries that find the CIs and services that fill the most
  panels.
- **No user counts or criticality.** Neither APM nor the CMDB data has them, so *Business applications impacted*
  ranks by the errors the callers see.
- **Empty panels in section 2 usually mean "no data for this CI", not "healthy".** *Server Health*, *Middleware
  Health*, *Database Health* and *Process Health* are empty when the CI is not a monitored server (e.g. a network device or an
  application service).
- **The SLO panel is not filtered to the CI's services.** It shows the CI's own per-CI SLOs (★) first, then every
  SLO burning ≥ 1×. Compare the names with *Applications on this CI*.
- **Changes show the planned start.** The data has no actual start or maintenance windows; an unsuccessful or
  emergency change shortly before the incident opened is the strongest lead.

### Clicks and links

- **Only some columns are clickable**, the ones with a link: Incident, Affected CI and Pri in *Active Incidents*;
  CI and Active Incident in *Escalate*; Change and CI in *Changes*; the Service health tiles and Downstream bars in section 4; business
  applications in *Business applications impacted*.
- **The click menu lists every link of that panel.** Kibana cannot attach a link to one column, so each link is
  labelled with the column it belongs to (e.g. "Open incident in ServiceNow — use on the Incident column"). Pick
  the one for the column you clicked. *Apply filter to current view* adds a filter instead (see above).
- **On Kibana 9.5, links only work on real fields.** Kibana 9.5 greys out ⊕ (*"…relies on a field created at query
  time"*) on any column the query creates or renames. MIM V3's link columns are built to stay real fields; if you
  edit a query, do not EVAL / RENAME / DISSECT into a link column (see *MIM-V3-LINKS-INVESTIGATION.md*).
- **Service names open the APM Service Map** (last hour, all environments), which draws the dependency diagram that a
  Kibana dashboard cannot.
- **The Applications Operations and Infra links in section 5** open those dashboards in a new tab.

### Speed and access

- **Speed is untested on real data.** The *Downstream* and *Business applications impacted* panels read an hour of
  trace and dependency data each time they refresh. If they are slow, collapse section 4 when you do not need it
  (Kibana does not load panels in a collapsed section) and report it so the queries can be narrowed.
- **Viewers need read access to every index the panels use**: `servicenow-*`, `cmdb-ci-relations*`,
  `cmdb_app_dependencies_v2`, `metrics-*`, `metricbeat-*`, `logs-*`, `synthetics-*`, `traces-apm*` and the hidden
  `.ds-bridge-alerts-netcool-default-*`, `.ds-metrics-system.*` and `.slo-observability.*`. A panel the viewer cannot
  read shows an error, not "no results". The full list is in *MIM-V3-CHANGES-2026-10-16.md*.

---

## Panel reference

**Status:** ✅ ready on the confirmed data · ⚠️ ready, with the limit noted.

| Section | Panel | Status | What it shows | How it works |
|---|---|---|---|---|
| Control | **Incident** (first) | ✅ | The incident to work on; sections 2 to 4 follow its affected CI | Lists every active P1 / P2 / P3 as "number · affected CI", plus *(all incidents)*. A query variable (`?incident`); every section 2 and 3 query takes the CI from the part after " · " (and the number from the part before, for *Escalate*), so no extra lookup is needed. |
| Control | **CI** (second) | ✅ | The CI to investigate when no incident is picked | Lists every CI with a P1 / P2 / P3 opened in the last 31 days, plus *(no CI selected)*. A query variable (`?ci`), used by sections 2 to 4 only while the Incident control is on *(all incidents)*. |
| 1 | **Active P1 / P2 / P3** | ✅ | Donut: active P1 (red), P2 (amber) and P3 (blue), total in the middle | Vega chart, transparent, text in Kibana's theme colours (reads in light and dark mode); P1 / P2 / P3 colours match the priority badges in Active Incidents. `servicenow-incidents-*`, active P1 / P2 / P3, one count per incident, same active rule and same fixed panel range (Last 1 month) as Active Incidents. Kibana 9.5 applies a Vega panel's time range to its ES|QL query by itself, so without the fixed range the donut followed the dashboard's time picker. Every non-zero priority gets at least 6 % of the ring (a smaller slice was hidden by the gap between slices). |
| 1 | **Users impacted** | ⚠️ | Placeholder number (2,500, demo only), "Real count to be incorporated from ServiceNow and RUM" | No user-count data in Elastic yet. |
| 1 | **P1 / P2 / P3 Time to Resolve vs Target (P1 4 h · P2 8 h · P3 24 h)** | ✅ | Average time to resolve per opened day, P1 (red), P2 (amber) and P3 (blue), with dashed target lines; P1 / P2 on the left axis, P3 on the right, both from 0 h | P1 / P2 / P3 opened in the last 30 days, one value per incident: `resolution_time` (ServiceNow's opened → resolved seconds) or resolved_at − opened_at; still open → age so far; canceled left out. Points always drawn. Target lines are a reference-line layer. |
| 1 | **Open Alerts with No Incident** | ⚠️ | Netcool alerts still open on CIs with no open incident: CI, severity, alert, open for, last seen, count, ack, node, class, support group | `.ds-bridge-alerts-netcool-*` (CMDB-enriched `ci.name`) + `servicenow-incidents-*` (any priority, not closed). Open = the alert's latest record is not severity 0 or a resolution. Last 24 hours (alerts and open incidents seen in that window). CI links to the CMDB. **Limit:** alerts carry no incident number, so "no incident" means no open incident on the same CI; an alert whose node is not in the CMDB shows an empty CI and is listed. |
| 1 | **Active Incidents (P1 / P2 / P3)** | ✅ | Every active P1 / P2 / P3: Incident, Pri, Affected CI, State, SLA, Assignment Group, Assignee, Assignee Email, Group Manager Name, Manager Email Id | Incidents joined to `servicenow-task-sla` (real SLA: breached, breaching ≥ 75 % or due in 30 min, paused). No SLA record → age rule (P1 4 h, P2 8 h, P3 24 h), marked "(age)". Full rules: *MIM-V3-SLA-CALCULATION.md*. Incident and CI link to ServiceNow. |
| 2 | **Alerts on this CI** | ⚠️ | The CI's Netcool alerts: Open / Cleared, severity, text, timing against the picked incident, first / last seen, count, ack | `.ds-bridge-alerts-netcool-*` on `ci.name` (or node "<CI>.cna.com"), one row per `netcool.identifier`; the picked incident's `opened_at` for the timing. Likely trigger = first seen ≤ 2 h before the incident opened. Last 7 days. **Limit:** a match by CI and time, not a recorded link (round 7: no incident or ticket field on the alerts). |
| 2 | **Escalate** | ✅ | One row per active P1 / P2 / P3 on the CI: CI, Active Incident, Priority, Class, Env, CI support group, Assignment Group, Assignee, Assignee Email, Group Manager Name, Manager Email Id | Incidents on the CI (or the one in the Incident control) plus the CMDB enrichment on its server metrics; last month. CI and Active Incident link to ServiceNow; no other column is clickable. A CI with no active P1 / P2 / P3 still shows one row with its owners. If an incident is picked whose CI is not the one in the CI control, Class / Env / support group come from the incident record and may show "—". |
| 2 | **Blast radius** | ✅ | Count of applications that depend on the CI, split into application services and business applications | `cmdb_app_dependencies_v2`: records whose child is the CI and whose parent is a business application or application service, not retired. Amber from 1, red from 5. No time window. |
| 2 | **Applications that depend on this CI** | ✅ | Those applications: kind, how they depend ("Runs on", "Depends on", "Consumes" …), env, APM number | Same records; relationship names from the ServiceNow relationship-type IDs (round 6, AD). Business applications first. Application links to the CMDB. |
| 2 | **Server Health** | ✅ | Minutes since last data, CPU p90, peak memory, fullest disk — RAG coloured, the server named on each tile | System metrics matched on `ci.name` (equal to the host name). Amber ≥ 80 %, red ≥ 90 %; red if silent > 10 min. Empty if the CI is not a monitored server. |
| 2 | **Middleware Health** | ✅ | Table: each middleware component on the CI, Down / Healthy badge (Down first), minutes since seen, server (links to the CMDB) | Middleware processes labelled by the Paladin monitoring enrichment (IBM MQ, IHS, JBoss, WebSphere) and Windows middleware services (IIS, MQ, Tomcat …). Down = stopped or silent > 10 min. |
| 2 | **Database Health** | ✅ | Table: each database on the CI, Down / Healthy badge (Down first), minutes since seen, server (links to the CMDB) | SQL Server metrics (`metricbeat-*` sql / mssql), plus processes and Windows services whose name is a database engine (SQL Server, Oracle, Db2, PostgreSQL, MySQL, MongoDB, Sybase, Informix). Down = stopped or silent > 10 min. Split from the former *Middleware / DB Health* (12 Oct). |
| 2 | **Applications on this CI** | ✅ | APM services that sent data from the CI in the last 7 days: last data, environment | `metrics-apm.internal-*` matched on the APM host name (the CI, upper or lower case). Last 7 days. The CMDB part moved to the dependency panels (14 Oct). |
| 2 | **SLO Error Burn Rate** | ⚠️ | 1-hour burn rate per SLO: page now (≥ 14.4×), burning (≥ 1×), on track | `.slo-observability.summary-*` (173 Kibana SLOs). The CI's own per-CI SLOs (★) first, then every SLO burning ≥ 1×. **Limit:** Kibana cannot combine SLO summaries with timestamped data in one panel, so for service SLOs it cannot filter to "services on this CI" — compare names with *Applications on this CI*. Viewers need read access to the hidden `.slo-observability.*` indices. |
| 2 | **Synthetics Health** | ✅ | Monitors that target the CI: status now, down checks | `synthetics-*`, ping monitors enriched with the CI, or monitors whose URL is the CI's host name. Browser journeys are tagged with the application, so they do not appear here. |
| 2 | **Errors from the Logs** | ✅ | Warning-and-worse log lines from the CI, grouped by message | Syslog (server, WebSphere, JBoss, Red Hat, AIX, system), generic file logs, APM error and application logs, matched on `ci.name`; syslog severity code ≤ 4 or log level warning or worse; numbers replaced by # so repeats group together |
| 2 | **Process Health** | ✅ | Stopped / not-seen processes and services first, then healthy middleware | Windows services (Stopped = Automatic service not running) and Paladin-labelled middleware processes; Not seen = silent > 10 min |
| 2 | **Changes in the Last 7 Days on this CI** | ⚠️ | Changes active in the last 7 days on the CI, and on CMDB-linked CIs when the link was recorded in the same 7 days; the CI column shows which | `servicenow-change-requests` + `cmdb-ci-relations`. The selected CI's own changes first. Type (Emergency in red), category, state, outcome (close code), planned start, end, group. **Limit:** no actual start and no maintenance windows in the data; "application" category is the nearest thing to a release. Change and CI link to ServiceNow. |
| 3 | **Middleware View / Database View / Server View / Application View** | ⚠️ | The CIs related to the selected CI in the CMDB, by class: related CI, type, relationship (both directions), env (CMDB status removed 16 Oct) | `cmdb_app_dependencies_v2`, exact ServiceNow classes from round 10 (AU / AV) for the lists in `relationships1.png` / `relatiosnhips2.png`; retired CIs left out. Follows the Incident / CI controls. **Limit:** CMDB data only, no live health (the index has no timestamp); the name is not a link (it comes from either side of the relationship, which Kibana 9.5 counts as created by the query). Built by a colleague, fixed 15 Oct (*MIM-V3-REVIEW-UPDATED-DASHBOARD.md*). |
| 4 | **Application Health** | ✅ | Every production business application: health from its services (Failing / Degraded / Healthy), failing and degraded service counts, worst service error rate, application error rate, transactions, APM number, support group | `metrics-apm.service_transaction.1m-*`, business application from the APM CMDB enrichment (`ci.name`, on 398 of 400 production services, round 10). Last hour. Application links to the CMDB. |
| 4 | **Services of the Application** | ✅ | The services of the application in the Application control (all when none is picked), worst first, with error rate, latency, throughput | Same data; click a service for its APM Service Map. Last hour. |
| 4 | **⬅ Upstream — what they depend on** | ✅ | Horizontal bars: calls per dependency, coloured Failing / Degraded / Healthy, label with % failed; top 15 | `metrics-apm.service_destination.1m-*`, production only. Failing ≥ 10 % failed calls, Degraded ≥ 1 %. Other services appear by host:port, as APM records them. |
| 4 | **Service health** | ✅ | One tile per service in scope: % of its transactions that failed, RAG background, business application | `metrics-apm.service_transaction.1m-*`; "(services on this CI)" = services whose APM host is the CI (`metrics-apm.internal-*`). Click a tile to open the APM Service Map. |
| 4 | **Downstream — who is impacted ➡** | ⚠️ | Horizontal bars: calls per calling service, coloured by the health of those calls; top 15 | Hosts the services in scope answer on (URL host of their incoming-request transactions, CNA host names only) matched to every production service's dependency addresses. Batch / messaging transactions and external hosts (Google storage, Okta …) are ignored. **Limit:** when several services share a host (an API gateway), callers of that host are listed for each of them. Click a bar to open that service's APM Service Map. |
| 4 | **Business applications impacted** | ⚠️ | The callers' CMDB business applications, worst first, with portfolio and support group | From the APM CMDB enrichment on the callers. **Limit:** no user counts or criticality (not in APM or the CMDB data). Click to open the application in the CMDB. |
| Control | **Service** | ✅ | The service(s) for section 4 | Production APM services seen in the last day, plus *(services on this CI)*. A query variable (`?service`) used only by section 4. |
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
| SLO panel not filtered to the CI's services | Kibana limitation (see *KIBANA-LIMITATIONS.md*) | Group SLOs by `ci.name` in Kibana where it makes sense — those follow the CI control |
| Major-incident and bridge flags unused | `is_major_incident` and `has_been_handled_by_bridge` are empty on all P1 / P2 for a year | ServiceNow integration mapping |
| Containerised services not linked to servers | APM reports pod names | Expected; use the application / SLO panels |
| Section 4 has no drawn node-and-arrow diagram | Kibana's Vega charts could draw one, but they cannot read the ES\|QL Service control (only the time range and filters), so the map could not follow the selected service | Section 4 is laid out left to right instead; click a service for the APM Service Map |
| Section 4 is empty for most incident CIs unless a service is picked | P1 / P2 are raised mostly against servers (Linux, AIX), network devices and application services; only servers with APM agents have services on them, and no incident CI is an APM business application (round 5, X and Y) | Pick the service in the Service control; longer term, record the affected business application / service on the incident |
| Estimated user base | Not in Elastic | Add the ServiceNow user-base field to the CI enrichment |
| The related-CI views (section 3) and *Applications that depend on this CI* show CMDB data only, not live health | `cmdb_app_dependencies_v2` has no timestamp, and Kibana filters every row of a Lens panel on the timestamp of the other indices it reads (incidents, metrics), so the dependency records would vanish | Add an `@timestamp` (sync time) to the dependency index records, e.g. a `set` processor in its ingest pipeline. A live version (server reporting / CPU, APM error rate, active P1 / P2 per item) was built and tested on 9 Oct and can be added back |

## Related dashboards (section 5): the links

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
