# Operations Dashboard — Panel Guide

**Saved object:** `operation-dashboard.ndjson` → dashboard `ops-dashboard-consolidated-v1`
**Title:** *Operations Dashboard — Consolidated (Alert, Infra, Platform Health)*
**Default time range:** `now-24h` → `now` (saved with the dashboard) · **Auto-refresh:** every 60 s
**Panels:** 43 · every panel is *by value* (embedded in the dashboard), so importing this one NDJSON is the whole deployment.

---

## 0. Dashboard flow — four sections

The dashboard reads top to bottom as a narrative, each section answering the question the one above it
raises. Section headers are markdown banners on the dashboard itself.

| # | Section | Question it answers | Panels, in order |
|---|---|---|---|
| **1** | 🏢 **Executive Health** | *Is the business healthy right now?* | Overall Infrastructure Health · Server Availability % · Active P1 · Active P2 · Impacted Domain · Affected CIs · Application Health — APM |
| **2** | 🔧 **Operational Effectiveness** | *How is the estate actually running, and what needs hands on it?* | Total Servers · Servers Up · Servers Down · Servers Availability % · Server Availability Trend · Servers Down — Affected CIs · Disk Saturation · Network Errors |
| **3** | 📡 **Monitoring Maturity** | *How much can we see, and can we trust sections 1 and 2?* | Monitored Estate by Tier · Business Applications Monitored · APM Services Instrumented · Application Estate by environment · Agent / Collector Health · Total CIs Monitored · CIs Not Reporting · Telemetry Freshness · Telemetry Freshness Trend · Ingest Pipeline Health · Coverage Gap — CIs Not Reporting · Applications on Silent Servers |
| **4** | 🤖 **Automation & Predictive Operations** | *What is automation taking off the queue, and what is coming?* | Raw Netcool Alerts · Correlated SN Events · Alert Dedup Ratio · Alert Volume Trend · Noise Reduction — AI KPI status · Predictive Insights |

Quick links and **Notes & Data Limitations** trail the four sections as reference material.

**Why panels sit where they do.** Section 3 is deliberately *after* the operational detail rather than
buried at the bottom: a coverage gap or a stale feed means the availability figures in sections 1 and 2
are optimistic, so it reads as the confidence statement for everything above it. Alert correlation and
deduplication sit in section 4 rather than with the alert-handling detail because they measure what
automation removes from the analyst queue, which is the same question the predictive tiles ask.

> The per-panel write-ups below keep their original numbering (§2 for the executive panels, §3 for the
> operational ones). That numbering is a reference index, not the on-screen order — use the table above
> for the layout.

---

## 0.1 Terminology — Affected CI vs Impacted CI

Aligned to the client's definitions, September 2026. An earlier version of this dashboard had the two
terms the other way round; every panel title, column label and note has been realigned.

| Term | Definition | On the dashboard |
|---|---|---|
| **Affected CI** | The configuration item that *is* affected by the incident — the server, switch, database or service the incident was raised against. | `ci.name` on the ServiceNow incident record. This is what every CI panel shows today. |
| **Impacted CI** | A configuration item that could be affected *as a consequence* of the affected CI failing — the downstream, dependent side of a CMDB relationship. | **Not available yet.** See below. |

**Why Impacted CIs are not on the dashboard.** Deriving them needs the CMDB relationship graph in
`cmdb-ci-relations-000002` (33.9M edges: `parent`, `child`, `type.name`, and an `impacted_ci` field
naming which side is downstream). ES|QL cannot traverse a graph that size at query time, and
`ci.parents.*` / `ci.top_level_parents.*` exist in the incident mapping but are populated on **0**
documents, so the incident record carries no downstream rollup of its own. Closing this needs an ENRICH
policy or a denormalising transform on the Elasticsearch side — an infrastructure change, not a
dashboard one. `business_service.name` is populated on 2.8% of incidents and is the nearest available
proxy; it is shown on the Affected CIs worklist.

**Panels renamed:** *Impacted CIs — Active P1 / P2 Incidents* → **Affected CIs — Active P1 / P2
Incidents**; *Servers Down — Impacted CIs* → **Servers Down — Affected CIs**. The *Impacted Domain*
panel keeps its name (a domain is not a CI) but its CI column is now **Affected CIs**.

---

## 0.2 Reconciling the incident counts

The client found three different P2 figures on one screen: the **Active P2** tile said 44, *Impacted
Domain* summed to 40, and *Affected CIs* listed 41 rows. Three panels, three numbers, two separate
causes.

| Panel | Showed | Why |
|---|---|---|
| **Active P2 Incidents** (tile) | 44 | `WHERE priority == 2` — counts **every** open P2. |
| **Impacted Domain** | 40 | Also had `AND ci.name IS NOT NULL`. Incidents with no CI on the record were silently dropped — 44 − 40 = **4 open P2s with no CI**. |
| **Affected CIs** | 41 rows | Same 40 incidents, but grouped by eight attributes. One incident had an attribute change between snapshots (`business_service.name` filling in, a reassignment, a re-description) and so appeared on **two rows**. |

**Fixes.** *Impacted Domain* no longer filters on `ci.name`; incidents without one now land in a
**⚠️ No CI mapped** row, so its P1 and P2 columns add up to the tiles exactly — and the count of
unmapped incidents becomes a visible data-quality signal rather than a silent omission. *Affected CIs*
now groups on `number`, `ci.name` and `priority` only, so it is one row per incident × CI.

*Affected CIs* still lists only incidents that carry a CI, so its row count equals the tile total minus
the *No CI mapped* row. That is by design — it is a CI worklist — and the Domain panel now makes the
difference visible.

**To verify against the cluster:**

```esql
FROM servicenow-open-incidents-snapshots-*
| WHERE priority == 2
| STATS all_p2 = COUNT_DISTINCT(number),
        with_ci = COUNT_DISTINCT(CASE(ci.name IS NOT NULL, number, null))
| EVAL no_ci = all_p2 - with_ci
```

```esql
FROM servicenow-open-incidents-snapshots-*
| WHERE priority == 2 AND ci.name IS NOT NULL
| STATS rows = COUNT(*) BY number, ci.name, ci.class_name, ci.environment,
                           assignment_group.name, business_service.name, short_description
| STATS variants = COUNT(*) BY number
| WHERE variants > 1
```

The first should return `no_ci = 4`; the second should return the one incident that was splitting.

---

## 0.3 How to import

Kibana → **Stack Management → Saved Objects → Import** → select `operation-dashboard.ndjson` →
choose *"Check for existing objects"* and **overwrite** the existing dashboard to keep the same URL/bookmarks.

The file contains two saved objects: the `metrics-*` data view and the dashboard itself. All other index
patterns are **ad-hoc ES|QL data views** embedded inside each panel — nothing else to create.

---

## 1. Global controls (top of dashboard)

| Control | Field | What it does |
|---|---|---|
| Location | `ci.geo.name` | Filter everything to a data centre — Aurora IL70, Slough, Germantown, Blythewood, Chicago IL00, Greenford, GCP |
| Support Group (L2) | `ci.support_group.l2.name` | Filter to the owning L2 team — Wintel, Unix Engineering, Exadata Admin, IT.Sec.*, GCP Services |
| Host | `host.name` | Drill to one or more servers |

Controls are **hierarchical** — picking a location narrows the values offered in the next two controls.

---

## 2. Executive Summary  *(new — built from the team's feedback)*

> Rendered under the banner *"🏢 Executive Summary — Overall Infrastructure Health"*.
> This whole block is the leadership view: RAG status, availability, incident load and business impact
> without opening any SRE dashboard.

### 2.0 Scope — what the availability number actually covers

`metrics-*` is **not** a server-only index pattern. It spans **578 data streams and ~830 M documents**
across eleven infrastructure tiers:

| Tier | Data streams | Max distinct `host.name` | Documents |
|---|---|---|---|
| Applications — APM | 513 | 5,285 | 306.8 M |
| **Servers — OS telemetry** | **13** | **2,893** | **214.1 M** |
| Cloud — GCP | 4 | 1 | 199.5 M |
| Prometheus targets | 1 | 9 | 61.0 M |
| Servers — Windows services | 2 | 1,602 | 43.6 M |
| Containers — Kubernetes | 23 | 1 | 4.5 M |
| Monitoring stack (agent / fleet) | 8 | 13 | 265.6 K |
| Virtualisation — vSphere | 7 | 1 | 234.8 K |
| Database — Oracle | 5 | 2 | 14.3 K |
| Middleware — IBM MQ | 1 | 1 | 2.9 K |
| Database — SQL | 1 | 2 | 568 |

The critical detail is the middle column. `host.name` is only a valid *availability unit* for
**agent-based** collection — `system.*` and `windows.*` — where it identifies the monitored machine.
For every **remotely-collected** tier the agent writes its own hostname, so `host.name` is the
**collector**, not the device: `vsphere.virtualmachine` carries 150,838 documents under a *single*
`host.name`, every `kubernetes.*` stream shows 1, `gcp.gke` shows 1 for 197 M documents, and `oracle.*`
shows 2.

A plain `COUNT_DISTINCT(host.name)` over `metrics-*` therefore returns a **mixed population** — real
servers, plus APM service hosts and containers, plus a handful of collector hostnames standing in for
thousands of VMs, cloud resources and databases. Every availability panel on this dashboard is now
scoped with:

```esql
| WHERE STARTS_WITH(data_stream.dataset, "system.")
```

so the denominator is the real server estate (~2,893 hosts) and the number means something. Panel 2.9
lists every other tier and whether its telemetry is flowing.

**How to say it in the room:** *availability is measured on the OS-monitored server estate; P1/P2 covers
every infrastructure domain; collection health for the other tiers is the Monitored Estate panel.*

### 2.1 Overall Infrastructure Health  🟢 / 🟠 / 🔴
**Type:** Lens data table (single row) · **Indices:** `metrics-*` **+** `servicenow-open-incidents-snapshots-*`

One ES|QL query spans both indices (using `METADATA _index` to tell the two document sources apart), so
availability and incident load are evaluated **together** in a single number — which is exactly what the
feedback asked for ("health should be derived from availability **and** active critical issues").

| Column | Meaning |
|---|---|
| **Infra Health** | 🔴 RED / 🟠 AMBER / 🟢 GREEN |
| **CI availability %** | Monitored, Operational **CIs** reporting in the last 15 min ÷ all such CIs |
| **CIs not reporting** | Count of monitored CIs with no telemetry in the last 15 min |
| **Active P1** | Distinct open ServiceNow P1 incident numbers — **all** infrastructure domains |
| **Active P2** | Distinct open ServiceNow P2 incident numbers — **all** infrastructure domains |

> **Changed September 2026 — CI availability, not server availability.** The team asked for this panel
> to be driven by **CI** availability. The denominator is now every CI with `ci.is_monitored == true`
> and `ci.operational_status == "Operational"`, counted on `ci.name`, rather than distinct `host.name`
> on `system.*` datasets. That is a **wider** population: it includes CIs monitored through tiers where
> `host.name` is the collector rather than the device (vSphere, Oracle, MQ, GCP…), which the server-based
> figure could never see. Expect this number to differ from the *Server Availability %* tile beside it —
> they measure different estates, and both are correct.

**RAG rules (hard-coded in the panel's ES|QL, easy to re-tune):**

| Status | Condition |
|---|---|
| 🔴 **RED** | any active **P1** (any domain) **OR** CI availability **< 99 %** |
| 🟠 **AMBER** | any active **P2** (any domain) **OR** CI availability **< 99.9 %** |
| 🟢 **GREEN** | no P1, no P2, CI availability **≥ 99.9 %** |

Evaluation order is top-down, so RED always wins over AMBER. The 99 % / 99.9 % boundaries are the
two-nines / three-nines availability tiers, matching the RAG colouring on the availability tiles (§2.2).

*To change the thresholds:* open the panel → **Edit ES|QL** → change `99.0` / `99.9` in the
`EVAL infra_health = CASE(...)` block.

### 2.2 Server Availability %
**Type:** Lens metric · **Index:** `metrics-*`, scoped to `system.*`

Denominator: distinct `host.name` shipping `system.*` telemetry anywhere in the dashboard time range
(~2,893 servers). Numerator: the same, restricted to hosts with a document in the **last 15 minutes**.
Displayed as a percentage with 2 decimals (e.g. `99.52%`), matching the example in the feedback.

> **Renamed** from *Infrastructure Availability %*. The KPI the team asked for is unchanged; the title now
> states its scope, because the number is a server-estate figure and the old name implied the whole estate.

"Up" therefore means *the server is still shipping metricbeat data*. It is an agent-liveness proxy for
availability — it does not require an extra uptime probe.

#### RAG colouring (added September 2026)

Both availability tiles — *Server Availability %* in the executive row and *Servers Availability %* in
the operational row — now colour the number against the standard availability tiers:

| Colour | Availability | Tier |
|---|---|---|
| 🟢 Green | **≥ 99.9 %** | three nines |
| 🟠 Amber | **99.0 – 99.9 %** | two nines |
| 🔴 Red | **< 99.0 %** | below two nines |

These are the conventional infrastructure availability bands, which is what "industry standard" means
here. **Read the operational consequence before adopting them:** at ~3,139 monitored servers, three nines
is **3 hosts**. A routine patch window that reboots a dozen machines will show amber, and a larger
maintenance wave will show red — correctly, by this definition, but noisily if the team treats the tile as
an alarm rather than a status.

If that is too tight for how this estate is actually run, the usual alternative is to set green at 99.5 %
and amber at 99 %. It is a two-number edit: the `colorStops` in each tile's palette. The thresholds are
deliberately the same as the Overall Infrastructure Health RAG rules (§2.1) so the header tile and the
availability tiles never disagree about what "green" means.

### 2.3 Active P1 Incidents · 2.4 Active P2 Incidents
**Type:** Lens metric ×2 · **Index:** `servicenow-open-incidents-snapshots-*`

`COUNT_DISTINCT(number)` filtered on `priority == 1` / `priority == 2`. Counting distinct **incident
numbers** (not documents) means the recurring open-incident snapshots do not inflate the number.

> These two tiles replace the old *"Active Critical Alerts (P1)"* tile, which has been removed to avoid
> showing the same figure twice.

### 2.5 Applications Degraded (Prod) — *removed*

Removed at the client's request, September 2026: the team judged the way degradation was calculated to
be wrong. Application health is still on the dashboard as the full *Application Health — APM* table
(§2.7), which shows the underlying error rate and latency per service rather than rolling them into a
single count.

### 2.6 Impacted Domain — Active P1 / P2 Incidents
**Type:** Lens data table · **Index:** `servicenow-open-incidents-snapshots-*`

Which technology domain the open P1s and P2s are actually landing in. Columns: **Status · Domain · P1 ·
P2 · Incidents · Affected CIs**, worst-first.

Incidents with no CI on the record appear under **⚠️ No CI mapped**, and ones whose CI carries no
class under **⚠️ CI class missing**, so the P1 and P2 columns add up to the Active P1 / Active P2
tiles exactly.

Domain is grouped from `ci.class_name` **on the incident record**, using the CMDB's real class
vocabulary:

| Domain | CI classes |
|---|---|
| Windows | Windows Server |
| Linux | Linux Server |
| AIX / UNIX | AIX Server |
| Network | IP Switch · IP Router · Wireless Access Point · IP Address |
| Database | MSFT SQL Instance |
| Storage | Storage Server |
| Middleware | Application Server |
| Virtualisation | VMware Virtual Machine Instance · ESX Server |
| Application / Service | Mapped / Calculated / Tag-Based / plain Application Service · Infrastructure Service · Business Application |
| Batch | Batch Job |
| Facilities / Power | UPS |
| Other infrastructure | Computer · Server · Hardware · Printer · Configuration Item |

Anything unmapped falls through to its **raw class name** rather than a catch-all bucket, so a class we
haven't seen shows up by name instead of disappearing into "Other".

> **This replaces the CMDB-derived version.** Feedback item #3 asked for impacted domain *for active
> incidents*, and that is now what it is. The earlier panel grouped server telemetry by support group
> because the incident CI fields were believed to be empty — see the correction in 2.11.

### 2.7 Application Health — APM (error rate & latency)
**Type:** Lens data table · **Index:** `metrics-apm*`, dataset `apm.service_transaction.1m`

One row per **business application × portfolio × environment**:

| Column | Meaning |
|---|---|
| Health | 🔴 RED ≥ 5% errors · 🟠 AMBER ≥ 1% · 🟢 GREEN below that |
| Business application | `ci.name` from the ServiceNow Business Application record, e.g. *Document Management Facility* |
| Portfolio | `ci.customer_specific.pm_portfolio`, e.g. *Policy Admin (Commercial and Specialty)* |
| Env | Normalised `service.environment` |
| Error rate % | Failed ÷ total transactions |
| Avg latency (ms) | Mean transaction duration |
| Failed txns / Transactions | The underlying counts |

**How the maths works.** `event.success_count` and `transaction.duration.summary` are
**`aggregate_metric_double`** fields — each document stores `{sum, value_count}` rather than a single
number. In ES|QL, `COUNT(field)` returns the summed `value_count` and `SUM(field)` the summed `sum`, so:

```
error rate    = (COUNT(event.success_count) − SUM(event.success_count)) / COUNT(event.success_count)
avg latency   = SUM(transaction.duration.summary) / COUNT(transaction.duration.summary)
```

This is exactly how Elastic's own APM UI derives failure rate, so the dashboard and the APM app agree.

**Sanity check after import:** if *Transactions* equals the raw document count on every row, this build
is not unwrapping `value_count` and the rates are wrong. Confirm with:

```esql
FROM metrics-apm*
| WHERE data_stream.dataset == "apm.service_transaction.1m"
| STATS docs = COUNT(*), txns = COUNT(event.success_count), ok = SUM(event.success_count)
```

`txns` should be well above `docs`.

**Drill-down into APM.** Click a value in the **APM service** column and that service's APM overview
opens in a new tab:

```
/app/apm/services/<service.name>/overview?rangeFrom=now-24h&rangeTo=now&environment=ENVIRONMENT_ALL
```

Two design constraints shape how this works, both worth knowing before anyone asks:

1. **The drilldown must be pinned to one column.** A Lens ES|QL table fires the click action on *every*
   column it treats as a dimension, so the drilldown was originally offered on cells whose value was
   never meant to reach the URL. Every column except `service.name` is now marked as a metric
   (`inMetricDimension`), which is what decides whether a cell is clickable, so the action appears on
   the **APM service** column alone.

   > *Correction.* An earlier version of this guide said Kibana only offers a drilldown on columns backed
   > by a real index field, and that `EVAL`/`STATS`-computed columns were inert. That is not true of ES|QL
   > tables — the client found the ServiceNow link offered on every column of the CI worklist. Wrapping a
   > column in `TO_STRING()` does not make it unclickable; marking it as a metric does.
2. **The link must key on `service.name`, not the business application name.** APM addresses services by
   `service.name` (`document management facility prod`); the ServiceNow Business Application name
   (`Document Management Facility`) would resolve to a service that does not exist in APM. The table
   shows the business application as the label and carries `service.name` as the clickable column
   beside it.

The table is consequently **one row per APM service**, with its business application shown alongside,
rather than one row per business application. Leadership reads the Business application and Health
columns; SRE clicks the APM service column to investigate.

> **Note on ES|QL tables:** the URL *field formatter* — the usual way to make a table cell a hyperlink —
> does not render as a link in ES|QL-backed Lens tables, only in data-view-backed ones. The URL drilldown
> is the supported route here, which is why the value opens on click rather than looking like a blue link.

**Application naming.** APM documents carry the CMDB *Business Application* enrichment — `ci.name`,
`ci.number` (`APM0003276`), `ci.customer_specific.pm_portfolio` and `ci.support_group.l2.name`. Panels
key on `COALESCE(ci.name, service.name)`, so services without enrichment still appear under their raw
APM service name rather than vanishing.

### Applications on Silent Servers (CMDB cross-reference)
**Type:** Lens data table · **Index:** `metrics-*` · **Location:** Operational Detail, beside *Coverage Gap*

The CMDB-derived view is kept, but demoted out of the executive band now that APM gives real application
health. It answers a different question: **which applications sit on servers that have gone silent**.
One row per application × environment from `ci.short_description`, with CIs down, CIs total, and
🔴 RED (all CIs down) vs 🟠 AMBER (partial impact). It sits beside *Coverage Gap — Monitored CIs Not
Reporting* because both read the same signal: an empty table is the good state.

### 2.8 Predictive Insights — 🚧 Coming Soon / In Progress
**Type:** Markdown tile (placeholder, as requested)

Reserves the slot and states the intended scope: alert-storm forecasting, disk-full / capacity prediction,
incident-volume forecasting, and anomaly-based early warning via Elastic ML. It also records the next
concrete step — create the ML forecast/anomaly jobs and land their output in a `predictive-insights-*`
index, then swap this markdown tile for a live Lens panel.

### 2.9 Monitored Estate — Coverage by Tier
**Type:** Lens data table · **Index:** `metrics-*`

Answers the question the team asked, directly: *what is actually being monitored?* One row per
infrastructure tier, derived from `data_stream.dataset`:

| Column | Meaning |
|---|---|
| Infrastructure tier | Servers (OS / Windows), Applications (APM), vSphere, Oracle, SQL, IBM MQ, GCP, Kubernetes, Prometheus, Monitoring stack |
| Data streams | How many datasets feed that tier |
| Distinct `host.name` | Reporting hosts — **the collector count for remotely-collected tiers**, not a device count |
| Documents in range | Volume in the dashboard time window |
| Mins since last doc | Freshness of that tier's collection |
| Collection | 🟢 Flowing (≤15 min) · 🟠 Delayed (≤60 min) · 🔴 Stalled |

This is a **collection-health** view, not per-device availability. Per-device availability for vSphere,
Oracle, MQ, GCP and Kubernetes needs each tier's own entity identifier (VM name, instance, queue manager,
resource id) instead of `host.name` — see the limitations section.

### 2.10 Application Estate — APM

**Type:** two Lens metrics + one data table · **Index:** `metrics-apm*`

| Panel | What it shows |
|---|---|
| **Applications Instrumented (APM)** | `COUNT_DISTINCT(service.name)` — the size of the observed application estate (508 services today) |
| **Applications in Production (APM)** | The same, restricted to `prd*` / `prod*` environments |
| **Application Estate — by environment** | Applications, document volume, minutes since last document and a 🟢/🟠/🔴 telemetry status, per normalised environment |

`service.environment` arrives inconsistently cased and suffixed — `prd`, `prd1`, `PRD`, `drt1`, `DRT2`,
`ete1`–`ete4`, `cut1`, `stg1`, and blank — so the panels normalise it with `TO_LOWER()` plus prefix
matching into Production · DR · ETE/Test · CUT · Stage · Dev · Sandbox · Unspecified · Other.

> **This is inventory and telemetry freshness, not application health.** See the limitations section for
> why a health panel needs one more field confirmation.

### 2.11 Affected CIs — Active P1 / P2 Incidents
**Type:** Lens data table · **Index:** `servicenow-open-incidents-snapshots-*`

*Renamed from "Impacted CIs" — see [Terminology](#01-terminology--affected-ci-vs-impacted-ci).*

The incident-side worklist: every open P1/P2 with the CI it landed on. Columns: **Sev · Incident ·
Affected CI · CI class · Business service · Env · Assigned to · Short description · Last seen · CMDB
record**.

#### Drill-down — direct CMDB record link (September 2026)

Clicking the **CMDB record** column opens that CI's record in ServiceNow:

```
https://cnaprod.service-now.com/nav_to.do?uri=cmdb_ci.do%3Fsys_id%3D<ci.sys_id>
```

`sys_id` is the CI's primary key, so ServiceNow resolves the record and renders it on **its own class
form** — a Windows server opens as a Windows server. That is what the team asked for when they said the
old link went to "the base link for the CI", and it needs no class parameter at all.

**Why there is a separate column for it.** A Kibana URL drilldown receives exactly **one** value: the
cell that was clicked. It cannot read the rest of the row. So whatever value the URL needs must *be* the
clicked cell — which means a column has to carry it. `Affected CI` stays clean and readable and is no
longer clickable; `cmdb_record` is the only clickable column and is width-capped at the end of the row.

*The alternative considered and rejected:* the class-scoped list URL the team sent
(`cmdb_ci_list.do?sysparm_query=name%3D…%5Esys_class_name%3D…`) needs **two** values, so the clicked cell
had to carry `vskau1p1328^sys_class_name=cmdb_ci_win_server` — accurate, but ugly in an executive table.
`sys_id` reaches the same record with one opaque reference id, which reads like the record pointer it is.

> **Check on import:** if the **CMDB record** column is blank, `ci.sys_id` is not populated on
> `servicenow-open-incidents-snapshots-*` and the link has nothing to key on. The fallback is the
> class-scoped list URL described above — say so and it goes back in.

**One row per incident × CI.** The source is a snapshot index. Grouping on the descriptive fields meant
an incident that was reassigned or re-described inside the dashboard window appeared twice — which is
why this table used to show 41 rows for 40 P2 incidents. It now groups on `number`, `ci.name` and
`priority` only, and collapses the descriptive columns with `VALUES(...)` + `MV_MAX(...)`. An incident
genuinely raised against two CIs still, correctly, shows twice.

**Correction:** an earlier version of this guide said `ci.name` was not populated on the incidents index,
and the Impacted Domain / Impacted Applications panels were built CMDB-derived as a result. That was
wrong. The index carries **340 fields**, including the full CI enrichment (`ci.name`, `ci.sys_id`,
`ci.class_name`, `ci.environment`, `ci.fqdn`, `ci.ip_address`, `ci.geo.*`, `ci.support_group.l2.name`)
plus `assignment_group.name` and `category.1/2`. The wrong conclusion came from an empty CSV export, not
from the data.


---

## 3. Operational Detail — NOC / SRE

> Everything below the *"🔧 Operational Detail"* banner is the pre-existing NOC content, unchanged
> except that the duplicate P1 tile was removed and its row re-flowed to three equal tiles.

### 3.1 KPI tiles — row 1

| Tile | Index | How it works |
|---|---|---|
| **Agent / Collector Health (%)** | `metrics-*` | Distinct `agent.name` seen in the **last 5 min** ÷ all distinct agents in the window. Detects metricbeat/agent death, which is the upstream cause of most coverage gaps. |
| **Total CIs Monitored** | `metrics-*` | `COUNT_DISTINCT(ci.name)` over CIs flagged `ci.is_monitored` and `Operational` — the denominator behind the coverage figures. |
| **CIs Not Reporting (>15 min)** | `metrics-*` | **Count** of monitored + Operational CIs whose **last seen** is older than 15 min. *Was Coverage Gap Risk (%) until September 2026; the team asked for the absolute number rather than a share, so it now reads "7 CIs" instead of "0.2 %". Pair it with the Total CIs tile to its left to recover the ratio.* |
| **Telemetry Freshness (max lag, min)** | `metrics-*` | `MAX(ingest_lag_in_sec) / 60`. Worst end-to-end pipeline delay in the window — how stale the *worst* number on this dashboard could be. |

### 3.2 KPI tiles — row 2 (server availability detail)

All four are scoped to `system.*` telemetry, same as panel 2.2 — they previously carried the same
unscoped denominator and so over-counted.

| Tile | How it works |
|---|---|
| **Total Servers Monitored** | `COUNT_DISTINCT(host.name)` across the time range |
| **Servers Up** | `COUNT_DISTINCT(host.name)` with a document in the last 15 min |
| **Servers Down** | Total − Up |
| **Servers Availability %** | Up ÷ Total, 1 decimal |

This is the NOC-level breakdown of the single executive figure in 2.2 — same definition, shown as its
component parts so an on-call engineer can see *how many* boxes, not just the percentage.

### 3.3 KPI tiles — row 3 (alert pipeline / noise)

| Tile | Index | How it works |
|---|---|---|
| **Raw Netcool Alerts (24h)** | `.ds-bridge-alerts-netcool-default-*` | Raw alert document count, last 24 h |
| **Correlated SN Events (24h)** | `.ds-logs-servicenow.event-default-*` | Events that survived correlation into ServiceNow |
| **Alert Dedup Ratio (24h)** | both, via `METADATA _index` | `(raw − correlated) ÷ raw` — the share of alert noise suppressed before it reached an analyst. Higher is better. |

### 3.4 Alert Volume Trend — hourly *(Storm-Prediction baseline)*
**Type:** Lens line chart · **Index:** `.ds-bridge-alerts-netcool-default-*`
Alert count bucketed hourly (`DATE_TRUNC(1 hour, @timestamp)`). This is the empirical baseline an
alert-storm forecast would be trained against — visible spikes are today's storm signal.

### 3.5 Telemetry Freshness Trend — max lag per hour (min)
**Type:** Lens line chart · **Index:** `metrics-*`
`MAX(ingest_lag_in_sec)` per hour, converted to minutes. A rising staircase = the ingest pipeline is
falling behind; a spike = a transient relay/backpressure event.

### 3.x Server Availability Trend — % of server estate reporting, per hour

**Type:** Lens line chart · **Index:** `metrics-*`, scoped to `system.*` · **Location:** between the
Servers Up / Down / Availability tiles and the Servers Down worklist

The **Server Availability %** tiles answer *"how many servers are up right now?"*. This answers *"has
that been getting better or worse?"* — one point per hour across the dashboard window.

**How it is computed.**

1. Every `system.*` metric document is bucketed to the hour it landed in.
2. A server counts as **up in that hour** if it produced at least one document in it. The distinct-host
   count is exact — a two-stage `STATS ... BY host.name, bucket` then `COUNT(*) BY bucket`, rather than
   `COUNT_DISTINCT` — so the line does not jitter from HyperLogLog estimation error the way a single
   approximate count would on a percentage axis.
3. The denominator, **estate**, is the busiest hour in the window: the largest number of servers seen
   reporting in any one hour.
4. `availability_pct = servers_up ÷ estate × 100`, rounded to two decimals.

The first and last buckets are dropped because both are partial — the window starts mid-hour and the
current hour is still filling. Without that the line always ends in a false cliff.

> **Reading it against the tile.** The trend and the **Servers Availability %** tile will not agree to
> the decimal, and that is expected: they answer different questions. The tile applies a **15-minute**
> silence rule at this instant; the trend asks whether a server reported **at any point in the hour**,
> which is more forgiving. Use the tile for *now*, the trend for *direction*.
>
> **What it cannot show.** A server that was down for the *entire* window produces no documents at all,
> so it lands in neither the numerator nor the denominator — availability still reads 100 % while that
> server is dead. The existing tiles share this blind spot, because they also take their total from the
> hosts seen in the window. Servers dead longer than the window are caught by **Coverage Gap — Monitored
> CIs Not Reporting**, which starts from the CMDB list rather than from telemetry.

*Implementation note:* ES|QL has no window functions, so the per-hour counts and the single estate figure
cannot be produced by one aggregation. The query packs each `(hour, servers_up)` pair into one long,
collapses to a single row to compute the estate, then re-expands with `MV_EXPAND`. It is the only panel on
the dashboard using that pattern — if it ever errors after an upgrade, that is the line to look at.

### 3.x Servers Down — Affected CIs (>15 min without telemetry)

**Type:** Lens data table · **Index:** `metrics-*`, scoped to `system.*` · **Location:** directly under the
Servers Up / Down / Availability tiles

The worklist behind the **Servers Down** tile. It uses the **same scope and window as that tile** —
`STARTS_WITH(data_stream.dataset, "system.")`, seen in the dashboard window but not in the last 15
minutes — so the row count and the tile agree. Deliberately no `ci.is_monitored` filter, because the tile
has none either.

**One row per host, by construction.** `last_seen` is `MAX(@timestamp)` grouped on **`host.name` alone**;
the CI columns are collapsed onto that one row with `VALUES(...)` + `MV_MAX(...)`. This matters — see the
fix note below.

| Column | Meaning |
|---|---|
| **Host** | `host.name` — **click to open the host in Observability → Infrastructure** |
| Affected CI | `ci.name`, the ServiceNow CI record for that server |
| CI class | Windows Server / Linux Server / AIX Server … |
| Application / purpose | `ci.short_description`. Shows `—` where the CMDB holds `uname` output instead of a real name (typical for Linux CIs) |
| Env | `ci.environment` |
| Location | `ci.geo.name` |
| Support group | `ci.support_group.l2.name` — who to call |
| Down (min) | Minutes since the last document, worst first |

Every column except `host.name` is marked as a metric, so the Infrastructure drilldown is offered on the
**Host** column alone.

> **On "affected CI":** this shows the CI *that is down* plus what the CMDB says it is for. It does **not**
> show downstream CIs that depend on it — that needs the `cmdb-ci-relations-*` graph joined to the host
> list, which ES|QL cannot do at query time on a 33.9M-edge index. It needs an ENRICH policy or a
> denormalising transform on the Elasticsearch side.

*Overlaps with* **Coverage Gap — Monitored CIs Not Reporting**, which covers all of `metrics-*` (not just
servers) and filters to monitored + Operational CIs. This panel is the server-specific, tile-matching view
with the drill-down.

#### Fixed September 2026 — phantom "down" servers

The client reported the **Servers Down** tile showing **0** while this table listed a screen of dead
servers, one of which (`kw3lniicsd002`) was demonstrably reporting CPU metrics a minute earlier.

The table used to group on **seven** keys: `host.name` *plus six CMDB enrichment attributes*
(`ci.name`, `ci.class_name`, `ci.environment`, `ci.geo.name`, `ci.support_group.l2.name`,
`ci.short_description`). Those attributes are **mutable**. When a CI's enrichment changes, every document
written before the change keeps the old values and every document after carries the new ones — so one
host becomes **two groups**. The group holding the superseded values has a `last_seen` frozen at the
moment of the change, sails through `WHERE last_seen < NOW() - 15 minutes`, and is rendered as a dead
server. The host is alive; only that combination of attribute values is.

The tell was in the data: every phantom row read **1,425–1,426 minutes down** — 23 h 45 m, landing a few
minutes inside a 24-hour window. That is not a fleet of servers failing independently, it is one bulk
CMDB update at a single moment, just inside the window's reach. All of them were Linux servers in the
same data centre under the same support group.

The **Servers Down** tile was never wrong: it counts `COUNT_DISTINCT(host.name)` with no attribute
grouping, so a host is one entity no matter how many times its metadata changed.

**The fix.** Group on `host.name` alone, then collapse the CI columns onto that row with `VALUES(...)` +
`MV_MAX(...)`. The table's definition of *down* is now identical to the tile's — no document in the last
15 minutes — so the two agree by construction rather than by coincidence.

> **The same defect exists in *Coverage Gap — Monitored CIs Not Reporting*** (§3.6), which groups on
> `ci.name`, `host.name`, `ci.geo.name` and `ci.support_group.l2.name`. A support-group rename or a data
> centre correction splits a CI the same way. It is not fixed here because the fix trades away a feature:
> the two descriptive columns would stop being index-backed and lose click-to-filter. *Applications on
> Silent Servers* had the same defect and **is** fixed, because its displayed columns do not change.

### 3.6 Coverage Gap — Monitored CIs Not Reporting (>15 min)
**Type:** Lens data table · **Index:** `metrics-*`
The actionable worklist behind the Coverage Gap Risk tile. Last-seen per CI, keeps anything older than
15 min, and shows **CI name · host · location · L2 support group · minutes stale**, worst first, top 100.

> ⚠️ **Known defect — same root cause as the Servers Down table.** This panel groups `last_seen` on
> `ci.name`, `host.name`, `ci.geo.name` and `ci.support_group.l2.name`. The last two are mutable CMDB
> attributes, so a support-group rename or a location correction splits one CI into two groups and the
> stale one is reported as not reporting. Treat long-stale rows with suspicion until this is fixed: check
> the host in Infrastructure before raising anything. The fix is the same shape as the one applied to
> Servers Down, but it costs click-to-filter on **Data Center** and **Support Team**, so it is being held
> for a decision.

*The Coverage Gap Risk tile above it is **not** affected* — it groups on `ci.name` alone, which is an
identity, not a description.
Click any cell to filter the whole dashboard to that CI/site/team.

### 3.7 Disk Saturation (>50 % used)
**Type:** Lens data table · **Index:** `.ds-metrics-system.filesystem-default*`
`MAX(system.filesystem.used.pct)` per **host × mount point**, filtered to >50 %, top 25 descending.
Threshold lives in the `WHERE disk_pct > 0.5` clause.

### 3.8 Network Errors (per interface)
**Type:** Lens data table · **Index:** `.ds-metrics-system.network-default*`
`MAX` of `system.network.in.errors` and `system.network.out.errors` per **host × interface**, summed into
a total, filtered to >0, top 25. Surfaces bad NICs, duplex mismatches and saturated links.

### Host drill-down — Disk Saturation & Network Errors

Clicking a **Host** on either panel opens that host in **Observability → Infrastructure**:

```
https://kibana-prod.gcp.cna.com/app/metrics/detail/host/<host>
```

Built the same way as the APM service drill-down: a URL drilldown on the panel, fired by a single click.

**Why the queries changed slightly.** Both panels previously grouped by *two* index
fields (`host.name` **and** the mount point / interface), which made the second column
clickable too and sent a mount point like `P:\` into the host URL. Each query now wraps that column in
`TO_STRING()`, and every column except `host.name` is marked as a metric, which is what actually stops a
cell being clickable — leaving `host.name` as the single actionable column.
`oneClickFilter` is off on the host column so the click opens the action menu rather than applying a
filter.

Nothing else on either panel changed — same thresholds, same limits, same columns, same position.

> **One thing to check on import:** the path `/app/metrics/detail/host/<host>` is the Observability
> Infrastructure host-detail route. If it 404s in your Kibana, the fix is a one-line edit to the
> drilldown URL template on each panel — everything else stays as is.

### 3.9 Ingest Pipeline Health — max lag per data source
**Type:** Lens data table · **Index:** `metrics-*`
Max lag, average lag and document count grouped by `data_stream.dataset` (system.filesystem,
system.network, system.cpu, …). Tells you *which* collector is the one dragging the freshness KPI down.

### 3.10 Noise Reduction — AI KPI status
**Type:** Markdown.
Documents why the *Noise Reduction Opportunity Score* KPI cannot be built from today's mappings
(no stable rule identifier, no dedup outcome, no analyst-feedback flag, no alert↔incident join key) and
what would close the gap. Kept so the KPI is visibly *tracked*, not silently dropped.

### 3.11 Quick links — Servers / Database / Middleware / Integration
**Type:** Markdown link tiles. Deep links into Discover / saved searches per platform
(Windows, Linux/UNIX, AIX, HPUX, …) so an engineer can jump from the dashboard to raw documents.

### 3.12 Notes & Data Limitations
**Type:** Markdown. The dashboard's own README — availability definition, how to re-tune thresholds,
where the domain/application attribution comes from, and the KPIs still blocked on source data.

---

## 4. Feedback → implementation traceability

| # | Team feedback | Delivered as | Status |
|---|---|---|---|
| 1 | Overall Infra Health as 🟢 / 🟠 / 🔴, derived from availability **and** active critical issues | Panel 2.1 *Overall Infrastructure Health* (single cross-index ES|QL over `metrics-*` + `servicenow-open-incidents-snapshots-*`) | ✅ Done |
| 2 | Active P1 count · Active P2 count | Panels 2.3 / 2.4 | ✅ Done |
| 3 | Impacted domain (Windows, Linux, Network, Database, Middleware, Storage…) for active incidents | Panel 2.6 *Impacted Domain* | ⚠️ Done **CMDB-derived**, not incident-derived — see §5 |
| 4 | Impacted applications: count + application health indicator | Panels 2.5 + 2.7, from real APM transaction health keyed on the ServiceNow Business Application name | ✅ Done |
| 5 | Infra Availability % KPI (e.g. 99.5 %) | Panel 2.2, renamed *Server Availability %*, plus panel 2.9 *Monitored Estate* | ✅ Done — scope now explicit |
| 6 | Predictive Insights placeholder tile ("Coming Soon / In Progress") | Panel 2.8 | ✅ Done |

---

## 5. Known gap — incident-side domain & application attribution

Items 3 and 4 above are currently computed from the **CMDB enrichment on the telemetry** rather than from
the incident records themselves, because the only fields confirmed to exist in
`servicenow-open-incidents-snapshots-*` today are `number` and `priority`:

* `ci.name` is **not** populated on the ServiceNow incident documents (confirmed by `ci_name_exists.csv`,
  which came back empty), so incidents cannot be joined to CMDB CIs on CI name.
* No category / assignment-group / business-service field has been confirmed on that index.

**What that means in practice:** the two panels answer *"which domains and applications have
infrastructure that has gone silent"*, which is a true impact signal — but they are not a breakdown of the
P1/P2 incidents themselves.

**To close it**, run this in Kibana → Discover → ES|QL and share the column list:

```esql
FROM servicenow-open-incidents-snapshots-*
| WHERE priority <= 2
| LIMIT 5
```

Once a domain/category field and a business-service/application field are confirmed, the two panels swap to
incident-based ES|QL, for example:

```esql
FROM servicenow-open-incidents-snapshots-*
| WHERE priority <= 2
| STATS p1 = COUNT_DISTINCT(CASE(priority == 1, number, null)),
        p2 = COUNT_DISTINCT(CASE(priority == 2, number, null))
  BY domain = <category_or_assignment_group_field>
| SORT p1 DESC, p2 DESC
```

Nothing else on the dashboard changes — the RAG tile already reads P1/P2 straight from that index.

---

## 6. Other known limitations (carried over)

* **"Up" = shipping telemetry.** A server that is powered on but whose metricbeat agent has died counts as
  down. That is intentional (it *is* a monitoring outage), but it is worth stating when presenting the
  availability number.
* **No per-device availability outside the server estate.** vSphere VMs, Oracle instances, MQ queue
  managers, GCP resources and Kubernetes objects are all collected remotely, so `host.name` is the
  collector. Measuring their availability needs each tier's own entity field; panel 2.9 shows collection
  health as the interim signal.
* **The APM application register is now on the dashboard** (panel 2.10). The CMDB-derived Impacted
  Applications panels (2.5 / 2.7) are kept because they answer a different question — *which applications
  sit on servers that have gone silent* — rather than being replaced by it.
