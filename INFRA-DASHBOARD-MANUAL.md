# Infrastructure Dashboard: user manual

*Updated 5 Nov 2026 (Incident control) · Kibana 9.5.3 · dashboard "Infrastructure Dashboard"*

## What it is for

The Infrastructure Dashboard answers one question about **one configuration item (CI)** at a time, picked directly or through an incident: *is this CI, and
what runs on it, healthy, and who owns it?* You pick a CI (a server, an application service, a network device …)
and every section follows it:

1. **Incidents, changes and alerts:** what is open, what changed, and what is alerting on the CI.
2. **Infrastructure overview:** the health of the server behind it (CPU, memory, disk, databases, middleware,
   processes), plus cloud (GKE) health.
3. **Applications overview:** the applications that depend on the CI, and the health of their services.
4. **Detailed dashboards:** links to the Server, Database, Cloud, Middleware and VMware infra dashboards, and to the Applications Operations and MIM dashboards.

Since 5 Nov the dashboard has the MIM V5 look: section icons (🚨 🖥️ 🩺 🔗), tiles with icons that are green at 0,
and row numbers in the tables.

With **no CI picked**, the dashboard shows an estate-wide view: incident counts for every CI, every active Elastic
infrastructure alert, every GKE cluster and every monitored application. The CI-specific tables stay empty until a CI
is picked. **That is expected, not a fault.**

## Before you start

- **After importing a new version:** open the dashboard, then **More (⋯) → Reset changes**. Kibana keeps your unsaved
  control picks in the browser and reapplies them over a new version, which can hide new controls.
- **Between investigations:** use **More → Reset changes** to clear every control.
- **The time picker changes nothing.** Every panel has its own fixed window (shown on its badge, e.g. "Last 7 days")
  or follows the **Health window** control. "Last 5 years" on a badge only means the panel also reads CMDB links,
  whatever their age.

## The controls

The controls have an icon in their title, and a blue **numbered banner** sits next to each group, saying what to
pick: ① an incident or a CI (top bar), ② a server (section 2), ③ an application and a service (section 3).

| Control | Where | What it does | Default |
|---|---|---|---|
| **🚨 Incident** | Top bar | The incident to investigate, listed as `INC number · CI name` (active P1–P3 incidents; type the number to search). **It selects the incident's CI and wins over the CI control**, exactly as on MIM | *(all incidents)* |
| **🖥️ CI** | Top bar | The CI to investigate. Lists CIs with a P1–P3 incident opened in the last 31 days (open or closed), and production servers that sent metrics in the last day. Type to search. | *(no CI selected)*: estate-wide view |
| **🧩 Monitored application** | Top bar | Limits the application panels to the applications MIM escalates: In Production, Operational and monitored in `cmdb_with_apm_flag` (138 on 2 Nov). Pick one to see only that application | *(all monitored applications)* |
| **🖥️ Server** | Section 2 | The server for the health panels **when the CI is not a server** (an application service, for example). Take a server from *Applications related to this CI* or from MIM's *Server View*. If the CI is itself a server, the CI wins | *(no server selected)* |
| **⏱️ Health window** | Section 2 | How far back the health panels look: 15 minutes to 7 days | 24 hours |
| **🧩 Application** | Section 3 | One application for *Services of the Application* (monitored applications that sent APM data in the last day) | *(all applications)* |
| **⚙️ Service** | Section 3 | One APM service for *Service health*. With the default, it uses the services running on the CI | *(services on this CI)* |

**Rule of thumb:** pick the **incident** (or, without one, the **CI**) first. If it is not a server, pick one of its servers in **Server**. Then pick an
**Application** and a **Service** to fill section 3.

## The panels, and what fills them

### 🚨 1 · Incidents, changes and alerts

| Panel | Shows | Fills when |
|---|---|---|
| **Active P1 incidents**, **P2 over 8 h** | Active P1 incidents, and active P2 incidents open longer than MIM's 8 h target (not On Hold, Resolved, Closed or Canceled; updated in the last 30 days), on the CI or on every CI when none is picked. Green at 0. They count the rows of the table below | Always |
| **Active Elastic infra alerts** | How many Elastic infrastructure alerts are active now on the CI, or across the estate with no CI. Green at 0. The rows are in *Elastic infra alerts* below | Always |
| **User impact · ServiceNow**, **User impact · RUM** | Placeholders: the integrations are in progress | Not yet |
| **Active Incidents (P1 · P2 over 8 h)** | MIM's *Active Incidents* table, with MIM's rule (every P1; a P2 once open longer than 8 h): incident, priority, CI, state, when opened, SLA, assignment group, assignee and group manager (with emails), description. With nothing picked: **every CI's**; with an incident or CI: those on that CI. Click the incident or the CI to open it in ServiceNow | Always |
| **Changes on this CI (last 7 days)** | Change requests in the last 7 days on the CI **and on CIs linked to it in the CMDB** (its ESX host, cluster, applications …) | A change touched the CI or a linked CI this week |
| **Alerts on this CI (Netcool)** | Netcool alerts on the CI in the last 7 days: Open or Cleared, severity, how often it fired | The CI is a network device, UPS or other Netcool-monitored node with alerts |
| **Elastic infra alerts** | Alerts from Elastic's own rules (the paladin-* rules: host up, filesystem, CPU, memory, processes, Windows services, IBM MQ) on the CI in the last 7 days. With no CI: **every active paladin alert** | No CI picked, or a server that raised an Elastic alert |

### 🖥️ 2 · Infrastructure overview

The health panels follow **the CI if it is a server, otherwise the Server control**.

| Panel | Shows | Fills when |
|---|---|---|
| **Server Health** | Status (Reporting; Silent = no data for 10 min; No data in window), CPU p90, memory peak, fullest disk. Amber from 80 %, red from 90 % | A server that sends metrics. A server with no metrics still shows, as "No data in window" |
| **Database Health** | Databases on the server: SQL Server and database services or processes (SQL Server, Oracle, Db2, PostgreSQL …), Down first | The server runs a database |
| **Middleware Health** | Middleware on the server: IBM MQ, IBM HTTP Server, JBoss, WebSphere, IIS, Tomcat … | The server runs middleware |
| **Process Health** | Windows services and middleware processes; Stopped = an Automatic service that is not running | The server sends process or service data |
| **Cloud health · GKE** | One row per GKE cluster: status, nodes, CPU, memory (non-evictable memory used ÷ allocatable; reclaimable cache is left out), container restarts. With no CI: every collected cluster | No CI picked, or a cluster CI (or a CI linked to one) |
| **VMware health**, **Custom integration health** | Placeholders: not available yet (each says why) | Not yet |

### 🩺 3 · Applications overview

| Panel | Shows | Fills when |
|---|---|---|
| **Applications related to this CI** | Every application linked to the CI in the CMDB, in both directions, with the relationship | A CI is picked and it has CMDB links |
| **Application Health** | Health of the monitored applications (Failing / Degraded / Healthy, error rate, services, servers). With a CI: the applications related to it. Applications with no APM data yet are listed as *Enrolled — no telemetry yet* | Always (all monitored applications), or the CI's applications |
| **Services of the Application** | The services of the picked application, worst first: health, error rate, latency, throughput | Always (every monitored application's services), or one application's |
| **Service health** | One tile per service: share of failed transactions in the last hour, green / amber / red | A Service is picked, or the CI runs APM services |

### 🔗 4 · Detailed dashboards

Each card opens the technology team's own dashboard in a new tab. They do not follow this dashboard's controls: pick
the server or cluster again there.

| Link | Opens | Use it for |
|---|---|---|
| **🖥️ Server Infra Dashboard** | `kibana-prod.gcp.cna.com/app/r/s/qJk5u` | Full server metrics, beyond *Server Health* |
| **🗄️ Database Infra Dashboard** | `…/app/r/s/w6zL4` | Database detail, beyond *Database Health* |
| **⚙️ Middleware Dashboard** | `…/app/r/s/jwCRg` | Middleware detail, beyond *Middleware Health* |
| **🧱 VMware Infra Dashboard** | `…/app/r/s/t4oxr` | VMware, while *VMware health* is a placeholder |
| **☁️ Cloud Infra Dashboard** | `…/app/r/s/MDJ9f` | GCP detail, beyond *Cloud health · GKE* |
| **🩺 Applications Operations Dashboard** | `…/app/r/s/I3R7D` | Application and service detail, beyond section 3 |
| **🚨 MIM Dashboard** | `…/app/r/s/ZSMtk` | Running a major incident |

## How to investigate

1. **Start from the incident.** Pick it in **🚨 Incident** (or its CI in **CI**). *Active Incidents* names who to call.
2. **Check what changed and what alerted:** *Changes*, *Alerts on this CI (Netcool)*, *Elastic infra alerts*.
3. **Find the server.** If the CI is a server, section 2 already shows it. If not, take a server from *Applications
   related to this CI* or MIM's *Server View*, and pick it in **Server**.
4. **Read the server's health:** red or amber in *Server Health*, Down rows in *Database* / *Middleware* / *Process
   Health*. Widen **Health window** to 7 days to see trends.
5. **Check the applications:** *Application Health* for the CI's applications, then pick an **Application** and a
   **Service** to see its services and failure rate.
6. **Go deeper:** open the technology's dashboard from section 4.

**Starting without a CI:** *Elastic infra alerts* lists every active infrastructure alert. Pick one of its servers in
**CI** to investigate it.

## Demo scenes: fill as many panels as possible

Values checked against data from 2–3 Nov. Incidents close and data changes, so if a value is missing from a list, use
the backup. **More → Reset changes** before each scene, then set the controls in the order given.

| Scene | Controls, in order | What fills | Stays empty |
|---|---|---|---|
| **1. Estate overview** (open with this) | Nothing picked | *Active P1 / P2* (every CI), *Elastic infra alerts* (every active alert), *Cloud health · GKE* (every cluster), *Application Health* (138 monitored applications), *Services of the Application* | The CI tables, the server panels, *Service health*: no CI picked |
| **2. Application service: eFile** (main scene) | CI = `eFile PROD` → Server = `vslrau1p400` → Application = `eFile` → Service = `efile` | *Active P1 / P2*, *Active Incidents* (4 on 3 Nov), *Changes* (if any on eFile or a linked CI), *Server*, *Middleware* (JBoss), *Process Health*, *Applications related* (18), *Application Health*, *Services of the Application*, *Service health* | *Alerts (Netcool)*, *Database Health* (JBoss server, no database) |
| **3. Server with APM: vslrau1p338** | CI = `vslrau1p338` → Application = `Underwriting Tools` → Service = `oltp-data-api` | *Server*, *Middleware* (6 JBoss components), *Process Health*, *Elastic infra alerts* (if the server has any), *Applications related*, *Application Health*, *Services of the Application*, *Service health* | *Active Incidents* (no incident on the server itself), *Alerts (Netcool)*, *Database Health* |
| **4. Change and database: kau1p802** | CI = `kau1p802` | *Changes* (1 change on 2 Nov), *Server*, *Database* (SQL Server), *Process Health* (Windows services) | APM panels: a Windows database server with no APM |
| **5. Network device alerts: cuwash1** | CI = `cuwash1` (backup: `adc-wan-agg2`) | *Active Incidents*, *Alerts on this CI (Netcool)* | Server and application panels: not a server |

**Backups for scene 2:** CI = `Enterprise PolicyCenter PROD` → Server = `vrau1pap0041` → Application =
`Enterprise PolicyCenter` → Service = `papc-papcintcons1` (it calls 13 services; 1 change on 2 Nov). Or CI =
`Underwriting Tools PROD` → Server = `vslrau1p338` → Service = `oltp-data-api`.

**Panels that no scene fills yet:** *User impact · ServiceNow*, *User impact · RUM*, *VMware health* and *Custom
integration health* are placeholders that say why. Present them as "coming next".

## Known limits

- **One CI at a time.** The CI list offers only CIs with a P1–P3 incident opened in the last 31 days, or production
  servers sending metrics today. A device with no recent incident (most switches, GKE clusters) cannot be picked; with no CI, the GKE and
  Elastic alert panels still show the whole estate.
- **An application service has no metrics of its own.** Pick one of its servers in **Server** for section 2.
- **Netcool alerts exist mostly on network devices and UPSs**, so *Alerts on this CI* is usually empty for servers
  and applications.
- **Database metrics** are recorded under the SQL instance's name (`MSSQLSERVER@host`), so some databases appear only
  as their Windows service.
