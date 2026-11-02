# MIM V4: test run sheet (values from Round 19, 2 Nov 2026)

These are the exact values to pick in each control, one row per test case. MIM V4 has the same panels as MIM V3,
plus the new section at the bottom, so these values work on either. Background and expected results:
`MIM-V3-TEST-CASES.md`.

**Before every case:** use **More → Reset changes**. Everything then goes back to its default:

| Control | Default |
|---|---|
| Incident (pinned, top) | `(all incidents)` |
| CI (pinned, top) | `(no CI selected)` |
| Server (section 3) | `(no server selected)` |
| Health window (section 3) | `24 hours` |
| Service (section 3) | `(services on this CI)` |
| Application (section 3) | `(all applications)` |
| Telemetry (section 3) | `(all applications)` |

In the tables, **—** means leave that control at its default. Pick values in the order of the columns, left to right.

**Typing in a control:** the Incident control lists entries as `INC number · CI name`. Type the INC number and pick
the match. **If an incident is missing from the list,** set the time picker to *Last 30 days* and look again. The
time picker changes no panel (TC-21), only what the list may offer. If it is still missing, the incident has
closed since 2 Nov. Use the variant in the last column.

## The incident's CI (section A)

| Case | Incident | CI | Server | Other controls | Variant if the first pick is gone | Screenshot |
|---|---|---|---|---|---|---|
| **TC-02** Server with metrics, no APM | `INC2684835 · vskau1p1277` | — | — | — | `INC2683913 · kau1p464` | Section 2 *Escalate*; section 3 *Server*, *Database* and *Process Health* |
| **TC-03** Server with no metrics | `INC2684506 · kw3l1p714` | — | — | — | `INC2684495 · kw3l1p713` | *Server Health* showing "No data in window" |
| **TC-04** Application service | `INC2676704 · Automated Claim Transaction PROD` | — | — | — | `INC2677984 · Europe Underwriter Desktop PROD` | Section 2: *Applications related*, *Blast radius*, *Server View* (note its servers for TC-05); empty health panels |
| **TC-05** App service + a server | `INC2676704 · Automated Claim Transaction PROD` | — | `vslrau1p276` | — | Any server listed in TC-04's *Server View* that is also in the Server list | Health panels now showing that server |
| **TC-06** Business application | `INC2677598 · CNA Central` | — | — | Application = `CNA Central` if listed | — | *Application Health*; *Services of the Application* |
| **TC-07** SQL Server instance | `INC2684839 · MSSQLSERVER@vskau1p1033` | — | — | — | `INC2684587 · MSSQLSERVER@vskau1p945`, `INC2684399 · MSSQLSERVER@kw3l1p237` | *Server View* naming **vskau1p1033**. Then also set Server = `vskau1p1033` (if listed) and capture the health panels |
| **TC-08** Network device | `INC2684277 · sdc-core-sw2` | — | — | — | `INC2684990 · adc-f5apm-02` (no alerts) | *Alerts on this CI* (9 Netcool alerts); *Escalate* |
| **TC-09** No CI | `INC2684997 · (no CI)` | — | — | — | Any other `· (no CI)` entry | *Escalate* filled, the rest empty |
| **TC-10a** Non-production app service | `INC2678694 · CNA Canada Insurance System DRE` | — | — | — | — | *Escalate* (Env = dre); related tables with no non-production rows |
| **TC-10b** Non-production server | `INC2683481 · vclch1d0205d` | — | — | — | `INC2684847 · vslrch1d363` | Health panels filled (dre server) |
| **TC-24** Other CI classes, one run each | ① `INC2684435 · CNA1BSYS` ② `INC2680061 · SSL/VPN` ③ `INC2673853 · HARDY TandemAcumen Rec Report` ④ `INC2684990 · adc-f5apm-02` | — | — | — | — | *Escalate* and the CMDB panels, one screenshot per pick |

## The controls (section B)

| Case | Incident | CI | Server | Other controls | Screenshot |
|---|---|---|---|---|---|
| **TC-11** CI control instead of an incident | — | `vslrau1p220` | — | — | Same panels as TC-01 |
| **TC-12** CI with no active incident | — | `vslrau1p219` (if not listed: `vslrau1p220`) | — | — | *Escalate*: one row with the CI's owners; health panels filled |
| **TC-13** The incident wins over the CI | `INC2684835 · vskau1p1277` | `Automated Claim Transaction PROD` | — | — | Panels showing **vskau1p1277**, not the application service |
| **TC-14a** A server in the CI control wins | — | `vskau1p1277` | `vslrau1p301` | — | Health panels showing **vskau1p1277** |
| **TC-14b** App service in CI, Server used | — | `Automated Claim Transaction PROD` | `vslrau1p301` | — | Health panels showing **vslrau1p301** |
| **TC-15** Server control alone | — | — | `vslrau1p301` | — | Health panels filled; section 2 empty |
| **TC-16** Health window | — | `vslrau1p219` (or `vslrau1p220`) | — | Health window = `15 minutes`, then `7 days` | One screenshot per window: CPU / memory and *Errors from the Logs* (7 days can take a minute) |
| **TC-17** One service | — | — | — | Service = `rst-api` (Risk Support Tool: calls 23 services, busy all hour). Backups: `dmf`, `blport-webapp` | *Upstream*, *Service health*, *Downstream* |
| **TC-18** Application control | — | — | — | Application = `Risk Support Tool`, then `Claim ECM` (4 busy services). Backup: `Enterprise Content Service 2.0` | *Services of the Application* for each |
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
| **TC-25** Telemetry control | — | — then `vslrau1p220` | Telemetry = `Enrolled, no telemetry yet` | *Application Health* lists only applications marked *Enrolled — no telemetry yet* (41 on 2 Nov, e.g. Claim Center, Data Lake, Adobe Experience Manager, Wage Calculator), with or without a CI | *Application Health*, both times |
| **TC-26a** SLA breached | — | — | — | *Active Incidents* row **INC2680236** (Claim Financial Interface PROD) shows **Breached**. **Run this by about 05:00 UTC on 3 Nov**: after that it is older than 7 days and leaves the table | That row |
| **TC-26b** SLA not breached | — | — | — | Row **INC2684181** (Claim Center PROD) shows Breaching / Paused / Within SLA / Met; row **INC2684312** shows **No SLA record** | Those rows |
| **TC-27** On Hold left out | First nothing; then `INC2684277 · sdc-core-sw2` | — | — | With nothing picked, INC2684277 (P2, On Hold, 68 h) is **not** in *Active Incidents* or the *P2 over 8 h* tile. Once picked, it shows in *Escalate* | Section 1 without it; *Escalate* with it |
| **TC-28** Tiles match the table | — | — | — | Active P1 = P1 rows in *Active Incidents*; P2 over 8 h = P2 rows; P3 over 24 h = P3 rows | Tiles and table in one screenshot |

**Not covered by Round 19** (values carried over from 21 Oct): the TC-05 server and TC-12's vslrau1p219.
TC-17 / TC-18 use Round 21 (RD2, 2 Nov). Use each row's fallback if a value isn't in the list.
