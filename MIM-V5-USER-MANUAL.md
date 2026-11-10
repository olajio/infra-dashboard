# MIM V5 dashboard: user manual

*4 Nov 2026, updated 10 Nov · Kibana 9.5.3 · dashboard "MIM V5"*

## What it is for

MIM V5 is the **Major Incident Management** dashboard. It answers the questions a MIM lead asks during an incident,
top to bottom:

1. **🚨 Major Incident Overview:** *how bad is it right now?* Which incidents are past their target, and which alerts
   have nobody working on them.
2. **🔎 Investigate the CI:** *what is affected, and who do I call?* The incident's CI, its owners, what changed,
   what alerted, and what it is connected to in the CMDB.
3. **🩺 Application & Service Health, Dependencies:** *is it the application, the service, or the server?* The
   health of the CI's applications, their services and dependencies, and the server underneath.
4. **🔗 Related dashboards:** the Applications Operations and Infra dashboards, for deeper detail.

Section 1 shows the whole estate (only its *Open alerts, no incident* tile narrows to a picked CI). Sections 2
and 3 follow what you pick in the controls. With nothing picked,
they stay mostly empty. **That is expected, not a fault.**

## Before you start

- **After importing a new version:** open the dashboard, then **More (⋯) → Reset changes**. Kibana keeps your
  unsaved control picks in the browser and reapplies them over a new version, which can hide new controls.
- **Between investigations:** **More → Reset changes** clears every pick.
- **The time picker changes almost nothing.** Every panel in sections 1–3 has its own fixed window, shown on its
  badge (e.g. "Last 7 days"), or follows the **Health window** control. "Last 5 years" on a badge only means the
  panel also reads CMDB links, whatever their age. The default time picker (last 7 days) affects no panel.
- **Blue numbered banners** (① at the top of section 1, ② at the top of section 3) tell you what to pick next.

## The controls

| Control | Where | What it does | Default |
|---|---|---|---|
| **🚨 Incident** | Top bar | The incident to investigate, listed as `INC number · CI name`. Lists active P1–P3 incidents. Type the number to search | *(all incidents)* |
| **🖥️ CI** | Top bar | A CI to investigate without an incident: CIs with a P1–P3 incident opened in the last 31 days, and production servers that sent metrics in the last day | *(no CI selected)* |
| **🧩 Monitored application** | Top bar | Limits the application panels to the applications MIM escalates: In Production, Operational and monitored in `cmdb_with_apm_flag` (138 on 2 Nov). Pick one to see only that application | *(all monitored applications)* |
| **🖥️ Server** | Section 3 | The server for the health panels **when the CI is not a server** (an application service, for example). Take a server from *Server View* (section 2) | *(no server selected)* |
| **🧩 Application** | Section 3 | One application for *Services of the Application*: monitored applications that sent APM data in the last day | *(all applications)* |
| **⚙️ Service** | Section 3 | One APM service for *Upstream*, *Service health* and *Downstream*. With the default, it uses the services running on the CI | *(services on this CI)* |
| **⏱️ Health window** | Section 3 | How far back the server health panels look: 15 minutes to 7 days | 24 hours |

### Which CI the panels follow

1. **An incident is picked:** its CI. The incident always wins over the CI control.
2. **Otherwise, a CI is picked:** that CI.
3. **The server health panels** use that CI if it is a server; if not, the **Server** control.

So for an **application service** (the most common case), pick the incident, then one of its servers in **Server**.
For a **server** CI, the health panels fill by themselves.

## The panels, and what fills them

### 🚨 1 · Major Incident Overview (whole estate; only the *Open alerts, no incident* tile follows the controls)

| Panel | Shows | Fills when |
|---|---|---|
| **Needs attention now** | Every P1, every P2 open longer than 8 h and every P3 open longer than 24 h, in one number, with a strip by priority. **Green at 0** | Always |
| **Active P1**, **P2 over 8 h**, **P3 over 24 h** | The same incidents, by priority. Green and "All clear" at 0; "Needs action" in the priority colour above 0 | Always |
| **Open alerts, no incident** | How many open Netcool alerts (last 24 h) are on production CIs with no open incident, with the Critical count under it: possible blind spots. **Follows the Incident / CI controls** like the table in section 2: the CI's alerts and its CMDB-linked CIs'; every CI's when nothing is picked. Green at 0 | Always |
| **User base · ServiceNow**, **Real users · RUM** | Placeholders: the integrations are in progress | Not yet |
| **Active Incidents (P1 · P2 over 8 h · P3 over 24 h)** | The incidents behind the tiles: priority, CI, state, **when opened**, **SLA**, assignment group, assignee, group manager (with emails), description. Click an incident to open it in ServiceNow | Always |
| **P1 / P2 / P3 Time to Resolve vs Target** | Average age so far of the active incidents opened each day, against the targets (P1 4 h, P2 8 h, P3 24 h, dashed lines, all on one hours axis) | Always |

**Reading the SLA column:** *Breached* or *Breaching* come from ServiceNow's SLA records. *No SLA record* means
ServiceNow sent no SLA record for that incident to Elastic, which is true of most incidents today (raised with the
ServiceNow team).

**What section 1 leaves out:** On Hold, Resolved, Closed and Canceled incidents, and P2 / P3 incidents still within
their target. They can still be picked in the Incident control.

### 🔎 2 · Investigate the CI

Layout: *Escalation Channel* and *Open Alerts with No Incident* side by side at the top; *Changes* and *Alerts on this CI* side by side under them.

| Panel | Shows | Fills when |
|---|---|---|
| **Open Alerts with No Incident** | Open Netcool alerts on CIs with no open incident, Critical first, last 24 h. **With an incident or CI picked:** only alerts on that CI and on CIs linked to it in the CMDB; with nothing picked, every CI's. Sits next to *Escalation Channel* | Always |
| **Escalation Channel** | **Who to call.** One row per active incident on the CI: priority, **state**, **when opened**, CI class and environment, assignment group, assignee and group manager (with emails). With a CI and no incident, one row with the CI's owners | An incident or CI is picked |
| **Changes in the Last 7 Days on this CI** | Change requests in the last 7 days on the CI **and on CIs linked to it** (its ESX host, cluster, switch, applications …) | A change touched the CI or a linked CI this week |
| **Alerts on this CI** | Netcool alerts on the CI, last 7 days: Open or Cleared, severity, and when each started compared with the incident ("likely trigger" if up to 2 h before it opened) | The CI is a Netcool-monitored node with alerts |
| **Blast radius** | How many applications depend directly on the CI. Amber from 1, red from 5 | The CI has applications linked above it in the CMDB |
| **Applications related to this CI** | Every application linked to the CI in the CMDB, in both directions, with the relationship | The CI has CMDB links |
| **Middleware View**, **Database View**, **Server View**, **Other related CIs** | The CI's CMDB neighbours by class. **Server View** names the servers to pick in the **Server** control | The CI has CMDB links |

#### *Alerts on this CI* or *Open Alerts with No Incident*?

Both tables read the same Netcool alerts, but answer different questions:

- **Alerts on this CI:** *"What is alerting on the CI I'm investigating, and did it cause the incident?"*
- **Open Alerts with No Incident:** *"What is alerting that nobody has raised an incident for?"* These are possible
  blind spots.

| | **Alerts on this CI** | **Open Alerts with No Incident** |
|---|---|---|
| **Which CIs** | Only the picked CI, matched by CMDB name or by its Netcool node (`<CI>.cna.com`) | With nothing picked, every production CI. With an incident or CI picked, that CI and the CIs linked to it in the CMDB |
| **Incident filter** | None: shows alerts whether or not an incident exists | Leaves out any CI that has an open incident |
| **Open or cleared** | Both, with the state now (Open or Cleared) | Open only |
| **Time window** | Last 7 days | Last 24 hours |
| **With nothing picked** | Empty | Fills: every open alert with no incident |
| **Extra column** | When each alert started compared with the incident. "Likely trigger" means it started up to 2 hours before the incident was opened | How long it has been open, and whether it was acknowledged |
| **Use it to** | Find the cause of the incident | Spot problems nobody is working on yet, around the CI |

**When you pick an incident**, its CI has an open incident by definition, so that CI's own alerts never appear in
*Open Alerts with No Incident*; they show in *Alerts on this CI*. What remains in *Open Alerts with No Incident* are
alerts on the **linked** CIs (the switch, ESX host or other device the CI depends on) that have no incident of their
own: a neighbouring device may be failing without anyone having raised it.

On a server or application CI, both tables are often empty, because Netcool alerts mostly come from network devices
and UPSs.

**Neither table contains the other.** *Alerts on this CI* goes **deeper** on one CI: open and cleared alerts, 7 days,
incident or not. *Open Alerts with No Incident* goes **wider**: the CI's neighbours too, but only alerts open now that
nobody is handling. They overlap in one case only:

| An alert that is… | In *Alerts on this CI*? | In *Open Alerts with No Incident*? |
|---|---|---|
| On the picked CI, **cleared** | ✅ | ❌ (open alerts only) |
| On the picked CI, open, but no update in the last 24 h | ✅ | ❌ (last 24 h only) |
| On the picked CI, open, and the CI **has an open incident** (always the case when you pick an incident) | ✅ | ❌ (CIs with incidents are dropped) |
| On a **linked CI** (switch, ESX host …), open, no incident | ❌ (picked CI only) | ✅ |
| On the picked CI, open in the last 24 h, the CI has **no** open incident (picked in the **CI** control) | ✅ | ✅ (the only overlap) |

So when you investigate an incident they usually share no rows: one shows what happened **on** the CI, the other
what is failing **around** it that nobody has picked up.

### 🩺 3 · Application & Service Health, Dependencies

| Panel | Shows | Fills when |
|---|---|---|
| **Application Health** | Traffic light of the monitored applications: Failing (a service at 10 %+ failed transactions), Degraded (1 %+), Healthy, with servers, services, error rate, APM number and support group. With a CI: the applications related to it. Applications with no APM data yet: *Enrolled — no telemetry yet* | Always |
| **Services of the Application** | The services of the picked application, worst first: health, error rate, latency, throughput, servers | Always (every monitored application's services), or one application's |
| **⬅ Upstream — what they depend on** | What the service calls (databases, queues, other services) and how healthy those calls are, last hour | A Service is picked, or the CI runs APM services |
| **Service health** | The service's failed-transaction share, last hour: green / amber (1 %) / red (10 %) | Same |
| **Downstream — who is impacted ➡** | Production services that call it: the impacted side | Same, and something calls the service |
| **Middleware Health**, **Database Health**, **Server Health** | On the server: middleware (JBoss, WebSphere, IBM MQ …) and databases with their status; CPU p90, memory peak and fullest disk (amber from 80 %, red from 90 %) | A server that sends metrics. A server with no metrics still shows, as "No data in window" |
| **APM Services Health**, **Process Health**, **Synthetics Health** | APM services running on the server; Windows services and middleware processes; ping monitors | The server has them |
| **Errors from the Logs** | Warning-and-worse log lines from the server, grouped by message | The server sends logs with errors in the Health window |

## How to run an investigation

1. **Section 1:** check *Needs attention now* and the three priority tiles. Find the incident in *Active Incidents*.
2. **Pick it** in **🚨 Incident** (type its number).
3. **Section 2:** *Escalation Channel* names the assignee and manager to call. Check *Changes* and *Alerts on this CI* for a
   likely cause, and *Blast radius* and *Applications related* for the impact.
4. **Section 3:** if the CI is an application service, pick one of its servers (from *Server View*) in **🖥️ Server**.
   Read *Server Health* (red or amber), then the Down rows in *Middleware*, *Database* and *Process Health*.
5. **Applications:** *Application Health* shows the CI's applications. Pick the application in **🧩 Application**
   and its busiest service in **⚙️ Service**: *Upstream* shows what it depends on, *Downstream* who is impacted.
6. **Logs:** *Errors from the Logs*. Widen **⏱️ Health window** to 7 days to see trends.
7. **Escalate** to the assignee, then the group manager, both named in *Escalation Channel*.

**Starting from a CI instead of an incident:** pick it in **🖥️ CI**. *Escalation Channel* still lists every active incident on
it, and the scene keeps working when one incident closes. This is the most reliable way to present the dashboard.

## Demo scenes: fill as many panels as possible

From `MIM-V4-TEST-RUNSHEET.md` (checked with screenshots on 3 Nov). Incidents close and data changes: if a value is
missing from a list, use the next scene. **More → Reset changes** before each scene, then set the controls in order.

| Scene | Controls, in order | Result on 3 Nov |
|---|---|---|
| **1. eFile** (main scene) | CI = `eFile PROD` → Server = `vslrau1p400` → Application = `eFile` → Service = `efile` | **17 of 20 panels filled**: Escalate (4 incidents), every CMDB view (blast radius 18), Application Health, Services, Upstream (efile → oracle, 67,671 calls), Service health, Downstream, Middleware, Process, APM Services, Server, Synthetics, Errors from the Logs. Empty: Changes, Alerts, Database Health |
| **2. Underwriting Tools** | CI = `Underwriting Tools PROD` → Server = `vslrau1p338` → Application = `Underwriting Tools` → Service = `oltp-data-api` | As scene 1, with 4 APM services on the server |
| **3. Enterprise PolicyCenter** (for Changes) | CI = `Enterprise PolicyCenter PROD` → Server = `vrau1pap0041` → Application = `Enterprise PolicyCenter` → Service = `papc-papcintcons1` | As scene 1; *Changes* fills if its 2 Nov change is still within 7 days |
| **4. Alerts** | CI = `cuwash1` (backup `adc-wan-agg2`) | *Alerts on this CI*, *Escalation Channel* |
| **5. Database** | Keep scene 1, then Server = `kau1p802` | *Database Health* (SQL Server). The APM panels empty, as this server runs no APM |

Section 1 fills in every scene.

## Known limits

- **One CI at a time.** The CI list offers only CIs with a recent incident or production servers sending metrics
  today. A device with no recent incident cannot be picked.
- **An application service has no metrics of its own.** Pick one of its servers in **Server**.
- **Netcool alerts exist mostly on network devices and UPSs**, so *Alerts on this CI* is usually empty for servers
  and applications.
- **SLA records:** most incidents show *No SLA record* until the ServiceNow SLA integration is fixed.
- **Database metrics** are recorded under the SQL instance's name (`MSSQLSERVER@host`), so some databases appear only
  as their Windows service.
- **The section 3 Application list** offers every monitored application, whatever is picked in the top **Monitored
  application** control (the team chose to keep it this way on 4 Nov). Picking different applications in the two
  controls empties *Services of the Application*.
- **Placeholders:** *User base · ServiceNow* and *Real users · RUM* are waiting for their integrations.
