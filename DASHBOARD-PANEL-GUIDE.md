# Operations Dashboard — Panel Guide

**Saved object:** `operation-dashboard.ndjson` → dashboard `ops-dashboard-consolidated-v1`
**Title:** *Operations Dashboard — Consolidated (Alert, Infra, Platform Health)*
**Default time range:** `now-24h` → `now` (saved with the dashboard) · **Auto-refresh:** every 60 s
**Panels:** 44 · every panel is *by value* (embedded in the dashboard), so importing this one NDJSON is the whole deployment.

---

## 0. Dashboard flow — four sections

The dashboard reads top to bottom as a narrative, each section answering the question the one above it
raises. Section headers are markdown banners on the dashboard itself.

| # | Section | Question it answers | Panels, in order |
|---|---|---|---|
| **1** | 🏢 **Executive Health** | *Is the business healthy right now?* | Overall Infrastructure Health · Server Availability % · Active P1 · Active P2 · Applications Degraded (Prod) · Impacted Domain · Impacted CIs · Application Health — APM |
| **2** | 🔧 **Operational Effectiveness** | *How is the estate actually running, and what needs hands on it?* | Total Servers · Servers Up · Servers Down · Servers Availability % · Server Availability Trend · Servers Down — Impacted CIs · Disk Saturation · Network Errors |
| **3** | 📡 **Monitoring Maturity** | *How much can we see, and can we trust sections 1 and 2?* | Monitored Estate by Tier · Business Applications Monitored · APM Services Instrumented · Application Estate by environment · Agent / Collector Health · Coverage Gap Risk · Telemetry Freshness · Telemetry Freshness Trend · Ingest Pipeline Health · Coverage Gap — CIs Not Reporting · Applications on Silent Servers |
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

## 0.1 How to import

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
| **Server availability %** | Servers shipping `system.*` telemetry in the last 15 min ÷ all such servers |
| **Servers down** | Count of servers with no telemetry in the last 15 min |
| **Active P1** | Distinct open ServiceNow P1 incident numbers — **all** infrastructure domains |
| **Active P2** | Distinct open ServiceNow P2 incident numbers — **all** infrastructure domains |

**RAG rules (hard-coded in the panel's ES|QL, easy to re-tune):**

| Status | Condition |
|---|---|
| 🔴 **RED** | any active **P1** (any domain) **OR** server availability **< 98 %** |
| 🟠 **AMBER** | any active **P2** (any domain) **OR** server availability **< 99.5 %** |
| 🟢 **GREEN** | no P1, no P2, server availability **≥ 99.5 %** |

Evaluation order is top-down, so RED always wins over AMBER.

*To change the thresholds:* open the panel → **Edit ES|QL** → change `98.0` / `99.5` in the
`EVAL infra_health = CASE(...)` block. No other panel needs touching.

### 2.2 Server Availability %
**Type:** Lens metric · **Index:** `metrics-*`, scoped to `system.*`

Denominator: distinct `host.name` shipping `system.*` telemetry anywhere in the dashboard time range
(~2,893 servers). Numerator: the same, restricted to hosts with a document in the **last 15 minutes**.
Displayed as a percentage with 2 decimals (e.g. `99.52%`), matching the example in the feedback.

> **Renamed** from *Infrastructure Availability %*. The KPI the team asked for is unchanged; the title now
> states its scope, because the number is a server-estate figure and the old name implied the whole estate.

"Up" therefore means *the server is still shipping metricbeat data*. It is an agent-liveness proxy for
availability — it does not require an extra uptime probe.

### 2.3 Active P1 Incidents · 2.4 Active P2 Incidents
**Type:** Lens metric ×2 · **Index:** `servicenow-open-incidents-snapshots-*`

`COUNT_DISTINCT(number)` filtered on `priority == 1` / `priority == 2`. Counting distinct **incident
numbers** (not documents) means the recurring open-incident snapshots do not inflate the number.

> These two tiles replace the old *"Active Critical Alerts (P1)"* tile, which has been removed to avoid
> showing the same figure twice.

### 2.5 Applications Degraded (Prod)
**Type:** Lens metric · **Index:** `metrics-apm*`

Production business applications whose APM **error rate is 1% or worse** over the dashboard window.
This is real transaction health, not a proxy.

### 2.6 Impacted Domain — Active P1 / P2 Incidents
**Type:** Lens data table · **Index:** `servicenow-open-incidents-snapshots-*`

Which technology domain the open P1s and P2s are actually landing in. Columns: **Status · Domain · P1 ·
P2 · Incidents · Impacted CIs**, worst-first.

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

1. **Kibana only offers a drilldown on columns backed by a real index field.** Values produced by `EVAL`
   or `STATS` are not index-backed, so they cannot be clicked through. `service.name` is therefore
   grouped raw and stays actionable, while Business application, Portfolio, Env and every metric are
   computed and inert on click. That is deliberate — a stray click on the wrong column cannot open a
   broken APM page.
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

### 2.11 Impacted CIs — Active P1 / P2 Incidents
**Type:** Lens data table · **Index:** `servicenow-open-incidents-snapshots-*`

The incident-side worklist: every open P1/P2 with the CI it landed on. Columns: **Sev · Incident ·
Impacted CI · CI class · Env · Assigned to · Short description · Last seen**.

**Drill-down:** click an **Impacted CI** to open that CI in the ServiceNow CMDB
(`https://cnaprod.service-now.com/cmdb_ci_list.do?sysparm_query=name=<ci>`), where the Affected CIs and
relationship tabs live. As with the APM table, only `ci.name` is grouped raw so it is the single
drilldown-actionable column — every other column is passed through `TO_STRING()`/`CASE()` and is inert
on click, so a stray click cannot open the wrong record.

**Correction:** an earlier version of this guide said `ci.name` was not populated on the incidents index,
and the Impacted Domain / Impacted Applications panels were built CMDB-derived as a result. That was
wrong. The index carries **340 fields**, including the full CI enrichment (`ci.name`, `ci.sys_id`,
`ci.class_name`, `ci.environment`, `ci.fqdn`, `ci.ip_address`, `ci.geo.*`, `ci.support_group.l2.name`)
plus `assignment_group.name` and `category.1/2`. The wrong conclusion came from an empty CSV export, not
from the data.

*Caveat:* the source is a snapshot index, so an incident reassigned or re-described inside the dashboard
window can appear on more than one row; the newest sorts first.

---

## 3. Operational Detail — NOC / SRE

> Everything below the *"🔧 Operational Detail"* banner is the pre-existing NOC content, unchanged
> except that the duplicate P1 tile was removed and its row re-flowed to three equal tiles.

### 3.1 KPI tiles — row 1

| Tile | Index | How it works |
|---|---|---|
| **Agent / Collector Health (%)** | `metrics-*` | Distinct `agent.name` seen in the **last 5 min** ÷ all distinct agents in the window. Detects metricbeat/agent death, which is the upstream cause of most coverage gaps. |
| **Coverage Gap Risk (%)** | `metrics-*` | Of all monitored + Operational CIs, the share whose **last seen** is older than 15 min. The blind-spot rate for the monitoring estate. |
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

### 3.x Servers Down — Impacted CIs (>15 min without telemetry)

**Type:** Lens data table · **Index:** `metrics-*`, scoped to `system.*` · **Location:** directly under the
Servers Up / Down / Availability tiles

The worklist behind the **Servers Down** tile. It uses the **same scope and window as that tile** —
`STARTS_WITH(data_stream.dataset, "system.")`, seen in the dashboard window but not in the last 15
minutes — so the row count and the tile agree. Deliberately no `ci.is_monitored` filter, because the tile
has none either.

| Column | Meaning |
|---|---|
| **Host** | `host.name` — **click to open the host in Observability → Infrastructure** |
| Impacted CI | `ci.name`, the ServiceNow CI record for that server |
| CI class | Windows Server / Linux Server / AIX Server … |
| Application / purpose | `ci.short_description`. Shows `—` where the CMDB holds `uname` output instead of a real name (typical for Linux CIs) |
| Env | `ci.environment` |
| Location | `ci.geo.name` |
| Support group | `ci.support_group.l2.name` — who to call |
| Down (min) | Minutes since the last document, worst first |

Only `host.name` is grouped raw, so it is the single drilldown-actionable column; every other column
passes through `TO_STRING()` or `CASE()` and is inert on click.

> **On "impacted CI":** this shows the CI *that is down* plus what the CMDB says it is for. It does **not**
> show downstream CIs that depend on it — that needs the `cmdb-ci-relations-*` graph joined to the host
> list, which ES|QL cannot do at query time on a 33.9M-edge index. It needs an ENRICH policy or a
> denormalising transform on the Elasticsearch side.

*Overlaps with* **Coverage Gap — Monitored CIs Not Reporting**, which covers all of `metrics-*` (not just
servers) and filters to monitored + Operational CIs. This panel is the server-specific, tile-matching view
with the drill-down.

### 3.6 Coverage Gap — Monitored CIs Not Reporting (>15 min)
**Type:** Lens data table · **Index:** `metrics-*`
The actionable worklist behind the Coverage Gap Risk tile. Last-seen per CI, keeps anything older than
15 min, and shows **CI name · host · location · L2 support group · minutes stale**, worst first, top 100.
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

**Why the queries changed slightly.** Kibana only offers a drilldown on columns backed by a real index
field — values produced by `EVAL` or `STATS` are not. Both panels previously grouped by *two* index
fields (`host.name` **and** the mount point / interface), which would have made the second column
clickable too and sent a mount point like `P:\` into the host URL. Each query now wraps that column in
`TO_STRING()` so it becomes computed and inert, leaving `host.name` as the single actionable column.
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
