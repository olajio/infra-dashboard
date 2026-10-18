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

### Round 9 results (AS, AT — 14 Oct)

| Query | Result | Consequence |
|---|---|---|
| AS | Last 30 days: P1 2 of 3 incidents promoted to major incident; P2 0 of 2,539; lower priorities 1 of ~26k | *Assigned MIM* shows the real MIM on promoted P1s and the assignment group's manager, marked "(group manager)", on everything else |
| AT | Last 90 days: all promotions by Matt Huelsman (3 Accepted, 1 Canceled) | `promoted_by` names the MIM; kept as built |

## Round 10 — CI classes for the grouped relationships, and APM coverage for application health (15 Oct 2026)

Run in **Dev Tools Console** and upload the output to `round10.txt`. AU–AW use the CMDB dependency index (no
`@timestamp`, no time filter needed); AX–AZ use APM, last day / last hour.

**AU. Every class that appears as a child (the CI that something runs on / uses)**
```
POST /_query?format=json
{ "query": "FROM cmdb_app_dependencies_v2 | WHERE child_ci.class.keyword IS NOT NULL | STATS rows = COUNT(*), cis = COUNT_DISTINCT(child_ci.name.keyword) BY class = child_ci.class.keyword | SORT rows DESC | LIMIT 300" }
```

**AV. Every class that appears as a parent (the CI that runs on / uses something)**
```
POST /_query?format=json
{ "query": "FROM cmdb_app_dependencies_v2 | WHERE parent_ci.class.keyword IS NOT NULL | STATS rows = COUNT(*), cis = COUNT_DISTINCT(parent_ci.name.keyword) BY class = parent_ci.class.keyword | SORT rows DESC | LIMIT 300" }
```

**AW. What the demo CI is related to, by class and direction** (checks the four groups on a real application service)
```
POST /_query?format=json
{ "query": "FROM cmdb_app_dependencies_v2 | WHERE parent_ci.name.keyword == \"Automated Claim Transaction PROD\" OR child_ci.name.keyword == \"Automated Claim Transaction PROD\" | EVAL direction = CASE(parent_ci.name.keyword == \"Automated Claim Transaction PROD\", \"runs on / uses\", \"used by\"), other_class = CASE(parent_ci.name.keyword == \"Automated Claim Transaction PROD\", child_ci.class.keyword, parent_ci.class.keyword), other = CASE(parent_ci.name.keyword == \"Automated Claim Transaction PROD\", child_ci.name.keyword, parent_ci.name.keyword) | STATS cis = COUNT_DISTINCT(other), examples = VALUES(other) BY direction, other_class | EVAL examples = MV_SLICE(examples, 0, 2) | SORT direction, cis DESC" }
```

**AX. How many production APM services carry their business application** (`ci.name` from the APM CMDB enrichment)
```
POST /_query?format=json
{ "query": "FROM metrics-apm.service_transaction.1m-* | WHERE @timestamp >= NOW() - 1 day AND TO_LOWER(TO_STRING(service.environment)) IN (\"prd1\", \"prd2\", \"prd\", \"prod\", \"production\") | EVAL has_app = CASE(ci.name IS NOT NULL, 1, 0), has_number = CASE(ci.number IS NOT NULL, 1, 0) | STATS with_app = MAX(has_app), with_number = MAX(has_number) BY service.name | STATS services = COUNT(*), with_app = SUM(with_app), with_number = SUM(with_number)" }
```

**AY. How many services each application has** (the 30 largest, and the spread)
```
POST /_query?format=json
{ "query": "FROM metrics-apm.service_transaction.1m-* | WHERE @timestamp >= NOW() - 1 day AND TO_LOWER(TO_STRING(service.environment)) IN (\"prd1\", \"prd2\", \"prd\", \"prod\", \"production\") AND ci.name IS NOT NULL | STATS services = COUNT_DISTINCT(service.name), names = VALUES(service.name), numbers = VALUES(ci.number) BY application = ci.name | EVAL names = MV_SLICE(names, 0, 4) | SORT services DESC | LIMIT 30" }
```

**AZ. Preview of the roll-up: application health from its services, last hour** (Failing ≥ 10 % errors, Degraded ≥ 1 %)
```
POST /_query?format=json
{ "query": "FROM metrics-apm.service_transaction.1m-* | WHERE @timestamp >= NOW() - 1 hour AND TO_LOWER(TO_STRING(service.environment)) IN (\"prd1\", \"prd2\", \"prd\", \"prod\", \"production\") AND ci.name IS NOT NULL | STATS ok = SUM(event.success_count), n = COUNT(event.success_count) BY application = ci.name, service.name | EVAL error_pct = CASE(n > 0, ROUND((n - ok) * 100.0 / n, 1)) | EVAL failing = CASE(error_pct >= 10, 1, 0), degraded = CASE(error_pct >= 1 AND error_pct < 10, 1, 0) | STATS services = COUNT(*), failing = SUM(failing), degraded = SUM(degraded), worst_error_pct = MAX(error_pct) BY application | EVAL health = CASE(failing > 0, \"Failing\", degraded > 0, \"Degraded\", \"Healthy\") | SORT failing DESC, degraded DESC, worst_error_pct DESC | LIMIT 30" }
```

What the answers decide:

| Query | Decides |
|---|---|
| AU, AV | The exact ServiceNow class names for the Middleware, Database, Server and Application groups (e.g. `cmdb_ci_app_server_tomcat`), including the server classes too small to read in `relatiosnhips2.png` |
| AW | Which groups a real application service actually has, and in which direction (runs on vs used by) |
| AX | Whether the application-health roll-up can rely on APM's `ci.name` alone (a high share = yes) or needs the CMDB link as a fallback |
| AY | Whether applications map to several services, i.e. whether a roll-up adds value over the per-service view |
| AZ | What the panel would show today, and whether the 10 % / 1 % thresholds give a sensible spread |

### Round 10 results (15 Oct)

| Query | Result | Consequence |
|---|---|---|
| AU, AV | 275 classes. The client's lists exist as e.g. `cmdb_ci_app_server_tomcat` / `_jboss` / `_jb_module` / `_tomcat_war` / `_weblogic` / `_websphere` / `_ws_ear` / `cmdb_ci_app_server`; `cmdb_ci_db_ora_instance` / `_ora_service` / `_mssql_instance` / `_mssql_database` / `_mssql_analysis` / `_mssql_integration` / `_mssql_reporting` / `_db2_instance` / `_mysql_instance` / `_postgresql_instance` / `_syb_instance` / `_mongodb_instance` / `_hbase_instance` / `_instance` / `_instance_size`, `cmdb_ci_cassandra_instance`, `cmdb_ci_cloud_database`; servers `cmdb_ci_win_server`, `_linux_server`, `_aix_server`, `_hpux_server`, `_solaris_server`, `_esx_server`, `_hyper_v_server`, `_server`, `_mainframe_lpar`, `_ibm_frame`, `_isam_server`, `_storage_server`, `_net_app_server`, `_lb_bigip`, `_lb_netscaler`; `cmdb_ci_business_app` | Exact class lists in the four views. No "DB2 Subsystem" class in the index: DB2 instances are used |
| AW | *Automated Claim Transaction PROD* runs on 2 Linux servers, a mainframe LPAR and Tomcat, uses 432 batch jobs; used by 27 application services and its business application | Both directions are needed |
| AX | 398 of 400 production APM services carry `ci.name` and `ci.number` | Application health can rely on APM alone |
| AY | Up to 25 services per application (Surety External Agency Integration 25, CNA.COM 15, PolicyCenter 13 …) | The roll-up adds value over the per-service view |
| AZ | Last hour: 15 applications Failing, 15+ Degraded at the 10 % / 1 % thresholds | Built with the same thresholds as section 4; the transaction count is shown so low-traffic noise can be judged |

**Built:** the fixed related-CI views (section 3) and *Application Health* / *Services of the Application* (section 4).


## Round 11 — Server control, Health window and automatic servers (18 Oct 2026)

**Where to run:** all of these run in **Dev Tools Console**; none needs Discover. Paste a block, put the cursor in it
and press the ▶ button (or Ctrl/Cmd + Enter). Then copy the response into `round11.txt`, with the query letter
above each one.

**Why these:** BA–BD size and time what phase 1 already does: the CI and Server lists, and the share of incident CIs
that are servers. BE–BH measure what automatic servers (step 4) would cost, so you can decide between options A–D in
*MIM-V3-SUMMARY-SERVER-CONTROL-PHASE1.md*. BI is an optional spot-check of the related-CI tables.

**Note `took` for each `POST /_query`.** It is the first line of the JSON response, in milliseconds. That is the
number that decides automatic mode.

**Go easy on the cluster.** BE–BG read every server's data in the window, which is the expensive part of automatic
mode. Run each one with `1 hour` first. Run the `24 hours` version only if `took` stayed under about 10 seconds.
Run them outside the busiest hours if you can.

The demo names are *Automated Claim Transaction PROD* (an application service) and *Claim Center* (a business
application). Replace them with any CI you prefer.

### Phase 1: list sizes and costs

**BA. Documents per day in each index the health panels read** (the `_count` API, cheap)
```
GET .ds-metrics-system.cpu-default*,.ds-metrics-system.memory-default*,.ds-metrics-system.filesystem-default*/_count
{ "query": { "range": { "@timestamp": { "gte": "now-1d" } } } }

GET metrics-system.process-*/_count
{ "query": { "range": { "@timestamp": { "gte": "now-1d" } } } }

GET metrics-windows.service-*/_count
{ "query": { "range": { "@timestamp": { "gte": "now-1d" } } } }

GET metricbeat-*/_count
{ "query": { "range": { "@timestamp": { "gte": "now-1d" } } } }

GET logs-syslog-classic-*,logs-websphere-syslog-*,logs-redhat6x-syslog-*,logs-jboss-*,logs-aix-syslog-*,logs-system.syslog-*,logs-filestream.generic-*,logs-apm.error-*,logs-apm.app.*/_count
{ "query": { "range": { "@timestamp": { "gte": "now-1d" } } } }

GET metrics-apm.internal-*/_count
{ "query": { "range": { "@timestamp": { "gte": "now-1d" } } } }

GET synthetics-*/_count
{ "query": { "range": { "@timestamp": { "gte": "now-1d" } } } }
```

**BB. Servers by environment** (which ones the CI and Server lists include: `in_list` = production, or blank)
```
POST /_query?format=txt
{ "query": """
FROM .ds-metrics-system.cpu-default*
| WHERE @timestamp >= NOW() - 1 day AND ci.name IS NOT NULL
| EVAL env = COALESCE(TO_LOWER(TO_STRING(ci.environment)), "(blank)")
| EVAL in_list = CASE(env IN ("(blank)", "", "null") OR env LIKE "prod*" OR env LIKE "prd*", "yes", "no")
| STATS servers = COUNT_DISTINCT(ci.name) BY in_list, env
| SORT in_list DESC, servers DESC
| LIMIT 100
""" }
```

**BC. The Server and CI lists as the dashboard builds them: how many options, and how long it takes** (the same
work as the two controls, ending in a count instead of the list)
```
POST /_query?format=json
{ "query": """
FROM .ds-metrics-system.cpu-default*
| WHERE @timestamp >= NOW() - 1 day AND ci.name IS NOT NULL
    AND (TO_STRING(ci.environment) IS NULL OR TO_STRING(ci.environment) IN ("", "null")
         OR TO_LOWER(TO_STRING(ci.environment)) LIKE "prod*" OR TO_LOWER(TO_STRING(ci.environment)) LIKE "prd*")
| STATS servers = VALUES(TO_STRING(ci.name))
| MV_EXPAND servers
| STATS server_list_options = COUNT(*)
""" }

POST /_query?format=json
{ "query": """
FROM servicenow-incidents-*, .ds-metrics-system.cpu-default* METADATA _index
| WHERE (priority IN (1, 2, 3) AND opened_at >= NOW() - 31 days) OR @timestamp >= NOW() - 1 day
| EVAL from_inc = _index LIKE "*servicenow*"
| WHERE ci.name IS NOT NULL AND ((from_inc AND priority IN (1, 2, 3) AND opened_at >= NOW() - 31 days)
    OR (NOT from_inc AND (TO_STRING(ci.environment) IS NULL OR TO_STRING(ci.environment) IN ("", "null")
        OR TO_LOWER(TO_STRING(ci.environment)) LIKE "prod*" OR TO_LOWER(TO_STRING(ci.environment)) LIKE "prd*")))
| STATS cis = VALUES(TO_STRING(ci.name))
| MV_EXPAND cis
| STATS ci_list_options = COUNT(*)
""" }
```

**BD. How many incident CIs are servers** (P1–P3 in the last 31 days; a server = sent CPU metrics in the last day).
The ones that are not servers are the incidents where you would pick a server in the Server control, or where
automatic mode would help.
```
POST /_query?format=txt
{ "query": """
FROM servicenow-incidents-*, .ds-metrics-system.cpu-default* METADATA _index
| WHERE (priority IN (1, 2, 3) AND opened_at >= NOW() - 31 days) OR @timestamp >= NOW() - 1 day
| EVAL from_inc = _index LIKE "*servicenow*", name = TO_LOWER(TO_STRING(ci.name))
| WHERE name IS NOT NULL
| STATS on_incident = MAX(CASE(from_inc AND priority IN (1, 2, 3) AND opened_at >= NOW() - 31 days, 1, 0)),
        is_server = MAX(CASE(from_inc, 0, 1)) BY name
| WHERE on_incident == 1
| STATS incident_cis = COUNT(*), servers = SUM(is_server)
| EVAL not_servers = incident_cis - servers
""" }
```

### Phase 2: what automatic servers would cost

Each query below does what one automatic panel would do: it finds the CI's linked CIs in the CMDB and reads
**every** server's data in the window, keeping only the linked ones at the end. The rows show which linked CIs send
data. Run each with `1 hour` as written, then change both `1 hour`s to `24 hours` and run it again.

**BE. Server Health** (CPU, memory, disk: the lightest data)
```
POST /_query?format=json
{ "query": """
FROM .ds-metrics-system.cpu-default*, .ds-metrics-system.memory-default*, .ds-metrics-system.filesystem-default*, cmdb-ci-relations* METADATA _index
| WHERE @timestamp >= NOW() - 1 hour
    OR parent.name == "Automated Claim Transaction PROD" OR child.name == "Automated Claim Transaction PROD"
| EVAL is_rel = _index LIKE "*relations*", app = "automated claim transaction prod",
       p = TO_LOWER(TO_STRING(parent.name)), c = TO_LOWER(TO_STRING(child.name))
| EVAL name = CASE(is_rel AND p == app, c, is_rel AND c == app, p, is_rel, NULL, TO_LOWER(TO_STRING(ci.name)))
| WHERE name IS NOT NULL AND (is_rel OR @timestamp >= NOW() - 1 hour)
| STATS linked = MAX(CASE(is_rel, 1, 0)), data_docs = SUM(CASE(is_rel, 0, 1)), last_data = MAX(CASE(is_rel, NULL, @timestamp)) BY name
| WHERE linked == 1
| SORT data_docs DESC, name ASC
| LIMIT 100
""" }
```

**BF. Process and Windows services** (Middleware, Database and Process Health)
```
POST /_query?format=json
{ "query": """
FROM metrics-system.process-*, metrics-windows.service-*, cmdb-ci-relations* METADATA _index
| WHERE @timestamp >= NOW() - 1 hour
    OR parent.name == "Automated Claim Transaction PROD" OR child.name == "Automated Claim Transaction PROD"
| EVAL is_rel = _index LIKE "*relations*", app = "automated claim transaction prod",
       p = TO_LOWER(TO_STRING(parent.name)), c = TO_LOWER(TO_STRING(child.name))
| EVAL name = CASE(is_rel AND p == app, c, is_rel AND c == app, p, is_rel, NULL, TO_LOWER(TO_STRING(ci.name)))
| WHERE name IS NOT NULL AND (is_rel OR @timestamp >= NOW() - 1 hour)
| STATS linked = MAX(CASE(is_rel, 1, 0)), data_docs = SUM(CASE(is_rel, 0, 1)), last_data = MAX(CASE(is_rel, NULL, @timestamp)) BY name
| WHERE linked == 1
| SORT data_docs DESC, name ASC
| LIMIT 100
""" }
```

**BG. Logs** (Errors from the Logs; every log line, so this is the upper bound: the panel itself also filters on
severity)
```
POST /_query?format=json
{ "query": """
FROM logs-syslog-classic-*, logs-websphere-syslog-*, logs-redhat6x-syslog-*, logs-jboss-*, logs-aix-syslog-*, logs-system.syslog-*, logs-filestream.generic-*, logs-apm.error-*, logs-apm.app.*, cmdb-ci-relations* METADATA _index
| WHERE @timestamp >= NOW() - 1 hour
    OR parent.name == "Automated Claim Transaction PROD" OR child.name == "Automated Claim Transaction PROD"
| EVAL is_rel = _index LIKE "*relations*", app = "automated claim transaction prod",
       p = TO_LOWER(TO_STRING(parent.name)), c = TO_LOWER(TO_STRING(child.name))
| EVAL name = CASE(is_rel AND p == app, c, is_rel AND c == app, p, is_rel, NULL, TO_LOWER(TO_STRING(ci.name)))
| WHERE name IS NOT NULL AND (is_rel OR @timestamp >= NOW() - 1 hour)
| STATS linked = MAX(CASE(is_rel, 1, 0)), data_docs = SUM(CASE(is_rel, 0, 1)), last_data = MAX(CASE(is_rel, NULL, @timestamp)) BY name
| WHERE linked == 1
| SORT data_docs DESC, name ASC
| LIMIT 100
""" }
```

**BH. A business application's servers through APM** (the hosts its services run on). Shows what automatic mode
would find for a business application, which has no servers linked directly in the CMDB.
```
POST /_query?format=json
{ "query": """
FROM metrics-apm.service_transaction.1m-*, metrics-apm.internal-* METADATA _index
| WHERE @timestamp >= NOW() - 1 hour
| EVAL is_tx = _index LIKE "*service_transaction*"
| STATS apps = VALUES(CASE(is_tx, TO_STRING(ci.name))), hosts = VALUES(CASE(NOT is_tx, TO_LOWER(TO_STRING(host.name)))) BY service.name
| WHERE apps == "Claim Center"
| MV_EXPAND hosts
| STATS services = VALUES(service.name) BY host = hosts
| SORT host
| LIMIT 100
""" }
```

### Optional

**BI. Everything the CMDB links to one CI** (compare with the dashboard's related-CI tables, or with ServiceNow; no
time range needed in Dev Tools)
```
POST /_query?format=txt
{ "query": """
FROM cmdb-ci-relations*
| WHERE parent.name == "Claim Center PROD" OR child.name == "Claim Center PROD"
| EVAL down = parent.name == "Claim Center PROD"
| EVAL related = CASE(down, child.name, parent.name), class = CASE(down, child.class, parent.class),
       direction = CASE(down, "this CI → it", "it → this CI")
| STATS links = COUNT(*), examples = VALUES(related) BY class, direction, type.name
| EVAL examples = MV_SLICE(examples, 0, 4)
| SORT links DESC
| LIMIT 200
""" }
```

### What the answers decide

| Query | Decides |
|---|---|
| BA | How much data automatic mode would scan per day, per panel. A few million documents a day: fine up to 24 hours. Hundreds of millions: too slow |
| BB, BC | Whether the CI and Server lists stay under Kibana's 10,000-option limit, whether the "production or blank" rule keeps the right servers, and how long the two lists take to build (they run every time the dashboard loads) |
| BD | How often an incident's CI is not a server, i.e. how often the Server control or automatic mode is needed at all |
| BE–BG | The real cost of automatic mode per panel (`took`, 1 hour and 24 hours), and whether the demo CI's linked servers send data. Over about 10 s at 24 hours means option A is too slow for that panel |
| BH | Whether APM finds the servers of a business application (the second way automatic mode finds servers) |
| BI | Optional check that the related-CI tables show every CMDB link of a CI |

### Round 11 results (18 Oct)

| Query | Result | Consequence |
|---|---|---|
| BA | Documents per day: CPU / memory / disk 17.7 M; processes 202 M; Windows services 42.6 M; `metricbeat-*` 18 M; logs **1.1 billion** (3,039 shards); APM internal 19.9 M; synthetics 4.6 M | Logs and processes are far too big to scan in full |
| BB | 1,224 production servers and 2 with a blank environment are in the lists. 1,506 others are left out (drt 449, cut 410, ete 303, dre 130, dev 97, sandbox 68, test 46, eit 3) | As intended. Say if the DR servers (drt / dre) should be listed too |
| BC | Server list 1,225 options in 0.3 s; CI list 2,541 options in 0.5 s | Well under the 10,000 limit, and fast |
| BD | 1,725 CIs had a P1–P3 in 31 days: 858 are servers, **867 are not** | Half of the incidents need a server picked (Server control) or found automatically |
| BE | Server Health, automatic: 1 hour 1.4 s (0.8 M documents, 10 CPU-seconds); 24 hours **8.9 s** (17.8 M documents, **582 CPU-seconds**). The demo CI's servers with data: vslrau1p276, vslrau1p174, vcwau1p0132 | Too heavy at 24 hours: about 10 CPU-minutes of cluster work per viewer every 5-minute refresh. 7 days would be about 4× more |
| BF | Processes, automatic: 1 hour 4.2 s (10 M documents, 166 CPU-seconds); 24 hours **failed (502 Bad Gateway: timed out)** | Not usable beyond very short windows |
| BG | Logs, automatic: **failed at 1 hour** (502) | Not usable at all |
| BH | Error: `apps` holds several values for some services, which `==` rejects | Fixed below (BH2) |
| BI | *Claim Center PROD* has about 160 linked servers (88 Linux, 48 AIX, 20 Windows, 2 HP-UX …), batch jobs, WebSphere / JBoss, Oracle … | The related-CI tables show these. 10 links have no name or class in the CMDB (empty records) and cannot be shown. An automatic mode on every panel would list ~160 servers' processes and logs for one application |

**Discover's "Function NOT not allowed in STATS".** Kibana's query editor rejects `NOT` inside `STATS`. Elasticsearch
accepts it (BE ran in Dev Tools). No dashboard query uses it. BE–BG and BM below now use `CASE(is_rel, NULL, …)`
instead, so they also run in Discover.

**Decision this supports:** automatic mode on all health panels (option A) is not possible on this cluster. Even
Server Health alone is too heavy at 24 hours. See *MIM-V3-AUTOMATIC-SERVERS-DECISION.md* for the cheaper proposal
(BM measures it).

## Round 11b — phase 1 panel cost, BH fixed, and the cheap automatic option (18 Oct 2026)

**Where to run:** all in **Dev Tools Console**, as before. Copy the responses into `round11b.txt` and note `took`
for each one.

**BJ–BL time the dashboard's own phase 1 queries.** They are copied from the dashboard, with the Server control set
to `vslrau1p276` (one of the demo CI's servers), as if you had picked it. Run each with `"24 hours"`, then change
`"health_window"` to `"7 days"` and run again. For BL (logs), run `"7 days"` only if 24 hours took under 10 seconds.

**BH2. A business application's servers through APM** (fixed)
```
POST /_query?format=txt
{ "query": """
FROM metrics-apm.service_transaction.1m-*, metrics-apm.internal-* METADATA _index
| WHERE @timestamp >= NOW() - 1 hour
| EVAL is_tx = _index LIKE "*service_transaction*"
| WHERE NOT is_tx OR ci.name == "Claim Center"
| STATS in_app = MAX(CASE(is_tx, 1, 0)), hosts = VALUES(CASE(is_tx, NULL, TO_LOWER(TO_STRING(host.name)))) BY service.name
| WHERE in_app == 1
| MV_EXPAND hosts
| STATS services = VALUES(service.name) BY host = hosts
| SORT host
| LIMIT 100
""" }
```

**BJ. Server Health, phase 1** (24 hours, then 7 days)
```
POST /_query?format=json
{ "query": """
FROM .ds-metrics-system.cpu-default*, .ds-metrics-system.memory-default*, .ds-metrics-system.filesystem-default*, cmdb-ci-relations* METADATA _index
| WHERE (@timestamp >= NOW() - TO_TIMEDURATION(CASE(?health_window == "3 days", "72 hours", ?health_window == "7 days", "168 hours", ?health_window)) AND (ci.name IN (CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)), TO_UPPER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), TO_LOWER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), CASE(?ci == "(no CI selected)", "", ?ci), TO_UPPER(CASE(?ci == "(no CI selected)", "", ?ci)), TO_LOWER(CASE(?ci == "(no CI selected)", "", ?ci)), CASE(?server == "(no server selected)", "", ?server), TO_UPPER(CASE(?server == "(no server selected)", "", ?server)), TO_LOWER(CASE(?server == "(no server selected)", "", ?server))))) OR parent.name IN (CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)), TO_UPPER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), TO_LOWER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), CASE(?ci == "(no CI selected)", "", ?ci), TO_UPPER(CASE(?ci == "(no CI selected)", "", ?ci)), TO_LOWER(CASE(?ci == "(no CI selected)", "", ?ci)), CASE(?server == "(no server selected)", "", ?server), TO_UPPER(CASE(?server == "(no server selected)", "", ?server)), TO_LOWER(CASE(?server == "(no server selected)", "", ?server))) OR child.name IN (CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)), TO_UPPER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), TO_LOWER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), CASE(?ci == "(no CI selected)", "", ?ci), TO_UPPER(CASE(?ci == "(no CI selected)", "", ?ci)), TO_LOWER(CASE(?ci == "(no CI selected)", "", ?ci)), CASE(?server == "(no server selected)", "", ?server), TO_UPPER(CASE(?server == "(no server selected)", "", ?server)), TO_LOWER(CASE(?server == "(no server selected)", "", ?server)))
| EVAL is_rel = _index LIKE "*relations*", is_cpu = _index LIKE "*metrics-system.cpu*"
| EVAL inc_l = TO_LOWER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), ci_l = TO_LOWER(CASE(?ci == "(no CI selected)", "", ?ci)), srv_l = TO_LOWER(CASE(?server == "(no server selected)", "", ?server)),
       p_l = TO_LOWER(TO_STRING(parent.name)), c_l = TO_LOWER(TO_STRING(child.name)),
       p_srv = TO_STRING(parent.class) IN ("cmdb_ci_aix_server", "cmdb_ci_esx_server", "cmdb_ci_hpux_server", "cmdb_ci_hyper_v_server", "cmdb_ci_ibm_frame", "cmdb_ci_isam_server", "cmdb_ci_lb_bigip", "cmdb_ci_lb_netscaler", "cmdb_ci_linux_server", "cmdb_ci_mainframe", "cmdb_ci_mainframe_lpar", "cmdb_ci_net_app_server", "cmdb_ci_server", "cmdb_ci_solaris_server", "cmdb_ci_storage_server", "cmdb_ci_win_server"), c_srv = TO_STRING(child.class) IN ("cmdb_ci_aix_server", "cmdb_ci_esx_server", "cmdb_ci_hpux_server", "cmdb_ci_hyper_v_server", "cmdb_ci_ibm_frame", "cmdb_ci_isam_server", "cmdb_ci_lb_bigip", "cmdb_ci_lb_netscaler", "cmdb_ci_linux_server", "cmdb_ci_mainframe", "cmdb_ci_mainframe_lpar", "cmdb_ci_net_app_server", "cmdb_ci_server", "cmdb_ci_solaris_server", "cmdb_ci_storage_server", "cmdb_ci_win_server"),
       cpu_l = CASE(is_cpu, TO_LOWER(TO_STRING(ci.name)))
| EVAL inc_hit = CASE(inc_l == "", 0, is_rel AND ((p_l == inc_l AND p_srv) OR (c_l == inc_l AND c_srv)), 1, cpu_l == inc_l, 1, 0),
       ci_hit = CASE(ci_l == "", 0, is_rel AND ((p_l == ci_l AND p_srv) OR (c_l == ci_l AND c_srv)), 1, cpu_l == ci_l, 1, 0)
| INLINE STATS inc_is_server = MAX(inc_hit), ci_is_server = MAX(ci_hit)
| EVAL target = CASE(inc_is_server == 1, inc_l, ci_is_server == 1, ci_l, srv_l != "", srv_l)
| EVAL is_data = NOT is_rel AND (true)
| WHERE target IS NOT NULL AND ((is_data AND TO_LOWER(TO_STRING(ci.name)) == target)
     OR (is_rel AND (p_l == target OR c_l == target)))
| EVAL srv = CASE(is_data, TO_STRING(ci.name), p_l == target, TO_STRING(parent.name), TO_STRING(child.name))
| STATS cpu = PERCENTILE(system.cpu.total.norm.pct, 90), mem = MAX(system.memory.actual.used.pct),
        disk = MAX(system.filesystem.used.pct), last_seen = MAX(CASE(is_data, @timestamp)), names = VALUES(srv)
  BY server_key = TO_LOWER(srv)
| EVAL server = MV_FIRST(names), silent_min = DATE_DIFF("minutes", last_seen, NOW())
| EVAL status = CASE(last_seen IS NULL, "No data in window", silent_min > 10, "Silent", "Reporting"),
       cpu_p90 = ROUND(cpu * 100, 1), mem_peak = ROUND(mem * 100, 1), disk_max = ROUND(disk * 100, 1),
       rank = CASE(last_seen IS NULL, 1, silent_min > 10, 2, 3)
| SORT rank ASC, server ASC
| KEEP server, status, silent_min, cpu_p90, mem_peak, disk_max
""",
  "params": [
  {"ci": "(no CI selected)"},
  {"health_window": "24 hours"},
  {"incident": "(all incidents)"},
  {"server": "vslrau1p276"}
  ],
  "filter": { "range": { "@timestamp": { "gte": "now-5y" } } } }
```

**BK. Process Health, phase 1** (24 hours, then 7 days)
```
POST /_query?format=json
{ "query": """
FROM metrics-windows.service-*, metrics-system.process-*, .ds-metrics-system.cpu-default*, cmdb-ci-relations* METADATA _index
| WHERE (@timestamp >= NOW() - TO_TIMEDURATION(CASE(?health_window == "3 days", "72 hours", ?health_window == "7 days", "168 hours", ?health_window)) AND (ci.name IN (CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)), TO_UPPER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), TO_LOWER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), CASE(?ci == "(no CI selected)", "", ?ci), TO_UPPER(CASE(?ci == "(no CI selected)", "", ?ci)), TO_LOWER(CASE(?ci == "(no CI selected)", "", ?ci)), CASE(?server == "(no server selected)", "", ?server), TO_UPPER(CASE(?server == "(no server selected)", "", ?server)), TO_LOWER(CASE(?server == "(no server selected)", "", ?server))))) OR parent.name IN (CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)), TO_UPPER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), TO_LOWER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), CASE(?ci == "(no CI selected)", "", ?ci), TO_UPPER(CASE(?ci == "(no CI selected)", "", ?ci)), TO_LOWER(CASE(?ci == "(no CI selected)", "", ?ci)), CASE(?server == "(no server selected)", "", ?server), TO_UPPER(CASE(?server == "(no server selected)", "", ?server)), TO_LOWER(CASE(?server == "(no server selected)", "", ?server))) OR child.name IN (CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)), TO_UPPER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), TO_LOWER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), CASE(?ci == "(no CI selected)", "", ?ci), TO_UPPER(CASE(?ci == "(no CI selected)", "", ?ci)), TO_LOWER(CASE(?ci == "(no CI selected)", "", ?ci)), CASE(?server == "(no server selected)", "", ?server), TO_UPPER(CASE(?server == "(no server selected)", "", ?server)), TO_LOWER(CASE(?server == "(no server selected)", "", ?server)))
| EVAL is_rel = _index LIKE "*relations*", is_cpu = _index LIKE "*metrics-system.cpu*"
| EVAL inc_l = TO_LOWER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), ci_l = TO_LOWER(CASE(?ci == "(no CI selected)", "", ?ci)), srv_l = TO_LOWER(CASE(?server == "(no server selected)", "", ?server)),
       p_l = TO_LOWER(TO_STRING(parent.name)), c_l = TO_LOWER(TO_STRING(child.name)),
       p_srv = TO_STRING(parent.class) IN ("cmdb_ci_aix_server", "cmdb_ci_esx_server", "cmdb_ci_hpux_server", "cmdb_ci_hyper_v_server", "cmdb_ci_ibm_frame", "cmdb_ci_isam_server", "cmdb_ci_lb_bigip", "cmdb_ci_lb_netscaler", "cmdb_ci_linux_server", "cmdb_ci_mainframe", "cmdb_ci_mainframe_lpar", "cmdb_ci_net_app_server", "cmdb_ci_server", "cmdb_ci_solaris_server", "cmdb_ci_storage_server", "cmdb_ci_win_server"), c_srv = TO_STRING(child.class) IN ("cmdb_ci_aix_server", "cmdb_ci_esx_server", "cmdb_ci_hpux_server", "cmdb_ci_hyper_v_server", "cmdb_ci_ibm_frame", "cmdb_ci_isam_server", "cmdb_ci_lb_bigip", "cmdb_ci_lb_netscaler", "cmdb_ci_linux_server", "cmdb_ci_mainframe", "cmdb_ci_mainframe_lpar", "cmdb_ci_net_app_server", "cmdb_ci_server", "cmdb_ci_solaris_server", "cmdb_ci_storage_server", "cmdb_ci_win_server"),
       cpu_l = CASE(is_cpu, TO_LOWER(TO_STRING(ci.name)))
| EVAL inc_hit = CASE(inc_l == "", 0, is_rel AND ((p_l == inc_l AND p_srv) OR (c_l == inc_l AND c_srv)), 1, cpu_l == inc_l, 1, 0),
       ci_hit = CASE(ci_l == "", 0, is_rel AND ((p_l == ci_l AND p_srv) OR (c_l == ci_l AND c_srv)), 1, cpu_l == ci_l, 1, 0)
| INLINE STATS inc_is_server = MAX(inc_hit), ci_is_server = MAX(ci_hit)
| EVAL target = CASE(inc_is_server == 1, inc_l, ci_is_server == 1, ci_l, srv_l != "", srv_l)
| EVAL is_data = NOT is_rel AND (NOT is_cpu OR false)
| WHERE is_data AND target IS NOT NULL AND TO_LOWER(TO_STRING(ci.name)) == target AND (windows.service.name IS NOT NULL OR paladin.enrichment.computed.proc_type IS NOT NULL)
| EVAL kind = CASE(windows.service.name IS NOT NULL, "Windows service", "Middleware process")
| EVAL ptype = TO_STRING(paladin.enrichment.computed.proc_type), pinst = TO_STRING(paladin.enrichment.computed.proc_instance)
| EVAL name = CASE(kind == "Windows service",
      CONCAT(COALESCE(TO_STRING(windows.service.display_name), TO_STRING(windows.service.name)), " (", TO_STRING(windows.service.name), ")"),
      CASE(pinst IS NULL OR pinst == "n/a", ptype, CONCAT(ptype, " · ", pinst)))
| EVAL st = CASE(kind == "Windows service", TO_STRING(windows.service.state), "Running")
| STATS last_ts = MAX(@timestamp), latest = MAX(CONCAT(TO_STRING(TO_LONG(@timestamp)), "~", st)),
        starts = VALUES(TO_STRING(windows.service.start_type)),
        owners = VALUES(TO_STRING(`enrich_policy.cmdb-cis.proc_assignment`))
  BY kind, name
| DISSECT latest "%{ts}~%{state_now}"
| EVAL start_type = MV_FIRST(starts), minutes_since = DATE_DIFF("minutes", last_ts, NOW())
| EVAL status = CASE(
      minutes_since > 10, "Not seen",
      kind == "Windows service" AND state_now != "Running" AND start_type LIKE "Automatic*", "Stopped",
      kind == "Windows service" AND state_now != "Running", CONCAT("Not running (", COALESCE(start_type, "?"), ")"),
      "Running")
| WHERE status IN ("Stopped", "Not seen") OR kind == "Middleware process" OR TO_LOWER(name) RLIKE ".*(sql|w3svc|iis|mq|websphere|jboss|tomcat|oracle|httpd|ihs|weblogic).*"
| EVAL owner = MV_FIRST(owners), rank = CASE(status IN ("Stopped", "Not seen"), 1, 2)
| SORT rank ASC, kind ASC, name ASC
| LIMIT 100
| KEEP name, status, kind, minutes_since, owner
""",
  "params": [
  {"ci": "(no CI selected)"},
  {"health_window": "24 hours"},
  {"incident": "(all incidents)"},
  {"server": "vslrau1p276"}
  ],
  "filter": { "range": { "@timestamp": { "gte": "now-5y" } } } }
```

**BL. Errors from the Logs, phase 1** (24 hours; 7 days only if 24 hours took under 10 s)
```
POST /_query?format=json
{ "query": """
FROM logs-syslog-classic-*, logs-websphere-syslog-*, logs-redhat6x-syslog-*, logs-jboss-*, logs-aix-syslog-*, logs-system.syslog-*, logs-filestream.generic-*, logs-apm.error-*, logs-apm.app.*, .ds-metrics-system.cpu-default*, cmdb-ci-relations* METADATA _index
| WHERE (@timestamp >= NOW() - TO_TIMEDURATION(CASE(?health_window == "3 days", "72 hours", ?health_window == "7 days", "168 hours", ?health_window)) AND (ci.name IN (CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)), TO_UPPER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), TO_LOWER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), CASE(?ci == "(no CI selected)", "", ?ci), TO_UPPER(CASE(?ci == "(no CI selected)", "", ?ci)), TO_LOWER(CASE(?ci == "(no CI selected)", "", ?ci)), CASE(?server == "(no server selected)", "", ?server), TO_UPPER(CASE(?server == "(no server selected)", "", ?server)), TO_LOWER(CASE(?server == "(no server selected)", "", ?server))))) OR parent.name IN (CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)), TO_UPPER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), TO_LOWER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), CASE(?ci == "(no CI selected)", "", ?ci), TO_UPPER(CASE(?ci == "(no CI selected)", "", ?ci)), TO_LOWER(CASE(?ci == "(no CI selected)", "", ?ci)), CASE(?server == "(no server selected)", "", ?server), TO_UPPER(CASE(?server == "(no server selected)", "", ?server)), TO_LOWER(CASE(?server == "(no server selected)", "", ?server))) OR child.name IN (CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3)), TO_UPPER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), TO_LOWER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), CASE(?ci == "(no CI selected)", "", ?ci), TO_UPPER(CASE(?ci == "(no CI selected)", "", ?ci)), TO_LOWER(CASE(?ci == "(no CI selected)", "", ?ci)), CASE(?server == "(no server selected)", "", ?server), TO_UPPER(CASE(?server == "(no server selected)", "", ?server)), TO_LOWER(CASE(?server == "(no server selected)", "", ?server)))
| EVAL is_rel = _index LIKE "*relations*", is_cpu = _index LIKE "*metrics-system.cpu*"
| EVAL inc_l = TO_LOWER(CASE(?incident == "(all incidents)", "", SUBSTRING(?incident, LOCATE(?incident, " · ") + 3))), ci_l = TO_LOWER(CASE(?ci == "(no CI selected)", "", ?ci)), srv_l = TO_LOWER(CASE(?server == "(no server selected)", "", ?server)),
       p_l = TO_LOWER(TO_STRING(parent.name)), c_l = TO_LOWER(TO_STRING(child.name)),
       p_srv = TO_STRING(parent.class) IN ("cmdb_ci_aix_server", "cmdb_ci_esx_server", "cmdb_ci_hpux_server", "cmdb_ci_hyper_v_server", "cmdb_ci_ibm_frame", "cmdb_ci_isam_server", "cmdb_ci_lb_bigip", "cmdb_ci_lb_netscaler", "cmdb_ci_linux_server", "cmdb_ci_mainframe", "cmdb_ci_mainframe_lpar", "cmdb_ci_net_app_server", "cmdb_ci_server", "cmdb_ci_solaris_server", "cmdb_ci_storage_server", "cmdb_ci_win_server"), c_srv = TO_STRING(child.class) IN ("cmdb_ci_aix_server", "cmdb_ci_esx_server", "cmdb_ci_hpux_server", "cmdb_ci_hyper_v_server", "cmdb_ci_ibm_frame", "cmdb_ci_isam_server", "cmdb_ci_lb_bigip", "cmdb_ci_lb_netscaler", "cmdb_ci_linux_server", "cmdb_ci_mainframe", "cmdb_ci_mainframe_lpar", "cmdb_ci_net_app_server", "cmdb_ci_server", "cmdb_ci_solaris_server", "cmdb_ci_storage_server", "cmdb_ci_win_server"),
       cpu_l = CASE(is_cpu, TO_LOWER(TO_STRING(ci.name)))
| EVAL inc_hit = CASE(inc_l == "", 0, is_rel AND ((p_l == inc_l AND p_srv) OR (c_l == inc_l AND c_srv)), 1, cpu_l == inc_l, 1, 0),
       ci_hit = CASE(ci_l == "", 0, is_rel AND ((p_l == ci_l AND p_srv) OR (c_l == ci_l AND c_srv)), 1, cpu_l == ci_l, 1, 0)
| INLINE STATS inc_is_server = MAX(inc_hit), ci_is_server = MAX(ci_hit)
| EVAL target = CASE(inc_is_server == 1, inc_l, ci_is_server == 1, ci_l, srv_l != "", srv_l)
| EVAL is_data = NOT is_rel AND (NOT is_cpu OR false)
| WHERE is_data AND target IS NOT NULL AND TO_LOWER(TO_STRING(ci.name)) == target
| EVAL lvl = TO_LOWER(TO_STRING(log.level))
| EVAL sev_code = COALESCE(TO_INTEGER(syslog_severity_code),
      CASE(lvl IN ("emergency", "emerg", "alert", "critical", "crit", "fatal"), 2, lvl IN ("error", "err", "severe"), 3,
           lvl IN ("warning", "warn"), 4, 6))
| WHERE sev_code <= 4
| EVAL severity = CASE(sev_code <= 2, "critical", sev_code == 3, "error", "warning"), sev_rank = sev_code
| EVAL msg = SUBSTRING(TO_STRING(message), 1, 400)
| GROK msg "<%{INT}>%{NOTSPACE} %{NOTSPACE} %{GREEDYDATA:body}"
| EVAL text = SUBSTRING(REPLACE(COALESCE(body, msg), "[0-9]+", "#"), 1, 160), source = TO_STRING(data_stream.dataset)
| STATS occurrences = COUNT(*), first_seen = MIN(@timestamp), last_seen = MAX(@timestamp) BY sev_rank, severity, source, text
| SORT sev_rank ASC, occurrences DESC
| LIMIT 50
| KEEP occurrences, severity, source, text, first_seen, last_seen
""",
  "params": [
  {"ci": "(no CI selected)"},
  {"health_window": "24 hours"},
  {"incident": "(all incidents)"},
  {"server": "vslrau1p276"}
  ],
  "filter": { "range": { "@timestamp": { "gte": "now-5y" } } } }
```

**BM. The cheap automatic option: live status of the demo CI's linked servers, last 15 minutes** (CPU data only).
*No longer needed: you chose to keep phase 1 only. Run it only if you want option E reconsidered.*
```
POST /_query?format=json
{ "query": """
FROM .ds-metrics-system.cpu-default*, cmdb-ci-relations* METADATA _index
| WHERE @timestamp >= NOW() - 15 minutes
    OR parent.name == "Automated Claim Transaction PROD" OR child.name == "Automated Claim Transaction PROD"
| EVAL is_rel = _index LIKE "*relations*", app = "automated claim transaction prod",
       p = TO_LOWER(TO_STRING(parent.name)), c = TO_LOWER(TO_STRING(child.name))
| EVAL name = CASE(is_rel AND p == app, c, is_rel AND c == app, p, is_rel, NULL, TO_LOWER(TO_STRING(ci.name)))
| WHERE name IS NOT NULL AND (is_rel OR @timestamp >= NOW() - 15 minutes)
| STATS linked = MAX(CASE(is_rel, 1, 0)), last_data = MAX(CASE(is_rel, NULL, @timestamp)),
        cpu_max = MAX(system.cpu.total.norm.pct) BY name
| WHERE linked == 1 AND last_data IS NOT NULL
| EVAL min_ago = DATE_DIFF("minutes", last_data, NOW()), cpu_max = ROUND(cpu_max * 100, 1)
| SORT name
| LIMIT 100
""" }
```
Then do the same with *Claim Center PROD* (about 160 linked servers) in place of the demo CI, in both places, to see
the cost for a large application.

| Query | Decides |
|---|---|
| BH2 | Whether APM finds a business application's servers |
| BJ–BL | Whether phase 1's panels are fast enough on real data, especially logs at 7 days (1.1 billion log lines a day) |
| BM | Optional, no longer needed: the cost of option E |
