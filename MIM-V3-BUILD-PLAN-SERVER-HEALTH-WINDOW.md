# MIM V3 — build plan: CI / Server controls, Health window, automatic servers (18 Oct 2026)

*Plan for your approval. Nothing is built until you accept it.*

**Yes, this is possible.** It is all dashboard-only, with no cluster changes and no lookup index. One limit applies
to business applications; see "Automatic servers".

## Controls (top of the dashboard)

Order: **Incident · CI · Server (new) · Health window (new) · Service · Application**

| Control | Lists | Default |
|---|---|---|
| **CI** (changed) | CIs on P1–P3 incidents (as today), **plus every server that sent Metricbeat data in the last day**. Type to search | (no CI selected) |
| **Server** (new) | Every server that sent Metricbeat data in the last day. If Kibana 9.5 allows it, narrowed to the selected CI's servers (tested first; otherwise the full list, searchable) | (no server selected) |
| **Health window** (new) | 15 minutes · 30 minutes · 1 hour · 6 hours · 8 hours · **24 hours** · 3 days · 7 days | **24 hours** |

- A Kibana control holds at most 10,000 values. If CNA has more monitored servers than that, the lists will be cut.
  The count query in *MIM-V3-SERVER-CONTROLS-FEASIBILITY.md* tells us.
- **Every** Health window option applies, the short ones included.

## Which server the health panels show (precedence)

1. **The Incident's CI**, if it is a server.
2. **The CI control's value**, if it is a server.
3. **The Server control's value.**
4. **Otherwise, automatic:** the servers of the CI (the incident's CI, or the CI control's when no incident is picked)
   — see below.

**"Is a server"** = its CMDB class is a server class (the Server View list), **or** it sent server metrics in the
Health window. Checking both means a server that has gone silent is still recognised as a server.

The other section 2 panels are unchanged. *Escalate*, *Changes*, *Blast radius*, *Applications related to this CI* and
the related-CI views keep following the incident's CI (or the CI control), as today.

## Automatic servers (step 4)

The servers of an application CI are found two ways, combined:
- **CMDB, one step:** servers linked directly to the CI in the full relationship graph, either direction (e.g.
  *Automated Claim Transaction PROD* "runs on" `vslrau1p276`). Production or blank environment, not retired.
- **APM:** servers whose APM agents report services of that application (`metrics-apm.internal`, `host.name`, where
  the service's application is the CI).

**Limit (correction to my earlier answer):** a business application usually reaches its servers in two CMDB steps
(business application → its services → their servers). One ES|QL query cannot look up the second step's links without
a lookup index. So for a **business application** CI, automatic mode finds:
- the servers its **APM agents** run on;
- any servers linked to it **directly** in the CMDB.

Its services' CMDB servers are not found. For an **application service** CI (the usual incident CI, like *Automated
Claim Transaction PROD*), one step finds its servers.

## Panels that follow the chosen server(s) and the Health window

| Panel | Change |
|---|---|
| **Server Health** | Becomes a **table, one row per server**, worst first: Server, Last seen, CPU p90 %, Memory peak %, Fullest disk %, Status. A target server with no data in the window still gets a row, "No data in window", so it is not silently missing |
| **Middleware Health**, **Database Health**, **Process Health** | Follow the server(s); a Server column added |
| **Synthetics Health** | Monitors that target the server(s) (or the CI itself) |
| **Errors from the Logs** | Log errors from the server(s) |
| **Applications on this CI** | APM services on the server(s); window: Health window instead of a fixed 7 days |
| **Alerts on this CI** | Netcool alerts on the server(s) and on the CI itself. **Recommendation: keep its fixed 7 days.** Its "Likely trigger" needs to reach back to before the incident opened; a 15-minute window would hide the trigger |

Each of these panels shows the badge **"Last 5 years"**. That range is only there so the panel can read the CMDB links.
The data window is the Health window, explained in each panel's description.

**Unchanged:** section 1 (fixed ranges), section 3 (fixed last hour), *Changes* (fixed 7 days). The dashboard's time
picker therefore no longer affects section 2's health panels.

## Not included

- **Middleware / Database controls:** left out, as agreed.
- **Two-step CMDB lookup for business applications:** needs the lookup index (option (b)).

## How it will be checked

- **Tests on Elasticsearch 9.5.3** with test data covering each precedence step:
  1. incident on a server;
  2. CI control server;
  3. Server control;
  4. automatic, for an application-service CI, and for a business-application CI through APM.
- **Also tested:** every Health window value, a silent server ("No data in window"), and non-production servers left
  out.
- **Kibana 9.5.3:** screenshots, and the link check.
- **First, a quick test** that:
  - a fixed-values control works;
  - the Health window filter is applied efficiently by Elasticsearch;
  - whether the Server list can narrow to the CI's servers.
- **Docs:** the guide, the walkthrough and a summary updated.
