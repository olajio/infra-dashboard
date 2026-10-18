# MIM V3 — Services of the Application, and when the section 2 health panels fill (18 Oct 2026)

Answers to two questions; nothing changed on the dashboard.

## Services of the Application

| Application control | What it lists |
|---|---|
| *(all applications)* | Every **production** APM service (`prd1`, `prd2`, `prd`, `prod`, `production`) that sent transaction data in the **last hour** |
| An application picked | Only the services of that application that sent transaction data in the last hour, with how they are doing: Failing / Degraded / Healthy, error rate, latency, calls per minute, transaction count |

Details:
- **"Ingesting" means sending transaction data.** A service that sends only other APM data (errors, logs) but handled
  no transactions in the hour is not listed.
- **It needs the application name on the service** (`ci.name`). That is present on 398 of 400 production services;
  the other two do not appear.
- "How they are doing now" means **over the last hour**, refreshed every 5 minutes.
- It does not follow the Incident or CI control, only the Application control.

## Why the six panels were empty for "Automated Claim Transaction PROD"

**That CI is an application service, not a server.** Middleware Health, Database Health, Server Health, Applications
on this CI, Process Health and Synthetics Health look for monitoring data reported **by the CI itself**, matched on
its name.

*Automated Claim Transaction PROD* is a logical CI in the CMDB (an application service); no agent runs "on" it. Its
CPU, processes, services and APM agents report under the names of the servers it runs on (e.g. `vslrau1p276`,
`vslrau1p174`). So nothing matches its name and the panels stay empty.

The **Application control has no effect on section 2**; it only filters *Services of the Application*.

## When each panel fills

The CI is the incident's affected CI, or the CI control's choice when no incident is picked.

| Panel | Needs | Time range |
|---|---|---|
| **Server Health** | The CI is a **server** running Metricbeat (CPU, memory, disk), with records tagged with its exact name (`ci.name`) | Time picker |
| **Middleware Health** | The server reports **middleware** processes (labelled by the monitoring enrichment: MQ, IHS, JBoss, WebSphere …) or Windows middleware services (IIS, Tomcat, MQ …) | Time picker |
| **Database Health** | Same, for **databases**: SQL Server metrics, or Oracle / SQL / DB2 / PostgreSQL … processes or Windows services | Time picker |
| **Process Health** | The server reports **Windows services** or labelled processes; it shows only problems (Stopped, Not seen) and middleware | Time picker |
| **Applications on this CI** | **APM-instrumented production services run on the server** (APM `host.name` = the CI, exact or UPPER case) | Last 7 days (fixed) |
| **Synthetics Health** | A **synthetic monitor targets the CI**: tagged with its name, or its URL's domain is `<CI>` or `<CI>.cna.com` | Time picker |

**For all six to fill at once**, the CI must be a **server** that:
1. runs Metricbeat;
2. runs labelled middleware **and** database processes or services;
3. hosts production APM services;
4. is the target of a synthetic monitor.

Few servers have all four, so a partly empty section 2 is normal.

Two more things empty these panels:
- a CI name that differs in case from the monitoring data (except *Applications on this CI*, which also tries UPPER
  case);
- the time picker: with "Last 15 minutes", a server that went silent 30 minutes ago shows nothing.

## What to do today with an application CI

- **Section 2, *Applications related to this CI* and *Server View*:** show which servers it runs on.
- **Section 3, *Application Health*:** shows its business application's live health.
- **Service control:** pick one of its services there to see the dependency panels.

To see a server's own health, pick that server in the CI control. But the control only lists CIs that had a P1–P3 in
the last 31 days, so the server is often not there.

## Two ways to close this gap (proposed)

1. **Let the CI control list every monitored CI.** This was option (a) in *MIM-V3-CI-VS-CMDB-RELATIONSHIPS.md*: read
   the server name in *Server View* and pick it. It is a small change.
2. **For an application CI, show its servers' health automatically.** Section 2 would look up the servers it runs on
   in the CMDB and fill the six panels for them. The catch: those panels would get a fixed time window (e.g. last 24
   hours) instead of following the time picker. It is a bigger change.

Assessment of both, and of the Server / Middleware / Database controls asked for next:
*MIM-V3-SERVER-CONTROLS-FEASIBILITY.md*.
