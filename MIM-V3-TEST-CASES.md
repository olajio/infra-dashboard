# MIM V3 — test cases (20 Oct 2026)

**Exact control values for each case: `MIM-V4-TEST-RUNSHEET.md`.**

TC-01 is done: *MIM-V3-TEST-CASE-INC2676403.md* (a server CI with APM). This catalog covers every other kind of CI
and every control combination.

**Finding values:** run **BZ** in `queries_ro_run.md` (Round 13, Dev Tools). It lists the active incidents by CI
class, with up to 3 examples per class. Each example is tagged:
- `[metrics]`: the CI sends server metrics;
- `[APM]`: it runs production APM services;
- `[dre]`, `[cut]` …: a non-production environment.

**Defaults unless a case says otherwise:** Health window *24 hours*, Service *(services on this CI)*, Application
*(all applications)*, CI and Server controls empty. Use **More → Reset changes** between cases.

> **Refreshing the values:** incidents close quickly. Run **Round 19** in `queries_ro_run.md` (CA2, plus CB / CC / CD,
> SL, OH, TL) before a test session. Since 25–27 Oct, *Escalate* and section 1 only show incidents opened in the last
> 7 days, and section 1 leaves On Hold incidents out: pick incidents with `newest_days` ≤ 6 in CA2, and not On Hold
> for anything checked in section 1.

## Values to use (Round 19, 2 Nov)

From `round19.txt`: CA2, SL, OH and TL were run. CB, CC and CD were not, so the TC-05, TC-12, TC-17 and TC-18 server
and service picks are carried forward and marked *(unverified)*. **Test soon:** the 7-day window drops incidents every
day. INC2680236, the TC-26 pick, leaves *Escalate* and section 1 about 17 h after this run.

**Picking an incident:** CA2 shows each CI's *oldest* active incident. For a CI with several incidents, type the CI
name into the **Incident** control and pick the newest. Incidents **On Hold** show in the Incident control and in
*Escalate*, but not in section 1 (that is TC-27).

| Case | Incident / CI / controls | What to expect from this pick |
|---|---|---|
| **TC-02** | Incident **INC2684835 · vskau1p1277** (Windows, prod, In Progress, score 3: metrics + database + Windows services) | *Server*, *Database* and *Process Health* fill. Variant: **INC2683913 · kau1p464** (the Round 15 server, new incident, On Hold) |
| **TC-03** | Incident **INC2684506 · kw3l1p714** (Windows Server, prod, **no metrics**) | *Server Health*: one row, "No data in window". No AIX server has an active incident now. Variant: **INC2684495 · kw3l1p713** |
| **TC-04** | Incident on **Automated Claim Transaction PROD** (14 open incidents, newest 2 days old, 1 change) | Section 2 fills from the CMDB. Health panels empty. Variant: **Europe Underwriter Desktop PROD** (12 incidents, one opened today, 9 changes) |
| **TC-05** | TC-04, then Server = **vslrau1p276** *(unverified)* | The health panels show that server. If it isn't listed in *Server View*, pick any server shown there |
| **TC-06** | Incident on **CNA Central** (Business Application, 5 open incidents, newest 2 days old) | Still the only business application with an incident. Pick it in the Application control |
| **TC-07** | Incident **INC2684839 · MSSQLSERVER@vskau1p1033** (prod, opened today) | *Server View* names **vskau1p1033**. Variants: **INC2684587 · MSSQLSERVER@vskau1p945**, **INC2684399 · MSSQLSERVER@kw3l1p237**. The kau1p522 incident is 24 days old, outside *Escalate* |
| **TC-08** | Incident **INC2684277 · sdc-core-sw2** (IP Switch, **P2**, **9** Netcool alerts, On Hold) | *Alerts on this CI* shows its 9 alerts; health panels empty. It is On Hold, so it is not in *Active Incidents*. Variant: **INC2684990 · adc-f5apm-02** (F5 BIG-IP, In Progress, no alerts) |
| **TC-09** | Incident **INC2684997 · (no CI)** (P3, In Progress) | Only *Escalate* fills. The no-CI P2 from Round 15 has closed. 152 of the 283 CA2 rows have no CI |
| **TC-10** | Incident on **CNA Canada Insurance System DRE** (dre, 8 incidents, 3 changes); then **INC2683481 · vclch1d0205d** (dre server with metrics and WebSphere) | The CI's panels show; its non-production relationships are hidden. vclch1d0205d's health panels fill. Variant: **INC2684847 · vslrch1d363** (drt) |
| **TC-11** | CI = **vslrau1p220** (TC-01's server) | Repeats TC-01 through the CI control |
| **TC-12** | CI = **vslrau1p219** *(unverified; it has no active incident in CA2)* | *Escalate* shows one row with the owners. Section 3 fills, as in TC-01 |
| **TC-13** | Incident **INC2684835 · vskau1p1277**, CI = **Automated Claim Transaction PROD** | Every panel follows vskau1p1277, the incident's CI, not the CI control |
| **TC-14** | (a) CI = **vskau1p1277**, Server = **vslrau1p301**. (b) CI = **Automated Claim Transaction PROD**, Server = **vslrau1p301** | (a) The health panels show vskau1p1277: a server in the CI control wins. (b) They show vslrau1p301 (Linux, sends metrics, active incident INC2684312) |
| **TC-15** | Server = **vslrau1p301** | The health panels fill without an incident or CI |
| **TC-16** | TC-12, then Health window 15 minutes, then 7 days | 7 days: more log groups; the first load can take up to a minute |
| **TC-17** | Service = **juno-data-api** or **eds-data-api** *(unverified)* | *Upstream*, *Service health* and *Downstream* follow it, if it still has callers |
| **TC-18** | Application = **Juno**, then **Agency Bill Pay** *(unverified)* | *Services of the Application* lists only that application's services |
| **TC-24** | **INC2684435 · CNA1BSYS** (mainframe LPAR, prod, 4 changes); **SSL/VPN** (infrastructure service, 5 incidents, one opened today); **INC2673853 · HARDY TandemAcumen Rec Report** (batch job, dev, In Progress); **INC2684990 · adc-f5apm-02** (F5 BIG-IP) | *Escalate* and the CMDB panels only. The only Cloud DataBase incident (pubsub_data_view) is 28 days old, outside *Escalate* |
| **TC-25** | Monitored application = `(all monitored applications)`, then `Claim Center` | Since 3 Nov (patch 03w) the Telemetry control is replaced by the top-bar *Monitored application* control: 138 applications on 2 Nov (In Production, Operational, monitored in `cmdb_with_apm_flag`) |
| **TC-26** | **INC2680236 · Claim Financial Interface PROD** (P3, 2 SLA records, 1 breached); **INC2684181 · Claim Center PROD** (P3, 2 SLA records, none breached) | The first shows **Breached**. If it shows another status, its latest SLA record is the unbreached one. The second shows Breaching / Paused / Within SLA / Met. Any other row, e.g. INC2684312, shows **No SLA record**. Only 6 active incidents have an SLA record |
| **TC-27** | **INC2684277 · sdc-core-sw2** (P2 On Hold, 68 h) or **INC2684604 · vclau1p0147** (P2 On Hold, 33 h) | Both are P2s over 8 h, but neither appears in *Active Incidents* or the *P2 over 8 h* tile. Picking either in the Incident control still fills *Escalate*. 20 On Hold P2s were opened in the last 7 days, 16 of them on vslrau1p001 / vslrau1p105 |
| **TC-28** | Nothing picked | Count the P1, P2 and P3 rows in *Active Incidents* and compare them with the three tiles |

**What changed since Round 15 (23 Oct):**
- **Most 23 Oct incidents closed or fell out of the 7-day window.** TC-02, 03, 07, 08, 09 and 24 have new picks.
  The TC-04, 06 and 10 CIs still have active incidents.
- **On Hold is common:** 91 of the 152 no-CI rows and most server rows are On Hold. They suit TC-27, but not checks in
  section 1.
- **Still no active incident's CI runs APM services**, so the section 3 dependency panels are only shown through
  TC-11, TC-12, TC-15 and TC-17.

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

## D. Added for the current MIM V3 (3 Nov 2026)

| ID | Scenario | Pick | Expected |
|---|---|---|---|
| **TC-25** | Monitored application control (top bar, since 3 Nov) | *(all monitored applications)*, then one application | *Application Health*, *Services of the Application* and the section 3 Application / Service lists show only applications in `cmdb_with_apm_flag` that are In Production, Operational and monitored, then only the one picked. Those with no APM data yet are listed last as *Enrolled — no telemetry yet* |
| **TC-26** | SLA column from ServiceNow's breach flag | An incident from **SL** with `breached` > 0 and `in_table` = yes, and one with `breached` = 0 | The first shows **Breached** in *Active Incidents*; the second Breaching / Paused / Within SLA / Met. An incident not in SL shows **No SLA record** |
| **TC-27** | On Hold left out of section 1 | An incident from **OH** | It is **not** in *Active Incidents*, not counted in the Active P1 / P2 over 8 h / P3 over 24 h tiles, and not in the Time to Resolve graph; it still appears in the Incident control and in *Escalate* when picked |
| **TC-28** | Tiles match the table | Section 1, nothing picked | Active P1 = the number of P1 rows in *Active Incidents*; P2 over 8 h = its P2 rows; P3 over 24 h = its P3 rows |

## Suggested order for the team demo

1. **TC-01** (done): the full picture on a server.
2. **TC-04 → TC-05:** the most common real case. An application service has no server metrics of its own; one
   server picked from *Server View* brings the health panels back.
3. **TC-06** (business application) and **TC-08** (network device): what to expect from other CI types.
4. **TC-09:** an incident without a CI, and how to recover.
5. **TC-14** and **TC-16:** precedence and the Health window, for the technical audience.
