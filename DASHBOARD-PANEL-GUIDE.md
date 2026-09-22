# Operations Dashboard — Panel Guide

**Landing page:** `operation-dashboard.ndjson` → dashboard `ops-dashboard-consolidated-v1`
**Title:** *Operations Dashboard — Consolidated (Alert, Infra, Platform Health)*
**Default time range:** `now-24h` → `now` (saved with the dashboard) · **Auto-refresh:** every 60 s
**Panels:** 45 · every panel is *by value* (embedded in the dashboard), so importing that one NDJSON is the whole landing page.

Four **detail dashboards** sit behind it, each its own saved object and its own import — see
[§0.0 The dashboard family](#00-the-dashboard-family) for the inventory and
[§7 Detail dashboards](#7-detail-dashboards) for their panels.

---

## 0.0 The dashboard family

Five saved objects, five separate imports. The landing page answers *is anything wrong*; the detail
dashboards answer *what exactly*, each against a different index.

| Dashboard | File | Saved-object id | Panels | Source |
|---|---|---|---|---|
| **Operations Dashboard — Consolidated** | `operation-dashboard.ndjson` | `ops-dashboard-consolidated-v1` | 45 | `metrics-*`, `metrics-apm*`, `servicenow-open-incidents-snapshots-*`, Netcool + SN event streams |
| **Database Detail — CloudSQL PostgreSQL** | `database-postgresql-dashboard.ndjson` | `06a07662-c4fa-4074-981c-ff075c3c5da1` | 23 | `metrics-*` (`gcp.cloudsql_postgresql`) |
| **Database Detail — Microsoft SQL Server** | `database-mssql-dashboard.ndjson` | `db-detail-mssql-v1` | 10 | `metricbeat-*` |
| **Service Management — Incident Effectiveness** | `service-management-dashboard.ndjson` | `sm-incident-effectiveness-v1` | 10 | `servicenow-incidents-*` |
| **Availability — Synthetic Monitoring** | `synthetic-availability-dashboard.ndjson` | `availability-synthetics-v1` | 11 | `synthetics-*` |

**There is no Oracle or MySQL dashboard**, and that is a finding rather than an omission — see
[§7.5](#75-why-there-is-no-oracle-or-mysql-dashboard).

**Why they are separate saved objects.** Each detail dashboard imports and updates independently, so a
change to one cannot break the landing page. The CloudSQL dashboard in particular keeps the saved-object
id it was adapted from, which means re-importing it overwrites in place rather than leaving a duplicate.

---

## 0. Dashboard flow — four sections

The dashboard reads top to bottom as a narrative, each section answering the question the one above it
raises. Section headers are markdown banners on the dashboard itself.

| # | Section | Question it answers | Panels, in order |
|---|---|---|---|
| **1** | 🏢 **Executive Health** | *Is the business healthy right now?* | Overall Infrastructure Health · Server Availability % · Active P1 · Active P2 · Impacted Domain · Affected CIs · Application Health — APM |
| **2** | 🔧 **Operational Effectiveness** | *How is the estate actually running, and what needs hands on it?* | Total Servers · Servers Up · Servers Down · Servers Availability % · Server Availability Trend · Servers Down — Affected CIs · CPU Saturation · Memory Saturation · Disk Saturation · Network Errors |
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
proxy, though it was removed from the Affected CIs worklist in September 2026 — at 2.8 % coverage the
column was blank on almost every row.

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

The four detail dashboards (§0.0) import the same way, one file each, in any order — none of them depends
on the landing page or on each other. `database-postgresql-dashboard.ndjson` also carries the GCP
integration's data view, tags and 25 references it was adapted from; overwriting on import keeps its
existing id so it replaces the managed copy rather than sitting beside it.

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
| **Errors %** | Share of that tier's documents carrying an `error.message` |
| Mins since last doc | Freshness of that tier's collection |
| Collection | 🔴 All errors · 🔴 Mostly errors (≥50 %) · 🔴 Stalled (>60 min) · 🟠 Errors present (≥5 %) · 🟠 Delayed (>15 min) · 🟢 Flowing |

#### Fixed September 2026 — a tier emitting only errors read as healthy

**Database — Oracle** showed **🟢 Flowing**. Documents were arriving every 60 seconds, on schedule, from
two collectors — and every single one was a connection failure:

```
DPI-1047: Cannot locate a 64-bit Oracle Client library: "libclntsh.so: cannot open shared object file"
```

All 323 `oracle.*` metric fields are empty. The `sql` tier is the same input pointed at the same Oracle
database, failing the same way. The panel only measured **whether documents arrived**, never **whether
they contained anything** — so a completely broken integration was indistinguishable from a healthy one,
and had been for as long as it has been misconfigured.

The status now counts `error.message` per tier and **tests the error conditions before the staleness
ones**, so a tier that is punctually delivering nothing but failures reads 🔴 **All errors** at 100 %,
not 🟢 Flowing. The tier mapping itself is unchanged — nothing was reclassified.

*Why the threshold ladder:* a handful of transient errors in a healthy tier is normal, so ≥5 % turns it
amber rather than red, ≥50 % is red, and 100 % gets its own label because it means the integration has
never worked rather than that it is degrading.

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
Affected CI · CI class · Env · Assigned to · Short description**.

*Removed September 2026 at the team's request: **Business service** (populated on only 2.8 % of incidents,
so the column was blank on almost every row) and **Last seen**. `last_seen` is still computed — it is the
sort key that puts the newest incident first — it is simply no longer displayed.*

#### Drill-downs — two columns, two destinations

| Click | Action | Opens |
|---|---|---|
| **Incident** | *Open incident in ServiceNow* | `…/now/nav/ui/classic/params/target/incident_list.do%3Fsysparm_query%3Dnumber%253D<INC>` |
| **Affected CI** | *Open CI in ServiceNow CMDB* | `cmdb_ci_list.do?sysparm_query=name=<ci>` |

Both columns also offer **Filter for value**, so a click on an incident number can filter the whole
dashboard to that incident. Every other column is marked as a metric and is inert on click.

**The Incident column is now the raw `number` field**, not an `EVAL`-derived string. That matters: Kibana
can only build a dashboard filter from a column backed by a real index field, so the previous
`TO_STRING(number)` version could be drilled from but not filtered on.

> **Both drilldowns are offered on both columns.** Kibana attaches drilldowns to the *panel*, not to a
> column, and every one of them fires on the same value-click trigger. So clicking the Incident cell
> shows *Open incident* **and** *Open CI in CMDB*, and clicking the Affected CI cell shows both too. Pick
> the one that matches the column you clicked; the mismatched pair (a CI name sent to the incident list,
> or an incident number sent to the CI list) just returns an empty ServiceNow list. The column labels name
> the right action.

> **Filtering on an incident empties the `metrics-*` panels.** `number` exists only on
> `servicenow-open-incidents-snapshots-*`, so once that filter is applied every panel reading `metrics-*`
> matches nothing and renders blank until the filter is cleared. That is inherent to a cross-index
> dashboard filter, not a fault in the panel — the incident-side panels are the ones that stay meaningful.

#### `encode_url` — the bug behind every failed link

**Kibana's `encode_url` option percent-encodes the URL *after* the template is compiled, and `%` is one
of the characters it encodes.** A template that already contains percent-encoding is therefore mangled:
`%3F` becomes `%253F`, `%253D` becomes `%25253D`, and ServiceNow receives nonsense.

That single setting explains every link on this panel that failed:

| Link | Template contains `%XX`? | `encode_url` | Outcome |
|---|---|---|---|
| CI, name only — `…?sysparm_query=name={{event.value}}` | no | true | **Works.** Nothing for the encoder to damage |
| Attempt 1 — packed `name%3D…%5Esys_class_name%3D…` | yes | true | Broken |
| Attempt 2 — `nav_to.do?uri=cmdb_ci.do%3Fsys_id%3D…` | yes | true | Broken |
| Attempt 3 — `{{event.points}}` with `%3D` / `%5E` | yes | true | Broken |
| Incident — `…incident_list.do%3Fsysparm_query%3D…` | yes | **false** | **Works** |

**The rule:** if a URL template contains percent-encoding of its own, `encode_url` must be **off**. If it
contains none and the value might hold a space or an `&`, leave it **on** so the value is escaped. The two
drilldowns on this panel are deliberately set differently for exactly that reason.

> **A conclusion recorded here earlier was wrong.** This guide previously stated that Lens sends one point
> per cell click, and that a class-scoped CMDB link was therefore impossible. That was inferred from
> attempt 3 failing — but attempt 3's template carried `%3D` and `%5E` with `encode_url` on, so it was
> never a valid test of `event.points`. Whether Lens carries the whole row in the click context is still
> **unknown**. What *is* established: attempts 1 and 2 were mechanically sound and failed only because of
> the encoding setting, so the class-scoped CI link is very likely achievable with `encode_url` off.

#### Both drilldowns appear on both columns — this one is a real limit

Kibana attaches drilldowns to the **panel**, not to a column, and every drilldown fires on the same
value-click trigger. There is no per-column binding, so clicking **Incident** offers both actions and so
does clicking **Affected CI**. Each label names the column it belongs to; the mismatched pairing (a CI
name sent to the incident list, or an incident number sent to the CI list) opens an empty ServiceNow list
rather than the wrong record.

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

#### Fixed September 2026 — the last of the mutable-attribute bugs

This panel used to group `last_seen` on `ci.name`, `host.name`, `ci.geo.name` **and**
`ci.support_group.l2.name`. The last two are mutable CMDB attributes, so a support-group rename or a
location correction split one CI into two groups, and the group holding the superseded values kept a
`last_seen` frozen at the moment of the change — reported as a CI that had stopped reporting. Exactly the
defect that produced the phantom down-servers.

It now groups on **`ci.name` and `host.name` only** — both identities, not descriptions — and collapses
the two descriptive columns with `VALUES(...)` + `MV_MAX(...)`.

**The cost, as flagged before the change:** *Data Center* and *Support Team* are now computed columns
rather than index fields, so Kibana cannot build a working dashboard filter from them and they are no
longer clickable. **CI Name and Host still filter normally**, and the dashboard's own `ci.geo.name`,
`ci.support_group.l2.name` and `host.name` controls at the top of the page are unaffected — that is still
the better way to filter a whole dashboard to a site or a team. Nothing else on the panel changed.

*The Coverage Gap Risk tile above it was never affected* — it groups on `ci.name` alone, which is an
identity, not a description.

### 3.6b CPU Saturation (P90 ≥ 80 %) · Memory Saturation (P90 ≥ 85 %)
**Type:** Lens data tables ×2 · **Indices:** `.ds-metrics-system.cpu-default*`, `.ds-metrics-system.memory-default*`
**Location:** directly above Disk Saturation / Network Errors

Added September 2026. Both datasets cover **2,893 hosts** — the same hosts behind the availability
number — and neither was read by any panel until now. CPU and memory saturation are the two most
standard panels on an infrastructure dashboard; the data had been collected all along.

| Column | Meaning |
|---|---|
| **Host** | `host.name` — **click to open the host in Observability → Infrastructure** |
| Env | `ci.environment` |
| Support group | `ci.support_group.l2.name` — who to call |
| P90 % | The figure the threshold is applied to |
| Peak % | Worst single sample in the window |
| Avg % | Mean across the window |

**Why P90 and not peak.** Disk fills monotonically, so `MAX()` is the right summary for it. CPU and memory
are bursty — almost every host touches 100 % CPU for one sample at some point, so a peak-based threshold
would list the entire estate. P90 means *"at or above this level for at least 10 % of the window"*, which
is sustained pressure rather than a spike. Peak and average are shown alongside so a genuine spike is
still visible.

**Field choices, both deliberate:**

- **CPU uses `system.cpu.total.norm.pct`, not `system.cpu.total.pct`.** The un-normalised field is summed
  across cores, so a 16-core host at half load reads `8.0` — 800 %. The `norm` variant is 0–1 regardless
  of core count.
- **Memory uses `system.memory.actual.used.pct`, not `system.memory.used.pct`.** On a sample from this
  cluster a healthy host read **0.86** on `used.pct` and **0.52** on `actual.used.pct`. The difference is
  page cache, which Linux reclaims on demand. The naive field would have painted most of the estate red.

**Grouping is on `host.name` alone**, with `ci.environment` and the support group collapsed onto the row
via `VALUES(...)` + `MV_MAX(...)`. This is the same fix applied to the Servers Down worklist — grouping on
mutable CMDB attributes splits one host into several rows when its enrichment changes.

*Thresholds live in the `WHERE p90 >= 0.8` / `>= 0.85` clause of each panel.*

> **Both fields verified populated in this cluster.** `system.cpu.total.norm.pct` returns **703,279**
> values from `FROM .ds-metrics-system.cpu-default* | STATS n = COUNT(system.cpu.total.norm.pct)`, and
> `system.memory.actual.used.pct` was confirmed on a document sample. Neither panel rests on an assumed
> field name.
>
> *If a future agent upgrade ever drops the `norm` variant,* the equivalent is
> `system.cpu.total.pct / system.cpu.cores` — the same figure computed by hand.

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
| 3 | Impacted domain (Windows, Linux, Network, Database, Middleware, Storage…) for active incidents | Panel 2.6 *Impacted Domain*, incident-derived from `ci.class_name` on the snapshot index | ✅ Done — see §5 for the earlier, wrong reading of this index |
| 4 | Impacted applications: count + application health indicator | Panels 2.5 + 2.7, from real APM transaction health keyed on the ServiceNow Business Application name | ✅ Done |
| 5 | Infra Availability % KPI (e.g. 99.5 %) | Panel 2.2, renamed *Server Availability %*, plus panel 2.9 *Monitored Estate* | ✅ Done — scope now explicit |
| 6 | Predictive Insights placeholder tile ("Coming Soon / In Progress") | Panel 2.8 | ✅ Done |

---

## 5. Known gap — the Impacted CI side of the relationship

**An earlier version of this section was wrong and is worth correcting rather than quietly deleting.** It
recorded that `ci.name` was not populated on `servicenow-open-incidents-snapshots-*`, on the strength of a
`ci_name_exists.csv` export that came back empty, and that domain and application attribution therefore had
to be CMDB-derived. `ci.name` **is** populated, along with `ci.class_name`, `ci.environment`,
`assignment_group.name` and `short_description`. Panel 2.6 *Impacted Domain* and the *Affected CIs* worklist
are both **incident-derived** today: they read the incident record's own CI and map `ci.class_name` to a
domain (§2.6), with a `⚠️ No CI mapped` bucket for the incidents that genuinely carry no CI.

**What is still open is the other half of the terminology** (§0.1): the *Impacted* CIs — the downstream
dependents of an affected CI. That needs the CMDB relationship graph in `cmdb-ci-relations-000002`
(33.9M edges), which ES|QL cannot traverse at query time, and the incident record carries no rollup of its
own (`ci.parents.*` and `ci.top_level_parents.*` are mapped but populated on 0 documents). Closing it is an
Elasticsearch-side change — an ENRICH policy or a denormalising transform — not a dashboard one.

The *Impacted Applications* panels (2.5 / 2.7) remain CMDB-derived on purpose, and §6 says why.

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

---

## 7. Detail dashboards

Four saved objects behind the landing page. Each is its own import and its own index; none of them
touches `operation-dashboard.ndjson`.

### 7.1 Database Detail — CloudSQL PostgreSQL

**File:** `database-postgresql-dashboard.ndjson` · **Id:** `06a07662-c4fa-4074-981c-ff075c3c5da1`
**Panels:** 23 · **Source:** `metrics-*`, dataset `gcp.cloudsql_postgresql`

**22 instances across 4 GCP projects** — `spg` (prd + dr, main + control), `anomalo` (prd + dr), and
8 pre-production instances each in `ilap` and `rst`. All PostgreSQL 14, region `us-central`.

Keyed on **`gcp.labels.resource.database_id`**, never `host.name` — `host.name` here is the GKE
collector pod running the GCP integration, so keying on it would collapse all 22 instances into one.

This dashboard is the Elastic GCP integration's own, adapted. The top row is an availability band, then
a per-instance worklist, then the integration's charts.

**Row 1 — availability, four tiles.** They do not all answer the same question, and that is deliberate:

| Tile | What it counts | Window |
|---|---|---|
| **Database Availability %** | `AVG(database.up)` — the share of *checks* that reported up, formatted as a percentage | the time picker |
| **Instances Up** | Instances whose every sample in the last 15 min reported up | last 15 min |
| **Instances Down** | Instances that reported **down** at least once in the last 15 min | last 15 min |
| **Instances Silent** | Instances that sent **nothing** for 15 min — the collector lost them | last 15 min |

Up + Down + Silent = 22. An instance that is silent cannot also be counted up or down, because "down"
here means *CloudSQL said it was down*, not *we stopped hearing from it* — those are different failures
and they route to different people. **Availability % will not equal Up ÷ 22.** It is time-weighted over
the whole picker window, so an instance that was down for an hour of a 24-hour window and is up now
lowers the percentage while still counting under Instances Up.

**Row 2 — CloudSQL Instance Health**, the per-instance table with staleness and RAG. It ranks *which*
instance to look at before the charts below explain why. Its `health` column is the same logic as the
tiles, evaluated per instance and in this order:

| Status | Condition |
|---|---|
| 🔴 Silent | no document for > 15 min (`DATE_DIFF` on `MAX(@timestamp)`) |
| 🔴 Reported down | `MIN(database.up) == 0` anywhere in the window |
| 🔴 At risk | transaction-ID utilisation ≥ 90 % **or** disk ≥ 90 % |
| 🟠 Pressure | XID or disk ≥ 80 %, or CPU or memory ≥ 90 % |
| 🟢 Healthy | none of the above |

Silent is checked first, so an instance that stopped reporting is never shown as healthy on the strength
of its last good sample. **Reported down uses `MIN` over the whole window**, so it is sticky: one down
sample at any point in the picker window flags the row for the rest of that window. That is intentional
for a worklist — a database that bounced overnight is worth seeing — but it is why the table can show
"Reported down" while the Instances Down tile reads 0.

**The other 19 panels are the integration's work**, unchanged apart from Database Up being reformatted
as a percentage: uptime, CPU, memory quota and usage, disk bytes used / quota / read ops / write ops,
network sent and received, transaction count, connections, replication lag, and the Query Insights
breakdown (execution time, IO time, latencies, lock time).

> **Three panels render empty here, and that is expected, not a fault.**
> *Database Network Connections* — `network.connections.count` is not populated; `num_backends` is the
> connection count that works. *Replication Replica Lag* and *Replication Network Lag* —
> `replication.replica_lag.sec` is not populated, because none of the 22 instances has a read replica.

> **Removed: the Max Transaction-ID Utilisation tile.** It showed `MAX(transaction_id_utilization.pct)`
> across the fleet as a bare fraction — the share of PostgreSQL's ~2-billion transaction-ID space
> consumed before autovacuum must freeze old rows. The metric itself matters (at 100 % PostgreSQL stops
> accepting writes to protect itself), but a single unlabelled fleet-wide fraction is not how anyone
> would act on it, and the **CloudSQL Instance Health table already carries the same number per instance
> with RAG at 80 / 90 %**. The signal is kept where it is usable; the tile is gone.

> **Database Uptime is the weakest panel on this dashboard.** It averages `database.uptime.sec` across
> all 22 instances and prints raw seconds. Per instance, uptime is a genuinely useful restart detector —
> a sudden drop to near zero is an unplanned restart nobody filed a change for. Averaged across a fleet
> it is almost meaningless: one instance rebooting moves a multi-million-second average by a rounding
> error. The Instance Health table already shows `uptime_days` per instance. **Candidate for removal or
> for conversion to "instances restarted in the window".**

*The dashboard does not pin a time range*, unlike the others — it inherits whatever the picker holds.

### 7.2 Database Detail — Microsoft SQL Server

**File:** `database-mssql-dashboard.ndjson` · **Id:** `db-detail-mssql-v1`
**Panels:** 10 · **Source:** `metricbeat-*`

**390 instances across 333 servers**, keyed on `ci.name` (`INSTANCE@server`). 45 servers host more than
one instance. Nine environments, 45 % of instances in prod.

> **These documents are not in `metrics-*`.** They live in the legacy pre-data-stream `metricbeat-*`
> indices, which is why an earlier survey of this cluster concluded MSSQL was not collected at all. That
> conclusion was wrong, and the mistake is worth remembering: `metrics-*` is not the whole cluster.

Three metricsets feed it — `sql`/`query` (390 instances), `mssql`/`performance` (135) and
`mssql`/`transaction_log` (66). That spread is itself the headline finding, see below.

| Panel | What it shows |
|---|---|
| MSSQL Instances · Reporting Performance Metrics · Instances Failing Collection · Databases Never Log-Backed-Up | The four tiles |
| **Collection Failures** | Instances the collector cannot read, with endpoint, environment, DBA group and the error text |
| Instance Health | Peak connections, worst page life expectancy, buffer pool GB, temp tables, staleness, RAG on PLE |
| Throughput | Batch requests, logins, page splits and lock waits **per second** |
| **Transaction Log** | Per database: log fullness, allocated vs used, unbacked bytes, and backup age with its own RAG |
| Collection Coverage | Instances reporting per hour, by metricset |

**Three deliberate departures from the raw fields**, each of which would otherwise put a visibly wrong
number in front of a DBA:

1. **The `*_per_sec` fields are not rates.** `batch_requests_per_sec` sampled at **9,694,126** and
   `logins_per_sec` at **281,543**, with logouts almost identical — the giveaway that these are
   cumulative counters from `sys.dm_os_performance_counters` carrying a misleading name. Every one is
   read only as `MIN` and `MAX`, and shown as *(max − min) ÷ elapsed seconds*. **A counter reset from an
   instance restart inside the window will distort that row.**
2. **`buffer.cache_hit.pct` is omitted entirely.** It sampled at **2.2**, where a real buffer cache hit
   ratio is 95–99 %. The field is the raw counter without its `_base` divisor and cannot be corrected
   from the dashboard.
3. **`transaction_log.space_usage.used.pct` is already 0–100**, unlike the percentage fields everywhere
   else in this cluster. Verified against the byte fields: 52.9 MB of 39,240 MB reads `0.135`. No percent
   formatter is used anywhere on this dashboard — it would have rendered 39.74 % as 3,974 %.

> **The finding to act on.** 390 instances configured, 135 returning performance data. The sampled error
> is a SQL Server login failure for the monitoring service account, so roughly **255 instances have
> collection configured with credentials that do not work** — invisible until now because documents kept
> arriving. The Collection Failures panel routes to `IT.I.Database_Engineering_-_Microsoft_SQL_Server.DBA`.
>
> Separately, two of three sampled databases have **never had a transaction log backup** — the
> `backup_time` field carries SQL Server's 1900 sentinel. In FULL recovery model the log then grows until
> it fills the disk.

### 7.3 Service Management — Incident Effectiveness

**File:** `service-management-dashboard.ndjson` · **Id:** `sm-incident-effectiveness-v1`
**Panels:** 10 · **Source:** `servicenow-incidents-*` · **Window:** `now-7d` → `now`

The ITSM KPI set: **MTTR mean and P90, first-call resolution, reopen rate**, MTTR by priority, intake
channel, slowest assignment groups with service provider and reassignment rate, an MTTR trend, and
opened-versus-resolved per hour.

**`resolution_time` is pre-computed wall-clock seconds** and equals `resolved_at − opened_at` exactly —
verified to the second on three sampled incidents (72, 6250 and 248 seconds). MTTR needs no date
arithmetic and carries no business-hours assumption: it is elapsed time including nights and weekends.

**This is a different index from the landing page.** `servicenow-incidents-*` is one document per
incident (1.23M docs); the landing page reads `servicenow-open-incidents-snapshots-*`, which is 87.8M
documents of repeated snapshots. None of the de-duplication the landing-page panels need applies here.

**The window is 7 days, not 24 hours**, and deliberately so: it selects incidents *opened* in the
window, and a day is too small a sample for a stable MTTR. A long-running incident opened before the
window and resolved inside it does not appear.

> **SLA breach is not on this dashboard.** `has_breached_sla` and the whole `sla.*` tree are null even on
> resolved incidents — that data lives in the separate `servicenow-task-sla` index (199k docs), not yet
> wired up. There is also **no per-person resolver leaderboard**; the data supports one, and putting it
> on a dashboard is a different conversation from the one this answers.

### 7.4 Availability — Synthetic Monitoring

**File:** `synthetic-availability-dashboard.ndjson` · **Id:** `availability-synthetics-v1`
**Panels:** 11 · **Source:** `synthetics-*`

**This is the only real availability measurement in the family.** Every availability figure on the
landing page is *agent liveness* — is metricbeat still shipping. These are active checks against the
target from the Aurora observer locations.

Monitors configured · check success rate · monitors with failures · monitors broken by config →
availability by protocol and by observer location → **failing monitors, separating sustained outage from
flapping** → **TLS certificates by days to expiry** → slowest monitors by P50/P90 → hourly availability
trend split by protocol.

**Read the protocols separately. Never blend them.**

| Protocol | Monitors | Checks | Check availability |
|---|---|---|---|
| ICMP | 3,103 up / 32 down | 758,038 | **99.13 %** |
| HTTP | 228 up / 150 down | 14,935 | **67.49 %** |
| TCP | 36 up / 20 down | 1,738 | **57.08 %** |
| Browser | 0 up | 1,080 | **0.00 %** |

ICMP is 98 % of all checks, so a single combined figure would read ≈98.7 % and hide the other three
entirely. **ICMP covers essentially the whole server estate** — 3,103 monitors against 3,139 hosts on the
Total Servers tile.

**Two filters are applied to every rate on this dashboard:**

- `monitor.status IS NOT NULL` — synthetics indices hold per-step journey documents as well as per-check
  summaries, and only summaries carry a status. **744 step documents** would otherwise have been counted
  as checks.
- `error.code != "AGENT_NOT_BROWSER_CAPABLE"` — six browser monitors have failed continuously since
  **27 July 2026** because the agent cannot run browser journeys. That is a configuration fault, not an
  outage. They are excluded from the rates and counted on their own tile so the problem stays visible.
  *The TLS expiry panel deliberately omits this guard*, since it is not a rate.

> **An overstatement corrected.** Those broken monitors were initially described as something that would
> poison the availability metric. At **1,008 checks of 776,535 — 0.13 %** they would not have. They are
> still excluded, because a runner that cannot start is not an outage.

> **The decision this dashboard puts to you.** The landing page says *Server Availability 99.84 %* and
> means agents are reporting. ICMP says **99.13 %** and means hosts answer. Both are defensible, they
> measure different things, and they will never agree. The suggestion on the table is to relabel the
> landing-page tile *Telemetry Coverage* and promote ICMP as the real availability number.

### 7.5 Why there is no Oracle or MySQL dashboard

Neither can be built, and both reasons are worth recording.

**Oracle collects nothing.** All five `oracle.*` datasets and the `sql` dataset carry the same error on
every document:

```
DPI-1047: Cannot locate a 64-bit Oracle Client library: "libclntsh.so: cannot open shared object file"
```

**All 323 `oracle.*` metric fields are empty.** The ~2,850 documents per dataset per day are two
collectors — `lrch1e01` and `vslrau1p298` — logging a connection failure every 60 seconds. Installing the
Oracle Instant Client on those two hosts is the whole fix. Only one Oracle target is configured at all
(`drtora19c1-scan.cna.com:1522/oem135r.cna.com`), so even once fixed it would be one database.

This is what the estate panel's error-aware status now catches — see §2.9.

**MySQL and self-managed PostgreSQL emit nothing at all.** No `mysql.*` or `postgresql.*` dataset exists
under any naming. The only PostgreSQL is GCP CloudSQL, which has its own dashboard (§7.1).

> **Note the `sql` dataset is not MSSQL.** It is a second Metricbeat SQL input pointed at the same Oracle
> database, failing the same way on a 300-second interval. Real MSSQL lives in `metricbeat-*` (§7.2).
