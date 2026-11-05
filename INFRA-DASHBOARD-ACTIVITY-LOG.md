# Infrastructure Dashboard: activity log

Work done since the KPIs were defined on 28 Oct 2026. **KPI #** is the row number on the *KPIs* sheet of
`INFRA-DASHBOARD-KPIS.xlsx`. The same list is on that workbook's *Activity log* sheet.

| Date | Activity | KPI # | Status |
|---|---|---|---|
| 28 Oct | Assessed all 16 KPIs from `dashboard_kpis.txt`: what is achievable now, partly or not yet, and why | All | Done |
| 28 Oct | Built the Infrastructure Dashboard, driven by the CI control: 3 sections reusing MIM's tested panels. Placeholder cards explain each KPI not yet possible | 1–16 | Done |
| 28 Oct | Created the KPI status workbook (`INFRA-DASHBOARD-KPIS.xlsx`) and the investigation queries (`dashboard_queries.md`) | All | Done |
| 28 Oct | Built the automated test: every panel query, with and without a CI (`tools/test_infra_dashboard_2026-10-28.py`) | All | Done |
| 29 Oct | Added the Telemetry control and *Enrolled — no telemetry yet* applications to *Application Health* (via MIM V3) | 15 | Superseded on 3 Nov |
| 2 Nov | Investigated VMware (Round 17): one vSphere cluster collected (4 ESXi hosts, 46 VMs), no CMDB link. Needs the vSphere integration extended | 10 | Done (blocked) |
| 2 Nov | Investigated Elastic infrastructure alerts (Round 17b): the paladin-* rules and how alerts name their server | 4 | Done |
| 2 Nov | **Built the *Elastic infra alerts* panel** in place of its placeholder: alerts on the CI, or every active paladin alert with no CI | 4 | Done |
| 2 Nov | Investigated GCP (Rounds 17c, 17d): what is collected, its health metrics, and which names match the CMDB. 4 of 5 GKE clusters match; Cloud SQL and buckets do not | 11 | Done |
| 2 Nov | **Built the *Cloud health · GKE* panel** in place of the Cloud placeholder: one row per cluster (status, nodes, CPU, memory, restarts), following the CI | 11 | Done (GKE part) |
| 2 Nov | Fixed GKE memory (used ÷ allocatable bytes) and restart counting after the Round 20 checks | 11 | Done |
| 3 Nov | **Added the *Monitored application* control** (top bar): the application panels show only the 138 In Production, Operational and monitored applications. Removed the Telemetry control; the dashboard is now built from MIM V4 | 15, 16 | Done |
| 3 Nov | Wrote the **user manual** with five demo scenes (`INFRA-DASHBOARD-MANUAL.md`) | All | Done |
| 4 Nov | Made the controls hard to miss: icons in the control titles, three numbered "Start here" banners, full-width top-bar controls | All | Done |
| 5 Nov | Fixed GKE memory after check CG7: node memory is split into evictable and non-evictable; *Mem peak* now counts non-evictable only | 11 | Done |
| 5 Nov | **Gave the dashboard the MIM V5 look:** tile icons (green at 0), section icons, row numbers; new *Active Elastic infra alerts* tile | 1, 4 | Done |
| 5 Nov | **Added section 4 *Detailed dashboards*:** links to the Server, Database, Middleware, VMware and Cloud infra dashboards | 6–11 | Done |
| 5 Nov | **Added the Incident control** (top bar), as on MIM: a picked incident selects its CI. *Incidents on this CI* became **Active P1 and P2 incidents** (MIM's Active Incidents table). Built on the team's layout (`infra2.ndjson`) | 1, 2 | Done |

## KPI status now

- **Achievable (10):** #1 CI control, #2 P1/P2 counts, #4 Elastic infra alerts, #5 Incidents table, #6 Changes table,
  #7 Server health, #13 Process health, #14 Applications related, #15 Application health, #16 Service health.
- **Partly achievable (3):** #8 Database health (SQL Server is matched by instance name; Oracle and Db2 are collected
  under the collector's host name, not per server), #9 Middleware health, #11 Cloud health (GKE built; Cloud SQL
  blocked because the collected databases are not in the CMDB).
- **Not achievable yet (3):** #3 User impact (waiting for the ServiceNow user base and RUM integrations), #10 VMware
  health (only one vSphere cluster collected), #12 Custom integration health (needs a definition).

## Still open

- Test the five demo scenes on the dashboard (`INFRA-DASHBOARD-MANUAL.md`).
- Cloud health (#11): Cloud SQL stays blocked until the CMDB and the GCP collection cover the same databases (CG7
  done 5 Nov).
- Custom integration health (#12): define which integrations count and what "healthy" means.
- User impact (#3): waiting for the ServiceNow user base and RUM integrations.
- VMware health (#10): waiting for the vSphere integration to cover the main vCenters.
