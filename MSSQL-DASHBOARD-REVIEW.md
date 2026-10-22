# Review: "mssql trial" dashboard (22 Oct 2026)

*Reviewed: `msql_trial.ndjson`, 26 panels in 7 sections. It was compared against the team feedback (`DB Dahsbaord.docx`)
and the KPI document (`Executive Summary Row.docx`). The corrected queries were checked on Elasticsearch 9.5.3 with
test data.*

## In short

**The direction is right.** The sections follow the team's structure, the panels use ES|QL, and most panels have a
description written for the DBA. **Several headline numbers are wrong or misleading**, though, and those should be
fixed before DBAs rely on it:

1. ***Database Availability (%)* is a fixed number (96.34 %).** Both gauges are drawn from a value typed into the
   chart; they read no data.
2. **Databases are counted by name only.** `master`, `tempdb`, `msdb`, `model` (and any name reused across
   instances) collapse into one database, so totals, states and lists undercount.
3. **"Current" panels count every state seen in the time range.** A database that was offline yesterday and is
   online now still counts as *Unhealthy*, and appears in both *Online* and *Offline*.
4. **Sums and averages over repeated samples.** *SQL Servers Consuming the Most Storage* adds up every sample, so a
   server with 96 samples in the window shows 96 × its size.
5. **Reachability is always 100 %.** The query only keeps rows that have a state, then checks whether they have a
   state.

With test data (two servers, both with `master`; one database offline 3 h ago and back online; one offline now; one
server silent for 30 min):

| Panel | Dashboard shows | Correct |
|---|---|---|
| Total MSSQL Databases | 3 | **4** |
| Unhealthy Databases | 2 | **1** offline (+ 1 not reporting) |
| SQL Servers Consuming the Most Storage (srv1) | 64 GB | **16 GB** |
| Reachability | 100 % | **75 %** (1 of 4 not reporting) |

## What works well

- **The structure follows the team feedback:** Executive Summary → Availability → Connections → Query → Locking →
  Storage → Backup.
- **Every panel has a description** that says why it matters, as the KPI document asks.
- **Action queues, not just charts.** *Databases Requiring Immediate Investigation*, *Storage Risk Action Queue* and
  *Backup Investigation Queue* all fit "focus on exceptions".
- **The query gap is said out loud.** The *Query Performance* placeholders state that the data is missing, rather
  than showing a misleading chart.

## Must fix (correctness)

| # | Panel(s) | Problem | Fix |
|---|---|---|---|
| 1 | *Database Availability (%)* ×2 | Hard-coded `availability = 96.34` in the Vega spec | Replace with a Lens metric / gauge on the "current state" query below (`availability_pct`) |
| 2 | Every panel using `COUNT_DISTINCT(mssql.database.name)` or `BY mssql.database.name` | Same database name on different instances is counted once | Identify a database as **instance + name**, e.g. `CONCAT(ci.name, " / ", mssql.database.name)` |
| 3 | *Database State*, *Unhealthy*, *Databases Requiring Immediate Investigation*, *Database Service Health*, *Servers Requiring Investigation* | They count any state seen in the time range, not the current one | Take each database's **latest** record (query A below) |
| 4 | *Reachability* | Always 100 % | Databases that reported in the last 15 min ÷ databases seen in the last 24 h (query A gives `not_reporting`) |
| 5 | *SQL Servers Consuming the Most Storage* | `SUM` over every sample in the time range | Latest size per database, then sum per server (query C) |
| 6 | *Storage Critical Databases*, *Storage Risk Action Queue* | `AVG` log usage over the time range hides the current value; thresholds differ (70 % in one, 85 % in another) | Latest value per database; use the KPI document's bands: > 95 Critical, 85–95 High, 70–85 Medium (query B) |
| 7 | *Index Fragmentation Hotspots*, *Locking & Blocking Risk Servers* | Fields named `…_per_sec` are often **cumulative counters** in the SQL Server integration (SQL Server reports per-second counters as running totals). Then `AVG` ranks servers by uptime, not activity | Check with query V4; if they only go up, use (last − first) ÷ seconds (query D) |
| 8 | All panels | `FROM metric*` reads **every** metrics index in the cluster | Use the SQL Server data stream(s) found by query V1 |

## Should fix (clarity and consistency)

- **Duplicates:**
  - *Database Availability (%)* and *Database State* appear in two sections.
  - *Database Service Health* and *Servers Requiring Investigation* run the same query.
  - *Top 10 Fastest Growing Databases* and *Backup Investigation Queue* show the same metric.
- **Names that don't match the data:**
  - *Largest Databases by Storage Consumption* and *SQL Servers Consuming the Most Storage* measure only the
    **transaction log**, not data files.
  - *Top 10 Fastest Growing Databases* shows log written **since the last backup**, not growth over time.
  - *Databases with Oldest Backups* shows the last **log** backup only.
- **Labels and typos:**
  - Column names are raw fields (`affected_dbs`, `growth_gb`, `mssql.database.name`).
  - Typos: "Unhealthy Dtabase", "Occurance", "Serers".
  - Four metric tiles have no title.
- **Colours:**
  - Most tiles use the same yellow whatever the value. Use green / amber / red thresholds (e.g. Unhealthy: 0 green,
    ≥ 1 red).
  - The availability thresholds differ between panels (99.5 / 99 in the gauge, 98 / 99 in the tile).
- **Time:**
  - No default time range is saved, and no panel has its own range, so every number changes with the time picker.
  - "Current" KPIs should use a fixed short window (last 15 min) in the query.
  - Trends and top-N lists can follow the picker.
- **All sections are collapsed** when the dashboard opens. Open at least the Executive Summary.
- **No filter controls.** Add SQL Server instance and database controls, so a DBA can drill into one server (the
  "drill-down navigation" principle).
- ***Databases Requiring Immediate Investigation*** shows "Occurrence" (how many samples): replace it with "since"
  (first time in the current state) or "minutes ago".
- **Restoring isn't always a problem.** It is normal for log-shipping or AG secondaries, so list it separately from
  Offline / Suspect / Recovery Pending. The Executive Summary includes *recovering* while the other panels don't:
  align the lists.

## Coverage against the team feedback

| Area (feedback / KPI document) | In the dashboard | Gap / suggestion |
|---|---|---|
| Executive Summary: total DBs, availability, unhealthy, log risk | ✅ (but see fixes 1–3) | — |
| Executive Summary: **Critical alerts**, **P1 / P2 incidents** | ❌ | Netcool / Elastic alerts and ServiceNow incidents on the SQL CIs (both already in Elastic: MIM V3 uses them) |
| Executive Summary: **Failed backups**, **Replication issues** | ❌ | Need a source (below) |
| Availability: reachability, uptime %, state, service health | ⚠️ (reachability broken; no uptime %) | Query A; uptime % = share of samples Online over 24 h |
| Connections: active, top servers | ✅ | Show the latest total, not the highest single value in the range |
| Connections: saturation %, rejected connections, failed logins | ❌ | Saturation needs the max-connections setting; failed logins come from the SQL Server error log (event 18456) via the logs integration |
| Query performance: latency, slow / top queries, timeouts | ❌ (placeholders) | **Elastic APM already records database calls**: `traces-apm*` spans with `span.db.type: sql` give the slowest statements and failing calls per service. Query Store / DMVs need a custom SQL query |
| Locking: deadlocks, lock waits, blocking sessions, long transactions | ⚠️ (lock waits only) | Deadlocks counter if collected; blocking sessions / long transactions need a custom SQL query (sys.dm_exec_requests) |
| Storage: tablespace / data files, disk, growth rate, days to full | ⚠️ (log only) | Data-file size and free space (custom query or OS disk metrics of the SQL host); growth = latest − value 7 days ago |
| Backups: success %, failed, last full backup, SLA | ⚠️ (last log backup only) | Commvault / Control-M (as the feedback says), or msdb `backupset` via a custom SQL query |
| Replication: AG / log shipping status and lag | ❌ | AG DMVs via a custom SQL query (`sys.dm_hadr_database_replica_states`) |
| Server resource health (CPU, memory, disk, network) | ❌ | Reuse the system metrics of the SQL hosts (already collected), or link to the Infra Dashboard |
| Application dependency (Application → Middleware → Database) | ❌ | `cmdb-ci-relations*` links SQL instances to applications (MIM V3's *Database View* already reads it). APM `service_destination` shows which services call each database |
| **Hotspot panel** ("where to focus first") | ❌ | One ranked table built from the queries below: unhealthy state, not reporting, log > 85 %, high lock waits, log growth since backup |
| Oracle | ❌ | This dashboard is SQL Server only; the feedback covers Oracle too (OEM). Say so in the title, or plan a second dashboard |

## Suggested V1 layout

1. **Hotspots** (top, open): one ranked table, with columns database · issue · severity · since.
2. **Executive Summary:** total databases, availability %, unhealthy, not reporting, log > 85 %, P1 / P2 incidents on
   SQL CIs, open critical alerts.
3. **Availability & Health:** current-state table (query A), with a state breakdown.
4. **Storage & Log:** query B, plus log size per server (query C).
5. **Activity:** connections, lock waits, page splits (per-second rates, query D) per instance.
6. **Backups:** last log backup age, with full backups once a source exists.
7. **Application impact:** applications using each SQL instance (CMDB), and APM database calls.

## Corrected queries (checked on Elasticsearch 9.5.3)

Replace `metric*` with the SQL Server data stream from V1.

**A. Current state per database, and the summary tiles**
```
FROM metric*
| WHERE @timestamp >= NOW() - 24 hours AND mssql.database.name IS NOT NULL AND mssql.database.state IS NOT NULL
| EVAL db = CONCAT(TO_STRING(ci.name), " / ", TO_STRING(mssql.database.name)),
       rec = CONCAT(TO_STRING(TO_LONG(@timestamp)), "|", TO_UPPER(TO_STRING(mssql.database.state)))
| STATS latest = MAX(rec), last_seen = MAX(@timestamp) BY db
| DISSECT latest "%{ts}|%{state}"
| EVAL silent_min = DATE_DIFF("minutes", last_seen, NOW()),
       status = CASE(silent_min > 15, "NOT REPORTING", state)
| KEEP db, status, silent_min | SORT db
```
For the tiles, replace the last line with:
```
| STATS total = COUNT(*), online = COUNT(CASE(status == "ONLINE", 1)),
        unhealthy = COUNT(CASE(status IN ("OFFLINE", "RECOVERY_PENDING", "SUSPECT", "EMERGENCY"), 1)),
        not_reporting = COUNT(CASE(status == "NOT REPORTING", 1))
| EVAL availability_pct = ROUND(online * 100.0 / total, 2)
```

**B. Transaction log usage now, with severity**
```
FROM metric*
| WHERE @timestamp >= NOW() - 15 minutes AND mssql.transaction_log.space_usage.used.pct IS NOT NULL
| EVAL db = CONCAT(TO_STRING(ci.name), " / ", TO_STRING(mssql.database.name)),
       rec = CONCAT(TO_STRING(TO_LONG(@timestamp)), "|", TO_STRING(mssql.transaction_log.space_usage.used.pct))
| STATS latest = MAX(rec) BY db
| DISSECT latest "%{ts}|%{pct}"
| EVAL log_used_pct = ROUND(TO_DOUBLE(pct), 1),
       severity = CASE(log_used_pct > 95, "Critical", log_used_pct >= 85, "High", log_used_pct >= 70, "Medium", "Low")
| WHERE log_used_pct >= 70
| SORT log_used_pct DESC
| KEEP db, log_used_pct, severity
```

**C. Log size per server (latest per database, then summed)**
```
FROM metric*
| WHERE @timestamp >= NOW() - 15 minutes AND mssql.transaction_log.stats.total_size.bytes IS NOT NULL
| STATS size = MAX(mssql.transaction_log.stats.total_size.bytes) BY ci.name, mssql.database.name
| STATS log_size_gb = ROUND(SUM(size) / 1073741824, 2), databases = COUNT(*) BY ci.name
| SORT log_size_gb DESC
```

**D. Lock waits per second from a cumulative counter (only if V4 confirms it is cumulative)**
```
FROM metric*
| WHERE @timestamp >= NOW() - 1 hour AND mssql.performance.lock_waits_per_sec IS NOT NULL
| STATS first_v = MIN(mssql.performance.lock_waits_per_sec), last_v = MAX(mssql.performance.lock_waits_per_sec),
        t0 = MIN(@timestamp), t1 = MAX(@timestamp), connections = MAX(mssql.performance.user_connections) BY ci.name
| EVAL lock_waits_per_sec = ROUND((last_v - first_v) * 1.0 / GREATEST(DATE_DIFF("seconds", t0, t1), 1), 2)
| SORT lock_waits_per_sec DESC
| KEEP ci.name, lock_waits_per_sec, connections
```

## Check on the real data first (Dev Tools, `POST /_query?format=txt`)

| # | Checks | Query |
|---|---|---|
| V1 | Which indices hold the SQL Server data | `FROM metric* METADATA _index \| WHERE @timestamp >= NOW() - 1 hour AND mssql.database.name IS NOT NULL \| STATS docs = COUNT(*) BY _index` |
| V2 | Database names shared by several instances (fix 2) | see below |
| V3 | The real state values and their case (the queries use lower case) | `FROM metric* \| WHERE @timestamp >= NOW() - 1 hour \| STATS dbs = COUNT(*) BY mssql.database.state` |
| V4 | Whether `…_per_sec` fields only go up (fix 7) | see below (put one SQL Server instance name in) |

**V2**
```
FROM metric*
| WHERE @timestamp >= NOW() - 24 hours AND mssql.database.name IS NOT NULL
| STATS servers = COUNT_DISTINCT(ci.name) BY mssql.database.name
| WHERE servers > 1
| SORT servers DESC
| LIMIT 20
```

**V4**
```
FROM metric*
| WHERE ci.name == "<one SQL Server instance>" AND mssql.performance.lock_waits_per_sec IS NOT NULL
| STATS lowest = MIN(mssql.performance.lock_waits_per_sec), highest = MAX(mssql.performance.lock_waits_per_sec) BY bucket = BUCKET(@timestamp, 1 hour)
| SORT bucket
```
If `lowest` keeps rising from one hour to the next, the field is a running total.
