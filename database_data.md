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



---
---
Critical finding in the samples. Let me verify it before I state it.

The samples answer the question definitively — and they turned up something more important than a dashboard.

## The Oracle and MSSQL collection is broken. It has never collected a metric.

Every document in both `oracle.csv` and `sql.csv` carries this:

```
cannot open connection: testing connection: ORA-00000: DPI-1047:
Cannot locate a 64-bit Oracle Client library: "libclntsh.so: cannot open
shared object file: No such file or directory"
```

I checked field by field: **323 `oracle.*` metric fields exist in the mapping, and exactly zero carry a value.** Same for `sql.*`. There is no tablespace data, no SGA/PGA, no sysmetrics — nothing. The ~2,850 documents per day per dataset are two agents logging a connection failure every 60 seconds.

The Metricbeat Oracle module needs the Oracle Instant Client installed on the collector host. It isn't installed on either `lrch1e01` or `vslrau1p298`. That's the whole problem, and it's a host-provisioning fix, not a dashboard one.

**The `sql` dataset is not MSSQL.** Same two hosts, same `event.module: sql`, same error, same target — it's a second Metricbeat SQL input pointed at the *same Oracle database* on a 300-second interval. There is no MSSQL collection anywhere in the cluster.

Also worth noting: only **one** Oracle target is configured at all — `service.address = drtora19c1-scan.cna.com:1522/oem135r.cna.com`, which looks like the OEM repository database. Even once the client library is installed, that's one database, not an estate.

**This means a panel on your current dashboard is lying.** *Monitored Estate by Tier* reports "Database — Oracle · 2 reporting hosts · 🟢 Flowing", because documents are arriving on schedule. They're error documents. I'd like to fix that panel to distinguish "collecting" from "connecting" — say the word.

## So, per target

| | Verdict |
|---|---|
| **Oracle** | Cannot build. Zero metric values. Fix `libclntsh.so` on the two collectors first |
| **MSSQL** | Cannot build. Does not exist — the `sql` dataset is a second failing Oracle input |
| **MySQL** | Cannot build. No telemetry of any kind |
| **Postgres (self-managed)** | Cannot build. None |
| **Postgres (GCP CloudSQL)** | **Buildable** — real metrics, see below |

## CloudSQL Postgres is the one thing that works

Two live instances, and the data is genuine:

- `cna-g-prod-proj-spg:g-prd-spg-main-csql-pg`
- `cna-g-prod-proj-spg:g-prd-spg-control-csql-pg`

Postgres 14, region `us-central`, state `RUNNABLE`, with `num_backends.count` (connections) and `transaction.count` populated.

Critically, it must be keyed on **`gcp.labels.resource.database_id`**, not `host.name` — `host.name` here is the GKE collector pod `elastic-agent-gcp-integration-agent-…`, exactly the collector-vs-device trap we hit with vSphere.

Of 46 `gcp.cloudsql_postgresql.*` fields in the mapping, 3 were populated in your 3-document sample. GCP emits one metric per document, so the other 43 almost certainly appear in other documents — I just can't see which from 3 rows. Two queries and I can build it:

```
GET metrics-*/_field_caps?fields=gcp.cloudsql_postgresql.*
```
```esql
FROM metrics-*
| WHERE data_stream.dataset == "gcp.cloudsql_postgresql"
| STATS docs = COUNT(*) BY gcp.labels.resource.database_id, gcp.labels.metrics.database
| SORT docs DESC
```

## Why your fourth query returned nothing

**There is no CMDB enrichment on any of these datasets.** No `ci.*` field carries a value in any of the three samples — no `ci.name`, no `ci.class_name`, nothing. So database CIs cannot be cross-referenced from `metrics-*` at all. The `MSFT SQL Instance` class vocabulary we used in Impacted Domain lives on the **incidents** index, not here.

That's a second gap: even if the collection is fixed, database metrics won't join to the CMDB until the enrichment pipeline covers these data streams.

## What I'd do next

I'm not going to build three empty dashboards. Two things I can do now — tell me which:

1. **Fix the Monitored Estate panel** so a tier emitting only errors shows as 🔴 rather than 🟢 Flowing, and add a small *Database Collection Health* panel surfacing the `error.message` per dataset and host. Built entirely on fields I've verified. This keeps the Oracle failure visible until it's fixed instead of buried in a chat thread.
2. **Build the CloudSQL Postgres panels** once you run the two queries above.

And the real headline for the team: **the database tier is unmonitored.** Two collectors have been failing to connect since they were configured, and nobody noticed because documents kept arriving. That's worth more to them than a dashboard would have been.
