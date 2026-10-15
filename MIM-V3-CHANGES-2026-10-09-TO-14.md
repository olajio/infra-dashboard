# MIM V3 — changes from Friday 9 Oct to Wednesday 14 Oct 2026, and what is left

## Changes

### Friday 9 Oct
- Fixed links that only worked in edit mode on Kibana 9.5, and wrote up the investigation
  (*MIM-V3-LINKS-INVESTIGATION.md*).
- Renamed the "SRE Dashboard" link to "Applications Operations Dashboard".
- Cut At a Glance to six tiles and made Hotspot CI count P1s per CI, then renamed it "Hotspot CI" (both replaced on
  14 Oct).
- Analysed the CMDB dependency index (Round 6, *MIM-V3-APP-DEPENDENCIES.md*).
- Added the **Applications impacted** tile (section 1).
- Added three CMDB dependency panels (section 2): **Blast radius**, **Applications that depend on this CI** and
  **What this CI runs on**.

### Monday 12 Oct
- Moved the **Incident** control first and the **CI** control second.
- Picking an incident now makes sections 2 and 3 show its affected CI; each incident option shows its CI
  ("INC… · CI").
- Added a Users impacted placeholder tile.
- Split Middleware and Database Health; renamed Infra Health to **Server Health**.

### Tuesday 13 Oct
- Changes limited to the last 7 days (Round 7 queries).
- Added **Alerts on this CI** (section 2): Netcool alerts on the CI, with "likely trigger / earlier / after" timing
  against the picked incident.
- Added **Open Alerts with No Incident** (section 1).
- Added an **Assigned MIM** column to Active Incidents and Escalate: the person who promoted the incident to a major
  incident, or the assignment group's manager when nobody did (Round 8).

### Wednesday 14 Oct (all of `suggestions2.txt`)
- One **Active P1 / P2 donut** replaces the six tiles.
- Users impacted shows a **demo number** (2,500).
- Removed the "Pick the incident…" ribbon.
- **Middleware / Database Health** are now tables: Down / Healthy badge, minutes since seen, and the server, which
  links to the CMDB.
- **Server Health** names the server on each tile.
- **Applications on this CI** and **Changes** look at the last 7 days.
- The section 4 cards show the hyperlinks only.
- Added a `tools/` folder with the patch script, a test and the link checker (the earlier build scripts were lost
  when the work environment was reset).

## Still to do, per the suggestions files

### Not done
1. **"Include a table to automatically select"** (`new_suggestions.txt`). Kibana cannot set a control by clicking a
   table row. An alternative needs agreeing: either a click on Active Incidents applies a filter, or the MIM lead
   keeps using the Incident control.
2. **Number of users likely impacted** from CMDB static user counts or real-user monitoring (RUM). The dashboard shows
   a demo number until ATOS ingests the data.

### New request (15 Oct): related CIs grouped by CI class
See `relationships1.png` and `relatiosnhips2.png`. For the selected CI, fill the Middleware, Database, Server and
Application views from its **CMDB relationships**, grouping each related CI by its class:

| Group | CMDB classes |
|---|---|
| Middleware (application servers) | Application Server, JBoss, JBoss module, Tomcat, Tomcat WAR, WebLogic, IBM WebSphere, WebSphere EAR |
| Database | Cassandra Instance, Cloud DataBase, DB2 Subsystem, HBase Instance, Database Instance, DB Instance Size, MongoDB Instance, SQL Server Analysis / Integration / Reporting Services, MS SQL DataBase, MSFT SQL Instance, MySQL Instance, Oracle Instance, Oracle DB Service, PostgreSQL Instance, Sybase Instance |
| Server | AIX, ESX, HPUX, Hyper-V, IBM Frame, Load Balancer, Citrix Netscaler, Linux, IBM Mainframe, Mainframe LPAR, Network Appliance Hardware, Server, Solaris, Storage Server, Windows Server (some names in the image too small to read; confirm the full list) |
| Application | Business Application (application-to-application relationships) |

- Source: `cmdb_app_dependencies_v2` carries each related CI's class (`child_ci.class` / `parent_ci.class`), so the
  grouping is a refinement of *What this CI runs on*, which today mixes all classes in one list.
- Lets application-service CIs (e.g. *Automated Claim Transaction PROD*) show their middleware, databases and servers.
- To do first: confirm the full class list (the ServiceNow class names, e.g. `cmdb_ci_app_server_tomcat`) with a
  query on the dependency index.
- **Limit:** the dependency index has no timestamp, so these grouped panels can show CMDB status but not live
  health (up / down) unless an `@timestamp` is added to the index (same blocker as *What this CI runs on*).

### New request (15 Oct): application health from its services
Rate each application by the health of its associated services, so the MIM can see which application to look at and
then drill down to the services that are down or degraded.

- **Not covered today.** Section 3's *Service health* rates single services (the picked one, or those on the selected
  CI); *Business applications impacted* rolls up only the applications whose services call the picked service;
  section 1's *Applications impacted* counts applications from the CMDB without health.
- **Proposed:** an *Application health* panel. One row or tile per business application with its worst service
  status (Failing / Degraded / Healthy), how many of its services are failing or degraded, and its error rate.
  Worst first, scoped to the applications related to the selected incident / CI, or to all applications when none is
  picked.
- **Drill down:** clicking an application lists its services with their health (error rate, latency, throughput), and
  from there the APM Service Map, as section 3 does today.
- **Data:** APM transaction metrics already carry the business application on each service (`ci.name`, `ci.number`
  from the APM CMDB enrichment), so the roll-up can be live with no dependency-index join. The CMDB link business
  application → Kubernetes services in `cmdb_app_dependencies_v2` can fill gaps, but without live health (no
  timestamp on that index).
- **To check first:** how many production APM services carry `ci.name`, and whether one application maps to several
  services as expected (a short query round).

### Needs clarifying
3. **"Service health"** (`new_suggestions.txt`). Section 3 already has Service health tiles; what is wanted beyond
   that?

### Done, with limits
4. **Alert that resulted in the incident.** Matched by CI and time only, because Netcool alerts carry no incident
   number. An exact link needs the Netcool / ServiceNow integration to write the incident number back to the alert.
5. **Clickable health widgets.** Middleware and Database link to the server in the CMDB. Server Health has no
   click-through, because Kibana 9.5 blocks it on those tiles. Whether the section is "appealing" enough is for the
   client to judge.
6. **Changes, 7 days.** Mostly shows changes on the CI itself. Changes on linked CIs only appear when their CMDB link
   was updated in the same week.
7. **Assigned MIM.** The real MIM shows only on incidents promoted to major incident (last 30 days: 2 of 3 P1s, no
   P2s). Everything else shows the assignment group's manager.

### Other open items, outside the suggestions files
- Live health in *What this CI runs on* needs an `@timestamp` added to the CMDB dependency index.
- Whether to remove *Applications on this CI*: kept for now.
- None of this week's changes have been checked on the Kibana 9.5.3 cluster yet.
