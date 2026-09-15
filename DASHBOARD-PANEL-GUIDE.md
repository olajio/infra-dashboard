# Operations Dashboard — Panel Guide

**Saved object:** `operation-dashboard.ndjson` → dashboard `ops-dashboard-consolidated-v1`
**Title:** *Operations Dashboard — Consolidated (Alert, Infra, Platform Health)*
**Default time range:** `now-24h` → `now` (saved with the dashboard) · **Auto-refresh:** every 60 s
**Panels:** 34 · every panel is *by value* (embedded in the dashboard), so importing this one NDJSON is the whole deployment.

---

## 0. How to import

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

### 2.5 Impacted Applications  *(count tile)*
**Type:** Lens metric · **Index:** `metrics-*`

Number of distinct **business systems / applications that have at least one CI not reporting** for >15 min.

How the application name is resolved: the CMDB enrichment on every metric document carries
`ci.short_description` — the ServiceNow CI short description (e.g. *ImageRight*, *FileNet Server*,
*Exchange*, *Citrix XenApp Servers*, *CNA Canada Insurance System DB Server*). The query:

1. keeps only monitored, Operational CIs,
2. drops descriptions that begin with `Linux ` — on Linux CIs the field usually holds raw `uname` output
   rather than an application name, so those would be noise,
3. rolls up to **last-seen per CI**, keeps the stale ones, and counts distinct applications.

### 2.6 Impacted Domain — Infrastructure Health by Domain
**Type:** Lens data table · **Index:** `metrics-*`

Answers *"which technology domain is hurting right now?"*. Columns: **Domain · Impacted CIs · Total CIs ·
Availability % · Health**, sorted worst-first, with the same 🟢/🟠/🔴 wording as the executive tile
(GREEN = 0 impacted, AMBER = ≥98 % available, RED = below that).

Domain is derived per CI, first match wins:

| Domain shown | Derived from |
|---|---|
| Database | `ci.support_group.l2.name` starts with `IT.I.Exadata` |
| Network / Boundary | starts with `IT.Sec.Boundary` |
| Security / SIEM | starts with `IT.Sec.SIEM` |
| Security / IAM | starts with `IT.Sec` (catch-all for the remaining security groups) |
| Cloud / GCP | starts with `IT.I.GCP` |
| Windows | `ci.class_name == "Windows Server"` |
| Linux / UNIX | `ci.class_name == "Linux Server"` |
| Other / Unclassified | everything else |

*To add a domain* (Middleware, Storage, …) add one more `STARTS_WITH(ci_group, "<prefix>"), "<Domain>"`
pair at the top of the `EVAL domain = CASE(...)` block.

### 2.7 Impacted Applications — Business Impact
**Type:** Lens data table · **Index:** `metrics-*`

The drill-down behind tile 2.5 — one row per **application × environment**, only where something is down:

| Column | Meaning |
|---|---|
| Application / Business system | `ci.short_description` from the CMDB enrichment |
| Env | `ci.environment` — prod, drt, cut, ete, dre, dev, test, sandbox, eit |
| CIs down | CIs for that application with no telemetry in 15 min |
| CIs total | CIs mapped to that application |
| App health | 🔴 **RED — all CIs down** (application fully dark) vs 🟠 **AMBER — partial impact** (redundancy still carrying it) |

Sorted by *CIs down* descending, top 50. **An empty table is the good state** — it means no application
has a silent CI. Splitting by environment lets leadership separate a *prod* outage from *drt/dev* noise
at a glance.

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
| 4 | Impacted applications: count + application health indicator | Panels 2.5 + 2.7 | ⚠️ Done **CMDB-derived** (`ci.short_description`) — see §5 |
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

* **MTTA** — blocked: `acknowledged_at` / `assigned_at` / `assigned_by` are not in `servicenow-incidents-*`.
  Needs a ServiceNow Business Rule to write the Acknowledge state-change timestamp plus a mapping update.
* **Noise Reduction Opportunity Score** — blocked; see panel 3.10 for the full reasoning.
* **Environment scope** — availability and impact figures currently span **all** environments (prod, drt,
  cut, ete, dre, dev, test, sandbox, eit). If leadership wants the executive row to be prod-only, add a
  `ci.environment` control next to the existing three, or add `AND ci.environment == "prod"` to the
  executive panels' `WHERE` clauses.
* **"Up" = shipping telemetry.** A server that is powered on but whose metricbeat agent has died counts as
  down. That is intentional (it *is* a monitoring outage), but it is worth stating when presenting the
  availability number.
* **No per-device availability outside the server estate.** vSphere VMs, Oracle instances, MQ queue
  managers, GCP resources and Kubernetes objects are all collected remotely, so `host.name` is the
  collector. Measuring their availability needs each tier's own entity field; panel 2.9 shows collection
  health as the interim signal.
* **508 `apm.app.*` data streams exist** — a real, named application register (`cnacentral`, `claimecm`,
  `ilap_pricing_api`, `billigportal`, …). That is a materially better source for the Impacted Applications
  panels than the CMDB `ci.short_description` free text they use today, and worth a follow-up.
