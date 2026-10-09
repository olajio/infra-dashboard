# MIM V3 — using `cmdb_app_dependencies_v2` for app relationships and "applications impacted"

**Status:** proposal, based on the 10,000-row sample (`cmdb_app_dependencies_v2.csv`); Round 6 queries
(`queries_ro_run.md`) confirm it against the whole index before building · **Date:** 9 Oct 2026

## What the sample shows

Each record is one parent → child link between two CIs, with each side's name, class, environment, status and sys_id,
the relationship type (as a ServiceNow sys_id only) and, on business applications, the APM number and APM service name.

| Pattern (parent → child) | Rows in sample | Example | Use |
|---|---|---|---|
| Business application → Kubernetes service / deployment, Docker container / image, web application | ~600 | *Automated Claim Transaction* (APM0002870) → `clmact-pymt-subs`, `clmact-fin-subs`, `clmact-event-gen` | The APM services behind an app; the child names are the APM service names |
| Application service (*service_by_tags*, *service_discovered*, *service_calculated*) → servers | small | *Underwriting Tools PROD* → `vskau1p861` (Windows), `surfsda5` (AIX); *Tableau Cloud PROD* → `vskau1p1352`, `vskau1p1353` | **The servers an app service runs on** — fills section 2 for app-service CIs, and gives the apps impacted when a server fails |
| Application service → DB instances, SSIS, generic apps | ~250 | *Underwriting Tools PROD* → `p1dw2@lrau1p33` (Oracle), `SSIS@vskau1p861` | Databases behind an app |
| Server → ESX host, switch, VMware instance | ~1,500 | Windows server → ESX host; Linux server → IP switch | Infrastructure a server depends on |
| Computer / Kubernetes namespace / server → *(no child name)* | ~7,000 (70 %) | `w365-vima-…` → — | No use: no child to follow |

**Direction:** the parent depends on the child. So for a selected CI:

- **Upstream (impacted):** records where the CI is the **child** → the applications / app services that depend on it.
  *A failing server `vskau1p861` impacts Underwriting Tools PROD.*
- **Downstream (what it runs on):** records where the CI is the **parent** → its servers, databases, containers.
  *Selecting Underwriting Tools PROD gives its servers, so section 2 can show their health.*

"Automated Claim Transaction **PROD**" (the CI you picked) is not in the sample; its business application
*Automated Claim Transaction* is, with its Kubernetes services. Query AE checks how the two are linked.

## Can the dashboard show how many apps are impacted?

**Yes, with this index.**

- **Per selected CI (section 2):** count the distinct applications / app services that depend on the CI
  (upstream), plus the business applications behind those app services if the index links them (query AF).
- **Across all active P1 / P2 (section 1):** one tile, *Applications impacted*, counting the distinct applications that
  depend on any CI with an active P1 / P2.

How complete these counts are depends on coverage: query AG measures how many P1 / P2 CIs the index knows about.

## Proposed additions (after Round 6)

1. **Section 1 tile — Applications impacted**: distinct applications depending on CIs with active P1 / P2 (RAG).
2. **Section 2 — Application relationships of the selected CI** (new panels):
   - *Applications that depend on this CI* (upstream), with class, environment and a count tile;
   - *What this CI runs on / depends on* (downstream): servers, databases, containers, with live health for servers
     (reporting / CPU / memory) and APM health for Kubernetes services.
3. **Section 2 for app-service CIs**: when the selected CI is an application service, its servers from this index
   are added to the infrastructure panels (Infra, Middleware, Process, Logs) so they no longer come up empty.
   Heavier queries; built and timed after Round 6.

## What Round 6 must confirm

| Query | Why |
|---|---|
| AA | Whether the index has `@timestamp`. Without it, a panel mixing it with timestamped data loses its rows to the dashboard time filter (same as the SLO summaries), so these panels are built without a time field and filter time in the query |
| AB | Size: decides whether the section 1 tile can scan the index on every refresh |
| AC, AF | The full set of parent → child patterns, and whether app services link to business applications |
| AD | Readable relationship names ("Runs on", "Depends on", "Virtualized by" …) for the sys_ids |
| AE | How the demo CI is linked |
| AG | Coverage of P1 / P2 CIs, i.e. how often the new panels will have something to show |
