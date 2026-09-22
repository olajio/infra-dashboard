Let me look at what those Server dashboards actually are, and what database telemetry exists.

I studied what I could, and the answer is **no — not with what's in the cluster today.** Two separate blockers.

## Blocker 1: I can't see the Server detail dashboards

The Windows / Linux / AIX / HPUX links are Kibana short URLs into your instance:

```
https://kibana-prod.gcp.cna.com/app/r/s/Lu97N   (Windows)
…/BxPH2 (Linux)  …/Gr9nf (AIX)  …/c3A0T (HPUX)
```

Those are separate saved objects in your Kibana. They aren't in this repo and I have no access to your cluster, so I can't study their structure, panel types, or layout to match the pattern. **Export one of them** (Stack Management → Saved Objects → export the Windows dashboard as NDJSON) and I'll mirror it exactly.

## Blocker 2: the database telemetry basically doesn't exist

This is the bigger problem. From `esql_result.csv` — your own dataset inventory, 578 datasets, 830M documents:

| Target | Datasets | **Hosts** | Docs / 24 h |
|---|---|---|---|
| **Oracle** | `oracle.memory`, `.tablespace`, `.performance`, `.sysmetric`, `.system_statistics` | **2** | ~2,850 each (14 k total) |
| **MSSQL** | `sql` | **2** | **568** |
| **MySQL** | — none — | **0** | **0** |
| **Postgres** (self-managed) | — none — | **0** | **0** |
| Postgres (GCP CloudSQL) | `gcp.cloudsql_postgresql` | 1 *(the collector)* | 138 k |

For comparison, the Server dashboards stand on `system.cpu` / `system.memory` / `system.network` at **2,893 hosts each**, plus `windows.service` at 1,602 hosts and 43.5M documents.

I checked exhaustively — no `mysql.*`, no `postgresql.*`, no `mssql.*` under any naming. Only 8 of 578 datasets are database-related at all, and one of those (`apm.app.sold_program_database`) is an application that merely has "database" in its name.

**Taking each in turn:**

- **MySQL / Postgres — cannot be built.** There is no self-managed MySQL or Postgres telemetry. The only Postgres is GCP CloudSQL, collected remotely, where `host.name` is the collector rather than the database — the same trap we hit with vSphere. A per-instance view needs the GCP resource identifier, not `host.name`.

- **MSSQL — 568 documents from two hosts** is roughly one document every 2.5 minutes. That's the generic `sql` module running a custom query, and I don't know what it collects. It won't support a dashboard.

- **Oracle — the only real candidate.** Those five datasets are the standard Metricbeat Oracle module (tablespace usage, SGA/PGA, performance, sysmetrics), which genuinely is enough for a proper Oracle dashboard. But it covers **two instances**. That's not an estate view, it's two databases — and I don't know the field names inside those datasets.

## What I'd need

I'm not going to guess field names and ship panels — that's precisely what broke this dashboard before. Four queries and I can build whatever the data supports:

```esql
FROM metrics-* | WHERE STARTS_WITH(data_stream.dataset, "oracle.") | LIMIT 3
```
```esql
FROM metrics-* | WHERE data_stream.dataset == "sql" | LIMIT 3
```
```esql
FROM metrics-* | WHERE data_stream.dataset == "gcp.cloudsql_postgresql" | LIMIT 3
```

And this one matters most — how big the gap actually is:

```esql
FROM metrics-*
| WHERE ci.class_name LIKE "*SQL*" OR ci.class_name LIKE "*Oracle*"
     OR ci.class_name LIKE "*Database*" OR ci.class_name LIKE "*MySQL*"
     OR ci.class_name LIKE "*Postgre*"
| STATS cis = COUNT_DISTINCT(ci.name), docs = COUNT(*) BY ci.class_name
| SORT cis DESC
```

## What I'd suggest telling the team

The honest finding is worth more than a thin dashboard: **the database tier is effectively unmonitored.** The CMDB carries database CIs — `MSFT SQL Instance` is already in the Impacted Domain class mapping — but only 2 Oracle and 2 SQL hosts emit any telemetry at all.

That last query gives you the number for that conversation: *N database CIs in the CMDB, 4 reporting.* That's a monitoring-coverage gap to fix with the DBA team, and it fits the Monitoring Maturity section rather than a Database detail dashboard.

If you want, I can build a **Database Coverage Gap** panel from data that exists today — CMDB database CIs vs. what's reporting — while the instrumentation question gets worked. Say the word and I'll add it.
