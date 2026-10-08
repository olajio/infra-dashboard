# MIM V3 — how a Major Incident Manager uses the dashboard

**File:** `MIM V3.ndjson` · **Dashboard:** MIM V3 · **Built from:** Naveen's MIM sketch (`naveen-mim suggestion.png`)
**Default time range:** last 24 hours, refreshing every 5 minutes

MIM V3 answers four questions, in order:

1. **What is going on?** Every active P1 / P2 incident across the estate, how old it is, where it sits and what
   state it is in.
2. **Why, and how bad?** Everything Elastic knows about the one CI behind the incident: its own health, the
   middleware and processes on it, the applications that depend on it, whether customers are feeling it, what the
   logs say and what changed on it recently.
3. **Who do we call?** The CI's support group and the group each incident is with, with one-click links into
   ServiceNow.
4. **What else is hit?** The services behind the CI, what they depend on, which services call them and which
   business applications those belong to.

The dashboard has four sections and three controls:

| | What it covers | Time window |
|---|---|---|
| **CI control** (top) | Picks the CI that section 2 investigates. Lists the CIs with P1 / P2 incidents in the last month; type to search. *(no CI selected)* clears it. | — |
| **Incident control** (top) | Narrows the *Escalate* panel and the *Longest open P1* tile of *At a Glance* to one active P1 / P2 incident. *(all incidents)* clears it. No other panel uses it. | — |
| **Service control** (top) | Picks the service section 3 shows. *(services on this CI)* (the default) uses the production APM services running on the CI in the CI control; or type to pick any production service. | — |
| **1 · Major Incident Overview** | All active P1 / P2 incidents, all CIs | Fixed last month |
| **2 · Investigate the CI** | The CI picked in the control only | Time picker (last 24 h by default), except where a panel says otherwise |
| **3 · Service Dependency & Blast Radius** | The service(s) from the Service control | Fixed last hour |
| **4 · Related dashboards** | Links to the SRE and Infra dashboards | — |

---

## The walkthrough — telling the story

*Example used below: it is 09:00, the bridge line is quiet, and a P1 has just come in.*

### Step 1 — Spot the incident (section 1, top row)

The MIM lead opens MIM V3 and reads the top row from left to right.

- **Active P1 / P2 at a Glance** — six tiles that sum up the state of play:
  - **Longest open P1**: how long the longest-running active P1 has been open, with its number and CI. Pick an
    incident in the Incident control and the tile shows that incident instead.
  - **Active P1 · P2**: how many are open now.
  - **Past target time**: P1 open 4 h or more, or P2 open 8 h or more.
  - **Open more than 24 h**: candidates for escalation, whatever else is happening today.
  - **Hotspot CI**: the CI with the most active P1 / P2. Several incidents on one CI is very likely the centre of the
    problem. *In the example, three incidents point at `kau1s054`.* Shows "—" when no CI has more than one.
  - **Not picked up (New)**: incidents nobody has picked up yet.
- **P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)** — are we resolving within target? The average time to
  resolve the P1 and P2 incidents opened each day, against the dashed target lines (red P1 4 h, amber P2 8 h). A
  run of points above a line means incidents are taking longer than target. Hover a point for how many incidents
  are behind it.

### Step 2 — Pick the incident (section 1, table)

**Active Incidents (P1 / P2)** lists every active P1 / P2, P1 first and oldest first. For each one the lead sees:

- the **SLA**: Breached, Breaching, Paused or Within SLA, taken from ServiceNow's SLA records. How this is worked
  out is explained in *MIM-V3-SLA-CALCULATION.md*;
- the assignment group, the age and the description.

*In the example, the P1 on `kau1s054` shows SLA Breached.* The lead clicks the incident to open it in ServiceNow if
needed, then **selects `kau1s054` in the CI control**.

### Step 3 — Measure the impact (section 2)

Section 2 now shows `kau1s054` only.

- **Applications on this CI** — the blast radius. The applications and software that run on or depend on the CI
  (from the CMDB relationships) and the APM services sending data from it. *Three applications live on this
  server, including the policy-admin service.*
- **SLO Error Burn Rate** — are customers feeling it? The CI's own SLOs (marked ★) first, then every SLO burning its
  error budget right now. *policy-admin is burning at 38× — well past the 14.4× "page now" level.*
- **Synthetics Health** — does the CI answer from outside? *The ping monitor for the server is down.*

At this point the lead knows the incident is real, customer-facing and tied to one server.

### Step 4 — Confirm it is this CI (section 2)

- **Infra Health** — the server's own telemetry: minutes since it last reported, CPU, memory, fullest disk, each
  green / amber / red. *CPU is at 92 % and the disk is 88 % full.*
- **Middleware / DB Health** — the SQL Server, IBM MQ, IBM HTTP Server, JBoss, WebSphere and Windows middleware
  services on the CI: healthy vs down. *Two components are down.*

### Step 5 — Find the cause (section 2)

- **Process Health** — which process or service actually stopped. *The SQL Server Windows service is Stopped and an
  IBM HTTP Server instance has not been seen for 25 minutes.*
- **Errors from the Logs** — the warning-and-worse lines from the CI's server and application logs, grouped by
  message. *"MSSQLSERVER terminated unexpectedly", followed by SQL timeouts in policy-admin.*
- **Changes on this CI and linked CIs** — was there a change just before? On the CI itself and on CIs linked to it
  in the CMDB (its ESX host, cluster, switch, applications). *An emergency change on `kau1s054` ended unsuccessful
  two hours before the incident opened.*

The story is now complete: an unsuccessful emergency change stopped SQL Server on `kau1s054`, which took down
policy-admin and the applications that depend on it.

### Step 6 — Escalate

**Escalate** gives the lead the people to call without leaving the dashboard. It has one row per active P1 / P2
incident on the CI, showing the incident, its priority and its assignment group, next to the CI's class,
environment and CMDB support group. With several incidents on the CI, pick one in the **Incident control** to show
only that one. Only the CI and the Active Incident are links; clicking either opens it in ServiceNow.

The lead now:

- declares a major incident if several applications are affected or an SLO is past the page-now level;
- opens the bridge and engages the CI support group, the incident's assignment group and the team that made the
  change (the Changes panel shows its group);
- shares the evidence: the burn-rate chart, the stopped service, the first error and the change.

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
  calls fail. This is the impact.
- **Business applications impacted**: the CMDB business applications of those callers, worst first, with their
  portfolio and support groups: the teams to warn.

Click a service (a tile or a downstream bar) and choose *Open service in APM Service Map* for the drawn dependency
diagram.

During the bridge the dashboard keeps refreshing every five minutes, so the lead can watch the SLO burn fall back
below 1×, the service return to Running and the ping monitor go green.

### Step 8 — Look wider (section 4)

If the problem is bigger than one CI or one service, the two cards at the bottom open the **SRE Dashboard**
(applications, services, SLOs) and the **Infra Dashboard** (servers and platforms across the estate) in a new tab,
so MIM V3 stays open on the bridge.

---

## Things to know

### Controls and selections

- **Use the controls, not cell clicks, to choose what to look at.** Clicking a value and choosing *Apply filter*
  (or *Filter for*) adds a dashboard filter that applies to **every** panel. For example, a filter on an incident
  number also hides the SLA records, so *Active Incidents* drops to the "(age)" estimate. Remove such filters with
  the **×** on the filter pill under the search bar.
- **The CI control only lists CIs with a P1 / P2 opened in the last 31 days.** A CI outside that list cannot be
  picked. Type in the control to search the list.
- **A ⚠ next to the picked incident means it is no longer active.** The Incident control lists active P1 / P2 only;
  once the picked incident is resolved, *Escalate* shows no rows for it. Pick another incident or *(all incidents)*.
- **The controls cannot be left empty.** Each has a "nothing selected" option instead: *(no CI selected)*,
  *(all incidents)*, *(services on this CI)*.
- **Each control drives specific panels.** CI → section 2 and, through *(services on this CI)*, section 3.
  Incident → *Escalate* and the *Longest open P1* tile only. Service → section 3 only. Section 1 ignores all three.
- **For most incident CIs, you'll need to pick the service yourself.** Round 5 showed most P1 / P2s are raised
  against Linux / AIX servers, network devices or application services. Only servers with APM agents have services
  on them, so for the rest section 3 stays empty until you choose a service in the Service control.
- **Selections are unsaved changes.** Picking a CI or an incident does not change the saved dashboard. Do not click
  *Save* with a CI picked unless you want every viewer to open MIM V3 on that CI. Use **More (⋯) → Reset changes**
  to go back to the saved state.

### Time windows

- **A badge on a panel means a fixed window.** "Last 1 month", "Last 7 days", "Last 30 days" and "Last 1 hour"
  panels ignore the time picker. Panels without a badge follow the time picker.
- **Section 1** is fixed to the last month. **Section 3** is fixed to
  the last hour. **Section 2** follows the time picker (last 24 h by default), except *Escalate* (last month),
  *Applications on this CI* and *Changes* (last 30 days).
- **Set the time picker to suit the question in section 2.** Use the last 15 minutes to see the CI's state *now*:
  *Infra Health* shows CPU p90 and peak memory over the whole range, so a 24-hour range can show yesterday's peak.
  Use a range starting before the incident opened to see the first errors in the logs.
- **The dashboard refreshes every 5 minutes.** Click **Refresh** for an immediate update.

### Reading the numbers

- **"(age)" in the SLA column is an estimate.** It appears when the incident has no ServiceNow SLA record: its age
  is compared with P1 4 h / P2 8 h (dashboard defaults, to be confirmed). Full rules: *MIM-V3-SLA-CALCULATION.md*.
- **Active** everywhere means priority 1 or 2 and state not Resolved, Closed, Canceled or Cancelled.
- **"Longest open P1" counts from the incident's opened time**, not from when a major incident was declared (no such
  time exists in the data).
- **"Past target time" and the trend use the same targets**: P1 4 h, P2 8 h, the dashboard's age rule (to be
  confirmed against CNA's resolution targets). "Past target time" counts incidents still open; the trend plots only
  resolved incidents, by the day they were opened, using ServiceNow's `resolution_time`.
- **One slow incident moves a day's average.** On days with one or two P1s, a single long incident can put the point
  far above the line; hover the point to see how many incidents it averages.
- **Health thresholds.** Infra Health: amber from 80 %, red from 90 %, red if the server has been silent more than
  10 minutes. Middleware and Process Health: *Down* / *Not seen* after 10 minutes without data. Section 3: *Failing*
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
- **No user counts or criticality.** Neither APM nor the CMDB data has them, so *Business applications impacted*
  ranks by the errors the callers see.
- **Empty panels in section 2 usually mean "no data for this CI", not "healthy".** *Infra Health*, *Middleware /
  DB Health* and *Process Health* are empty when the CI is not a monitored server (e.g. a network device or an
  application service).
- **The SLO panel is not filtered to the CI's services.** It shows the CI's own per-CI SLOs (★) first, then every
  SLO burning ≥ 1×. Compare the names with *Applications on this CI*.
- **Changes show the planned start.** The data has no actual start or maintenance windows; an unsuccessful or
  emergency change shortly before the incident opened is the strongest lead.

### Clicks and links

- **Only some columns are clickable**, the ones with a link: Incident, Affected CI and Pri in *Active Incidents*;
  CI and Active Incident in *Escalate*; Change and CI in *Changes*; the Service health tiles and Downstream bars in section 3; business
  applications in *Business applications impacted*.
- **The click menu lists every link of that panel.** Kibana cannot attach a link to one column, so each link is
  labelled with the column it belongs to (e.g. "Open incident in ServiceNow — use on the Incident column"). Pick
  the one for the column you clicked. *Apply filter to current view* adds a filter instead (see above).
- **Service names open the APM Service Map** (last hour, all environments), which draws the dependency diagram that a
  Kibana dashboard cannot.
- **The SRE and Infra cards in section 4** open those dashboards in a new tab.

### Speed and access

- **Speed is untested on real data.** The *Downstream* and *Business applications impacted* panels read an hour of
  trace and dependency data each time they refresh. If they are slow, collapse section 3 when you do not need it
  (Kibana does not load panels in a collapsed section) and report it so the queries can be narrowed.
- **Viewers need read access to every index the panels use**: `servicenow-*`, `cmdb-ci-relations*`, `metrics-*`,
  `metricbeat-*`, `logs-*`, `synthetics-*`, `traces-apm*` and the hidden `.slo-observability.*`. A panel the viewer
  cannot read shows an error, not "no results".

---

## Panel reference

**Status:** ✅ ready on the confirmed data · ⚠️ ready, with the limit noted.

| Section | Panel | Status | What it shows | How it works |
|---|---|---|---|---|
| Control | **CI** | ✅ | The CI to investigate | Lists every CI with a P1 / P2 opened in the last 31 days, plus *(no CI selected)*. A query variable (`?ci`) that every section-2 panel uses. |
| Control | **Incident** | ✅ | One incident for *Escalate* and the *Longest open P1* tile | Lists every active P1 / P2 incident, plus *(all incidents)*. A query variable (`?incident`) used only by those two panels. |
| 1 | **Active P1 / P2 at a Glance** | ✅ | Six tiles: Longest open P1 (or the picked incident), Active P1 · P2, Past target time, Open more than 24 h, Hotspot CI, Not picked up (New) | `servicenow-incidents-*`, active P1 / P2. Replaces the earlier P1 Duration, Active by Age, Active by CI and Active by State widgets (client feedback, 8 Oct). Longest open P1 follows the Incident control. |
| 1 | **P1 / P2 Time to Resolve vs Target (P1 4 h · P2 8 h)** | ✅ | Average time to resolve per opened day, P1 (red) and P2 (amber), with dashed target lines | Resolved P1 / P2 opened in the last 30 days; `resolution_time` (ServiceNow's opened → resolved seconds), or resolved_at − opened_at. Target lines are a reference-line layer. |
| 1 | **Active Incidents (P1 / P2)** | ✅ | Every active P1 / P2 with SLA, group, age | Incidents joined to `servicenow-task-sla` (real SLA: breached, breaching ≥ 75 % or due in 30 min, paused). No SLA record → age rule (P1 4 h, P2 8 h), marked "(age)". Full rules: *MIM-V3-SLA-CALCULATION.md*. Incident and CI link to ServiceNow. |
| 2 | **How to use this section** | ✅ | One-line instruction | Text panel |
| 2 | **Escalate** | ✅ | One row per active P1 / P2 on the CI: CI, Active Incident, Priority, Class, Env, CI support group, Assignment Group | Incidents on the CI (or the one in the Incident control) plus the CMDB enrichment on its server metrics; last month. CI and Active Incident link to ServiceNow; no other column is clickable. A CI with no active P1 / P2 still shows one row with its owners. If an incident is picked whose CI is not the one in the CI control, Class / Env / support group come from the incident record and may show "—". |
| 2 | **Infra Health** | ✅ | Minutes since last data, CPU p90, peak memory, fullest disk — RAG coloured | System metrics matched on `ci.name` (equal to the host name). Amber ≥ 80 %, red ≥ 90 %; red if silent > 10 min. Empty if the CI is not a monitored server. |
| 2 | **Middleware / DB Health** | ✅ | Healthy vs Down components on the CI | SQL Server metrics (`metricbeat-*` sql / mssql), middleware processes labelled by the Paladin monitoring enrichment (IBM MQ, IHS, JBoss, WebSphere) and Windows middleware services. Down = stopped or silent > 10 min. |
| 2 | **Applications on this CI** | ⚠️ | Applications and software linked to the CI, and APM services on it | `cmdb-ci-relations` ("Runs on", etc., application-type CIs only) + APM services that sent data from the server in the last day. **Limit:** APM services running in Kubernetes report pod names, not the server, so they don't appear; fixed 30-day window. |
| 2 | **SLO Error Burn Rate** | ⚠️ | 1-hour burn rate per SLO: page now (≥ 14.4×), burning (≥ 1×), on track | `.slo-observability.summary-*` (173 Kibana SLOs). The CI's own per-CI SLOs (★) first, then every SLO burning ≥ 1×. **Limit:** Kibana cannot combine SLO summaries with timestamped data in one panel, so for service SLOs it cannot filter to "services on this CI" — compare names with *Applications on this CI*. Viewers need read access to the hidden `.slo-observability.*` indices. |
| 2 | **Synthetics Health** | ✅ | Monitors that target the CI: status now, down checks | `synthetics-*`, ping monitors enriched with the CI, or monitors whose URL is the CI's host name. Browser journeys are tagged with the application, so they do not appear here. |
| 2 | **Errors from the Logs** | ✅ | Warning-and-worse log lines from the CI, grouped by message | Syslog (server, WebSphere, JBoss, Red Hat, AIX, system), generic file logs, APM error and application logs, matched on `ci.name`; syslog severity code ≤ 4 or log level warning or worse; numbers replaced by # so repeats group together |
| 2 | **Process Health** | ✅ | Stopped / not-seen processes and services first, then healthy middleware | Windows services (Stopped = Automatic service not running) and Paladin-labelled middleware processes; Not seen = silent > 10 min |
| 2 | **Changes on this CI and linked CIs** | ⚠️ | Changes active in the last 7 days on the CI and on CMDB-linked CIs; the CI column shows which | `servicenow-change-requests` + `cmdb-ci-relations`. The selected CI's own changes first. Type (Emergency in red), category, state, outcome (close code), planned start, end, group. **Limit:** no actual start and no maintenance windows in the data; "application" category is the nearest thing to a release. Change and CI link to ServiceNow. |
| 3 | **⬅ Upstream — what they depend on** | ✅ | Horizontal bars: calls per dependency, coloured Failing / Degraded / Healthy, label with % failed; top 15 | `metrics-apm.service_destination.1m-*`, production only. Failing ≥ 10 % failed calls, Degraded ≥ 1 %. Other services appear by host:port, as APM records them. |
| 3 | **Service health** | ✅ | One tile per service in scope: % of its transactions that failed, RAG background, business application | `metrics-apm.service_transaction.1m-*`; "(services on this CI)" = services whose APM host is the CI (`metrics-apm.internal-*`). Click a tile to open the APM Service Map. |
| 3 | **Downstream — who is impacted ➡** | ⚠️ | Horizontal bars: calls per calling service, coloured by the health of those calls; top 15 | Hosts the services in scope answer on (URL host of their incoming-request transactions, CNA host names only) matched to every production service's dependency addresses. Batch / messaging transactions and external hosts (Google storage, Okta …) are ignored. **Limit:** when several services share a host (an API gateway), callers of that host are listed for each of them. Click a bar to open that service's APM Service Map. |
| 3 | **Business applications impacted** | ⚠️ | The callers' CMDB business applications, worst first, with portfolio and support group | From the APM CMDB enrichment on the callers. **Limit:** no user counts or criticality (not in APM or the CMDB data). Click to open the application in the CMDB. |
| Control | **Service** | ✅ | The service(s) for section 3 | Production APM services seen in the last day, plus *(services on this CI)*. A query variable (`?service`) used only by section 3. |
| 4 | **SRE Dashboard** / **Infra Dashboard** | ✅ | Cards linking to the two dashboards | Text panels; the title of each card is the link (opens in a new tab). Addresses from `links.txt`. |

---

## Known limits and the enrichment they point to

| Limit | Why | What would fix it |
|---|---|---|
| No acknowledgement time (time to acknowledge) | Incidents carry no assigned / acknowledged timestamps; the response SLA says *whether* it was met, not *when* | ServiceNow: send assigned / acknowledged timestamps |
| No maintenance windows or releases | No outage-window or actual-start values on 148k change requests; no release or maintenance index | ServiceNow: export maintenance schedules and releases (or Caused-by-change on incidents) to Elastic |
| Change → incident link is inferred | Incidents have no "Caused by change"; matched on the same CI within 7 days | ServiceNow: send Caused-by-change |
| SLO panel not filtered to the CI's services | Kibana limitation (see *KIBANA-LIMITATIONS.md*) | Group SLOs by `ci.name` in Kibana where it makes sense — those follow the CI control |
| Major-incident and bridge flags unused | `is_major_incident` and `has_been_handled_by_bridge` are empty on all P1 / P2 for a year | ServiceNow integration mapping |
| Containerised services not linked to servers | APM reports pod names | Expected; use the application / SLO panels |
| Section 3 has no drawn node-and-arrow diagram | Kibana's Vega charts could draw one, but they cannot read the ES\|QL Service control (only the time range and filters), so the map could not follow the selected service | Section 3 is laid out left to right instead; click a service for the APM Service Map |
| Section 3 is empty for most incident CIs unless a service is picked | P1 / P2 are raised mostly against servers (Linux, AIX), network devices and application services; only servers with APM agents have services on them, and no incident CI is an APM business application (round 5, X and Y) | Pick the service in the Service control; longer term, record the affected business application / service on the incident |
| Estimated user base | Not in Elastic | Add the ServiceNow user-base field to the CI enrichment |

## Related dashboards (section 4): the links

The two cards link to:

| Card | Address |
|---|---|
| SRE Dashboard | https://kibana-prod.gcp.cna.com/app/r/s/b4Jas |
| Infra Dashboard | https://kibana-prod.gcp.cna.com/app/r/s/3A7f1 |

The addresses come from `links.txt` and are built into `MIM V3.ndjson`. To change one, update `links.txt` and
rebuild, so a re-import keeps it. A quick fix in Kibana (**Edit** → panel **⋯** → **Edit**, change the address in
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
