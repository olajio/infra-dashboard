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

---

## Round 17 results (2 Nov 2026)

| Query | Result | Meaning |
|---|---|---|
| IQ1a, IQ2a | Failed: `Unknown column [ci.name]` | vSphere and GCP data carry no CMDB enrichment. Re-run as IQ5a / IQ5b below |
| IQ1b | One collector (`vslrau1p302`) reports on one VMware Cloud Foundation cluster (`bly1-vcf-m1c1`, Blythewood): VM name in `vsphere.virtualmachine.name`, host in `vsphere.host.name` (FQDN, e.g. `vxbly1h003.cna.com`), status green / yellow / red, CPU, memory, datastore usage | The fields needed for VMware health exist |
| IQ1c | 46 VMs in vSphere (last hour), 2,740 servers sending OS metrics, **1** name in both | VM names don't match the monitored servers |
| IQ1d | 549 ESX hosts in the CMDB, **4** in vSphere, 0 matching | Only one small cluster is collected; most of the VMware estate isn't |
| IQ2b | Not run (needs the data set names from IQ2a) | Re-run after IQ5b |
| IQ2c (`round17_IQ2c.csv`) | Cloud CIs in CMDB relations: 13,762 Kubernetes replica sets, 7,010 namespaces, 2,519 cloud service accounts, 448 Kubernetes clusters, 270 Google data centres, 123 GCP projects, 27 cloud load balancers, 10 cloud databases … | Cloud resources are in the CMDB, so a CI link may be possible |
| IQ2d | No AWS or Azure indices | GCP only |
| IQ3a | Observability alert indices in use: metrics, custom threshold, APM, logs, SLO, uptime, ML anomaly | Elastic alerting is active |
| IQ3b | Only rule ids came back (883 rules): the `fields=` filter stripped the rest | Re-run as IQ5c below |
| IQ3c | 9,415 alerts in 7 days (692 active): custom threshold 4,265, synthetics 2,726, APM anomaly 1,372, metric threshold 647, SLO 321 … Infrastructure rules **paladin-***: host uptime, filesystem usage, CPU / memory (ML), middleware and Linux processes, Windows services, IBM MQ channel status, data outages, Windows event ids. `ci.name` on **0** alerts, `host.name` on only **4** hosts | Infra alerts exist; the server must be found in another field (IQ5d) |
| IQ4a | 36 Fleet integrations; custom ones: Custom Logs (filestream, log), httpjson, Custom Google Pub/Sub | |
| IQ4b | All feeds delivered within the last hour (2 Nov 11:27–11:28): Paladin alerts 216,708 in 24 h, ServiceNow incident snapshots 617,985, CMDB relations 64,810, Netcool bridge 6,266, ServiceNow incidents 270, changes 164, **SLA 33** | Feed freshness can be shown as a panel; the SLA feed's low volume matches the SLA gap (`sla_email.md`) |

## IQ5. Follow-ups (Round 17b)

Paste the answers into `round17b.txt`. If one fails in Dev Tools, run the ES|QL in Discover and save the CSV as
`round17b_IQ5x.csv`.

**IQ5a. IQ1a without the CMDB field**

```
POST /_query?format=txt
{
  "query": """
FROM metrics-vsphere.*
| WHERE @timestamp >= NOW() - 1 hour
| STATS docs = COUNT(*), last_seen = MAX(@timestamp) BY data_stream.dataset
| SORT data_stream.dataset
"""
}
```

**IQ5b. IQ2a without the CMDB field** — then run IQ2b once for each data set it lists (`gcp.gke` → `metrics-gcp.gke-*`)

```
POST /_query?format=txt
{
  "query": """
FROM metrics-gcp.*
| WHERE @timestamp >= NOW() - 1 hour
| STATS docs = COUNT(*), last_seen = MAX(@timestamp) BY data_stream.dataset
| SORT data_stream.dataset
"""
}
```

**IQ5c. The paladin rules, in full** (IQ3b without the field filter, limited to the infrastructure rules)

```
GET kbn:/api/alerting/rules/_find?per_page=100&search_fields=name&search=paladin*
```

**IQ5d. Where the server name is in the infrastructure alerts** — the group-by values and instance ids per paladin
rule, then one full alert from the host uptime rule

```
GET .alerts-observability.*/_search
{
  "size": 0,
  "query": { "bool": { "filter": [
    { "range": { "@timestamp": { "gte": "now-7d" } } },
    { "prefix": { "kibana.alert.rule.name": "paladin" } } ] } },
  "aggs": { "by_rule": { "terms": { "field": "kibana.alert.rule.name", "size": 30 }, "aggs": {
    "group_fields": { "terms": { "field": "kibana.alert.group.field", "size": 5 } },
    "group_values": { "terms": { "field": "kibana.alert.group.value", "size": 3 } },
    "instances": { "terms": { "field": "kibana.alert.instance.id", "size": 3 } } } } }
}

GET .alerts-observability.*/_search?size=1&sort=@timestamp:desc&q=kibana.alert.rule.name:"paladin-host-uptime-c30"
```

### Round 17b results (2 Nov 2026)

| Query | Result | Meaning |
|---|---|---|
| IQ5a | vSphere data sets: cluster, datastore, host, network, resource pool, virtual machine (8,280 VM records an hour) | All from the one VCF cluster seen in IQ1b |
| IQ5b | GCP data sets: `gcp.cloudsql_postgresql`, `gcp.compute` (60,167 / hour), `gcp.gke` (5.4 M / hour), `gcp.storage` | Next: IQ2b for each, to see the resource fields (Round 17c) |
| IQ5c | 0 rules found | The paladin rules live in the Kibana space `bridge-p` (IQ5d); Dev Tools searched the default space |
| IQ5d | 3,455 paladin alerts in 7 days, 27 rules. The server is in `kibana.alert.group` (`ci.name_normalized` / `ci_name`) and inside `kibana.alert.instance.id`: `<ci sys_id>,<server>,…` for the threshold rules, `<sys_id>#<server>#…` for the ML rules, the host name alone for one rule | **Elastic infra alerts can be matched to a CI** |

**Built (2 Nov):** the *Elastic infra alerts* placeholder on the Infrastructure Dashboard is now a real panel: Elastic
Observability alerts on the selected CI (matched on the CI name inside `kibana.alert.instance.id`), last 7 days, active
first; with no CI picked, every active paladin-* alert with its server.

**IQ2b for each GCP data set (Round 17c)** — paste into `round17c.txt`:

```
GET metrics-gcp.compute-*/_search?size=1&sort=@timestamp:desc
GET metrics-gcp.gke-*/_search?size=1&sort=@timestamp:desc
GET metrics-gcp.storage-*/_search?size=1&sort=@timestamp:desc
GET metrics-gcp.cloudsql_postgresql-*/_search?size=1&sort=@timestamp:desc
```

### Round 17c results (2 Nov 2026)

| Data set | Resource fields | Metrics in the sample |
|---|---|---|
| `gcp.compute` | `cloud.account.id` (project), `cloud.instance.name` (here a GKE node VM), `cloud.machine.type`, `gcp.labels.user.goog-k8s-cluster-name` | network egress / ingress bytes and packets |
| `gcp.gke` | `gcp.labels.resource.cluster_name`, `gcp.labels.resource.node_name`, `cloud.account.id` | node CPU / memory capacity (allocatable, total) |
| `gcp.storage` | `gcp.labels.resource.bucket_name`, `gcp.labels.metrics.response_code` | API request count, bytes sent / received |
| `gcp.cloudsql_postgresql` | `gcp.labels.resource.database_id` (`project:instance`), `gcp.labels.metrics.state` | `database.instance_state`, state (RUNNING / SUSPENDED …) |

The samples come from two projects only (`cna-g-prod-proj-elm-bridge`, `cna-g-prod-proj-spg`), against 123 GCP projects in
the CMDB. Before building Cloud health: how much of GCP is collected, and do its names match the CMDB's cloud CIs?

## Round 17d — GCP coverage and its match to the CMDB

Paste into `round17d.txt`. CG2 and CG3 can return a few hundred rows: run them in **Discover** (ES|QL mode) and save
the CSVs as `round17d_CG2.csv` and `round17d_CG3.csv` (CG3 reads the CMDB relations, which timed out in Dev Tools in
Round 17).

**CG1. How much of GCP is collected (last hour)**

```
POST /_query?format=txt
{
  "query": """
FROM metrics-gcp.*
| WHERE @timestamp >= NOW() - 1 hour
| STATS projects = COUNT_DISTINCT(cloud.account.id), clusters = COUNT_DISTINCT(gcp.labels.resource.cluster_name),
        databases = COUNT_DISTINCT(gcp.labels.resource.database_id), buckets = COUNT_DISTINCT(gcp.labels.resource.bucket_name),
        vms = COUNT_DISTINCT(cloud.instance.name)
  BY data_stream.dataset
"""
}
```

**CG2. Every collected project and resource** (Discover → CSV)

```
FROM metrics-gcp.*
| WHERE @timestamp >= NOW() - 1 hour
| EVAL resource = CASE(data_stream.dataset == "gcp.gke", TO_STRING(gcp.labels.resource.cluster_name),
                       data_stream.dataset == "gcp.cloudsql_postgresql", TO_STRING(gcp.labels.resource.database_id),
                       data_stream.dataset == "gcp.storage", TO_STRING(gcp.labels.resource.bucket_name),
                       COALESCE(TO_STRING(`gcp.labels.user.goog-k8s-cluster-name`), TO_STRING(cloud.instance.name)))
| STATS docs = COUNT(*) BY data_stream.dataset, project = cloud.account.id, resource
| SORT data_stream.dataset, project, resource
| LIMIT 2000
```

**CG3. The cloud CIs in the CMDB, by class and name** (Discover → CSV)

```
FROM cmdb-ci-relations*
| EVAL p = parent.class IN ("cmdb_ci_gcp_project", "cmdb_ci_kubernetes_cluster", "cmdb_ci_cloud_database", "cmdb_ci_cloud_object_storage")
| EVAL cls = CASE(p, parent.class, child.class), name = CASE(p, parent.name, child.name)
| WHERE cls IN ("cmdb_ci_gcp_project", "cmdb_ci_kubernetes_cluster", "cmdb_ci_cloud_database", "cmdb_ci_cloud_object_storage")
| STATS relations = COUNT(*) BY cls, name
| SORT cls, name
| LIMIT 2000
```

**CG4. Every GCP metric collected, by data set** (the sample documents showed only some of them)

```
GET metrics-gcp.*/_field_caps?fields=gcp.gke.*,gcp.compute.*,gcp.storage.*,gcp.cloudsql_postgresql.*&filter_path=fields.*.*.type
```

### Round 17d results (2 Nov)

**CG1 — what is collected (last hour)**

| Data set | Projects | Resources |
|---|---|---|
| gcp.compute | 7 | 271 VMs |
| gcp.storage | 7 | 18 buckets |
| gcp.gke | 4 | 5 clusters |
| gcp.cloudsql_postgresql | 2 | 6 databases |

**CG4: health signals available per data set**

| Data set | Fields | Fields that can drive a health colour |
|---|---|---|
| Cloud SQL (46) | `database.instance_state`, `cpu.utilization.pct`, `memory.utilization.pct`, `disk.utilization.pct`, `network.connections.count`, `replication.replica_lag.sec`, `auto_failover_request.count` | instance_state (down = red), CPU/memory/disk % (same 80/90 thresholds as Database Health), replica lag |
| GKE (40) | `node.cpu.allocatable_utilization.pct`, `node.memory.allocatable_utilization.pct`, `container.restart.count`, `container.cpu/memory.limit_utilization.pct`, `pod.volume.utilization.pct`, `node.pid_used/pid_limit` | node CPU/memory %, container restarts, volumes near full |
| Compute (19) | `instance.cpu.usage.pct`, `instance.uptime.sec`, disk/network bytes, `firewall.dropped_packets_count` | CPU %, uptime reset (reboot); no memory % without the Ops agent (only balloon fields) |
| Storage (9) | `api.request.count`, `storage.object.count`, `storage.total.bytes`, network bytes | No health signal beyond request volume. Error ratio needs `api.request.count` split by response code, which is not in the field list. |

**CG2 and CG3: do the collected GCP resources match CMDB names?**

| GCP resource | Collected (CG2) | In the CMDB (CG3) | Match |
|---|---|---|---|
| GKE clusters | g-prd-gke-2, g-pre-gke-4, g-pre-gke-5, g-stg-gke-2, g-prod-gke-elm-bridge | 34 `cmdb_ci_kubernetes_cluster` names | **4 of 5** (all but g-pre-gke-4). g-prd-gke-2 has 189 CMDB relations |
| Projects | 9 (anomalo, spg, looker cut/stg/prd, gke-prod, gke-preprod, gke-stg, elm-bridge) | 21 `cmdb_ci_gcp_project` names | **3 of 9**: cna-g-prd-proj-gke-prod, cna-g-pre-proj-gke-preprod, cna-g-prod-proj-elm-bridge |
| Cloud SQL | 6 (anomalo and spg instances; the resource is `project:instance`) | 8 `cmdb_ci_cloud_database` names (abp, bandc, clmfi, cnax, mvr …) | **None**. Different databases on each side |
| Buckets | 18 (looker, elm-bridge, cloudbuild) | 15 `cmdb_ci_cloud_object_storage` names | **None** |
| Compute VMs | Mostly GKE nodes and Looker VMs | Not in CG3 (server classes) | Not checked |

**Conclusion (Cloud health: Partly achievable).** GKE health can follow the CI: when the selected CI is a Kubernetes
cluster, or one of its relations is, match `gcp.labels.resource.cluster_name` to
the CMDB name. Show node CPU and memory %, container restarts and volumes near full. Cloud SQL cannot follow a CI until one
of two things happens: the collected anomalo and spg instances are added to the CMDB, or the CMDB's databases are
added to the GCP integration. Buckets carry no health signal. `INFRA-DASHBOARD-KPIS.xlsx` is updated.
