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

> **Refreshing the values:** incidents close quickly. Re-run **CA** in `queries_ro_run.md` (Round 14, re-run as
> Round 15) before a test session if these no longer appear in the controls — the query itself doesn't change, just
> paste a fresh result. Run CB too for any CI you need confirmed in the Server list.

## Values to use (Round 15, 23 Oct)

Only **CA** was re-run this round (no CB, CC or CD). Most Round 14 picks for cases that need CB/CC/CD still stand,
since those depend on CMDB relationships or non-incident servers, which change far more slowly than incidents —
they're carried forward below and marked *(unverified since 21 Oct)*. Re-run CB/CC/CD if you want those confirmed
too.

| Case | Incident / CI / controls | What to expect from this pick |
|---|---|---|
| **TC-02** | Incident **INC2674667 · kau1p464** (Windows, score 3: metrics + database + Windows services) | *Server*, *Database* and *Process Health* fill. Variant: **INC2673019 · vkau1pwb0003** (same shape, also prod) |
| **TC-03** | Incident **INC2676297 · sch1h020** (AIX, no metrics, database) | *Server Health*: one row, "No data in window". Variant with real middleware names instead of "unknown": **INC2678574 · sch1h628** (`ibm_mq_amqpcsea_positional`, `ibm_mq_amqrmppa_positional`; environment `cut`, doubles as a TC-10 pick) |
| **TC-04** | Incident **INC2667546 · Automated Claim Transaction PROD** (still active since 21 Oct, now 14 open incidents) | Section 2 fills from the CMDB. Health panels empty |
| **TC-05** | TC-04, then Server = **vslrau1p276** *(unverified since 21 Oct)* | The health panels show vslrau1p276, including its APM service. Also in the list: vslrau1p174, vcwau1p0132. Backup: **Enterprise PolicyCenter PROD** (now incident INC2670814) with Server = **vrau1pap0041** |
| **TC-06** | Incident **INC2673785 · CNA Central** (still active, now 4 open incidents) | The only business application with an incident. Pick it in the Application control |
| **TC-07** | Incident **INC2670699 · MSSQLSERVER@kau1p522** (still active) | *Server View* names **kau1p522**, which sends no server metrics, so it is **not in the Server list**: health panels stay empty — a documented limit worth showing. Variants: **INC2676747 · MSSQLSERVER@vkau1pdb0015** (still active), **INC2678417 · MSSQLSERVER@vskau1p945** (new) |
| **TC-08** | Incident **INC2678287 · adc-wan-agg2** (an **IP Switch**, score 1, 3 Netcool alerts) | A real network device this time — *Alerts on this CI* shows its 3 alerts; health panels empty. Variant: **INC2678391 · cuprsp2** (a UPS, 4 alerts) |
| **TC-09** | Incident **INC2677314** (P2, no CI — still active) | Only *Escalate* fills |
| **TC-10** | Incident **INC2667298 · CNA Canada Insurance System DRE** (dre, still active, now 19 open incidents, 5 changes); then **INC2676782 · lrch1d54** (drt, server with metrics, still active) | The CI's panels show; its non-production relationships are hidden. lrch1d54's health panels still fill |
| **TC-11** | CI = **vslrau1p220** (TC-01's server) | Repeats TC-01 through the CI control. Not incident-dependent |
| **TC-12** | CI = **vslrau1p219** *(unverified since 21 Oct — not in today's CA table, so still has no active incident)* | *Escalate* shows one row with the owners. Section 3 fills, as in TC-01 |
| **TC-13** | Incident **INC2674667 · kau1p464**, CI = **Automated Claim Transaction PROD** | Every panel follows kau1p464, the incident's CI, not the CI control |
| **TC-14** | (a) CI = **kau1p464**, Server = **vslrau1p229** *(server unverified since 21 Oct)*. (b) CI = **Automated Claim Transaction PROD**, Server = **vslrau1p229** | (a) The health panels show kau1p464: a server in the CI control wins. (b) They show vslrau1p229 |
| **TC-15** | Server = **vslrau1p229** *(unverified since 21 Oct)* | The health panels fill without an incident or CI |
| **TC-16** | TC-12, then Health window 15 minutes, then 7 days | 7 days: more log groups; the first load can take up to a minute |
| **TC-17** | Service = **juno-data-api** or **eds-data-api** *(traffic figures unverified since 21 Oct)* | *Upstream*, *Service health* and *Downstream* follow it, if it still has callers |
| **TC-18** | Application = **Juno**, then **Agency Bill Pay** *(unverified since 21 Oct)* | *Services of the Application* lists only that application's services |
| **TC-24** | **INC2678126 · CNA1BSYS** (mainframe LPAR, **prod**, 2 incidents, 3 changes — better than 21 Oct's dev pick); **INC2665397 · RightFax** (infrastructure service, still active); **INC2674755 · PRINT OPEN SYSTEMS DAILY JOB LOG** (batch job, still active); **INC2678582 · gnfcnacvtma-01** (Network Appliance Hardware, new, 1 change) | *Escalate* and the CMDB panels only |

**What changed since Round 14 (23 Oct):**
- **TC-08 finally has a real network device:** `adc-wan-agg2`, an IP Switch, with 3 live Netcool alerts — a better
  fit than the UPS workaround from 21 Oct.
- **Most long-running picks held:** the same incidents are still open on *kau1p522* (TC-07), *CNA Central* (TC-06),
  *Automated Claim Transaction PROD* (TC-04), the no-CI P2 (TC-09) and both TC-10 CIs — two days hasn't closed them.
- **TC-02's and TC-24's 21 Oct picks closed** (vkau1pdb0016, m10w3l2gm0a30bm, the old UPS `cumtri1`); replaced above.
- **Still no active incident's CI runs APM services** (CA's `apm` / `services` columns are empty throughout). The
  section 3 dependency panels are only shown through TC-11, TC-12, TC-15 and TC-17.
- **Database metrics are recorded against the SQL instance's name** (`MSSQLSERVER@…`), not the server's, so
  *Database Health* for a picked server may show only its SQL Server Windows service.

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
| **TC-15** | Server control alone | Incident and CI empty; Server = any server | The health panels show the server. Section 2 is empty (no CI). *Application Health* lists every production application |
| **TC-16** | Health window | TC-01, then *15 minutes*, then *7 days* | 15 minutes: CPU and memory reflect *now*; fewer log errors. 7 days: more log groups and older first-seen times; **the first load can take up to a minute** |
| **TC-17** | One service, with callers | Service control = a busy API service (high *Per minute* in *Services of the Application*) | *Upstream*, *Service health* and *Downstream* follow that service. If other services call it over HTTP, *Downstream* fills |
| **TC-18** | Application control | *(all applications)*, then one application | *Services of the Application* lists every production service, then only that application's services, worst first |
| **TC-19** | Nothing selected | Reset changes | Section 1 fills; section 2 is empty; *Application Health* lists every production application; the health panels stay empty |

## C. Behaviour and navigation

| ID | Scenario | Do | Expected |
|---|---|---|---|
| **TC-20** | Links | Click: an incident and a CI in *Active Incidents* / *Escalate*; an application in *Application Health*; a service in *Services of the Application*; the related dashboards | ServiceNow (incident, CI), ServiceNow CMDB (application), APM Service Map (service), and the Applications Operations / Infra dashboards open in a new tab |
| **TC-21** | Time picker has no effect | Change the time picker from 24 hours to 7 days | Nothing changes: every panel has a fixed range or uses the Health window |
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
