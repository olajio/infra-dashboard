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

## Values to use (Round 13, 20 Oct)

Incidents change: if one is no longer listed in the Incident control, take another example from `round13.txt` for
the same class.

| Case | Pick | Why this one |
|---|---|---|
| TC-02 | Incident **INC2665383 · vskau1p945** | Windows server with metrics; Round 12 also found a database, Windows services and a change on it, so *Database Health*, *Process Health* and *Changes* fill too |
| TC-03 | Incident **INC2675141 · sau1h670** | AIX server, no server metrics; has MQ processes, a change and a ping monitor |
| TC-04 | Incident **INC2658097 · Claim Center PROD** | Mapped application service with a large CMDB footprint (about 160 linked servers) |
| TC-05 | TC-04, then Server = a server from *Server View* that is also in the Server control's list (e.g. `vclau1p0236`) | Only servers that send metrics are in the Server list; type to check |
| TC-06 | Incident **INC2673785 · CNA Central** | The only business application with an active incident. *Application Health* shows it only if its APM services carry that exact name |
| TC-07 | Incident **INC2670699 · MSSQLSERVER@kau1p522**, then Server = `kau1p522` | SQL Server instance; its server's name is in the CI name. Also: *agenp@sau1h688* (Oracle), *conjur-port-@vslrau1p254* (PostgreSQL) |
| TC-08 | **No candidate today**: no network device has an active incident | Re-run BZ later. The CI control can't help: it only lists CIs with an incident in the last 31 days, plus servers |
| TC-09 | Incident **INC2657347 · (no CI)** | One of 154 active incidents without a CI |
| TC-10 | Incident **INC2667298 · CNA Canada Insurance System DRE**; then **INC2670363 · vkau1rdb0003** | A DR application service; then a DR Windows server with metrics. The server's health still shows, although the Server list leaves out non-production servers |
| TC-11 | CI = `vslrau1p220` | TC-01's server. Its incident INC2676403 is no longer active, so this is now the way to repeat TC-01 |
| TC-12 | CI = `vslrau1p276` (or any server with no open incident) | *Escalate* should still show its owners |
| TC-13 | Incident INC2665383; CI = `Claim Center PROD` | The incident's server (vskau1p945) must win |
| TC-14 | (a) CI = `vskau1p945`, Server = `vslrau1p276` → health panels show vskau1p945. (b) CI = `Claim Center PROD`, Server = `vslrau1p276` → they show vslrau1p276 | |
| TC-15 | Server = `vslrau1p220` | Health panels without any incident or CI |
| TC-17 | Service = `fmrsmartapp` (busiest service in TC-01) or any high-traffic API service | |
| TC-24 | Optional, other CI classes: **INC2676850 · CNA1BSYS** (mainframe LPAR), **INC2665397 · RightFax** (infrastructure service), **INC2674755 · PRINT OPEN SYSTEMS DAILY JOB LOG** (batch job), **INC2668705 · pubsub_data_view** (cloud database) | Expect the CMDB panels and *Escalate* only; no health data |

**What Round 13 shows about today's incidents:**
- **No active incident's CI runs APM services** (`with_apm` = 0 everywhere). So, picked through an incident,
  *Upstream*, *Service health*, *Downstream* and *Business applications impacted* stay empty. Use TC-11
  (vslrau1p220) or TC-17 to demo them.
- **Most incidents are on application services** (Mapped, Calculated, Tag-based, Service Instance: about 300 of 529).
  So TC-04 / TC-05 is the everyday case.
- **154 active incidents (29 %) have no CI.** The dashboard can't investigate those until the CI is filled in
  ServiceNow, a data-quality point for the team.

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
| **TC-24** | Other CI classes (mainframe LPAR, infrastructure service, batch job, cloud database) | Open an incident on such a CI (see the values table) | *Escalate* and the CMDB panels fill; the health panels stay empty, as these CIs send no server data |

## Suggested order for the team demo

1. **TC-01** (done): the full picture on a server.
2. **TC-04 → TC-05:** the most common real case. An application service has no server metrics of its own; one
   server picked from *Server View* brings the health panels back.
3. **TC-06** (business application) and **TC-08** (network device): what to expect from other CI types.
4. **TC-09:** an incident without a CI, and how to recover.
5. **TC-14** and **TC-16:** precedence and the Health window, for the technical audience.
