# MIM V3 — test cases (20 Oct 2026)

TC-01 is done: *MIM-V3-TEST-CASE-INC2676403.md* (a server CI with APM). This catalog covers every other kind of CI
and every control combination.

**Finding values:** run **BZ** in `queries_ro_run.md` (Round 13, Dev Tools). It lists the active incidents by CI
class, with up to 3 examples per class. Each example is tagged:
- `[metrics]`: the CI sends server metrics;
- `[APM]`: it runs production APM services;
- `[dre]`, `[cut]` …: a non-production environment.

**Defaults unless a case says otherwise:** Health window *24 hours*, Service *(services on this CI)*, Application
*(all applications)*, CI and Server controls empty. Use **More → Reset changes** between cases.

## A. The incident's CI is not a server with APM

| ID | Scenario | Pick | Expected |
|---|---|---|---|
| **TC-02** | Server with metrics but no APM (e.g. a Windows or database server) | Incident on a CI tagged `[metrics]` but not `[APM]` (BZ: *Windows Server*, *Linux Server*) | *Server*, *Process* and (if any) *Database Health* fill. *APM Services Health*, *Upstream*, *Service health* and *Downstream* stay empty: no APM on it |
| **TC-03** | Server that sends no metrics (e.g. AIX) | Incident on a server-class CI with no tag (BZ: *AIX Server*) | *Server Health* shows one row, **"No data in window"**: it is recognised from its CMDB class. Process and middleware panels fill only if their data is collected |
| **TC-04** | Application service | Incident on an *Application Service* CI (e.g. *Automated Claim Transaction PROD*) | Section 2 fills from the CMDB: *Applications related*, *Blast radius*, and *Server View* lists its servers. The health panels stay **empty**: the CI is not a server |
| **TC-05** | Application service + a server picked | As TC-04, then type a server from *Server View* into the **Server** control | The health panels now show that server; section 2 stays on the application service. Confirms precedence step 3 |
| **TC-06** | Business application | Incident on a *Business Application* CI | *Application Health* lists the application itself. Pick it in the **Application** control: *Services of the Application* lists its services. Health panels empty (pick a server, as in TC-05) |
| **TC-07** | Middleware or database instance (e.g. Tomcat, Oracle instance) | Incident on such a CI (BZ: *Tomcat*, *Oracle Instance* …) | *Server View* names the server it runs on; pick it in the **Server** control to see its health. *Middleware View* / *Database View* show what it connects to |
| **TC-08** | Network device | Incident on an *IP Switch* / *IP Router* CI | *Alerts on this CI* (Netcool down alerts) and *Synthetics Health* (ping monitor) are the main signals. Health panels empty: no server metrics |
| **TC-09** | Incident with no CI | An incident shown as `<number> · (no CI)` | *Escalate* shows the incident and its owners; the rest of sections 2 and 3 stay empty. Recovery: ask the assignment group for the CI and pick it in the **CI** control |
| **TC-10** | Non-production CI | An example tagged `[dre]`, `[cut]` … | The CI's own panels still show (*Escalate* Env shows its environment). Its non-production relationships are **hidden** from the related-CI tables and *Blast radius* (production only) |

## B. The controls

| ID | Scenario | Pick | Expected |
|---|---|---|---|
| **TC-11** | CI control instead of an incident | Incident *(all incidents)*; CI = TC-01's CI | Same panels as TC-01. *Escalate* lists every active incident on the CI |
| **TC-12** | CI with no active incident | CI control = a production server with no open incident (type any server name) | *Escalate* still shows **one row with the CI's owners**; health panels fill for the server |
| **TC-13** | The incident wins over the CI control | Incident = TC-01; CI = any other CI | Every panel follows the incident's CI, not the CI control |
| **TC-14** | Server precedence | (a) CI = a server X, Server = server Y. (b) CI = an application service, Server = server Y | (a) The health panels show **X**: a server in the CI control wins. (b) They show **Y** |
| **TC-15** | Server control alone | Incident and CI empty; Server = any server | The health panels show the server. Section 2 is empty (no CI), except *SLO Error Burn Rate*. *Application Health* lists every production application |
| **TC-16** | Health window | TC-01, then *15 minutes*, then *7 days* | 15 minutes: CPU and memory reflect *now*; fewer log errors. 7 days: more log groups and older first-seen times; **the first load can take up to a minute** |
| **TC-17** | One service, with callers | Service control = a busy API service (high *Per minute* in *Services of the Application*) | *Upstream*, *Service health* and *Downstream* follow that service. If other services call it over HTTP, *Downstream* and *Business applications impacted* fill |
| **TC-18** | Application control | *(all applications)*, then one application | *Services of the Application* lists every production service, then only that application's services, worst first |
| **TC-19** | Nothing selected | Reset changes | Section 1 fills; section 2 is empty except *SLO Error Burn Rate*; *Application Health* lists every production application; the health panels stay empty |

## C. Behaviour and navigation

| ID | Scenario | Do | Expected |
|---|---|---|---|
| **TC-20** | Links | Click: an incident and a CI in *Active Incidents* / *Escalate*; an application in *Application Health*; a service in *Services of the Application*; the related dashboards | ServiceNow (incident, CI), ServiceNow CMDB (application), APM Service Map (service), and the Applications Operations / Infra dashboards open in a new tab |
| **TC-21** | Time picker has no effect | Change the time picker from 24 hours to 7 days | Nothing changes: every panel has a fixed range or uses the Health window. *SLO Error Burn Rate* is the one to watch: it has no fixed range |
| **TC-22** | Selections are not saved | Pick an incident, reload the page without saving | The dashboard opens on the saved defaults. **More → Reset changes** also clears the selection |
| **TC-23** | Auto-refresh | Leave TC-01 open for 5 minutes | Panels refresh by themselves (*Min. ago* and *Last data* values change) |

## Suggested order for the team demo

1. **TC-01** (done): the full picture on a server.
2. **TC-04 → TC-05:** the most common real case. An application service has no server metrics of its own; one
   server picked from *Server View* brings the health panels back.
3. **TC-06** (business application) and **TC-08** (network device): what to expect from other CI types.
4. **TC-09:** an incident without a CI, and how to recover.
5. **TC-14** and **TC-16:** precedence and the Health window, for the technical audience.
