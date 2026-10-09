Pulling your answers and query results.

Good news: process data and Windows services both carry the CI across 1,729 and 1,589 hosts respectively, confirming Process Health is buildable, and server CPU, memory, disk, and network carry it for 2,881 hosts. Now I'll check `queries.txt` next.

Host and CI names match directly for Infrastructure Health, but the logs query errored due to a field type mismatch between `ci.name` and `data_stream.dataset`—I'll fix that query. Next I'll check the four remaining samples: app dependencies, synthetics, Windows services, and processes.

The Windows services block uses Kibana Console's `"""` multi-line strings, which aren't valid JSON. Converting those and printing the populated fields of each sample:

Windows services give a reliable down signal via CI, state, and start type, but the app-dependency sample only shows the parent CI's name while the child appears as an ID. I'll check if that table has child-name columns that were just empty in these 5 rows.

The samples show synthetics tied to CIs or business apps, Linux processes enriched with an expected-process list and proc_diff field, and application dependency rows with empty child-name/APM-service columns. Before sending the follow-up queries, I'm testing the trickiest fix (logs) against my local Elasticsearch with mismatched types to make sure it won't fail again on your side.

The local Elasticsearch stopped since last session. Restarting it:

Your results moved most of the dashboard to "ready". I reproduced the logs-query error locally and confirmed a fix for it.

## What your results show

| Panel | Status now | Why |
|---|---|---|
| Infrastructure Health | **Ready** | Server metrics carry the CI, and the host name equals the CI name (e.g. `gprdwce1a-pwn25` on both). 2,881 hosts have CPU, memory, disk and network data. |
| Process Health, Windows | **Ready** | `windows.service` (1,589 hosts) has each service's state and start type. An Automatic service that isn't Running is a clear "down" signal. |
| Process Health, Linux | **Ready, one check** | `system.process` (1,729 hosts) lists running processes, and the monitoring enrichment adds an expected-process list plus a `proc_diff` field. If `proc_diff` flags missing processes, we get "expected but not running" for free (query C). |
| Synthetics Health | **Ready for ping checks** | Ping monitors carry the CI (`vslrau1p300`). Browser journeys are tagged with the application (e.g. "Document Management Facility"), so they'll appear under the CI's applications instead. |
| Applications on this CI | **One check** | The dependency table has the right columns (server → application, plus an APM service), but they were empty in your 5 rows (query D). Fallback if it's sparse: APM data records the server each service runs on, so "services running on this server" works regardless. |
| Logs, Middleware / DB | **Re-run needed** | The logs query failed because some log indices store `ci.name` and the dataset name as text instead of keyword. The fixed version converts them; I reproduced your error locally and confirmed the fix (query A). |

## One design point I need to reopen: the CI filter

You agreed to a normal, clearable control. Your results show that isn't enough for the dependency panels:
- A normal control works by adding a filter, which only applies to records that carry a CI field.
- The dependency and relationship tables don't carry the selected CI as a field. They identify CIs by internal ID and their own parent/child name columns.
- So with a normal control, **"Applications on this CI" and "Changes on CIs linked to it" can't follow the selection.**

Those two panels need the CI value placed directly in their query, which only a query-variable control can do. That's the kind of control you had problems with in MIM V2: it has no Clear button and can't be emptied.

**My recommendation:** use the query-variable control for MIM V3, with a "— no CI selected —" option as the way to "clear" it. The dropdown would list the CIs with P1/P2 incidents in the last month and be searchable. Every panel, including the dependency ones, would then follow it. One thing you'd lose: clicking a CI in the incident table won't set the control, so you'd pick it from the dropdown.

Is that OK, or would you rather keep the clearable control and accept that those two panels show every CI?

## How to check SLOs

1. In Kibana, open the main menu → **Observability → SLOs**. A "Create your first SLO" page means none are set up.
2. Or in **Dev Tools**, run `GET kbn:/api/observability/slos`. An empty `results` list means none.

If there are none, I'll calculate burn rate from APM against a target (99.5 % unless you name another).

## How to check releases and maintenance windows

- **In Elastic:** queries F and G below. They show whether changes carry release categories or outage windows, and whether any release, maintenance, blackout or deployment index exists.
- **In ServiceNow:** ask your ServiceNow admin three things:
  - Do CIs have a *Maintenance schedule* set?
  - Are releases raised as a change type or category, or in Release Management?
  - Is either exported to Elastic?
- **Not the same thing:** Kibana's own *Stack Management → Maintenance Windows* only mutes Kibana alerts. It isn't ServiceNow's maintenance windows.

## Queries to run

The same way as before. Use the time picker shown for each; the log and metric indices are huge, so keep those to 15 minutes.

**A. Logs that can be filtered by CI** (Last 15 minutes)
```
FROM logs-* | STATS docs = COUNT(*), with_host = COUNT(TO_STRING(host.name)), with_ci = COUNT(TO_STRING(ci.name)), with_level = COUNT(TO_STRING(log.level)) BY dataset = TO_STRING(data_stream.dataset) | SORT docs DESC | LIMIT 60
```
**B. Middleware / DB metrics that carry a CI** (Last 15 minutes)
```
FROM metrics-*, metricbeat-* | WHERE TO_STRING(ci.name) IS NOT NULL | STATS docs = COUNT(*), cis = COUNT_DISTINCT(TO_STRING(ci.name)) BY dataset = TO_STRING(data_stream.dataset), module = TO_STRING(event.module) | WHERE dataset IS NULL OR NOT (STARTS_WITH(dataset, "apm") OR STARTS_WITH(dataset, "system.") OR STARTS_WITH(dataset, "windows.")) | SORT docs DESC | LIMIT 50
```
**C. Linux expected-process check** (Last 15 minutes)
```
FROM metrics-system.process-* | STATS docs = COUNT(*), hosts = COUNT_DISTINCT(host.name) BY paladin.enrichment.computed.proc_diff | SORT docs DESC
```
**D. Application dependency coverage** (no time filter needed)
```
FROM cmdb_app_dependencies_v2 | STATS links = COUNT(*), with_child_name = COUNT(child_ci.name.keyword), with_apm_service = COUNT(service.name.keyword) BY parent_class = parent_ci.class.keyword, child_class = child_ci.class.keyword | SORT links DESC | LIMIT 30
```
**E. CMDB relationships sample**, for "CIs linked to the affected CI"
```
FROM cmdb-ci-relations* | LIMIT 5
```
**F. Releases and outage windows on changes** (Last 1 year)
```
FROM servicenow-change-requests-* | STATS changes = COUNT(*), with_outage_window = COUNT(planned_outage_start_at), with_actual_start = COUNT(start_at), with_end = COUNT(end_at) BY type, category.1 | SORT changes DESC | LIMIT 30
```
**G. Dev Tools**, any SLO, release, maintenance or deployment indices
```
GET _cat/indices/.slo-observability*,*release*,*maint*,*blackout*,*schedule*,*deploy*?v&expand_wildcards=all&s=index
```

Once I have these and your answer on the CI control, I'll update the mock-up to the final data picture and then build MIM V3.

---

## Round 3 — remaining checks for MIM V3 (3 Oct 2026)

Run these in **Discover (ES|QL mode)** unless marked *Dev Tools*, with the time picker shown for each, and upload the results as before (CSV, or the Console output). The log and metric indices are very large, so keep those to **Last 15 minutes**.

What we already know from rounds 1–2: Infrastructure Health, Windows services, synthetics ping monitors, CMDB relationships and change requests are ready; 173 SLOs exist. These queries close the last gaps.

**F (corrected). Releases and outage windows on changes** — *Last 1 year*
The earlier version failed because a field name with a numeric part (`category.1`) needs backticks in ES|QL.
```
FROM servicenow-change-requests-* | STATS changes = COUNT(*), with_outage_window = COUNT(planned_outage_start_at), with_actual_start = COUNT(start_at), with_end = COUNT(end_at) BY type, category = `category.1` | SORT changes DESC | LIMIT 30
```

**H. SLO summary sample** — *Last 1 year*
Shows the field names that link each SLO to its service, and whether your account can read the hidden SLO indices.
```
FROM .slo-observability.summary-v3* | LIMIT 5
```
If ES|QL refuses the hidden index, run this in *Dev Tools* instead:
```
GET .slo-observability.summary-v3.5/_search?size=3
```

**I. Which relationships connect servers to other CIs** — *no time filter needed*
Tells us whether server → application links exist in the CMDB relationships (for "Applications on this CI").
```
FROM cmdb-ci-relations* | WHERE parent.class IN ("cmdb_ci_win_server", "cmdb_ci_linux_server", "cmdb_ci_aix_server") OR child.class IN ("cmdb_ci_win_server", "cmdb_ci_linux_server", "cmdb_ci_aix_server") | STATS links = COUNT(*) BY type.name, parent.class, child.class | SORT links DESC | LIMIT 40
```

**J. What "not_equal" means on Linux processes** — *Last 15 minutes*
742 hosts are flagged `not_equal`; this shows what the flag is comparing.
```
FROM metrics-system.process-* | WHERE paladin.enrichment.computed.proc_diff == "not_equal" | LIMIT 5
```

**K. APM services per server** — *Last 15 minutes*
Fallback for "Applications on this CI": which APM services run on each server.
```
FROM metrics-apm* | WHERE host.name IS NOT NULL | STATS services = VALUES(service.name) BY host.name | LIMIT 10
```

**L. Syslog sample, for the severity field** — *Last 15 minutes*
Infrastructure logs carry the CI but no log level; this shows which field holds the syslog severity.
```
FROM logs-syslog-classic-default | LIMIT 3
```

**Access check for your Elastic admin:** the SLO summaries live in hidden `.slo-observability.*` indices. Everyone who views MIM V3 needs read access to them for the SLO Error Burn Rate panel to show data. Query H tells us whether your own account has it.

---

## Round 4 — "Service Dependency & Blast Radius" checks (4 Oct 2026)

Run these in **Discover (ES|QL mode)** with the time picker shown, and upload the results as before (CSV, or the
Console output). These answer whether we can build Senthil's *Service Dependency & Blast Radius* panel.

**M. Dependency metrics sample** — *Last 15 minutes*
What APM records about the calls each service makes (field names for downstream dependencies).
```
FROM metrics-apm.service_destination.1m-* | LIMIT 5
```

**N. Kinds of dependencies** — *Last 1 hour*
How many services call databases, queues, HTTP endpoints, etc.
```
FROM metrics-apm.service_destination.1m-* | STATS callers = COUNT_DISTINCT(service.name), resources = COUNT_DISTINCT(TO_STRING(span.destination.service.resource)) BY target_type = TO_STRING(service.target.type) | SORT callers DESC
```

**O. What the dependency addresses look like** — *Last 1 hour*
Shows whether a call to another service is recorded by name or by host:port.
```
FROM metrics-apm.service_destination.1m-* | STATS callers = VALUES(service.name) BY resource = TO_STRING(span.destination.service.resource) | SORT resource ASC | LIMIT 40
```

**P. Which host names each service is reached on** — *Last 15 minutes*
Used to work out a service's callers (match the addresses in O to these host names).
```
FROM traces-apm* | WHERE processor.event == "transaction" AND url.domain IS NOT NULL | STATS transactions = COUNT(*) BY service.name, url.domain | SORT transactions DESC | LIMIT 40
```

**Q. CMDB fields on APM services** — *Last 15 minutes*
Shows the business application, criticality and owner fields carried by APM service metrics.
```
FROM metrics-apm.service_transaction.1m-* | LIMIT 3
```

**R. Do CMDB relationships link applications to business services?** — *Last 1 year*
```
FROM cmdb-ci-relations* | WHERE parent.class LIKE "*service*" OR child.class LIKE "*service*" OR parent.class LIKE "*business*" OR child.class LIKE "*business*" | STATS links = COUNT(*) BY type.name, parent.class, child.class | SORT links DESC | LIMIT 40
```

**S. What a CMDB CI record holds** — *Last 1 year*
May include criticality, owner or user-count fields.
```
FROM cmdb-cis* | LIMIT 3
```

**T. Does APM record users or sessions?** — *Last 15 minutes*
For a "users affected" figure. An "Unknown column" error is also an answer (it means none).
```
FROM traces-apm* | WHERE processor.event == "transaction" | STATS docs = COUNT(*), with_user = COUNT(TO_STRING(user.id)), with_session = COUNT(TO_STRING(session.id)) BY agent = TO_STRING(agent.name) | SORT docs DESC | LIMIT 20
```

**U. Manual check — APM Service Map**
In Kibana open **Observability → APM → Service Map** (or open any service and its *Service map* tab). If a map
draws, the licence includes it and the dashboard can link to it. If you see a licence / upgrade message, it does not.

## Round 5 — finishing the Blast Radius design (7 Oct 2026)

Same as before: **Discover (ES|QL mode)** with the time picker shown, upload the results (CSV or Console output). An
error is also an answer, so upload it too.

**V. Environment names on APM services** — *Last 1 hour*
So the panel can keep to production (round 4 showed `prd1`, `stg1`, `cut3` …).
```
FROM metrics-apm.service_transaction.1m-* | STATS services = COUNT_DISTINCT(service.name) BY env = TO_STRING(service.environment) | SORT services DESC | LIMIT 30
```

**W. Failed calls on dependencies** — *Last 1 hour*
Whether failed calls are recorded, for the dependency health colour.
```
FROM metrics-apm.service_destination.1m-* | STATS docs = COUNT(*), calls = SUM(span.destination.service.response_time.count) BY outcome = TO_STRING(event.outcome)
```

**X. Do incident CIs match APM business applications?** — *Last 1 year*
APM services carry their CMDB business application in `ci.name` (round 4, M and Q). This lists the P1 / P2 CIs of the
last 6 months that are also an APM business application, so we know how often "derive the service from the CI"
works.
```
FROM servicenow-incidents-*, metrics-apm.service_transaction.1m-* METADATA _index | WHERE (_index LIKE "*servicenow*" AND priority IN (1, 2) AND opened_at >= NOW() - 180 days) OR (_index LIKE "*apm*" AND @timestamp >= NOW() - 1 hour) | EVAL src = CASE(_index LIKE "*servicenow*", "incident", "apm") | STATS sources = VALUES(src), incidents = COUNT_DISTINCT(CASE(src == "incident", TO_STRING(number))) BY ci = TO_STRING(ci.name) | EVAL in_apm = MV_COUNT(sources) == 2 | STATS cis = COUNT(*), incidents = SUM(incidents) BY in_apm
```

**Y. Which CI classes P1 / P2 incidents are raised against** — *Last 1 year*
```
FROM servicenow-incidents-* | WHERE priority IN (1, 2) AND opened_at >= NOW() - 180 days | STATS incidents = COUNT_DISTINCT(number), cis = COUNT_DISTINCT(ci.name) BY ci_class = TO_STRING(ci.class_name) | SORT incidents DESC | LIMIT 30
```

**Z. Volume of dependency metrics** — *Last 15 minutes*
To size the query that finds a service's callers.
```
FROM metrics-apm.service_destination.1m-* | STATS docs = COUNT(*), services = COUNT_DISTINCT(service.name), resources = COUNT_DISTINCT(TO_STRING(span.destination.service.resource))
```

**P2. Host names per service, with environment** — *Last 15 minutes* (P again, split by environment)
```
FROM traces-apm* | WHERE processor.event == "transaction" AND url.domain IS NOT NULL | STATS transactions = COUNT(*) BY service.name, env = TO_STRING(service.environment), url.domain | SORT transactions DESC | LIMIT 60
```

**U (still open). APM Service Map** — manual: open **Observability → APM → Service Map**. Does a map draw, or a
licence / upgrade message?

## Round 6 — `cmdb_app_dependencies_v2` for app relationships and "applications impacted" (9 Oct 2026)

Run in **Dev Tools Console** (no time filter; the index appears to have no `@timestamp`, so Discover's time picker may
hide its rows). If a query 502s in Console, run it in Discover with *Last 1 year* and note that. Upload the results to
`round6.txt`.

**AA. One full record** — what fields exist (is there an `@timestamp`?)
```
POST /_query?format=json
{ "query": "FROM cmdb_app_dependencies_v2 | LIMIT 2" }
```

**AB. Size and freshness**
```
POST /_query?format=json
{ "query": "FROM cmdb_app_dependencies_v2 | STATS docs = COUNT(*), with_child_name = COUNT(child_ci.name.keyword), parents = COUNT_DISTINCT(parent_ci.name.keyword), children = COUNT_DISTINCT(child_ci.name.keyword)" }
```

**AC. Which kinds of CI point at which** (whole index, not the 10k sample)
```
POST /_query?format=json
{ "query": "FROM cmdb_app_dependencies_v2 | WHERE child_ci.name.keyword IS NOT NULL | STATS rows = COUNT(*), parents = COUNT_DISTINCT(parent_ci.name.keyword), children = COUNT_DISTINCT(child_ci.name.keyword) BY parent_ci.class.keyword, child_ci.class.keyword | SORT rows DESC | LIMIT 60" }
```

**AD. Names of the relationship types** (the dependency index only has the ServiceNow ID; the relations index has both)
```
POST /_query?format=json
{ "query": "FROM cmdb-ci-relations* | STATS links = COUNT(*) BY type.sys_id, type.name | SORT links DESC | LIMIT 40" }
```

**AE. The CI from the demo**
```
POST /_query?format=json
{ "query": "FROM cmdb_app_dependencies_v2 | WHERE parent_ci.name.keyword == \"Automated Claim Transaction PROD\" OR child_ci.name.keyword == \"Automated Claim Transaction PROD\" OR parent_ci.name.keyword == \"Automated Claim Transaction\" | STATS rows = COUNT(*) BY parent_ci.name.keyword, parent_ci.class.keyword, child_ci.class.keyword, relationship.latest.servicenow.event.type.value | SORT rows DESC | LIMIT 50" }
```

**AF. Do application services point at business applications (or the other way)?**
```
POST /_query?format=json
{ "query": "FROM cmdb_app_dependencies_v2 | WHERE parent_ci.class.keyword LIKE \"*service*\" OR child_ci.class.keyword LIKE \"*service*\" OR parent_ci.class.keyword == \"cmdb_ci_business_app\" OR child_ci.class.keyword == \"cmdb_ci_business_app\" | STATS rows = COUNT(*) BY parent_ci.class.keyword, child_ci.class.keyword | SORT rows DESC | LIMIT 30" }
```

**AG. Coverage: how many P1 / P2 CIs (last 6 months) the dependency index knows about**
```
POST /_query?format=json
{ "query": "FROM servicenow-incidents-*, cmdb_app_dependencies_v2 METADATA _index | WHERE (_index LIKE \"*servicenow*\" AND priority IN (1, 2) AND opened_at >= NOW() - 180 days) OR _index LIKE \"*cmdb_app_dependencies*\" | EVAL src = CASE(_index LIKE \"*servicenow*\", \"inc\", \"dep\") | EVAL as_child = CASE(src == \"dep\", TO_STRING(child_ci.name.keyword)), as_parent = CASE(src == \"dep\", TO_STRING(parent_ci.name.keyword)), inc_ci = CASE(src == \"inc\", TO_STRING(ci.name)), key = COALESCE(inc_ci, as_child) | EVAL is_inc = CASE(src == \"inc\", 1, 0), parent_of = CASE(src == \"dep\", as_parent) | STATS inc = MAX(is_inc), parents = COUNT_DISTINCT(parent_of) BY key | WHERE inc == 1 | STATS cis = COUNT(*), with_parents = COUNT(CASE(parents > 0, 1)), avg_parents = AVG(parents)" }
```
