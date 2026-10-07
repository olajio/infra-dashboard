# Operations Dashboard: how the NOC and leadership use it

**File:** `operation-dashboard.ndjson` · **Dashboard:** *Operations Dashboard — Consolidated (Alert, Infra, Platform Health)*
(id `ops-dashboard-consolidated-v1`) · **Audience:** NOC / Infrastructure Operations, plus a leadership summary at the top
**Default time range:** last 4 hours · **Auto-refresh:** off by default (set to 1 minute when switched on)

The Operations Dashboard answers four questions, top to bottom:

1. **Is the business healthy right now?** One RAG verdict for the infrastructure, server availability, open P1 / P2
   incidents, which domains they sit in and how the applications are doing.
2. **How is the estate running?** The server estate behind those numbers: which servers are down, who owns them, and
   where CPU, memory, disk and network are under strain.
3. **How much can we see, and can we trust it?** Monitoring coverage and data freshness. These are confidence measures
   for sections 1 and 2.
4. **What is automation taking off the queue?** Alert volume, correlation and deduplication, and the predictive
   capabilities still to come.

The dashboard has a link strip, four sections, a reference section and three filter controls:

| | What it covers | Time window |
|---|---|---|
| **Detail dashboards** (top strip) | Links to the server, database, middleware, integration and service detail dashboards | — |
| **Data center / Support group / Host controls** (top) | Filter the **whole dashboard** to one or more data centres (`ci.geo.name`), L2 support groups (`ci.support_group.l2.name`) or hosts (`host.name`). Multi-select; empty = everything. | — |
| **1 · Executive Health** | The verdict, availability, P1 / P2, domains, application health, affected CIs | Time picker |
| **2 · Operational Effectiveness** | Servers up / down, availability trend, saturation, disk, network | Time picker |
| **3 · Monitoring Maturity** | What is collected, what has gone silent, how fresh the data is | Time picker |
| **4 · Automation & Predictive Operations** | Netcool alerts, ServiceNow correlation, dedup ratio, predictive placeholder | Time picker (the "24h" tiles also cap at 24 h, see *Things to know*) |
| **Reference — notes & data limitations** (collapsed) | About, data limitations, KPI status cards | — |

---

## The walkthrough — telling the story

*Example used below: it is 08:00, the start of the NOC shift and 30 minutes before the leadership stand-up. The
names and numbers are illustrative.*

### Step 1 — Take the temperature (section 1, top row)

The NOC lead opens the dashboard and reads the four tiles left to right.

- **Overall Infrastructure Health** is the one-word answer. **🔴 RED** when any P1 is open or fewer than 99.0 % of
  monitored CIs are reporting; **🟠 AMBER** when any P2 is open or fewer than 99.9 % are reporting; otherwise
  **🟢 GREEN**. The line under it says why, e.g. *"1 P1 · 3 P2 · 12 CIs down"*. *This morning it is RED: one P1.*
- **Server Availability %**: the share of the OS-monitored server estate that sent data in the last 15 minutes.
  *99.6 %, so about a dozen servers are silent.*
- **Active P1 Incidents / Active P2 Incidents**: every open incident at that priority, all domains. *1 P1, 3 P2.*

### Step 2 — Is this new or ongoing? (section 1, trends)

- **CI Availability Trend**: the share of monitored CIs reporting in each 15-minute interval. A dip that starts at
  one point in time and stays down means an outage; a single dip that recovers is usually a network blip or a
  collector restart. *A step down at 06:45 that has not recovered.*
- **CIs Down During Period**: the CIs behind that dip. **🔴 Down now** = silent for more than 15 minutes;
  **🟠 Recovered** = missed at least one interval in the range but is back. It shows the host, data centre, support
  team, availability over the range and minutes down. Click a CI to open it in the ServiceNow CMDB.
  *Nine CIs in the Aurora data centre went down at 06:45, all owned by the same Linux team.*
- **Active P1 / P2 Incidents — Trend**: open P1 and P2 incidents per hour. *The P1 appeared at 07:00, fifteen minutes
  after the CIs dropped, so the outage came first.*

### Step 3 — Where is it, and is the business feeling it? (section 1)

- **Impacted Domain**: open P1 / P2 by infrastructure domain (Windows, Linux, AIX / UNIX, Network, Database, Storage,
  Middleware, Virtualisation, Application / Service …), from the CI class on each incident. **⚠️ No CI mapped**
  collects incidents without a CI, so the P1 and P2 columns add up to the tiles. *The P1 is in Linux.*
- **Application Health Mix** and **Application Health**: real APM health. Each service's error rate and average
  latency; an application takes the status of its worst service (**🔴 RED** ≥ 5 % errors, **🟠 AMBER** ≥ 1 %).
  Click a service to open it in APM. *Two applications are RED; both have production services whose error rate jumped
  after 06:45.*
- **Affected CIs — Active P1 / P2**: the incident worklist, one row per incident and CI, P1 first: severity, incident,
  Affected CI, class, environment, owning group, summary. Click the incident or the CI to open it in ServiceNow.
  *The P1 is raised against one of the nine Linux servers, assigned to the Linux team.*

At this point the lead can brief leadership in one sentence: *"One P1 since 07:00: nine Linux servers in Aurora went
silent at 06:45, two applications are failing; the Linux team has it."* For a P1, the Major Incident Manager takes it
from here in **MIM V3**.

### Step 4 — Look at the estate behind it (section 2)

- **Total Servers Monitored / Servers Up / Servers Down / Servers Availability %**: the server headcount tiles.
- **Server Availability Trend**: % of the estate reporting, per hour. Confirms whether the drop is still ongoing.
- **Servers Down**: every server silent for more than 15 minutes, longest first, with the Affected CI, class,
  application (from the CMDB description), environment, location, support group and minutes down (amber from 15 min,
  red from 60). Click a host to open it in Observability → Infrastructure. *The nine Aurora servers, all 75 minutes
  down. Same VLAN: a network or hypervisor problem, not nine separate faults.*
- **Server Estate by Platform**: Windows / Linux / AIX / HP-UX split of the estate, for scale.

### Step 5 — Check for slow-burning trouble (section 2)

Not every problem is an outage. The lead scans the saturation tables for what is about to become the next incident.

- **Resource Utilisation Trend**: P90 CPU and P90 memory across all servers over the range.
- **CPU Saturation** (P90 ≥ 80 %, red from 90 %) and **Memory Saturation** (P90 ≥ 85 % excluding page cache, red
  from 95 %): the hosts working hardest, with environment and support group.
- **Disk Saturation**: filesystems more than 50 % used, fullest first (amber from 80 %, red from 90 %). *A /var on a
  database server at 94 %: a ticket to the DBA team before it fills.*
- **Network Errors**: interfaces with in / out errors.

Every host in these tables opens in Observability → Infrastructure.

### Step 6 — Can we trust these numbers? (section 3)

Before quoting a figure to leadership, the lead checks that the data behind it is complete and fresh.

- **Telemetry Freshness (max lag, min)** and **Telemetry Freshness Trend**: the worst delay between an event and its
  arrival in Elastic. Anything over 15 minutes means "up / down" figures can be wrong.
- **Ingest Pipeline Health**: which data source has that lag.
- **Monitored Estate**: each collection tier (server OS, Windows services, APM, vSphere, Oracle, SQL, IBM MQ, GCP,
  Kubernetes …) with datasets, reporting hosts, volume and **🟢 Flowing / 🟠 Delayed / 🔴 Stalled**. *All tiers
  flowing, so the nine servers are really down, not a stalled feed.*
- **Coverage Gap** and **CIs Not Reporting (>15 min)**: monitored, operational CIs that have gone silent.
- **Applications on Silent Servers**: applications with at least one CI on a silent server, 🔴 when all of their CIs
  are down, 🟠 when only some are.
- **Agent / Collector Health (%)**, **Total CIs Monitored**, **Business Applications Monitored**,
  **APM Services Instrumented**, **Application Estate**: the size of what we can see, by environment.

### Step 7 — Noise and automation (section 4)

- **Raw Netcool Alerts (24h)** and **Correlated SN Events (24h)**: how many raw alerts arrived and how many reached
  ServiceNow as events. **Alert Dedup Ratio (24h)** is the share of raw alerts that correlation removed.
- **Alert Volume Trend**: raw alerts per hour. *An alert storm at 06:45 (the nine servers and everything on them),
  which correlation collapsed to a handful of events.*
- **Predictive Insights**: a placeholder until the Elastic ML forecasting jobs exist.

### Step 8 — Hand off or drill down

- **For a P1 / P2**: open **MIM V3** for the investigation and the bridge.
- **For one platform**: the **Detail dashboards** strip at the top opens the Windows, Linux, AIX, HP-UX, PostgreSQL and
  MSSQL dashboards, middleware and integration searches in Discover (JBoss, Tomcat, WebSphere, MQ, API gateway), and
  the Incident effectiveness and Synthetic availability dashboards.
- **For one team or site**: pick it in the **Support group** or **Data center** control. The whole dashboard then
  shows only that slice (see *Things to know*).

---

## Things to know

### Time range and refresh

- **Every panel follows the time picker** (last 4 hours by default). Nothing on this dashboard has a fixed window.
- **Auto-refresh is off by default.** Switch it on (it is set to 1 minute) when the dashboard is on a wall screen or
  during an incident; otherwise click **Refresh**.
- **"Up" always means "reported in the last 15 minutes", whatever the time range.** The tiles for Overall Health,
  Server Availability, Servers Up / Down and CIs Not Reporting, and the *Servers Down* and *Coverage Gap* tables, all
  use that rule.
- **The time range decides who is counted at all.** A server or CI is only in the estate if it sent data at some
  point in the range. One that has been silent for longer than the whole range drops out of the denominator and does
  not show as down. With the default 4 hours, a server that died yesterday is invisible. **Widen the range to 24 h or
  7 days** to catch long-dead servers. *CIs Down During Period* says this in its description too.
- **Incident tiles read ServiceNow snapshots.** P1 / P2 counts are the incidents whose latest snapshot in the time
  range shows them open. A shorter range gives a more current count; a longer one can include incidents that have
  since been resolved if they stopped appearing in the snapshots before a closed state was recorded.
- **The "(24h)" tiles in section 4 also get the time-picker filter.** Their query keeps the last 24 hours, but the
  dashboard's range still applies. With the default 4 hours they show 4 hours of data. **Set the range to 24 hours
  or more** for the 24-hour figures.
- **Trends need a long enough range.** The first and last 15-minute or hourly intervals are partial, so the trends
  leave them out. With a short range (under an hour) the CI Availability Trend may show only a point or two.

### Controls and filters

- **The three controls filter every panel.** They are standard filters, not per-section. A panel whose data does not
  have the control's field shows **no data or zero**, which is not the same as "all clear". For example, picking a
  **Host** can make the P1 / P2 tiles, application health or Netcool tiles go to zero. Clear the control
  (**×** on it) before reading those tiles.
- **Clicking a cell can also filter the whole dashboard.** Some tables offer *Filter for / Filter out*, or the click
  menu offers *Apply filter to current view*, which adds a filter that applies to every panel. Remove it with the
  **×** on the filter pill under the search bar.
- **Each table's link is meant for one column**: *Affected CIs* for the **Affected CI** and **Incident** columns
  (ServiceNow), *Application Health* for the **service** (APM), *CIs Down During Period* for the **CI** (CMDB), and
  *Servers Down*, *CPU / Memory / Disk Saturation* and *Network Errors* for the **host** (Observability →
  Infrastructure). When a table has two links, the click menu lists both, each labelled with its column; pick the one
  for the column you clicked.
- **Another column may also offer the link menu.** Kibana makes a table column clickable when its name matches a
  field in the data (*KIBANA-LIMITATIONS.md*, row 23), so a column such as *Environment* can show the menu too. A
  link opened from the wrong column points at a record that does not exist; use only the intended column.
- **Links need a Gold or higher licence.** Without it a click only adds a filter.

### Reading the numbers

- **RED is common.** Overall Health turns RED whenever a single P1 is open anywhere, and AMBER for a single P2. Read
  the detail line (*"1 P1 · 3 P2 · 12 CIs down"*) to see which condition triggered it.
- **Several "down" panels, different scopes.** They will not always agree:

  | Panel | Unit | Scope | Silent = |
  |---|---|---|---|
  | Servers Down, Server Availability, Servers Up | host (`host.name`) | Servers with OS telemetry (`system.*` datasets) | No data for 15 min |
  | CIs Down During Period, CI Availability Trend, Overall Health | CI (`ci.name`) | Every monitored, operational CI in `metrics-*` | Missed a 15-min interval in the range, or silent now |
  | Coverage Gap, CIs Not Reporting | CI | Every monitored, operational CI | No data for 15 min |

- **Server availability is servers only.** Remotely collected tiers (vSphere, GCP, Kubernetes, Oracle, IBM MQ,
  Prometheus) report under the collector's host name, not the device's, so they are not in the availability figures.
  *Monitored Estate* shows those tiers' collection health instead.
- **Application health covers all environments.** *Application Health Mix* takes the worst service of each
  application, including test (CUT, ETE, Stage) and DR services. A RED application may be RED because of a test
  service. Check the **Environment** column in *Application Health*.
- **Thresholds differ from MIM V3.** Here an application is RED from 5 % errors and AMBER from 1 %. In MIM V3 section 3
  a service is *Failing* from 10 %.
- **Check the transaction count before trusting an error rate.** A service with 20 transactions and 1 failure shows
  5 %, which is RED.
- **Network errors are counters.** Interface error counts accumulate from when the interface came up, so a large
  number may be old. A count that keeps rising between refreshes is the real signal.
- **Disk Saturation shows the 25 fullest filesystems** above 50 %. Saturation tables show the top 50 hosts.
- **"Application" on server panels is CMDB free text.** *Servers Down* and *Applications on Silent Servers* use the
  CI's short description as the application name, and skip descriptions that just start with "Linux". APM panels
  use the ServiceNow Business Application name instead, which is more reliable.
- **Affected CI vs Impacted CI.** *Affected CI* is the CI the incident was raised against. *Impacted* CIs (things that
  depend on it) are not on this dashboard; MIM V3 sections 2 and 3 cover them for one CI or service.
- **Incident counts reconcile like this.** The P1 / P2 tiles count every open incident. *Impacted Domain* includes
  incidents with no CI (⚠️ No CI mapped), so its columns add up to the tiles. *Affected CIs* lists only incidents
  with a CI, one row per incident and CI.

### Speed and access

- **The CI-level panels scan all of `metrics-*`** (CI Availability Trend, CIs Down During Period, Coverage Gap,
  Overall Health). On a 7-day range they can take a while; Kibana does not run a collapsed section's queries, so
  collapse the sections you are not using.
- **Viewers need read access to** `metrics-*` (including `metrics-apm*` and the `.ds-metrics-system.*` streams),
  `servicenow-open-incidents-snapshots-*`, `.ds-bridge-alerts-netcool-*` and `.ds-logs-servicenow.event-*`. A
  panel the viewer cannot read shows an error.

---

## Panel reference

**Status:** ✅ ready on the confirmed data · ⚠️ ready, with the limit noted · 🚧 placeholder.

| Section | Panel | Status | What it shows | How it works |
|---|---|---|---|---|
| Top | **Detail dashboards** | ✅ | Links to the detail dashboards | Windows, Linux, AIX, HP-UX, PostgreSQL, MSSQL dashboards; Discover searches for JBoss, Tomcat, WebSphere, MQ, API gateway, integration services; Incident effectiveness and Synthetic availability dashboards. Oracle is marked *not collecting*. |
| Control | **Data center / Support group / Host** | ⚠️ | Filter the dashboard | Options lists on `ci.geo.name`, `ci.support_group.l2.name`, `host.name` (data view `metrics-*`). **Limit:** filter every panel; panels without the field go empty. |
| 1 | **Overall Infrastructure Health** | ✅ | 🔴 / 🟠 / 🟢 verdict with "n P1 · n P2 · n CIs down" | RED: any P1, or CI availability < 99.0 %. AMBER: any P2, or < 99.9 %. CI availability = monitored, operational CIs reporting in the last 15 min ÷ those seen in the range. P1 / P2 from the latest open snapshot per incident. |
| 1 | **Server Availability %** | ✅ | Share of servers reporting now | Hosts in `system.*` datasets with data in the last 15 min ÷ hosts seen in the range |
| 1 | **Active P1 Incidents / Active P2 Incidents** | ⚠️ | Open incidents at that priority | `servicenow-open-incidents-snapshots-*`: latest snapshot per incident not Resolved / Canceled / Closed. **Limit:** depends on the time range (see *Things to know*). |
| 1 | **CI Availability Trend** | ✅ | % of monitored CIs reporting per 15 min | Against the most CIs seen in any interval; partial first / last intervals left out |
| 1 | **CIs Down During Period** | ✅ | CIs that missed an interval or are silent now: 🔴 Down now / 🟠 Recovered, host, data centre, team, availability, minutes down | Full 15-min intervals with data ÷ full intervals in the range. CIs silent for the whole range are not listed. CI opens in the CMDB. |
| 1 | **Active P1 / P2 Incidents — Trend** | ✅ | Open P1 and P2 per hour | Distinct open incidents in each hour's snapshots |
| 1 | **Impacted Domain** | ✅ | Open P1 / P2 and affected CIs per domain | Domain from the incident's CI class; ⚠️ No CI mapped / ⚠️ CI class missing shown; unmapped classes keep their own name |
| 1 | **Application Health Mix** | ⚠️ | Applications by worst-service health | `apm.service_transaction.1m`: error rate = failed ÷ all transactions. RED ≥ 5 %, AMBER ≥ 1 %. **Limit:** all environments, including test. |
| 1 | **Application Health** | ✅ | Per service: health, application, portfolio, environment, error rate, average latency, transactions | Same source; application = CMDB Business Application (or the service name if not enriched). Service opens in APM. |
| 1 | **Affected CIs — Active P1 / P2** | ✅ | Open P1 / P2 incidents with their Affected CI, class, environment, owning group, summary | One row per incident × CI; incidents without a CI not listed. Incident and CI open in ServiceNow. |
| 2 | **Total Servers Monitored / Servers Up / Servers Down / Servers Availability %** | ✅ | Server headcount | `system.*` hosts; up = data in the last 15 min |
| 2 | **Server Availability Trend** | ✅ | % of servers reporting per hour | Against the most servers seen in any hour; partial hours left out |
| 2 | **Resource Utilisation Trend** | ✅ | P90 CPU and P90 memory across all servers | `.ds-metrics-system.cpu / memory`, 48 intervals over the range; memory excludes page cache |
| 2 | **Server Estate by Platform** | ✅ | Servers by CMDB class | Windows / Linux / AIX / HP-UX / Other / No CMDB class |
| 2 | **Servers Down** | ✅ | Servers silent > 15 min with CI, class, application, environment, location, support group, minutes down | Host opens in Observability → Infrastructure. Amber from 15 min, red from 60. |
| 2 | **CPU Saturation** / **Memory Saturation** | ✅ | Hosts with P90 CPU ≥ 80 % / P90 memory ≥ 85 % | P90, peak and average over the range; red from 90 % / 95 % |
| 2 | **Disk Saturation** | ✅ | Filesystems > 50 % used (top 25) | Highest used % per host and mount point over the range; amber 80 %, red 90 % |
| 2 | **Network Errors** | ⚠️ | Interfaces with in / out errors (top 25) | **Limit:** cumulative counters, so a big number may be old |
| 3 | **Business Applications Monitored / APM Services Instrumented** | ✅ | Size of the APM estate | Distinct Business Applications / services in `metrics-apm*`, all environments |
| 3 | **Agent / Collector Health (%)** | ⚠️ | Share of agents reporting in the last 5 min | Distinct `agent.name` values; **limit:** depends on how agents are named |
| 3 | **Total CIs Monitored / CIs Not Reporting (>15 min)** | ✅ | Monitored, operational CIs and the silent ones | `ci.is_monitored` and `ci.operational_status` from the CMDB enrichment |
| 3 | **Telemetry Freshness (max lag, min)** / **Trend** | ✅ | Worst ingest delay, now and per hour | `ingest_lag_in_sec`; > 15 min = stale |
| 3 | **Monitored Estate** | ✅ | Collection health per tier | Datasets, reporting hosts, volume, minutes since last data; Flowing ≤ 15 min, Delayed ≤ 60, Stalled after |
| 3 | **Coverage Gap** | ✅ | Monitored CIs silent > 15 min with host, location, support group | — |
| 3 | **Applications on Silent Servers** | ⚠️ | Applications with CIs on silent servers: all down (🔴) or partial (🟠) | **Limit:** application = CMDB short description (free text) |
| 3 | **Application Estate** | ✅ | APM applications and services per environment, with freshness | Environment names normalised (prd / prod → Production, etc.) |
| 3 | **Ingest Pipeline Health** | ✅ | Worst and average ingest lag per data source | Top 20 by worst lag |
| 4 | **Raw Netcool Alerts (24h) / Correlated SN Events (24h)** | ⚠️ | Alert and event counts | **Limit:** also capped by the time picker |
| 4 | **Alert Dedup Ratio (24h)** | ⚠️ | (raw − correlated) ÷ raw | Same limit |
| 4 | **Alert Volume Trend** | ✅ | Raw Netcool alerts per hour | Baseline for alert-storm detection |
| 4 | **Predictive Insights** | 🚧 | Placeholder | Waiting on Elastic ML forecast / anomaly jobs |
| Ref | **About this dashboard / Notes / Noise Reduction / Predictive Insights** | — | Background, data limitations, KPI status | Text panels; the section is collapsed by default |

---

## Known limits and the enrichment they point to

| Limit | Why | What would fix it |
|---|---|---|
| No MTTA (time to acknowledge) | `acknowledged_at` / `assigned_at` are not in the incident data | ServiceNow business rule and mapping update |
| No Impacted CIs | The CMDB relationship graph (33.9M edges) cannot be walked at query time, and the incident's parent fields are empty | ENRICH policy or a transform that adds downstream CIs to incidents |
| No per-device availability for vSphere, GCP, Kubernetes, Oracle, MQ | Those tiers report under the collector's host name | Use each tier's own entity ID (VM name, instance, queue manager, resource) |
| Oracle not collecting | No Oracle metrics arriving | Fix the Oracle integration |
| No Noise Reduction Opportunity Score | No stable Netcool rule ID, dedup outcome, analyst feedback or alert ↔ incident join field | ML job plus an analyst feedback field, scores written to their own index |
| Predictive Insights not built | Needs forecast / anomaly jobs | Elastic ML jobs writing to a `predictive-insights-*` index |
| Application name on server panels is free text | CMDB short description | Link servers to Business Applications in the CMDB enrichment |

---

## Importing

Import `operation-dashboard.ndjson` in **Stack Management → Saved objects → Import**, with *overwrite*. It contains
the dashboard and the `metrics-*` data view that the three controls use. A re-import replaces any changes made to the
dashboard in Kibana.

If you had the dashboard open with unsaved changes (a control selection, a different time range), Kibana can lay those
over the newly imported version. After a re-import, click **More (⋯) → Reset changes → Reset dashboard**, then reload
the page. Do not click Save before doing that.

`DASHBOARD-PANEL-GUIDE.md` is the older, more technical panel-by-panel guide (last updated 22 Sep). Where the two
differ, this guide follows the dashboard as exported on 29 Sep.
