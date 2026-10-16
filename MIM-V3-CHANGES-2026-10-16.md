# MIM V3 — changes on Friday 16 Oct 2026, and what is left on the cluster

## Changes (from the updated `suggestions2.txt`)

| # | Request | What changed |
|---|---|---|
| 1 | Users impacted text | The tile reads **"Real count to be incorporated from ServiceNow and RUM"** under the 2,500 demo number. |
| 2 | Remove Applications impacted | Removed from section 1. |
| 3 | Active Incidents columns | Exactly these ten columns: Incident, Pri, Affected CI, State, SLA, Assignment Group, Assignee, Assignee Email, Group Manager Name, Manager Email Id. Assigned MIM, Opened, Age and Short description are gone. |
| 4 | Open Alerts with No Incident, 24 hours | The panel looks at the last 24 hours. **Limit:** an open incident that was not updated in the last 24 hours is not seen, so its alerts can show as "no incident". |
| 5 | Investigate the CI (Escalate) columns | Eleven columns: CI, Active Incident, Priority, Class, Env, CI support group, Assignment Group, Assignee, Assignee Email, Group Manager Name, Manager Email Id. Assigned MIM is gone. |
| 6 | Remove CMDB status | Removed from *Applications that depend on this CI*. |
| 7 | Remove What this CI runs on | Removed; *Applications that depend on this CI* is widened to fill the row. |
| 8 | First two panels black | *Active P1 / P2* (donut) and *Users impacted* both have a black background. |

Section 3 keeps the four views (Middleware, Database, Server, Application), as agreed.

**Checks:** the test (`tools/test_mim_v3_2026-10-16.py`) passes on local Elasticsearch / Kibana 9.4.1, the link
check passes, and screenshots were taken. Nothing has been checked on the 9.5.3 cluster yet.

## Re-check of the current version (16 Oct, later)
The cluster still has this version, and `MIM V3.ndjson` in the repo is byte-for-byte the 16 Oct version
(commit `9886491`). Re-checked against local Elasticsearch / Kibana 9.4.1:

- All three tests pass: 14 Oct (15 checks), 15 Oct (18 checks), 16 Oct (13 checks). The 14 Oct test was updated
  because *Active P1 / P2* became a Vega donut on 16 Oct; it now runs the donut's own query.
- All link columns are real fields, so Kibana 9.5 allows the links.
- All 31 queries (panels, both Vega panels, four controls) parse. 21 run with the small test data. The other 10 stop
  only on "Unknown column" / "Unknown index", because the test data does not include those fields: Time to Resolve,
  Open Alerts with No Incident, Alerts on this CI, Process, Synthetics, Logs, Changes, Upstream, Downstream, Business
  applications impacted. None of these were changed on 16 Oct, and they read the real fields on the cluster.
- The dashboard imports cleanly; the top row shows the black donut and Users impacted tile, and Active Incidents shows
  the ten columns.

So nothing in the dashboard file needs changing. What is left is on the cluster side, below.

## What is left to do on the cluster

### 1. Import the dashboard (already done if the cluster has the 16 Oct version)
1. Stack Management → Saved objects → Import `MIM V3.ndjson`, choosing **overwrite**. It replaces the colleague's
   version (same dashboard id) and adds the new **Application** control.
2. Open the dashboard, then **More → Reset changes** and reload the page, so Kibana drops any unsaved layout it kept
   from the old version.

### 2. Optional clean-up
- The colleague's data view `cmdb_app_dependencies_v2` (id `1e5c8fab-f6d6-4546-8fd1-b54ac1281ad5`) is no longer used
  by the dashboard. Delete it only if nothing else uses it (Saved objects → the data view → Relationships).

### 3. Viewer access
Viewers need read access to every index the panels read, or the panel shows an error instead of "no results":

| Data | Indices |
|---|---|
| ServiceNow | `servicenow-incidents-*`, `servicenow-task-sla-*`, `servicenow-change-requests-*` |
| CMDB | `cmdb-ci-relations*`, `cmdb_app_dependencies_v2` |
| Netcool alerts | `.ds-bridge-alerts-netcool-default-*` (hidden backing indices) |
| Server metrics | `.ds-metrics-system.cpu-default*`, `.ds-metrics-system.memory-default*`, `.ds-metrics-system.filesystem-default*` (hidden), `metrics-system.process-*`, `metrics-windows.service-*`, `metricbeat-*` |
| APM | `metrics-apm.service_transaction.1m-*`, `metrics-apm.service_destination.1m-*`, `metrics-apm.internal-*`, `traces-apm*`, `logs-apm.app.*`, `logs-apm.error-*` |
| Logs | `logs-syslog-classic-*`, `logs-system.syslog-*`, `logs-aix-syslog-*`, `logs-redhat6x-syslog-*`, `logs-websphere-syslog-*`, `logs-jboss-*`, `logs-filestream.generic-*` |
| Synthetics | `synthetics-*` |
| SLOs | `.slo-observability.summary-v3*` (hidden) |

A role that grants `metrics-*` or `logs-*` does not by itself cover the `.ds-…` names that some panels read directly;
grant those patterns too.

### 4. Check on 9.5.3 after the import
- *Active P1 / P2* and *Users impacted* render on black (both are Vega panels).
- Picking an incident fills sections 2 and 3 with its CI.
- The four views in section 3 fill for a CI that has CMDB relationships.
- The Application control filters *Application Health* and *Services of the Application*.
- Click-through links work in view mode (Active Incidents, Escalate, the CMDB links).

## Not dashboard changes (need other teams)
- **Live health in the CMDB views:** needs an `@timestamp` on `cmdb_app_dependencies_v2`.
- **Real users-impacted count:** needs ATOS to ingest the ServiceNow / RUM user counts.
- **Exact alert-to-incident link:** needs the Netcool / ServiceNow integration to write the incident number back to the
  alert.
