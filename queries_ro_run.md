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

## Round 7 — alerts behind an incident, and open alerts with no incident (13 Oct 2026)

Goal: (1) show the alerts that led to the selected incident; (2) show open alerts that never became an incident. The
dashboard needs to know how an alert names its CI, whether it records the incident it raised, and how it says it is
open. Run in **Dev Tools Console** and upload the output to `round7.txt`. Each query is limited to the last 1–7 days.

**AH. Which alert / event indices exist**
```
GET _cat/indices/*alert*,*netcool*,*servicenow.event*,*em_alert*,*em_event*?v&s=index&h=index,docs.count,store.size
```

**AI. Two raw Netcool alerts** — all their fields
```
POST /_query?format=json
{ "query": "FROM .ds-bridge-alerts-netcool-default-* | WHERE @timestamp >= NOW() - 1 day | LIMIT 2" }
```

**AJ. Two ServiceNow events** — all their fields
```
POST /_query?format=json
{ "query": "FROM .ds-logs-servicenow.event-default-* | WHERE @timestamp >= NOW() - 1 day | LIMIT 2" }
```

**AK. The fields that could link an alert to a CI, an incident, or say whether it is open**
```
GET .ds-bridge-alerts-netcool-default-*,.ds-logs-servicenow.event-default-*/_field_caps?fields=*node*,*ci*,*host*,*ticket*,*incident*,*TT*,*tt*,*alert*,*severity*,*state*,*status*,*ack*,*clear*,*type*&filter_path=fields.*.*.type,fields.*.*.indices
```

**AL. Does any alert or event carry an incident number?** (incident numbers look like `INC2669663`)
```
GET .ds-bridge-alerts-netcool-default-*,.ds-logs-servicenow.event-default-*/_search
{ "size": 3, "_source": true,
  "query": { "bool": {
    "filter": [ { "range": { "@timestamp": { "gte": "now-7d" } } } ],
    "must": [ { "query_string": { "query": "INC2*", "default_field": "*", "lenient": true } } ] } } }
```

**AM. Volume per day** — decides how much a panel can scan
```
POST /_query?format=json
{ "query": "FROM .ds-bridge-alerts-netcool-default-*, .ds-logs-servicenow.event-default-* METADATA _index | WHERE @timestamp >= NOW() - 7 days | EVAL src = CASE(_index LIKE \"*netcool*\", \"netcool\", \"sn_event\") | STATS docs = COUNT(*) BY src, day = DATE_TRUNC(1 day, @timestamp) | SORT src, day" }
```

**AN. Freshness of the CMDB relations** — the *Changes* panel is now fixed to 7 days; relation records older than that
would drop the "linked CIs" from it
```
POST /_query?format=json
{ "query": "FROM cmdb-ci-relations* | STATS records = COUNT(*), last_7_days = COUNT(CASE(@timestamp >= NOW() - 7 days, 1)), oldest = MIN(@timestamp), newest = MAX(@timestamp)" }
```

What happens next, depending on the answers:

| Finding | Panel |
|---|---|
| Alerts or events record the incident number (AL / AK: a ticket or incident field) | **Alerts behind this incident** (section 2): the alerts linked to the picked incident, exactly |
| No incident number, but alerts name the CI / node (AK) | **Alerts on this CI** (section 2): alerts on the incident's CI from shortly before it opened — matched by CI and time, and labelled as such |
| A state, type or cleared field exists (AK) | **Open alerts with no incident** (section 1): alerts still open whose CI has no active incident (or with no incident number, if AL finds one) |

### Round 7 results (13 Oct)

| Query | Result | Consequence |
|---|---|---|
| AH | Netcool: `.ds-bridge-alerts-netcool-*` (~8k records a day). `.ds-logs-servicenow.event-*` is large (~300k a day). Also `paladin-alerts-*` (not used yet) | Netcool is the alert source |
| AI | Netcool records carry the CMDB CI (`ci.name`, class, support group), `node`, `severity` (0 = clear … 5 = critical), `netcool.type_name` (problem / resolution), `netcool.identifier`, `first_occurrence`, `last_occurrence`, `netcool.tally`, `netcool.acknowledged_name`. **No incident or ticket number** | Alerts are tied to incidents by CI and time |
| AJ | The ServiceNow "event" index holds ServiceNow table records (`servicenow.event.table_name` = cmdb_ci, incident, change_request …), not monitoring alerts | Not used for alerts |
| AK | 400: field pattern too complex | Not needed after AI |
| AL | Incident numbers only in ServiceNow table records (incidents, changes), not in alerts | Confirms AI |
| AM | Netcool ~8k / day; ServiceNow events ~140k–375k / day | Netcool panels can scan 30 days |
| AN | CMDB relations: 34.2M records, 129k updated in the last 7 days, oldest 2023-09 | *Changes* and *Applications on this CI* need a long panel window ("Last 5 years"); the 7-day limit on changes stays in the query |

**Built:** *Open Alerts with No Incident* (section 1) and *Alerts on this CI* (section 2).

## Round 8 — where the assigned MIM is recorded (13 Oct 2026)

The incident index (`servicenow-incidents-*`) has no MIM field: only `assigned_to`, `assignment_group` and the group's
manager, and `is_major_incident` is empty. The raw ServiceNow incident records in `.ds-logs-servicenow.event-*` carry
every filled-in ServiceNow field, including MIM fields (`u_mim_notification_count`, `u_required_p1_bridge`,
`u_managed_p2` on a P4 in round 7). These queries find the field that names the MIM on P1 / P2 incidents. Run in
**Dev Tools Console** and upload the output to `round8.txt`.

**AO. Three recent P1 / P2 incident records, every filled-in field**
```
GET .ds-logs-servicenow.event-default-*/_search
{ "size": 3, "sort": [ { "@timestamp": "desc" } ], "_source": [ "servicenow.event.*", "@timestamp" ],
  "query": { "bool": { "filter": [
    { "range": { "@timestamp": { "gte": "now-14d" } } },
    { "term": { "servicenow.event.table_name": "incident" } },
    { "terms": { "servicenow.event.priority.value": [ "1", "2" ] } } ] } } }
```

**AP. Every incident field whose name suggests a MIM, major incident or bridge**
```
GET .ds-logs-servicenow.event-default-*/_field_caps?fields=servicenow.event.*mim*,servicenow.event.*major*,servicenow.event.*bridge*&filter_path=fields.*.*.type
```

**AQ. The same for manager / coordinator / commander / promoted fields**
```
GET .ds-logs-servicenow.event-default-*/_field_caps?fields=servicenow.event.*manager*,servicenow.event.*coordinat*,servicenow.event.*command*,servicenow.event.*promot*&filter_path=fields.*.*.type
```

**AR. Which ServiceNow tables reach this index** (a separate MIM or bridge table would show up here)
```
POST /_query?format=json
{ "query": "FROM .ds-logs-servicenow.event-default-* | WHERE @timestamp >= NOW() - 1 day | STATS records = COUNT(*) BY servicenow.event.table_name | SORT records DESC | LIMIT 50" }
```

If AO–AQ show the field (for example a MIM user reference), the dashboard adds an **Assigned MIM** column to *Active
Incidents* and *Escalate*, read from the latest ServiceNow record of each incident.

### Round 8 results (13 Oct)

| Query | Result | Consequence |
|---|---|---|
| AO | 0 hits: in the raw records `priority.value` is coded (e.g. `13` = "3 - Medium"), not 1 / 2 | Incidents are matched by number instead |
| AP | ServiceNow Major Incident Management fields exist: `major_incident_state`, `u_required_p1_bridge`, `u_mim_notification_count` | — |
| AQ | `promoted_by`, `promoted_on` (who promoted the incident to a major incident, and when) | **Assigned MIM = `promoted_by`** |
| AR | Tables in the index: cmdb_ci (most), cmdb_ci_appl, cmdb_rel_ci, servers, services, **incident** (~4k records a day), rm_release, change_request | No separate MIM table |
| round8.csv | Export of `servicenow-incidents-*`: `assignment_group.name` and `assignment_group.manager.name` filled on every incident; no MIM field | Fallback when no `promoted_by`: the group manager, marked "(group manager)" |

**Built:** *Assigned MIM* column in *Active Incidents* and *Escalate*.

**Optional check (AS): how often P1 / P2 incidents carry `promoted_by`** — if the count is near zero, the column will
mostly show group managers, and the MIM must be recorded somewhere else in ServiceNow
```
POST /_query?format=json
{ "query": "FROM .ds-logs-servicenow.event-default-* | WHERE @timestamp >= NOW() - 30 days AND servicenow.event.table_name == \"incident\" | EVAL promoted = CASE(servicenow.event.promoted_by.display_value IS NOT NULL AND servicenow.event.promoted_by.display_value != \"\", servicenow.event.number.value) | STATS incidents = COUNT_DISTINCT(servicenow.event.number.value), promoted = COUNT_DISTINCT(promoted) BY priority = servicenow.event.priority.display_value | SORT priority" }
```

**AT. Who promotes, and to what state** (names the MIMs, if the field is used)
```
POST /_query?format=json
{ "query": "FROM .ds-logs-servicenow.event-default-* | WHERE @timestamp >= NOW() - 90 days AND servicenow.event.table_name == \"incident\" AND servicenow.event.promoted_by.display_value != \"\" | STATS incidents = COUNT_DISTINCT(servicenow.event.number.value) BY promoted_by = servicenow.event.promoted_by.display_value, state = servicenow.event.major_incident_state.display_value | SORT incidents DESC | LIMIT 20" }
```

