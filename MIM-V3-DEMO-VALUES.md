# MIM V3 — finding demo values for the CI, Incident and Service controls

Sections 2 and 3 only fill when the controls point at something Elastic has data for. Most P1 / P2 CIs are servers
without APM, network devices or application services, so a CI picked at random often leaves panels empty. These
three queries find the combinations that fill the most panels **in your data, right now**.

**How to run:** Kibana **Discover**, switch to **ES|QL**, paste the query, set the time picker as shown, run. Then
pick the values from the first rows in MIM V3's controls. Re-run them just before a demo: the queries look at the
last 15 minutes to 1 hour, so the best picks change.

---

## Query 1 — CIs that fill section 2 (time picker: *Last 1 year*)

*Run it in Discover, not Dev Tools Console: Console gives up after about 30 seconds (the "502 Bad Gateway" you saw).
The first version used `IN` inside STATS, which Kibana 9.5 rejects ("Function IN not allowed in STATS"); this version
is fixed.*

Ranks the CIs in the **CI control** (P1 / P2 opened in the last 31 days) by how many section-2 data sources have data
for them now. It also gives an active incident on the CI (for the **Incident** control) and a production APM service
running on it (section 3).

```
FROM servicenow-incidents-*, .ds-metrics-system.cpu-default*, metrics-windows.service-*, metrics-system.process-*, metricbeat-*, logs-syslog-classic-*, synthetics-*, servicenow-change-requests-*, metrics-apm.internal-* METADATA _index
| EVAL src = CASE(_index LIKE "*servicenow-incidents*", "incident", _index LIKE "*change-request*", "Changes",
      _index LIKE "*system.cpu*", "Infra", _index LIKE "*windows.service*", "Processes", _index LIKE "*system.process*", "Middleware",
      _index LIKE "*metricbeat*", "SQL", _index LIKE "*syslog*", "Logs", _index LIKE "*synthetics*", "Synthetics", "APM")
| WHERE (src == "incident" AND TO_INTEGER(priority) IN (1, 2) AND opened_at >= NOW() - 31 days)
     OR (src == "Changes" AND (end_at >= NOW() - 7 days OR start_date >= NOW() - 7 days))
     OR (src == "Logs" AND @timestamp >= NOW() - 15 minutes AND TO_INTEGER(syslog_severity_code) <= 4)
     OR (src == "Middleware" AND paladin.enrichment.computed.proc_type IS NOT NULL AND @timestamp >= NOW() - 15 minutes)
     OR (src NOT IN ("incident", "Changes", "Logs", "Middleware") AND @timestamp >= NOW() - 15 minutes)
| EVAL key = TO_LOWER(CASE(src == "APM", TO_STRING(host.name), TO_STRING(ci.name)))
| EVAL active = src == "incident" AND TO_STRING(state_name) NOT IN ("Resolved", "Closed", "Canceled", "Cancelled"),
       prod_apm = src == "APM" AND TO_LOWER(TO_STRING(service.environment)) IN ("prd1", "prd2", "prd", "prod", "production")
| EVAL source = CASE(src != "incident", src), inc_ci = CASE(src == "incident", TO_STRING(ci.name)),
       inc_open = CASE(active, TO_STRING(number)), svc = CASE(prod_apm, TO_STRING(service.name))
| STATS sources = VALUES(source), names = VALUES(inc_ci), active_incidents = VALUES(inc_open), services = VALUES(svc)
  BY key
| WHERE names IS NOT NULL AND key IS NOT NULL
| EVAL panels_with_data = COALESCE(MV_COUNT(sources), 0), has_active = CASE(active_incidents IS NOT NULL, 1, 0)
| SORT panels_with_data DESC, has_active DESC
| LIMIT 25
| EVAL ci = MV_FIRST(names), incident = COALESCE(MV_FIRST(active_incidents), "(all incidents)"),
       service = COALESCE(MV_FIRST(services), "(services on this CI)"), data_for = MV_CONCAT(sources, ", ")
| KEEP ci, panels_with_data, data_for, incident, service
```

| Column | Meaning | Use it for |
|---|---|---|
| `ci` | The CI, exactly as the CI control lists it | **CI** control |
| `panels_with_data` | How many of the sources below have data for it (max 8) | Pick the highest |
| `data_for` | Which panels will show data: Infra → *Infra Health*; Processes, Middleware, SQL → *Middleware / DB Health* and *Process Health*; Logs → *Errors from the Logs*; Synthetics → *Synthetics Health*; Changes → *Changes on this CI*; APM → *Applications on this CI* and section 3 | — |
| `incident` | An active P1 / P2 on the CI, or *(all incidents)* if none is open | **Incident** control (fills *Escalate* and the *Longest P1* tile) |
| `service` | A production APM service running on the CI, or *(services on this CI)* if none | **Service** control; leave it on *(services on this CI)* when a service is listed |

*Escalate* always fills once a CI is picked. *SLO Error Burn Rate* does not depend on the CI.

## Query 2 — services that fill section 3, upstream side (time picker: *Last 1 hour*)

Production services with the most dependencies. Picking one in the **Service** control fills *Services in scope* and
*Upstream — what they call*; a non-zero `error_pct` gives a *Failing* or *Degraded* row to talk about.

```
FROM metrics-apm.service_destination.1m-*
| WHERE TO_LOWER(TO_STRING(service.environment)) IN ("prd1", "prd2", "prd", "prod", "production") AND @timestamp >= NOW() - 1 hour
| EVAL n = span.destination.service.response_time.count
| STATS dependencies = COUNT_DISTINCT(TO_STRING(span.destination.service.resource)), calls = SUM(n),
        failed = SUM(CASE(TO_STRING(event.outcome) == "failure", n, 0)), app = VALUES(TO_STRING(ci.name))
  BY service.name
| EVAL error_pct = ROUND(failed * 100.0 / calls, 1), business_app = MV_FIRST(app)
| SORT dependencies DESC
| LIMIT 25
| KEEP service.name, business_app, dependencies, calls, error_pct
```

## Query 3 — services that fill section 3, downstream side (time picker: *Last 15 minutes*)

Production services with the most callers. Picking one fills *Downstream — who calls them* and *Business applications
impacted*. (`callers` can include the service itself if it calls its own host; the panel leaves that out.)

*Fixed on 8 Oct: the first version counted batch and listener services (RAPID, cmt-batch, the ivans listeners …) as
having dozens of callers, because their batch transactions record the URL they call (`storage.googleapis.com`,
`metadata.google.internal`, `cna.okta.com`). Only incoming-request transactions on CNA host names count now, and hosts
shared by more than 5 services are skipped. The dashboard's Downstream panel had the same flaw and is fixed too.*

```
FROM traces-apm*, metrics-apm.service_destination.1m-* METADATA _index
| WHERE TO_LOWER(TO_STRING(service.environment)) IN ("prd1", "prd2", "prd", "prod", "production") AND @timestamp >= NOW() - 15 minutes
| EVAL src = CASE(_index LIKE "*service_destination*", "dst", "trc")
| WHERE src == "dst" OR (processor.event == "transaction" AND transaction.type == "request" AND url.domain IS NOT NULL)
| EVAL key = CASE(src == "trc", TO_LOWER(TO_STRING(url.domain)),
                  TO_LOWER(MV_FIRST(SPLIT(TO_STRING(span.destination.service.resource), ":"))))
| WHERE ENDS_WITH(key, "cna.com") OR NOT key LIKE "*.*"
| EVAL target = CASE(src == "trc", service.name), caller = CASE(src == "dst", service.name),
       caller_app = CASE(src == "dst", TO_STRING(ci.name))
| STATS targets = VALUES(target), callers = VALUES(caller), apps = VALUES(caller_app) BY key
| WHERE targets IS NOT NULL AND callers IS NOT NULL AND MV_COUNT(targets) <= 5
| MV_EXPAND targets
| STATS callers = COUNT_DISTINCT(callers), caller_apps = COUNT_DISTINCT(apps), hosts = VALUES(key) BY service = targets
| SORT callers DESC
| LIMIT 25
| EVAL host = MV_CONCAT(hosts, ", ")
| KEEP service, callers, caller_apps, host
```

The best demo service appears near the top of **both** Query 2 and Query 3.

---

## Suggested demo flow

1. **Section 1** needs no selection: it shows all active P1 / P2.
2. Pick the top `ci` from Query 1 in the **CI** control: section 2 fills.
3. Pick its `incident` in the **Incident** control: *Escalate* narrows to it and the *Longest P1* tile shows its age.
4. If Query 1 listed a `service` for that CI, leave the **Service** control on *(services on this CI)*: section 3
   fills from the CI. If not, pick a service that is near the top of Query 2 and Query 3.
5. Click a service name in section 3 to open its APM Service Map.

## Picks for section 3 from your results (8 Oct)

These services came out near the top of both Query 2 (dependencies) and Query 3 (callers on their own CNA host names).
Pick one in the **Service** control; the CI control can stay on anything.

| Service | Business application | What it shows | Why |
|---|---|---|---|
| `document management facility prod` | Document Management Facility | Upstream: 14 dependencies, ~1 % failed calls (a *Degraded* row to talk about). Downstream: 6 calling services from 5 business applications on `dmf.cna.com` | **Best all-round demo** |
| `ecs-retrieve-api` | Enterprise Content Service 2.0 | Upstream: 6 dependencies. Downstream: the most callers of any service (14, from 10 business applications) | Big blast radius. Note: `ecs-data-api.gcp.cna.com` is shared by four ECS services, so *Via host* explains the overlap |
| `ecs-manage-api` | Enterprise Content Service 2.0 | 6 dependencies, 12 callers from 10 applications | Alternative to the above |
| `jupiter-orchestration` | Jupiter | Upstream: 14 dependencies, 1.5 % failed calls | A *Degraded* upstream example |
| `dmf` | Document Management Facility | 7 dependencies, the highest call volume (250k / hour), 6 callers | Busy, healthy service |

Numbers are from the last hour / 15 minutes on 8 Oct, before the Query 3 fix; re-run Queries 2 and 3 on the day of the
demo. The services that topped the old Query 3 (RAPID, rmw-report-runner, cmt-batch, the listeners) were artefacts of
the flaw above, so don't use them.

## Picks for section 2 from your Query 1 results (8 Oct)

| CI | Incident control | Service control | Fills |
|---|---|---|---|
| `vslrau1p228` | *(all incidents)* | *(services on this CI)* (APM service `billigportal` runs on it) | Infra, Middleware, Synthetics, Applications **and section 3 without picking a service**: best all-round |
| `vslrau1p061` | `INC2652251` (active P2) | pick a section-3 service | Infra, Middleware, Synthetics; *Escalate* and the *Longest P1* tile show the incident |
| `vslrau1p058` | `INC2670595` | pick a section-3 service | Infra, Middleware, Synthetics with an active incident |
| `sau1h630` | `INC2669663` | pick a section-3 service | Synthetics, Middleware / DB (SQL Server) with an active incident |
| `vskau1p1025`, `vclau1p0147` or `prau1pdb0003` | *(all incidents)* | pick a section-3 service | Infra, Processes / Middleware, Synthetics **and Changes** |

No CI had warning-or-worse syslog lines in the 15 minutes Query 1 looked at, so *Errors from the Logs* may stay
empty; it reads a wider set of logs over the time picker, so try *Last 24 hours*. Incidents get resolved: if the
Incident control shows a ⚠ next to one, it has closed — re-run Query 1.

*Tip: the CSV download from Discover can come out empty for ES|QL results like these; the table on screen (or
Inspect → Response, as you did) has the rows.*

**Before the demo:** after selecting values, don't click *Save*; use **More (⋯) → Reset changes** afterwards to clear them.
