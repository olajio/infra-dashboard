# MIM V3 — using `cmdb_app_dependencies_v2` for app relationships and "applications impacted"

**Status:** built in MIM V3 (9 Oct 2026) after Round 6 · **Date:** 9 Oct 2026

## Round 6 results and what was built

| Query | Result | Consequence |
|---|---|---|
| AA | No `@timestamp`; `*_ci.*` fields are text with a `.keyword` sub-field; missing values are often the string `"null"` | Panels use the `.keyword` fields and treat `"null"` as empty. Lens panels must read the index on its own (below) |
| AB | 10.6 M records, 7.8 M with a child name; 1.05 M parents, 0.76 M children | Too big to scan without a filter: every query filters on the CI name or on application classes first |
| AC, AF | Mostly infrastructure (disks, storage, Kubernetes, cloud, network). Application pairs: business application → application service (Consumes), application service → servers (Runs on), → batch jobs (Uses), → other application services (Depends on) | "Applications" = business applications and application services (by tags, calculated, discovered, auto) |
| AD | Names of the 29 relationship types | Shown as "Runs on", "Depends on", "Consumes" … |
| AE | *Automated Claim Transaction PROD* depends on 436 batch jobs, 3 servers, Kubernetes, Tomcat and other services; 30+ application services depend on it | Its section 2 now lists both directions |
| AG | 375 of 425 P1 / P2 CIs (6 months) have parents in the index, 362 on average, mostly infrastructure | Counting only application parents is essential |

**Built:**

1. Section 1 — **Applications impacted** tile.
2. Section 2 — **Blast radius** (count), **Applications that depend on this CI** and **What this CI runs on** (CMDB
   status).

**Not possible yet — live health in *What this CI runs on*:** Kibana filters every row of a Lens ES|QL panel on
the timestamp it finds in the indices the panel reads. A panel that reads this index together with metrics or
incidents therefore loses every dependency record (no timestamp), whatever the panel's settings (*KIBANA-LIMITATIONS.md*,
row 20). *Applications impacted* avoids it as a Vega panel (Vega adds no time filter), but Vega cannot follow the CI
control, so that route is closed for section 2. **Fix:** give the dependency records an `@timestamp` (the sync time,
e.g. a `set` processor in the index's ingest pipeline). The live version (active P1 / P2 on each item, server
reporting and CPU, APM error rate for Kubernetes services) is written and tested, ready to switch on.

---

*The proposal below is kept as written before Round 6.*

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
