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
| **Changes in progress or due in the next 24 h** | Changes on infrastructure CIs that have started and not ended, or start within 24 h |
| **Infrastructure incidents per day** | Incidents of every priority opened per day in the last 30 days, by domain |

### 🔗 4 · Detailed dashboards

The seven dashboards (Server, Database, Cloud, Middleware, VMware, Applications Operations, MIM), and **Data
freshness**: when each source last delivered (green ≤ 30 min, amber ≤ 2 h, red older). If a source is red, the panels
that read it are out of date.

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

## Known limits

- **VMware:** only 4 of 549 ESX hosts are collected, so the tile shows incidents and alerts on VMware CIs but no health.
- **Database / Middleware:** marked *partial*: their status comes from incidents and alerts; the detailed health is on
  their own dashboards.
- **Network:** no detailed dashboard yet.
- **Failed changes** counts the close code *unsuccessful* (IO2); *canceled* is not a failure.
- **Changes without a CI class** (most of them, IO2) show *Unknown* as their domain.
