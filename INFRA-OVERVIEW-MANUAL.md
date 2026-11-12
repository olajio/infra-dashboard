# Infrastructure Overview: user manual

*10 Nov 2026, updated 11 Nov · Kibana 9.5.3 · dashboard "Infrastructure Overview" (replaces the CI-driven "Infrastructure Dashboard",
same id, so its links and bookmarks still work). Design: `INFRA-OVERVIEW-KPIS.md`, `previews/INFRA-OVERVIEW-WALKTHROUGH.md`.*

## What it is for

The landing page of the infrastructure dashboards. It answers *"is anything wrong, and where?"* in a few seconds, and
sends you to the right detailed dashboard. **There is nothing to pick:** every panel reads correctly when the page
opens. Investigating one CI or one incident is done in MIM.

**Import:** import `Infrastructure Overview.ndjson` with **Automatically overwrite conflicts**, in the same space as
the old Infrastructure Dashboard, then **More (⋯) → Reset changes**. It refreshes itself every 5 minutes. The time
picker changes nothing: each panel has its own window, shown on its badge.

## The page

### 🧭 1 · Infrastructure status

| Panel | Shows |
|---|---|
| **Domain status** | One tile per domain: Server, Database, Middleware, VMware, Cloud, Network. **Red (Action):** an open P1, a Critical alert, a server not reporting or a GKE cluster critical / silent. **Amber (Attention):** an active P2, a Major alert, a server at 90 % CPU, memory or disk, or a GKE cluster warning. **Green (Healthy):** none of these. **Grey (Not monitored):** VMware with nothing open. Under each status: open P1 / P2, Critical / Major alerts and the domain's own facts |
| **VMware tile** (since 12 Nov) | From the vSphere integration (the same data as the VMware Infra Dashboard), last hour: hosts, VMs (red ones), datastores at 80 % or more, and the hosts' peak CPU, memory and disk latency. **Red:** a host silent 15 min, host CPU ≥ 90 %, memory ≥ 95 % or disk latency ≥ 25 ms, a datastore ≥ 90 %, or a red VM. **Amber:** host CPU ≥ 75 %, memory ≥ 85 % or latency ≥ 10 ms, a datastore ≥ 80 %, or a yellow VM (thresholds from `vmware_data.xlsx`). Plus incidents and alerts on VMware CIs, as for every domain. **Grey** only when vSphere sends nothing. Tagged *partial*: vSphere covers only part of the estate (4 of 549 ESX hosts on 2 Nov) |
| **Links under the tiles** | Each domain's detailed dashboard. Network has none yet: its alerts are in section 2 |
| **Active P1 (infrastructure)** | Open P1 incidents on infrastructure CIs (not application services). Green at 0 |
| **P2 over 8 h (infrastructure)** | Active P2 incidents open longer than 8 h, MIM's target |
| **Critical alerts** | Open Critical alerts (Netcool and Elastic), with the Major count |
| **Servers not reporting** | Production servers with metrics in the last day but none in the last 10 minutes, out of all reporting |
| **Servers under pressure** | Reporting servers at 90 % or more CPU (p90), memory or disk in the last hour, with how many because of a disk |
| **Failed changes (7 days)** | Changes that ended in the last 7 days unsuccessful, failed or backed out, out of all that ended |

### 🚨 2 · What needs attention now

| Panel | Shows |
|---|---|
| **Active P1 · P2 over 8 h on infrastructure** | The incidents behind the tiles, with their domain. Click the incident or the CI to open it in ServiceNow; a third action opens MIM (pick the CI there) |
| **Open infrastructure alerts by domain** | A bar per domain, by severity |
| **Top open alerts** | Every open alert, Critical first, oldest first: domain, CI, alert, source (Netcool or Elastic), how long open |

### 🔄 3 · Changes and trend

| Panel | Shows |
|---|---|
| **Change Request Summary** | Four cards, as on Portfolio v4: **Open changes** (not Closed or Canceled) with N / S / E = normal, standard, emergency; **Implemented this week** (Closed, not canceled, in the last 7 days) with the change against the week before; **Pending approval** (Assess or Authorize: action required); **Scheduled next 7 days** (Scheduled, starting within 7 days) |
| **Change requests** | The changes behind the cards, beside it: In progress first, then Pending approval, Scheduled (7 d), other Open, and Implemented this week, with type, state, domain, CI, planned start and end, assignment group |
| **Infrastructure incidents per day** | Incidents of every priority opened per day in the last 30 days, by domain |

Both change panels count **each change once** (its latest record, updated in the last 30 days), on infrastructure CIs
or with no CI class (most changes have none: IO2). Portfolio v4 counts records, so its numbers are higher for the
same changes.

### 🔗 4 · Detailed dashboards

Two lists side by side:

| Left: technology dashboards | Right: related dashboards |
|---|---|
| 🖥️ Server Infra Dashboard | 🩺 Applications Operations Dashboard |
| 🗄️ Database Infra Dashboard | 🧱 VMware Infra Dashboard |
| ⚙️ Middleware Dashboard | 💼 Portfolio Dashboard |
| ☁️ Cloud Infra Dashboard | 🚨 MIM Dashboard |

Each opens in a new tab. The Portfolio link uses the Portfolio v4 dashboard's id (no short link was given). Below
the lists, **Data freshness**: when each source last delivered (green ≤ 30 min, amber ≤ 2 h, red older). If a source
is red, the panels that read it are out of date.

## How to use it

1. **Scan the domain tiles.** All green: check *Data freshness* and *Changes*, then done.
2. **A red or amber tile:** read its facts. An open P1 / P2? It is an incident: find it in section 2 and run it in
   **MIM**. Otherwise open the domain's dashboard from the link under the tile and find the CI.
3. **Network:** no dashboard yet: use *Top open alerts*, then MIM for the device.
4. Come back: the tile turns green once its alerts clear and its incidents close.

## How a CI gets its domain

From the CMDB class of the incident's, change's or alert's CI (both forms, e.g. *Linux Server* and
`cmdb_ci_linux_server`):

Checked on 11 Nov against every class in production (IO1, `io.txt`):

| Domain | Classes in production (IO1) | Rule: class contains |
|---|---|---|
| **Network** | IP Switch, UPS, Wireless Access Point, Network Appliance Hardware, Network Gear, IP Firewall, DNS Name, IP Router, F5 BIG-IP, Palo Alto Firewall Device, Storage Switch, Communication Device | switch, router, ups, firewall, load bal, network, wireless, access point, ip, big-ip, f5, dns, communication, pdu |
| **Server** | Linux Server, Windows Server, AIX Server, HPUX Server, Mainframe LPAR, IBM LPAR Instance, Hardware, Computer, Storage Server, Server, UNIX Cluster (Node), Windows Cluster Node | server, linux, windows, aix, solaris, unix, computer, mainframe, lpar, storage, hardware |
| **Database** | MSFT SQL Instance, MSSQL Cluster, Oracle Database, Oracle Instance, Database, Database Instance, PostgreSQL Instance, Cloud DataBase | sql, oracle, db2, database, postgres, mongo, sybase |
| **VMware** | VMware Virtual Machine Instance, ESX Server | esx, vmware, vcenter, vsphere, hyper-v |
| **Middleware** | Tomcat WAR Inclusion | mq, websphere, jboss, tomcat, weblogic, iis, application server, web server |
| **Cloud** | *(none in IO1: GKE health comes from the GCP metrics instead)* | kubernetes, gke, cloud, gcp, container |
| *Application (left out)* | Mapped / Tag-Based / Calculated Application Service, Application Service, Business Application, Business Service, Service Instance, Batch Job | application, service, business, batch |
| *Other* | Infrastructure Service, Data Center, Printer | anything not matched; listed in the incident table, not in a domain |
| *Unknown* | no class | listed in the incident table, not in a domain |

The checks are in this order, so *SQL Server* is Database and *Application Server* is Middleware. Elastic alerts get
their domain from the rule (MQ, WebSphere, JBoss → Middleware; SQL, Oracle, Db2 → Database; otherwise Server); a
Netcool alert on a node with no CMDB CI counts as Network. To change a rule, edit `DOMAIN()` in
`tools/build_infra_overview.py` and rebuild.

## Checks to run once in production (Dev Tools)

**IO1. Which CMDB classes appear, and the domain each gets** (any landing in *Other* needs a rule):

```
POST /_query?format=txt
{ "query": """
FROM servicenow-incidents-*, .ds-bridge-alerts-netcool-default-*
| WHERE @timestamp >= NOW() - 30 days
| STATS records = COUNT(*) BY class = TO_STRING(ci.class_name)
| SORT records DESC
| LIMIT 60
""" }
```

**IO2. Do change requests carry the CI class, and future start dates?** (the Changes table needs both)

```
POST /_query?format=txt
{ "query": """
FROM servicenow-change-requests-*
| WHERE @timestamp >= NOW() - 7 days
| STATS changes = COUNT_DISTINCT(number), with_class = COUNT(ci.class_name),
        starting_later = COUNT_DISTINCT(CASE(TO_DATETIME(start_date) > NOW(), number)),
        close_codes = VALUES(TO_STRING(close_code))
""" }
```

**Results on 11 Nov (`io.txt`):** IO1 above. IO2: 3,251 changes in 7 days, 256 starting later (scheduled changes are
sent, so *due in the next 24 h* works); close codes *successful*, *canceled*, *unsuccessful* (*Failed changes* counts
*unsuccessful*). Only 823 change records carry a CI class, so many changes show **Unknown** as their domain in the
Changes table: they are still listed.

**VM1. What vSphere collects now, and the units of the % fields** (the tile reads up to 1.5 as a fraction):

```
POST /_query?format=txt
{ "query": """
FROM metrics-vsphere.host-*, metrics-vsphere.datastore-*, metrics-vsphere.virtualmachine-* METADATA _index
| WHERE @timestamp >= NOW() - 1 hour
| EVAL kind = CASE(_index LIKE "*vsphere.host*", "host", _index LIKE "*vsphere.datastore*", "datastore", "vm")
| STATS hosts = COUNT_DISTINCT(vsphere.host.name), datastores = COUNT_DISTINCT(vsphere.datastore.name),
        vms = COUNT_DISTINCT(vsphere.virtualmachine.name), cpu_pct_max = MAX(vsphere.host.cpu.used.pct),
        ds_pct_max = MAX(vsphere.datastore.capacity.used.pct), vm_status = VALUES(vsphere.virtualmachine.status) BY kind
""" }
```

## Known limits

- **VMware:** health comes from what vSphere collects (4 of 549 ESX hosts on 2 Nov; check VM1). CPU ready time,
  ballooning, swapping and packet loss are not collected (`vmware_data.xlsx`), so they are not in the status.
- **Database / Middleware:** marked *partial*: their status comes from incidents and alerts; the detailed health is on
  their own dashboards.
- **Network:** no detailed dashboard yet.
- **Failed changes** counts the close code *unsuccessful* (IO2); *canceled* is not a failure.
- **Changes without a CI class** (most of them, IO2) show *Unknown* as their domain.
