# Action tracker: 3–4 Nov 2026

Actions completed on 3 and 4 Nov, for the action tracker spreadsheet. MIM and the Infrastructure Dashboard are
listed separately.

## MIM dashboard

| Date | Action | Dashboard | Status | Evidence |
|---|---|---|---|---|
| 3 Nov | Documented test cases TC-02 (server with metrics, no APM: vskau1p1277, disk 95.6 % full) and TC-03 (server with no metrics: kw3l1p714, unreachable) in the TC01 format | MIM V4 | Done (both Pass) | `MIM Test Case TC02.docx`, `MIM Test Case TC03.docx` |
| 3 Nov | Added the **Monitored application** control (top bar): the application panels show only the applications in `cmdb_with_apm_flag` that are In Production, Operational and monitored (138). Removed the Telemetry control | MIM V4 | Done | Patch 03w, test `test_mim_v4_2026-11-03w.py` |
| 3 Nov | Removed the colleague's "New collapsible section" | MIM V4 | Done | Patch 03x |
| 3 Nov | Diagnosed the missing Monitored application control and "Unknown query parameter" errors: Kibana reapplies stale unsaved changes after an import. Fix: More → Reset changes. Documented as a standard step | MIM V4 | Done | `tools/README.md`, run sheet |
| 3 Nov | Tested whether the section 3 Application list can follow the top Monitored application pick: supported in Kibana 9.5.3. Wrote it up for the team | MIM V4 | Done | `MIM-V4-CONTROLS.md` |
| 3 Nov | Found the inputs that fill the most panels (Rounds 21–22: servers, services, applications, and application services linked to APM servers), and wrote **demo scenes** driven by the CI control. eFile fills 17 of 20 panels | MIM V4 | Done | `MIM-V4-TEST-RUNSHEET.md`, `queries_ro_run.md` |
| 3 Nov | Built **MIM V5** with a new look, as a separate dashboard. Portfolio-style KPI tiles with icons (green at 0); new tiles *Needs attention now* and *Open alerts, no incident*; section icons; row numbers. Every MIM V4 query kept | MIM V5 | Done | `MIM V5.ndjson`, `tools/build_mim_v5.py` |
| 3 Nov | Made previews of two more MIM V5 ideas: *CI at a glance* tiles and an *application health distribution* bar | MIM V5 | Waiting for a decision | Preview screenshots |
| 4 Nov | Team decision recorded: the section 3 Application list stays as is (option B) | MIM V4 / V5 | Done | `MIM-V4-CONTROLS.md` |
| 4 Nov | Applied new_suggestions2.txt to the team's MIM V5 layout. **Escalate:** State and Opened added, CI support group removed. **Active Incidents:** Opened added. **Open Alerts with No Incident:** only the picked CI's and its CMDB-linked CIs' alerts | MIM V5 | Done | Patch 04a, test `test_mim_v5_2026-11-04a.py` |
| 4 Nov | Made the controls hard to miss: icons in the control titles, numbered "Start here" banners, full-width top-bar controls | MIM V5 | Done | Patch 04a |
| 4 Nov | Explained where the alerts come from (the Netcool/OMNIbus bridge, `bridge-alerts-netcool-default`) and the options for clickable alerts (Kibana Discover, Netcool Web GUI, ServiceNow) | MIM V5 | Done; Round 23 queries to run | `ALERT-DRILLDOWN.md` |
| 4 Nov | Updated the MIM KPI spreadsheet for MIM V5: 10 rows revised, 3 KPIs added; evidence pictures kept | MIM V5 | Done | `Dashboard Testing and Verification Template.xlsx` |
| 4 Nov | Wrote the **MIM V5 user manual** | MIM V5 | Done | `MIM-V5-USER-MANUAL.md` |

**Open (MIM):**
- Run the Round 23 queries (alert source fields), then decide how to link alerts.
- Decide on the MIM V5 previews (*CI at a glance*, *health distribution* bar).
- Revisit making the Service control default to the services on the picked server (parked).
- Add the Opened-column follow-up for SLA once the ServiceNow SLA record issue is fixed.
- Continue the test cases on MIM V5 (TC-04 to TC-28 values are in the run sheet).

## Infrastructure Dashboard

| Date | Action | Status | Evidence |
|---|---|---|---|
| 3 Nov | Added the **Monitored application** control (top bar), scoping the application panels to the 138 monitored applications. Removed the Telemetry control. The dashboard is now built from MIM V4 | Done | `Infrastructure Dashboard.ndjson`, `tools/build_infra_dashboard.py` |
| 3 Nov | Wrote the **user manual**, with five demo scenes (estate overview, eFile, server with APM, change and database, network alerts) | Done | `INFRA-DASHBOARD-MANUAL.md` |
| 3 Nov | Wrote the activity log since 28 Oct, as a new *Activity log* sheet in the KPI workbook and as a Markdown file | Done | `INFRA-DASHBOARD-KPIS.xlsx`, `INFRA-DASHBOARD-ACTIVITY-LOG.md` |
| 4 Nov | Made the controls hard to miss: icons in the control titles, three numbered "Start here" banners (sections 1–3), full-width top-bar controls | Done | `tools/build_infra_dashboard.py`, test `test_infra_dashboard_2026-10-28.py` |
| 4 Nov | Updated the user manual for the new controls | Done | `INFRA-DASHBOARD-MANUAL.md` |

**Open (Infrastructure Dashboard):**
- Run the demo scenes on the dashboard itself and share screenshots.
- Cloud health (#11): run check CG7 (is node memory split by type?); Cloud SQL blocked until the CMDB and the GCP
  collection cover the same databases.
- Custom integration health (#12): needs a definition.
- User impact (#3) and VMware health (#10): waiting for their integrations.
