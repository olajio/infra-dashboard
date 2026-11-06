# Infrastructure Overview: KPIs for a landing page

*6 Nov 2026. Replaces the CI-driven design of the Infrastructure Dashboard, after the team review.*

## 1. Is this common practice?

**Yes.** A top-level page that shows the state of every domain and links down to each domain's own dashboard is the
usual way to organise operations dashboards. It goes by several names: an *overview* or *landing* dashboard, a NOC
"wall" view, or "single pane of glass". The common pattern has three levels:

| Level | Question it answers | Here |
|---|---|---|
| **L0 Overview** (this page) | *Is anything wrong, and where?* In seconds, without picking anything | The renamed Infrastructure Dashboard |
| **L1 Domain** | *What is wrong in this domain?* | Server, Database, Middleware, VMware and Cloud infra dashboards |
| **L2 Detail / investigation** | *Why, on which CI, and who do I call?* | The domain dashboards' detail panels; MIM for an incident |

The practices that decide what goes on an L0 page:

- **Status first, then drill down.** Each domain gets one status that is green, amber or red, and a link. Detail
  belongs one level down.
- **No input needed.** An overview should read correctly when opened, with no control to pick. This is the main
  reason the CI-driven design did not fit: it was empty until someone picked a CI.
- **Few numbers, each actionable.** About 8–12 tiles. Every number should make someone either relax or click.
- **Resource health by the USE method** (Utilisation, Saturation, Errors) for servers, databases and clusters, and
  **demand on the operations team** from the ITIL processes: open incidents, alerts and changes.
- **Say what is not covered.** A green tile for a domain that isn't monitored is worse than a grey "not monitored"
  tile.

**Suggested name:** **Infrastructure Overview**. Alternatives: *Infrastructure Health Overview*, *Infrastructure
Home*. In Kibana the native **Links** panel suits the navigation row: it shows the target dashboards by name and can
carry the time range across.

## 2. The KPIs

**Relevance** is how much the KPI serves this page's purpose: to show at a glance where there is a problem and send
the user to the right detailed dashboard. Status and current impact score highest. Trends and management figures
score lower: they are useful, but belong in a report or a domain dashboard.

**Achievable** reflects what we found in this environment's data (Rounds 1–23):
**Yes** = the data is there and matched to the CMDB; **Partial** = only part of the domain, or it needs one
agreement or check first; **No** = the data is not collected.

### A. Status at a glance (top row)

| # | KPI | Why it matters | Relevance | Achievable | Data, and the gap |
|---|---|---|---|---|---|
| 1 | **Domain status board**: one tile per domain (Server, Database, Middleware, VMware, Cloud, Network), green / amber / red from that domain's open P1–P2 incidents and Critical alerts; each tile links to its detailed dashboard | The core of a landing page: in one look, which domain needs attention, and one click to it | **100 %** | **Partial** (5 of 6 domains) | Incidents and alerts are there for all but VMware (only 4 of 549 ESX hosts are collected). Needs the class → domain mapping (KPI 2) |
| 2 | **Active P1 / P2 incidents on infrastructure, by domain** | The direct measure of business impact on infrastructure right now | **95 %** | **Yes** | `servicenow-incidents`, domain from `ci.class_name` (e.g. *Linux Server* → Server, *IP Switch* → Network). The team must agree the class → domain table once |
| 3 | **Active infrastructure alerts, by severity and domain** | Shows problems before they become incidents; the earliest warning on the page | **90 %** | **Yes** | Elastic rules (`.alerts-observability.*`, paladin-*) and Netcool (`bridge-alerts-netcool-default`), both matched to CMDB CIs |
| 4 | **Servers not reporting** (no data for 10 min, or the host-up rule firing) | A silent server is either down or unmonitored; both need action | **90 %** | **Yes** | `metrics-system.*` heartbeat and the paladin host-uptime rule |

### B. Resource health (one tile per domain, linking down)

| # | KPI | Why it matters | Relevance | Achievable | Data, and the gap |
|---|---|---|---|---|---|
| 5 | **Servers under pressure**: count with CPU p90, memory or a disk at 90 % or more | Saturation is the most common cause of slowness and outages, and the most common reason to open the Server dashboard | **85 %** | **Yes** | `metrics-system.*` (cpu, memory, filesystem), as in today's *Server Health* |
| 6 | **Network devices and UPSs with open Critical / Major alerts** | Network faults have the widest blast radius; there is no network dashboard yet, so this tile is the only view | **80 %** | **Yes** | Netcool alerts (mostly network devices and UPSs) |
| 7 | **Databases down or degraded** | Databases sit under most applications; one down database is many incidents | **80 %** | **Partial** | SQL Server: yes, by instance (`MSSQLSERVER@host`). Oracle and Db2: collected under the collector's host name, not per server |
| 8 | **VMware: hosts or VMs down, cluster capacity** | Most servers are VMs, so a host problem is many server problems | **80 %** | **No** | vSphere collects one cluster (4 ESXi hosts, 46 VMs) of 549 ESX hosts in the CMDB. Needs the vSphere integration extended to the main vCenters. Until then the tile says "not monitored" |
| 9 | **Middleware components down** (JBoss, WebSphere, IBM MQ, IIS, Tomcat) | Middleware failures look like application outages; this points straight to the Middleware dashboard | **75 %** | **Partial** | Processes, Windows services and IBM MQ alerts are there; no common "up / down" status across products yet |
| 10 | **GKE clusters not healthy** (CPU or memory pressure, silent nodes, container restarts) | Cloud workloads change fastest; this is the Cloud dashboard's entry point | **75 %** | **Yes** (GKE) | `metrics-gcp.gke-*`, as in today's *Cloud health · GKE* (4 of 5 clusters match the CMDB). Cloud SQL: **No**, its databases are not in the CMDB |

### C. Change and demand

| # | KPI | Why it matters | Relevance | Achievable | Data, and the gap |
|---|---|---|---|---|---|
| 11 | **Changes in progress or due in the next 24 h, by domain** | Most incidents follow a change; knowing what is changing now explains many red tiles | **75 %** | **Partial** | `servicenow-change-requests` (164 a day). Check that changes scheduled in the future are sent, not only ones that have started |
| 12 | **Failed or backed-out changes, last 7 days** | A direct signal of change risk per domain | **65 %** | **Yes** | Change `close_code` |
| 13 | **Infrastructure incidents opened per day, by domain, last 30 days** | Shows whether a domain is getting better or worse | **60 %** | **Yes** | `servicenow-incidents` |
| 14 | **Mean time to resolve, by domain, last 30 days** | The usual service-quality measure for operations | **55 %** | **Partial** | Needs resolved incidents with `resolved_at` kept for 30 days; MTTR is not on MIM today for the same reason |

### D. Trust in the page

| # | KPI | Why it matters | Relevance | Achievable | Data, and the gap |
|---|---|---|---|---|---|
| 15 | **Monitoring coverage**: % of production infrastructure CIs that send data, by domain | Green only means something if the CI is monitored; shows the gaps (VMware today) | **70 %** | **Partial** | Servers and GKE: yes. Needs a CMDB inventory index by class to count the denominator (to check) |
| 16 | **Data feed freshness**: when each source last delivered (ServiceNow, Netcool, metrics, GKE, CMDB) | If a feed stops, every tile that uses it is wrong; this says so | **65 %** | **Yes** | Query IQ4b already does this (all feeds within the hour on 2 Nov) |
| 17 | **Availability %, by domain, last 30 days** | The standard summary for management | **60 %** | **Partial** | Synthetics ping monitors and the host-up rule cover only part of the estate |
| 18 | **Disks predicted full within 7 days** | Turns a future outage into a planned task | **50 %** | **Partial** | Disk usage is collected; needs a trend calculation or an ML job |
| 19 | **Noisiest CIs**: top 5 by alerts in 24 h | Finds flapping devices and bad thresholds | **45 %** | **Yes** | Netcool and Elastic alerts |
| 20 | **Infrastructure incidents breaching SLA** | Important for reporting, less for a landing page | **40 %** | **No** | The SLA feed sends very few records (33 a day): most incidents have no SLA record |

## 3. Recommendation

**Version 1 (buildable now):** KPIs **1 to 6, 10, 12, 13 and 16**. That is ten tiles, all from data we have, plus
the navigation row (the seven links already on the dashboard).

**Shown as "partial" or "not monitored":** 7 Database (SQL Server only), 9 Middleware, 8 VMware (grey "not
monitored" tile linking to the VMware dashboard), 11 Changes due (once future changes are confirmed in the feed).

**Later, or in a report:** 14, 15, 17, 18, 19, 20.

**What leaves this page:** the CI control and the per-CI tables (incidents, changes and alerts on a CI, server
health). Investigating one CI is MIM's job; the overview links to MIM instead.

**Decisions needed from the team:**
1. The name (*Infrastructure Overview* suggested).
2. The `ci.class_name` → domain table (the list of classes per domain).
3. Thresholds for amber and red per domain (suggested: red = any open P1 or Critical alert; amber = P2 or Major
   alert, or a resource at 90 %).
4. Whether a Network domain dashboard is planned (KPI 6 is the only network view today).
