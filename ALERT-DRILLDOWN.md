# Where the MIM alerts come from, and how to link to them

*4 Nov 2026. For new_suggestions2.txt: make the alerts in **Open Alerts with No Incident** and **Alerts on this CI**
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

## Ways to link an alert to its details

| Option | Opens | Needs | Works today? |
|---|---|---|---|
| **A. Kibana Discover** | Every record of the alert in Elastic (its full history: each update, clear, tally change), filtered on `netcool.identifier` | Nothing more | Yes |
| **B. Netcool Web GUI event viewer** | The live event in Netcool, with Netcool's own details and tools (journal, acknowledge, related events) | The event's **Serial** and **ServerName** (ObjectServer) in the records, and the Web GUI's address | Only if the bridge carries Serial and ServerName (check AL2) |
| **C. ServiceNow alert** | The alert in ServiceNow Event Management, if the bridge or Netcool also sends events there | A ServiceNow alert number or sys_id in the records | Only if such a field exists (check AL2) |

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
