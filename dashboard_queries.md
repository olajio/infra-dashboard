# Infrastructure Dashboard — queries to run (28 Oct 2026)

These settle the KPIs from `dashboard_kpis.txt` that are **placeholders** on the new *Infrastructure Dashboard*
(`Infrastructure Dashboard.ndjson`): **VMware health**, **Cloud health**, **Elastic Infra Alerts** and **Custom
Integration health**. Everything else on the dashboard already works from data we know exists (see
`INFRA-DASHBOARD-KPIS.xlsx`).

All are read-only. Run them in **Dev Tools Console** and paste every answer into `round17.txt`, with the query name
(IQ1a, IQ1b …) above it. Each one is limited to recent data so it answers quickly; none of them searches every
index (that's what timed out with a 502 in Round 16).

If a query fails with `Unknown column [...]`, the field has a different name on the cluster: paste the error anyway,
the sample document from the same group (IQ1b / IQ2b) shows the real name.

---

## IQ1. VMware health

vSphere is collected (`metrics-vsphere.*`, 7 data streams), but under the collector's `host.name`. To show a CI's
VMware health we need (1) the VM and ESXi host names in the vSphere data and (2) a way from the CI to them: either
the VM name is the server's name, or the CMDB link *server → ESX host* (`cmdb_ci_esx_server`).

**IQ1a. What vSphere data arrives, and how fresh**

```
POST /_query?format=txt
{
  "query": """
FROM metrics-vsphere.*
| WHERE @timestamp >= NOW() - 1 hour
| STATS docs = COUNT(*), last_seen = MAX(@timestamp), with_ci_name = COUNT(ci.name) BY data_stream.dataset
| SORT data_stream.dataset
"""
}
```

**IQ1b. One sample document per vSphere data set** (shows the real field names: VM name, host name, status, CPU,
memory, datastore usage)

```
GET metrics-vsphere.virtualmachine-*/_search?size=1&sort=@timestamp:desc
GET metrics-vsphere.host-*/_search?size=1&sort=@timestamp:desc
GET metrics-vsphere.datastore-*/_search?size=1&sort=@timestamp:desc
```

**IQ1c. Do VM names match the servers that send OS metrics?** (field names from the Elastic vSphere integration;
fix them from IQ1b if they differ)

```
POST /_query?format=txt
{
  "query": """
FROM metrics-vsphere.virtualmachine-*, .ds-metrics-system.cpu-default* METADATA _index
| WHERE @timestamp >= NOW() - 1 hour
| EVAL vm = _index LIKE "*vsphere*"
| EVAL name = TO_LOWER(CASE(vm, TO_STRING(vsphere.virtualmachine.name), TO_STRING(host.name)))
| STATS in_vsphere = MAX(CASE(vm, 1, 0)), sends_os_metrics = MAX(CASE(vm, 0, 1)) BY name
| STATS vms = SUM(in_vsphere), servers = SUM(sends_os_metrics), both = SUM(in_vsphere * sends_os_metrics)
"""
}
```

**IQ1d. Do the ESX hosts named in the CMDB appear in the vSphere host data?**

```
POST /_query?format=txt
{
  "query": """
FROM cmdb-ci-relations*, metrics-vsphere.host-* METADATA _index
| WHERE (_index LIKE "*relations*" AND child.class == "cmdb_ci_esx_server") OR (_index LIKE "*vsphere*" AND @timestamp >= NOW() - 1 hour)
| EVAL rel = _index LIKE "*relations*"
| EVAL esx = TO_LOWER(CASE(rel, TO_STRING(child.name), TO_STRING(vsphere.host.name)))
| STATS in_cmdb = MAX(CASE(rel, 1, 0)), in_vsphere = MAX(CASE(rel, 0, 1)), servers_on_it = COUNT_DISTINCT(parent.name) BY esx
| STATS esx_hosts_in_cmdb = SUM(in_cmdb), in_vsphere = SUM(in_vsphere), both = SUM(in_cmdb * in_vsphere), servers_linked = SUM(servers_on_it)
"""
}
```

## IQ2. Cloud health

GCP is collected (`metrics-gcp.*`, 4 data streams, ~200 M documents, including CloudSQL and GKE). We need the data
sets, each one's resource identifier, and whether anything links them to CMDB CIs (`ci.*` enrichment, or CMDB
classes such as `cmdb_ci_cloud_database`, `cmdb_ci_google_datacenter`, `cmdb_ci_kubernetes_cluster`). IQ2d checks for
other clouds.

**IQ2a. GCP data sets, freshness and CI enrichment**

```
POST /_query?format=txt
{
  "query": """
FROM metrics-gcp.*
| WHERE @timestamp >= NOW() - 1 hour
| STATS docs = COUNT(*), last_seen = MAX(@timestamp), with_ci_name = COUNT(ci.name) BY data_stream.dataset
| SORT data_stream.dataset
"""
}
```

**IQ2b. One sample document per GCP data set** — replace `<dataset>` with each name from IQ2a, written with a dash
(e.g. `gcp.gke` → `metrics-gcp.gke-*`)

```
GET metrics-<dataset>-*/_search?size=1&sort=@timestamp:desc
```

**IQ2c. Cloud CIs in the CMDB**

```
POST /_query?format=txt
{
  "query": """
FROM cmdb-ci-relations*
| EVAL cls = CASE(parent.class LIKE "*cloud*" OR parent.class LIKE "*google*" OR parent.class LIKE "*gcp*" OR parent.class LIKE "*kubernetes*", parent.class,
                  child.class LIKE "*cloud*" OR child.class LIKE "*google*" OR child.class LIKE "*gcp*" OR child.class LIKE "*kubernetes*", child.class)
| WHERE cls IS NOT NULL
| STATS relations = COUNT(*) BY cls
| SORT relations DESC
"""
}
```

**IQ2d. Any AWS or Azure data**

```
GET _cat/indices/*aws*,*azure*?v&h=index,docs.count&s=index&expand_wildcards=all
```

## IQ3. Elastic Infra Alerts

The new dashboard shows Netcool alerts on the CI. "Elastic Infra Alerts" means alerts raised by **Elastic's own
alerting rules** (Observability: inventory / metric threshold / custom threshold / log threshold rules). These
check whether such rules and alerts exist, and whether the alerts name a host or CI we can filter on.

**IQ3a. Alert indices and their size**

```
GET _cat/indices/.internal.alerts-*?v&h=index,docs.count&s=index&expand_wildcards=all
```

**IQ3b. The rules defined in Kibana** (Dev Tools sends `kbn:` requests to Kibana)

```
GET kbn:/api/alerting/rules/_find?per_page=100&fields=name,rule_type_id,enabled,tags
```

**IQ3c. Alerts in the last 7 days: by rule type, rule and status, and whether they carry a host or CI**

```
GET .alerts-observability.*/_search
{
  "size": 0,
  "query": { "range": { "@timestamp": { "gte": "now-7d" } } },
  "aggs": {
    "rule_types": { "terms": { "field": "kibana.alert.rule.rule_type_id", "size": 30 } },
    "rules": { "terms": { "field": "kibana.alert.rule.name", "size": 30 } },
    "status": { "terms": { "field": "kibana.alert.status", "size": 5 } },
    "hosts": { "cardinality": { "field": "host.name" } },
    "with_ci_name": { "value_count": { "field": "ci.name" } }
  }
}
```

**IQ3d. One recent alert, to see its fields**

```
GET .alerts-observability.*/_search?size=1&sort=@timestamp:desc
```

## IQ4. Custom integration health

"Custom integration" needs a definition from you. Two readings are possible: (a) the **custom data feeds** built for
this estate (ServiceNow incidents / SLA / changes / CMDB relations, the Netcool bridge, Paladin alerts), or (b)
**custom integrations installed in Fleet**. IQ4a answers (b); IQ4b shows how fresh each feed in (a) is.

**IQ4a. Integrations installed in Fleet (custom ones included)**

```
GET kbn:/api/fleet/epm/packages/installed?perPage=200
```

**IQ4b. When each custom feed last delivered data**

`@timestamp` on ServiceNow incidents is the incident's opened time (Round 16), and CMDB relation records are only
written when a relation changes, so for those two the "last" time is a lower bound, not the sync time.

```
POST /_query?format=txt
{
  "query": """
FROM servicenow-incidents-*, servicenow-task-sla-*, servicenow-change-requests-*, servicenow-open-incidents-snapshots-*, .ds-bridge-alerts-netcool-*, cmdb-ci-relations*, paladin-alerts-* METADATA _index
| WHERE @timestamp >= NOW() - 7 days
| EVAL feed = CASE(_index LIKE "*task-sla*", "ServiceNow SLA", _index LIKE "*open-incidents-snapshots*", "ServiceNow incident snapshots",
                   _index LIKE "*servicenow-incidents*", "ServiceNow incidents", _index LIKE "*change-requests*", "ServiceNow changes",
                   _index LIKE "*netcool*", "Netcool bridge", _index LIKE "*relations*", "CMDB relations", _index LIKE "*paladin*", "Paladin alerts", _index)
| STATS last_data = MAX(@timestamp), docs_last_24h = SUM(CASE(@timestamp >= NOW() - 24 hours, 1, 0)), docs_last_7d = COUNT(*) BY feed
| SORT feed
"""
}
```

---

## What each answer decides

| If … | Then |
|---|---|
| IQ1a has VM / host data and IQ1c or IQ1d shows a match | **VMware health** can be built for the selected CI: its own VM (by name) or its ESX host (by CMDB link) with status, CPU, memory and datastore usage |
| IQ1 has data but no match | VMware health as an estate view only (hosts / VMs with problems), not per CI |
| IQ2a/IQ2b show resource IDs and IQ2a or IQ2c gives a link to CIs | **Cloud health** per CI (e.g. a CloudSQL instance or GKE cluster in the CMDB) |
| IQ2 has no link to CIs | Cloud health as an estate view per GCP resource, plus the link to the CloudSQL dashboard |
| IQ3a/IQ3b show Observability rules and IQ3c alerts with `host.name` | **Elastic Infra Alerts** for the CI's servers |
| IQ3 shows no Observability rules | The KPI needs alerting rules created first (an Elastic configuration task, not a dashboard one) |
| You confirm which feeds count, and IQ4b shows them | **Custom integration health**: one row per feed, red when it hasn't delivered within an agreed time |
