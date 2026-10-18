# MIM V3 — CI / Server / Middleware / Database controls and automatic server health: is it possible? (18 Oct 2026)

*Assessment only: nothing has been built. The decisions at the end are yours.*

## What you asked for

1. The **CI control** lists every monitored CI, so you can read a server name in *Server View* and pick it.
2. A new **Server control**, used when the CI control does not hold a server:
   - a server picked in the **CI** control wins;
   - if the CI control holds something that is not a server (e.g. an application), the **Server** control's server
     is used.
3. **Middleware** and **Database** controls that work the same way.
4. **Automatic server health for an application CI.** When the CI is an application, section 2 looks up the servers
   it runs on in the CMDB and fills the six health panels for them, over a fixed window (e.g. last 24 hours). An
   explicitly picked server switches this off.

## Short answer

| # | Possible? | Effort | Notes |
|---|---|---|---|
| 1 | **Yes** | Small | Limit of 10,000 options per control. Needs one count query on the cluster first |
| 2 | **Yes** | Medium | The precedence rule is written into each server panel's query |
| 3 | **Possible, but I advise against it for now** | Medium | Monitoring data has no reliable link to CMDB middleware / database names |
| 4 | **Yes, two ways** | Medium to large | Your exact time rule (fixed window when automatic, time picker when picked) cannot be done in one panel; see part 4 |

## 1. CI control lists every monitored CI

- **The list:** CIs on P1–P3 incidents (as today), plus every CI that sent monitoring data in the last day (servers
  from Metricbeat, hosts from APM). You search it by typing.
- **Limit:** a Kibana control list can hold at most **10,000** values. Run this in Discover (ES|QL mode) to count
  the servers first:

  ```
  FROM .ds-metrics-system.cpu-default*
  | WHERE @timestamp >= NOW() - 1 day
  | STATS monitored_cis = COUNT_DISTINCT(ci.name)
  ```

## 2. Server control, and which value wins

**The Server control** lists the servers that sent Metricbeat data in the last day.

**Which server the health panels use**, in order:
1. the **Incident** control's CI, if it is a server (the Incident control already overrides the CI control today);
2. the **CI** control's value, if it is a server;
3. the **Server** control's value;
4. otherwise, with point 4 built, the servers the CI runs on in the CMDB (automatic).

**"Is a server"** = the CI sends server metrics (CPU, memory, disk). This is the same data the panels show, so the
test always matches what can be displayed. The CMDB class would miss servers whose class is unusual.

**Which panels use the server:**
- Server Health, Middleware Health, Database Health, Process Health, Applications on this CI and Synthetics Health.
- I would add *Errors from the Logs* and *Alerts on this CI*: logs and Netcool alerts are also reported per server.
- *Escalate*, *Changes* and the related-CI tables stay on the incident's CI. They describe the CI, not where it runs.

**To verify when building:** whether the Server control's list can be narrowed to the servers of the selected CI.
Kibana 9.5 passes the other controls' values to a control's query; I will test that the list refreshes when the CI
changes. If it does not, the Server list shows all servers, still searchable by typing.

## 3. Middleware and Database controls

Possible, but less useful than they sound:
- **CMDB names do not match monitoring names.** The CMDB names middleware and databases like
  `Tomcat@vslrau1p276:8081` or `oradb01`. The monitoring data identifies them differently: by server plus process
  type (e.g. `vslrau1p276 · ibm_mq · QM1`) or Windows service name. There is no reliable link between the two, so
  picking a CMDB middleware CI could not reliably drive the health panels.
- **What would work:** controls that list the **monitored** components (server · component) and narrow *Middleware
  Health*, *Database Health* and *Process Health* to the one you pick.
- **Value:** small today. Those tables already list every component on the server, Down first. They would help mainly
  when automatic mode (point 4) shows many servers at once.

**My advice:** leave them out for now, and add them if automatic mode shows long lists in practice.

## 4. Automatic server health for an application CI

**Possible.** The health panels would show a **Server** column, so you can see which servers automatic mode picked.
*Server Health* would become one row per server (last seen, CPU, memory, fullest disk, worst first) instead of
four tiles.

### The time window

A Kibana panel's time range is set in the panel's settings. It cannot switch between "fixed 24 hours" and "the time
picker" depending on a control. So "fixed window when automatic, time picker when a server is picked" is not
possible as stated. Two ways round it:

**(a) Dashboard-only (no cluster change).** The panels read the CMDB links and the monitoring data in one query, as
*Application Health* does now. Because the CMDB links need the 5-year range, these panels **never** follow the time
picker, whether the server is automatic or picked. Their window is set:
- either **fixed** (e.g. last 24 hours);
- or by a new **"Health window"** control (15 min / 1 h / 24 h / 7 days) that replaces the time picker for these
  panels.

**(b) With a one-off cluster set-up (recommended long term).** A **lookup copy** of the application-to-server links
from the CMDB, read with ES|QL `LOOKUP JOIN`. I tested on 9.4 that the time picker does not apply to the lookup side.
So the panels **follow the time picker in both modes**, and no fixed window is needed at all. Needs:
1. a lookup index, for example the "Runs on" / "Hosted on" links from applications to servers;
2. a job that refreshes it (e.g. daily);
3. someone who owns it;
4. read access for viewers.

**Reach in both:**
- **One step in the CMDB** covers application **services** like *Automated Claim Transaction PROD*, which "runs on"
  its servers.
- **A business application** usually reaches its servers through its services, two steps. Both designs can follow two
  steps; it adds query work.

## Recommended plan

| Phase | What | Needs |
|---|---|---|
| **1** | CI control lists every monitored CI; **Server control** with the precedence above; the six health panels plus Logs and Alerts follow the chosen server and keep the **time picker** | Dashboard only; the count query in part 1 |
| **2** | **Automatic servers** for an application CI | Either (a) now, accepting a fixed window or a "Health window" control; or (b) once a lookup index has an owner, keeping the time picker |
| Later | Middleware / Database controls, if long lists show up in practice | — |

## Decisions for you

1. Go ahead with **phase 1**?
2. For automatic servers: **(a)** now, with a fixed 24-hour window or a "Health window" control, or **(b)** later,
   with the lookup index and the time picker?
3. Middleware / Database controls: **leave out for now**, or build the monitored-component version?
