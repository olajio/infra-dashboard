# Action tracker: 3–17 Nov 2026

Actions for the action tracker spreadsheet. MIM and the Infrastructure Dashboard are listed separately. MIM is up to
date to 17 Nov (see *MIM progress, 5–17 Nov*); the Infrastructure Dashboard is up to date to 17 Nov (see
*Infrastructure Dashboard progress, 5–17 Nov*).

## MIM progress summary (to 17 Nov), for the spreadsheet

> **MIM V5: on track.** Since 4 Nov MIM V5 has been refined from the team's feedback and the 16 Nov recap: P3 removed
> (MIM covers P1 and P2 only), the SLA column removed, the alert panels cut to the last 7 days, and *Alerts on this
> CI* removed. The time-to-resolve chart now shows a rolling 7-day median against the 4 h / 8 h targets. Agreed with
> James Patock and Dan Tautges to report **P1 MTTR** (from when the incident became a P1) and **P2 Duration** (from
> opened) instead of the ServiceNow SLAs; both are now on the dashboard, with a *Linked incidents* count for user
> impact and On Hold P1s shown. Every active P1 and P2 is now shown whatever its age. Every change is tested, and the user manual and MIM KPI sheet are up to date.
> **Next:** check the new MTTR columns on live data; decisions pending on alert links and the two design previews.

## Infrastructure Dashboard progress summary (to 17 Nov), for the spreadsheet

> **Infrastructure Dashboard: on track; now the Infrastructure Overview.** On 5 Nov the CI-driven Infrastructure
> Dashboard got the MIM V5 look, the Incident control, MIM's Active P1 / P2-over-8 h table and links to the detailed
> dashboards. After the 6 Nov team review it became a landing page, the **Infrastructure Overview** (built 10 Nov):
> one status tile per domain (Server, Database, Middleware, VMware, Cloud, Network) linking to its detailed dashboard,
> KPI tiles, active incidents, open alerts by domain, a Change Request Summary as on Portfolio, and data freshness.
> Domain rules were checked against every production CI class, and VMware status now comes from vSphere health. On
> 17 Nov the team's version (*Infrastructure Overview v2*) became the basis: links are grouped into *Related
> Dashboards* and *Detailed Dashboards*, and a *Future Releases* section shows the roadmap and planned AI insights.
> **Next:** import v2 and check it on live data; VMware and Cloud SQL coverage depend on their integrations.

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

## MIM progress, 5–17 Nov

| Date | Action | Dashboard | Status | Evidence |
|---|---|---|---|---|
| 5 Nov | Reviewed the Round 23 alert results and recommended how to link alerts: open the alert's history in Kibana Discover, and the CI's record in the ServiceNow CMDB; the Netcool Web GUI once the Netcool team confirms the server name | MIM V5 | Waiting for go-ahead | `ALERT-DRILLDOWN.md` |
| 6 Nov | *Open alerts, no incident* tile now follows the Incident / CI controls; *Escalate* renamed *Escalation Channel*; section 2 laid out side by side; *Time to Resolve* on one axis | MIM V5 | Done | Patch 06a, test `test_mim_v5_2026-11-06a.py` |
| 6 Nov | Updated the MIM KPI spreadsheet for the 6 Nov changes | MIM V5 | Done | `Dashboard Testing and Verification Template.xlsx` |
| 9–10 Nov | User manual: explained the difference between *Alerts on this CI* and *Open Alerts with No Incident* | MIM V5 | Done | `MIM-V5-USER-MANUAL.md` |
| 11 Nov | Removed *Alerts on this CI*; *Changes in the Last 7 Days* takes the full row | MIM V5 | Done | Patch 11a, test `test_mim_v5_2026-11-11a.py` |
| 11 Nov | Preview of links from the section 3 health panels to the detailed infrastructure dashboards | MIM V5 | Preview made; not built | `previews/mim-v5-health-links-preview.png` |
| 13 Nov | Removed the SLA column from *Active Incidents* (team request) | MIM V5 | Done | Patch 13a, test `test_mim_v5_2026-11-13a.py` |
| 13 Nov | *Time to Resolve vs Target* fixed to show real time to resolve (opened → resolved), as a median so a few very long incidents do not distort it; checked against production (TTR1 / TTR2) | MIM V5 | Done | Patches 13b, 13c |
| 16 Nov | Worked through the 16 Nov recap: checks for PBA, CMDB link age, P1 MTTR and P2 duration. Result: no PBA field exists, so no change | MIM V5 | Done | `mim_recap.txt`, `queries_to_run.md`, `recap_results*.txt` |
| 16 Nov | Alert panels read the last 7 days instead of 5 years (CMDB links are re-sent daily, so nothing is lost) | MIM V5 | Done | Patch 16a, test `test_mim_v5_2026-11-16a.py` |
| 17 Nov | Removed P3 from the whole dashboard (MIM covers P1 and P2 only); *Active Incidents* about 25 % narrower, *Time to Resolve* wider | MIM V5 | Done | Patch 17a, test `test_mim_v5_2026-11-17a.py` |
| 17 Nov | *Time to Resolve* as a rolling 7-day median, so one slow day no longer makes the line jump | MIM V5 | Done | Patch 17b |
| 17 Nov | Reviewed the SLA email thread (James Patock, Dan Tautges) and found the data for James's proposal (checks O1–O5): Outage records are not in Elastic, but the incident timeline gives the exact time an incident became a P1 | MIM V5 | Done | `MIM SLA update.docx`, `outage_results.txt`, `timeline_results*.txt` |
| 17 Nov | Built **P1 MTTR** (from when the incident became a P1) and **P2 Duration** (from opened): new *Time as P1 / Duration (h)* and *Linked incidents* columns in *Active Incidents*; On Hold P1s shown (tiles too); P1 line of *Time to Resolve* = MTTR | MIM V5 | Done; to check on live data | Patch 17c, test `test_mim_v5_2026-11-17c.py` |
| 17 Nov | Team decision: show **every active P1 and P2 regardless of age** on every panel. *P2 over 8 h* tile → *Active P2*; *Active Incidents* shows every active P1 and P2 | MIM V5 | Done | Patch 17d, test `test_mim_v5_2026-11-17d.py` |
| 6–17 Nov | Kept the MIM V5 user manual and the MIM KPI spreadsheet up to date with every change | MIM V5 | Done | `MIM-V5-USER-MANUAL.md`, `Dashboard Testing and Verification Template.xlsx` |

**Open (MIM), as of 17 Nov:**
- Import the updated MIM V5 and check the new MTTR / Duration and Linked incidents columns on live data.
- Go-ahead on the alert links (Discover and CMDB now; Netcool Web GUI after the Netcool team answers).
- Decide on the MIM V5 previews (*CI at a glance*, *health distribution* bar, links to the detailed dashboards).
- Only if James needs the MIM team's manual adjustments: ask the ServiceNow team to add the Outage table to the
  integration.
- Share screenshots with Matt (MIM user manual) and Abhishek Panchal (Incident Management user manual).
- Revisit making the Service control default to the services on the picked server (parked).
- Continue the test cases on MIM V5 (TC-04 to TC-28 values are in the run sheet).

**Closed since 4 Nov:** Round 23 queries run (5 Nov); the SLA follow-up is replaced by P1 MTTR / P2 Duration
(17 Nov).

## Infrastructure Dashboard

| Date | Action | Status | Evidence |
|---|---|---|---|
| 3 Nov | Added the **Monitored application** control (top bar), scoping the application panels to the 138 monitored applications. Removed the Telemetry control. The dashboard is now built from MIM V4 | Done | `Infrastructure Dashboard.ndjson`, `tools/build_infra_dashboard.py` |
| 3 Nov | Wrote the **user manual**, with five demo scenes (estate overview, eFile, server with APM, change and database, network alerts) | Done | `INFRA-DASHBOARD-MANUAL.md` |
| 3 Nov | Wrote the activity log since 28 Oct, as a new *Activity log* sheet in the KPI workbook and as a Markdown file | Done | `INFRA-DASHBOARD-KPIS.xlsx`, `INFRA-DASHBOARD-ACTIVITY-LOG.md` |
| 4 Nov | Made the controls hard to miss: icons in the control titles, three numbered "Start here" banners (sections 1–3), full-width top-bar controls | Done | `tools/build_infra_dashboard.py`, test `test_infra_dashboard_2026-10-28.py` |
| 4 Nov | Updated the user manual for the new controls | Done | `INFRA-DASHBOARD-MANUAL.md` |

## Infrastructure Dashboard progress, 5–17 Nov

| Date | Action | Status | Evidence |
|---|---|---|---|
| 5 Nov | Gave the dashboard the **MIM V5 look**: tile icons (green at 0), section icons, row numbers; new *Active Elastic infra alerts* tile | Done | `tools/build_infra_dashboard.py` |
| 5 Nov | Added section 4 **Detailed dashboards**: links to the Server, Database, Middleware, VMware and Cloud infra dashboards, plus Applications Operations and MIM | Done | `respective_detailed_dashboards.txt` |
| 5 Nov | Added the **Incident control** (as on MIM: a picked incident selects its CI); *Incidents on this CI* replaced by MIM's **Active Incidents (P1 · P2 over 8 h)** table, with MIM's 8 h rule for P2. Built on the team's layout (`infra2.ndjson`) | Done | Tests, `INFRA-DASHBOARD-MANUAL.md` |
| 5 Nov | Fixed GKE memory after check CG7: *Mem peak* counts non-evictable memory only | Done | `INFRA-DASHBOARD-ACTIVITY-LOG.md` |
| 6 Nov | After the team review: proposed the landing-page KPIs (20, with relevance and achievability), a mockup, a usage flowchart and a walkthrough | Done | `INFRA-OVERVIEW-KPIS.md`, `previews/`, *Overview KPIs* sheet in `INFRA-DASHBOARD-KPIS.xlsx` |
| 10 Nov | **Built the Infrastructure Overview** (landing page, no controls): domain status tiles linking to each detailed dashboard, KPI tiles, active P1 / P2-over-8 h incidents, open alerts by domain, top alerts, changes, trend, data freshness. Replaces the CI-driven dashboard (same id); the old one is archived | Done | `Infrastructure Overview.ndjson`, `tools/build_infra_overview.py`, `INFRA-OVERVIEW-MANUAL.md` |
| 11 Nov | Checked the domain rules against every production CI class (IO1 / IO2) and fixed them (e.g. F5 BIG-IP → Network, Hardware → Server); all 49 classes land in a domain | Done | Test, `INFRA-OVERVIEW-MANUAL.md` |
| 11 Nov | Added a **Change Request Summary** as on Portfolio v4 (open N / S / E, implemented this week vs last, pending approval, scheduled next 7 days) with the change list beside it; fixed it for production's change fields | Done | `Infrastructure Overview.ndjson` |
| 11 Nov | Dashboard links as two lists side by side; Portfolio Dashboard added | Done | `Infrastructure Overview.ndjson` |
| 12 Nov | **VMware tile from vSphere health**: hosts, VMs, datastores over 80 %, host CPU / memory / disk latency, with the thresholds from `vmware_data.xlsx`; checked on production (VM1: 4 hosts, 5 datastores, 46 VMs) | Done | `vmware.ndjson`, `vmware_data.xlsx`, `INFRA-OVERVIEW-MANUAL.md` |
| 17 Nov | Adopted the team's updated version (**Infrastructure Overview v2**) as the basis. Dashboard Links split into **Related Dashboards** (Executive (in progress), Portfolio, Applications Operations, Major Incident Management) and **Detailed Dashboards** (Cloud, Database, Middleware, Server, VMware) | Done | `Infrastructure Overview v2.ndjson`, `tools/infra_overview_v2_patch_2026-11-17a.py` |
| 17 Nov | Added a **Future Releases** section: *Next Release Roadmap* and *Predictive & AI Insights* cards with the planned infrastructure items | Done | `Infrastructure Overview v2.ndjson` |
| 17 Nov | Added 20 capabilities from the dashboard work to the Capability Tracker (CAP-086 to CAP-105) | Done | `Capability Tracker.xlsx` |
| 5–17 Nov | Kept the user manuals, activity log and KPI workbook up to date with every change | Done | `INFRA-DASHBOARD-MANUAL.md`, `INFRA-OVERVIEW-MANUAL.md`, `INFRA-DASHBOARD-ACTIVITY-LOG.md` |

**Open (Infrastructure Dashboard / Overview), as of 17 Nov:**
- Import *Infrastructure Overview v2* and check it on live data (links, Future Releases cards).
- Executive Dashboard: add its link once the dashboard exists (shown as *In Progress*).
- VMware (#10): only 4 of 549 ESX hosts are collected; waiting for the vSphere integration to cover the main
  vCenters. CPU ready time, ballooning, swapping and packet loss are not collected.
- Cloud health (#11): Cloud SQL blocked until the CMDB and the GCP collection cover the same databases.
- Network: no detailed dashboard yet.
- Custom integration health (#12): needs a definition.
- User impact (#3): waiting for the ServiceNow user base and RUM integrations.

**Closed since 4 Nov:** CG7 (GKE memory) checked and fixed (5 Nov). The demo scenes on the CI-driven dashboard are no
longer needed: it was replaced by the Infrastructure Overview on 10 Nov.
