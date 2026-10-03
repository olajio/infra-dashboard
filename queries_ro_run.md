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
