# Review of `updated mim dashboard.ndjson` (15 Oct 2026)

Compared with `MIM V3.ndjson` in this repo. Nothing has been changed yet.

## What is unchanged

All 26 existing panels (queries, layout, links) and the three controls (Incident, CI, Service) are identical to the
repo version, so everything from 9–14 Oct is intact.

## What the colleague added

- **A new section**, still named "New collapsible section", at the bottom below section 4. It holds:
  - an inline filter control on `parent_ci.name` from the dependency index;
  - four tables: **Database View**, **Server View**, **Middleware View** and **Application View**.
- **A data view** for `cmdb_app_dependencies_v2` (time field `parent_ci.last_updated`), which the control needs.
- **Two dashboard-level changes:** the default time range went from the last 24 hours to the last 3 years, and
  sections 1–4 are now saved collapsed.

## Against the to-do list

| Ask | Status |
|---|---|
| Related CIs grouped by class (middleware / database / server / application) | **Partly done, with bugs** (below) |
| Application health from its services | **Not done.** Application View lists names and classes only, with no health |
| Table to auto-select an incident | Not done |
| Users impacted from CMDB or RUM | Not done (still the demo number) |
| "Service health" | Still needs clarifying |
| Live health in *What this CI runs on* | Not done (needs `@timestamp` on the dependency index) |

## Bugs in the new section

### Serious
1. **Database View matches everything.** Its filter `LIKE "*db*"` matches every class, because all ServiceNow classes
   start with `cmdb_ci_`. So it lists servers, disks, network gear and so on.
2. **The other filters are too broad too:**
   - Server View's `"*server*"` also catches application servers (Tomcat is `cmdb_ci_app_server_tomcat`) and web
     servers.
   - Application View's `"*service*"` catches Kubernetes services, load-balancer services, cloud service accounts
     and Oracle DB services.
   - Middleware View includes Kubernetes, Docker and containers, which are not in the client's middleware list
     (application servers only, see `relationships1.png`).
   - The fix is to match the exact class lists, which Round 10 (AU / AV) will give.
3. **The views ignore the Incident and CI controls.** They are scoped only by the new filter control, so the MIM has
   to pick the CI a second time, unlike every other panel.
4. **The new control may blank the rest of the dashboard.** It applies the filter `parent_ci.name.keyword = X`. If
   Kibana applies that filter dashboard-wide rather than just to the new section, every other panel reads indices
   without that field and goes empty once something is selected. Needs testing on 9.5.
5. **Heavy and meaningless with nothing selected.** With no CI picked, each view aggregates the whole index
   (10.6 million records) on every 5-minute refresh, four times over, and lists the CIs with the most relationship
   records.

### Moderate
6. **Default time is now the last 3 years.** Probably changed so the control's data view shows values, but it changes
   every section 2 panel that follows the time picker: Server Health's CPU p90 and peak memory would cover 3 years,
   Logs would look back 3 years, and the queries get heavy. It should go back to 24 hours.
7. **Sections 1–4 are saved collapsed.** On import the dashboard opens with everything folded away and the overview
   hidden until someone expands it.
8. **Only one direction.** Filtering on `parent_ci.name` shows what the CI runs on, never what uses it. The views
   also mix child and parent names (`COALESCE`), so the selected CI can show up in its own list.
9. **No CMDB link and no status.** The name column is created by the query, so Kibana 9.5 cannot link it to the CMDB.
   The views also show no CMDB operational status, which *What this CI runs on* already does.

### Cosmetic
10. The section title is still "New collapsible section". Column headers are raw (`ci_name`, `ci_class`), with row
    numbers and no panel descriptions. Rows are sorted by a hidden count of relationship records rather than anything
    meaningful.

## Suggestion

- Keep the idea and the layout, and rebuild the four views:
  - drive them from the Incident and CI controls, like the rest of section 2, and drop the extra filter control;
  - use the exact class lists from Round 10, and cover both directions;
  - add CMDB status and CMDB links.
- Restore the 24-hour default and expanded sections.
- Run Round 10 first to settle the class lists.
