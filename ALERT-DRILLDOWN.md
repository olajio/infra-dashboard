# Where the MIM alerts come from, and how to link to them

*4 Nov 2026, Round 23 results added 5 Nov. For new_suggestions2.txt: make the alerts in **Open Alerts with No Incident** and **Alerts on this CI**
clickable, to drill into an alert's details. This page explains the source first, as asked. Nothing is built yet.*

## The source

Both tables read the same Elasticsearch data stream: **`bridge-alerts-netcool-default`** (indices
`.ds-bridge-alerts-netcool-default-*`). It is filled by a **bridge from IBM Netcool/OMNIbus**, the event manager that
collects device and infrastructure events (ping failures, UPS faults, link down …). Every time Netcool inserts,
updates or clears an event, the bridge writes **one record**. Before indexing, an ingest step adds the CMDB CI the
event's node belongs to (`ci.*`).

| Field the dashboard uses | Netcool meaning |
|---|---|
| `netcool.identifier` | Netcool's **Identifier**: the event's de-duplication key, the same for every record of one alert. The tables group on it: one row per alert |
| `node` | The Netcool **Node** (the device's host name, often `<name>.cna.com`) |
| `severity` | Netcool severity: 5 Critical, 4 Major, 3 Minor, 2 Warning, 1 Indeterminate, 0 Clear |
| `message` | The alert text (Netcool **Summary**) |
| `first_occurrence`, `last_occurrence` | Netcool **FirstOccurrence** / **LastOccurrence** |
| `netcool.tally` | Netcool **Tally**: how many times the event has fired (the tables' *Times fired*) |
| `netcool.type_name` | Netcool **Type**: problem, resolution … (a resolution or severity 0 closes the alert) |
| `netcool.acknowledged_name` | Netcool **Acknowledged** |
| `ci.name`, `ci.class_name`, `ci.environment`, `ci.support_group.l2.name` | Added in Elastic from the CMDB, by node |

**The two tables** read the same records differently:
- **Alerts on this CI:** alerts on the selected CI (by CMDB CI, or node `<CI>.cna.com`), last 7 days, open or cleared.
- **Open Alerts with No Incident:** alerts still open in the last 24 h on CIs with no open incident. Since today,
  with an incident or CI picked, only the CI's alerts and its CMDB-linked CIs'.

## Round 23 results (5 Nov, `round23.txt`)

| Check | Found | So |
|---|---|---|
| **AL1** full records | The bridge is **Node-RED** (`agent.name: node-red-netcool`, `agent.type: netcool.alerts`). Each record carries `netcool.identifier`, `netcool.serial` (e.g. 2543984), `netcool.server_serial` (1999229), `netcool.manager` ("MTTrapd Probe"), `alert.id`, `alert.lifecycle_id`, `alert.correlation_key`, `alert.node`, `alert.alert_key`, `alert.alert_group`; `node` is an IP (e.g. 10.2.71.14), with `node_alias`. The CI comes from an enrich policy matching **by IP** (`enrich_policy.bridge_alerts.match: by_ip`) and adds `ci.sys_id`, `ci.name`, `ci.fqdn`, `ci.class`, `ci.is_monitored` | Each alert has stable keys for a link |
| **AL2** external references | **No ServerName** (ObjectServer name) field, and **no ServiceNow alert number or sys_id**. The wildcard field list was too broad to run; AL1 shows every field | B needs one fact from the Netcool team; C is not possible |
| **AL3** how it is filled | Data stream from the `bridge-alerts-netcool` template (package "bridge", ILM `bridge_3months`: 3 months kept). No ingest pipeline named `*netcool*`: the enrichment runs in the bridge's own pipeline | Nothing to change in Elastic |
| **AL4** records per alert | Up to about **927 records a day** for one alert (every Netcool update is a record) | A link must filter on the alert's key, not show raw records |

### What this means for each option

- **A. Kibana Discover: works now.** The tables already use URL drill-downs (the incident links). A click on an alert
  would open Discover on `bridge-alerts-netcool-default`, filtered on that `netcool.identifier`, last 7 days, newest
  first, with the useful columns (severity, type, tally, acknowledged, message). Nothing else is needed.
- **B. Netcool Web GUI: possible, with one answer from the Netcool team.** The records carry `netcool.serial` and
  `netcool.server_serial`, but not the ObjectServer name. Ask them for (1) the Web GUI address, (2) the ObjectServer
  name these events come from (one name for all is enough), and (3) whether an event can be opened by Serial in a URL.
- **C. ServiceNow alert: not possible.** Nothing in the records points to a ServiceNow alert. What is possible instead:
  a link from the alert's CI to its **CMDB record** in ServiceNow, using `ci.sys_id` (the same way the incident tables
  link to ServiceNow).

**Recommendation:** build **A** now (click the alert → its history in Discover), add a **CI → ServiceNow CMDB** link
on `ci.sys_id`, and add **B** once the Netcool team answers. Waiting for your go-ahead before building.

## Ways to link an alert to its details

| Option | Opens | Needs | Works today? |
|---|---|---|---|
| **A. Kibana Discover** | Every record of the alert in Elastic (its full history: each update, clear, tally change), filtered on `netcool.identifier` | Nothing more | Yes |
| **B. Netcool Web GUI event viewer** | The live event in Netcool, with Netcool's own details and tools (journal, acknowledge, related events) | The event's **Serial** and **ServerName** (ObjectServer) in the records, and the Web GUI's address | Serial yes; ServerName missing: ask the Netcool team (Round 23) |
| **C. ServiceNow alert** | The alert in ServiceNow Event Management, if the bridge or Netcool also sends events there | A ServiceNow alert number or sys_id in the records | No: no such field (Round 23) |

**My recommendation:** start with **A**. It works with what is in Elastic now, and it shows the whole life of the
alert. Add **B** if the queries show Serial and ServerName and the team has Netcool Web GUI access, because Netcool's
event viewer is where operators act on an alert.

## Queries to settle it (Round 23, Dev Tools)

Paste the answers into `round23.txt`.

**AL1. Two recent records in full: every field the bridge sends**

```
GET .ds-bridge-alerts-netcool-default-*/_search?size=2&sort=@timestamp:desc
```

**AL2. Fields that could identify the alert outside Elastic** (Serial, ServerName, a URL, a ServiceNow reference)

```
GET .ds-bridge-alerts-netcool-default-*/_field_caps?fields=*serial*,*Serial*,*server*,*Server*,*url*,*link*,*sys_id*,*sn_*,*servicenow*,netcool.*&filter_path=fields.*.*.type
```

**AL3. How the data stream is filled** (index template, ingest pipeline and enrichment)

```
GET _data_stream/bridge-alerts-netcool-default

GET _ingest/pipeline/*netcool*?filter_path=*.description,*.processors.*.tag,*.processors.*.description
```

**AL4. Records per alert** (the record model: how many updates one alert produces)

```
POST /_query?format=txt
{
  "query": """
FROM .ds-bridge-alerts-netcool-default-*
| WHERE @timestamp >= NOW() - 1 day
| STATS records = COUNT(*), first_record = MIN(@timestamp), last_record = MAX(@timestamp), nodes = COUNT_DISTINCT(node)
  BY netcool.identifier
| SORT records DESC
| LIMIT 10
"""
}
```

Also worth asking the Netcool team: the Netcool Web GUI address, and whether operators can open an event by its
Serial in a URL.
