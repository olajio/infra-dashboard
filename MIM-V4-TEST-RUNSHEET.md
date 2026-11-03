# MIM V4: test run sheet (values from Rounds 19 and 21, 2 Nov 2026)

These are the exact values to pick in each control, one row per test case. MIM V4 has the same panels as MIM V3,
plus the new section at the bottom, so these values work on either. Background and expected results:
`MIM-V3-TEST-CASES.md`.

**After importing a new version of the dashboard, and before every case:** use **More → Reset changes**. After an
import this also clears Kibana's stale copy of the controls, which can otherwise hide new controls such as *Monitored
application*. Everything then goes back to its default:

| Control | Default |
|---|---|
| Incident (pinned, top) | `(all incidents)` |
| CI (pinned, top) | `(no CI selected)` |
| Server (section 3) | `(no server selected)` |
| Health window (section 3) | `24 hours` |
| Service (section 3) | `(services on this CI)` |
| Application (section 3) | `(all applications)` |
| Monitored application (pinned, top) | `(all monitored applications)` |

In the tables, **—** means leave that control at its default. Pick values in the order of the columns, left to right.

**Typing in a control:** the Incident control lists entries as `INC number · CI name`. Type the INC number and pick
the match. **If an incident is missing from the list,** set the time picker to *Last 30 days* and look again. The
time picker changes no panel (TC-21), only what the list may offer. If it is still missing, the incident has
closed since 2 Nov. Use the variant in the last column.

## Fill the most panels: three combinations (Round 21, 2 Nov)

No CI has everything at once: the servers with APM services have no incident, change or alert this week, and the
CIs with changes or alerts are not servers. These three combinations together fill every panel. **Reset changes**
before each one.

| # | Set these controls | Panels it fills |
|---|---|---|
| **1** Server deep dive | CI = `vslrau1p338`; Health window = `7 days` | Section 2: *Escalate* (owners), *Server View*, *Applications related*, *Blast radius*, *Middleware View*. Section 3: *Server Health*, *APM Services Health* (agency-api, bond-api, corp-data-api …), *Middleware Health* and *Process Health* (JBoss), *Service health*, *Upstream*, *Downstream*, *Errors from the Logs*, *Application Health*. Backups: `vslrau1p337`, `vrau1pap0041` |
| **2** Incident with changes | Incident = `INC2685011 · Data Lake PROD`; then Server = `vslrau1p338`; Application = `CNA PolicyCenter`; Service = `rst-api` | Section 1; *Escalate*; *Changes in the Last 7 Days* (13 changes); the CMDB panels; the health panels (from the Server control); *Services of the Application*; *Service health*, *Upstream*, *Downstream* (rst-api). Backup incident: `INC2685206 · Power BI PROD` (8 changes) |
| **3** Alerts | CI = `adc-wan-agg1` (4 Netcool alerts), or Incident = `INC2685121 · cuwash1` (In Progress, 1 alert) | *Alerts on this CI*, *Escalate* |

Section 1 (tiles, *Active Incidents*, *Time to Resolve*, *Open Alerts with No Incident*) fills with nothing selected.

## The incident's CI (section A)

| Case | Incident | CI | Server | Other controls | Variant if the first pick is gone | Screenshot |
|---|---|---|---|---|---|---|
| **TC-02** Server with metrics, no APM | `INC2684835 · vskau1p1277` | — | — | — | `INC2683913 · kau1p464`; or, with no incident, CI = `kau1p802` (Windows, SQL Server, 1 change) | Section 2 *Escalate*; section 3 *Server*, *Database* and *Process Health* |
| **TC-03** Server with no metrics | `INC2684506 · kw3l1p714` | — | — | — | `INC2684495 · kw3l1p713` | *Server Health* showing "No data in window" |
| **TC-04** Application service | `INC2676704 · Automated Claim Transaction PROD` | — | — | — | `INC2685169 · Automated Claim Transaction PROD` (newer, On Hold), or `INC2677984 · Europe Underwriter Desktop PROD` | Section 2: *Applications related*, *Blast radius*, *Server View* (note its servers for TC-05); empty health panels |
| **TC-05** App service + a server | `INC2676704 · Automated Claim Transaction PROD` | — | `vslrau1p276` (confirmed 2 Nov: sends metrics and runs `clmact`, the Automated Claim Transaction service) | — | Any server listed in TC-04's *Server View* that is also in the Server list | Health panels now showing that server |
| **TC-06** Business application | `INC2677598 · CNA Central` | — | — | Application = `CNA Central` if listed | — | *Application Health*; *Services of the Application* |
| **TC-07** SQL Server instance | `INC2684839 · MSSQLSERVER@vskau1p1033` | — | — | — | `INC2684587 · MSSQLSERVER@vskau1p945`, `INC2684399 · MSSQLSERVER@kw3l1p237` | *Server View* naming **vskau1p1033**. Then also set Server = `vskau1p1033` (if listed) and capture the health panels |
| **TC-08** Network device | `INC2684277 · sdc-core-sw2` | — | — | — | `INC2685121 · cuwash1` (In Progress, 1 alert); or, with no incident, CI = `adc-wan-agg1` (4 alerts) | *Alerts on this CI* (9 Netcool alerts); *Escalate* |
| **TC-09** No CI | `INC2684997 · (no CI)` | — | — | — | Any other `· (no CI)` entry | *Escalate* filled, the rest empty |
| **TC-10a** Non-production app service | `INC2678694 · CNA Canada Insurance System DRE` | — | — | — | — | *Escalate* (Env = dre); related tables with no non-production rows |
| **TC-10b** Non-production server | `INC2683481 · vclch1d0205d` | — | — | — | `INC2684847 · vslrch1d363` | Health panels filled (dre server) |
| **TC-24** Other CI classes, one run each | ① `INC2684435 · CNA1BSYS` ② `INC2680061 · SSL/VPN` ③ `INC2673853 · HARDY TandemAcumen Rec Report` ④ `INC2684990 · adc-f5apm-02` | — | — | — | — | *Escalate* and the CMDB panels, one screenshot per pick |

## The controls (section B)

| Case | Incident | CI | Server | Other controls | Screenshot |
|---|---|---|---|---|---|
| **TC-11** CI control instead of an incident | — | `vslrau1p220` | — | — | Same panels as TC-01 |
| **TC-12** CI with no active incident | — | `vslrau1p219` (confirmed 2 Nov: metrics, 2 APM services, no incident) | — | — | *Escalate*: one row with the CI's owners; health panels filled |
| **TC-13** The incident wins over the CI | `INC2684835 · vskau1p1277` | `Automated Claim Transaction PROD` | — | — | Panels showing **vskau1p1277**, not the application service |
| **TC-14a** A server in the CI control wins | — | `vskau1p1277` | `vslrau1p301` | — | Health panels showing **vskau1p1277** |
| **TC-14b** App service in CI, Server used | — | `Automated Claim Transaction PROD` | `vslrau1p338` | — | Health panels showing **vslrau1p338** |
| **TC-15** Server control alone | — | — | `vslrau1p338` | — | Health panels filled, including 4 APM services; section 2 empty |
| **TC-16** Health window | — | `vslrau1p338` (or `vslrau1p219`) | — | Health window = `15 minutes`, then `7 days` | One screenshot per window: CPU / memory and *Errors from the Logs* (7 days can take a minute) |
| **TC-17** One service | — | — | — | Service = `rst-api` (Risk Support Tool: calls 23 services, busy all hour). Backups: `dmf`, `blport-webapp` | *Upstream*, *Service health*, *Downstream* |
| **TC-18** Application control | — | — | — | Application = `CNA PolicyCenter` (13 production services, the most), then `Juno` (10). Backup: `Claim ECM` (9) | *Services of the Application* for each |
| **TC-19** Nothing selected | — | — | — | — (after Reset changes) | Section 1 filled; section 2 empty; *Application Health* listing every application |

## Behaviour and navigation (section C)

| Case | What to do | Screenshot |
|---|---|---|
| **TC-20** Links | Incident `INC2684835 · vskau1p1277`. Click the incident and the CI in *Escalate*; an application in *Application Health*; a service in *Services of the Application*; both links in *4 · Related dashboards* | Each page that opens in a new tab |
| **TC-21** Time picker has no effect | Nothing picked. Change the time picker from *Last 7 days* to *Last 24 hours* | Before and after: section 1 numbers unchanged (only the new section at the bottom follows the picker) |
| **TC-22** Selections aren't saved | Pick `INC2684835 · vskau1p1277`, then reload the page without saving | The dashboard back on `(all incidents)` |
| **TC-23** Auto-refresh | TC-11, then wait 5 minutes | *Min. ago* / *Last data* values before and after |

## Added for the current version (section D)

| Case | Incident | CI | Other controls | Expected | Screenshot |
|---|---|---|---|---|---|
| **TC-25** Monitored application control | — | — | Monitored application = `(all monitored applications)`, then `Claim Center`, then `Juno` | *Application Health* and *Services of the Application* show only the applications in `cmdb_with_apm_flag` that are In Production, Operational and monitored (138 on 2 Nov), then only the one picked. Applications with no APM data yet are listed last as *Enrolled — no telemetry yet*. The section 3 Application and Service lists offer only those applications' services | *Application Health* and *Services of the Application* for each value |
| **TC-26a** SLA breached | — | — | — | *Active Incidents* row **INC2680236** (Claim Financial Interface PROD) shows **Breached**. **Run this by about 05:00 UTC on 3 Nov**: after that it is older than 7 days and leaves the table | That row |
| **TC-26b** SLA not breached | — | — | — | Row **INC2684181** (Claim Center PROD) shows Breaching / Paused / Within SLA / Met; row **INC2684312** shows **No SLA record** | Those rows |
| **TC-27** On Hold left out | First nothing; then `INC2684277 · sdc-core-sw2` | — | — | With nothing picked, INC2684277 (P2, On Hold, 68 h) is **not** in *Active Incidents* or the *P2 over 8 h* tile. Once picked, it shows in *Escalate* | Section 1 without it; *Escalate* with it |
| **TC-28** Tiles match the table | — | — | — | Active P1 = P1 rows in *Active Incidents*; P2 over 8 h = P2 rows; P3 over 24 h = P3 rows | Tiles and table in one screenshot |

Round 21 (2 Nov) confirmed the servers: vslrau1p338, vslrau1p219, vslrau1p220 and vslrau1p276 send metrics and run APM
services. TC-17 / TC-18 use RD2 and RD3. Use each row's fallback if a value isn't in the list.
