# MIM V3 — finding demo values for the CI, Incident and Service controls

Sections 2 and 3 only fill when the controls point at something Elastic has data for. Most P1 / P2 CIs are servers
without APM, network devices or application services, so a CI picked at random often leaves panels empty. These
three queries find the combinations that fill the most panels **in your data, right now**.

**How to run:** Kibana **Discover**, switch to **ES|QL**, paste the query, set the time picker as shown, run. Then
pick the values from the first rows in MIM V3's controls. Re-run them just before a demo: the queries look at the
last 15 minutes to 1 hour, so the best picks change.

---

## Query 1 — CIs that fill section 2 (time picker: *Last 1 year*)

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
     OR (src == "Logs" AND TO_INTEGER(syslog_severity_code) <= 4 AND @timestamp >= NOW() - 1 hour)
     OR (src == "Middleware" AND paladin.enrichment.computed.proc_type IS NOT NULL AND @timestamp >= NOW() - 15 minutes)
     OR (src NOT IN ("incident", "Changes", "Logs", "Middleware") AND @timestamp >= NOW() - 15 minutes)
| EVAL key = TO_LOWER(CASE(src == "APM", TO_STRING(host.name), TO_STRING(ci.name)))
| EVAL active = src == "incident" AND TO_STRING(state_name) NOT IN ("Resolved", "Closed", "Canceled", "Cancelled")
| STATS sources = VALUES(CASE(src != "incident", src)), names = VALUES(CASE(src == "incident", TO_STRING(ci.name))),
        active_incidents = VALUES(CASE(active, TO_STRING(number))),
        services = VALUES(CASE(src == "APM" AND TO_LOWER(TO_STRING(service.environment)) IN ("prd1", "prd2", "prd", "prod", "production"), TO_STRING(service.name)))
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
| `incident` | An active P1 / P2 on the CI, or *(all incidents)* if none is open | **Incident** control (fills *Escalate* and *P1 Duration*) |
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

```
FROM traces-apm*, metrics-apm.service_destination.1m-* METADATA _index
| WHERE TO_LOWER(TO_STRING(service.environment)) IN ("prd1", "prd2", "prd", "prod", "production") AND @timestamp >= NOW() - 15 minutes
| EVAL src = CASE(_index LIKE "*service_destination*", "dst", "trc")
| WHERE src == "dst" OR (processor.event == "transaction" AND url.domain IS NOT NULL)
| EVAL key = CASE(src == "trc", TO_LOWER(TO_STRING(url.domain)),
                  TO_LOWER(MV_FIRST(SPLIT(TO_STRING(span.destination.service.resource), ":"))))
| STATS targets = VALUES(CASE(src == "trc", service.name)), callers = VALUES(CASE(src == "dst", service.name)),
        apps = VALUES(CASE(src == "dst", TO_STRING(ci.name)))
  BY key
| WHERE targets IS NOT NULL AND callers IS NOT NULL
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
3. Pick its `incident` in the **Incident** control: *Escalate* narrows to it and *P1 Duration* shows its age.
4. If Query 1 listed a `service` for that CI, leave the **Service** control on *(services on this CI)*: section 3
   fills from the CI. If not, pick a service that is near the top of Query 2 and Query 3.
5. Click a service name in section 3 to open its APM Service Map.

**Leads from the earlier data checks** (confirm with Queries 2 and 3 first):
- `CNACentral` — the Service Map screenshot (`service_map.png`) shows it calling `dnb-service-api`,
  `elm-standardize-services`, Oracle and PostgreSQL, and being called by `cnac-service`.
- `papc-papcintcons1` (Enterprise PolicyCenter) — round 4 query M showed it calling Oracle and several HTTP services.
- Services behind `abp-data-api.gcp.cna.com` and `abp-doc-api.gcp.cna.com` — round 4 query O showed `abp-web`,
  `abp-batch`, `juno-doc-api` and `jupiter-orchestration` calling them.

**Before the demo:** after selecting values, don't click *Save*; use **More (⋯) → Reset changes** afterwards to clear them.
