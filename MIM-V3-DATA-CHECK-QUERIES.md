# MIM V3 — data-check queries (correct versions)

Every query we ran to confirm what data exists before building MIM V3 (and the SLA / change work in MIM V2),
in its **corrected, working form**, with what it answered.

**How to run:** Kibana **Discover**, switched to **ES|QL**, unless marked *Dev Tools*. Set the time picker as shown —
the log and metric indices are very large, so keep those to **Last 15 minutes**.

**Two ES|QL rules these queries rely on** (both caused errors along the way):

- A field whose type differs between indices (e.g. `ci.name` is keyword in most log indices but text in some)
  must be wrapped in a conversion function: `TO_STRING(ci.name)`.
- A field name with a numeric part must be in backticks: `` `category.1` ``.

---

## Queries A – L (MIM V3)

### A. Which logs can be filtered by CI — *Last 15 minutes*
```
FROM logs-* | STATS docs = COUNT(*), with_host = COUNT(TO_STRING(host.name)), with_ci = COUNT(TO_STRING(ci.name)), with_level = COUNT(TO_STRING(log.level)) BY dataset = TO_STRING(data_stream.dataset) | SORT docs DESC | LIMIT 60
```
**Answered:** syslog, WebSphere, JBoss, Red Hat, AIX, BIG-IP and Tableau logs carry `ci.name` but no `log.level`;
application logs (`apm.app.*`, `apm.error`) carry both. *(The first version, without `TO_STRING`, failed on mixed
field types.)*

### B. Middleware / DB metrics that carry a CI — *Last 15 minutes*
```
FROM metrics-*, metricbeat-* | WHERE TO_STRING(ci.name) IS NOT NULL | STATS docs = COUNT(*), cis = COUNT_DISTINCT(TO_STRING(ci.name)) BY dataset = TO_STRING(data_stream.dataset), module = TO_STRING(event.module) | WHERE dataset IS NULL OR NOT (STARTS_WITH(dataset, "apm") OR STARTS_WITH(dataset, "system.") OR STARTS_WITH(dataset, "windows.")) | SORT docs DESC | LIMIT 50
```
**Answered:** only SQL Server metrics carry the CI (`sql` module 386 CIs, `mssql` 135). IBM MQ, Oracle and
WebSphere metrics do not.

### C. Linux expected-process check — *Last 15 minutes*
```
FROM metrics-system.process-* | STATS docs = COUNT(*), hosts = COUNT_DISTINCT(host.name) BY paladin.enrichment.computed.proc_diff | SORT docs DESC
```
**Answered:** `equal` on 1,534 hosts, `not_equal` on 742 (see J for what that means).

### D. Application dependency coverage — *no time filter*
```
FROM cmdb_app_dependencies_v2 | STATS links = COUNT(*), with_child_name = COUNT(child_ci.name.keyword), with_apm_service = COUNT(service.name.keyword) BY parent_class = parent_ci.class.keyword, child_class = child_ci.class.keyword | SORT links DESC | LIMIT 30
```
**Answered:** not usable for applications — the 2.1M server rows have no child names; the rest is
infrastructure (disks, zones, Kubernetes). `cmdb-ci-relations` is used instead.

### E. CMDB relationships sample — *no time filter*
```
FROM cmdb-ci-relations* | LIMIT 5
```
**Answered:** `parent.name`, `child.name`, `parent.class`, `child.class` and `type.name` (e.g. "Owns::Owned by"),
all keyword — so one CI's neighbours are a fast lookup.

### F. Releases and outage windows on changes — *Last 1 year*
```
FROM servicenow-change-requests-* | STATS changes = COUNT(*), with_outage_window = COUNT(planned_outage_start_at), with_actual_start = COUNT(start_at), with_end = COUNT(end_at) BY type, category = `category.1` | SORT changes DESC | LIMIT 30
```
**Answered:** none of 148k changes has an outage window or an actual start; ~17k are categorised "application" /
"Applications Software" (the nearest thing to releases). *(The first version used `category.1` without backticks
and failed.)*

### G. SLO, release, maintenance or deployment indices — *Dev Tools*
```
GET _cat/indices/.slo-observability*,*release*,*maint*,*blackout*,*schedule*,*deploy*?v&expand_wildcards=all&s=index
```
**Answered:** SLO indices exist and are active (`.slo-observability.sli-*` > 1M records a month,
`.slo-observability.summary-*`); no release, maintenance or blackout index; `bridge-deployments` has only 18
records.

### H. SLO summary sample — *Last 1 year*
```
FROM .slo-observability.summary-v3* | LIMIT 5
```
*Dev Tools alternative:* `GET .slo-observability.summary-v3.5/_search?size=3`

**Answered:** each SLO summary has `service.name`, `status`, `oneHourBurnRate.value`, `oneDayBurnRate.value`,
`errorBudgetConsumed`, `summaryUpdatedAt`, `slo.groupBy` / `slo.instanceId` (some SLOs are grouped per CI) — and
no `@timestamp`. The account can read the hidden index through ES|QL.

### I. Relationships that connect servers to other CIs — *no time filter*
```
FROM cmdb-ci-relations* | WHERE parent.class IN ("cmdb_ci_win_server", "cmdb_ci_linux_server", "cmdb_ci_aix_server") OR child.class IN ("cmdb_ci_win_server", "cmdb_ci_linux_server", "cmdb_ci_aix_server") | STATS links = COUNT(*) BY type.name, parent.class, child.class | SORT links DESC | LIMIT 40
```
**Answered:** "Runs on" links software to servers (Tomcat, SQL Server, SharePoint, batch jobs), "Virtualized by"
gives the ESX host, "IP Connection" / "Connects to" the switches.

### J. What "not_equal" means on Linux processes — *Last 15 minutes*
```
FROM metrics-system.process-* | WHERE paladin.enrichment.computed.proc_diff == "not_equal" | LIMIT 5
```
**Answered:** a changed process fingerprint, not a process down. The same records label middleware processes by
type and instance (`paladin.enrichment.computed.proc_type` / `proc_instance`, e.g. IBM MQ queue manager DRT2Q7,
IBM HTTP Server HTTPServer01) with the owning group (`enrich_policy.cmdb-cis.proc_assignment`).

### K. APM services per server — *Last 15 minutes*
```
FROM metrics-apm* | WHERE host.name IS NOT NULL | STATS services = VALUES(service.name) BY host.name | LIMIT 10
```
**Answered:** APM records the server in upper case for VMs (`VKBLYDAP4015`) and the pod name for Kubernetes
services — so services can be matched to a server CI, but not containerised ones.

### L. Syslog sample, for the severity field — *Last 15 minutes*
```
FROM logs-syslog-classic-default | LIMIT 3
```
**Answered:** `syslog_severity` / `syslog_severity_code` (0–7); "error or worse" = code ≤ 3.

---

## Round 4 — Service Dependency & Blast Radius (results in `round4.txt`, `p.csv`, `t.txt`)

| # | Query | Time | Answered |
|---|---|---|---|
| M | `FROM metrics-apm.service_destination.1m-* \| LIMIT 5` | 15 min | Each record is one service calling one dependency per minute: `service.name`, `span.destination.service.resource` (e.g. `oracle`, `esbwsrrutil.cna.com:443`), `service.target.type` / `name`, call count and total time (`span.destination.service.response_time.count` / `sum.us`), `event.outcome`. Records also carry the calling service's CMDB **business application** in `ci.*` (`ci.name` "Enterprise PolicyCenter", `ci.number` APM0003360, `ci.support_group.l2.name`, `ci.customer_specific.pm_portfolio`) and `service.environment` (`prd1`) |
| N | `… \| STATS callers = COUNT_DISTINCT(service.name), resources = … BY target_type = TO_STRING(service.target.type)` | 1 h | 493 services make HTTP calls (1,691 addresses); 253 call PostgreSQL, 71 gRPC, 35 Oracle, 28 SQL Server, 17 DB2, 8 JMS |
| O | `… \| STATS callers = VALUES(service.name) BY resource = TO_STRING(span.destination.service.resource)` | 1 h | Calls to other services are recorded by **host:port** (`abp-data-api.gcp.cna.com:443`), not by service name |
| P | `FROM traces-apm* \| WHERE processor.event == "transaction" AND url.domain IS NOT NULL \| STATS transactions = COUNT(*) BY service.name, url.domain` | 15 min | (502 in Console; result in `p.csv`.) The host names each service answers on, e.g. `dmf` → `dmf.cna.com`. Matching these to O gives a service's callers. Non-production hosts (`-stg`, `-ete1`, `-cut1`) are mixed in |
| Q | `FROM metrics-apm.service_transaction.1m-* \| LIMIT 3` | 15 min | Service metrics carry the same business-application fields as M; `labels.service_group` = the APM number; no criticality or user-count field |
| R | `FROM cmdb-ci-relations* \| WHERE parent.class LIKE "*service*" … \| STATS links = COUNT(*) BY type.name, parent.class, child.class` | 1 year | (40 rows in the Console output.) `cmdb_ci_business_app` *Consumes* `cmdb_ci_service_calculated` (application services, 4,581), which *Runs on* Windows / Linux servers (4,379 / 3,903) — a server → application service → business application chain exists |
| S | `FROM cmdb-cis* \| LIMIT 3` | 1 year | CI records: name, class, install / operational status, location; no criticality or user-count field in the sample |
| T | `FROM traces-apm* \| … with_user = COUNT(TO_STRING(user.id)) …` | 15 min | Error *Unknown column [user.id]*: APM records no user IDs, so "users impacted" cannot be shown |

## Round 5 — Blast Radius design (results in `round5.txt`, `service_map.png`)

Run in Dev Tools Console, which applies **no time filter**, so V, W and Z cover the whole retention.

| # | Query | Answered |
|---|---|---|
| V | `FROM metrics-apm.service_transaction.1m-* \| STATS services = COUNT_DISTINCT(service.name) BY env = TO_STRING(service.environment)` | 426 services in `prd1`; production is also spelled `prd2`, `prd`, `Prod`, `PRD`. Non-production: `cut*`, `ete*`, `stg*`, `drt*`, `UAT`, `QA`, `DEV`; 42 services have no environment |
| W | `FROM metrics-apm.service_destination.1m-* \| STATS docs = COUNT(*), calls = SUM(span.destination.service.response_time.count) BY outcome = TO_STRING(event.outcome)` | Failed calls are recorded: 140M failed vs 17.3B successful (0.8 %), so a per-dependency error % works |
| X | incidents ∪ `metrics-apm.service_transaction.1m-*`, CIs present in both | 562 P1 / P2 CIs (7,234 incidents) in 6 months; **none** is an APM business application name (the single match is the blank CI). Deriving the service from the incident CI's name does not work |
| Y | `FROM servicenow-incidents-* \| … STATS incidents, cis BY ci_class` (6 months) | P1 / P2 are raised mostly against servers: Linux 2,800, AIX 2,719, Windows 766; network 423; application services ~200 (Mapped, Application, Tag-Based, Calculated); 415 without a CI |
| Z | `FROM metrics-apm.service_destination.1m-* \| STATS docs, services, resources` | 350M records, 515 calling services, 1,766 dependencies over the whole retention; a 15-minute window is a small fraction |
| U | Manual: APM → Service Map | The map draws (licence includes it) and resolves service-to-service calls, e.g. cnac-service → CNACentral → elm-standardize-services → elm-hazard-services |

---

## Earlier checks

### Round 1 for MIM V3 (before A – L)

| # | Query | Time | Answered |
|---|---|---|---|
| 1 | `FROM metrics-* \| WHERE ci.name IS NOT NULL \| STATS docs = COUNT(*), hosts = COUNT_DISTINCT(host.name) BY data_stream.dataset \| SORT docs DESC \| LIMIT 50` | 15 min | Server CPU / memory / disk / network (2,881 hosts), `system.process` (1,729) and `windows.service` (1,589) carry the CI |
| 2 | `FROM metrics-system.cpu-* \| KEEP host.name, ci.name, ci.class_name, ci.support_group.l2.name \| LIMIT 10` | 15 min | Host name equals CI name; class and support group are on the metrics |
| 3 | `FROM cmdb_app_dependencies_v2 \| LIMIT 5` | — | Columns of the dependency table (see D) |
| 4 | `FROM synthetics-* \| LIMIT 5` | 1 year | Ping monitors carry `ci.name`; browser journeys carry `labels.service.name` (the application) |
| 5 | `FROM metrics-windows.service-* \| LIMIT 5` | 15 min | `windows.service.state`, `start_type`, `display_name`, with the CI |
| 6 | `FROM metrics-system.process-* \| LIMIT 5` | 15 min | Running processes with the CI and the Paladin enrichment |

### SLA, change and acknowledgement checks (MIM V2 section 2)

| # | Query | Time | Answered |
|---|---|---|---|
| S1 | `FROM servicenow-incidents-* \| WHERE priority IN (1, 2) \| EVAL status = CASE(state_name IN ("Resolved", "Closed", "Canceled", "Cancelled"), "closed", "active") \| STATS incidents = COUNT(*), has_breached_sla = COUNT(has_breached_sla), sla_primary = COUNT(sla.primary.task_has_breached), sla_response = COUNT(sla.response.task_has_breached), major_flag = COUNT(is_major_incident), bridge_flag = COUNT(has_been_handled_by_bridge), assignee = COUNT(assigned_to.name) BY status` | 1 year | The SLA, major-incident and bridge fields on incidents are empty (0 of 1,582 P1 / P2); assignee is filled |
| S2 | `FROM servicenow-task-sla* \| LIMIT 5` | 1 year | Real SLA records: `task_number`, `stage`, `task_has_breached`, `percentage`, `planned_end_time`, `contract_name` |
| S3 | `FROM servicenow-change-requests* \| LIMIT 5` | 1 year | Change number, CI, type, state, close code, risk, planned start, end |
| S4 | `FROM servicenow-incident-timelines* \| LIMIT 5` | 1 year | One record per update with the state at that moment; other fields show current values, so no assignment timestamps |
